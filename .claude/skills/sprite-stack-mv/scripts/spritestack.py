#!/usr/bin/env python3
"""Sprite stacking for music videos: build voxel-slice models, animate them to the beat, render frames or video,
and layer the result with other footage (for example JIZURA's transparent lyric layers).

A model is a pile of 2D slices, bottom to top. Each frame, every slice is rotated by the same angle and drawn one
step higher than the one below, which reads as a rotating 3D object while every pixel stays pixel art.

    spritestack.py model      MODEL -o sheet.png          convert any model to a slice sheet
    spritestack.py turntable  MODEL -o spin.gif           check a model from every side
    spritestack.py still      scene.json -t 0,2,4 -o s.png   contact sheet of moments in a scene
    spritestack.py render     scene.json -o out.mp4       .mp4 / .mov (alpha) / .gif / directory of PNGs
    spritestack.py composite  -o final.mp4 LAYER...       stack layers bottom to top, add audio

Needs Python 3.9+, Pillow and numpy; ffmpeg for video. See ../references/ for the model and scene formats.
"""
import argparse, ast, json, math, os, re, struct, subprocess, sys, tempfile, zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


# ---------- colours ----------
def rgba(c, palette=None):
    if c is None:
        return (0, 0, 0, 0)
    if isinstance(c, (list, tuple)):
        c = list(c) + [255] * (4 - len(c))
        return tuple(int(v) for v in c[:4])
    if palette and c in palette:
        return rgba(palette[c])
    s = c.lstrip('#')
    if len(s) in (3, 4):
        s = ''.join(ch * 2 for ch in s)
    if len(s) == 6:
        s += 'ff'
    if len(s) != 8 or any(ch not in '0123456789abcdefABCDEF' for ch in s):
        raise SystemExit(f'colour not understood: {c!r} (use "#rrggbb", "#rrggbbaa" or a palette name)')
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4, 6))


# ---------- models: everything becomes V[z, y, x, 4] uint8, z = 0 is the bottom slice ----------
def _find_font(name):
    if name and os.path.exists(name):
        return name
    try:
        out = subprocess.run(['fc-match', '-f', '%{file}', name or 'sans:lang=ja'], capture_output=True, text=True).stdout
        if out and os.path.exists(out):
            return out
    except OSError:
        pass
    raise SystemExit(f'font not found: {name!r}. Give "font" as a path to a .ttf/.otf file.')


def _text_image(p, palette):
    font = ImageFont.truetype(_find_font(p.get('font')), int(p.get('font_size', 24)))
    text = p['text']
    box = font.getbbox(text)
    im = Image.new('L', (max(1, box[2] - box[0]), max(1, box[3] - box[1])), 0)
    ImageDraw.Draw(im).text((-box[0], -box[1]), text, fill=255, font=font)
    mask = np.asarray(im) >= int(p.get('threshold', 128))  # hard edge: anti-aliased greys are not pixel art
    out = np.zeros(mask.shape + (4,), np.uint8)
    out[mask] = rgba(p.get('color', '#ffffff'), palette)
    return out


def _part_voxels(p, palette, base):
    """One part -> (xs, ys, zs, colours[n,4]). Units are voxels; x right, y toward the viewer at yaw 0, z up."""
    kind = p['type']
    col = np.array(rgba(p.get('color', '#ffffff'), palette), np.float32)
    top = np.array(rgba(p['color_top'], palette), np.float32) if 'color_top' in p else None

    def solid(lo, hi, inside):
        lo = [int(math.floor(v)) for v in lo]
        hi = [int(math.ceil(v)) for v in hi]
        if any(h <= l for l, h in zip(lo, hi)):
            return np.zeros(0, int), np.zeros(0, int), np.zeros(0, int), np.zeros((0, 4), np.uint8)
        x, y, z = np.mgrid[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
        m = inside(x + .5, y + .5, z + .5)
        x, y, z = x[m], y[m], z[m]
        if top is not None and hi[2] - lo[2] > 1:
            f = ((z - lo[2]) / (hi[2] - lo[2] - 1))[:, None]
            c = col * (1 - f) + top * f
        else:
            c = np.repeat(col[None], len(x), 0)
        return x, y, z, c.round().astype(np.uint8)

    if kind == 'box':
        a, b = p['from'], p['to']
        return solid(a, b, lambda x, y, z: np.ones(x.shape, bool))
    if kind == 'cylinder':  # "radius_top" tapers it into a cone or a trunk
        cx, cy = p['center']
        z0, z1 = p['z']
        r0 = p['radius']
        r1 = p.get('radius_top', r0)
        rm = max(r0, r1)
        def inside(x, y, z):
            r = r0 + (r1 - r0) * (z - z0) / max(1e-6, z1 - z0)
            return (x - cx) ** 2 + (y - cy) ** 2 <= r * r
        return solid([cx - rm, cy - rm, z0], [cx + rm, cy + rm, z1], inside)
    if kind in ('sphere', 'ellipsoid'):
        c = p['center']
        r = p.get('radii') or [p['radius']] * 3
        return solid([c[i] - r[i] for i in range(3)], [c[i] + r[i] for i in range(3)],
                     lambda x, y, z: ((x - c[0]) / r[0]) ** 2 + ((y - c[1]) / r[1]) ** 2 + ((z - c[2]) / r[2]) ** 2 <= 1)
    if kind == 'lathe':  # one radius per slice: vases, lanterns, trees, bottles
        cx, cy = p['center']
        z0 = p.get('z0', 0)
        radii = p['radii']
        cols = p.get('colors')
        outs = []
        for i, r in enumerate(radii):
            q = dict(type='cylinder', center=[cx, cy], radius=r, z=[z0 + i, z0 + i + 1],
                     color=(cols[i % len(cols)] if cols else p.get('color', '#ffffff')))
            outs.append(_part_voxels(q, palette, base))
        return tuple(np.concatenate([o[k] for o in outs]) for k in range(4))
    if kind == 'layers':  # hand-drawn slices: "rows" is one slice, or a list of slices, bottom first
        key = {k: rgba(v, palette) for k, v in p['key'].items()}
        rows = p['rows']
        slices = rows if isinstance(rows[0], list) else [rows]
        ox, oy = p.get('at', [0, 0])
        z0, z1 = p['z'] if 'z' in p else (p.get('z0', 0), None)
        if z1 is not None and len(slices) == 1:
            slices = slices * (z1 - z0)
        xs, ys, zs, cs = [], [], [], []
        for k, sl in enumerate(slices):
            for j, row in enumerate(sl):
                for i, ch in enumerate(row):
                    if ch in key and key[ch][3]:
                        xs.append(ox + i); ys.append(oy + j); zs.append(z0 + k); cs.append(key[ch])
        return np.array(xs, int), np.array(ys, int), np.array(zs, int), np.array(cs, np.uint8).reshape(-1, 4)
    if kind in ('flat', 'upright', 'text'):
        if kind == 'text' or 'text' in p:
            img = _text_image(p, palette)
        else:
            img = np.asarray(Image.open(base / p['image']).convert('RGBA'))
        mode = p.get('mode', 'flat' if kind == 'flat' else 'upright')
        depth = int(p.get('depth', 2))
        ox, oy, oz = (list(p.get('at', [0, 0, 0])) + [0, 0, 0])[:3]
        v, u = np.nonzero(img[..., 3] >= 128)
        c = img[v, u]
        c[:, 3] = 255
        n = len(u)
        k = np.repeat(np.arange(depth), n)
        u, v, c = np.tile(u, depth), np.tile(v, depth), np.tile(c, (depth, 1))
        if mode == 'flat':  # lies on the ground, readable from above; depth is its thickness upward
            return ox + u, oy + v, oz + k, c
        return ox + u, oy + k, oz + (img.shape[0] - 1 - v), c  # stands up facing the viewer; depth runs along y
    raise SystemExit(f'unknown part type: {kind!r}')


def model_from_spec(spec, base):
    palette = spec.get('palette', {})
    parts = spec.get('parts')
    if parts is None:  # shorthand: {"text": "..."} or {"image": "..."} alone is a one-part model
        parts = [dict(spec, type='text' if 'text' in spec else 'upright')]
    built = [(p, _part_voxels(p, palette, base)) for p in parts]
    pts = [b for _, b in built if len(b[0])]
    if not pts:
        raise SystemExit('model has no voxels')
    if 'size' in spec:
        w, d, h = spec['size']
        off = (0, 0, 0)
    else:  # fit the box to the parts
        lo = [min(int(b[k].min()) for b in pts) for k in range(3)]
        hi = [max(int(b[k].max()) for b in pts) for k in range(3)]
        off = lo
        w, d, h = (hi[k] - lo[k] + 1 for k in range(3))
    V = np.zeros((h, d, w, 4), np.uint8)
    for p, (x, y, z, c) in built:
        x, y, z = x - off[0], y - off[1], z - off[2]
        ok = (x >= 0) & (x < w) & (y >= 0) & (y < d) & (z >= 0) & (z < h)
        V[z[ok], y[ok], x[ok]] = 0 if p.get('erase') else c[ok]
    return V


def model_from_sheet(path, slices=None, slice_size=None, layout='horizontal', top_first=False):
    im = np.asarray(Image.open(path).convert('RGBA'))
    H, W = im.shape[:2]
    if slice_size:
        sw, sh = slice_size
    elif slices:
        sw, sh = (W // slices, H) if layout == 'horizontal' else (W, H // slices)
    else:  # square slices in a strip
        sw = sh = min(W, H)
    cols, rows = W // sw, H // sh
    cells = [im[r * sh:(r + 1) * sh, c * sw:(c + 1) * sw] for r in range(rows) for c in range(cols)]
    if slices:
        cells = cells[:slices]
    while len(cells) > 1 and not cells[-1][..., 3].any():
        cells.pop()  # empty padding cells at the end of a grid
    if top_first:
        cells.reverse()
    return np.stack(cells)


def model_from_vox(path):
    """MagicaVoxel .vox (first model in the file)."""
    data = Path(path).read_bytes()
    if data[:4] != b'VOX ':
        raise SystemExit(f'{path}: not a MagicaVoxel .vox file')
    size = vox = pal = None
    i = 8

    def walk(i, end):
        nonlocal size, vox, pal
        while i < end:
            cid, n, m = data[i:i + 4], *struct.unpack('<II', data[i + 4:i + 12])
            body = data[i + 12:i + 12 + n]
            if cid == b'SIZE' and size is None:
                size = struct.unpack('<III', body[:12])
            elif cid == b'XYZI' and vox is None:
                k = struct.unpack('<I', body[:4])[0]
                vox = np.frombuffer(body[4:4 + 4 * k], np.uint8).reshape(-1, 4)
            elif cid == b'RGBA':
                pal = np.frombuffer(body[:1024], np.uint8).reshape(-1, 4)
            walk(i + 12 + n, i + 12 + n + m)
            i += 12 + n + m
    walk(i, len(data))
    if size is None or vox is None:
        raise SystemExit(f'{path}: no voxel data found')
    if pal is None:
        raise SystemExit(f'{path}: the file has no palette chunk; re-save it from MagicaVoxel')
    w, d, h = size
    V = np.zeros((h, d, w, 4), np.uint8)
    V[vox[:, 2], d - 1 - vox[:, 1], vox[:, 0]] = pal[vox[:, 3].astype(int) - 1]  # MagicaVoxel's y points away
    V[..., 3] = np.where(V[..., 3] > 0, 255, 0)
    return V


def load_model(path, **opt):
    path = Path(path)
    ext = path.suffix.lower()
    if ext == '.json':
        return model_from_spec(json.loads(path.read_text(encoding='utf-8')), path.parent)
    if ext == '.vox':
        return model_from_vox(path)
    if ext == '.png':
        return model_from_sheet(path, opt.get('slices'), opt.get('slice_size'), opt.get('layout', 'horizontal'), opt.get('top_first', False))
    raise SystemExit(f'{path}: use a .json model, a MagicaVoxel .vox, or a .png slice sheet')


def bake_walls(V, wall):
    """Darken every voxel that has another directly above it. In a stack, the visible part of such a voxel is the
    sliver not covered by the slice above, i.e. a side wall, so this lights tops and shades sides for free."""
    if not wall or len(V) < 2:
        return V
    V = V.copy()
    covered = V[1:, ..., 3] > 0
    V[:-1, ..., :3][covered] = (V[:-1, ..., :3][covered] * (1 - wall)).astype(np.uint8)
    return V


def to_sheet(V):
    return Image.fromarray(np.concatenate(list(V), axis=1))  # horizontal strip, bottom slice first


# ---------- drawing one stack ----------
def render_stack(V, yaw=0.0, scale=1.0, gap=1.0, squash=1.0, shade=0.0, outline=None, pivot=None):
    """Returns (sprite[H,W,4], anchor_x, anchor_y, footprint[H2,W,bool], foot_anchor_y): the anchor is where the
    centre of the bottom slice sits. yaw in degrees; gap = screen pixels between slices per unit of scale."""
    h, d, w, _ = V.shape
    px, py = pivot if pivot else (w / 2, d / 2)
    rad = max(math.hypot(px, py), math.hypot(w - px, py), math.hypot(px, d - py), math.hypot(w - px, d - py))
    n = int(math.ceil(rad * scale)) * 2 + 2
    nh = max(2, int(math.ceil(rad * scale * squash)) * 2 + 2)
    u = (np.arange(n) + .5 - n / 2) / scale
    v = (np.arange(nh) + .5 - nh / 2) / (scale * squash)
    gx, gy = np.meshgrid(u, v)
    a = math.radians(yaw)
    sx = np.floor(math.cos(a) * gx + math.sin(a) * gy + px).astype(int)
    sy = np.floor(-math.sin(a) * gx + math.cos(a) * gy + py).astype(int)
    ok = (sx >= 0) & (sx < w) & (sy >= 0) & (sy < d)
    R = V[:, np.clip(sy, 0, d - 1), np.clip(sx, 0, w - 1)]  # every slice rotated with one index map
    R[:, ~ok] = 0
    if shade:
        f = 1 - shade * (1 - np.arange(h) / max(1, h - 1))  # lower slices darker: cheap depth
        R = R.copy()
        R[..., :3] = (R[..., :3] * f[:, None, None, None]).astype(np.uint8)
    g = gap * scale
    fill = max(1, int(math.ceil(g)))  # repeat each slice so a gap above 1 px leaves no holes
    rise = int(round((h - 1) * g)) + fill - 1
    pad = 1 if outline else 0
    out = np.zeros((nh + rise + 2 * pad, n + 2 * pad, 4), np.uint8)
    for i in range(h):
        m = R[i, ..., 3] > 0
        if not m.any():
            continue
        y0 = pad + rise - int(round(i * g))
        for k in range(fill):
            out[y0 - k:y0 - k + nh, pad:pad + n][m] = R[i][m]
    if outline:
        s = out[..., 3] > 0
        e = np.zeros_like(s)
        e[1:] |= s[:-1]; e[:-1] |= s[1:]; e[:, 1:] |= s[:, :-1]; e[:, :-1] |= s[:, 1:]
        out[e & ~s] = outline
    foot = R[..., 3].max(axis=0) > 0
    return out, pad + n / 2, pad + rise + nh / 2, foot, nh / 2


def blit(dst, src, x, y, opacity=1.0):
    """Alpha-over src onto dst (both RGBA uint8) with its top-left at (x, y); clips at the edges."""
    H, W = dst.shape[:2]
    h, w = src.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32)
    d = dst[y0:y1, x0:x1].astype(np.float32)
    sa = s[..., 3:4] / 255 * opacity
    da = d[..., 3:4] / 255
    oa = sa + da * (1 - sa)
    rgb = (s[..., :3] * sa + d[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-6)
    dst[y0:y1, x0:x1, :3] = rgb.round()
    dst[y0:y1, x0:x1, 3:4] = (oa * 255).round()


# ---------- animated values: a number, an expression of t / b, or keyframes ----------
def _hash(n):
    n = math.sin(n * 127.1 + 311.7) * 43758.5453
    return n - math.floor(n)

def _noise(x, seed=0):
    i = math.floor(x); f = x - i; f = f * f * (3 - 2 * f)
    return (_hash(i + seed * 57) * (1 - f) + _hash(i + 1 + seed * 57) * f) * 2 - 1

_frac = lambda x: x - math.floor(x)
FUNCS = dict(
    sin=math.sin, cos=math.cos, abs=abs, min=min, max=max, floor=math.floor, sqrt=math.sqrt, pow=pow, exp=math.exp,
    pi=math.pi, tau=math.tau, frac=_frac,
    clamp=lambda x, a=0, b=1: max(a, min(b, x)),
    lerp=lambda a, b, f: a + (b - a) * f,
    smooth=lambda x: (lambda f: f * f * (3 - 2 * f))(max(0, min(1, x))),
    pulse=lambda x, k=4: math.exp(-k * _frac(x)),             # 1 on every whole x, then decays: a kick
    bounce=lambda x: abs(math.sin(math.pi * x)),               # one hop per whole x
    tri=lambda x: 1 - abs(2 * _frac(x) - 1),                   # 0 -> 1 -> 0 per whole x
    step=lambda x, n=1: math.floor(x * n) / n,                 # hold a value, change n times per unit
    ramp=lambda x, a, b: max(0, min(1, (x - a) / (b - a))) if b != a else float(x >= a),  # 0 before a, 1 after b
    noise=_noise, rand=lambda seed: _hash(seed),
)
_ALLOWED = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Compare, ast.IfExp, ast.BoolOp, ast.Call, ast.Name, ast.Load,
            ast.Constant, ast.operator, ast.unaryop, ast.cmpop, ast.boolop)
_cache = {}

def compile_value(v):
    if isinstance(v, bool) or isinstance(v, (int, float)):
        return lambda env: v
    if isinstance(v, dict) and 'keys' in v:  # {"keys": [[at, value], ...], "unit": "beat"|"sec", "ease": "linear"|"smooth"|"hold"}
        keys = sorted((float(a), float(b)) for a, b in v['keys'])
        unit = 'b' if v.get('unit', 'beat').startswith('b') else 't'
        ease = v.get('ease', 'smooth')
        def f(env):
            x = env[unit]
            if x <= keys[0][0]:
                return keys[0][1]
            for (a, va), (b, vb) in zip(keys, keys[1:]):
                if x < b:
                    q = (x - a) / (b - a)
                    q = 0 if ease == 'hold' else q * q * (3 - 2 * q) if ease == 'smooth' else q
                    return va + (vb - va) * q
            return keys[-1][1]
        return f
    if isinstance(v, str):
        if v not in _cache:
            tree = ast.parse(v, mode='eval')
            for node in ast.walk(tree):  # scene files may come from anywhere: arithmetic and listed functions only
                if not isinstance(node, _ALLOWED):
                    raise SystemExit(f'expression not allowed: {v!r} ({type(node).__name__})')
                if isinstance(node, ast.Call) and not (isinstance(node.func, ast.Name) and node.func.id in FUNCS):
                    raise SystemExit(f'unknown function in expression: {v!r}')
            _cache[v] = compile(tree, '<expr>', 'eval')
        code = _cache[v]
        def f(env):
            try:
                return eval(code, {'__builtins__': {}}, {**FUNCS, **env})
            except NameError as e:
                raise SystemExit(f'expression {v!r}: {e}. Variables: t (seconds), b (beats), bar, i, n.')
        return f
    raise SystemExit(f'value not understood: {v!r}')


# ---------- scenes ----------
OBJ_DEFAULTS = dict(x=0, y=0, z=0, yaw=0, scale=1, gap=1, opacity=1, visible=1)

class Scene:
    def __init__(self, path):
        self.path = Path(path)
        s = self.spec = json.loads(self.path.read_text(encoding='utf-8'))
        self.W, self.H = int(s.get('width', 1920)), int(s.get('height', 1080))
        self.fps = float(s.get('fps', 24))
        self.ps = int(s.get('pixel_scale', 4))
        self.w, self.h = math.ceil(self.W / self.ps), math.ceil(self.H / self.ps)
        self.bpm = float(s.get('bpm', 120))
        self.offset = float(s.get('offset', 0))        # seconds until beat 0
        self.per_bar = float(s.get('beats_per_bar', 4))
        self.duration = float(s['duration']) if 'duration' in s else float(s.get('beats', 16)) * 60 / self.bpm
        self.anim_fps = s.get('anim_fps')              # e.g. 12 = animate on twos, like hand-drawn animation
        cam = s.get('camera', {})
        self.cam = {k: compile_value(cam.get(k, dv)) for k, dv in dict(yaw=0, x=0, y=0, zoom=1, squash=1).items()}
        self.yaw_steps = s.get('yaw_steps')            # e.g. 32 = snap rotation to 32 directions
        self.bg = s.get('background', 'transparent')
        self.floor = s.get('floor')
        models = {}
        self.objects = []
        for o in s.get('objects', []):
            key = json.dumps([o['model'], o.get('slices'), o.get('slice_size'), o.get('layout'), o.get('top_first'), o.get('wall')])
            if key not in models:
                V = load_model(self.path.parent / o['model'], **{k: o[k] for k in ('slices', 'slice_size', 'layout', 'top_first') if k in o})
                models[key] = bake_walls(V, o.get('wall', 0.18))
            n = int(o.get('count', 1))
            for i in range(n):
                self.objects.append(dict(
                    V=models[key], i=i, n=n, spec=o,
                    vals={k: compile_value(o.get(k, dv)) for k, dv in OBJ_DEFAULTS.items()},
                    squash=compile_value(o['squash']) if 'squash' in o else None,
                    outline=rgba(o['outline']) if o.get('outline') else None))

    def env(self, t):
        if self.anim_fps:
            t = math.floor(t * self.anim_fps + 1e-6) / self.anim_fps
        b = (t - self.offset) * self.bpm / 60
        return dict(t=t, b=b, bar=b / self.per_bar)

    def background(self, env, cam):
        w, h = self.w, self.h
        bg = self.bg
        if bg == 'transparent' or bg is None:
            img = np.zeros((h, w, 4), np.uint8)
        elif isinstance(bg, str):
            img = np.tile(np.array(rgba(bg), np.uint8), (h, w, 1))
        else:  # {"gradient": [top, bottom]}
            a, b = (np.array(rgba(c), np.float32) for c in bg['gradient'])
            f = np.linspace(0, 1, h)[:, None, None]
            img = np.broadcast_to((a * (1 - f) + b * f).round().astype(np.uint8), (h, w, 4)).copy()
        fl = self.floor
        if fl:  # a checkerboard on the ground, turning with the camera: sells the rotation
            size = fl.get('size', 16)
            cols = [np.array(rgba(c), np.uint8) for c in fl.get('colors', ['#2a2a3a', '#343448'])]
            sxx, syy = np.meshgrid(np.arange(w) + .5 - w / 2, np.arange(h) + .5 - (h * fl.get('horizon', 0.5)))
            gx, gy = sxx / cam['zoom'], syy / (cam['zoom'] * cam['squash'])
            a = math.radians(cam['yaw'])
            wx = math.cos(a) * gx + math.sin(a) * gy + cam['x']
            wy = -math.sin(a) * gx + math.cos(a) * gy + cam['y']
            chk = ((np.floor(wx / size) + np.floor(wy / size)) % 2).astype(int)
            tile = np.where(chk[..., None] == 0, cols[0], cols[1])
            if 'radius' in fl:
                tile = tile.copy()
                tile[wx * wx + wy * wy > fl['radius'] ** 2, 3] = 0
            blit(img, tile.astype(np.uint8), 0, 0)
        return img

    def frame(self, t):
        """One frame at the small internal size (RGBA)."""
        env = self.env(t)
        cam = {k: f(env) for k, f in self.cam.items()}
        img = self.background(env, cam)
        ca = math.radians(cam['yaw'])
        cx, cy = self.w / 2, self.h * (self.floor or {}).get('horizon', 0.5)
        drawn = []
        for o in self.objects:
            e = dict(env, i=o['i'], n=o['n'])
            p = {k: f(e) for k, f in o['vals'].items()}
            sp = o['spec']
            if not p['visible'] or p['opacity'] <= 0 or p['scale'] <= 0:
                continue
            if 'beats' in sp and not (sp['beats'][0] <= env['b'] < sp['beats'][1]):
                continue
            if 'time' in sp and not (sp['time'][0] <= env['t'] < sp['time'][1]):
                continue
            squash = o['squash'](e) if o['squash'] else cam['squash']
            dx, dy = p['x'] - cam['x'], p['y'] - cam['y']
            rx = (math.cos(ca) * dx - math.sin(ca) * dy) * cam['zoom']
            ry = (math.sin(ca) * dx + math.cos(ca) * dy) * cam['zoom']
            yaw = p['yaw'] + cam['yaw']
            if self.yaw_steps:
                yaw = round(yaw * self.yaw_steps / 360) * 360 / self.yaw_steps
            spr, ax, ay, foot, fay = render_stack(o['V'], yaw, p['scale'] * cam['zoom'], p['gap'], squash,
                                                  sp.get('shade', 0.2), o['outline'], sp.get('pivot'))
            gx, gy = cx + rx, cy + ry * squash
            drawn.append((ry, spr, int(round(gx - ax)), int(round(gy - ay - p['z'] * cam['zoom'])), p['opacity'],
                          foot, int(round(gx - foot.shape[1] / 2)), int(round(gy - fay)), sp.get('shadow', 0.3)))
        for _, _, _, _, op, foot, fx, fy, sh in drawn:  # all shadows first, so no object is shadowed from below
            if sh:
                s = np.zeros(foot.shape + (4,), np.uint8)
                s[foot] = (0, 0, 0, int(255 * sh))
                blit(img, s, fx + 1, fy + 1, op)
        for _, spr, x, y, op, *_ in sorted(drawn, key=lambda d: d[0]):  # far to near
            blit(img, spr, x, y, op)
        return img

    def full(self, t, opaque=False):
        """One frame at output size. opaque=True flattens it onto black (for formats without alpha)."""
        key = self.env(t)['t']  # with anim_fps, several output frames share one drawing
        if getattr(self, '_last', (None,))[0] == key:
            return self._last[1]
        img = self.frame(t)
        if opaque:
            flat = np.zeros_like(img); flat[..., 3] = 255
            blit(flat, img, 0, 0); img = flat
        self._last = (key, np.repeat(np.repeat(img, self.ps, 0), self.ps, 1)[:self.H, :self.W])
        return self._last[1]


# ---------- commands ----------
def _ffmpeg(args, stdin=None):
    try:
        return subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y'] + args, stdin=stdin)
    except FileNotFoundError:
        raise SystemExit('ffmpeg is not installed. Render to a directory of PNGs or a .gif instead, or install ffmpeg.')


def cmd_model(a):
    V = load_model(a.model, slices=a.slices, top_first=a.top_first)
    h, d, w, _ = V.shape
    print(f'{a.model}: {w} wide x {d} deep x {h} slices, {int((V[..., 3] > 0).sum())} voxels')
    if a.output:
        to_sheet(V).save(a.output)
        print(f'wrote {a.output} (horizontal strip, bottom slice first; load it with "slices": {h})')


def cmd_turntable(a):
    V = bake_walls(load_model(a.model, slices=a.slices, top_first=a.top_first), a.wall)
    outline = rgba(a.outline) if a.outline else None
    sprs = [render_stack(V, 360 * k / a.frames, 1, a.gap, a.squash, a.shade, outline) for k in range(a.frames)]
    H = max(s[0].shape[0] for s in sprs) + 2
    W = max(s[0].shape[1] for s in sprs) + 2
    frames = []
    for spr, ax, ay, *_ in sprs:
        c = np.zeros((H, W, 4), np.uint8)
        c[:] = rgba(a.bg)
        blit(c, spr, int(W / 2 - ax), int(H - 1 - spr.shape[0]))
        frames.append(Image.fromarray(c).resize((W * a.scale, H * a.scale), Image.NEAREST))
    out = Path(a.output)
    if out.suffix.lower() == '.gif':
        frames[0].save(out, save_all=True, append_images=frames[1:], duration=int(1000 * a.seconds / a.frames), loop=0, disposal=2)
    else:  # one image with every direction side by side (also usable as a pre-rendered rotation sheet)
        cols = min(a.frames, 8)
        sheet = Image.new('RGBA', (cols * frames[0].width, math.ceil(a.frames / cols) * frames[0].height))
        for k, f in enumerate(frames):
            sheet.paste(f, ((k % cols) * f.width, (k // cols) * f.height))
        sheet.save(out)
    print(f'wrote {out} ({a.frames} directions, cell {frames[0].width}x{frames[0].height})')


def cmd_still(a):
    sc = Scene(a.scene)
    times = [float(x) for x in a.times.split(',')] if a.times else [sc.duration * (k + .5) / 6 for k in range(6)]
    shots = [Image.fromarray(sc.frame(t)).resize((sc.w * a.scale, sc.h * a.scale), Image.NEAREST) for t in times]
    cols = min(len(shots), 3)
    sheet = Image.new('RGBA', (cols * shots[0].width, math.ceil(len(shots) / cols) * shots[0].height), (40, 40, 40, 255))
    for k, s in enumerate(shots):
        sheet.paste(s, ((k % cols) * s.width, (k // cols) * s.height), s)
    sheet.save(a.output)
    print(f'wrote {a.output}: t = {", ".join(f"{t:g}s" for t in times)}')


def cmd_render(a):
    sc = Scene(a.scene)
    t0 = a.start or 0
    t1 = a.end if a.end is not None else sc.duration
    n = max(1, int(round((t1 - t0) * sc.fps)))
    out = Path(a.output)
    ext = out.suffix.lower()
    W, H = sc.W, sc.H
    proc = None
    if ext in ('.mp4', '.mov', '.webm'):
        src = ['-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', f'{sc.fps:g}', '-i', '-']
        audio = ['-i', a.audio, '-shortest'] if a.audio else []
        if ext == '.mp4':  # no alpha in H.264: a transparent scene lands on black
            if sc.bg in ('transparent', None):
                print('note: .mp4 has no transparency, so the background is black. Use .mov or a directory to keep it transparent.')
            enc = ['-vf', f'pad=ceil(iw/2)*2:ceil(ih/2)*2,format=yuv420p', '-c:v', 'libx264', '-crf', '16', '-preset', 'medium',
                   '-sws_flags', 'neighbor', '-movflags', '+faststart']
        elif ext == '.mov':
            enc = ['-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le']
        else:
            enc = ['-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-b:v', '0', '-crf', '24']
        proc = _ffmpeg(src + audio + enc + [str(out)], stdin=subprocess.PIPE)
    elif ext == '.gif':
        gif = []
    else:
        out.mkdir(parents=True, exist_ok=True)
    for k in range(n):
        t = t0 + k / sc.fps
        if proc:
            proc.stdin.write(sc.full(t, opaque=ext == '.mp4').tobytes())
        elif ext == '.gif':
            s = a.gif_scale or min(sc.ps, 2)
            gif.append(Image.fromarray(sc.frame(t)).resize((sc.w * s, sc.h * s), Image.NEAREST))
        else:
            Image.fromarray(sc.full(t)).save(out / f'stack_{k:05d}.png', compress_level=3)
        if k % max(1, n // 10) == 0:
            print(f'  frame {k + 1}/{n}', flush=True)
    if proc:
        proc.stdin.close()
        if proc.wait():
            raise SystemExit('ffmpeg failed')
    elif ext == '.gif':
        gif[0].save(out, save_all=True, append_images=gif[1:], duration=int(1000 / sc.fps), loop=0, disposal=2)
    if ext == '.gif':
        W, H = gif[0].size
    print(f'wrote {out}: {n} frames, {W}x{H} at {sc.fps:g} fps ({n / sc.fps:.2f}s)')


def _probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height:format=duration',
                        '-of', 'json', str(path)], capture_output=True, text=True)
    j = json.loads(r.stdout or '{}')
    st = (j.get('streams') or [{}])[0]
    return st.get('width'), st.get('height'), float(j.get('format', {}).get('duration', 0) or 0)


def cmd_composite(a):
    """Layers bottom to top. Each is a video, a still image, a directory of numbered PNGs, or ZIP:FOLDER
    (a folder inside a zip, e.g. jizura.zip:back)."""
    tmp = tempfile.TemporaryDirectory()
    inputs, durs, size = [], [], None
    for k, layer in enumerate(a.layers):
        m = re.match(r'(.+\.zip)(?::(.*))?$', layer, re.I)
        if m:
            dest = Path(tmp.name) / f'z{k}'
            with zipfile.ZipFile(m.group(1)) as z:
                names = [nm for nm in z.namelist() if nm.lower().endswith('.png') and (not m.group(2) or nm.startswith(m.group(2).strip('/') + '/'))]
                if not names:
                    raise SystemExit(f'{layer}: no PNG files found there. Folders in the zip: {sorted({nm.split("/")[0] for nm in z.namelist() if "/" in nm})}')
                for nm in names:  # flatten, and never trust a path stored in a zip
                    (dest / Path(nm).name).parent.mkdir(parents=True, exist_ok=True)
                    (dest / Path(nm).name).write_bytes(z.read(nm))
            layer = str(dest)
        p = Path(layer)
        if p.is_dir():
            files = sorted(f.name for f in p.iterdir() if f.suffix.lower() == '.png')
            mm = files and re.match(r'(.*?)(\d+)\.png$', files[0], re.I)
            if not mm:
                raise SystemExit(f'{layer}: expected numbered PNG files like name_00000.png')
            with Image.open(p / files[0]) as im:
                wh = im.size
            inputs.append(['-framerate', f'{a.fps:g}', '-start_number', str(int(mm.group(2))), '-i', str(p / f'{mm.group(1)}%0{len(mm.group(2))}d.png')])
            durs.append(len(files) / a.fps)
        elif p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp'):
            with Image.open(p) as im:
                wh = im.size
            inputs.append(['-loop', '1', '-framerate', f'{a.fps:g}', '-i', str(p)])
            durs.append(0)
        elif p.exists():
            w, h, dur = _probe(p)
            wh = (w, h)
            inputs.append(['-i', str(p)])
            durs.append(dur)
        else:
            raise SystemExit(f'layer not found: {layer}')
        size = size or wh
    if a.size:
        size = tuple(int(v) for v in a.size.lower().split('x'))
    W, H = size[0] // 2 * 2, size[1] // 2 * 2
    dur = a.duration or max(durs)
    if not dur:
        raise SystemExit('give --duration: none of the layers has a length')
    args = ['-f', 'lavfi', '-i', f'color=c={a.bg.replace("#", "0x")}:s={W}x{H}:r={a.fps:g}']
    for i in inputs:
        args += i
    chain, last = [], '0:v'
    for k in range(len(inputs)):  # nearest-neighbour scaling keeps pixel art crisp when sizes differ
        chain.append(f'[{k + 1}:v]fps={a.fps:g},scale={W}:{H}:flags=neighbor,format=rgba[l{k}]')
        chain.append(f'[{last}][l{k}]overlay=eof_action=pass:format=auto[o{k}]')
        last = f'o{k}'
    if a.audio:
        args += ['-i', a.audio]
    args += ['-filter_complex', ';'.join(chain), '-map', f'[{last}]']
    if a.audio:
        args += ['-map', f'{len(inputs) + 1}:a', '-c:a', 'aac', '-b:a', '256k']
    args += ['-t', f'{dur:.3f}', '-r', f'{a.fps:g}', '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', a.output]
    if _ffmpeg(args).wait():
        raise SystemExit('ffmpeg failed')
    print(f'wrote {a.output}: {W}x{H}, {dur:.2f}s at {a.fps:g} fps, {len(inputs)} layers' + (' + audio' if a.audio else ''))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    def model_args(p):
        p.add_argument('model', help='.json model, MagicaVoxel .vox, or .png slice sheet')
        p.add_argument('--slices', type=int, help='number of slices in a .png sheet (default: square cells)')
        p.add_argument('--top-first', action='store_true', help='the sheet starts with the top slice')
    p = sub.add_parser('model', help='report a model and convert it to a slice sheet'); model_args(p)
    p.add_argument('-o', '--output'); p.set_defaults(fn=cmd_model)
    p = sub.add_parser('turntable', help='spin a model: .gif, or .png sheet of every direction'); model_args(p)
    p.add_argument('-o', '--output', required=True); p.add_argument('--frames', type=int, default=24)
    p.add_argument('--seconds', type=float, default=2.4); p.add_argument('--scale', type=int, default=6)
    p.add_argument('--gap', type=float, default=1); p.add_argument('--squash', type=float, default=1)
    p.add_argument('--shade', type=float, default=0.2); p.add_argument('--wall', type=float, default=0.18); p.add_argument('--outline'); p.add_argument('--bg', default='#00000000')
    p.set_defaults(fn=cmd_turntable)
    p = sub.add_parser('still', help='contact sheet of a scene at chosen times'); p.add_argument('scene')
    p.add_argument('-t', '--times', help='seconds, comma separated (default: six moments across the scene)')
    p.add_argument('-o', '--output', required=True); p.add_argument('--scale', type=int, default=2); p.set_defaults(fn=cmd_still)
    p = sub.add_parser('render', help='render a scene'); p.add_argument('scene')
    p.add_argument('-o', '--output', required=True, help='.mp4, .mov (ProRes 4444 with alpha), .webm (alpha), .gif, or a directory for PNGs')
    p.add_argument('--start', type=float); p.add_argument('--end', type=float); p.add_argument('--audio'); p.add_argument('--gif-scale', type=int)
    p.set_defaults(fn=cmd_render)
    p = sub.add_parser('composite', help='layer videos / PNG sequences bottom to top and add audio', description=cmd_composite.__doc__)
    p.add_argument('layers', nargs='+'); p.add_argument('-o', '--output', required=True)
    p.add_argument('--fps', type=float, default=24); p.add_argument('--bg', default='#000000'); p.add_argument('--audio')
    p.add_argument('--size', help='WxH (default: size of the first layer)'); p.add_argument('--duration', type=float)
    p.set_defaults(fn=cmd_composite)
    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()

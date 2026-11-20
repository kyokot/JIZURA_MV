#!/usr/bin/env python3
"""Builds the sprite-stack slice sheets the site draws (public/stacks/*.png + src/stacks.json).

The characters are Drum Legion's own 16x16 unit sprites (copied from the game's src/game/sprites.ts) puffed up
into figurines: thick in the middle, thin at the rim, the sprite on the front. Props are built from simple solids.
Uses the renderer from the sprite-stack-mv skill in this repository.

    python3 tools/build_models.py            # write the sheets
    python3 tools/build_models.py --preview out.png   # also write a contact sheet to look at
"""
import json, sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent / '.claude/skills/sprite-stack-mv/scripts'))
import spritestack as ss  # noqa: E402

OUTLINE = '#17111f'
BASE = dict(S='#f7c9a0', K='#1b1b2a', L='#4a4458', T='#7a4a2a', B='#8a5a2c', P='#9a6a3a', I='#dfe6f2', G='#ffcf3a',
            J='#ffd84a', Y='#ffcf3a', R='#e0383f', W='#f4f1ea', A='#8a5a2c', V='#2a2c3c', N='#ff5a5a')
HEADS = {
    'pawn0': ['................', '.....HHHHHH.....', '....HHHHHHHH....', '...HHHHHHHHHH...', '...HHHHHHHHHH...', '...HSSSSSSSSH...', '...SSKSSSSKSS...', '...SSKSSSSKSS...', '....SSSSSSSS....'],
    'knight': ['..RR............', '.RRRHHHHHHH.....', '.RR.HHHHHHHH....', '.R.HHHHHHHHHH...', '...HHHHHHHHHH...', '...HHHHHHHHHH...', '...HKKKHHKKKH...', '...HHHHHHHHHH...', '....HHHVVHHH....'],
    'king0': ['................', '...Y...YY...Y...', '...YYYYYYYYYY...', '...YRYYJJYYRY...', '...AAAAAAAAAA...', '...ASSSSSSSSA...', '...SSKSSSSKSS...', '...SSKSSSSKSS...', '....SSSSSSSS....'],
}
BODIES = {
    'tunic': ['....CCCCCCCC....', '...CCCCCCCCCC...', '..SCCBBBBBBCCS..', '...CCCCCCCCCC...', '....CCCCCCCC....', '....LLL..LLL....', '...TTTT..TTTT...'],
    'armor': ['....CCCCCCCC....', '.DDDCCCCCCCCC...', 'DDDDDCJJCCCCCS..', 'DDDDDCJJCCCCC...', '.DDDCCCCCCCC....', '....LLL..LLL....', '...TTTT..TTTT...'],
    'robe': ['...WWWWWWWWWW...', '..RCCCCJJCCCCS..', '.RRCCCCJJCCCC...', '.RRCCCCCCCCCC...', '.RRCCCCCCCCCC...', '..RWWWWWWWWWW...', '....TTT..TTT....'],
}
WEAPONS = {
    'blade': ['', '', '', '', '', '', '..............I.', '..............I.', '..............I.', '..............I.', '.............GGG', '..............P.', '', '', '', ''],
    'spear': ['', '..............I.', '.............III', '..............I.', '..............P.', '..............P.', '..............P.', '..............P.', '..............P.', '..............P.', '..............P.', '..............P.', '..............P.', '..............P.', '', ''],
}
UNITS = {
    'pawn': ('pawn0', 'tunic', 'blade', dict(H='#9fb0c4', C='#3fae5e')),
    'knight': ('knight', 'armor', 'spear', dict(H='#b9c6d6', C='#2f86d4', D='#e8b23a', R='#ff5a5a')),
    'king': ('king0', 'robe', 'blade', dict(C='#3866e8', R='#3866e8', W='#f4f1ea')),
}
FULL = {  # enemies: rows, palette, and which cells are the thin weapon (chars, from column)
    'grunt': (['................', '..N........N....', '..NN......NN....', '...PPPPPPPPPP...', '..PPPPPPPPPPPP..', '..PPEEPPPPEEPP..', '...PPEPPPPEPP...', '...PPPFPPFPPP...', '....PPPPPPPP....', '....MMMMMMMM..G.', '...MMMMMMMMMM.G.', '..PMMBBBBBBMMPGG', '...MMMMMMMMMM.GG', '....MMMMMMMM..G.', '....PPP..PPP....', '...PPPP..PPPP...'],
              dict(N='#eadfc8', P='#a866dc', E='#ff3b3b', F='#ffffff', M='#5f3a8a', B='#2e2038', G='#8f8a80'), ('G', 14)),
    'brute': (['................', '....OOOOOOOO....', '...OOOOOOOOOO...', '..OOOOOOOOOOOO..', '..OOEKOOOOEKOO..', '..OOOOOOOOOOOO..', '..OOFOFFFFOFOO..', '.OOOOOOOOOOOOOO.', 'OOOOUUUUUUUUOOOO', 'OOOOUUUUUUUUOOOO', 'OOO.UUUUUUUU.OOO', 'OOO.BBBBBBBB.OOO', '.O..OOOOOOOO..O.', '....OOO..OOO....', '...OOOO..OOOO...', '...TTTT..TTTT...'],
              dict(O='#e07b2c', E='#fff06a', K='#1b1b2a', F='#ffffff', U='#f2b06a', B='#5a3018', T='#3a2418'), ('', 99)),
    'guard': (['................', '.....AAAAAA...I.', '....AAAAAAAA.II.', '...AAAAAAAAAAII.', '...AAAAAAAAAA.P.', '...AKKEAAEKKA.P.', '...AAAAAAAAAA.P.', '....AAAAAAAA..P.', '....CCCCCCCC..P.', '.XXXCCCCCCCCC.P.', 'XXXXXCCCCCCCCSP.', 'XXRXXCCCCCCCC.P.', 'XXXXXCCCCCCCC.P.', '.XXXCCCCCCCC..P.', '....AAA..AAA....', '...AAAA..AAAA...'],
              dict(A='#5a6078', C='#414660', E='#ff3b3b', K='#0f0f18', X='#aab0c8', R='#c0303a', I='#dfe6f2', P='#7a5a3a', S='#5a6078'), ('IP', 13)),
    'archer': (['................', '.....DDDDDD.....', '....DDDDDDDD....', '...DDDDDDDDDD...', '...DDPPPPPPDD...', '...DPEEPPEEPD.W.', '...DPPEPPEPPDW.I', '....PPPFFPPP.W.I', '.....PPPPPP..W.I', '....MMMMMMMM.W.I', '...MMMMMMMMMMW.I', '..PMMBBBBBBMMPW.', '...MMMMMMMMMM.W.', '....MMMMMMMM....', '....PPP..PPP....', '...PPPP..PPPP...'],
               dict(D='#2f6b4a', P='#a866dc', E='#ff3b3b', F='#ffffff', M='#3d5a40', B='#2e2038', W='#b07a3c', I='#e8e8f0'), ('WI', 13)),
    'drummer': (['................', '..N........N....', '..NN......NN....', '...PPPPPPPPPP...', '..PRRRRRRRRRRP..', '..PPEEPPPPEEPP..', '...PPEPPPPEPP...', '.I.PPPFPPFPPP.I.', '.I..PPPPPPPP..I.', '.II.YYYYYYYY.II.', '..IYYYYYYYYYYI..', '...UUWUUUUWUU...', '...UUUWUUWUUU...', '...UUWUUUUWUU...', '....UUUUUUUU....', '....PP....PP....'],
                dict(N='#eadfc8', P='#a866dc', R='#e0383f', E='#ffe14a', F='#ffffff', I='#eadfc8', Y='#f2e2b0', U='#c0392b', W='#f2e2b0'), ('', 99)),
}
INLAY = set('KEF')  # eyes and fangs: drawn on the front only


def figurine(rows, pal, thin=lambda x, y, ch: False, depth=5):
    """A 16x16 sprite -> a rounded figurine: thick in the middle, one voxel thick at the rim and for weapons."""
    h, w = len(rows), 16
    grid = [list(r.ljust(w, '.')) for r in rows]
    body = np.array([[c != '.' and not thin(x, y, c) for x, c in enumerate(r)] for y, r in enumerate(grid)])
    weapon = np.array([[c != '.' and thin(x, y, c) for x, c in enumerate(r)] for y, r in enumerate(grid)])
    dist = np.zeros((h, w), int)
    m = body.copy()
    while m.any():  # how far each cell is from the edge of the silhouette
        dist += m
        p = np.pad(m, 1)
        m = m & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    V = np.zeros((h, depth, w, 4), np.uint8)
    mid = depth // 2
    for y in range(h):
        for x in range(w):
            ch = grid[y][x]
            if ch == '.':
                continue
            z = h - 1 - y
            if weapon[y, x]:
                V[z, mid, x] = ss.rgba(pal[ch])
                continue
            half = min(mid, dist[y, x])
            back = ch
            if ch in INLAY:  # behind the face, use the colour beside it
                back = next((c for c in grid[y][x::-1] if c != '.' and c not in INLAY), ch)
            for k in range(mid - half, mid + half + 1):
                V[z, k, x] = ss.rgba(pal[ch if k == mid + half else back])
    return V


def unit(name):
    head, body, weapon, pal = UNITS[name]
    rows = [list(r) for r in HEADS[head] + BODIES[body]]
    arm = set()
    for y, r in enumerate(WEAPONS[weapon]):
        for x, c in enumerate(r):
            if c != '.':
                rows[y][x] = c
                arm.add((x, y))
    return figurine([''.join(r) for r in rows], {**BASE, **pal}, lambda x, y, c: (x, y) in arm)


def enemy(name):
    rows, pal, (chars, x0) = FULL[name]
    return figurine(rows, {**BASE, **pal}, lambda x, y, c: c in chars and x >= x0)


def solid(spec):
    return ss.model_from_spec(spec, ROOT)


def castle():
    stone, dark, lite, roof, roof2, gold = '#8f93ab', '#5c6078', '#b9bdd2', '#c8323c', '#8e1f2c', '#ffcf3a'
    p = [dict(type='box', **{'from': [4, 4, 0], 'to': [44, 44, 14]}, color=dark, color_top=stone)]
    p.append(dict(type='box', **{'from': [7, 7, 6], 'to': [41, 41, 14]}, erase=True))  # the yard
    for k in range(4, 44, 4):  # battlements
        for a, b in (([k, 4], [k + 2, 6]), ([k, 42], [k + 2, 44]), ([4, k], [6, k + 2]), ([42, k], [44, k + 2])):
            p.append(dict(type='box', **{'from': a + [14], 'to': b + [16]}, color=lite))
    for cx, cy in ((6, 6), (42, 6), (6, 42), (42, 42)):  # corner towers
        p.append(dict(type='cylinder', center=[cx, cy], radius=5.5, z=[0, 22], color=dark, color_top=lite))
        p.append(dict(type='cylinder', center=[cx, cy], radius=6.5, radius_top=0.6, z=[22, 31], color=roof2, color_top=roof))
    p.append(dict(type='box', **{'from': [15, 15, 0], 'to': [33, 33, 28]}, color=dark, color_top=lite))  # keep
    for k in range(15, 33, 4):
        for a, b in (([k, 15], [k + 2, 17]), ([k, 31], [k + 2, 33]), ([15, k], [17, k + 2]), ([31, k], [33, k + 2])):
            p.append(dict(type='box', **{'from': a + [28], 'to': b + [30]}, color=lite))
    for i in range(7):  # stepped roof
        p.append(dict(type='box', **{'from': [17 + i, 17 + i, 28 + i], 'to': [31 - i, 31 - i, 29 + i]}, color=roof if i % 2 else roof2))
    p.append(dict(type='box', **{'from': [23, 23, 35], 'to': [25, 25, 42]}, color='#4a4458'))  # flag pole
    p.append(dict(type='box', **{'from': [25, 23, 38], 'to': [31, 24, 42]}, color=roof))
    p.append(dict(type='box', **{'from': [20, 42, 0], 'to': [28, 44, 9]}, color='#2a1c1c'))  # gate
    p.append(dict(type='box', **{'from': [21, 43, 0], 'to': [27, 44, 8]}, color='#6a4a2a'))
    for x in (19, 27):  # lit windows on the keep, front and back
        p.append(dict(type='box', **{'from': [x, 32, 16], 'to': [x + 2, 33, 21]}, color=gold))
        p.append(dict(type='box', **{'from': [x, 15, 16], 'to': [x + 2, 16, 21]}, color=gold))
    for y in (19, 27):
        p.append(dict(type='box', **{'from': [32, y, 16], 'to': [33, y + 2, 21]}, color=gold))
        p.append(dict(type='box', **{'from': [15, y, 16], 'to': [16, y + 2, 21]}, color=gold))
    return solid(dict(size=[48, 48, 42], parts=p))


def drum():
    red, dk, skin, gold, wood = '#c0392b', '#7d2219', '#f2e2b0', '#ffcf3a', '#7a4a2a'
    p = []
    for cx, cy in ((4, 4), (16, 4), (4, 16), (16, 16)):
        p.append(dict(type='box', **{'from': [cx - 1, cy - 1, 0], 'to': [cx + 1, cy + 1, 5]}, color=wood))
    p.append(dict(type='box', **{'from': [3, 3, 3], 'to': [17, 17, 5]}, color=wood))
    p.append(dict(type='lathe', center=[10, 10], z0=5, radii=[8, 8.6, 9.2, 9.6, 9.8, 9.8, 9.6, 9.2, 8.6, 8],
                  colors=[gold, dk, red, red, red, red, red, red, dk, gold]))
    p.append(dict(type='cylinder', center=[10, 10], radius=7.2, z=[15, 16], color=skin))
    p.append(dict(type='cylinder', center=[10, 10], radius=2.2, z=[15, 16], color='#e3cf96'))
    return solid(dict(size=[20, 20, 16], parts=p))


def tree():
    g = ['#1f6b3a', '#2a8a4a', '#35a257', '#49b868']
    p = [dict(type='cylinder', center=[9, 9], radius=2, z=[0, 6], color='#5a3a22', color_top='#7a4a2a')]
    radii = [6, 8, 8.5, 8, 7, 7.5, 7, 6, 5, 5.5, 4.5, 3.5, 2.5, 1.5]
    p.append(dict(type='lathe', center=[9, 9], z0=5, radii=radii, colors=[g[min(3, i // 4 + (i % 2))] for i in range(len(radii))]))
    return solid(dict(size=[18, 18, 19], parts=p))


def rock():
    return solid(dict(size=[14, 12, 8], parts=[
        dict(type='ellipsoid', center=[6, 6, 2], radii=[6, 5.5, 6], color='#5f6378', color_top='#9a9eb4'),
        dict(type='ellipsoid', center=[10, 7, 1], radii=[4, 4, 4], color='#565a70', color_top='#868aa0')]))


def flag():
    p = [dict(type='cylinder', center=[3, 3], radius=2.4, z=[0, 2], color='#4a4458'),
         dict(type='box', **{'from': [2, 2, 2], 'to': [4, 4, 26]}, color='#b9bdd2'),
         dict(type='box', **{'from': [4, 3, 15], 'to': [15, 4, 25]}, color='#e0383f'),
         dict(type='box', **{'from': [4, 3, 19], 'to': [15, 4, 21]}, color='#ffcf3a'),
         dict(type='sphere', center=[3, 3, 27], radius=1.6, color='#ffcf3a')]
    return solid(dict(size=[16, 6, 29], parts=p))


def torch():
    p = [dict(type='box', **{'from': [2, 2, 0], 'to': [4, 4, 9]}, color='#5a3a22'),
         dict(type='cylinder', center=[3, 3], radius=2.6, z=[9, 11], color='#4a4458'),
         dict(type='lathe', center=[3, 3], z0=11, radii=[2.6, 2.9, 2.4, 1.9, 1.3, 0.8],
              colors=['#ff7a3c', '#ffa23c', '#ffcf3a', '#ffe98a', '#fff6c8', '#ffffff'])]
    return solid(dict(size=[6, 6, 17], parts=p))


MODELS = dict(king=lambda: unit('king'), pawn=lambda: unit('pawn'), knight=lambda: unit('knight'),
              grunt=lambda: enemy('grunt'), brute=lambda: enemy('brute'), guard=lambda: enemy('guard'),
              archer=lambda: enemy('archer'), drummer=lambda: enemy('drummer'),
              castle=castle, drum=drum, tree=tree, rock=rock, flag=flag, torch=torch)


def finish(V, wall=0.2, shade=0.22):
    """Bake the lighting in (dark walls, darker toward the ground) and pad each slice by 1 px, so the browser only
    has to draw the slices, and the edge of a rotated slice is always transparent (no half-covered pixels)."""
    V = ss.bake_walls(V, wall)
    f = 1 - shade * (1 - np.arange(len(V)) / max(1, len(V) - 1))
    V = V.copy()
    V[..., :3] = (V[..., :3] * f[:, None, None, None]).astype(np.uint8)
    return np.pad(V, ((0, 0), (1, 1), (1, 1), (0, 0)))


def main():
    out = ROOT / 'public/stacks'
    out.mkdir(parents=True, exist_ok=True)
    manifest, built = {}, {}
    for name, make in MODELS.items():
        V = built[name] = finish(make())
        n, d, w, _ = V.shape
        ss.to_sheet(V).save(out / f'{name}.png', optimize=True)
        manifest[name] = dict(w=w, h=d, n=n)
        print(f'{name}: {n} slices of {w} x {d}')
    (ROOT / 'src/stacks.json').write_text(json.dumps(manifest, indent=1) + '\n')
    if '--preview' in sys.argv:
        cells = []
        for name, V in built.items():
            row = [ss.render_stack(V, a, 1, 1, 0.7, 0, ss.rgba(OUTLINE))[0] for a in (0, 45, 90, 180, 225)]
            hh, ww = max(r.shape[0] for r in row), sum(r.shape[1] for r in row)
            c = np.zeros((hh, ww, 4), np.uint8); c[:] = (48, 52, 70, 255)
            x = 0
            for r in row:
                ss.blit(c, r, x, hh - r.shape[0]); x += r.shape[1]
            cells.append(c)
        W = max(c.shape[1] for c in cells)
        sheet = np.concatenate([np.pad(c, ((0, 0), (0, W - c.shape[1]), (0, 0)), constant_values=40) for c in cells])
        Image.fromarray(sheet).resize((sheet.shape[1] * 3, sheet.shape[0] * 3), Image.NEAREST).save(sys.argv[sys.argv.index('--preview') + 1])


if __name__ == '__main__':
    main()

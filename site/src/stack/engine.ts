// Sprite stacking in a 2D canvas: every model is one row of slices (ground slice on the left). A slice is turned,
// flattened for the camera, then lifted one step per layer, exactly as the sheets were checked offline.
import manifest from '../stacks.json';

export type ModelName = keyof typeof manifest;
export interface Model { img: HTMLImageElement; sil: HTMLCanvasElement; w: number; h: number; n: number }
export type Models = Record<ModelName, Model>;

export const OUTLINE = '#17111f';

export interface Camera {
  /** radians: the whole world turns */
  yaw: number;
  /** 1 looks straight down; lower is a lower camera */
  squash: number;
  zoom: number;
  /** where world (0, 0) sits on the canvas, in canvas px */
  cx: number;
  cy: number;
}

export interface Obj {
  m: ModelName;
  x: number;
  y: number;
  z?: number;
  /** radians */
  yaw?: number;
  scale?: number;
  /** px between slices at scale 1 */
  gap?: number;
  /** overrides the camera's squash (figurines read best lower than buildings) */
  squash?: number;
  alpha?: number;
  /** keep its front to the viewer whatever the camera does */
  face?: boolean;
  outline?: boolean;
  shadow?: number;
}

let cache: Promise<Models> | null = null;

export function loadModels(): Promise<Models> {
  cache ??= Promise.all(
    (Object.keys(manifest) as ModelName[]).map(
      (name) =>
        new Promise<[ModelName, Model]>((resolve, reject) => {
          const img = new Image();
          img.onload = () => {
            // a one-colour copy of the sheet: drawn 1 px off in four directions, it outlines the finished stack
            const sil = document.createElement('canvas');
            sil.width = img.width;
            sil.height = img.height;
            const c = sil.getContext('2d')!;
            c.drawImage(img, 0, 0);
            c.globalCompositeOperation = 'source-in';
            c.fillStyle = OUTLINE;
            c.fillRect(0, 0, sil.width, sil.height);
            resolve([name, { img, sil, ...manifest[name] }]);
          };
          img.onerror = () => reject(new Error(`could not load stacks/${name}.png`));
          img.src = `${import.meta.env.BASE_URL.replace(/\/$/, '')}/stacks/${name}.png`; // BASE_URL may or may not end in a slash
        }),
    ),
  ).then((list) => Object.fromEntries(list) as Models);
  return cache;
}

function slices(ctx: CanvasRenderingContext2D, src: CanvasImageSource, m: Model, a: number, b: number, c: number, d: number, x: number, y: number, g: number) {
  const fill = Math.max(1, Math.ceil(g)); // repeat a slice so a gap above 1 px leaves no holes
  for (let i = 0; i < m.n; i++) {
    const lift = Math.round(i * g);
    const reps = i < m.n - 1 ? fill : 1;
    for (let k = 0; k < reps; k++) {
      ctx.setTransform(a, b, c, d, x, y - lift - k);
      ctx.drawImage(src, i * m.w, 0, m.w, m.h, -m.w / 2, -m.h / 2, m.w, m.h);
    }
  }
}

const OFFSETS = [[1, 0], [-1, 0], [0, 1], [0, -1]] as const;

/** Draws objects far to near. The canvas should be small and scaled up with image-rendering: pixelated. */
export function drawScene(ctx: CanvasRenderingContext2D, models: Models, objs: Obj[], cam: Camera) {
  ctx.imageSmoothingEnabled = false;
  const cs = Math.cos(cam.yaw);
  const sn = Math.sin(cam.yaw);
  const placed = objs
    .filter((o) => (o.alpha ?? 1) > 0.01 && (o.scale ?? 1) > 0.01)
    .map((o) => {
      const rx = (cs * o.x - sn * o.y) * cam.zoom;
      const ry = (sn * o.x + cs * o.y) * cam.zoom;
      return { o, ry, sx: Math.round(cam.cx + rx), sy: Math.round(cam.cy + ry * cam.squash) };
    })
    .sort((p, q) => p.ry - q.ry);

  for (const { o, sx, sy } of placed) {
    const m = models[o.m];
    const sh = o.shadow ?? 0.32;
    if (!sh) continue;
    const s = (o.scale ?? 1) * cam.zoom;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalAlpha = sh * (o.alpha ?? 1);
    ctx.fillStyle = '#05030a';
    ctx.beginPath();
    ctx.ellipse(sx, sy + 1, Math.max(m.w, m.h) * 0.42 * s, Math.max(m.w, m.h) * 0.42 * s * cam.squash, 0, 0, Math.PI * 2);
    ctx.fill();
  }

  for (const { o, sx, sy } of placed) {
    const m = models[o.m];
    const s = (o.scale ?? 1) * cam.zoom;
    const q = o.squash ?? cam.squash;
    const yaw = (o.yaw ?? 0) + (o.face ? 0 : cam.yaw);
    const a = s * Math.cos(yaw);
    const b = s * Math.sin(yaw) * q;
    const c = -s * Math.sin(yaw);
    const d = s * Math.cos(yaw) * q;
    const g = (o.gap ?? 1) * s;
    const y = sy - Math.round((o.z ?? 0) * cam.zoom);
    ctx.globalAlpha = o.alpha ?? 1;
    if (o.outline !== false) for (const [dx, dy] of OFFSETS) slices(ctx, m.sil, m, a, b, c, d, sx + dx, y + dy, g);
    slices(ctx, m.img, m, a, b, c, d, sx, y, g);
  }
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = 1;
}

/** A checkered ground that turns with the camera. */
export function drawGround(ctx: CanvasRenderingContext2D, cam: Camera, radius: number, tile: number, a: string, b: string) {
  const cs = Math.cos(cam.yaw) * cam.zoom;
  const sn = Math.sin(cam.yaw) * cam.zoom;
  ctx.setTransform(cs, sn * cam.squash, -sn, cs * cam.squash, cam.cx, cam.cy);
  const n = Math.ceil(radius / tile);
  for (let j = -n; j < n; j++) {
    for (let i = -n; i < n; i++) {
      const cx = (i + 0.5) * tile;
      const cy = (j + 0.5) * tile;
      if (cx * cx + cy * cy > radius * radius) continue;
      ctx.fillStyle = (i + j) & 1 ? a : b;
      ctx.fillRect(i * tile, j * tile, tile + 0.5, tile + 0.5);
    }
  }
  ctx.setTransform(1, 0, 0, 1, 0, 0);
}

import { useEffect, useRef } from 'react';
import { useReducedMotion } from 'motion/react';
import { loadModels, type Models } from './engine';
import { cn } from '../lib/cn';

export interface Frame {
  ctx: CanvasRenderingContext2D;
  models: Models;
  /** canvas size in its own (small) pixels */
  w: number;
  h: number;
  /** seconds since the canvas first drew */
  t: number;
}

interface Props {
  /** called once per animation frame while the canvas is on screen */
  draw: (f: Frame) => void;
  /** how many screen px one canvas px covers; a function gets the element's size */
  pixel?: number | ((width: number, height: number) => number);
  className?: string;
  label: string;
}

/** A low-resolution canvas scaled up without smoothing. It only animates while visible, and honours
 *  prefers-reduced-motion by drawing far less often. */
export function StackCanvas({ draw, pixel = 4, className, label }: Props) {
  const ref = useRef<HTMLCanvasElement>(null);
  const drawRef = useRef(draw);
  drawRef.current = draw;
  const reduce = useReducedMotion();

  useEffect(() => {
    const canvas = ref.current!;
    const ctx = canvas.getContext('2d')!;
    let models: Models | null = null;
    let raf = 0;
    let visible = false;
    let last = -1;
    const t0 = performance.now();

    const fit = () => {
      const r = canvas.getBoundingClientRect();
      const ps = Math.max(1, typeof pixel === 'function' ? pixel(r.width, r.height) : pixel);
      const w = Math.max(1, Math.round(r.width / ps));
      const h = Math.max(1, Math.round(r.height / ps));
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }
    };
    const tick = (now: number) => {
      raf = 0;
      if (!visible || !models) return;
      if (!reduce || now - last > 500) {
        last = now;
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        drawRef.current({ ctx, models, w: canvas.width, h: canvas.height, t: (now - t0) / 1000 });
      }
      raf = requestAnimationFrame(tick);
    };
    const start = () => {
      if (!raf && visible && models) raf = requestAnimationFrame(tick);
    };
    const io = new IntersectionObserver(([e]) => {
      visible = e.isIntersecting;
      start();
    }, { rootMargin: '100px' });
    io.observe(canvas);
    const ro = new ResizeObserver(fit);
    ro.observe(canvas);
    fit();
    let dead = false;
    loadModels().then((m) => {
      if (dead) return;
      models = m;
      start();
    });
    return () => {
      dead = true;
      io.disconnect();
      ro.disconnect();
      cancelAnimationFrame(raf);
    };
  }, [pixel, reduce]);

  return <canvas ref={ref} role="img" aria-label={label} className={cn('block [image-rendering:pixelated]', className)} />;
}

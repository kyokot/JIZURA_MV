import { useMemo, useRef } from 'react';
import { motion, useMotionValue, useScroll, useSpring, useTransform, useAnimationFrame } from 'motion/react';
import { ChevronDown, Play, Volume2, VolumeX } from 'lucide-react';
import { StackCanvas, type Frame } from '../stack/StackCanvas';
import { drawGround, drawScene, type Obj } from '../stack/engine';
import { beatNow, hop, pulse, setSound, useSound } from '../lib/beat';
import { FIG, GAME_URL } from '../lib/site';
import { PixelButton } from '../components/ui';

const TITLE = [...'ドラムレギオン'];

/** the battlefield: the army (near, facing the castle) and the lord's men (far, facing the army) */
function world(): { o: Obj; phase: number; kind: 'army' | 'foe' | 'prop' | 'drum' | 'fire' }[] {
  const out: ReturnType<typeof world> = [];
  const fig = (m: Obj['m'], x: number, y: number, army: boolean, phase = 0) =>
    out.push({ o: { m, x, y, yaw: army ? Math.PI : 0, ...FIG }, phase, kind: army ? 'army' : 'foe' });
  const prop = (m: Obj['m'], x: number, y: number, yaw = 0, kind: 'prop' | 'drum' | 'fire' = 'prop') => out.push({ o: { m, x, y, yaw }, phase: 0, kind });
  prop('castle', 0, -84);
  for (let i = 0; i < 15; i++) {
    const a = (i / 15) * Math.PI * 2 + 0.2;
    const r = 132 + ((i * 37) % 17);
    if (Math.abs(Math.sin(a)) > 0.93 && Math.cos(a) * 0 + Math.sin(a) > 0) continue; // leave the near side open
    prop(i % 4 === 3 ? 'rock' : 'tree', Math.cos(a) * r, Math.sin(a) * r, i);
  }
  prop('torch', -30, -46, 0, 'fire');
  prop('torch', 30, -46, 0, 'fire');
  prop('flag', -64, 34, 0.3);
  prop('flag', 64, 34, -0.3);
  prop('drum', -27, 52, 0, 'drum');
  fig('king', 0, 44, true);
  fig('knight', -54, 54, true, 0.5);
  fig('knight', 54, 54, true, 0.5);
  for (const [x, y] of [[-18, 70], [18, 70], [-36, 82], [0, 86], [36, 82], [-18, 100], [18, 100]]) fig('pawn', x, y, true);
  fig('brute', 0, -40, false, 0.5);
  for (const x of [-26, 0, 26]) fig('grunt', x, -14 - Math.abs(x) * 0.3, false, 0.5);
  fig('archer', -48, -34, false, 0.5);
  fig('archer', 48, -34, false, 0.5);
  fig('guard', 66, -8, false, 0.5);
  fig('drummer', -66, -8, false, 0.5);
  return out;
}

export function Hero() {
  const ref = useRef<HTMLElement>(null);
  const things = useMemo(world, []);
  const sound = useSound();
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end start'] });
  const drag = useMotionValue(0);
  const look = useMotionValue(0);
  const yaw = useSpring(useTransform([drag, look, scrollYProgress], ([d, l, s]: number[]) => 0.55 + d + l * 0.3 + s * 2.2), { stiffness: 60, damping: 16 });
  const fade = useTransform(scrollYProgress, [0, 0.7], [1, 0]);
  const lift = useTransform(scrollYProgress, [0, 1], [0, -90]);
  const beat = useMotionValue(1);
  useAnimationFrame(() => beat.set(1 + 0.035 * pulse(beatNow(), 6)));
  const dragging = useRef<number | null>(null);

  const draw = ({ ctx, models, w, h, t }: Frame) => {
    const b = beatNow();
    const cam = { yaw: yaw.get() + Math.sin(t * 0.25) * 0.06, squash: 0.68, zoom: 1, cx: w / 2, cy: h * 0.66 };
    drawGround(ctx, cam, 168, 16, '#241c3a', '#2b2246');
    const objs = things.map(({ o, phase, kind }) => {
      if (kind === 'army' || kind === 'foe') return { ...o, z: 2.6 * hop(b + phase) };
      if (kind === 'drum') return { ...o, gap: 1 + 0.45 * pulse(b, 5), yaw: (o.yaw ?? 0) + b * 0.2 };
      if (kind === 'fire') return { ...o, gap: 1 + 0.25 * pulse(b * 2, 3) };
      return o;
    });
    drawScene(ctx, models, objs, cam);
  };

  return (
    <header ref={ref} className="relative h-[100svh] min-h-[620px] overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_55%,#2a1f4a_0%,#120e1a_70%)]" />
      <StackCanvas
        draw={draw}
        pixel={(w, h) => Math.max(2, Math.min(6, Math.floor(Math.min(w / 330, h / 300))))}
        label="回転する戦場。手前に王と兵、奥に城と敵が並び、拍に合わせて跳ねている"
        className="absolute inset-0 size-full cursor-grab touch-pan-y active:cursor-grabbing"
      />
      {/* dragging turns the battlefield; the layer sits above the canvas and below the text */}
      <div
        className="absolute inset-0 cursor-grab touch-pan-y active:cursor-grabbing"
        onPointerDown={(e) => {
          dragging.current = e.clientX;
          e.currentTarget.setPointerCapture(e.pointerId);
        }}
        onPointerMove={(e) => {
          look.set(e.clientX / window.innerWidth - 0.5);
          if (dragging.current === null) return;
          drag.set(drag.get() + (e.clientX - dragging.current) * 0.008);
          dragging.current = e.clientX;
        }}
        onPointerUp={() => (dragging.current = null)}
        onPointerCancel={() => (dragging.current = null)}
      />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[46svh] bg-gradient-to-b from-night via-night/70 to-transparent" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-night to-transparent" />

      <motion.div style={{ opacity: fade, y: lift }} className="pointer-events-none relative z-10 mx-auto flex h-full max-w-6xl flex-col items-center px-5 pt-[7svh] text-center">
        <motion.p initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="font-pixel text-sm tracking-[0.35em] text-gold sm:text-base">
          リズム進軍アクション
        </motion.p>
        <motion.h1 style={{ scale: beat }} className="mt-3 flex font-pixel text-[13vw] leading-none sm:text-7xl lg:text-8xl" aria-label="ドラムレギオン">
          {TITLE.map((ch, i) => (
            <motion.span
              key={i}
              aria-hidden
              initial={{ y: -80, opacity: 0, rotate: -12 }}
              animate={{ y: 0, opacity: 1, rotate: 0 }}
              transition={{ type: 'spring', stiffness: 380, damping: 14, delay: 0.25 + i * 0.07 }}
              className="inline-block text-gold [text-shadow:0_4px_0_#b7791f,4px_8px_0_#17111f]"
            >
              {ch}
            </motion.span>
          ))}
        </motion.h1>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.9 }} className="px-text mt-6 max-w-xl text-balance font-pixel text-lg sm:text-2xl">
          拍に合わせた一歩は必ず通り、
          <br className="sm:hidden" />
          外した一歩は必ず返される。
        </motion.p>
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.1 }} className="pointer-events-auto mt-8 flex flex-wrap items-center justify-center gap-4">
          <PixelButton href={GAME_URL}>
            <Play className="size-5" aria-hidden />
            出陣する
          </PixelButton>
          <PixelButton tone="ghost" role="button" tabIndex={0} aria-pressed={sound} onClick={() => setSound(!sound)} onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), setSound(!sound))}>
            {sound ? <Volume2 className="size-5" aria-hidden /> : <VolumeX className="size-5" aria-hidden />}
            {sound ? '太鼓を止める' : '太鼓を鳴らす'}
          </PixelButton>
        </motion.div>
        <p className="mt-auto pb-20 font-pixel text-sm text-mist">ドラッグで戦場を回す</p>
      </motion.div>
      <motion.a href="#rule" aria-label="下へ進む" className="absolute bottom-5 left-1/2 z-10 grid size-12 -translate-x-1/2 place-items-center text-gold" animate={{ y: [0, 8, 0] }} transition={{ duration: 1, repeat: Infinity, ease: 'easeInOut' }}>
        <ChevronDown className="size-8" aria-hidden />
      </motion.a>
    </header>
  );
}

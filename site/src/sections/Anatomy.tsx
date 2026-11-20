import { useRef } from 'react';
import { motion, useScroll, useSpring, useTransform, type MotionValue } from 'motion/react';
import { StackCanvas, type Frame } from '../stack/StackCanvas';
import { drawScene } from '../stack/engine';

const STEPS = [
  { t: '城を、水平に輪切りにする。', d: 'この城は 3D モデルではありません。地面から屋根まで、42 枚の平らなドット絵です。' },
  { t: '1ドットずつ、ずらして積む。', d: '下の絵から順に、1 枚ごとに 1 ドット上へ。上の絵が下の絵を隠して、壁と屋根が生まれます。' },
  { t: '全部を、同じ角度で回す。', d: '向きごとの絵は 1 枚も描いていません。どの角度でも、画素はドット絵のまま。' },
];

function Step({ i, p, t, d }: { i: number; p: MotionValue<number>; t: string; d: string }) {
  const a = i / 3;
  const opacity = useTransform(p, [a - 0.03, a + 0.03, a + 0.25, a + 0.29], [i === 0 ? 1 : 0, 1, 1, i === 2 ? 1 : 0]);
  const y = useTransform(p, [a - 0.03, a + 0.03], [i === 0 ? 0 : 30, 0]);
  return (
    <motion.div style={{ opacity, y }} className="absolute inset-x-0 top-0">
      <p className="font-pixel text-6xl text-gold">{i + 1}</p>
      <h3 className="px-text mt-2 font-pixel text-2xl sm:text-4xl">{t}</h3>
      <p className="mt-4 max-w-md text-mist">{d}</p>
    </motion.div>
  );
}

/** A pinned scene: scrolling pulls the castle's slices apart, stacks them again, then turns the whole thing. */
export function Anatomy() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end end'] });
  const p = useSpring(scrollYProgress, { stiffness: 120, damping: 24 });
  const gap = useTransform(p, [0, 0.12, 0.3, 0.55, 1], [1, 4.2, 4.2, 1, 1]);
  const yaw = useTransform(p, [0, 0.3, 0.6, 1], [0.5, 0.75, 0.9, 0.9 + Math.PI * 2]);
  const squash = useTransform(p, [0, 0.12, 0.3, 0.55], [0.68, 0.5, 0.5, 0.68]);
  const bar = useTransform(p, [0, 1], ['0%', '100%']);

  const draw = ({ ctx, models, w, h }: Frame) => {
    const g = gap.get();
    const zoom = Math.max(1, Math.min(4, Math.min(w / 76, h / (42 * g + 62))));
    const tall = 42 * g * zoom;
    drawScene(ctx, models, [{ m: 'castle', x: 0, y: 0, yaw: yaw.get(), gap: g, shadow: 0.4 }], { yaw: 0, squash: squash.get(), zoom, cx: w / 2, cy: h / 2 + tall / 2 });
  };

  return (
    <section ref={ref} className="relative h-[320vh] bg-panel">
      <div className="sticky top-0 flex h-screen items-center overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_70%_50%,#3a2c63_0%,#1d1830_65%)]" />
        <div className="relative mx-auto grid w-full max-w-6xl items-center gap-6 px-5 md:grid-cols-2">
          <div>
            <p className="font-pixel text-sm tracking-[0.3em] text-gold">HOW IT IS DRAWN</p>
            <div className="relative mt-4 h-64 sm:h-72">
              {STEPS.map((s, i) => (
                <Step key={i} i={i} p={p} {...s} />
              ))}
            </div>
            <div className="mt-2 h-2 w-full max-w-md border-2 border-ink bg-night">
              <motion.div className="h-full bg-gold" style={{ width: bar }} />
            </div>
          </div>
          <StackCanvas draw={draw} pixel={(w) => (w < 480 ? 2 : 3)} label="輪切りの絵が離れ、積み重なり、回転する城" className="h-[46vh] w-full md:h-[78vh]" />
        </div>
      </div>
    </section>
  );
}

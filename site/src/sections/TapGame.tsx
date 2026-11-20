import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, useAnimationFrame, useMotionValue } from 'motion/react';
import { StackCanvas, type Frame } from '../stack/StackCanvas';
import { drawGround, drawScene, type Obj } from '../stack/engine';
import { BPM, beatNow, blip, frac, hop } from '../lib/beat';
import { FIG } from '../lib/site';
import { Reveal, SectionTitle } from '../components/ui';
import { cn } from '../lib/cn';

type Judge = 'PERFECT' | 'GOOD' | 'MISS' | '会心';
const MS_PER_BEAT = 60000 / BPM;
const TONE: Record<Judge, string> = { PERFECT: 'text-gold', 会心: 'text-ember', GOOD: 'text-moss', MISS: 'text-mist' };

interface Foe { m: Obj['m']; x: number; hit: number | null }
const LINE: Obj['m'][] = ['grunt', 'grunt', 'guard', 'grunt', 'archer', 'brute', 'grunt', 'drummer'];

/** Tap on the beat: a hit always lands, a miss always bounces. The same rule as the game, in one lane. */
export function TapGame() {
  const [judge, setJudge] = useState<{ j: Judge; id: number } | null>(null);
  const [combo, setCombo] = useState(0);
  const st = useRef({ foes: [] as Foe[], next: 0, lunge: -9, shake: -9, combo: 0, id: 0 });
  const ring = useMotionValue(1);
  const glow = useMotionValue(0);
  useAnimationFrame(() => {
    const f = frac(beatNow());
    ring.set(1 + (1 - f) * 0.9); // closes in on the target, touching it on the beat
    glow.set(Math.exp(-6 * f));
  });

  const tap = () => {
    const s = st.current;
    const b = beatNow();
    const off = Math.abs(b - Math.round(b)) * MS_PER_BEAT;
    const downbeat = ((Math.round(b) % 4) + 4) % 4 === 0;
    const j: Judge = off <= 70 ? (downbeat ? '会心' : 'PERFECT') : off <= 140 ? 'GOOD' : 'MISS';
    const now = performance.now() / 1000;
    if (j === 'MISS') {
      s.combo = 0;
      s.shake = now;
    } else {
      s.combo++;
      s.lunge = now;
      const front = s.foes.find((f) => f.hit === null);
      if (front) front.hit = now;
    }
    blip(j !== 'MISS');
    setCombo(s.combo);
    setJudge({ j, id: ++s.id });
  };

  useEffect(() => {
    const s = st.current;
    s.foes = Array.from({ length: 5 }, (_, i) => ({ m: LINE[i % LINE.length], x: 30 + i * 30, hit: null }));
    s.next = 5;
  }, []);

  const draw = ({ ctx, models, w, h }: Frame) => {
    const s = st.current;
    const now = performance.now() / 1000;
    const b = beatNow();
    const cam = { yaw: 0, squash: 0.62, zoom: 1, cx: Math.max(50, w / 2 - 40), cy: h * 0.7 };
    drawGround(ctx, cam, 400, 16, '#241c3a', '#2b2246');
    // fallen foes leave, the rest close ranks, a new one joins at the back
    s.foes = s.foes.filter((f) => f.hit === null || now - f.hit < 0.6);
    const alive = s.foes.filter((f) => f.hit === null);
    alive.forEach((f, i) => (f.x += (30 + i * 30 - f.x) * 0.12));
    while (alive.length < 5) {
      const f: Foe = { m: LINE[s.next++ % LINE.length], x: 30 + alive.length * 30 + 60, hit: null };
      s.foes.push(f);
      alive.push(f);
    }
    const lunge = Math.max(0, 1 - (now - s.lunge) / 0.22);
    const shake = Math.max(0, 1 - (now - s.shake) / 0.3);
    const objs: Obj[] = [
      { m: 'king', x: -34 + lunge * 16 + Math.sin(now * 70) * shake * 2.5, y: 0, yaw: -0.45, z: 2.5 * hop(b), ...FIG },
      { m: 'drum', x: -62, y: 8, gap: 1 + 0.5 * Math.exp(-5 * frac(b)) },
      { m: 'pawn', x: -58, y: -14, yaw: -0.45, z: 2.5 * hop(b), ...FIG },
      { m: 'pawn', x: -80, y: -2, yaw: -0.45, z: 2.5 * hop(b), ...FIG },
      ...s.foes.map((f): Obj => {
        if (f.hit === null) return { m: f.m, x: f.x, y: 0, yaw: 0.45, z: 2 * hop(b + 0.5), ...FIG };
        const k = (now - f.hit) / 0.6; // struck: the slices fly apart
        return { m: f.m, x: f.x + k * 26, y: 0, yaw: 0.45 + k * 5, z: 10 * Math.sin(k * Math.PI), ...FIG, gap: 1.25 + k * 5, alpha: 1 - k, shadow: 0 };
      }),
    ];
    drawScene(ctx, models, objs, cam);
  };

  const mood = combo >= 28 ? 'FEVER!!' : combo >= 12 ? 'GROOVE!' : null;
  return (
    <section id="rule" className="relative px-5 py-24 sm:py-32">
      <SectionTitle kicker="RULE" sub="乱数はありません。拍に合った体当たりは必ず通り、外せば必ず弾かれます。小節の頭（金色の拍）で PERFECT を取れば「会心」。">
        拍に合えば、<span className="text-gold">必ず通る。</span>
      </SectionTitle>
      <Reveal className="mx-auto mt-12 max-w-4xl">
        <div
          className={cn('px-shadow relative overflow-hidden border-2 border-ink bg-panel transition-colors duration-500', combo >= 28 ? 'bg-[#3a1626]' : combo >= 12 && 'bg-[#1c2444]')}
        >
          <StackCanvas draw={draw} pixel={(w, h) => Math.max(2, Math.min(5, Math.floor(Math.min(w / 215, h / 62))))} label="王が敵の列に体当たりする一本道。拍に合わせて叩くと先頭の敵が倒れる" className="h-56 w-full sm:h-72" />
          <div className="pointer-events-none absolute left-4 top-3 font-pixel">
            <p className="text-xs tracking-widest text-mist">連鎖</p>
            <motion.p key={combo} initial={{ scale: 1.5 }} animate={{ scale: 1 }} className={cn('origin-left text-4xl', combo >= 28 ? 'text-ember' : combo >= 12 ? 'text-gold' : 'text-paper')}>
              {combo}
            </motion.p>
          </div>
          <AnimatePresence>
            {mood && (
              <motion.p key={mood} initial={{ scale: 3, opacity: 0, rotate: -8 }} animate={{ scale: 1, opacity: 1, rotate: -4 }} exit={{ opacity: 0 }} className="px-text pointer-events-none absolute right-4 top-3 font-pixel text-3xl text-gold sm:text-4xl">
                {mood}
              </motion.p>
            )}
          </AnimatePresence>
          <div className="pointer-events-none absolute inset-x-0 top-6 flex justify-center" aria-live="polite">
            <AnimatePresence mode="popLayout">
              {judge && (
                <motion.p key={judge.id} initial={{ y: 16, opacity: 0, scale: 0.6 }} animate={{ y: 0, opacity: 1, scale: 1 }} exit={{ y: -18, opacity: 0 }} transition={{ type: 'spring', stiffness: 500, damping: 18 }} className={cn('px-text font-pixel text-3xl', TONE[judge.j])}>
                  {judge.j}
                </motion.p>
              )}
            </AnimatePresence>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-3">
          <button
            type="button"
            onPointerDown={(e) => {
              e.preventDefault();
              tap();
            }}
            onKeyDown={(e) => {
              if ((e.key === ' ' || e.key === 'Enter') && !e.repeat) {
                e.preventDefault();
                tap();
              }
            }}
            className="relative grid size-28 cursor-pointer select-none place-items-center rounded-full border-4 border-ink bg-ember font-pixel text-xl text-paper shadow-[0_6px_0_0_#17111f] active:translate-y-1 active:shadow-[0_2px_0_0_#17111f]"
          >
            <motion.span aria-hidden className="absolute inset-0 rounded-full border-4 border-gold" style={{ scale: ring, opacity: glow }} />
            <motion.span aria-hidden className="absolute inset-0 rounded-full bg-gold" style={{ opacity: glow, scale: 0.92 }} />
            <span className="relative">叩く</span>
          </button>
          <p className="text-center text-sm text-mist">
            輪が重なる瞬間に「叩く」。ボタンを選んでから Space / Enter でも叩けます。
            <br />
            連鎖 12 で GROOVE、28 で FEVER。
          </p>
        </div>
      </Reveal>
    </section>
  );
}

import { useEffect, useRef, useState } from 'react';
import { animate, motion, useInView, useScroll, useTransform } from 'motion/react';
import { Flag, Hand, Play, Shield, Swords, Zap } from 'lucide-react';
import { StackCanvas, type Frame } from '../stack/StackCanvas';
import { drawScene, type Obj } from '../stack/engine';
import { beatNow, hop, pulse } from '../lib/beat';
import { FIG, GAME_URL } from '../lib/site';
import { PixelButton, Reveal, SectionTitle } from '../components/ui';

function Count({ to, className }: { to: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const seen = useInView(ref, { once: true, margin: '-60px' });
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!seen) return;
    const c = animate(0, to, { duration: 1.1, ease: 'easeOut', onUpdate: (v) => setN(Math.round(v)) });
    return () => c.stop();
  }, [seen, to]);
  return <span ref={ref} className={className}>{n}</span>;
}

const RULES = [
  { icon: Swords, title: '拍に合えば必ず通る', text: 'GOOD は等倍、PERFECT は2倍、小節の頭の PERFECT は「会心」で3倍。' },
  { icon: Shield, title: '拍に乗っている間は守れる', text: 'PERFECT なら弾き返す。外した拍・動かなかった拍は守れない。' },
  { icon: Flag, title: '旗はチェックポイント', text: 'やられたら旗からすぐ再開。負けが続くと援軍が来る。' },
  { icon: Hand, title: '拍が苦手でも遊べる', text: '判定を「ゆるめ」に、拍そのものが苦手なら「おまかせ」に。' },
];

export function Rules() {
  return (
    <section className="px-5 py-24 sm:py-32">
      <SectionTitle kicker="GROOVE & FEVER">
        連鎖が、<span className="text-gold">曲を育てる。</span>
      </SectionTitle>
      <div className="mx-auto mt-14 grid max-w-5xl gap-5 md:grid-cols-6">
        <Reveal className="md:col-span-3">
          <div className="px-shadow h-full border-2 border-ink bg-[#1c2444] p-6">
            <p className="font-pixel text-sm text-mist">連鎖</p>
            <p className="font-pixel text-7xl text-gold"><Count to={12} /></p>
            <h3 className="font-pixel text-3xl">GROOVE!</h3>
            <p className="mt-2 text-sm text-mist">裏拍でも進める（＝倍速）。攻撃 +1。曲の楽器が増える。</p>
          </div>
        </Reveal>
        <Reveal delay={0.1} className="md:col-span-3">
          <div className="px-shadow h-full border-2 border-ink bg-[#3a1626] p-6">
            <p className="font-pixel text-sm text-mist">連鎖</p>
            <p className="font-pixel text-7xl text-ember"><Count to={28} /></p>
            <h3 className="font-pixel text-3xl">FEVER!!</h3>
            <p className="mt-2 text-sm text-mist">攻撃 +2。光の筋と紙吹雪。数字は白銀から金、そして炎へ。</p>
          </div>
        </Reveal>
        {RULES.map((r, i) => (
          <Reveal key={r.title} delay={0.05 * i} className="md:col-span-3">
            <div className="h-full border-2 border-line bg-panel p-6">
              <r.icon className="size-7 text-gold" aria-hidden />
              <h3 className="mt-3 font-pixel text-xl">{r.title}</h3>
              <p className="mt-2 text-sm text-mist">{r.text}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

/** The army marches toward the reader as the page ends. */
export function Finale() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start end', 'end end'] });
  const march = useTransform(scrollYProgress, [0, 1], [-70, 0]);
  const draw = ({ ctx, models, w, h }: Frame) => {
    const b = beatNow();
    const zoom = Math.max(1, Math.floor(w / 150));
    const objs: Obj[] = [];
    const rows: [Obj['m'], number][] = [['king', 1], ['knight', 2], ['pawn', 5], ['pawn', 6]];
    rows.forEach(([m, n], r) => {
      for (let i = 0; i < n; i++) objs.push({ m, x: (i - (n - 1) / 2) * 20, y: march.get() - r * 20 + 26, z: 2.6 * hop(b + r * 0.25), ...FIG });
    });
    objs.push({ m: 'drum', x: 0, y: march.get() - 62, gap: 1 + 0.5 * pulse(b, 5) }, { m: 'flag', x: -64, y: march.get() - 30 }, { m: 'flag', x: 64, y: march.get() - 30 });
    drawScene(ctx, models, objs, { yaw: 0, squash: 0.66, zoom, cx: w / 2, cy: h * 0.62 });
  };
  return (
    <section ref={ref} className="relative overflow-hidden bg-[radial-gradient(ellipse_at_50%_100%,#3a2c63_0%,#120e1a_70%)] px-5 pb-16 pt-24 text-center">
      <Reveal>
        <Zap className="mx-auto size-8 text-gold" aria-hidden />
        <h2 className="px-text mt-3 font-pixel text-4xl sm:text-6xl">太鼓を、打て。</h2>
        <p className="mx-auto mt-4 max-w-xl text-mist">インストール不要。ブラウザで動きます。キーボードでもタッチでも。模範プレイを見てから、途中で交代することもできます。</p>
        <motion.div className="mt-8 inline-block" animate={{ scale: [1, 1.05, 1] }} transition={{ duration: 0.5, repeat: Infinity, ease: 'easeOut' }}>
          <PixelButton href={GAME_URL} className="px-10 py-3 text-2xl">
            <Play className="size-6" aria-hidden />
            出陣する
          </PixelButton>
        </motion.div>
      </Reveal>
      <StackCanvas draw={draw} pixel={(w) => (w < 640 ? 2 : 3)} label="拍に合わせてこちらへ進む軍" className="mx-auto mt-6 h-72 w-full max-w-4xl" />
      <footer className="mt-6 text-xs text-mist">
        <p>ドラムレギオン — 世界観・キャラクター・ドット絵・音楽はすべてオリジナルです。</p>
        <p className="mt-1">このページの立体はすべてスプライトスタッキング（輪切りのドット絵の積み重ね）で描いています。</p>
      </footer>
    </section>
  );
}

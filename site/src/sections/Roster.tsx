import { useRef } from 'react';
import { motion, useMotionValue, useSpring } from 'motion/react';
import { StackCanvas, type Frame } from '../stack/StackCanvas';
import { drawScene, type ModelName } from '../stack/engine';
import { beatNow, hop } from '../lib/beat';
import { FIG } from '../lib/site';
import { Reveal, SectionTitle, TiltCard } from '../components/ui';

/** One figurine on a pedestal of light. It turns slowly by itself and follows the pointer across its card. */
function Figure({ m, label, scale = 3 }: { m: ModelName; label: string; scale?: number }) {
  const aim = useMotionValue(0);
  const turn = useSpring(aim, { stiffness: 90, damping: 14 });
  const box = useRef<HTMLDivElement>(null);
  const draw = ({ ctx, models, w, h, t }: Frame) => {
    drawScene(ctx, models, [{ m, x: 0, y: 0, yaw: Math.sin(t * 0.7) * 0.5 + turn.get(), z: 1.2 * hop(beatNow()), ...FIG }], {
      yaw: 0, squash: 0.6, zoom: scale, cx: w / 2, cy: h * 0.78,
    });
  };
  return (
    <div
      ref={box}
      onPointerMove={(e) => {
        const r = box.current!.getBoundingClientRect();
        aim.set(((e.clientX - r.left) / r.width - 0.5) * 5);
      }}
      onPointerLeave={() => aim.set(0)}
      className="relative"
    >
      <div aria-hidden className="absolute inset-x-6 bottom-3 h-8 rounded-[50%] bg-paper/10 blur-md" />
      <StackCanvas draw={draw} pixel={3} label={label} className="h-44 w-full" />
    </div>
  );
}

const ARMY: { m: ModelName; name: string; role: string; text: string; glow: string }[] = [
  { m: 'king', name: '王', role: '太鼓を打つ者', text: '王の隣の兵は攻撃 +1。前に出すほど軍は強くなるが、王が倒れたら終わり。', glow: '#3866e8' },
  { m: 'pawn', name: '兵', role: '数で押す', text: '王の太鼓が届く所までしか進まない。王を置き去りにして、兵だけで進むことはできない。', glow: '#3fae5e' },
  { m: 'knight', name: '騎士', role: '盾と槍', text: '騎士の盾は弓兵の矢を止める。列の先頭に立たせて、後ろの兵を守る。', glow: '#e8b23a' },
];

export function Army() {
  return (
    <section className="px-5 py-24 sm:py-32">
      <SectionTitle kicker="YOUR LEGION" sub="指揮は「全軍・王だけ・兵だけ」を切り替えられます。檻に捕らわれた仲間は、体当たりで救い出せます。">
        軍を進めるのは、<span className="text-gold">あなたの拍。</span>
      </SectionTitle>
      <div className="mx-auto mt-14 grid max-w-5xl gap-6 md:grid-cols-3">
        {ARMY.map((u, i) => (
          <Reveal key={u.m} delay={i * 0.1}>
            <TiltCard glow={u.glow} className="h-full p-5">
              <Figure m={u.m} label={`回転する${u.name}の立体ドット絵`} />
              <p className="mt-2 font-pixel text-xs tracking-widest" style={{ color: u.glow }}>{u.role}</p>
              <h3 className="font-pixel text-3xl">{u.name}</h3>
              <p className="mt-2 text-sm text-mist">{u.text}</p>
            </TiltCard>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

const FOES: { m: ModelName; name: string; text: string; scale?: number }[] = [
  { m: 'grunt', name: '雑兵', text: '数で来るが、拍に乗っていれば痛くない。連鎖とゲージの種。' },
  { m: 'brute', name: '大鬼', text: '構えたら下がれ。振り下ろした後は隙だらけ（被ダメージ2倍）。' },
  { m: 'guard', name: '衛兵', text: '盾。PERFECT 以外は半減（最低1は通る）。' },
  { m: 'archer', name: '弓兵', text: '同じ列の先頭を射る。騎士の盾と地形は矢を止める。' },
  { m: 'drummer', name: '鼓手', text: '叩いている間、周りの敵は倍速。先に倒す。' },
  { m: 'castle', name: '城主', text: '振り下ろし → 衝撃波 → 隙 → 手下、の巡り。隙でだけ攻撃がまともに通る。', scale: 1.4 },
];

/** A strip you drag sideways; it also drifts with the page scroll so it never sits still. */
export function Enemies() {
  const wrap = useRef<HTMLDivElement>(null);
  return (
    <section className="overflow-hidden border-y-2 border-ink bg-panel py-24 sm:py-32">
      <div className="px-5">
        <SectionTitle kicker="THE LORD'S MEN" sub="敵の通常攻撃は、その拍に乗れていれば防げます。赤い縞のマスだけは防げません。予告を見て、位置でかわす。">
          相手を知れば、<span className="text-ember">拍が決まる。</span>
        </SectionTitle>
      </div>
      <div ref={wrap} className="mt-14 px-5">
        <motion.ul drag="x" dragConstraints={wrap} dragElastic={0.12} className="mx-auto flex w-max cursor-grab gap-5 active:cursor-grabbing" aria-label="敵の一覧（横にドラッグ）">
          {FOES.map((f) => (
            <li key={f.name} className="px-shadow w-64 shrink-0 border-2 border-ink bg-night p-5">
              <Figure m={f.m} label={`回転する${f.name}の立体ドット絵`} scale={f.scale ?? 3} />
              <h3 className="mt-2 font-pixel text-2xl text-ember">{f.name}</h3>
              <p className="mt-2 text-sm text-mist">{f.text}</p>
            </li>
          ))}
        </motion.ul>
      </div>
      <p className="mt-6 text-center font-pixel text-sm text-mist">← ドラッグで見る →</p>
    </section>
  );
}

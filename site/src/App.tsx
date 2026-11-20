import { motion, useScroll, useSpring } from 'motion/react';
import { Hero } from './sections/Hero';
import { TapGame } from './sections/TapGame';
import { Anatomy } from './sections/Anatomy';
import { Army, Enemies } from './sections/Roster';
import { Finale, Rules } from './sections/Closing';
import { Marquee } from './components/ui';

export default function App() {
  const { scrollYProgress } = useScroll();
  const bar = useSpring(scrollYProgress, { stiffness: 200, damping: 30 });
  return (
    <>
      <motion.div aria-hidden className="fixed inset-x-0 top-0 z-50 h-1 origin-left bg-gold" style={{ scaleX: bar }} />
      <main>
        <Hero />
        <Marquee items={['拍に乗れ', 'PERFECT ×2', '会心 ×3', 'GROOVE!', 'FEVER!!', '仲間を救え', '城主を討て']} />
        <TapGame />
        <Anatomy />
        <Army />
        <Enemies />
        <Rules />
        <Finale />
      </main>
    </>
  );
}

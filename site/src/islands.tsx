// The interactive parts of the page, as Astro islands. Each island is its own React tree, so each gets the
// reduced-motion setting here rather than from a shared root.
import type { ComponentType } from 'react';
import { MotionConfig, motion, useScroll, useSpring } from 'motion/react';
import { Hero as HeroSection } from './sections/Hero';
import { TapGame as TapGameSection } from './sections/TapGame';
import { Anatomy as AnatomySection } from './sections/Anatomy';
import { Army as ArmySection, Enemies as EnemiesSection } from './sections/Roster';
import { Finale as FinaleSection, Rules as RulesSection } from './sections/Closing';
import { Marquee as MarqueeStrip } from './components/ui';

function island<P extends object>(C: ComponentType<P>) {
  return function Island(props: P) {
    return (
      <MotionConfig reducedMotion="user">
        <C {...props} />
      </MotionConfig>
    );
  };
}

function Progress() {
  const { scrollYProgress } = useScroll();
  const bar = useSpring(scrollYProgress, { stiffness: 200, damping: 30 });
  return <motion.div aria-hidden className="fixed inset-x-0 top-0 z-50 h-1 origin-left bg-gold" style={{ scaleX: bar }} />;
}

export const ScrollProgress = island(Progress);
export const Hero = island(HeroSection);
export const Marquee = island(MarqueeStrip);
export const TapGame = island(TapGameSection);
export const Anatomy = island(AnatomySection);
export const Army = island(ArmySection);
export const Enemies = island(EnemiesSection);
export const Rules = island(RulesSection);
export const Finale = island(FinaleSection);

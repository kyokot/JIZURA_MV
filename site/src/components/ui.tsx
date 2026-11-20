// Small building blocks in the shadcn / 21st.dev idiom: one file per idea, styled with Tailwind, moved with motion.
import { useRef, type ComponentProps, type ReactNode } from 'react';
import { motion, useMotionTemplate, useMotionValue, useSpring, useTransform } from 'motion/react';
import { cn } from '../lib/cn';

type ButtonProps = ComponentProps<typeof motion.a> & { tone?: 'gold' | 'ghost' };

/** A chunky pixel button. Use it as a link (href) or give it onClick with role="button". */
export function PixelButton({ tone = 'gold', className, children, ...rest }: ButtonProps) {
  return (
    <motion.a
      whileHover={{ y: -2 }}
      whileTap={{ y: 3, boxShadow: '0px 0px 0 0 #17111f' }}
      transition={{ type: 'spring', stiffness: 600, damping: 22 }}
      className={cn(
        'px-shadow inline-flex min-h-12 cursor-pointer select-none items-center justify-center gap-2 border-2 border-ink px-6 py-2 font-pixel text-lg',
        tone === 'gold' ? 'bg-gold text-ink hover:bg-[#ffe07a]' : 'bg-panel-2 text-paper hover:bg-line',
        className,
      )}
      {...rest}
    >
      {children}
    </motion.a>
  );
}

/** A card that leans toward the pointer and carries a soft light where the pointer is. */
export function TiltCard({ children, className, glow = '#ffcf3a' }: { children: ReactNode; className?: string; glow?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const px = useMotionValue(0.5);
  const py = useMotionValue(0.5);
  const rx = useSpring(useTransform(py, [0, 1], [9, -9]), { stiffness: 220, damping: 18 });
  const ry = useSpring(useTransform(px, [0, 1], [-11, 11]), { stiffness: 220, damping: 18 });
  const lx = useTransform(px, (v) => `${v * 100}%`);
  const ly = useTransform(py, (v) => `${v * 100}%`);
  const light = useMotionTemplate`radial-gradient(260px circle at ${lx} ${ly}, ${glow}38, transparent 70%)`;
  return (
    <motion.div
      ref={ref}
      onPointerMove={(e) => {
        const r = ref.current!.getBoundingClientRect();
        px.set((e.clientX - r.left) / r.width);
        py.set((e.clientY - r.top) / r.height);
      }}
      onPointerLeave={() => {
        px.set(0.5);
        py.set(0.5);
      }}
      style={{ rotateX: rx, rotateY: ry, transformPerspective: 900 }}
      className={cn('px-shadow relative border-2 border-ink bg-panel', className)}
    >
      <motion.div aria-hidden className="pointer-events-none absolute inset-0" style={{ background: light }} />
      <div className="relative">{children}</div>
    </motion.div>
  );
}

/** Fades and lifts its children in the first time they scroll into view. */
export function Reveal({ children, delay = 0, className }: { children: ReactNode; delay?: number; className?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 28 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.55, delay, ease: [0.2, 0.8, 0.2, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function Marquee({ items }: { items: string[] }) {
  const row = [...items, ...items];
  return (
    <div className="overflow-hidden border-y-2 border-ink bg-gold py-3 text-ink" aria-hidden>
      <motion.div className="flex w-max gap-10 font-pixel text-xl" animate={{ x: ['0%', '-50%'] }} transition={{ duration: 22, ease: 'linear', repeat: Infinity }}>
        {row.map((s, i) => (
          <span key={i} className="flex items-center gap-10 whitespace-nowrap">
            {s}
            <span className="inline-block size-2 bg-ink" />
          </span>
        ))}
      </motion.div>
    </div>
  );
}

export function SectionTitle({ kicker, children, sub }: { kicker: string; children: ReactNode; sub?: ReactNode }) {
  return (
    <Reveal className="mx-auto max-w-3xl text-center">
      <p className="font-pixel text-sm tracking-[0.3em] text-gold">{kicker}</p>
      <h2 className="px-text mt-3 font-pixel text-3xl leading-tight sm:text-5xl">{children}</h2>
      {sub && <p className="mx-auto mt-5 max-w-2xl text-mist">{sub}</p>}
    </Reveal>
  );
}

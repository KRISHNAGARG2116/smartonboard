import { motion, useScroll, useTransform } from 'framer-motion';
import { useRef } from 'react';

export function HeroCuriosity() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end start"]
  });

  const opacityCuriosity = useTransform(scrollYProgress, [0, 0.3], [1, 0]);
  const opacityOS = useTransform(scrollYProgress, [0.4, 0.8], [0, 1]);
  const yOS = useTransform(scrollYProgress, [0.4, 0.8], [50, 0]);

  return (
    <section ref={containerRef} className="relative w-full h-[200vh] bg-black text-white selection:bg-white selection:text-black">
      <div className="sticky top-0 h-screen w-full flex flex-col items-center justify-center px-6 md:px-12 lg:px-24">
        
        {/* Curiosity State (Visible on load, fades on scroll) */}
        <motion.div 
          style={{ opacity: opacityCuriosity }}
          className="absolute inset-0 flex flex-col items-center justify-center"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1] }}
          >
            <h1 className="text-4xl md:text-6xl lg:text-7xl font-light tracking-tight text-center max-w-4xl text-white/90">
              There is finally a <br/>
              <span className="font-serif italic text-white">better way to hire.</span>
            </h1>
          </motion.div>
          
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 2, duration: 1 }}
            className="absolute bottom-12 flex flex-col items-center gap-4 text-white/40 font-mono text-xs tracking-widest uppercase"
          >
            Scroll
            <div className="w-[1px] h-12 bg-gradient-to-b from-white/40 to-transparent" />
          </motion.div>
        </motion.div>

        {/* Operating System State (Reveals on scroll) */}
        <motion.div 
          style={{ opacity: opacityOS, y: yOS }}
          className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none"
        >
          <div className="text-center w-full max-w-6xl mx-auto px-6">
            <h2 className="text-[10vw] md:text-[8vw] leading-[0.9] tracking-tighter font-bold uppercase">
              The Operating System <br/>
              <span className="text-white/40 italic font-serif lowercase tracking-normal">for</span> <br/>
              Modern Hiring.
            </h2>
            <p className="mt-12 text-lg md:text-xl text-white/50 font-light max-w-2xl mx-auto leading-relaxed">
              Everything recruiters need, in one intelligent workspace.
            </p>
          </div>
        </motion.div>

      </div>
    </section>
  );
}

import { motion, useScroll, useTransform } from 'framer-motion';
import { useRef } from 'react';

export function KeywordTrap() {
  const containerRef = useRef<HTMLDivElement>(null);
  
  // We use scrollYProgress over a 200vh container to drive the progressive disclosure
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"]
  });

  // Phases:
  // 0.0 -> 0.3: Legacy ATS phase (Green highlights fade in)
  // 0.4 -> 0.6: Transition phase (Green fades out, Red fades in)
  // 0.6 -> 1.0: SmartOnboard phase (Red flags lock in, Headline appears)

  const atsOpacity = useTransform(scrollYProgress, [0.1, 0.3, 0.4, 0.5], [0, 1, 1, 0]);
  const smartOpacity = useTransform(scrollYProgress, [0.4, 0.6], [0, 1]);
  const smartY = useTransform(scrollYProgress, [0.4, 0.6], [10, 0]);

  // Headline opacity
  const titleOpacity = useTransform(scrollYProgress, [0.7, 0.9], [0, 1]);
  const titleY = useTransform(scrollYProgress, [0.7, 0.9], [20, 0]);

  return (
    <section ref={containerRef} className="h-[250vh] bg-white relative selection:bg-slate-200 selection:text-black">
      
      {/* Sticky Container */}
      <div className="sticky top-0 h-screen w-full flex flex-col items-center justify-center overflow-hidden px-6">
        
        {/* Section Context */}
        <div className="absolute top-24 inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-50 border border-slate-200 shadow-sm">
          <div className="w-1.5 h-1.5 rounded-full bg-slate-400" />
          <span className="text-[10px] font-bold tracking-widest text-slate-500 uppercase">The Problem</span>
        </div>

        {/* The Claim */}
        <div className="relative text-[2rem] md:text-[3.5rem] lg:text-[4.5rem] font-serif max-w-5xl text-center leading-[1.2] text-slate-800 tracking-tight">
          <span className="relative inline-block whitespace-nowrap">
            Led
            {/* ATS Layer */}
            <motion.span style={{ opacity: atsOpacity }} className="absolute inset-x-[-4px] bottom-1 top-4 bg-emerald-100 border-b-2 border-emerald-500 rounded-sm -z-10" />
            {/* SmartOnboard Layer */}
            <motion.div style={{ opacity: smartOpacity, y: smartY }} className="absolute -bottom-8 md:-bottom-12 left-1/2 -translate-x-1/2 text-[9px] md:text-xs font-bold uppercase tracking-widest text-red-500 whitespace-nowrap bg-red-50 px-2 py-1 rounded border border-red-200">
              Identity Unauthenticated
            </motion.div>
          </span>
          {' '}engineering team to build{' '}
          <span className="relative inline-block whitespace-nowrap">
            scalable
            <motion.span style={{ opacity: atsOpacity }} className="absolute inset-x-[-4px] bottom-1 top-4 bg-emerald-100 border-b-2 border-emerald-500 rounded-sm -z-10" />
            <motion.div style={{ opacity: smartOpacity, y: smartY }} className="absolute -bottom-8 md:-bottom-12 left-1/2 -translate-x-1/2 text-[9px] md:text-xs font-bold uppercase tracking-widest text-red-500 whitespace-nowrap bg-red-50 px-2 py-1 rounded border border-red-200">
              Metrics Unverified
            </motion.div>
          </span>
          {' '}React{' '}
          <span className="relative inline-block whitespace-nowrap">
            architecture.
            <motion.span style={{ opacity: atsOpacity }} className="absolute inset-x-[-4px] bottom-1 top-4 bg-emerald-100 border-b-2 border-emerald-500 rounded-sm -z-10" />
            <motion.div style={{ opacity: smartOpacity, y: smartY }} className="absolute -bottom-8 md:-bottom-12 left-1/2 -translate-x-1/2 text-[9px] md:text-xs font-bold uppercase tracking-widest text-red-500 whitespace-nowrap bg-red-50 px-2 py-1 rounded border border-red-200">
              Impact Missing
            </motion.div>
          </span>
        </div>

        {/* The Conclusion Headline */}
        <motion.div 
          style={{ opacity: titleOpacity, y: titleY }}
          className="absolute bottom-24 md:bottom-32 text-center"
        >
          <h2 className="text-xl md:text-2xl font-bold text-slate-900 tracking-tight mb-3">
            Legacy tools extract keywords perfectly.
          </h2>
          <p className="text-slate-500 font-medium">
            But keywords aren't evidence.
          </p>
        </motion.div>

        {/* Scroll Instruction (Fades out early) */}
        <motion.div 
           style={{ opacity: useTransform(scrollYProgress, [0, 0.1], [1, 0]) }}
           className="absolute bottom-12 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-slate-400"
        >
           <span className="text-[10px] font-bold uppercase tracking-widest">Scroll to scan</span>
           <div className="w-[1px] h-8 bg-gradient-to-b from-slate-400 to-transparent" />
        </motion.div>

      </div>
    </section>
  );
}

import { motion, useScroll, useTransform } from 'framer-motion';
import { useRef } from 'react';

export function SolutionJourney() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"]
  });

  const { scrollYProgress: exitProgress } = useScroll({
    target: containerRef,
    offset: ["end end", "end start"]
  });

  // Pull content down during exit to bridge the gap to the next section
  const exitY = useTransform(exitProgress, [0, 1], [0, 500]);

  // Phases
  // 0 -> 0.3: Candidate A (Keywords)
  // 0.3 -> 0.6: Candidate B (Evidence)
  // 0.6 -> 1.0: Evidence Collection Details
  
  // 0.00 -> 0.10: Phase 1 Enter
  // 0.10 -> 0.25: Phase 1 Hold
  // 0.25 -> 0.30: Phase 1 Exit
  // 0.30 -> 0.40: GAP (Clean screen)
  // 0.40 -> 0.50: Phase 2 Enter
  
  const opacityA = useTransform(scrollYProgress, [0, 0.1, 0.25, 0.3, 1], [0, 1, 1, 0, 0]);
  const yA = useTransform(scrollYProgress, [0, 0.1, 0.25, 0.3, 1], [40, 0, 0, -40, -40]);
  
  const opacityB = useTransform(scrollYProgress, [0, 0.4, 0.5, 1], [0, 0, 1, 1]);
  const yB = useTransform(scrollYProgress, [0, 0.4, 0.5, 1], [40, 40, 0, 0]);

  // Stretch the evidence cards across the remainder of the scroll
  const scaleEvidence = useTransform(scrollYProgress, [0, 0.55, 0.95, 1], [0.9, 0.9, 1, 1]);
  const opacityEvidence = useTransform(scrollYProgress, [0, 0.55, 0.95, 1], [0, 0, 1, 1]);

  return (
    <section ref={containerRef} className="h-[300vh] bg-[#0F172A] relative selection:bg-blue-500 selection:text-white">
      {/* Background Editorial Details */}
      <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden opacity-20">
         <div className="absolute inset-0 bg-[radial-gradient(#64748b_1px,transparent_1px)] [background-size:24px_24px] opacity-30" />
         <div className="absolute left-6 lg:left-24 top-0 bottom-0 w-[1px] bg-slate-700/50" />
         <div className="absolute right-6 lg:right-24 top-0 bottom-0 w-[1px] bg-slate-700/50" />
      </div>

      <div className="sticky top-0 h-screen w-full overflow-hidden px-6">
        <motion.div style={{ y: exitY }} className="w-full h-full flex flex-col items-center justify-center relative">
        
        <div className="absolute top-24 inline-flex items-center gap-2 px-3 py-1.5 rounded-sm bg-slate-800/50 border border-slate-700 shadow-sm backdrop-blur">
          <div className="w-1.5 h-1.5 rounded-sm bg-blue-500" />
          <span className="text-[10px] font-bold tracking-widest text-slate-300 uppercase font-mono">The Transformation</span>
        </div>

        {/* Stage 1: Candidate A (Keywords) */}
        <motion.div style={{ opacity: opacityA, y: yA }} className="absolute inset-0 flex flex-col lg:flex-row items-center justify-center gap-12 lg:gap-24 max-w-7xl mx-auto px-6 pointer-events-none">
           <div className="w-full lg:w-1/2">
              <h3 className="text-4xl lg:text-5xl font-serif text-white mb-6 tracking-tight">The Keyword Mirage</h3>
              <p className="text-slate-400 text-lg md:text-xl font-medium max-w-md leading-relaxed">
                 Candidate A knows how to beat the ATS. Their resume is packed with optimized buzzwords. The system confidently rewards them with a 98% match.
              </p>
           </div>
           <div className="w-full lg:w-1/2">
              <div className="bg-slate-900 border border-slate-700 rounded-lg p-8 shadow-2xl relative">
                 <div className="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
                    <div className="text-xl font-bold text-white">Candidate A</div>
                    <div className="px-3 py-1.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-bold rounded uppercase tracking-wider">98% ATS MATCH</div>
                 </div>
                 <div className="space-y-5">
                    <div className="flex items-start gap-4 opacity-50">
                       <div className="w-1.5 h-1.5 mt-2 rounded-sm bg-slate-600 shrink-0" />
                       <div className="text-sm font-mono text-slate-300 leading-relaxed">"Synergized scalable growth across cross-functional matrices..."</div>
                    </div>
                    <div className="flex items-start gap-4 opacity-50">
                       <div className="w-1.5 h-1.5 mt-2 rounded-sm bg-slate-600 shrink-0" />
                       <div className="text-sm font-mono text-slate-300 leading-relaxed">"Led paradigm-shifting ROI deliverables..."</div>
                    </div>
                 </div>
                 <div className="mt-8 pt-5 border-t border-slate-800 flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-red-500/50" />
                    <div className="text-[10px] text-red-400 font-bold tracking-widest uppercase">Zero Verified Evidence</div>
                 </div>
              </div>
           </div>
        </motion.div>

        {/* Stage 2 & 3: Candidate B & Evidence Collection */}
        <motion.div style={{ opacity: opacityB, y: yB }} className="absolute inset-0 flex flex-col lg:flex-row items-center justify-center gap-12 lg:gap-24 max-w-7xl mx-auto px-6 pointer-events-none">
           <div className="w-full lg:w-1/2 relative z-10 lg:pr-12">
              <h3 className="text-4xl lg:text-5xl font-serif text-white mb-6 tracking-tight leading-[1.1]">The Evidence Truth</h3>
              <p className="text-slate-400 text-lg md:text-xl font-medium max-w-lg leading-relaxed">
                 Candidate B wrote a simple resume. But their claims are backed by verifiable history, consistent timelines, and reviewed portfolios.
              </p>
           </div>
           
           <div className="w-full lg:w-1/2 relative">
              <div className="bg-slate-800 border border-blue-500/30 rounded-lg p-8 shadow-2xl relative z-10">
                 <div className="flex justify-between items-center mb-8 border-b border-slate-700 pb-4">
                    <div className="text-xl font-bold text-white">Candidate B</div>
                    <div className="px-3 py-1.5 bg-blue-500 text-white text-[10px] font-bold rounded uppercase tracking-widest shadow-[0_0_15px_rgba(59,130,246,0.5)]">SmartOnboard Verified</div>
                 </div>
                 <div className="space-y-6">
                    <div className="flex items-center gap-4">
                       <div className="w-2 h-2 rounded-sm bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,0.8)] shrink-0" />
                       <div className="text-sm font-medium text-slate-200">Shipped V2 Payment Gateway</div>
                    </div>
                    <div className="flex items-center gap-4">
                       <div className="w-2 h-2 rounded-sm bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,0.8)] shrink-0" />
                       <div className="text-sm font-medium text-slate-200">Grew team from 4 to 12</div>
                    </div>
                 </div>
              </div>

              {/* Evidence Collection Cards surfacing behind/around Candidate B */}
              <motion.div style={{ opacity: opacityEvidence, scale: scaleEvidence }} className="absolute inset-0 z-0">
                 <div className="absolute -top-12 -right-8 md:-right-16 bg-slate-900 border border-slate-700 p-3.5 rounded shadow-xl flex items-center gap-3">
                    <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                    <div className="text-[10px] text-slate-300 font-bold uppercase tracking-widest">Employment Verified</div>
                 </div>
                 <div className="absolute top-1/2 -left-8 md:-left-16 bg-slate-900 border border-slate-700 p-3.5 rounded shadow-xl flex items-center gap-3">
                    <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                    <div className="text-[10px] text-slate-300 font-bold uppercase tracking-widest">Portfolio Reviewed</div>
                 </div>
                 <div className="absolute -bottom-10 right-4 bg-slate-900 border border-slate-700 p-3.5 rounded shadow-xl flex items-center gap-3">
                    <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                    <div className="text-[10px] text-slate-300 font-bold uppercase tracking-widest">Timeline Confirmed</div>
                 </div>
              </motion.div>
           </div>
        </motion.div>
        </motion.div>
      </div>
    </section>
  );
}

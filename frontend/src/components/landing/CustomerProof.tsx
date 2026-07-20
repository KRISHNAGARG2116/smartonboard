import { motion, useScroll, useTransform } from 'framer-motion';
import { useRef } from 'react';

export function CustomerProof() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start end", "end start"]
  });

  const y = useTransform(scrollYProgress, [0, 1], [100, -100]);
  const opacity = useTransform(scrollYProgress, [0.2, 0.4, 0.9, 1], [0, 1, 1, 0]);

  return (
    <section ref={containerRef} className="py-32 md:py-48 bg-white relative border-y border-slate-200 overflow-hidden">
       {/* Editorial Texture */}
       <div className="absolute inset-0 pointer-events-none z-0">
         <div className="absolute inset-0 bg-[radial-gradient(#d6d3d1_1px,transparent_1px)] [background-size:24px_24px] opacity-30" />
         <div className="absolute left-6 lg:left-24 top-0 bottom-0 w-[1px] bg-slate-200" />
         <div className="absolute right-6 lg:right-24 top-0 bottom-0 w-[1px] bg-slate-200" />
         
         {/* Crop marks */}
         <div className="absolute top-12 left-6 lg:left-24 w-4 h-4 border-t border-l border-slate-400/50" />
         <div className="absolute top-12 right-6 lg:right-24 w-4 h-4 border-t border-r border-slate-400/50" />
       </div>

       <div className="max-w-7xl mx-auto px-6 relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-sm bg-slate-50 border border-slate-200 shadow-sm mb-20 md:mb-32">
            <div className="w-1.5 h-1.5 rounded-sm bg-blue-500" />
            <span className="text-[10px] font-bold tracking-widest text-slate-500 uppercase font-mono">The Impact</span>
          </div>

          <motion.div style={{ y, opacity }} className="grid grid-cols-1 xl:grid-cols-2 gap-16 xl:gap-32">
             {/* Text Side */}
             <div>
                <h2 className="text-4xl md:text-5xl lg:text-6xl font-serif font-bold text-slate-900 leading-[1.1] mb-8 tracking-tight">
                   Evidence eliminates the guessing game.
                </h2>
                <p className="text-lg md:text-xl text-slate-500 max-w-lg leading-relaxed">
                   When you stop relying on keyword parsing and start evaluating verified proof, the entire recruitment funnel condenses. 
                   Fewer interviews. Higher quality offers. Absolute recruiter confidence.
                </p>
             </div>
             
             {/* Data Side (Annual Report aesthetic) */}
             <div className="flex flex-col gap-10 border-t border-slate-900 pt-10">
                
                {/* Metric 1 */}
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
                  viewport={{ once: true, margin: "-100px" }}
                  className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4"
                >
                   <div>
                      <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">Traditional ATS Funnel</div>
                      <div className="text-slate-800 font-medium">42 Interviews <span className="mx-2 text-blue-300">→</span> 6 Offers</div>
                   </div>
                   <div className="md:text-right">
                      <div className="text-[10px] font-bold uppercase tracking-widest text-blue-600 mb-2">SmartOnboard Funnel</div>
                      <div className="text-3xl font-serif font-bold text-slate-900">28 Interviews <span className="mx-2 text-blue-300">→</span> <span className="text-blue-600">16 Offers</span></div>
                   </div>
                </motion.div>

                {/* Metric 2 */}
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
                  viewport={{ once: true, margin: "-100px" }}
                  className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 border-t border-slate-200 pt-10"
                >
                   <div>
                      <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">Recruiter Screening Time</div>
                      <div className="text-slate-800 font-medium">20+ Hours / Week</div>
                   </div>
                   <div className="md:text-right">
                      <div className="text-[10px] font-bold uppercase tracking-widest text-blue-600 mb-2">Evidence-Backed Screening</div>
                      <div className="text-3xl font-serif font-bold text-slate-900"><span className="text-blue-600">4 Hours</span> / Week</div>
                   </div>
                </motion.div>
                
                {/* Metric 3 */}
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
                  viewport={{ once: true, margin: "-100px" }}
                  className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 border-t border-slate-200 pt-10"
                >
                   <div>
                      <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">False Positives (Passed Screen)</div>
                      <div className="text-slate-800 font-medium">~35% Keyword Matches</div>
                   </div>
                   <div className="md:text-right">
                      <div className="text-[10px] font-bold uppercase tracking-widest text-blue-600 mb-2">SmartOnboard Pipeline</div>
                      <div className="text-3xl font-serif font-bold text-slate-900"><span className="text-blue-600">&lt; 2%</span> False Positives</div>
                   </div>
                </motion.div>

             </div>
          </motion.div>
       </div>
    </section>
  );
}

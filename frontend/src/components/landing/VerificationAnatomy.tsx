import { motion, useScroll, useTransform } from 'framer-motion';
import { useRef } from 'react';

export function VerificationAnatomy() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"]
  });

  const { scrollYProgress: enterProgress } = useScroll({
    target: containerRef,
    offset: ["start end", "start start"]
  });

  // Entrance animations that happen while the section scrolls into the viewport
  const initialOpacity = useTransform(enterProgress, [0, 0.5], [0, 1]);

  // Pull content up during entry to eliminate the 50vh top gap
  const enterY = useTransform(enterProgress, [0, 1], [-500, 0]);

  // Highlighting specific rows of the Intelligence Report as the user scrolls
  const identityHighlight = useTransform(scrollYProgress, [0, 0.2, 0.4, 0.5], [1, 1, 1, 0]);
  const evidenceHighlight = useTransform(scrollYProgress, [0.4, 0.5, 0.7, 0.8], [0, 1, 1, 0]);
  const decisionHighlight = useTransform(scrollYProgress, [0.7, 0.8, 1, 1], [0, 1, 1, 1]);

  return (
    <section ref={containerRef} className="h-[350vh] bg-[#0F172A] relative selection:bg-blue-500 selection:text-white">
      
      {/* Editorial Richness: Background Grid & Metadata */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden opacity-20">
         <div className="absolute inset-0 bg-[radial-gradient(#64748b_1px,transparent_1px)] [background-size:24px_24px] opacity-30" />
         <div className="absolute left-6 lg:left-24 top-0 bottom-0 w-[1px] bg-slate-700/50" />
         <div className="absolute right-6 lg:right-24 top-0 bottom-0 w-[1px] bg-slate-700/50" />
         <div className="absolute top-24 left-8 lg:left-28 text-[9px] font-mono text-slate-500 tracking-widest uppercase">
           TRUTH-PROTOCOL-ACTIVE
         </div>
      </div>

      <motion.div style={{ y: enterY }} className="sticky top-0 h-screen w-full flex flex-col items-center justify-center overflow-hidden px-6 max-w-7xl mx-auto">
        
        {/* The Section Header */}
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-sm bg-slate-800/50 border border-slate-700 shadow-sm backdrop-blur">
          <div className="w-1.5 h-1.5 rounded-sm bg-blue-500" />
          <span className="text-[10px] font-bold tracking-widest text-slate-300 uppercase font-mono">The Solution</span>
        </div>
        
        <div className="w-full flex flex-col lg:flex-row items-center gap-12 lg:gap-24 mt-16">
          
          {/* LEFT SIDE: The Recruiter Workspace Focal Point */}
          <div className="w-full lg:w-1/2 relative h-[500px]">
             
             {/* The Workspace Container */}
             <div className="absolute inset-0 bg-slate-50 shadow-[0_20px_60px_-15px_rgba(0,0,0,0.3)] border border-slate-200/50 rounded-lg overflow-hidden flex flex-col z-20">
                
                {/* Mock Browser/App Header */}
                <div className="h-10 border-b border-slate-200 bg-white flex items-center px-4 shrink-0 justify-between z-30">
                  <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-slate-200" />
                    <div className="w-2.5 h-2.5 rounded-full bg-slate-200" />
                    <div className="w-2.5 h-2.5 rounded-full bg-slate-200" />
                  </div>
                  <div className="text-[9px] font-medium text-slate-400 font-mono tracking-widest">smartonboard.os</div>
                  <div className="w-10" />
                </div>

                <div className="flex-1 flex relative overflow-hidden bg-white">
                  
                  {/* Candidate List (Always visible, background) */}
                  <div className="w-1/3 border-r border-slate-100 bg-slate-50/30 p-3 flex flex-col gap-2 z-10 shrink-0 hidden sm:flex">
                    <div className="h-4 w-16 bg-slate-200 rounded mb-2" />
                    
                    {/* Selected Candidate */}
                    <div className="p-2.5 bg-white border border-blue-100 shadow-sm rounded relative overflow-hidden">
                      <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-blue-500" />
                      <div className="text-xs font-bold text-slate-800">Alex Rivera</div>
                      <div className="text-[9px] text-slate-400 mt-0.5">Senior Designer</div>
                    </div>
                    
                    {/* Unselected Candidates */}
                    <div className="p-2.5 opacity-50">
                      <div className="text-xs font-medium text-slate-600">Jordan Smith</div>
                      <div className="text-[9px] text-slate-400 mt-0.5">Product Manager</div>
                    </div>
                    <div className="p-2.5 opacity-50">
                      <div className="text-xs font-medium text-slate-600">Taylor Swift</div>
                      <div className="text-[9px] text-slate-400 mt-0.5">Frontend Dev</div>
                    </div>
                  </div>

                  {/* Main Profile Area */}
                  <div className="flex-1 relative flex flex-col z-10">
                     
                     {/* Phase 1: Candidate Selected & Identity Confirmed */}
                     <motion.div 
                        style={{ opacity: initialOpacity }}
                        className="p-6 border-b border-slate-100"
                     >
                        <div className="flex justify-between items-start">
                           <div>
                              <div className="text-lg font-bold text-slate-900 mb-1">Alex Rivera</div>
                              <div className="text-xs text-slate-500">San Francisco, CA</div>
                           </div>
                           <div className="flex gap-2">
                              <span className="text-[9px] px-2 py-1 bg-emerald-50 text-emerald-700 rounded-sm font-bold uppercase tracking-wider">Identity Confirmed</span>
                           </div>
                        </div>
                     </motion.div>

                     {/* Phase 2: Evidence Drawer Sliding In */}
                     <motion.div 
                       style={{ 
                         x: useTransform(scrollYProgress, [0.3, 0.45], ["100%", "0%"]),
                         opacity: useTransform(scrollYProgress, [0.25, 0.4], [0, 1])
                       }}
                       className="absolute inset-y-0 right-0 w-full sm:w-[280px] bg-white border-l border-slate-100 p-5 shadow-[-20px_0_40px_-15px_rgba(0,0,0,0.05)] z-20 flex flex-col"
                     >
                       <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-6">Evidence Review</div>
                       
                       <div className="flex flex-col gap-5">
                          {[
                            "Employment Verified",
                            "Portfolio Reviewed",
                            "LinkedIn Consistent",
                            "Reference Available",
                            "Timeline Confirmed"
                          ].map((item, i) => (
                            <motion.div 
                              key={i} 
                              className="flex gap-3 items-center"
                            >
                               <div className="w-4 h-4 rounded-full bg-blue-50 border border-blue-100 flex items-center justify-center shrink-0">
                                  <div className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                               </div>
                               <div className="text-xs font-semibold text-slate-700">{item}</div>
                            </motion.div>
                          ))}
                       </div>
                     </motion.div>

                     {/* Phase 3: Decision Ready */}
                     <motion.div
                       style={{
                         opacity: decisionHighlight,
                         y: useTransform(scrollYProgress, [0.7, 0.8], [20, 0])
                       }}
                       className="absolute bottom-6 left-6 right-6 p-4 bg-slate-900 rounded shadow-xl z-30 flex items-center justify-between"
                     >
                        <div className="flex flex-col gap-1.5">
                           <div className="flex items-center gap-2">
                              <div className="w-2 h-2 rounded-full bg-blue-500" style={{ boxShadow: '0 0 10px rgba(59,130,246,0.5)' }} />
                              <div className="text-[10px] font-bold text-white uppercase tracking-widest">Decision Ready</div>
                           </div>
                           <div className="text-[10px] text-slate-400">Evidence Reviewed. Ready for next steps.</div>
                        </div>
                        <button className="px-4 py-2 bg-blue-600 text-white text-[10px] uppercase font-bold tracking-widest rounded-sm transition-colors cursor-pointer border border-blue-500">
                           Schedule Interview
                        </button>
                     </motion.div>
                     
                  </div>
                </div>
             </div>
          </div>

          {/* RIGHT SIDE: The Deep Dive Text */}
          <div className="w-full lg:w-1/2 relative h-[400px]">
             
             {/* 1. Identity Explainer */}
             <motion.div 
               style={{ opacity: identityHighlight, y: useTransform(scrollYProgress, [0, 0.4], [0, -20]) }}
               className="absolute inset-0 flex flex-col justify-center"
             >
               <h3 className="text-3xl md:text-4xl font-serif font-bold text-white mb-5 tracking-tight">
                 We verify the human before the resume.
               </h3>
               <p className="text-slate-400 text-lg leading-relaxed max-w-md font-medium">
                 Every candidate on SmartOnboard must authenticate their identity. We enforce multi-factor OTP verification and DNS checks on work emails. You are talking to who you think you are talking to.
               </p>
             </motion.div>

             {/* 2. Evidence Explainer */}
             <motion.div 
               style={{ opacity: evidenceHighlight, y: useTransform(scrollYProgress, [0.3, 0.7], [20, -20]) }}
               className="absolute inset-0 flex flex-col justify-center pointer-events-none"
             >
               <h3 className="text-3xl md:text-4xl font-serif font-bold text-white mb-5 tracking-tight">
                 Every claim requires cross-referenced proof.
               </h3>
               <p className="text-slate-400 text-lg leading-relaxed max-w-md font-medium">
                 We don't accept "built scalable architecture" at face value. Our engine cross-references claimed timelines against public product releases, verified scale metrics, and peer-authenticated ledgers.
               </p>
             </motion.div>

             {/* 3. Decision Explainer */}
             <motion.div 
               style={{ opacity: decisionHighlight, y: useTransform(scrollYProgress, [0.6, 1], [20, -20]) }}
               className="absolute inset-0 flex flex-col justify-center pointer-events-none"
             >
               <h3 className="text-3xl md:text-4xl font-serif font-bold text-white mb-5 tracking-tight">
                 Every recommendation is earned.
               </h3>
               <p className="text-slate-400 text-lg leading-relaxed max-w-md font-medium">
                 The AI doesn't generate candidates. It simply maps verified reality against your requirements. By the time a match is presented, the hard work of validation is already complete.
               </p>
             </motion.div>

          </div>

        </div>
      </motion.div>
    </section>
  );
}

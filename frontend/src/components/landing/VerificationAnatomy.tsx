import { motion, useScroll, useTransform } from 'framer-motion';
import { useRef } from 'react';

export function VerificationAnatomy() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"]
  });

  // Highlighting specific rows of the Intelligence Report as the user scrolls
  const identityHighlight = useTransform(scrollYProgress, [0, 0.2, 0.4, 0.5], [0, 1, 1, 0]);
  const evidenceHighlight = useTransform(scrollYProgress, [0.4, 0.5, 0.7, 0.8], [0, 1, 1, 0]);
  const decisionHighlight = useTransform(scrollYProgress, [0.7, 0.8, 1, 1], [0, 1, 1, 1]);

  return (
    <section ref={containerRef} className="h-[350vh] bg-[#FDFDFD] relative selection:bg-slate-200 selection:text-black">
      <div className="sticky top-0 h-screen w-full flex flex-col items-center justify-center overflow-hidden px-6 max-w-7xl mx-auto">
        
        <div className="absolute top-24 inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-50 border border-slate-200 shadow-sm">
          <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
          <span className="text-[10px] font-bold tracking-widest text-slate-500 uppercase">The Solution</span>
        </div>
        
        <div className="w-full flex flex-col lg:flex-row items-center gap-12 lg:gap-24 mt-16">
          
          {/* LEFT SIDE: The Intelligence Report Anchor */}
          <div className="w-full lg:w-1/2 relative">
             <div className="w-full bg-white shadow-[0_20px_60px_-15px_rgba(0,0,0,0.05)] border border-slate-200 rounded-xl overflow-hidden flex flex-col z-20">
                
                {/* Section 1: Identity */}
                <div className="relative flex flex-col md:flex-row border-b border-slate-100 overflow-hidden">
                   <motion.div style={{ opacity: identityHighlight }} className="absolute inset-0 bg-blue-50/40 -z-10" />
                   <div className="p-7 md:w-1/2 border-r border-slate-100 flex flex-col justify-center">
                      <div className="text-[10px] uppercase font-bold text-slate-400 tracking-widest mb-3">Verified Identity</div>
                      <div className="text-2xl font-serif font-bold text-slate-900 leading-none">Alex Rivera</div>
                      <div className="flex items-center gap-2 mt-3">
                         <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                         <span className="text-[9px] font-bold text-emerald-600 uppercase tracking-wide">Identity Confirmed</span>
                      </div>
                   </div>
                   <div className="p-7 md:w-1/2 flex flex-col justify-center">
                      <div className="text-[10px] uppercase font-bold text-slate-400 tracking-widest mb-3">Target Alignment</div>
                      <div className="text-base font-semibold text-slate-800">Senior Product Designer</div>
                   </div>
                </div>

                {/* Section 2: Experience */}
                <div className="relative p-7 border-b border-slate-100 overflow-hidden flex flex-col">
                   <motion.div style={{ opacity: evidenceHighlight }} className="absolute inset-0 bg-blue-50/40 -z-10" />
                   <div className="text-[10px] uppercase font-bold text-slate-400 tracking-widest mb-4">Evidence: Velocity & Impact</div>
                   <div className="space-y-4">
                      <div className="flex items-center gap-3">
                        <div className="w-4 h-4 rounded-full bg-emerald-100 flex items-center justify-center shrink-0">
                           <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        </div>
                        <div className="text-sm font-medium text-slate-700">Shipped 4 major fintech products</div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="w-4 h-4 rounded-full bg-emerald-100 flex items-center justify-center shrink-0">
                           <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        </div>
                        <div className="text-sm font-medium text-slate-700">Velocity &lt; 18 months</div>
                      </div>
                   </div>
                </div>

                {/* Section 3: Leadership & Scale */}
                <div className="relative flex flex-col md:flex-row border-b border-slate-100 overflow-hidden">
                   <motion.div style={{ opacity: evidenceHighlight }} className="absolute inset-0 bg-blue-50/40 -z-10" />
                   <div className="p-7 md:w-1/2 border-r border-slate-100 flex flex-col justify-center">
                      <div className="text-[10px] uppercase font-bold text-slate-400 tracking-widest mb-3">Evidence: Leadership</div>
                      <div className="text-sm font-semibold text-slate-800">Led Series B Design Team</div>
                   </div>
                   <div className="p-7 md:w-1/2 flex flex-col justify-center">
                      <div className="text-[10px] uppercase font-bold text-slate-400 tracking-widest mb-3">Evidence: Scale</div>
                      <div className="text-sm font-semibold text-slate-800">Verified $10M+ Scale</div>
                   </div>
                </div>

                {/* Section 4: Decision Ready */}
                <div className="relative p-7 bg-slate-900 text-white flex items-center justify-between overflow-hidden">
                   <motion.div style={{ opacity: decisionHighlight }} className="absolute inset-0 bg-blue-900/40 -z-10" />
                   <div className="flex items-center gap-3">
                      <div className="w-2.5 h-2.5 rounded-full bg-blue-500" style={{ boxShadow: '0 0 10px rgba(59, 130, 246, 0.5)' }} />
                      <span className="text-sm font-bold tracking-widest uppercase">Decision Ready</span>
                   </div>
                   <div className="flex gap-3 relative z-10">
                      <button className="px-5 py-2.5 bg-white/10 text-white rounded-md text-xs font-bold tracking-wide pointer-events-none">Dismiss</button>
                      <button className="px-5 py-2.5 bg-blue-600 text-white rounded-md text-xs font-bold tracking-wide pointer-events-none">Schedule Interview</button>
                   </div>
                </div>

             </div>
          </div>

          {/* RIGHT SIDE: The Deep Dive Text */}
          <div className="w-full lg:w-1/2 relative h-[400px]">
             
             {/* 1. Identity Explainer */}
             <motion.div 
               style={{ opacity: identityHighlight, y: useTransform(scrollYProgress, [0, 0.4], [20, -20]) }}
               className="absolute inset-0 flex flex-col justify-center"
             >
               <h3 className="text-3xl md:text-4xl font-serif font-bold text-slate-900 mb-5 tracking-tight">
                 We verify the human before the resume.
               </h3>
               <p className="text-slate-500 text-lg leading-relaxed max-w-md font-medium">
                 Every candidate on SmartOnboard must authenticate their identity. We enforce multi-factor OTP verification and DNS checks on work emails. You are talking to who you think you are talking to.
               </p>
             </motion.div>

             {/* 2. Evidence Explainer */}
             <motion.div 
               style={{ opacity: evidenceHighlight, y: useTransform(scrollYProgress, [0.3, 0.7], [20, -20]) }}
               className="absolute inset-0 flex flex-col justify-center pointer-events-none"
             >
               <h3 className="text-3xl md:text-4xl font-serif font-bold text-slate-900 mb-5 tracking-tight">
                 Every claim requires cross-referenced proof.
               </h3>
               <p className="text-slate-500 text-lg leading-relaxed max-w-md font-medium">
                 We don't accept "built scalable architecture" at face value. Our engine cross-references claimed timelines against public product releases, verified scale metrics, and peer-authenticated ledgers.
               </p>
             </motion.div>

             {/* 3. Decision Explainer */}
             <motion.div 
               style={{ opacity: decisionHighlight, y: useTransform(scrollYProgress, [0.6, 1], [20, -20]) }}
               className="absolute inset-0 flex flex-col justify-center pointer-events-none"
             >
               <h3 className="text-3xl md:text-4xl font-serif font-bold text-slate-900 mb-5 tracking-tight">
                 Every recommendation is earned.
               </h3>
               <p className="text-slate-500 text-lg leading-relaxed max-w-md font-medium">
                 The AI doesn't generate candidates. It simply maps verified reality against your requirements. By the time a match is presented, the hard work of validation is already complete.
               </p>
             </motion.div>

          </div>

        </div>
      </div>
    </section>
  );
}

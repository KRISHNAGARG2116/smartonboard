import { motion, useScroll, useTransform } from 'framer-motion';
import { useRef } from 'react';

export function HiringCrisis() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start end", "end start"]
  });

  // Dispersal transforms for various UI fragments to create "organized chaos"
  const y1 = useTransform(scrollYProgress, [0, 1], [100, -200]);
  const y2 = useTransform(scrollYProgress, [0, 1], [300, -100]);
  const y3 = useTransform(scrollYProgress, [0, 1], [0, -300]);
  const y4 = useTransform(scrollYProgress, [0, 1], [200, -250]);
  
  const rotate1 = useTransform(scrollYProgress, [0, 1], [-5, 10]);
  const rotate2 = useTransform(scrollYProgress, [0, 1], [12, -8]);
  const rotate3 = useTransform(scrollYProgress, [0, 1], [-15, -2]);

  return (
    <section ref={containerRef} className="h-[200vh] bg-slate-50 relative overflow-hidden border-b border-slate-200">
       <div className="sticky top-0 h-screen w-full flex flex-col items-center justify-center overflow-hidden">
          
          {/* Background Context */}
          <div className="absolute top-24 inline-flex items-center gap-2 px-3 py-1.5 rounded-sm bg-white border border-slate-200 shadow-sm z-50">
             <div className="w-1.5 h-1.5 rounded-sm bg-slate-400" />
             <span className="text-[10px] font-bold tracking-widest text-slate-500 uppercase font-mono">The Reality</span>
          </div>

          {/* Editorial Grid Texture */}
          <div className="absolute inset-0 pointer-events-none z-0">
             <div className="absolute inset-0 bg-[radial-gradient(#cbd5e1_1px,transparent_1px)] [background-size:24px_24px] opacity-40" />
             <div className="absolute left-6 lg:left-24 top-0 bottom-0 w-[1px] bg-slate-200" />
             <div className="absolute right-6 lg:right-24 top-0 bottom-0 w-[1px] bg-slate-200" />
          </div>

          {/* Title - Static */}
          <div className="z-10 text-center max-w-3xl px-6 pointer-events-none mt-[-10vh]">
             <h2 className="text-4xl md:text-5xl lg:text-7xl font-serif font-bold text-slate-900 tracking-tight leading-[1.05]">
                Hiring today is an exercise in fragmented chaos.
             </h2>
          </div>

          {/* The Fragments (The Chaos) */}
          <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
             
             {/* Fragment 1: ATS Dashboard */}
             <motion.div style={{ y: y1, rotate: rotate1 }} className="absolute -left-10 md:left-[10%] top-[20%] w-[280px] md:w-[320px] bg-white border border-slate-200 shadow-xl rounded-md p-4 opacity-90 backdrop-blur">
                <div className="text-[9px] font-mono text-slate-400 uppercase border-b border-slate-100 pb-2 mb-3">Legacy ATS Dashboard</div>
                <div className="space-y-2">
                   <div className="h-3 w-full bg-slate-100 rounded" />
                   <div className="h-3 w-4/5 bg-slate-100 rounded" />
                   <div className="h-3 w-full bg-slate-100 rounded" />
                   <div className="h-3 w-2/3 bg-slate-100 rounded" />
                </div>
                <div className="mt-4 flex gap-2">
                   <div className="px-2 py-1 bg-red-50 text-red-600 text-[10px] font-bold shadow-sm">142 UNREAD</div>
                   <div className="px-2 py-1 bg-amber-50 text-amber-600 text-[10px] font-bold shadow-sm">NEEDS REVIEW</div>
                </div>
             </motion.div>

             {/* Fragment 2: Messy Spreadsheet */}
             <motion.div style={{ y: y2, rotate: rotate2 }} className="absolute right-[-20px] md:right-[5%] top-[10%] w-[320px] md:w-[380px] bg-white border border-emerald-200 shadow-xl rounded-sm opacity-95">
                <div className="bg-emerald-50 border-b border-emerald-100 px-3 py-2 flex items-center gap-2">
                   <div className="w-2.5 h-2.5 bg-emerald-500 rounded-sm" />
                   <div className="text-[10px] font-bold text-emerald-800 tracking-wide">Q3_Candidates_Final_v4.xlsx</div>
                </div>
                <div className="p-3 grid grid-cols-4 gap-1 text-[8px] font-mono text-slate-400">
                   {[...Array(16)].map((_, i) => (
                      <div key={i} className="bg-slate-50 p-1.5 border border-slate-100 truncate">
                         {i % 4 === 0 ? 'NAME' : i % 3 === 0 ? '#REF!' : 'DATA'}
                      </div>
                   ))}
                </div>
             </motion.div>

             {/* Fragment 3: Slack/Messages */}
             <motion.div style={{ y: y3, rotate: rotate1 }} className="absolute left-[10%] md:left-[25%] bottom-[15%] w-[260px] md:w-[300px] bg-white border border-slate-200 shadow-2xl rounded-lg p-5 opacity-95">
                <div className="flex gap-3 items-start mb-4">
                   <div className="w-6 h-6 rounded-full bg-purple-100 border border-purple-200 shrink-0" />
                   <div>
                      <div className="text-xs font-bold text-slate-800">Hiring Manager</div>
                      <div className="text-[10px] text-slate-500 mt-1.5 leading-relaxed">"Did anyone verify if he actually led that team? His LinkedIn says something else."</div>
                   </div>
                </div>
                <div className="flex gap-3 items-start opacity-50">
                   <div className="w-6 h-6 rounded-full bg-blue-100 border border-blue-200 shrink-0" />
                   <div>
                      <div className="text-xs font-bold text-slate-800">Recruiter</div>
                      <div className="text-[10px] text-slate-500 mt-1.5">"I'll check the PDF again..."</div>
                   </div>
                </div>
             </motion.div>

             {/* Fragment 4: Stack of Resumes */}
             <motion.div style={{ y: y4, rotate: rotate3 }} className="absolute right-[10%] md:right-[20%] bottom-[5%] w-[200px] md:w-[240px] aspect-[1/1.4] bg-[#FCFBF9] border border-slate-300 shadow-2xl rounded-sm p-6 flex flex-col justify-between">
                <div className="space-y-3">
                   <div className="h-6 w-3/4 bg-slate-800" />
                   <div className="h-1.5 w-1/4 bg-slate-300 mb-6" />
                   <div className="h-1.5 w-full bg-slate-200" />
                   <div className="h-1.5 w-full bg-slate-200" />
                   <div className="h-1.5 w-5/6 bg-slate-200" />
                </div>
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rotate-[15deg] px-3 py-1 bg-white border-2 border-slate-900 text-slate-900 text-[10px] font-bold uppercase tracking-widest shadow-lg">
                   Rejected?
                </div>
             </motion.div>

          </div>
       </div>
    </section>
  );
}

import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useState } from 'react';

// Fast typewriter effect for the terminal phase
const FastTypewriter = ({ text, delay, onComplete }: { text: string, delay: number, onComplete?: () => void }) => {
  const [displayed, setDisplayed] = useState('');
  useEffect(() => {
    let i = 0;
    const t = setTimeout(() => {
      const interval = setInterval(() => {
        // Type 3 characters at a time for speed
        i += 3;
        setDisplayed(text.substring(0, i));
        if (i >= text.length) {
          clearInterval(interval);
          if (onComplete) onComplete();
        }
      }, 15);
      return () => clearInterval(interval);
    }, delay);
    return () => clearTimeout(t);
  }, [text, delay]);
  return <span>{displayed}</span>;
}

export function HeroSignature() {
  const [seq, setSeq] = useState(0);

  useEffect(() => {
    // 0: Initial state (Question types out)
    // 1: Reasoning streams
    // 2: Evidence locks
    // 3: Recommendation locks
    // 4: THE MORPH (Terminal -> Product)
    const t1 = setTimeout(() => setSeq(1), 800); 
    const t2 = setTimeout(() => setSeq(2), 1200);
    const t3 = setTimeout(() => setSeq(3), 1600);
    const t4 = setTimeout(() => setSeq(4), 2200); 
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); clearTimeout(t4); };
  }, []);

  return (
    <section className="relative w-full min-h-screen bg-[#FDFDFD] flex flex-col items-center pt-24 pb-20 px-6 overflow-hidden selection:bg-slate-200 selection:text-slate-900">
      
      {/* Background */}
      <div className="absolute inset-0 pointer-events-none z-0">
        <div className="absolute inset-0 opacity-[0.02] mix-blend-multiply" style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }} />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_60%_at_50%_50%,#000_70%,transparent_100%)]" />
      </div>

      {/* The Message */}
      <div className="relative z-10 w-full max-w-3xl mx-auto flex flex-col items-center text-center mb-16">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-slate-200 shadow-sm mb-6">
          <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
          <span className="text-[10px] font-bold tracking-wide text-slate-700 uppercase">The Verified Hiring Ecosystem</span>
        </div>

        <h1 className="text-[3rem] md:text-[4.25rem] font-bold tracking-tight text-slate-900 leading-[1.05] mb-5 font-serif">
          Intelligence built <br className="hidden md:block"/> on <span className="text-red-500">absolute truth.</span>
        </h1>
        
        <p className="text-base md:text-lg text-slate-500 mb-8 max-w-2xl leading-relaxed font-medium">
          SmartOnboard connects <span className="text-slate-800 font-semibold">verified professionals</span> with <span className="text-slate-800 font-semibold">exceptional companies</span> through irrefutable, evidence-based matching.
        </p>
      </div>

      {/* The Signature Interaction */}
      <div className="relative z-20 w-full max-w-5xl mx-auto flex items-center justify-center min-h-[400px]">
        
        <motion.div 
          layout
          initial={{ borderRadius: 16 }}
          animate={{
            backgroundColor: seq >= 4 ? '#ffffff' : '#0f172a',
            width: seq >= 4 ? '100%' : '550px',
            maxWidth: seq >= 4 ? '750px' : '550px',
            minHeight: seq >= 4 ? '350px' : '280px',
            boxShadow: seq >= 4 ? '0 25px 50px -12px rgba(0, 0, 0, 0.1), 0 0 0 1px rgba(0,0,0,0.05)' : '0 25px 50px -12px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255,255,255,0.1)'
          }}
          transition={{ type: "spring", bounce: 0, duration: 0.8 }}
          className="relative overflow-hidden flex flex-col"
        >
          <AnimatePresence mode="wait">
            
            {/* PHASE 1: THE TERMINAL (Intelligence) */}
            {seq < 4 && (
              <motion.div 
                key="terminal"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0, scale: 0.95, filter: 'blur(4px)' }}
                transition={{ duration: 0.4 }}
                className="absolute inset-0 p-6 font-mono flex flex-col justify-end gap-2"
              >
                {/* 0: Question */}
                <div className="text-slate-300 text-xs leading-relaxed mb-4">
                  <span className="text-blue-400 mr-2">›</span>
                  <FastTypewriter text="QUERY: Find a Senior Designer who shipped fintech infrastructure in under 18 months." delay={100} />
                </div>

                {/* 1: Reasoning */}
                {seq >= 1 && (
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="text-slate-500 text-[10px] space-y-1">
                    <div>[SYS] Scanning 247 verified profiles in network...</div>
                    <div className="text-slate-400">
                      <FastTypewriter text="[EVAL] Extracting contextual velocity metrics..." delay={0} />
                    </div>
                  </motion.div>
                )}

                {/* 2: Evidence */}
                {seq >= 2 && (
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="text-slate-400 text-[10px] space-y-1">
                    <div className="flex justify-between items-center pr-4">
                      <span>[EVIDENCE] Identity Authentication</span>
                      <span className="text-emerald-400">PASSED</span>
                    </div>
                    <div className="flex justify-between items-center pr-4">
                      <span>[EVIDENCE] Fintech Scale (Target: $5M+)</span>
                      <span className="text-emerald-400">VERIFIED ($10M+)</span>
                    </div>
                    <div className="flex justify-between items-center pr-4">
                      <span>[EVIDENCE] Velocity (Target: &lt;18mo)</span>
                      <span className="text-emerald-400">VERIFIED (14mo)</span>
                    </div>
                  </motion.div>
                )}

                {/* 3: Recommendation Lock */}
                {seq >= 3 && (
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-4 p-3 bg-blue-900/30 border border-blue-500/30 rounded flex items-center justify-between">
                    <div className="text-blue-300 text-xs font-bold uppercase tracking-widest">Match Confirmed</div>
                    <div className="text-emerald-400 text-xs font-bold">Confidence: 98%</div>
                  </motion.div>
                )}
              </motion.div>
            )}

            {/* PHASE 2: THE PRODUCT (Proof) */}
            {seq >= 4 && (
              <motion.div 
                key="product"
                initial={{ opacity: 0, scale: 1.05, filter: 'blur(4px)' }}
                animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
                transition={{ duration: 0.6, delay: 0.2 }}
                className="absolute inset-0 flex flex-col bg-white"
              >
                {/* Header */}
                <div className="w-full px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50 shrink-0">
                  <div className="flex items-center gap-2.5">
                    <div className="bg-white p-1 rounded-md border border-slate-200 shadow-sm">
                      <svg className="w-3.5 h-3.5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
                    </div>
                    <span className="text-[10px] font-bold uppercase tracking-widest text-slate-700">Verified Intelligence Report</span>
                  </div>
                  
                  <div className="px-2 py-0.5 rounded text-[9px] font-bold text-white bg-blue-600 uppercase tracking-wide shadow-sm flex items-center gap-1.5">
                    <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
                    Action Required
                  </div>
                </div>

                {/* Body */}
                <div className="flex-1 w-full grid grid-cols-1 md:grid-cols-12 gap-0">
                  
                  {/* Left: Entities */}
                  <div className="md:col-span-5 p-7 border-b md:border-b-0 md:border-r border-slate-100 flex flex-col justify-center relative bg-white">
                    <div className="mb-6">
                      <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Target Role</div>
                      <div className="text-xl font-serif font-bold text-slate-900 mb-1 leading-tight">Senior Product Designer</div>
                      <div className="text-[11px] text-slate-500 font-medium">Fintech Infrastructure</div>
                    </div>

                    <div className="relative w-full h-8 flex items-center mb-6">
                       <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-solid border-blue-200" /></div>
                       <div className="absolute left-1/2 -translate-x-1/2 w-8 h-8 rounded-full border border-blue-200 bg-blue-50 flex items-center justify-center z-10 shadow-sm">
                          <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 14l-7 7m0 0l-7-7m7 7V3" /></svg>
                       </div>
                    </div>

                    <div>
                      <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-3">Verified Candidate</div>
                      <div className="flex items-center gap-3 mb-4">
                        <div className="w-12 h-12 rounded-full bg-slate-50 border border-slate-200 flex items-center justify-center">
                          <span className="text-sm font-bold text-slate-700">AR</span>
                        </div>
                        <div>
                          <div className="text-xl font-serif font-bold text-slate-900 leading-tight mb-1">Alex Rivera</div>
                          <div className="flex items-center gap-1">
                            <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 rounded text-[8px] font-bold uppercase tracking-wide border border-emerald-100">ID Verified</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Right: Reasoning mapped from Terminal */}
                  <div className="md:col-span-7 p-7 bg-[#FAFAFA] flex flex-col justify-center">
                    <div className="flex items-end justify-between mb-8">
                       <div>
                         <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">Confidence Engine</div>
                         <div className="flex items-baseline gap-1">
                           <span className="text-6xl font-serif font-bold tracking-tight leading-none text-blue-600">98</span>
                           <span className="text-2xl font-serif font-bold text-slate-400">%</span>
                         </div>
                       </div>
                    </div>

                    <div className="space-y-4">
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5 w-6 h-6 rounded-full bg-white border border-slate-200 flex items-center justify-center shrink-0">
                           <svg className="w-3.5 h-3.5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                        </div>
                        <div>
                          <div className="text-[12px] font-bold text-slate-800">Demonstrated Velocity</div>
                          <div className="text-[11px] text-slate-500 font-medium">Candidate shipped 4 major fintech products in under 18 months, matching query constraints.</div>
                        </div>
                      </div>

                      <div className="flex items-start gap-3">
                        <div className="mt-0.5 w-6 h-6 rounded-full bg-white border border-slate-200 flex items-center justify-center shrink-0">
                           <svg className="w-3.5 h-3.5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
                        </div>
                        <div>
                          <div className="text-[12px] font-bold text-slate-800">Skill Authentication</div>
                          <div className="text-[11px] text-slate-500 font-medium">100% alignment on Systems Architecture and React verified by past employers.</div>
                        </div>
                      </div>
                    </div>

                  </div>
                </div>

                {/* Footer Actions */}
                <div className="w-full p-4 border-t border-slate-100 bg-white flex justify-end gap-3 mt-auto shrink-0">
                   <button className="px-4 py-1.5 rounded-md text-[11px] font-bold text-slate-500 hover:bg-slate-50 transition-colors">Dismiss</button>
                   <button className="px-4 py-1.5 rounded-md text-[11px] font-bold text-white bg-slate-900 hover:bg-slate-800 transition-colors">Schedule Interview</button>
                </div>
              </motion.div>
            )}
            
          </AnimatePresence>
        </motion.div>

      </div>
    </section>
  );
}

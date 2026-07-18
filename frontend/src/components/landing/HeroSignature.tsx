import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useState, useRef, useCallback } from 'react';

// Reusable component for the scattered floating state
const FloatingFragment = ({ layoutId, text, pos }: any) => (
  <motion.div
    layoutId={layoutId}
    initial={{ opacity: 0, scale: 0.9 }}
    animate={{ opacity: 1, scale: 1, top: pos.top, left: pos.left }}
    exit={{ opacity: 0, scale: 0.95 }}
    transition={{ type: "spring", bounce: 0, duration: 1.2 }}
    className="absolute font-mono text-[11px] px-3 py-1.5 bg-slate-50/80 text-slate-500 rounded border border-slate-200 shadow-sm whitespace-nowrap z-10 backdrop-blur-sm"
  >
    {text}
  </motion.div>
);

const generateRandomPositions = () => {
  // Spreading the fragments across a much wider horizontal and vertical space
  // Using zones to ensure they don't overlap completely, but look organically scattered
  return {
    name: { top: `${Math.random() * 20 + 5}%`, left: `${Math.random() * 20 - 15}%` }, // top far-left
    role: { top: `${Math.random() * 20 + 60}%`, left: `${Math.random() * 20 - 10}%` }, // bottom far-left
    exp1: { top: `${Math.random() * 20 + 15}%`, left: `${Math.random() * 20 + 80}%` }, // top far-right
    exp2: { top: `${Math.random() * 20 + 60}%`, left: `${Math.random() * 20 + 75}%` }, // bottom far-right
    lead: { top: `${Math.random() * 15 + 85}%`, left: `${Math.random() * 40 + 30}%` }, // bottom center
    scale: { top: `${Math.random() * 15 - 5}%`, left: `${Math.random() * 40 + 30}%` }, // top center
  };
};

export function HeroSignature() {
  const [seq, setSeq] = useState(-1);
  const [positions, setPositions] = useState(generateRandomPositions());
  const timeoutsRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearAllTimeouts = useCallback(() => {
    timeoutsRef.current.forEach(clearTimeout);
    timeoutsRef.current = [];
  }, []);

  const playSequence = useCallback(() => {
    clearAllTimeouts();
    setPositions(generateRandomPositions());
    setSeq(0); // 0: Scattered fragments
    
    timeoutsRef.current.push(setTimeout(() => setSeq(1), 1000)); // Identity
    timeoutsRef.current.push(setTimeout(() => setSeq(2), 2200)); // Experience
    timeoutsRef.current.push(setTimeout(() => setSeq(3), 3400)); // Leadership & Scale
    timeoutsRef.current.push(setTimeout(() => setSeq(4), 4600)); // Decision Ready
    timeoutsRef.current.push(setTimeout(() => setSeq(5), 5500)); // Complete Stillness
    
    // Breathing cycle: Hold stillness for 4s
    timeoutsRef.current.push(setTimeout(() => setSeq(-1), 9500)); // Graceful dissolve
    
    // Replay after dissolve
    timeoutsRef.current.push(setTimeout(() => playSequence(), 10500)); 
  }, [clearAllTimeouts]);

  useEffect(() => {
    playSequence();
    return clearAllTimeouts;
  }, [playSequence, clearAllTimeouts]);

  const handleReplay = () => {
    if (seq === 5) {
      setSeq(-1); // Instantly trigger dissolve
      setTimeout(() => playSequence(), 600); // Wait for fade out, then restart
    }
  };

  return (
    <section className="relative w-full min-h-screen bg-[#FDFDFD] flex flex-col items-center pt-24 pb-20 px-6 overflow-hidden selection:bg-slate-200 selection:text-slate-900">
      
      {/* Background Atmosphere */}
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

      {/* The Signature Interaction: Truth Forming */}
      {/* We use an AnimatePresence wrapping the whole assembly area for the graceful dissolve (seq === -1) */}
      <div className="relative z-20 w-full max-w-5xl mx-auto min-h-[500px] flex items-center justify-center">
        <AnimatePresence>
          {seq >= 0 && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.6 }}
              className="absolute inset-0 w-full h-full flex items-center justify-center"
            >
              {/* SCATTERED EVIDENCE LAYER */}
              <div className="absolute inset-0 pointer-events-none">
                <AnimatePresence>
                  {/* Identity */}
                  {seq < 1 && <FloatingFragment key="f-name" layoutId="frag-name" text="Alex Rivera" pos={positions.name} />}
                  {seq < 1 && <FloatingFragment key="f-role" layoutId="frag-role" text="Senior Product Designer" pos={positions.role} />}
                  
                  {/* Experience */}
                  {seq < 2 && <FloatingFragment key="f-exp1" layoutId="frag-exp1" text="Shipped 4 major fintech products" pos={positions.exp1} />}
                  {seq < 2 && <FloatingFragment key="f-exp2" layoutId="frag-exp2" text="Velocity < 18 months" pos={positions.exp2} />}
                  
                  {/* Leadership & Scale */}
                  {seq < 3 && <FloatingFragment key="f-lead" layoutId="frag-lead" text="Led Series B Design Team" pos={positions.lead} />}
                  {seq < 3 && <FloatingFragment key="f-scale" layoutId="frag-scale" text="Verified $10M+ Scale" pos={positions.scale} />}
                </AnimatePresence>
              </div>

              {/* THE STRUCTURED CONTAINER */}
              {/* Added onMouseEnter to trigger replay if the user hovers during the stillness phase */}
              <motion.div 
                layout
                onMouseEnter={handleReplay}
                initial={{ borderRadius: 16 }}
                className="relative w-full max-w-2xl bg-white shadow-xl border border-slate-200 overflow-hidden flex flex-col z-20 cursor-default"
              >
                 {/* Replay indicator (Subtle, only visible when complete) */}
                 <AnimatePresence>
                   {seq >= 5 && (
                     <motion.div 
                       initial={{ opacity: 0 }} 
                       animate={{ opacity: 1 }} 
                       exit={{ opacity: 0 }}
                       className="absolute top-4 right-4 z-50 pointer-events-none flex items-center gap-1.5 text-slate-300"
                     >
                       <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                     </motion.div>
                   )}
                 </AnimatePresence>

                 {/* Section 1: Identity (Earned at seq 1) */}
                 <AnimatePresence mode="popLayout">
                   {seq >= 1 && (
                     <motion.div 
                       initial={{ opacity: 0 }}
                       animate={{ opacity: 1 }}
                       className="flex flex-col md:flex-row border-b border-slate-100 overflow-hidden"
                     >
                       {/* Name */}
                       <div className="p-7 md:w-1/2 border-r border-slate-100 flex flex-col justify-center">
                          <div className="text-[10px] uppercase font-bold text-slate-400 tracking-widest mb-3">Verified Identity</div>
                          <motion.div 
                            layoutId="frag-name" 
                            className="text-2xl font-serif font-bold text-slate-900 leading-none"
                          >
                            Alex Rivera
                          </motion.div>
                          <div className="flex items-center gap-2 mt-3">
                             <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                             <span className="text-[9px] font-bold text-emerald-600 uppercase tracking-wide">Identity Confirmed</span>
                          </div>
                       </div>
                       
                       {/* Role */}
                       <div className="p-7 md:w-1/2 bg-slate-50/50 flex flex-col justify-center">
                          <div className="text-[10px] uppercase font-bold text-slate-400 tracking-widest mb-3">Target Alignment</div>
                          <motion.div 
                            layoutId="frag-role" 
                            className="text-base font-semibold text-slate-800"
                          >
                            Senior Product Designer
                          </motion.div>
                       </div>
                     </motion.div>
                   )}
                 </AnimatePresence>

                 {/* Section 2: Experience (Earned at seq 2) */}
                 <AnimatePresence mode="popLayout">
                   {seq >= 2 && (
                     <motion.div 
                       initial={{ opacity: 0 }}
                       animate={{ opacity: 1 }}
                       className="p-7 border-b border-slate-100 overflow-hidden flex flex-col"
                     >
                       <div className="text-[10px] uppercase font-bold text-slate-400 tracking-widest mb-4">Evidence: Velocity & Impact</div>
                       <div className="space-y-4">
                          <div className="flex items-center gap-3">
                            <div className="w-4 h-4 rounded-full bg-emerald-100 flex items-center justify-center shrink-0">
                               <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                            </div>
                            <motion.div 
                              layoutId="frag-exp1" 
                              className="text-sm font-medium text-slate-700"
                            >
                              Shipped 4 major fintech products
                            </motion.div>
                          </div>
                          <div className="flex items-center gap-3">
                            <div className="w-4 h-4 rounded-full bg-emerald-100 flex items-center justify-center shrink-0">
                               <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                            </div>
                            <motion.div 
                              layoutId="frag-exp2" 
                              className="text-sm font-medium text-slate-700"
                            >
                              Velocity &lt; 18 months
                            </motion.div>
                          </div>
                       </div>
                     </motion.div>
                   )}
                 </AnimatePresence>

                 {/* Section 3: Leadership & Scale (Earned at seq 3) */}
                 <AnimatePresence mode="popLayout">
                   {seq >= 3 && (
                     <motion.div 
                       initial={{ opacity: 0 }}
                       animate={{ opacity: 1 }}
                       className="flex flex-col md:flex-row border-b border-slate-100 overflow-hidden"
                     >
                       <div className="p-7 md:w-1/2 border-r border-slate-100 bg-slate-50/50 flex flex-col justify-center">
                          <div className="text-[10px] uppercase font-bold text-slate-400 tracking-widest mb-3">Evidence: Leadership</div>
                          <motion.div 
                            layoutId="frag-lead" 
                            className="text-sm font-semibold text-slate-800"
                          >
                            Led Series B Design Team
                          </motion.div>
                       </div>
                       <div className="p-7 md:w-1/2 flex flex-col justify-center">
                          <div className="text-[10px] uppercase font-bold text-slate-400 tracking-widest mb-3">Evidence: Scale</div>
                          <motion.div 
                            layoutId="frag-scale" 
                            className="text-sm font-semibold text-slate-800"
                          >
                            Verified $10M+ Scale
                          </motion.div>
                       </div>
                     </motion.div>
                   )}
                 </AnimatePresence>

                 {/* Section 4: Decision Ready (Earned at seq 4) */}
                 <AnimatePresence mode="popLayout">
                   {seq >= 4 && (
                     <motion.div 
                       initial={{ opacity: 0 }}
                       animate={{ opacity: 1 }}
                       className="p-7 bg-slate-900 text-white flex items-center justify-between overflow-hidden"
                     >
                       <div className="flex items-center gap-3">
                          <div 
                            className="w-2.5 h-2.5 rounded-full bg-blue-500 transition-all duration-300" 
                            style={{ 
                              animation: seq === 4 ? 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite' : 'none',
                              boxShadow: seq >= 5 ? '0 0 10px rgba(59, 130, 246, 0.5)' : 'none'
                            }} 
                          />
                          <span className="text-sm font-bold tracking-widest uppercase">Decision Ready</span>
                       </div>
                       
                       {seq >= 5 && (
                          <motion.div 
                            initial={{ opacity: 0, x: 10 }} 
                            animate={{ opacity: 1, x: 0 }} 
                            className="flex gap-3 relative z-10"
                          >
                             <button className="px-5 py-2.5 bg-white/10 hover:bg-white/20 text-white rounded-md text-xs font-bold tracking-wide transition-colors">
                               Dismiss
                             </button>
                             <button className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-xs font-bold tracking-wide transition-colors">
                               Schedule Interview
                             </button>
                          </motion.div>
                       )}
                     </motion.div>
                   )}
                 </AnimatePresence>

              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(0.8); }
        }
      `}</style>
    </section>
  );
}

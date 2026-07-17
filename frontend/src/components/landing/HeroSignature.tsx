import { motion, AnimatePresence, useInView } from 'framer-motion';
import { useEffect, useState, useRef } from 'react';

// --- SYSTEM EVENTS LIBRARY (Orbiting Widgets) ---
// Now with internal animations (pulsing, filling, ticking).

const EventMatch = () => (
  <div className="bg-white/95 backdrop-blur-md p-3 rounded-xl shadow-[0_4px_20px_rgba(10,37,64,0.08),0_1px_3px_rgba(10,37,64,0.04)] border border-slate-200/80 flex items-center gap-3">
    <div className="relative w-8 h-8 rounded-full bg-[#0A2540]/5 flex items-center justify-center shrink-0">
      <svg className="absolute inset-0 w-full h-full -rotate-90 text-[#0A2540]" viewBox="0 0 36 36">
        <path className="text-slate-100" strokeWidth="3" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
        <motion.path 
          initial={{ strokeDasharray: "0, 100" }} 
          animate={{ strokeDasharray: "98, 100" }} 
          transition={{ duration: 2, ease: "easeOut", repeat: Infinity, repeatType: "loop", repeatDelay: 5 }}
          strokeWidth="3" stroke="currentColor" fill="none" 
          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" 
        />
      </svg>
      <span className="text-[9px] font-bold text-[#0A2540]">98%</span>
    </div>
    <div className="pr-2">
      <div className="text-[11px] font-bold text-slate-900 leading-tight">Exceptional Match</div>
      <div className="text-[10px] text-slate-500">Skills align perfectly</div>
    </div>
  </div>
);

const EventCollab = () => (
  <div className="bg-white/95 backdrop-blur-md p-3 rounded-xl shadow-[0_4px_20px_rgba(10,37,64,0.08),0_1px_3px_rgba(10,37,64,0.04)] border border-slate-200/80 flex items-start gap-3 w-[220px]">
    <div className="relative w-6 h-6 shrink-0">
      <motion.div 
        animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0, 0.5] }} 
        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }} 
        className="absolute inset-0 bg-purple-400 rounded-full" 
      />
      <div className="absolute inset-0 rounded-full bg-purple-100 flex items-center justify-center border border-purple-200">
        <span className="text-[9px] font-bold text-purple-700">DK</span>
      </div>
    </div>
    <div>
      <div className="text-[10px] font-bold text-slate-900 mb-0.5">David K. <span className="text-slate-400 font-normal ml-1">Hiring Manager</span></div>
      <motion.div 
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5, duration: 1 }}
        className="text-[11px] text-purple-900/80 font-medium leading-snug"
      >
        "Let's fast-track this candidate."
      </motion.div>
    </div>
  </div>
);

const EventScheduled = () => (
  <div className="bg-emerald-50/95 backdrop-blur-md p-3 rounded-xl shadow-[0_4px_20px_rgba(16,185,129,0.08),0_1px_3px_rgba(16,185,129,0.04)] border border-emerald-200/60 flex items-center gap-3">
    <motion.div 
      animate={{ rotate: [0, 15, -15, 0] }}
      transition={{ duration: 1, repeat: Infinity, repeatDelay: 3 }}
      className="w-6 h-6 rounded-full bg-emerald-100 flex items-center justify-center shrink-0"
    >
      <svg className="w-3.5 h-3.5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
    </motion.div>
    <div className="pr-2">
      <div className="text-[11px] font-bold text-emerald-900 leading-tight">Interview Scheduled</div>
      <div className="text-[10px] text-emerald-700 font-medium">Tomorrow, 2:00 PM EST</div>
    </div>
  </div>
);

const EventInsight = () => (
  <div className="bg-[#0A2540]/95 backdrop-blur-md p-3 rounded-xl shadow-[0_8px_25px_rgba(10,37,64,0.2)] border border-[#0A2540] flex items-center gap-3 w-[200px]">
    <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center shrink-0">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
        <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-400"></span>
      </span>
    </div>
    <div>
      <div className="text-[10px] font-bold text-blue-200 uppercase tracking-widest mb-0.5">AI Insight</div>
      <div className="text-[11px] text-white font-medium leading-tight">Strong systems architecture background detected.</div>
    </div>
  </div>
);

const EventVelocity = () => (
  <div className="bg-white/95 backdrop-blur-md p-3 rounded-xl shadow-[0_4px_20px_rgba(10,37,64,0.08),0_1px_3px_rgba(10,37,64,0.04)] border border-slate-200/80 flex items-center gap-3">
    <div className="flex gap-1 shrink-0 items-end h-4 w-5">
      <motion.div animate={{ height: ["4px", "8px", "4px"] }} transition={{ duration: 2, repeat: Infinity }} className="w-1.5 bg-blue-200 rounded-sm" />
      <motion.div animate={{ height: ["8px", "16px", "8px"] }} transition={{ duration: 2.2, repeat: Infinity }} className="w-1.5 bg-blue-400 rounded-sm" />
      <motion.div animate={{ height: ["16px", "24px", "16px"] }} transition={{ duration: 1.8, repeat: Infinity }} className="w-1.5 bg-blue-600 rounded-sm" />
    </div>
    <div className="pr-2 pl-1">
      <div className="text-[11px] font-bold text-slate-900 leading-tight">Hiring Velocity</div>
      <div className="text-[10px] text-emerald-600 font-bold">Time-to-hire -4 days</div>
    </div>
  </div>
);

// --- MAIN CENTRAL VIEWS (The Core Operating System) ---

const ViewCandidate = () => (
  <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.4 }} className="w-full h-full flex flex-col justify-center">
    <div className="flex justify-between items-start mb-6">
      <div className="flex gap-4 items-center">
        <div className="w-12 h-12 rounded-full bg-indigo-50 border border-indigo-100 flex items-center justify-center shrink-0">
          <span className="text-sm font-bold text-indigo-700">AR</span>
        </div>
        <div>
          <h3 className="font-bold text-xl text-slate-900 tracking-tight mb-0.5">Alex Rivera</h3>
          <p className="text-xs text-slate-500 font-medium">Senior Product Designer</p>
        </div>
      </div>
      <button className="px-5 py-2.5 bg-emerald-600 text-white text-xs font-semibold rounded-lg shadow-[0_2px_10px_rgba(16,185,129,0.15),inset_0_1px_0_rgba(255,255,255,0.2)]">Approve</button>
    </div>
    <div className="relative pl-6 border-l-[3px] border-[#0A2540]/10 mb-6">
      <div className="absolute -left-[10px] top-0 w-4 h-4 rounded-full bg-white border-[3px] border-[#0A2540] flex items-center justify-center shadow-sm">
        <div className="w-1.5 h-1.5 bg-[#0A2540] rounded-full animate-pulse" />
      </div>
      <div className="text-[11px] font-bold text-[#0A2540] uppercase tracking-widest mb-3">AI Contextual Reasoning</div>
      <ul className="space-y-4">
        <li className="flex gap-3 items-start">
          <svg className="w-4 h-4 text-[#0A2540]/40 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
          <span className="font-serif text-slate-700 text-[14px] leading-relaxed">Built engineering and design teams from 5 → 60 people</span>
        </li>
        <li className="flex gap-3 items-start">
          <svg className="w-4 h-4 text-[#0A2540]/40 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
          <span className="font-serif text-slate-700 text-[14px] leading-relaxed">Strong leadership evidence in fast-paced environments</span>
        </li>
      </ul>
    </div>
    <div className="bg-amber-50/50 border border-amber-200/50 rounded-xl p-4 flex gap-3 items-start">
      <svg className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
      <div>
        <div className="text-[10px] font-bold text-amber-600 uppercase tracking-widest mb-1">Potential Concern</div>
        <div className="font-serif text-[13px] text-amber-900 italic">Limited enterprise hiring experience</div>
      </div>
    </div>
  </motion.div>
);

const ViewPipeline = () => (
  <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.4 }} className="w-full h-full flex flex-col justify-center">
    <div className="flex justify-between items-end mb-5">
      <div>
        <h3 className="font-bold text-xl text-slate-900 tracking-tight">Engineering Pipeline</h3>
        <p className="text-sm text-slate-500 font-medium">12 Active Candidates</p>
      </div>
      <div className="flex items-center gap-1.5 text-[11px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-100 px-2.5 py-1 rounded-md shadow-sm">
        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> Live Sync
      </div>
    </div>
    <div className="flex gap-4">
      {/* Stage 1 */}
      <div className="flex-1 bg-slate-50/50 rounded-xl border border-slate-200/60 p-2.5 flex flex-col gap-2.5">
        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1.5">AI Screen (8)</div>
        <div className="bg-white p-3 rounded-lg shadow-[0_1px_2px_rgba(0,0,0,0.05)] border border-slate-200/80 text-xs font-semibold text-slate-500 flex justify-between items-center opacity-70">
          T. Moore <span className="text-rose-500">42%</span>
        </div>
      </div>
      {/* Stage 2 */}
      <div className="flex-1 bg-slate-50/50 rounded-xl border border-slate-200/60 p-2.5 flex flex-col gap-2.5">
        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1.5">Tech Screen (3)</div>
        <motion.div initial={{ y: -10, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.5 }} className="bg-white p-3 rounded-lg shadow-[0_4px_12px_rgba(10,37,64,0.05)] border border-[#0A2540]/10 ring-1 ring-[#0A2540]/5 text-xs font-semibold text-slate-900 flex justify-between items-center">
          S. Jenkins <span className="text-[#0A2540]">95%</span>
        </motion.div>
      </div>
      {/* Stage 3 */}
      <div className="flex-1 bg-slate-50/50 rounded-xl border border-slate-200/60 p-2.5 flex flex-col gap-2.5">
        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1.5">Final (1)</div>
        <motion.div initial={{ scale: 0.95 }} animate={{ scale: 1 }} transition={{ repeat: Infinity, repeatType: "reverse", duration: 2 }} className="bg-white p-3 rounded-lg shadow-[0_4px_12px_rgba(16,185,129,0.08)] border-l-[3px] border-emerald-500 text-xs font-bold text-slate-900 flex flex-col gap-1.5">
          <div className="flex justify-between items-center">A. Rivera <span className="text-emerald-600">98%</span></div>
          <div className="text-[10px] text-emerald-600/80 font-medium tracking-wide">Interview Scheduled</div>
        </motion.div>
      </div>
    </div>
  </motion.div>
);

const ViewAnalytics = () => (
  <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.4 }} className="w-full h-full flex flex-col justify-center">
    <div className="mb-7 relative z-10">
      <h3 className="font-bold text-xl text-slate-900 tracking-tight mb-1">Skill Alignment</h3>
      <p className="text-sm text-slate-500 font-medium">Alex Rivera vs. Senior Product Designer JD</p>
    </div>
    <div className="space-y-4 relative z-10">
      {[
        { skill: 'Systems Design', score: 98, color: 'bg-[#0A2540]' },
        { skill: 'React / Frontend', score: 85, color: 'bg-[#0A2540]/80' },
        { skill: 'Enterprise SaaS', score: 40, color: 'bg-amber-400' },
      ].map((item, i) => (
        <div key={i}>
          <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1.5">
            <span>{item.skill}</span>
            <span>{item.score}%</span>
          </div>
          <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <motion.div initial={{ width: 0 }} animate={{ width: `${item.score}%` }} transition={{ duration: 1, delay: i * 0.1, ease: "easeOut" }} className={`h-full ${item.color}`} />
          </div>
        </div>
      ))}
    </div>
  </motion.div>
);

const CENTRAL_VIEWS = [
  { id: 'candidate', component: ViewCandidate },
  { id: 'pipeline', component: ViewPipeline },
  { id: 'analytics', component: ViewAnalytics },
];

export function HeroSignature() {
  const containerRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(containerRef, { amount: 0.3, once: false });

  const [hasPlayedIntro, setHasPlayedIntro] = useState(false);
  const [showChaos, setShowChaos] = useState(true);
  
  const [activeViewIndex, setActiveViewIndex] = useState(0);
  
  // 1. Initial Hook (247 -> 1)
  useEffect(() => {
    if (isInView && !hasPlayedIntro) {
      setShowChaos(true);
      const chaosTimer = setTimeout(() => {
        setShowChaos(false);
        setHasPlayedIntro(true);
      }, 1500);
      return () => clearTimeout(chaosTimer);
    }
  }, [isInView, hasPlayedIntro]);

  // 2. Central Carousel Rotation (The original animated widget)
  useEffect(() => {
    if (!hasPlayedIntro) return;
    const loop = setInterval(() => {
      setActiveViewIndex(prev => (prev + 1) % CENTRAL_VIEWS.length);
    }, 1400); // 1.4s per central view (0.4s transition + 1.0s visible)
    return () => clearInterval(loop);
  }, [hasPlayedIntro]);

  const ActiveComponent = CENTRAL_VIEWS[activeViewIndex].component;

  return (
    <section 
      ref={containerRef}
      className="relative w-full min-h-[90vh] bg-[#FBFBFB] flex flex-col items-center justify-center pt-32 pb-20 px-6 overflow-hidden selection:bg-[#0A2540]/10 selection:text-[#0A2540]"
    >
      {/* Background Atmosphere */}
      <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/4 -translate-y-1/2 w-[800px] h-[800px] bg-indigo-900/[0.015] blur-[100px] rounded-full" />
        <div className="absolute bottom-0 right-0 w-[600px] h-[600px] bg-blue-900/[0.02] blur-[120px] rounded-full" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#e2e8f0_1px,transparent_1px),linear-gradient(to_bottom,#e2e8f0_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_80%_60%_at_50%_50%,#000_20%,transparent_100%)] opacity-[0.15]" />
      </div>

      <div className="relative z-10 w-full max-w-7xl mx-auto flex flex-col lg:flex-row items-center gap-14 lg:gap-24">
        
        {/* Left Column: Messaging */}
        <div className="flex-1 flex flex-col items-start text-left max-w-2xl relative z-20">
          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            className="text-[3.25rem] md:text-6xl lg:text-[4.5rem] font-bold tracking-tight text-slate-900 leading-[1.05] mb-7"
          >
            Hire the right candidate.<br />
            <span className="text-slate-700">In minutes, not days.</span>
          </motion.h1>
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="text-lg md:text-xl text-slate-600 mb-10 max-w-lg leading-[1.7] font-light"
          >
            Review every application. Understand every recommendation. Hire the right candidate—in minutes, not days.
          </motion.p>
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-wrap items-center gap-4"
          >
            <button className="px-8 py-3.5 bg-[#0A2540] text-white font-medium rounded-lg hover:bg-[#0A2540]/90 transition-all shadow-[0_2px_10px_rgba(10,37,64,0.15),inset_0_1px_0_rgba(255,255,255,0.15)] ring-1 ring-inset ring-[#0A2540] cursor-pointer text-[17px] tracking-wide">
              Book a Demo
            </button>
            <button className="px-8 py-3.5 bg-white text-slate-700 font-medium rounded-lg border border-slate-200/80 hover:bg-slate-50 transition-all shadow-[0_1px_2px_rgba(0,0,0,0.05)] cursor-pointer text-[17px] tracking-wide">
              Explore Platform
            </button>
          </motion.div>
        </div>

        {/* Right Column: The OS Carousel + Orbiting Ecosystem */}
        <div className="flex-1 w-full relative min-h-[500px] flex items-center justify-center cursor-default shrink-0">
          
          {/* THE CENTRAL OS (Restored Carousel) */}
          <div className="relative z-10 w-full max-w-[440px] bg-white/95 backdrop-blur-xl rounded-[20px] shadow-[0_40px_80px_-20px_rgba(10,37,64,0.1),0_0_0_1px_rgba(10,37,64,0.02)] border border-slate-200/60 ring-1 ring-white/60 ring-inset flex flex-col mx-auto">
            
            <div className="h-11 border-b border-slate-100/80 bg-slate-50/50 rounded-t-[20px] flex items-center px-4.5 gap-2 shrink-0">
              <div className="w-2.5 h-2.5 rounded-full bg-slate-300/80" />
              <div className="w-2.5 h-2.5 rounded-full bg-slate-300/80" />
              <div className="w-2.5 h-2.5 rounded-full bg-slate-300/80" />
              <div className="ml-auto flex items-center gap-3">
                 <div className="flex gap-1.5 mr-2">
                   {CENTRAL_VIEWS.map((_, i) => (
                     <div key={i} className={`w-1.5 h-1.5 rounded-full transition-all ${i === activeViewIndex ? 'bg-[#0A2540]' : 'bg-slate-200'}`} />
                   ))}
                 </div>
                 <div className="text-[9px] font-mono text-slate-400 uppercase tracking-widest font-semibold flex items-center gap-2">
                   <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                   System Active
                 </div>
              </div>
            </div>

            <div className="p-7 relative overflow-hidden bg-[#FAFAFA] rounded-b-[20px] min-h-[340px] flex items-center">
              <AnimatePresence mode="wait">
                {!hasPlayedIntro && showChaos && (
                  <motion.div 
                    key="chaos"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95, filter: "blur(12px)" }}
                    transition={{ duration: 0.5 }}
                    className="absolute inset-0 flex flex-col items-center justify-center gap-6 p-8 bg-slate-50 z-50"
                  >
                    <div className="grid grid-cols-6 gap-2 w-full max-w-[280px] opacity-30">
                      {[...Array(42)].map((_, i) => (
                        <div key={i} className={`h-6 rounded border shadow-sm ${i % 7 === 0 ? 'bg-indigo-200 border-indigo-300' : 'bg-slate-300 border-slate-400'}`} />
                      ))}
                    </div>
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white/95 backdrop-blur-md px-10 py-5 rounded-2xl shadow-[0_20px_40px_-15px_rgba(0,0,0,0.1)] border border-slate-200/80 ring-1 ring-white/50 ring-inset flex flex-col items-center">
                      <span className="text-[2.5rem] font-bold text-slate-900 tracking-tight leading-none mb-2">247</span>
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">Applications</span>
                    </div>
                  </motion.div>
                )}
                {hasPlayedIntro && (
                   <ActiveComponent key={activeViewIndex} />
                )}
              </AnimatePresence>
            </div>
          </div>

          {/* THE ORBITING ECOSYSTEM (Static, Immediately Visible Micro-Widgets) */}
          {hasPlayedIntro && (
            <div className="absolute inset-0 pointer-events-none z-0">
               {/* 5 Distinct widgets placed perfectly around the anchor */}
               <motion.div 
                 initial={{ opacity: 0, scale: 0.95, y: 10 }}
                 animate={{ opacity: 1, scale: 1, y: 0 }}
                 transition={{ duration: 0.6, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
                 className="absolute -top-6 -left-12 lg:-left-24"
               >
                 <EventMatch />
               </motion.div>

               <motion.div 
                 initial={{ opacity: 0, scale: 0.95, y: 10 }}
                 animate={{ opacity: 1, scale: 1, y: 0 }}
                 transition={{ duration: 0.6, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
                 className="absolute -top-4 -right-8 lg:-right-20"
               >
                 <EventScheduled />
               </motion.div>

               <motion.div 
                 initial={{ opacity: 0, scale: 0.95, y: 10 }}
                 animate={{ opacity: 1, scale: 1, y: 0 }}
                 transition={{ duration: 0.6, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
                 className="absolute top-[40%] -left-16 lg:-left-32"
               >
                 <EventCollab />
               </motion.div>

               <motion.div 
                 initial={{ opacity: 0, scale: 0.95, y: 10 }}
                 animate={{ opacity: 1, scale: 1, y: 0 }}
                 transition={{ duration: 0.6, delay: 0.7, ease: [0.16, 1, 0.3, 1] }}
                 className="absolute top-[60%] -right-10 lg:-right-24"
               >
                 <EventInsight />
               </motion.div>

               <motion.div 
                 initial={{ opacity: 0, scale: 0.95, y: 10 }}
                 animate={{ opacity: 1, scale: 1, y: 0 }}
                 transition={{ duration: 0.6, delay: 0.9, ease: [0.16, 1, 0.3, 1] }}
                 className="absolute -bottom-8 -left-4 lg:-left-16"
               >
                 <EventVelocity />
               </motion.div>
            </div>
          )}

        </div>
      </div>
    </section>
  );
}

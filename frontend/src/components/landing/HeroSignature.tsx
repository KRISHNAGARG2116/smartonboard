import { motion, AnimatePresence, useInView } from 'framer-motion';
import { useEffect, useState, useRef } from 'react';

// Using Semantic Colors: Blue (AI), Green (Success), Amber (Pending), Red (Risk), Purple (Collab)
const CANDIDATES = [
  {
    id: 1,
    initials: 'AR',
    name: 'Alex Rivera',
    role: 'Senior Product Designer',
    match: '98%',
    status: 'pending', // Amber
    reasoning: [
      'Built engineering and design teams from 5 → 60 people',
      'Strong leadership evidence in fast-paced environments',
      '94% skill alignment with the job description'
    ],
    concern: 'Limited enterprise hiring experience',
    collab: 'Hiring Manager: "Love the portfolio. Let\'s fast-track." - 2m ago'
  },
  {
    id: 2,
    initials: 'SJ',
    name: 'Sarah Jenkins',
    role: 'Lead Frontend Engineer',
    match: '95%',
    status: 'approved', // Green
    reasoning: [
      'Architected scalable React systems for 3+ years',
      'Reduced initial load times by 40% in previous role',
      'Deep expertise in performance and accessibility'
    ],
    concern: 'Prefers 100% remote work',
    collab: 'Approved by Tech Lead - 15m ago'
  },
  {
    id: 3,
    initials: 'MK',
    name: 'Marcus Kim',
    role: 'Product Marketing Manager',
    match: '72%',
    status: 'rejected', // Red
    reasoning: [
      'Successfully launched 4 tier-1 SaaS products',
      'Exceptional copywriting portfolio'
    ],
    concern: 'Missing required B2B enterprise experience (Required: 5 yrs)',
    collab: 'System: Automatically flagged for missing core requirement.'
  }
];

export function HeroSignature() {
  const containerRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(containerRef, { amount: 0.3, once: false });

  const [hasPlayedIntro, setHasPlayedIntro] = useState(false);
  const [showChaos, setShowChaos] = useState(true);
  
  // Carousel State
  const [activeIndex, setActiveIndex] = useState(0);
  const [isInteracting, setIsInteracting] = useState(false);
  const interactionTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const autoplayIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 1. Initial Introduction Sequence (247 -> 1)
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

  // 2. Carousel Autoplay Logic (Living OS)
  useEffect(() => {
    if (hasPlayedIntro && !isInteracting) {
      autoplayIntervalRef.current = setInterval(() => {
        setActiveIndex((prev) => (prev + 1) % CANDIDATES.length);
      }, 5000); // Cycle every 5s to feel alive
    }

    return () => {
      if (autoplayIntervalRef.current) {
        clearInterval(autoplayIntervalRef.current);
      }
    };
  }, [hasPlayedIntro, isInteracting]);

  // Handle User Interaction
  const handleInteraction = () => {
    setIsInteracting(true);
    if (interactionTimeoutRef.current) clearTimeout(interactionTimeoutRef.current);
    interactionTimeoutRef.current = setTimeout(() => {
      setIsInteracting(false);
    }, 8000);
  };

  const activeCandidate = CANDIDATES[activeIndex];

  return (
    <section 
      ref={containerRef}
      className="relative w-full min-h-[90vh] bg-[#FBFBFB] flex flex-col items-center justify-center pt-32 pb-20 px-6 overflow-hidden selection:bg-blue-100 selection:text-blue-900"
    >
      {/* Background structure - Ambient Depth & Glows */}
      <div className="absolute inset-0 pointer-events-none z-0">
        <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-blue-400/10 blur-[120px] rounded-full mix-blend-multiply" />
        <div className="absolute bottom-1/4 right-1/4 w-[600px] h-[600px] bg-blue-300/10 blur-[150px] rounded-full mix-blend-multiply" />
        {/* Subtle structural grid */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#e2e8f0_1px,transparent_1px),linear-gradient(to_bottom,#e2e8f0_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] opacity-30" />
      </div>

      <div className="relative z-10 w-full max-w-7xl mx-auto flex flex-col lg:flex-row items-center gap-12 lg:gap-20">
        
        {/* Left Column: Messaging */}
        <div className="flex-1 flex flex-col items-start text-left max-w-2xl">
          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight text-slate-900 leading-[1.05] mb-6"
          >
            Hire the right candidate.<br />
            In minutes, not days.
          </motion.h1>
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="text-lg md:text-xl text-slate-600 mb-10 max-w-lg leading-relaxed font-light"
          >
            Review every application. Understand every recommendation. Hire the right candidate—in minutes, not days.
          </motion.p>
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-wrap items-center gap-4"
          >
            <button className="px-7 py-3.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors shadow-lg shadow-blue-600/20 cursor-pointer text-lg">
              Book a Demo
            </button>
            <button className="px-7 py-3.5 bg-white text-slate-700 font-medium rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors shadow-sm cursor-pointer text-lg">
              Explore Platform
            </button>
          </motion.div>
        </div>

        {/* Right Column: The Product Narrative */}
        <div 
          className="flex-1 w-full relative h-[600px] flex items-center justify-center cursor-default"
          onMouseEnter={handleInteraction}
          onMouseMove={handleInteraction}
          onTouchStart={handleInteraction}
        >
          <div className="absolute inset-0 bg-white/90 backdrop-blur-xl rounded-2xl shadow-[0_20px_40px_-15px_rgba(0,0,0,0.05)] border border-slate-200/60 overflow-hidden flex flex-col">
            {/* Window Header */}
            <div className="h-12 border-b border-slate-100 bg-slate-50/80 flex items-center px-4 gap-2 shrink-0">
              <div className="w-3 h-3 rounded-full bg-slate-300" />
              <div className="w-3 h-3 rounded-full bg-slate-300" />
              <div className="w-3 h-3 rounded-full bg-slate-300" />
              <div className="ml-auto flex items-center gap-3">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                </span>
                <div className="text-[10px] font-mono text-slate-400 uppercase tracking-widest">SmartOnboard OS</div>
              </div>
            </div>

            <div className="flex-1 relative bg-slate-50/30 p-6 flex items-center justify-center overflow-hidden">
              <AnimatePresence mode="wait">
                {/* STATE 1: Chaos (First 1.5 seconds) */}
                {!hasPlayedIntro && showChaos && (
                  <motion.div 
                    key="chaos"
                    initial={{ opacity: 0, scale: 0.95, filter: "blur(0px)" }}
                    animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
                    exit={{ opacity: 0, scale: 0.9, filter: "blur(20px)" }}
                    transition={{ duration: 0.5 }}
                    className="absolute inset-0 flex flex-col items-center justify-center gap-6 p-8 bg-slate-50 z-50"
                  >
                    <div className="grid grid-cols-8 gap-3 w-full max-w-md opacity-20">
                      {[...Array(64)].map((_, i) => (
                        <div key={i} className="h-8 bg-slate-400 rounded border border-slate-500 shadow-sm" />
                      ))}
                    </div>
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white/95 backdrop-blur-md px-8 py-4 rounded-full shadow-2xl border border-slate-200 flex flex-col items-center">
                      <span className="text-3xl font-bold text-slate-900 mb-1">247</span>
                      <span className="text-xs font-semibold text-slate-500 uppercase tracking-widest">Applications Processing</span>
                      <div className="w-full h-1 bg-slate-100 rounded-full mt-3 overflow-hidden">
                         <motion.div 
                           initial={{ width: "0%" }}
                           animate={{ width: "100%" }}
                           transition={{ duration: 1.5, ease: "linear" }}
                           className="h-full bg-blue-500"
                         />
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* STATE 2: Living OS (Interactive Carousel) */}
                {hasPlayedIntro && (
                  <motion.div 
                    key="living-os"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                    className="absolute inset-0 flex flex-col lg:flex-row items-stretch justify-start p-6 gap-6"
                  >
                    {/* Interactive Carousel Nav */}
                    <div className="w-full lg:w-2/5 flex flex-col gap-3 shrink-0 border-r border-slate-100 pr-4 overflow-y-auto hide-scrollbar">
                      <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2 flex items-center justify-between">
                        <span>Candidate Pipeline</span>
                        {isInteracting && <span className="text-blue-500 bg-blue-50 px-2 py-0.5 rounded">Manual Mode</span>}
                      </div>
                      {CANDIDATES.map((candidate, idx) => (
                        <button
                          key={candidate.id}
                          onClick={() => {
                            setActiveIndex(idx);
                            handleInteraction();
                          }}
                          className={`text-left p-4 rounded-xl transition-all border relative overflow-hidden group ${
                            activeIndex === idx 
                              ? 'bg-white border-slate-200 shadow-md ring-1 ring-blue-500/10' 
                              : 'bg-transparent border-transparent hover:bg-slate-100 hover:border-slate-200'
                          }`}
                        >
                          {activeIndex === idx && (
                            <motion.div layoutId="active-indicator" className="absolute left-0 top-0 bottom-0 w-1 bg-blue-500" />
                          )}
                          <div className="flex items-start gap-4">
                            <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold shrink-0 ${
                              activeIndex === idx ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20' : 'bg-slate-200 text-slate-600'
                            }`}>
                              {candidate.initials}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className={`font-semibold text-base truncate ${activeIndex === idx ? 'text-slate-900' : 'text-slate-700'}`}>
                                {candidate.name}
                              </div>
                              <div className="text-xs text-slate-500 truncate mb-2">{candidate.role}</div>
                              <div className="flex items-center gap-2">
                                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                                  candidate.match.startsWith('9') ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                                }`}>
                                  {candidate.match} Match
                                </span>
                                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                                  candidate.status === 'approved' ? 'bg-green-100 text-green-700 border border-green-200' :
                                  candidate.status === 'rejected' ? 'bg-red-100 text-red-700 border border-red-200' :
                                  'bg-amber-100 text-amber-700 border border-amber-200'
                                }`}>
                                  {candidate.status.toUpperCase()}
                                </span>
                              </div>
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>

                    {/* Candidate Details & Reasoning Thread */}
                    <div className="flex-1 relative flex flex-col justify-center overflow-y-auto hide-scrollbar">
                      <AnimatePresence mode="wait">
                        <motion.div
                          key={activeCandidate.id}
                          initial={{ opacity: 0, x: 20 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: -20 }}
                          transition={{ duration: 0.3 }}
                          className="w-full flex flex-col justify-start"
                        >
                          <div className="bg-white border border-slate-200 shadow-xl rounded-2xl p-7 relative">
                            {/* Candidate Header */}
                            <div className="flex justify-between items-start mb-6">
                              <div>
                                <h3 className="font-bold text-2xl text-slate-900 mb-1">{activeCandidate.name}</h3>
                                <p className="text-sm text-slate-500 font-medium">{activeCandidate.role}</p>
                              </div>
                              <div className="flex gap-2">
                                <button onClick={handleInteraction} className="px-4 py-2 bg-white border border-slate-200 hover:bg-red-50 hover:text-red-600 hover:border-red-200 text-slate-600 text-sm font-semibold rounded-lg transition-colors cursor-pointer">
                                  Reject
                                </button>
                                <button onClick={handleInteraction} className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors cursor-pointer shadow-green-600/20">
                                  Approve
                                </button>
                              </div>
                            </div>

                            {/* The Reasoning Thread (Visual Focus - AI Blue) */}
                            <div className="relative pl-6 border-l-2 border-blue-500 mb-6">
                              <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-white border-[3px] border-blue-500 flex items-center justify-center">
                                <div className="w-1 h-1 bg-blue-500 rounded-full animate-pulse" />
                              </div>
                              
                              <div className="text-xs font-bold text-blue-600 uppercase tracking-widest mb-3 flex items-center gap-2">
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                                AI Contextual Reasoning
                              </div>
                              
                              <ul className="space-y-4">
                                {activeCandidate.reasoning.map((reason, i) => (
                                  <li key={i} className="flex gap-3 items-start group">
                                    <svg className="w-5 h-5 text-blue-400 shrink-0 mt-0.5 group-hover:text-blue-600 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                                    </svg>
                                    <span className="font-serif text-slate-800 text-[15px] leading-relaxed">
                                      {reason}
                                    </span>
                                  </li>
                                ))}
                              </ul>
                            </div>

                            {/* Risk Indicator (Amber/Red) */}
                            {activeCandidate.concern && (
                              <div className={`rounded-xl p-4 mb-4 border ${activeCandidate.status === 'rejected' ? 'bg-red-50 border-red-100' : 'bg-amber-50 border-amber-100'}`}>
                                <div className={`text-[10px] font-bold uppercase tracking-widest mb-1 flex items-center gap-1.5 ${activeCandidate.status === 'rejected' ? 'text-red-600' : 'text-amber-600'}`}>
                                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                  </svg>
                                  {activeCandidate.status === 'rejected' ? 'Critical Missing Requirement' : 'Potential Concern'}
                                </div>
                                <span className={`font-serif text-[14px] italic ${activeCandidate.status === 'rejected' ? 'text-red-900' : 'text-amber-900'}`}>
                                  {activeCandidate.concern}
                                </span>
                              </div>
                            )}

                            {/* Collaboration (Purple) */}
                            {activeCandidate.collab && (
                              <div className="bg-purple-50/50 border border-purple-100 rounded-xl p-4 flex gap-3 items-start">
                                <div className="w-6 h-6 rounded-full bg-purple-200 flex items-center justify-center shrink-0">
                                  <svg className="w-3 h-3 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                                  </svg>
                                </div>
                                <span className="font-serif text-purple-900 text-[13px] leading-relaxed pt-0.5">
                                  {activeCandidate.collab}
                                </span>
                              </div>
                            )}

                          </div>
                        </motion.div>
                      </AnimatePresence>
                    </div>

                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

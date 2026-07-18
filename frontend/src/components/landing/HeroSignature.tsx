import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';

const MatchEvidence = ({ title, detail, isVisible, delay, iconColor, iconType }: { title: string, detail: string, isVisible: boolean, delay: number, iconColor: string, iconType: string }) => {
  const getIcon = () => {
    switch (iconType) {
      case 'velocity':
        return <svg className={`w-3.5 h-3.5 ${iconColor} shrink-0`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>;
      case 'scale':
        return <svg className={`w-3.5 h-3.5 ${iconColor} shrink-0`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>;
      case 'check':
      default:
        return <svg className={`w-3.5 h-3.5 ${iconColor} shrink-0`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>;
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, x: -10 }}
      animate={isVisible ? { opacity: 1, x: 0 } : { opacity: 0, x: -10 }}
      transition={{ duration: 0.4, delay, ease: "easeOut" }}
      className="flex gap-2.5 items-start"
    >
      <div className={`mt-0.5 w-6 h-6 rounded-full flex items-center justify-center shrink-0 bg-slate-50 border border-slate-200 shadow-sm`}>
        {getIcon()}
      </div>
      <div className="flex flex-col">
        <div className="text-[12px] font-bold text-slate-800">{title}</div>
        <div className="text-[11px] text-slate-500 leading-relaxed font-medium">{detail}</div>
      </div>
    </motion.div>
  );
};

export function HeroSignature() {
  const [seq, setSeq] = useState(0);
  const [counter, setCounter] = useState(0);

  useEffect(() => {
    // Total sequence ~1.8s
    // 0: Scanning 
    // 1: AI Evaluates Evidence
    const t1 = setTimeout(() => setSeq(1), 400); 
    // 2: Recommendation Locks
    const t2 = setTimeout(() => setSeq(2), 1100);
    // 3: Match Widget Updates
    const t3 = setTimeout(() => setSeq(3), 1300); 
    // 4: AI Insight Widget Activates
    const t4 = setTimeout(() => setSeq(4), 1500);
    // 5: Interview Scheduled Confirms -> Stillness
    const t5 = setTimeout(() => setSeq(5), 1800);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); clearTimeout(t4); clearTimeout(t5); };
  }, []);

  useEffect(() => {
    if (seq >= 1 && seq < 2) {
      let current = 0;
      const interval = setInterval(() => {
        current += Math.floor(Math.random() * 15) + 5;
        if (current >= 98) {
          setCounter(98);
          clearInterval(interval);
        } else {
          setCounter(current);
        }
      }, 30);
      return () => clearInterval(interval);
    } else if (seq >= 2) {
      setCounter(98);
    }
  }, [seq]);

  return (
    <section className="relative w-full min-h-screen bg-[#FDFDFD] flex flex-col items-center pt-28 pb-24 px-6 overflow-hidden selection:bg-slate-200 selection:text-slate-900">
      
      {/* 1. Pure Clean Background */}
      <div className="absolute inset-0 pointer-events-none z-0">
        <div className="absolute inset-0 opacity-[0.03] mix-blend-multiply" style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }} />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_60%_at_50%_50%,#000_70%,transparent_100%)]" />
      </div>

      {/* 2. The Message with Restrained Color (Pure Black + Red Accent) */}
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
        
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <button className="w-full sm:w-auto px-7 py-3 bg-slate-900 text-white font-medium rounded-lg shadow-sm hover:bg-slate-800 transition-colors text-[14px] tracking-wide cursor-pointer">
            Start Hiring
          </button>
          <button className="w-full sm:w-auto px-7 py-3 bg-white text-slate-700 font-medium rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors shadow-sm text-[14px] tracking-wide cursor-pointer">
            Claim Your Profile
          </button>
        </div>
      </div>

      {/* 3. The Artifact & Framed Ecosystem */}
      <div className="relative z-20 w-full max-w-5xl mx-auto h-[400px] flex items-center justify-center">
        
        {/* Supporting Widget 1: Match Updates (Left Side) */}
        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={seq >= 3 ? { opacity: 1, x: 0 } : { opacity: 0, x: 20 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="absolute left-0 lg:left-4 top-[10%] z-30 flex items-center gap-3 bg-white p-3 rounded-xl shadow-[0_10px_40px_rgb(0,0,0,0.08)] border border-slate-200 w-48"
        >
           <div className="w-8 h-8 rounded-full bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600">
             <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
           </div>
           <div className="flex flex-col">
             <div className="text-[10px] font-bold text-slate-800 uppercase tracking-wide">Match Verified</div>
             <div className="text-[9px] font-medium text-slate-500">Alex Rivera • Designer</div>
           </div>
        </motion.div>

        {/* Supporting Widget 2: AI Insight (Top Right) */}
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={seq >= 4 ? { opacity: 1, x: 0 } : { opacity: 0, x: -20 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="absolute right-0 lg:right-4 top-[5%] z-30 flex flex-col gap-2 bg-white p-4 rounded-xl shadow-[0_10px_40px_rgb(0,0,0,0.08)] border border-slate-200 w-48"
        >
          <div className="text-[9px] font-bold uppercase tracking-widest text-blue-600 flex items-center gap-1.5">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
            AI Insight
          </div>
          <div className="text-[10px] font-medium text-slate-600 leading-relaxed">
            Candidate's velocity in fintech directly matches the 18-month roadmap requirements.
          </div>
        </motion.div>

        {/* Supporting Widget 3: Interview Scheduled (Bottom Right) */}
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={seq >= 5 ? { opacity: 1, y: 0 } : { opacity: 0, y: -20 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="absolute right-8 lg:right-12 bottom-[10%] z-30 flex items-center gap-3 bg-slate-900 p-3 rounded-xl shadow-[0_10px_40px_rgb(0,0,0,0.15)] border border-slate-800 w-48"
        >
           <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-white">
             <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
           </div>
           <div className="flex flex-col">
             <div className="text-[10px] font-bold text-white uppercase tracking-wide">Interview Scheduled</div>
             <div className="text-[9px] font-medium text-slate-400">Tomorrow, 10:00 AM</div>
           </div>
        </motion.div>

        {/* Center: The Main Artifact */}
        <div className="w-full max-w-[650px] bg-white rounded-2xl shadow-[0_20px_60px_-15px_rgba(17,24,39,0.1),0_0_0_1px_rgba(17,24,39,0.05)] overflow-hidden flex flex-col z-20">
          
          {/* Header */}
          <div className="w-full px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
            <div className="flex items-center gap-2.5">
              <div className="bg-white p-1 rounded-md border border-slate-200 shadow-sm">
                <svg className="w-3.5 h-3.5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
              </div>
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-700">Verified Intelligence Report</span>
            </div>
            
            <motion.div 
              initial={{ opacity: 0 }}
              animate={seq >= 2 ? { opacity: 1 } : { opacity: 0 }}
              className="px-2 py-0.5 rounded text-[9px] font-bold text-white bg-blue-600 uppercase tracking-wide shadow-sm"
            >
              Match Locked
            </motion.div>
          </div>

          {/* Body */}
          <div className="w-full grid grid-cols-1 md:grid-cols-12 gap-0 relative">
            
            {/* Left: Entities */}
            <div className="md:col-span-5 p-7 border-b md:border-b-0 md:border-r border-slate-100 flex flex-col justify-center">
              
              <div className="mb-6">
                <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-slate-300" /> Target Role
                </div>
                <div className="text-xl font-serif font-bold text-slate-900 mb-1 leading-tight">Senior Product Designer</div>
                <div className="text-[11px] text-slate-500 font-medium">Fintech Infrastructure</div>
              </div>

              {/* Connecting Line (Solidifies on seq 2) */}
              <div className="relative w-full h-6 flex items-center mb-6">
                 <div className="absolute inset-0 flex items-center">
                    <div className={`w-full border-t transition-colors duration-300 ${seq >= 2 ? 'border-solid border-blue-200' : 'border-dashed border-slate-200'}`} />
                 </div>
                 <motion.div 
                    initial={{ scale: 0, opacity: 0 }}
                    animate={seq >= 2 ? { scale: 1, opacity: 1 } : { scale: 0, opacity: 0 }}
                    className="absolute left-1/2 -translate-x-1/2 w-6 h-6 rounded-full border border-blue-200 bg-blue-50 shadow-sm flex items-center justify-center z-10"
                 >
                    <svg className="w-3 h-3 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 14l-7 7m0 0l-7-7m7 7V3" /></svg>
                 </motion.div>
              </div>

              {/* Candidate Info (Fades in during seq 1) */}
              <motion.div 
                initial={{ opacity: 0 }}
                animate={seq >= 1 ? { opacity: 1 } : { opacity: 0 }}
                transition={{ duration: 0.3 }}
              >
                <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-2 flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-500" /> Verified Candidate
                </div>
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center shrink-0">
                    <span className="text-xs font-bold text-slate-700">AR</span>
                  </div>
                  <div>
                    <div className="text-lg font-serif font-bold text-slate-900 leading-tight">Alex Rivera</div>
                    <div className="flex items-center gap-1 mt-0.5">
                      <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                      <span className="text-[9px] text-emerald-600 font-bold uppercase tracking-wide">Identity Verified</span>
                    </div>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  <span className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-[9px] font-bold border border-slate-200">Design Systems</span>
                  <span className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-[9px] font-bold border border-slate-200">Fintech Context</span>
                </div>
              </motion.div>

            </div>

            {/* Right: Reasoning */}
            <div className="md:col-span-7 p-7 bg-[#FAFAFA] flex flex-col justify-center">

              <div className="flex items-end justify-between mb-6">
                 <div>
                   <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1 flex items-center gap-1.5">
                     <svg className="w-3.5 h-3.5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                     Match Confidence
                   </div>
                   <div className="flex items-baseline gap-1">
                     <span className={`text-5xl font-serif font-bold tracking-tight leading-none transition-colors duration-300 ${seq >= 2 ? 'text-blue-600' : 'text-slate-900'}`}>
                       {seq === 0 ? '--' : counter}
                     </span>
                     <span className="text-2xl font-serif font-bold text-slate-400">%</span>
                   </div>
                 </div>
                 
                 {seq === 0 && (
                   <div className="text-[9px] text-slate-500 font-bold tracking-wide uppercase bg-slate-100 px-2 py-1 rounded border border-slate-200 animate-pulse">
                     Evaluating...
                   </div>
                 )}
                 {seq > 0 && (
                   <motion.div 
                     initial={{ opacity: 0, scale: 0.9 }}
                     animate={seq >= 2 ? { opacity: 1, scale: 1 } : { opacity: 0.5, scale: 0.95 }}
                     className={`text-[9px] font-bold tracking-wide uppercase px-2 py-1 rounded border ${seq >= 2 ? 'text-emerald-700 bg-emerald-50 border-emerald-200' : 'text-slate-500 bg-white border-slate-200'}`}
                   >
                     Absolute Alignment
                   </motion.div>
                 )}
              </div>

              <div className="space-y-4">
                <MatchEvidence 
                  title="Demonstrated Velocity" 
                  detail="Evidence confirms candidate shipped 4 major fintech infrastructure products in under 18 months."
                  isVisible={seq >= 1}
                  delay={0}
                  iconColor="text-red-500"
                  iconType="velocity"
                />
                <MatchEvidence 
                  title="Scale Context" 
                  detail="Successfully managed design systems for platforms processing $10M+ daily volume."
                  isVisible={seq >= 1}
                  delay={0.15}
                  iconColor="text-blue-500"
                  iconType="scale"
                />
                <MatchEvidence 
                  title="Skill Verification" 
                  detail="100% alignment on critical requirements: Systems Architecture, Interaction Design, and React."
                  isVisible={seq >= 1}
                  delay={0.3}
                  iconColor="text-emerald-500"
                  iconType="check"
                />
              </div>

            </div>
          </div>

        </div>
      </div>

    </section>
  );
}

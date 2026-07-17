import { motion } from 'framer-motion';

const timeline = [
  { time: "8:45 AM", title: "Applications arrive", desc: "263 new candidates submitted overnight." },
  { time: "9:02 AM", title: "AI analyzes & organizes", desc: "SmartOnboard parses, verifies, and extracts key signals instantly." },
  { time: "9:08 AM", title: "Candidates ranked", desc: "Top 12 candidates are surfaced with explicit evidence and matching percentages." },
  { time: "9:15 AM", title: "Interviews scheduled", desc: "You review the top recommendations and send invitations directly from the workspace." },
  { time: "10:00 AM", title: "Back to actual work", desc: "The screening is done. You spend your day interviewing, not reading resumes." }
];

export function WorkflowSequence() {
  return (
    <section className="bg-black text-white py-32 md:py-48 selection:bg-white selection:text-black">
      <div className="max-w-[1440px] px-6 md:px-12 lg:px-24 mx-auto">
        
        <div className="text-center mb-32">
          <motion.h2 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ margin: "-10%" }} // Removed once: true
            transition={{ duration: 0.8 }}
            className="text-4xl md:text-6xl lg:text-7xl font-bold tracking-tighter"
          >
            A day in the life.
          </motion.h2>
        </div>

        <div className="max-w-3xl mx-auto relative">
          {/* Vertical Line */}
          <div className="absolute left-[23px] md:left-1/2 top-0 bottom-0 w-[2px] bg-zinc-900" />

          {timeline.map((step, i) => (
            <motion.div 
              key={i}
              initial={{ opacity: 0, y: 50 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ margin: "-10%" }}
              transition={{ duration: 0.8 }}
              className="relative flex flex-col md:flex-row items-start md:items-center justify-between mb-24 last:mb-0"
            >
              
              {/* Left Side (Time) */}
              <div className="md:w-1/2 md:pr-16 flex md:justify-end mb-4 md:mb-0 pl-16 md:pl-0">
                <div className="font-mono text-xl md:text-3xl tracking-tighter text-zinc-500">
                  {step.time}
                </div>
              </div>

              {/* Center Dot */}
              <div className="absolute left-[18px] md:left-1/2 md:-translate-x-1/2 w-3 h-3 bg-white rounded-full shadow-[0_0_15px_rgba(255,255,255,0.5)] z-10" />

              {/* Right Side (Content) */}
              <div className="md:w-1/2 md:pl-16 pl-16">
                <h3 className="text-2xl md:text-3xl font-semibold tracking-tight mb-3">
                  {step.title}
                </h3>
                <p className="text-zinc-400 font-light text-lg md:text-xl leading-relaxed">
                  {step.desc}
                </p>
              </div>

            </motion.div>
          ))}
        </div>

      </div>
    </section>
  );
}

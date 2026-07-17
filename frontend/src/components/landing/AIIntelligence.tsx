import { motion } from 'framer-motion';

export function AIIntelligence() {
  return (
    <section className="relative w-full bg-blue-950 text-white py-32 md:py-48 selection:bg-blue-500 selection:text-white overflow-hidden">
      {/* Background Ambience */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-900/40 via-blue-950 to-blue-950" />

      <div className="max-w-[1440px] px-6 md:px-12 lg:px-24 mx-auto relative z-10">
        
        <div className="text-center mb-24">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <div className="flex justify-center items-center gap-3 mb-8">
              <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse shadow-[0_0_15px_rgba(96,165,250,0.8)]" />
              <span className="font-mono text-xs uppercase tracking-[0.2em] text-blue-300">
                The Relief
              </span>
            </div>
            <h2 className="text-5xl md:text-7xl font-bold tracking-tighter leading-[1.0]">
              Intelligence that <br/>
              <span className="text-blue-300">explains itself.</span>
            </h2>
          </motion.div>
        </div>

        {/* Visual Reasoning Node Connection */}
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-center">
            
            {/* The Resume */}
            <motion.div 
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8 }}
              className="bg-white/5 border border-blue-500/20 backdrop-blur-md rounded-2xl p-8"
            >
              <div className="text-xs font-mono text-blue-400 mb-6 uppercase tracking-widest">Extracted Experience</div>
              <div className="space-y-4">
                <div className="h-2 w-3/4 bg-white/20 rounded" />
                <div className="h-2 w-full bg-white/10 rounded" />
                <div className="h-2 w-5/6 bg-white/10 rounded" />
                <div className="inline-block mt-4 px-3 py-1 bg-blue-500/20 text-blue-300 text-xs font-mono rounded border border-blue-500/30">
                  React 18 Architecture
                </div>
              </div>
            </motion.div>

            {/* The AI Connection */}
            <motion.div 
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="flex flex-col items-center justify-center py-12 md:py-0"
            >
              <div className="w-[1px] h-12 md:w-full md:h-[1px] bg-gradient-to-b md:bg-gradient-to-r from-blue-500/20 via-blue-400 to-blue-500/20 relative">
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-4 h-4 bg-blue-500 rounded-full shadow-[0_0_20px_rgba(59,130,246,1)]" />
              </div>
            </motion.div>

            {/* The Requirement */}
            <motion.div 
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="bg-white/5 border border-blue-500/20 backdrop-blur-md rounded-2xl p-8"
            >
              <div className="text-xs font-mono text-blue-400 mb-6 uppercase tracking-widest">Job Requirement</div>
              <h3 className="text-xl font-bold mb-4">Senior Frontend Engineer</h3>
              <p className="text-white/60 text-sm leading-relaxed mb-4">
                Must have 5+ years building scalable client applications with modern React patterns.
              </p>
              <div className="inline-block px-3 py-1 bg-green-500/20 text-green-400 text-xs font-mono rounded border border-green-500/30">
                Match Verified
              </div>
            </motion.div>

          </div>
        </div>

      </div>
    </section>
  );
}

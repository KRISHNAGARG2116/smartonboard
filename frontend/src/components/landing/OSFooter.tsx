import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';

export function OSFooter() {
  return (
    <footer className="bg-black text-white py-32 md:py-48 selection:bg-white selection:text-black text-center px-6 relative overflow-hidden">
      
      {/* Subtle background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-white/5 blur-[120px] rounded-full pointer-events-none" />

      <div className="max-w-[1440px] mx-auto flex flex-col items-center relative z-10">
        
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="w-full max-w-4xl flex flex-col items-center text-center"
        >
          <div className="flex items-center justify-center gap-3 mb-8">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse shadow-[0_0_10px_rgba(34,197,94,0.8)]" />
            <span className="font-mono text-xs tracking-[0.2em] text-white/50 uppercase">
              The Next Step
            </span>
          </div>
          
          <h2 className="text-4xl md:text-5xl lg:text-7xl font-serif font-bold text-white tracking-tight leading-[1.1] mb-6 w-full text-center">
            Stop reading resumes. <br/>
            Start meeting your next hire.
          </h2>
          <p className="text-xl font-light text-white/50 max-w-2xl mx-auto text-center mb-16">
            Join the forward-thinking hiring teams using SmartOnboard to cut screening time by 90% and make confident decisions instantly.
          </p>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="flex flex-col sm:flex-row gap-6 mb-32 w-full max-w-md justify-center"
        >
          <Link to="/register" className="w-full sm:w-auto px-10 py-5 rounded-xl bg-white text-black font-bold text-lg hover:bg-zinc-200 transition-colors shadow-[0_0_40px_rgba(255,255,255,0.2)] text-center">
            Start Free Trial
          </Link>
          <Link to="/demo" className="w-full sm:w-auto px-10 py-5 rounded-xl border border-white/20 bg-transparent text-white font-medium text-lg hover:bg-white/10 hover:border-white/40 transition-colors text-center">
            Book a Demo
          </Link>
        </motion.div>

        <div className="w-full flex flex-col md:flex-row justify-between items-center text-zinc-600 text-xs font-mono uppercase tracking-widest border-t border-zinc-900 pt-8">
          <div>© SmartOnboard {new Date().getFullYear()}</div>
          <div className="flex gap-8 mt-4 md:mt-0">
            <Link to="/privacy" className="hover:text-white transition-colors">Privacy</Link>
            <Link to="/terms" className="hover:text-white transition-colors">Terms</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}

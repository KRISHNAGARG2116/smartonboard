import { motion } from 'framer-motion';

export function PainAgitation() {
  return (
    <section className="relative w-full bg-white text-black pt-12 pb-32 md:pb-48 selection:bg-red-500 selection:text-white">
      <div className="max-w-[1440px] px-6 md:px-12 lg:px-24 mx-auto">
        
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-16 lg:gap-24 items-center">
          
          {/* Editorial Recognition (Left side, wider) */}
          <div className="lg:col-span-5 space-y-12">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
            >
              <h2 className="text-5xl md:text-7xl font-bold tracking-tighter leading-[1.0] mb-8">
                Your hiring team <br/>
                <span className="text-red-600">is exhausted.</span>
              </h2>
              <p className="text-xl md:text-2xl font-light text-black/60 leading-relaxed max-w-lg mb-8">
                The current system forces you to act like a machine. You spend hours sifting through noise, updating scattered spreadsheets, and praying you didn't miss the perfect candidate.
              </p>
              <div className="inline-flex items-center gap-3 text-red-600 font-mono text-xs tracking-widest uppercase border border-red-200 bg-red-50 px-4 py-2 rounded-full">
                <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
                The System is Broken
              </div>
            </motion.div>
          </div>

          {/* The Chaos Visualized (Right side) */}
          <div className="lg:col-span-7 relative h-[600px] w-full perspective-[1000px]">
             
             {/* Messy Spreadsheet Visual */}
             <motion.div 
               initial={{ opacity: 0, rotateY: 20, z: -100 }}
               whileInView={{ opacity: 1, rotateY: -10, z: 0 }}
               transition={{ duration: 1, delay: 0.2 }}
               className="absolute top-10 right-10 w-[500px] bg-white border border-black/10 shadow-2xl rounded-xl p-4 overflow-hidden origin-right"
             >
               <div className="h-6 border-b border-black/5 flex items-center gap-2 mb-4">
                 <div className="w-3 h-3 bg-red-500/20 rounded-full" />
                 <div className="text-[10px] font-mono text-black/30">candidates_v4_FINAL.xlsx</div>
               </div>
               <div className="space-y-2">
                 {[...Array(8)].map((_, i) => (
                   <div key={i} className="flex gap-2 opacity-40">
                     <div className="h-4 w-8 bg-zinc-100 rounded" />
                     <div className="h-4 w-32 bg-zinc-100 rounded" />
                     <div className="h-4 w-16 bg-red-100 rounded" />
                     <div className="h-4 w-24 bg-zinc-100 rounded" />
                   </div>
                 ))}
               </div>
               <div className="absolute inset-0 bg-gradient-to-t from-white/80 to-transparent" />
             </motion.div>

             {/* Unread Emails Visual */}
             <motion.div 
               initial={{ opacity: 0, rotateY: -20, x: -50 }}
               whileInView={{ opacity: 1, rotateY: 5, x: 0 }}
               transition={{ duration: 1, delay: 0.4 }}
               className="absolute bottom-20 left-0 w-[400px] bg-zinc-50 border border-black/10 shadow-[0_30px_60px_rgba(0,0,0,0.1)] rounded-xl p-6 origin-left"
             >
               <div className="flex items-center justify-between border-b border-black/5 pb-4 mb-4">
                 <div className="font-bold">Inbox</div>
                 <div className="text-red-500 font-bold bg-red-100 px-2 py-0.5 rounded text-xs">9,412</div>
               </div>
               <div className="space-y-4">
                 {[...Array(3)].map((_, i) => (
                   <div key={i} className="flex gap-4">
                     <div className="w-8 h-8 rounded-full bg-zinc-200 shrink-0" />
                     <div className="flex-1 space-y-2">
                       <div className="h-3 w-24 bg-zinc-300 rounded" />
                       <div className="h-2 w-full bg-zinc-200 rounded" />
                       <div className="h-2 w-2/3 bg-zinc-200 rounded" />
                     </div>
                   </div>
                 ))}
               </div>
             </motion.div>

             {/* The Breaking Point Label */}
             <motion.div
               initial={{ opacity: 0, scale: 0.9 }}
               whileInView={{ opacity: 1, scale: 1 }}
               transition={{ duration: 0.8, delay: 0.6 }}
               className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-red-600 text-white px-6 py-3 rounded-full font-bold shadow-2xl rotate-[-5deg]"
             >
               Manual Review Botleneck
             </motion.div>

          </div>

        </div>
      </div>
    </section>
  );
}

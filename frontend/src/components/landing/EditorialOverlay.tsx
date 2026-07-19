export function EditorialOverlay() {
  return (
    <div className="fixed inset-0 pointer-events-none z-40 overflow-hidden mix-blend-multiply opacity-80">
      {/* Subtle dot grid */}
      <div className="absolute inset-0 bg-[radial-gradient(#94a3b8_1px,transparent_1px)] [background-size:24px_24px] opacity-20" />
      
      {/* Structural Lines */}
      <div className="absolute left-6 lg:left-24 top-0 bottom-0 w-[1px] bg-slate-900/10" />
      <div className="absolute right-6 lg:right-24 top-0 bottom-0 w-[1px] bg-slate-900/10" />
      
      {/* Crosshairs */}
      <div className="absolute top-[20%] left-6 lg:left-24 -translate-x-1/2 -translate-y-1/2 text-slate-400/50 text-[10px]">┼</div>
      <div className="absolute top-[80%] left-6 lg:left-24 -translate-x-1/2 -translate-y-1/2 text-slate-400/50 text-[10px]">┼</div>
      <div className="absolute top-[50%] right-6 lg:right-24 -translate-x-1/2 -translate-y-1/2 text-slate-400/50 text-[10px]">┼</div>
      
      {/* Editorial Annotations */}
      <div className="absolute top-24 left-8 lg:left-28 text-[9px] font-mono text-slate-400 tracking-widest uppercase">
        SYS.REF: 902.11A
      </div>
      <div className="absolute bottom-12 right-8 lg:right-28 text-[9px] font-mono text-slate-400 tracking-widest uppercase">
        TRUTH PROTOCOL ACTIVE
      </div>
      <div className="absolute top-1/2 left-2 lg:left-10 -translate-y-1/2 -rotate-90 text-[9px] font-mono text-slate-400 tracking-widest uppercase transform-gpu">
        PAGE 01/01
      </div>
      <div className="absolute bottom-12 left-8 lg:left-28 text-[9px] font-mono text-slate-400 tracking-widest uppercase flex items-center gap-2">
         <div className="w-1.5 h-1.5 bg-emerald-500 rounded-sm" />
         AUTH-LOG: [SECURE]
      </div>
    </div>
  );
}

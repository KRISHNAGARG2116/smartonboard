import { motion } from 'framer-motion';
import { useState } from 'react';

const TABS = ['Dashboard', 'Candidates', 'AI Match', 'Resume Intel', 'Jobs'];

export function ProductShowcase() {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <section className="bg-white py-32 md:py-48 text-black selection:bg-black selection:text-white border-t border-black/10 overflow-hidden">
      <div className="max-w-[1440px] px-6 md:px-12 lg:px-24 mx-auto">
        
        <div className="text-center mb-24">
          <motion.h2 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-5xl md:text-7xl font-bold tracking-tighter leading-[1.1] mb-8"
          >
            The Workspace.
          </motion.h2>
          <motion.p 
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="text-xl text-black/50 font-light max-w-2xl mx-auto text-center"
          >
            A cohesive environment combining sourcing, AI intelligence, and interview management into a single, beautiful flow.
          </motion.p>
        </div>

        {/* Tab Navigation */}
        <div className="flex justify-center mb-16 overflow-x-auto pb-4 hide-scrollbar">
          <div className="inline-flex bg-zinc-100 p-1.5 rounded-full border border-black/5">
            {TABS.map((tab, i) => (
              <button
                key={tab}
                onClick={() => setActiveTab(i)}
                className={`relative px-8 py-3 rounded-full text-sm font-medium transition-colors ${
                  activeTab === i ? 'text-white' : 'text-black/60 hover:text-black'
                }`}
              >
                {activeTab === i && (
                  <motion.div 
                    layoutId="activeTabProduct"
                    className="absolute inset-0 bg-black rounded-full"
                    transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                  />
                )}
                <span className="relative z-10">{tab}</span>
              </button>
            ))}
          </div>
        </div>

        {/* CSS Rendered UI Preview container */}
        <motion.div
          animate={{ y: [0, -10, 0] }}
          transition={{ repeat: Infinity, duration: 8, ease: "easeInOut" }}
        >
          <motion.div 
            key={activeTab} // Force re-render on tab change for entry animation
            initial={{ opacity: 0, y: 20, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="w-full aspect-[16/11] md:aspect-[16/9] bg-zinc-50 border border-black/10 rounded-2xl md:rounded-[2rem] shadow-2xl overflow-hidden flex flex-col relative"
          >
          {/* Subtle AI Glow in Workspace */}
          <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-blue-500/5 blur-[100px] rounded-full pointer-events-none" />

          {/* Mock Browser Header */}
          <div className="h-14 border-b border-black/10 flex items-center px-6 gap-4 bg-white shrink-0 relative z-10">
            <div className="flex gap-2">
              <div className="w-3 h-3 rounded-full bg-red-400" />
              <div className="w-3 h-3 rounded-full bg-amber-400" />
              <div className="w-3 h-3 rounded-full bg-green-400" />
            </div>
            <div className="flex-1 bg-zinc-100 rounded-md h-8 flex items-center px-4 max-w-xl mx-auto">
              <span className="text-xs font-mono text-black/40">smartonboard.com/workspace</span>
            </div>
          </div>

          {/* Dynamic Content based on tab */}
          <div className="flex-1 p-6 md:p-12 overflow-hidden relative z-10">
            {activeTab === 0 && <MockDashboard />}
            {activeTab === 1 && <MockCandidates />}
            {activeTab === 2 && <MockAIMatch />}
            {activeTab === 3 && <MockResumeIntel />}
            {activeTab === 4 && <MockJobManagement />}
          </div>
          </motion.div>
        </motion.div>

      </div>
    </section>
  );
}

// ----------------------------------------------------
// UI Mockup Components 
// ----------------------------------------------------

function MockDashboard() {
  return (
    <div className="h-full flex flex-col gap-6">
      <div className="flex justify-between items-end">
        <div>
          <h3 className="text-2xl font-bold tracking-tight">Good morning, Sarah.</h3>
          <p className="text-black/50 text-sm">Here is your overview for today.</p>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-6">
        {[
          { title: "Active Jobs", val: "12" },
          { title: "New Applicants", val: "263" },
          { title: "Pending Reviews", val: "14" }
        ].map((stat, i) => (
          <div key={i} className="bg-white p-6 rounded-xl border border-black/5 shadow-sm">
            <div className="text-xs font-medium text-black/50 uppercase tracking-wider mb-2">{stat.title}</div>
            <div className="text-4xl font-bold tracking-tighter">{stat.val}</div>
          </div>
        ))}
      </div>
      <div className="flex-1 bg-white rounded-xl border border-black/5 shadow-sm p-6">
        <div className="text-sm font-medium mb-6">Recent Activity Timeline</div>
        <div className="space-y-4">
          {[1,2,3].map(i => (
            <div key={i} className="flex gap-4 items-start">
              <div className="w-2 h-2 rounded-full bg-blue-500 mt-1.5" />
              <div>
                <div className="text-sm font-medium">AI Match completed for Senior Frontend Engineer</div>
                <div className="text-xs text-black/40">2 minutes ago</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function MockCandidates() {
  return (
    <div className="h-full flex flex-col bg-white rounded-xl border border-black/5 shadow-sm overflow-hidden">
      <div className="h-14 border-b border-black/5 flex items-center px-6 gap-4">
        <div className="text-sm font-medium flex-1">All Candidates (1,042)</div>
        <div className="px-3 py-1.5 bg-zinc-100 rounded text-xs">Filter</div>
      </div>
      <div className="flex-1 p-6 space-y-2">
        {[
          { name: "Alex Rivera", role: "Frontend Engineer", match: "94%" },
          { name: "Jordan Smith", role: "Backend Engineer", match: "88%" },
          { name: "Taylor Swift", role: "Product Designer", match: "82%" }
        ].map((c, i) => (
          <div key={i} className="flex items-center justify-between p-4 rounded-lg hover:bg-zinc-50 border border-transparent hover:border-black/5 transition-colors cursor-pointer group">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-zinc-200 flex items-center justify-center font-medium">{c.name[0]}</div>
              <div>
                <div className="text-sm font-medium">{c.name}</div>
                <div className="text-xs text-black/50">{c.role}</div>
              </div>
            </div>
            <div className="flex items-center gap-6">
              <div className="flex flex-col items-end">
                <div className="text-xs text-black/50">AI Match</div>
                <div className="text-sm font-bold text-green-600">{c.match}</div>
              </div>
              <div className="px-4 py-2 bg-black text-white text-xs rounded-md font-medium opacity-0 group-hover:opacity-100 transition-opacity">Review</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MockAIMatch() {
  return (
    <div className="h-full grid grid-cols-12 gap-6">
      <div className="col-span-4 bg-white rounded-xl border border-black/5 shadow-sm p-6 flex flex-col items-center text-center justify-center">
        <div className="w-24 h-24 rounded-full border-4 border-green-500 flex items-center justify-center mb-6 relative">
           <div className="absolute inset-0 rounded-full bg-green-500/10 animate-ping" />
           <span className="text-3xl font-bold text-green-600">94%</span>
        </div>
        <h3 className="font-bold text-lg">Alex Rivera</h3>
        <p className="text-sm text-black/50 mb-6">Senior Frontend Engineer</p>
        <div className="w-full flex gap-2">
          <button className="flex-1 bg-black text-white py-2 rounded text-xs font-medium hover:bg-zinc-800 transition-colors">Advance</button>
          <button className="flex-1 bg-red-50 text-red-600 py-2 rounded text-xs font-medium hover:bg-red-100 transition-colors">Reject</button>
        </div>
      </div>
      <div className="col-span-8 bg-white rounded-xl border border-black/5 shadow-sm p-6 space-y-6 overflow-y-auto">
        <div>
          <div className="text-xs font-mono tracking-widest text-blue-600 mb-2 flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
            AI REASONING
          </div>
          <p className="text-sm leading-relaxed text-black/80">
            Candidate demonstrates exceptional proficiency in React and Framer Motion, directly matching the core requirements of this role. Their recent open-source commits provide strong evidence of component architecture skills.
          </p>
        </div>
        <div>
          <div className="text-xs font-mono tracking-widest text-black/40 mb-3">EVIDENCE FOUND</div>
          <div className="space-y-2">
            <div className="text-sm px-4 py-2 bg-zinc-50 border border-black/5 rounded flex justify-between">
              <span>React 18 Architecture</span>
              <span className="text-blue-500 font-mono text-xs">VERIFIED</span>
            </div>
            <div className="text-sm px-4 py-2 bg-zinc-50 border border-black/5 rounded flex justify-between">
              <span>Framer Motion Animations</span>
              <span className="text-blue-500 font-mono text-xs">VERIFIED</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MockResumeIntel() {
  return (
    <div className="h-full grid grid-cols-12 gap-6">
      <div className="col-span-7 bg-white rounded-xl border border-black/5 shadow-sm p-8 overflow-hidden relative">
        <div className="absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-white to-transparent z-10" />
        <div className="space-y-4 opacity-50 blur-[1px]">
          <div className="h-4 w-1/3 bg-black/10 rounded" />
          <div className="h-3 w-1/4 bg-black/5 rounded mb-8" />
          <div className="h-2 w-full bg-black/5 rounded" />
          <div className="h-2 w-full bg-black/5 rounded" />
          <div className="h-2 w-4/5 bg-black/5 rounded" />
        </div>
        <div className="absolute top-24 left-1/2 -translate-x-1/2 bg-blue-500 text-white px-4 py-2 rounded-full text-xs font-medium z-20 shadow-lg flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
          Extracting structured data...
        </div>
      </div>
      <div className="col-span-5 flex flex-col gap-4">
        <div className="bg-white rounded-xl border border-black/5 shadow-sm p-6">
           <div className="text-xs font-mono tracking-widest text-black/40 mb-4">IDENTIFIED SKILLS</div>
           <div className="flex flex-wrap gap-2">
             {["TypeScript", "React", "Node.js", "GraphQL", "AWS"].map(skill => (
               <div key={skill} className="px-3 py-1 bg-blue-50 text-blue-700 rounded text-xs font-medium border border-blue-100">
                 {skill}
               </div>
             ))}
           </div>
        </div>
        <div className="bg-white rounded-xl border border-black/5 shadow-sm p-6 flex-1">
           <div className="text-xs font-mono tracking-widest text-black/40 mb-4">RED FLAGS</div>
           <div className="flex items-center gap-3 p-3 bg-red-50 text-red-700 rounded border border-red-100">
             <div className="w-2 h-2 rounded-full bg-red-500" />
             <span className="text-xs font-medium">Employment gap detected (2023)</span>
           </div>
        </div>
      </div>
    </div>
  );
}

function MockJobManagement() {
  return (
    <div className="h-full flex flex-col bg-white rounded-xl border border-black/5 shadow-sm overflow-hidden">
      <div className="h-14 border-b border-black/5 flex items-center px-6 gap-4 justify-between">
        <div className="text-sm font-medium">Active Pipelines</div>
        <div className="px-4 py-1.5 bg-black text-white rounded text-xs font-medium">Create Job</div>
      </div>
      <div className="flex-1 p-6 space-y-4">
        {[
          { title: "Senior Frontend Engineer", dept: "Engineering", stage: "Interviewing" },
          { title: "Product Marketing Manager", dept: "Marketing", stage: "Sourcing" },
          { title: "Director of Design", dept: "Design", stage: "Offer" }
        ].map((job, i) => (
          <div key={i} className="flex justify-between items-center p-4 border border-black/5 rounded-lg hover:border-black/20 transition-colors cursor-pointer group">
             <div>
               <div className="font-bold text-sm mb-1">{job.title}</div>
               <div className="text-xs text-black/50">{job.dept}</div>
             </div>
             <div className="flex items-center gap-6">
               <div className="text-xs font-medium px-3 py-1 bg-zinc-100 rounded-full text-black/60">{job.stage}</div>
               <div className="font-mono text-black/30 group-hover:text-black transition-colors">→</div>
             </div>
          </div>
        ))}
      </div>
    </div>
  );
}

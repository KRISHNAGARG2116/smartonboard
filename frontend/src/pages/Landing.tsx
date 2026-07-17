import { useEffect } from 'react';
import { HeroSignature } from '../components/landing/HeroSignature';
import { PainAgitation } from '../components/landing/PainAgitation';
import { AIIntelligence } from '../components/landing/AIIntelligence';
import { ProductShowcase } from '../components/landing/ProductShowcase';
import { OSFooter } from '../components/landing/OSFooter';
import { Link } from 'react-router-dom';

export default function Landing() {
  useEffect(() => {
    if ('scrollRestoration' in window.history) {
      window.history.scrollRestoration = 'manual';
    }
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="bg-black font-sans selection:bg-white selection:text-black">
      {/* Permanent, Lightweight White Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-white/95 backdrop-blur-md shadow-sm border-b border-black/5">
        <div className="max-w-[1440px] mx-auto px-6 md:px-12 lg:px-24 h-16 flex items-center justify-between">
          <Link to="/" className="font-bold text-lg tracking-tighter uppercase text-black">
            SmartOnboard
          </Link>
          <div className="flex gap-6 items-center">
            <Link to="/login" className="text-sm font-medium text-black/60 hover:text-black transition-colors">
              Log In
            </Link>
            <Link to="/register" className="px-4 py-1.5 rounded-lg text-sm font-semibold bg-black text-white hover:bg-zinc-800 transition-all">
              Get Started
            </Link>
          </div>
        </div>
      </header>

      <main className="relative z-10">
        <HeroSignature />
        <PainAgitation />
        <AIIntelligence />
        <ProductShowcase />
      </main>

      <OSFooter />
    </div>
  );
}

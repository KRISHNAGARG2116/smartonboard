import React, { type ReactNode } from 'react';

interface SteepHeroProps {
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export default function SteepHero({
  children,
  className = '',
  style,
}: SteepHeroProps) {
  return (
    <div
      className={`steep-hero ${className}`}
      style={{
        position: 'relative',
        width: '100%',
        paddingTop: 'var(--spacing-96)',
        paddingBottom: 'var(--spacing-96)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        overflow: 'visible',
        ...style,
      }}
    >
      {/* Centered Peach Dawn radial gradient glow */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '600px',
          height: '600px',
          background: 'radial-gradient(circle, var(--color-apricot-wash) 0%, rgba(251, 225, 209, 0) 70%)',
          opacity: 0.35,
          pointerEvents: 'none',
          zIndex: 0,
        }}
      />

      <div style={{ position: 'relative', zIndex: 1, width: '100%' }}>
        {children}
      </div>
    </div>
  );
}

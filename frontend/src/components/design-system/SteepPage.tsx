import React, { ReactNode } from 'react';

interface SteepPageProps {
  children: ReactNode;
  bg?: 'fog' | 'canvas';
  constrained?: boolean;
  className?: string;
  style?: React.CSSProperties;
}

export default function SteepPage({
  children,
  bg = 'fog',
  constrained = true,
  className = '',
  style,
  ...props
}: SteepPageProps) {
  const pageStyle: React.CSSProperties = {
    minHeight: '100vh',
    background: bg === 'fog' ? 'var(--bg)' : 'var(--surface-canvas)',
    color: 'var(--text)',
    fontFamily: 'var(--font-sans)',
    display: 'flex',
    flexDirection: 'column',
    ...style,
  };

  const containerStyle: React.CSSProperties = constrained ? {
    width: '100%',
    maxWidth: 'var(--page-max-width)',
    margin: '0 auto',
    paddingInline: 'var(--spacing-24)',
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
  } : {
    width: '100%',
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
  };

  return (
    <div className={`steep-page ${className}`} style={pageStyle} {...props}>
      <div style={containerStyle}>
        {children}
      </div>
    </div>
  );
}

import React, { type ReactNode, type HTMLAttributes } from 'react';

interface SteepSectionProps extends HTMLAttributes<HTMLElement> {
  children: ReactNode;
  bg?: 'canvas' | 'fog';
  gap?: string;
}

export default function SteepSection({
  children,
  bg = 'canvas',
  gap = 'var(--spacing-80)',
  className = '',
  style,
  ...props
}: SteepSectionProps) {
  const sectionStyle: React.CSSProperties = {
    background: bg === 'fog' ? 'var(--surface-fog)' : 'var(--surface-canvas)',
    paddingTop: gap,
    paddingBottom: gap,
    position: 'relative',
    zIndex: 1,
    ...style,
  };

  return (
    <section className={className} style={sectionStyle} {...(props as any)}>
      {children}
    </section>
  );
}

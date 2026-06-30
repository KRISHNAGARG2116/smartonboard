import React, { type ReactNode } from 'react';
import SteepCard from './SteepCard';

interface SteepChartCardProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  variant?: 'default' | 'warm' | 'cool';
  className?: string;
  style?: React.CSSProperties;
}

export default function SteepChartCard({
  title,
  subtitle,
  children,
  variant = 'default',
  className = '',
  style,
}: SteepChartCardProps) {
  const getTitleColor = () => {
    if (variant === 'warm') return 'var(--color-rust)';
    return 'var(--color-ink)';
  };

  return (
    <SteepCard variant={variant} className={className} style={style}>
      <div style={{ marginBottom: 'var(--spacing-20)' }}>
        <h3
          style={{
            fontFamily: 'var(--font-sohne)',
            fontSize: '15px',
            fontWeight: 500,
            color: getTitleColor(),
            letterSpacing: '-0.009em',
            margin: 0,
          }}
        >
          {title}
        </h3>
        {subtitle && (
          <p
            style={{
              fontFamily: 'var(--font-sohne)',
              fontSize: '12px',
              color: 'var(--color-ash)',
              marginTop: 'var(--spacing-4)',
              margin: 0,
            }}
          >
            {subtitle}
          </p>
        )}
      </div>

      <div style={{ position: 'relative', width: '100%' }}>
        {children}
      </div>
    </SteepCard>
  );
}

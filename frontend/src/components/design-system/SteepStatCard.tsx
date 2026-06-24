import React, { ReactNode } from 'react';
import SteepCard from './SteepCard';

interface SteepStatCardProps {
  title: string;
  value: string | number;
  delta?: string | number;
  deltaType?: 'positive' | 'negative' | 'neutral';
  icon?: ReactNode;
  variant?: 'default' | 'warm' | 'cool';
  className?: string;
  style?: React.CSSProperties;
}

export default function SteepStatCard({
  title,
  value,
  delta,
  deltaType = 'neutral',
  icon,
  variant = 'default',
  className = '',
  style,
}: SteepStatCardProps) {
  const getDeltaColor = () => {
    if (deltaType === 'positive') return 'var(--success)';
    if (deltaType === 'negative') return 'var(--color-rust)'; // Rust as red
    return 'var(--text-tertiary)';
  };

  const getDeltaIcon = () => {
    if (deltaType === 'positive') return '↑';
    if (deltaType === 'negative') return '↓';
    return '';
  };

  return (
    <SteepCard variant={variant} className={className} style={style}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span
          style={{
            fontSize: 'var(--text-caption)',
            color: variant === 'warm' ? 'var(--color-rust)' : 'var(--text-secondary)',
            fontWeight: 500,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          {title}
        </span>
        {icon && <span style={{ fontSize: '18px' }}>{icon}</span>}
      </div>
      <div
        style={{
          fontSize: 'var(--text-heading-sm)',
          fontWeight: 480,
          marginTop: 'var(--spacing-12)',
          color: variant === 'warm' ? 'var(--color-rust)' : 'var(--color-ink)',
          display: 'flex',
          alignItems: 'baseline',
          gap: 'var(--spacing-8)',
        }}
      >
        <span>{value}</span>
      </div>
      {delta && (
        <div
          style={{
            fontSize: '11px',
            color: getDeltaColor(),
            fontWeight: 500,
            marginTop: 'var(--spacing-8)',
          }}
        >
          {getDeltaIcon()} {delta}
        </div>
      )}
    </SteepCard>
  );
}

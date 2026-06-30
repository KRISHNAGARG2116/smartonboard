import React, { type ReactNode, type HTMLAttributes } from 'react';

interface SteepCardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  variant?: 'default' | 'warm' | 'cool' | 'flat';
  padding?: 'default' | 'compact' | 'none';
}

export default function SteepCard({
  children,
  variant = 'default',
  padding = 'default',
  className = '',
  style,
  ...props
}: SteepCardProps) {
  const getBackground = () => {
    switch (variant) {
      case 'warm':
        return 'var(--surface-warm-tint)';
      case 'cool':
        return 'var(--surface-cool-tint)';
      case 'default':
      case 'flat':
      default:
        return 'var(--surface-card)';
    }
  };

  const getPadding = () => {
    switch (padding) {
      case 'compact':
        return 'var(--spacing-12)';
      case 'none':
        return '0';
      case 'default':
      default:
        return 'var(--spacing-24)';
    }
  };

  const cardStyle: React.CSSProperties = {
    background: getBackground(),
    borderRadius: 'var(--radius-cards)',
    padding: getPadding(),
    boxShadow: variant === 'flat' ? 'none' : 'var(--shadow-subtle)',
    border: '1px solid var(--border)',
    transition: 'transform var(--duration-normal) var(--ease-out), border-color var(--duration-normal) var(--ease-out), box-shadow var(--duration-normal) var(--ease-out)',
    ...style,
  };

  return (
    <div className={`card ${className}`} style={cardStyle} {...props}>
      {children}
    </div>
  );
}

import React, { ReactNode } from 'react';

interface SteepBadgeProps {
  children: ReactNode;
  variant?: 'neutral' | 'success' | 'warning' | 'danger' | 'interview' | 'hire' | 'reject';
  className?: string;
  style?: React.CSSProperties;
}

export default function SteepBadge({
  children,
  variant = 'neutral',
  className = '',
  style,
  ...props
}: SteepBadgeProps) {
  const getBadgeClass = () => {
    switch (variant) {
      case 'success':
        return 'badge--success';
      case 'warning':
        return 'badge--warning';
      case 'danger':
        return 'badge--danger';
      case 'interview':
        return 'badge--interview';
      case 'hire':
        return 'badge--hire';
      case 'reject':
        return 'badge--reject';
      case 'neutral':
      default:
        return 'badge--neutral';
    }
  };

  return (
    <span
      className={`badge ${getBadgeClass()} ${className}`}
      style={style}
      {...props}
    >
      {children}
    </span>
  );
}

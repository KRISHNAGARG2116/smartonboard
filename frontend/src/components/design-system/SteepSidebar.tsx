import React, { type ReactNode } from 'react';

interface SteepSidebarProps {
  children?: ReactNode;
  logo?: ReactNode;
  footer?: ReactNode;
  width?: string;
  className?: string;
  style?: React.CSSProperties;
}

export default function SteepSidebar({
  children,
  logo,
  footer,
  width = '240px',
  className = '',
  style,
}: SteepSidebarProps) {
  return (
    <aside
      className={`steep-sidebar ${className}`}
      style={{
        width,
        minWidth: width,
        background: 'var(--surface-fog)',
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        borderRight: '1px solid rgba(23, 25, 28, 0.04)', // extremely faint right border or borderless
        padding: 'var(--spacing-24) var(--spacing-16)',
        boxSizing: 'border-box',
        position: 'sticky',
        top: 0,
        zIndex: 50,
        ...style,
      }}
    >
      {logo && (
        <div style={{ marginBottom: 'var(--spacing-32)', paddingInline: 'var(--spacing-8)' }}>
          {logo}
        </div>
      )}

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 'var(--spacing-16)', overflowY: 'auto' }}>
        {children}
      </div>

      {footer && (
        <div style={{ marginTop: 'auto', paddingTop: 'var(--spacing-16)', paddingInline: 'var(--spacing-8)' }}>
          {footer}
        </div>
      )}
    </aside>
  );
}

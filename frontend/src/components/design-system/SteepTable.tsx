import React, { type ReactNode } from 'react';

interface SteepTableProps {
  headers: string[];
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export default function SteepTable({
  headers = [],
  children,
  className = '',
  style,
}: SteepTableProps) {
  return (
    <div
      className="table-wrap"
      style={{
        width: '100%',
        overflowX: 'auto',
        WebkitOverflowScrolling: 'touch',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-xl)',
        background: 'var(--surface-canvas)',
        boxShadow: 'var(--shadow-subtle)',
        ...style,
      }}
    >
      <table
        className={`steep-table ${className}`}
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          textAlign: 'left',
          fontSize: '14px',
          fontFamily: 'var(--font-sohne)',
        }}
      >
        <thead>
          <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface-fog)' }}>
            {headers.map((header, idx) => (
              <th
                key={idx}
                style={{
                  padding: 'var(--spacing-12) var(--spacing-20)',
                  fontWeight: 500,
                  fontSize: '11px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: 'var(--color-graphite)',
                }}
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {children}
        </tbody>
      </table>
    </div>
  );
}

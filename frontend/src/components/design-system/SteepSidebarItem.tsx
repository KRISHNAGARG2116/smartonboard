import { type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';

interface SteepSidebarItemProps {
  to: string;
  label: string;
  icon: ReactNode;
  active: boolean;
  collapsed?: boolean;
}

export default function SteepSidebarItem({
  to,
  label,
  icon,
  active,
  collapsed = false,
}: SteepSidebarItemProps) {
  return (
    <Link
      to={to}
      className={`btn btn--ghost btn--block ${active ? 'nav-link--active' : ''}`}
      style={{
        position: 'relative',
        justifyContent: 'flex-start',
        padding: '10px 14px',
        borderRadius: '12px',
        fontSize: '13.5px',
        fontWeight: active ? 500 : 400,
        color: active ? 'var(--color-ink)' : 'var(--text-secondary)',
        background: 'transparent',
      }}
    >
      {active && (
        <motion.div
          layoutId="active-indicator-sidebar"
          style={{
            position: 'absolute',
            inset: '2px 4px',
            backgroundColor: 'var(--color-pure-white)',
            borderRadius: '12px',
            boxShadow: 'var(--shadow-subtle)',
            zIndex: 0,
          }}
          transition={{ type: 'spring', stiffness: 380, damping: 30 }}
        />
      )}
      <span style={{ display: 'grid', placeItems: 'center', minWidth: '20px', marginRight: collapsed ? '0' : '8px', zIndex: 1 }}>
        {icon}
      </span>
      {!collapsed && <span style={{ zIndex: 1 }}>{label}</span>}
    </Link>
  );
}

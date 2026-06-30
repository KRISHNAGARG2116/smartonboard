import { type ReactNode } from 'react';
import { Link } from 'react-router-dom';

interface SteepNavbarProps {
  logoText?: string;
  links?: { label: string; to?: string; href?: string }[];
  actions?: ReactNode;
  className?: string;
}

export default function SteepNavbar({
  logoText = 'SmartOnboard',
  links = [],
  actions,
  className = '',
}: SteepNavbarProps) {
  return (
    <nav
      className={`app-header ${className}`}
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        height: 'var(--header-h)',
        background: 'var(--surface-canvas)',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        paddingInline: 'var(--spacing-24)',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 'var(--page-max-width)',
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-32)' }}>
          <Link
            to="/"
            className="brand font-signifier"
            style={{
              fontSize: 'var(--text-body-lg)',
              fontWeight: 500,
              color: 'var(--color-ink)',
              letterSpacing: '-0.015em',
            }}
          >
            {logoText}
          </Link>

          {links.length > 0 && (
            <div className="header-nav" style={{ display: 'flex', gap: 'var(--spacing-16)' }}>
              {links.map((link, idx) => {
                if (link.to) {
                  return (
                    <Link
                      key={idx}
                      to={link.to}
                      className="nav-link"
                      style={{
                        fontFamily: 'var(--font-sohne)',
                        fontSize: '14px',
                        fontWeight: 450,
                        color: 'var(--color-ash)',
                      }}
                    >
                      {link.label}
                    </Link>
                  );
                }
                return (
                  <a
                    key={idx}
                    href={link.href}
                    className="nav-link"
                    style={{
                      fontFamily: 'var(--font-sohne)',
                      fontSize: '14px',
                      fontWeight: 450,
                      color: 'var(--color-ash)',
                    }}
                  >
                    {link.label}
                  </a>
                );
              })}
            </div>
          )}
        </div>

        {actions && (
          <div className="header-actions" style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-8)' }}>
            {actions}
          </div>
        )}
      </div>
    </nav>
  );
}

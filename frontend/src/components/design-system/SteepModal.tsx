import { type ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import SteepCard from './SteepCard';

interface SteepModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  footer?: ReactNode;
  className?: string;
}

export default function SteepModal({
  isOpen,
  onClose,
  title,
  children,
  footer,
  className = '',
}: SteepModalProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 1000,
            display: 'grid',
            placeItems: 'center',
            padding: 'var(--spacing-16)',
            boxSizing: 'border-box',
          }}
        >
          {/* Overlay backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            style={{
              position: 'absolute',
              inset: 0,
              background: 'rgba(23, 25, 28, 0.2)', // Ink with low opacity
              backdropFilter: 'blur(4px)',
            }}
          />

          {/* Modal Container */}
          <motion.div
            initial={{ opacity: 0, y: 15, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.98 }}
            transition={{ type: 'spring', damping: 25, stiffness: 350 }}
            style={{
              position: 'relative',
              width: '100%',
              maxWidth: '520px',
              zIndex: 1001,
            }}
          >
            <SteepCard style={{ padding: 'var(--spacing-28)' }} className={className}>
              {/* Header */}
              {title && (
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'baseline',
                    marginBottom: 'var(--spacing-20)',
                  }}
                >
                  <h2
                    className="font-signifier"
                    style={{
                      fontSize: 'var(--text-subheading)',
                      color: 'var(--color-ink)',
                      fontWeight: 400,
                    }}
                  >
                    {title}
                  </h2>
                  <button
                    onClick={onClose}
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      color: 'var(--color-graphite)',
                      fontSize: '18px',
                      padding: 'var(--spacing-4)',
                    }}
                    aria-label="Close modal"
                  >
                    ✕
                  </button>
                </div>
              )}

              {/* Body */}
              <div style={{ color: 'var(--color-ash)', fontSize: 'var(--text-body)', lineHeight: 1.45 }}>
                {children}
              </div>

              {/* Footer */}
              {footer && (
                <div
                  style={{
                    marginTop: 'var(--spacing-28)',
                    display: 'flex',
                    justifyContent: 'flex-end',
                    gap: 'var(--spacing-12)',
                  }}
                >
                  {footer}
                </div>
              )}
            </SteepCard>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

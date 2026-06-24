import React, { ButtonHTMLAttributes, ReactNode } from 'react';
import { Link } from 'react-router-dom';

interface SteepButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'ghost' | 'accent';
  size?: 'sm' | 'md' | 'lg';
  block?: boolean;
  to?: string;
  href?: string;
}

export default function SteepButton({
  children,
  variant = 'primary',
  size = 'md',
  block = false,
  to,
  href,
  className = '',
  style,
  ...props
}: SteepButtonProps) {
  const getButtonClass = () => {
    let base = 'btn';
    if (variant === 'primary') base += ' btn--primary';
    else if (variant === 'secondary') base += ' btn--secondary';
    else if (variant === 'ghost') base += ' btn--ghost';
    else if (variant === 'accent') base += ' btn--accent';

    if (size === 'sm') base += ' btn--sm';
    else if (size === 'lg') base += ' btn--lg';

    if (block) base += ' btn--block';

    return base;
  };

  const buttonClass = `${getButtonClass()} ${className}`;

  if (to) {
    return (
      <Link to={to} className={buttonClass} style={style} {...(props as any)}>
        {children}
      </Link>
    );
  }

  if (href) {
    return (
      <a href={href} className={buttonClass} style={style} {...(props as any)}>
        {children}
      </a>
    );
  }

  return (
    <button className={buttonClass} style={style} {...props}>
      {children}
    </button>
  );
}

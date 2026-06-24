import React, { InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react';

interface SteepInputProps {
  label?: string;
  hint?: string;
  error?: string;
  textarea?: boolean;
  select?: boolean;
  options?: { value: string; label: string }[];
  containerStyle?: React.CSSProperties;
}

type CombinedProps = SteepInputProps & 
  InputHTMLAttributes<HTMLInputElement> & 
  SelectHTMLAttributes<HTMLSelectElement> & 
  TextareaHTMLAttributes<HTMLTextareaElement>;

export default function SteepInput({
  label,
  hint,
  error,
  textarea = false,
  select = false,
  options = [],
  containerStyle,
  className = '',
  id,
  ...props
}: CombinedProps) {
  const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;

  const renderInput = () => {
    if (textarea) {
      return (
        <textarea
          id={inputId}
          className={`form-textarea ${className}`}
          {...(props as any)}
        />
      );
    }

    if (select) {
      return (
        <select
          id={inputId}
          className={`form-select ${className}`}
          {...(props as any)}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      );
    }

    return (
      <input
        id={inputId}
        className={`form-input ${className}`}
        {...(props as any)}
      />
    );
  };

  return (
    <div className="form-group" style={containerStyle}>
      {label && (
        <label htmlFor={inputId} className="form-label">
          {label}
        </label>
      )}
      {renderInput()}
      {error && (
        <div className="form-hint" style={{ color: 'var(--danger)', fontWeight: 500, marginTop: 'var(--spacing-4)' }}>
          {error}
        </div>
      )}
      {!error && hint && <div className="form-hint">{hint}</div>}
    </div>
  );
}

import React from 'react'

interface JobPreviewHeaderProps {
  title: string
  companyName?: string
  department: string
  action?: React.ReactNode
}

export default function JobPreviewHeader({ title, companyName, department, action }: JobPreviewHeaderProps) {
  return (
    <div 
      style={{ 
        padding: 'var(--space-6)', 
        borderBottom: '1px solid var(--border)', 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'flex-start',
        gap: '12px'
      }}
    >
      <div>
        <h2 style={{ fontSize: 'var(--text-lg)', fontWeight: 800, letterSpacing: '-0.02em', margin: 0 }}>
          {title || 'Job Posting Title'}
        </h2>
        <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginTop: '4px', margin: 0 }}>
          {companyName || 'Our Company'} · <strong>{department || 'General'}</strong>
        </p>
      </div>
      {action}
    </div>
  )
}

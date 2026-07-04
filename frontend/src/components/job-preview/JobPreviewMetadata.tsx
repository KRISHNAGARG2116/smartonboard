interface JobPreviewMetadataProps {
  startDate?: string | null
  workplaceType: string
  employmentType: string
  location?: string
  salaryMin?: number | string | null
  salaryMax?: number | string | null
  currency?: string
  hideSalary?: boolean
  openings?: number
  benefits?: string[]
}

export default function JobPreviewMetadata({
  startDate,
  workplaceType,
  employmentType,
  location,
  salaryMin,
  salaryMax,
  currency = 'USD',
  hideSalary = false,
  openings = 1,
  benefits = []
}: JobPreviewMetadataProps) {
  const displaySalary = () => {
    if (hideSalary) return 'Salary: Not Disclosed'
    if (salaryMin && salaryMax) {
      return `${currency} ${Number(salaryMin).toLocaleString()} - ${Number(salaryMax).toLocaleString()} / Year`
    }
    if (salaryMin) {
      return `From ${currency} ${Number(salaryMin).toLocaleString()} / Year`
    }
    if (salaryMax) {
      return `Up to ${currency} ${Number(salaryMax).toLocaleString()} / Year`
    }
    return 'Salary: Not Specified'
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 750, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)', margin: 0 }}>
        Job Details & Logistics
      </h4>
      <div 
        style={{ 
          display: 'grid', 
          gridTemplateColumns: '1fr 1fr', 
          gap: 'var(--space-4)', 
          background: 'var(--color-pure-white)', 
          padding: 'var(--space-4)', 
          borderRadius: 'var(--radius-cards)', 
          border: '1px solid var(--border)' 
        }}
      >
        <div>
          <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', display: 'block' }}>Target Start Date</span>
          <strong style={{ fontSize: 'var(--text-xs)', color: 'var(--text)' }}>
            {startDate ? new Date(startDate).toLocaleDateString() : 'Immediate'}
          </strong>
        </div>

        <div>
          <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', display: 'block' }}>Setting & Workplace</span>
          <strong style={{ fontSize: 'var(--text-xs)', color: 'var(--text)' }}>
            {workplaceType || 'On-site'} · {employmentType || 'Full Time'}
          </strong>
        </div>

        <div>
          <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', display: 'block' }}>Office Location</span>
          <strong style={{ fontSize: 'var(--text-xs)', color: 'var(--text)' }}>
            {location || 'Not Disclosed'}
          </strong>
        </div>

        <div>
          <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', display: 'block' }}>Openings Available</span>
          <strong style={{ fontSize: 'var(--text-xs)', color: 'var(--text)' }}>
            {openings} {openings === 1 ? 'Role' : 'Roles'}
          </strong>
        </div>

        <div style={{ gridColumn: 'span 2' }}>
          <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', display: 'block' }}>Compensation Package</span>
          <strong style={{ fontSize: 'var(--text-xs)', color: 'var(--text)' }}>
            {displaySalary()}
          </strong>
        </div>

        {benefits.length > 0 && (
          <div style={{ gridColumn: 'span 2', borderTop: '1px solid var(--border)', paddingTop: 'var(--space-3)', marginTop: 'var(--space-1)' }}>
            <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', display: 'block', marginBottom: '8px' }}>Perks & Benefits Offered</span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {benefits.map((b, idx) => (
                <span 
                  key={idx} 
                  style={{ 
                    fontSize: '10px', 
                    padding: '2px 8px', 
                    borderRadius: '6px', 
                    background: 'var(--bg-subtle)', 
                    color: 'var(--text)',
                    border: '1px solid var(--border)',
                    fontWeight: 500
                  }}
                >
                  {b}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

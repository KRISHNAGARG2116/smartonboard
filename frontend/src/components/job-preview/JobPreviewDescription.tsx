export interface ParsedSections {
  overview: string
  responsibilities: string
  requirements: string
}

export function parseDescription(desc: string): ParsedSections {
  if (!desc) return { overview: '', responsibilities: '', requirements: '' }

  const overviewMarker = '### Role Overview'
  const responsibilitiesMarker = '### Key Responsibilities'
  const requirementsMarker = '### Requirements & Qualifications'

  let overview = ''
  let responsibilities = ''
  let requirements = ''

  if (desc.includes(overviewMarker) || desc.includes(responsibilitiesMarker) || desc.includes(requirementsMarker)) {
    const parts = desc.split(/### .+/g)
    const headers = [...desc.matchAll(/### (.+)/g)].map(m => m[0])

    let partIdx = 1 
    for (let i = 0; i < headers.length; i++) {
      const header = headers[i]
      const content = parts[partIdx]?.trim() || ''
      if (header.includes('Role Overview')) {
        overview = content
      } else if (header.includes('Key Responsibilities')) {
        responsibilities = content
      } else if (header.includes('Requirements & Qualifications')) {
        requirements = content
      }
      partIdx++
    }
  } else {
    overview = desc
  }

  return { overview, responsibilities, requirements }
}

export function combineDescription(overview: string, responsibilities: string, requirements: string): string {
  return `### Role Overview\n${overview || ''}\n\n### Key Responsibilities\n${responsibilities || ''}\n\n### Requirements & Qualifications\n${requirements || ''}`
}

interface JobPreviewDescriptionProps {
  description: string
}

export default function JobPreviewDescription({ description }: JobPreviewDescriptionProps) {
  const { overview, responsibilities, requirements } = parseDescription(description)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      {/* Overview Section */}
      {overview && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 750, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)', margin: 0 }}>
            Role Overview
          </h4>
          <div 
            style={{ 
              fontSize: 'var(--text-sm)', 
              color: 'var(--text)', 
              lineHeight: 1.6, 
              whiteSpace: 'pre-wrap',
              background: 'var(--color-pure-white)',
              padding: 'var(--space-4)',
              borderRadius: 'var(--radius-cards)',
              border: '1px solid var(--border)'
            }}
          >
            {overview}
          </div>
        </div>
      )}

      {/* Responsibilities Section */}
      {responsibilities && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 750, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)', margin: 0 }}>
            Key Responsibilities
          </h4>
          <div 
            style={{ 
              fontSize: 'var(--text-sm)', 
              color: 'var(--text)', 
              lineHeight: 1.6, 
              whiteSpace: 'pre-wrap',
              background: 'var(--color-pure-white)',
              padding: 'var(--space-4)',
              borderRadius: 'var(--radius-cards)',
              border: '1px solid var(--border)'
            }}
          >
            {responsibilities}
          </div>
        </div>
      )}

      {/* Requirements Section */}
      {requirements && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 750, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)', margin: 0 }}>
            Requirements & Qualifications
          </h4>
          <div 
            style={{ 
              fontSize: 'var(--text-sm)', 
              color: 'var(--text)', 
              lineHeight: 1.6, 
              whiteSpace: 'pre-wrap',
              background: 'var(--color-pure-white)',
              padding: 'var(--space-4)',
              borderRadius: 'var(--radius-cards)',
              border: '1px solid var(--border)'
            }}
          >
            {requirements}
          </div>
        </div>
      )}
    </div>
  )
}

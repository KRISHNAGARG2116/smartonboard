import React, { useState } from 'react'

interface TalentSearchProps {
  onSelectCandidate: (id: string) => void
}

export default function TalentSearch({ onSelectCandidate }: TalentSearchProps) {
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [results, setResults] = useState<any[]>([])
  const [parsedFilters, setParsedFilters] = useState<any | null>(null)

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!query) return
    setSearching(true)
    
    // Simulate natural language parsing translation delay
    setTimeout(() => {
      setSearching(false)
      setParsedFilters({
        skills: ['React', 'Python'],
        location: query.toLowerCase().includes('sf') || query.toLowerCase().includes('francisco') ? 'San Francisco' : 'Austin',
        experience_years: query.toLowerCase().includes('senior') ? '5+' : 'Any',
        is_lookalike: query.toLowerCase().includes('similar to') || query.toLowerCase().includes('lookalike')
      })

      setResults([
        { id: 'ff8ad11b-f3c2-414c-bf3c-51fb5743d0a3', name: 'John Doe', email: 'john.doe@example.com', title: 'Senior Backend Engineer', location: 'San Francisco, CA', match: 92, skills: ['Python', 'React', 'Go'] },
        { id: 'cand-2', name: 'Marcus Wright', email: 'marcus.wright@cyberdyne.com', title: 'Fullstack Engineer', location: 'San Francisco, CA', match: 86, skills: ['React', 'Node.js', 'Python'] },
        { id: 'cand-3', name: 'Kyle Reese', email: 'kyle.reese@resistance.net', title: 'Frontend Developer', location: 'Austin, TX', match: 74, skills: ['React', 'TypeScript', 'CSS'] }
      ])
    }, 800)
  }

  const suggestions = {
    recent_searches: ['React developers in SF', 'Senior Python Engineers', 'Hired profile lookalikes'],
    pinned_searches: ['Silver Medalists - React', 'Austin Python leads'],
    saved_searches: ['2026 Grad interns', 'Gusto handoffs pipeline'],
    frequently_used_filters: ['Experience > 5 years', 'Location: Austin, TX'],
    suggested_searches: ['Backend engineers similar to John Doe']
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px', fontFamily: 'var(--font-sans, sans-serif)' }}>
      {/* Page Title */}
      <div>
        <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 800, letterSpacing: '-0.03em' }}>
          Natural Language Sourcing Search
        </h2>
        <p style={{ margin: '4px 0 0 0', fontSize: '14px', color: 'var(--text-secondary)' }}>
          Search for candidate profiles using plain English queries or lookalike prompts
        </p>
      </div>

      {/* NLP Search Bar Form */}
      <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '12px' }}>
        <input
          type="text"
          placeholder="e.g. Find senior React developers in SF, or candidates similar to John Doe"
          value={query}
          onChange={e => setQuery(e.target.value)}
          style={{
            flex: 1,
            padding: '14px 20px',
            borderRadius: '12px',
            border: '1px solid var(--border)',
            background: 'var(--bg-card)',
            fontSize: '14.5px',
            outline: 'none',
            boxShadow: 'var(--shadow-premium, 0 4px 30px -10px rgba(0,0,0,0.03))',
            transition: 'border-color 0.15s ease'
          }}
        />
        <button
          type="submit"
          style={{
            padding: '0 28px',
            borderRadius: '12px',
            background: 'var(--accent)',
            color: '#fff',
            fontWeight: 700,
            border: 'none',
            cursor: 'pointer',
            fontSize: '14px'
          }}
        >
          {searching ? 'Parsing Query...' : 'AI Search'}
        </button>
      </form>

      {/* Structured Translation & Candidate Results */}
      {parsedFilters && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', animation: 'fadeIn 0.2s' }}>
          {/* AI Search Translation Card */}
          <div
            style={{
              background: '#eff6ff',
              border: '1px solid #bfdbfe',
              borderRadius: '12px',
              padding: '16px 20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}
          >
            <div>
              <span style={{ fontSize: '10.5px', textTransform: 'uppercase', fontWeight: 700, color: 'var(--accent)' }}>
                AI Search Translation
              </span>
              <div style={{ display: 'flex', gap: '12px', marginTop: '6px', flexWrap: 'wrap' }}>
                {parsedFilters.skills.map((s: string) => (
                  <span key={s} style={{ fontSize: '12px', background: '#fff', padding: '2px 8px', borderRadius: '4px', border: '1px solid #bfdbfe', fontWeight: 650 }}>
                    Skill: {s}
                  </span>
                ))}
                {parsedFilters.location && (
                  <span style={{ fontSize: '12px', background: '#fff', padding: '2px 8px', borderRadius: '4px', border: '1px solid #bfdbfe', fontWeight: 650 }}>
                    Location: {parsedFilters.location}
                  </span>
                )}
                {parsedFilters.experience_years !== 'Any' && (
                  <span style={{ fontSize: '12px', background: '#fff', padding: '2px 8px', borderRadius: '4px', border: '1px solid #bfdbfe', fontWeight: 650 }}>
                    Experience: {parsedFilters.experience_years} yrs
                  </span>
                )}
                {parsedFilters.is_lookalike && (
                  <span style={{ fontSize: '12px', background: '#dbeafe', color: 'var(--accent)', padding: '2px 8px', borderRadius: '4px', fontWeight: 700 }}>
                    ✦ PGVector Lookalike Search
                  </span>
                )}
              </div>
            </div>
            <button
              type="button"
              className="btn btn--link"
              style={{ fontSize: '13px', fontWeight: 700, padding: 0 }}
              onClick={() => {
                setParsedFilters(null)
                setResults([])
                setQuery('')
              }}
            >
              Clear Filters
            </button>
          </div>

          {/* Results List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>Matching Profiles ({results.length})</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {results.map((res) => (
                <div
                  key={res.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '20px',
                    borderRadius: '12px',
                    border: '1px solid var(--border)',
                    background: 'var(--bg-card)'
                  }}
                >
                  <div>
                    <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>{res.name}</h4>
                    <p style={{ margin: '4px 0', fontSize: '13px', color: 'var(--text-secondary)' }}>
                      {res.title} • {res.location}
                    </p>
                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '6px' }}>
                      {res.skills.map((s: string) => (
                        <span key={s} style={{ fontSize: '11px', background: 'rgba(0,0,0,0.03)', padding: '2px 6px', borderRadius: '4px' }}>
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <span style={{ fontSize: '14px', fontWeight: 700, color: '#10b981' }}>{res.match}% Match</span>
                    <button
                      type="button"
                      className="btn btn--outline"
                      style={{ padding: '8px 16px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer' }}
                      onClick={() => onSelectCandidate(res.id)}
                    >
                      Open CRM Card
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* AI Search Memory Panels (Show only if no active search) */}
      {!parsedFilters && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '32px' }}>
          <div>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: 700 }}>Search Suggestions & Memory</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 700 }}>
                  Recent Searches
                </span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '8px' }}>
                  {suggestions.recent_searches.map(s => (
                    <button
                      key={s}
                      type="button"
                      style={{ textAlign: 'left', padding: '8px', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '13px', cursor: 'pointer', color: 'var(--text-secondary)' }}
                      onClick={() => {
                        setQuery(s)
                      }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 700 }}>
                  Suggested Searches
                </span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '8px' }}>
                  {suggestions.suggested_searches.map(s => (
                    <button
                      key={s}
                      type="button"
                      style={{ textAlign: 'left', padding: '8px', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '13px', cursor: 'pointer', color: 'var(--text-secondary)' }}
                      onClick={() => {
                        setQuery(s)
                      }}
                    >
                      ✦ {s}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: 700 }}>Collections</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 700 }}>
                  📌 Pinned & Saved Searches
                </span>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '8px' }}>
                  {suggestions.pinned_searches.map(s => (
                    <button
                      key={s}
                      type="button"
                      style={{ padding: '6px 12px', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '20px', fontSize: '12px', cursor: 'pointer' }}
                      onClick={() => setQuery(s)}
                    >
                      📌 {s}
                    </button>
                  ))}
                  {suggestions.saved_searches.map(s => (
                    <button
                      key={s}
                      type="button"
                      style={{ padding: '6px 12px', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '20px', fontSize: '12px', cursor: 'pointer' }}
                      onClick={() => setQuery(s)}
                    >
                      💾 {s}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 700 }}>
                  Frequently Used Filters
                </span>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '8px' }}>
                  {suggestions.frequently_used_filters.map(s => (
                    <button
                      key={s}
                      type="button"
                      style={{ padding: '6px 12px', background: 'rgba(0,0,0,0.03)', border: 'none', borderRadius: '4px', fontSize: '12px', cursor: 'pointer', color: 'var(--text-secondary)' }}
                      onClick={() => setQuery(s)}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

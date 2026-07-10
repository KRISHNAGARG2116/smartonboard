import { useState } from 'react'

interface TalentPoolsProps {
  onSelectCandidate: (id: string) => void
}

interface Pool {
  id: string
  name: string
  description: string
  color: string
  icon: string
  visibility: string
  is_dynamic: boolean
  dynamic_rules: any
  rule_version: number
  member_count: number
}

export default function TalentPools({ onSelectCandidate }: TalentPoolsProps) {
  const [pools, setPools] = useState<Pool[]>([
    {
      id: 'pool-1',
      name: 'React Developers (SF)',
      description: 'Senior React leads located in San Francisco Bay Area',
      color: '#3b82f6',
      icon: '⚛️',
      visibility: 'public',
      is_dynamic: true,
      dynamic_rules: { location: 'San Francisco', skills: ['React'] },
      rule_version: 3,
      member_count: 14
    },
    {
      id: 'pool-2',
      name: 'Silver Medalists (Backend)',
      description: 'Candidates who passed final loops for Backend positions',
      color: '#10b981',
      icon: '🥈',
      visibility: 'public',
      is_dynamic: false,
      dynamic_rules: null,
      rule_version: 1,
      member_count: 5
    }
  ])

  const [selectedPool, setSelectedPool] = useState<Pool | null>(pools[0])
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newPoolName, setNewPoolName] = useState('')
  const [newPoolDesc, setNewPoolDesc] = useState('')
  const [isDynamic, setIsDynamic] = useState(false)
  const [ruleLocation, setRuleLocation] = useState('')
  const [ruleSkills, setRuleSkills] = useState('')
  const [showHistory, setShowHistory] = useState(false)

  const handleCreatePool = () => {
    if (!newPoolName) return
    const newPool: Pool = {
      id: `pool-${Date.now()}`,
      name: newPoolName,
      description: newPoolDesc,
      color: '#6b7280',
      icon: isDynamic ? '⚙️' : '📁',
      visibility: 'public',
      is_dynamic: isDynamic,
      dynamic_rules: isDynamic ? { location: ruleLocation, skills: ruleSkills.split(',').map(s => s.trim()) } : null,
      rule_version: 1,
      member_count: 0
    }
    setPools([...pools, newPool])
    setShowCreateModal(false)
    setNewPoolName('')
    setNewPoolDesc('')
    setIsDynamic(false)
    setRuleLocation('')
    setRuleSkills('')
  }

  const handleSoftDelete = (poolId: string) => {
    setPools(pools.filter(p => p.id !== poolId))
    if (selectedPool?.id === poolId) {
      setSelectedPool(null)
    }
  }

  const mockMembers = [
    { id: 'ff8ad11b-f3c2-414c-bf3c-51fb5743d0a3', name: 'John Doe', email: 'john.doe@example.com', location: 'San Francisco, CA', match: 92 },
    { id: 'cand-2', name: 'Marcus Wright', email: 'marcus.wright@cyberdyne.com', location: 'San Francisco, CA', match: 86 },
    { id: 'cand-3', name: 'Sarah Connor', email: 'sarah.connor@cyberdyne.com', location: 'San Francisco, CA', match: 90 }
  ]

  const mockHistory = [
    { version: 3, updated_at: '2 hours ago', updated_by: 'Sarah Connor', rules: { location: 'San Francisco', skills: ['React'] } },
    { version: 2, updated_at: '1 day ago', updated_by: 'John Connor', rules: { location: 'Oakland', skills: ['React', 'TypeScript'] } },
    { version: 1, updated_at: '3 days ago', updated_by: 'Sarah Connor', rules: { location: 'California', skills: ['React'] } }
  ]

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '32px', fontFamily: 'var(--font-sans, sans-serif)' }}>
      {/* Sidebar Pool List */}
      <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>Talent Pools</h3>
          <button
            type="button"
            className="btn btn--primary"
            style={{ fontSize: '12px', padding: '6px 12px', background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer' }}
            onClick={() => setShowCreateModal(true)}
          >
            + Create
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {pools.map(pool => (
            <div
              key={pool.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid ' + (selectedPool?.id === pool.id ? 'var(--accent)' : 'var(--border)'),
                background: selectedPool?.id === pool.id ? 'var(--accent-subtle, #eff6ff)' : 'var(--bg)',
                cursor: 'pointer'
              }}
              onClick={() => {
                setSelectedPool(pool)
                setShowHistory(false)
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '18px' }}>{pool.icon}</span>
                <div>
                  <h4 style={{ margin: 0, fontSize: '13.5px', fontWeight: 650 }}>{pool.name}</h4>
                  <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                    {pool.is_dynamic ? 'Smart Pool' : 'Static Pool'} • {pool.member_count} candidates
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Main Details and Member Viewer */}
      {selectedPool ? (
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '12px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border)', paddingBottom: '16px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '24px' }}>{selectedPool.icon}</span>
                <h3 style={{ margin: 0, fontSize: '20px', fontWeight: 700 }}>{selectedPool.name}</h3>
              </div>
              <p style={{ margin: '6px 0 0 0', fontSize: '13.5px', color: 'var(--text-secondary)' }}>
                {selectedPool.description}
              </p>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              {selectedPool.is_dynamic && (
                <button
                  type="button"
                  className="btn btn--outline"
                  style={{ fontSize: '12px', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer' }}
                  onClick={() => setShowHistory(!showHistory)}
                >
                  {showHistory ? 'View Members' : 'History & Rollback'}
                </button>
              )}
              <button
                type="button"
                className="btn btn--danger"
                style={{ fontSize: '12px', padding: '6px 12px', border: '1px solid #ef4444', color: '#ef4444', background: 'transparent', borderRadius: '6px', cursor: 'pointer' }}
                onClick={() => handleSoftDelete(selectedPool.id)}
              >
                Delete Pool
              </button>
            </div>
          </div>

          {showHistory ? (
            // Dynamic rule rollback panel
            <div>
              <h4 style={{ margin: '0 0 16px 0', fontSize: '15px', fontWeight: 700 }}>Rules Modification History</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {mockHistory.map(hist => (
                  <div key={hist.version} style={{ border: '1px solid var(--border)', borderRadius: '8px', padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <h5 style={{ margin: 0, fontSize: '13.5px', fontWeight: 650 }}>Version {hist.version}</h5>
                      <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                        Updated {hist.updated_at} by {hist.updated_by}
                      </span>
                      <pre style={{ margin: '8px 0 0 0', fontSize: '11px', background: '#f3f4f6', padding: '6px', borderRadius: '4px' }}>
                        {JSON.stringify(hist.rules, null, 2)}
                      </pre>
                    </div>
                    <button
                      type="button"
                      className="btn btn--outline"
                      style={{ fontSize: '12px', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer' }}
                      onClick={() => {
                        setSelectedPool({ ...selectedPool, dynamic_rules: hist.rules, rule_version: selectedPool.rule_version + 1 })
                        setShowHistory(false)
                      }}
                    >
                      Rollback to v{hist.version}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            // Members List
            <div>
              <h4 style={{ margin: '0 0 16px 0', fontSize: '15px', fontWeight: 700 }}>Pool Members ({selectedPool.member_count})</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {mockMembers.map(member => (
                  <div
                    key={member.id}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '16px',
                      borderRadius: '8px',
                      border: '1px solid var(--border)',
                      background: 'var(--bg)'
                    }}
                  >
                    <div>
                      <h5 style={{ margin: 0, fontSize: '14px', fontWeight: 650 }}>{member.name}</h5>
                      <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                        {member.email} • {member.location}
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span style={{ fontSize: '13px', fontWeight: 700, color: '#10b981' }}>{member.match}% Match</span>
                      <button
                        type="button"
                        className="btn btn--outline"
                        style={{ fontSize: '12px', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer' }}
                        onClick={() => onSelectCandidate(member.id)}
                      >
                        Details
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div style={{ display: 'grid', placeItems: 'center', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '12px', color: 'var(--text-secondary)', padding: '48px' }}>
          Select a pool to view details
        </div>
      )}

      {/* Create Pool Modal */}
      {showCreateModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.4)', display: 'grid', placeItems: 'center', zIndex: 1000 }}>
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '16px', padding: '24px', width: '400px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 700 }}>Create Talent Pool</h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '13px', fontWeight: 600 }}>Pool Name</label>
              <input type="text" value={newPoolName} onChange={e => setNewPoolName(e.target.value)} style={{ padding: '8px', borderRadius: '6px', border: '1px solid var(--border)' }} />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '13px', fontWeight: 600 }}>Description</label>
              <textarea value={newPoolDesc} onChange={e => setNewPoolDesc(e.target.value)} style={{ padding: '8px', borderRadius: '6px', border: '1px solid var(--border)', height: '80px' }} />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <input type="checkbox" id="dynamic" checked={isDynamic} onChange={e => setIsDynamic(e.target.checked)} />
              <label htmlFor="dynamic" style={{ fontSize: '13px', fontWeight: 600 }}>Make this a dynamic Smart Pool</label>
            </div>

            {isDynamic && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', border: '1px solid var(--border)', padding: '12px', borderRadius: '8px', background: '#f9fafb' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label style={{ fontSize: '12px', fontWeight: 600 }}>Target Location</label>
                  <input type="text" placeholder="e.g. San Francisco" value={ruleLocation} onChange={e => setRuleLocation(e.target.value)} style={{ padding: '6px', borderRadius: '4px', border: '1px solid var(--border)', fontSize: '12.5px' }} />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label style={{ fontSize: '12px', fontWeight: 600 }}>Required Skills (comma separated)</label>
                  <input type="text" placeholder="e.g. React, Python" value={ruleSkills} onChange={e => setRuleSkills(e.target.value)} style={{ padding: '6px', borderRadius: '4px', border: '1px solid var(--border)', fontSize: '12.5px' }} />
                </div>
              </div>
            )}

            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '8px' }}>
              <button type="button" className="btn btn--outline" onClick={() => setShowCreateModal(false)} style={{ padding: '8px 16px', borderRadius: '8px', cursor: 'pointer' }}>Cancel</button>
              <button type="button" className="btn btn--primary" onClick={handleCreatePool} style={{ padding: '8px 16px', background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>Save Pool</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

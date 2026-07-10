import { useState } from 'react'
import AppLayout from '../../components/AppLayout'

interface PrivacyRequest {
  id: string
  request_type: 'Erasure' | 'Portability'
  candidate_email: string
  status: 'Submitted' | 'In Review' | 'Approved' | 'Rejected' | 'Processing' | 'Completed'
  created_at: string
}

export default function ComplianceDashboard() {
  const [requests, setRequests] = useState<PrivacyRequest[]>([
    {
      id: 'req-401',
      request_type: 'Erasure',
      candidate_email: 'john.smith@gmail.com',
      status: 'Submitted',
      created_at: '2026-07-10 14:20'
    },
    {
      id: 'req-392',
      request_type: 'Portability',
      candidate_email: 'clara.jones@yahoo.com',
      status: 'Completed',
      created_at: '2026-07-08 09:12'
    },
    {
      id: 'req-388',
      request_type: 'Erasure',
      candidate_email: 'dev.rob@github.com',
      status: 'In Review',
      created_at: '2026-07-07 16:45'
    }
  ])

  const handleTransition = (id: string, newStatus: PrivacyRequest['status']) => {
    setRequests(prev =>
      prev.map(r => (r.id === id ? { ...r, status: newStatus } : r))
    )
  }

  const handleDownloadEvidence = () => {
    // Trigger download of zip evidence bundle
    window.open('/api/v1/compliance/evidence-bundle', '_blank')
  }

  return (
    <AppLayout>
      <div
        style={{
          fontFamily: 'var(--font-sans, sans-serif)',
          color: 'var(--text)',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '24px'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 800 }}>Compliance & Data Portability Center</h1>
            <span style={{ fontSize: '12.5px', color: 'var(--text-secondary)' }}>
              Manage GDPR/CCPA subject access requests, Right to Erasure workflows, and download verification records.
            </span>
          </div>
          <button
            type="button"
            className="btn btn--primary"
            style={{
              padding: '10px 18px',
              borderRadius: '8px',
              background: 'var(--accent)',
              color: '#ffffff',
              border: 'none',
              fontWeight: 700,
              cursor: 'pointer'
            }}
            onClick={handleDownloadEvidence}
          >
            📦 Download Evidence Bundle
          </button>
        </div>

        {/* GDPR Request Tracker Table */}
        <div
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: '12px',
            padding: '20px'
          }}
        >
          <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: 700 }}>GDPR / CCPA Active Requests</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13.5px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-secondary)' }}>
                <th style={{ padding: '12px 8px' }}>Request ID</th>
                <th style={{ padding: '12px 8px' }}>Type</th>
                <th style={{ padding: '12px 8px' }}>Candidate Email</th>
                <th style={{ padding: '12px 8px' }}>Status</th>
                <th style={{ padding: '12px 8px' }}>Submitted Date</th>
                <th style={{ padding: '12px 8px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {requests.map(req => (
                <tr key={req.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <td style={{ padding: '12px 8px', fontWeight: 650 }}>{req.id}</td>
                  <td style={{ padding: '12px 8px' }}>{req.request_type}</td>
                  <td style={{ padding: '12px 8px' }}>{req.candidate_email}</td>
                  <td style={{ padding: '12px 8px' }}>
                    <span
                      style={{
                        display: 'inline-block',
                        fontSize: '11px',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        background:
                          req.status === 'Completed' ? '#ecfdf5' :
                          req.status === 'In Review' ? '#fffbeb' : '#eff6ff',
                        color:
                          req.status === 'Completed' ? '#10b981' :
                          req.status === 'In Review' ? '#f59e0b' : 'var(--accent)'
                      }}
                    >
                      ● {req.status}
                    </span>
                  </td>
                  <td style={{ padding: '12px 8px', color: 'var(--text-secondary)' }}>{req.created_at}</td>
                  <td style={{ padding: '12px 8px', textAlign: 'right' }}>
                    {req.status === 'Submitted' && (
                      <button
                        type="button"
                        onClick={() => handleTransition(req.id, 'In Review')}
                        style={{
                          padding: '4px 8px',
                          borderRadius: '4px',
                          border: '1px solid var(--border)',
                          fontSize: '12px',
                          cursor: 'pointer',
                          background: 'none'
                        }}
                      >
                        Start Review
                      </button>
                    )}
                    {req.status === 'In Review' && (
                      <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                        <button
                          type="button"
                          onClick={() => handleTransition(req.id, 'Approved')}
                          style={{
                            padding: '4px 8px',
                            borderRadius: '4px',
                            border: 'none',
                            fontSize: '12px',
                            cursor: 'pointer',
                            background: '#10b981',
                            color: '#ffffff'
                          }}
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          onClick={() => handleTransition(req.id, 'Rejected')}
                          style={{
                            padding: '4px 8px',
                            borderRadius: '4px',
                            border: '1px solid #ef4444',
                            fontSize: '12px',
                            cursor: 'pointer',
                            background: 'none',
                            color: '#ef4444'
                          }}
                        >
                          Reject
                        </button>
                      </div>
                    )}
                    {req.status === 'Approved' && (
                      <button
                        type="button"
                        onClick={() => handleTransition(req.id, 'Processing')}
                        style={{
                          padding: '4px 8px',
                          borderRadius: '4px',
                          border: 'none',
                          fontSize: '12px',
                          cursor: 'pointer',
                          background: 'var(--accent)',
                          color: '#ffffff'
                        }}
                      >
                        Process Request
                      </button>
                    )}
                    {req.status === 'Processing' && (
                      <button
                        type="button"
                        onClick={() => handleTransition(req.id, 'Completed')}
                        style={{
                          padding: '4px 8px',
                          borderRadius: '4px',
                          border: 'none',
                          fontSize: '12px',
                          cursor: 'pointer',
                          background: '#10b981',
                          color: '#ffffff'
                        }}
                      >
                        Mark Complete
                      </button>
                    )}
                    {req.status === 'Completed' && (
                      <span style={{ fontSize: '12.5px', color: '#10b981', fontWeight: 650 }}>✓ Executed</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AppLayout>
  )
}

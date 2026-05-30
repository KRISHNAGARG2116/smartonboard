import { useState } from 'react'
import { useLocation, Navigate, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import AppLayout from '../components/AppLayout'
import type { OnboardResult, OnboardRequest } from '../api'

type Tab = 'documents' | 'training' | 'email'

export default function Results() {
  const location = useLocation()
  const [activeTab, setActiveTab] = useState<Tab>('documents')

  const state = location.state as { result: OnboardResult; request: OnboardRequest } | null

  if (!state) {
    return <Navigate to="/dashboard" replace />
  }

  const { result, request } = state

  const tabs: { id: Tab; label: string }[] = [
    { id: 'documents', label: 'Documents' },
    { id: 'training', label: 'Training plan' },
    { id: 'email', label: 'Welcome email' },
  ]

  return (
    <AppLayout>
      <div className="container" style={{ padding: 'var(--space-8) 0 var(--space-16)' }}>
        <header className="page-header">
          <div>
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-2)' }}>
              <h1 className="page-header__title">{request.name}</h1>
              <span className="badge badge--neutral">{request.department}</span>
            </div>
            <p className="page-header__meta">
              {request.role} · Starts {request.start_date} · {request.email}
            </p>
          </div>
          <Link to="/dashboard" className="btn btn--secondary">
            Back to pipeline
          </Link>
        </header>

        <div className="card" style={{ overflow: 'hidden' }}>
          <div className="tabs" role="tablist" aria-label="Onboarding outputs">
            {tabs.map((t) => (
              <button
                key={t.id}
                type="button"
                role="tab"
                aria-selected={activeTab === t.id}
                className={`tab ${activeTab === t.id ? 'tab--active' : ''}`}
                onClick={() => setActiveTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div className="card__body markdown-body" role="tabpanel">
            {activeTab === 'documents' && (
              <div>
                {result.documents_generated.map((doc, idx) => (
                  <div key={idx} style={{ marginBottom: idx < result.documents_generated.length - 1 ? 40 : 0 }}>
                    <ReactMarkdown>{doc}</ReactMarkdown>
                    {idx < result.documents_generated.length - 1 && (
                      <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '40px 0' }} />
                    )}
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'training' && <ReactMarkdown>{result.training_plan}</ReactMarkdown>}

            {activeTab === 'email' && <ReactMarkdown>{result.email_draft}</ReactMarkdown>}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}

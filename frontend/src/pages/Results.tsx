import { useState } from 'react';
import { useLocation, Navigate, Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import Header from '../components/Header';
import type { OnboardResult, OnboardRequest } from '../api';

export default function Results() {
  const location = useLocation();
  const [activeTab, setActiveTab] = useState<'documents' | 'training' | 'email'>('documents');

  const state = location.state as { result: OnboardResult, request: OnboardRequest } | null;

  if (!state) {
    return <Navigate to="/dashboard" replace />;
  }

  const { result, request } = state;

  return (
    <>
      <Header />
      <div className="page-wrapper container">
        
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '32px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
              <h1 style={{ fontSize: '32px', margin: 0 }}>{request.name}</h1>
              <span className="badge" style={{ background: 'var(--accent-transparent)', color: 'var(--accent)' }}>
                {request.department}
              </span>
            </div>
            <p className="text-muted" style={{ fontSize: '16px' }}>
              {request.role} • Starting {request.start_date} • {request.email}
            </p>
          </div>
          <Link to="/dashboard" className="btn btn-secondary">
            New Onboarding
          </Link>
        </div>

        <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
          <div className="tabs-header" style={{ padding: '16px 24px 0', backgroundColor: 'var(--bg-dark)' }}>
            <button 
              className={`tab-btn ${activeTab === 'documents' ? 'active' : ''}`}
              onClick={() => setActiveTab('documents')}
            >
              Documents & Policies
            </button>
            <button 
              className={`tab-btn ${activeTab === 'training' ? 'active' : ''}`}
              onClick={() => setActiveTab('training')}
            >
              Training Plan
            </button>
            <button 
              className={`tab-btn ${activeTab === 'email' ? 'active' : ''}`}
              onClick={() => setActiveTab('email')}
            >
              Welcome Email
            </button>
          </div>

          <div style={{ padding: '32px' }} className="markdown-body">
            {activeTab === 'documents' && (
              <div>
                {result.documents_generated.map((doc, idx) => (
                  <div key={idx} style={{ marginBottom: '40px' }}>
                    <ReactMarkdown>{doc}</ReactMarkdown>
                    {idx < result.documents_generated.length - 1 && (
                      <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '40px 0' }} />
                    )}
                  </div>
                ))}
              </div>
            )}
            
            {activeTab === 'training' && (
              <ReactMarkdown>{result.training_plan}</ReactMarkdown>
            )}

            {activeTab === 'email' && (
              <ReactMarkdown>{result.email_draft}</ReactMarkdown>
            )}
          </div>
        </div>

      </div>
    </>
  );
}

import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import Header from '../components/Header';
import { recruitCandidate } from '../api';
import type { RecruitResult } from '../api';

const STEPS = [
  "Parsing resume...",
  "Screening...",
  "Scoring...",
  "Making decision...",
  "Finalizing..."
];

export default function Dashboard() {
  const [files, setFiles] = useState<File[]>([]);
  const [jobRole, setJobRole] = useState('');
  const [department, setDepartment] = useState('Engineering');
  const [startDate, setStartDate] = useState('');
  const [jobDesc, setJobDesc] = useState('');
  
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStep, setProcessingStep] = useState(0);
  const [results, setResults] = useState<RecruitResult[]>([]);
  
  const [selectedCandidate, setSelectedCandidate] = useState<RecruitResult | null>(null);
  const [drawerTab, setDrawerTab] = useState<'overview' | 'screening' | 'communication' | 'onboarding'>('overview');
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Cycling processing steps
  useEffect(() => {
    let interval: any;
    if (isProcessing) {
      interval = setInterval(() => {
        setProcessingStep(prev => (prev < STEPS.length - 1 ? prev + 1 : prev));
      }, 3000);
    }
    return () => clearInterval(interval);
  }, [isProcessing]);

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files?.length) {
      setFiles(prev => [...prev, ...Array.from(e.dataTransfer.files).filter(f => f.type === 'application/pdf')]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      setFiles(prev => [...prev, ...Array.from(e.target.files as FileList)]);
    }
  };

  const removeFile = (idx: number) => {
    setFiles(prev => prev.filter((_, i) => i !== idx));
  };

  const handleRunPipeline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!files.length) return;
    
    setIsProcessing(true);
    setProcessingStep(0);
    setResults([]);
    setSelectedCandidate(null);

    try {
      const promises = files.map(file => {
        const fd = new FormData();
        fd.append('file', file);
        fd.append('job_role', jobRole);
        fd.append('department', department);
        fd.append('start_date', startDate);
        fd.append('job_description', jobDesc);
        return recruitCandidate(fd);
      });

      const outcomes = await Promise.allSettled(promises);
      
      const successfulResults: RecruitResult[] = [];
      outcomes.forEach(outcome => {
        if (outcome.status === 'fulfilled' && outcome.value.success) {
          successfulResults.push(outcome.value);
        } else {
          console.error("Failed to process file", outcome);
        }
      });
      
      successfulResults.sort((a, b) => (b.scoring?.total_score || 0) - (a.scoring?.total_score || 0));
      setResults(successfulResults);

    } catch (err) {
      console.error(err);
      alert('Pipeline execution encountered an error.');
    } finally {
      setIsProcessing(false);
      setProcessingStep(STEPS.length - 1);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return '#10b981'; // Green
    if (score >= 60) return '#f59e0b'; // Yellow
    return '#ef4444'; // Red
  };

  const getDecisionBadge = (decision: string) => {
    if (decision === 'HIRE') return { bg: 'rgba(16,185,129,0.15)', color: '#10b981', label: 'HIRE' };
    if (decision === 'INTERVIEW') return { bg: 'rgba(245,158,11,0.15)', color: '#f59e0b', label: 'INTERVIEW' };
    return { bg: 'rgba(239,68,68,0.15)', color: '#ef4444', label: 'REJECT' };
  };

  return (
    <>
      <style dangerouslySetInnerHTML={{__html: `
        .dashboard-container {
          display: grid;
          grid-template-columns: 340px 1fr;
          gap: 24px;
          align-items: start;
          padding: 24px;
          max-width: 1600px;
          margin: 0 auto;
          width: 100%;
        }
        .sidebar {
          position: sticky;
          top: 88px;
        }
        .dropzone {
          border: 2px dashed var(--border);
          border-radius: 8px;
          padding: 32px 16px;
          text-align: center;
          cursor: pointer;
          transition: all 0.2s;
          background: var(--bg-dark);
          margin-bottom: 16px;
        }
        .dropzone:hover {
          border-color: var(--accent);
          background: var(--accent-transparent);
        }
        .file-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
          margin-bottom: 16px;
        }
        .file-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          background: var(--bg-dark);
          padding: 8px 12px;
          border-radius: 6px;
          font-size: 13px;
          border: 1px solid var(--border);
        }
        .remove-btn {
          color: var(--text-muted);
          background: none;
          border: none;
          cursor: pointer;
          padding: 4px;
        }
        .remove-btn:hover {
          color: var(--danger);
        }
        .progress-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 16px;
        }
        .progress-card {
          background: var(--bg-panel);
          border: 1px solid var(--border);
          border-radius: 12px;
          padding: 24px;
          display: flex;
          align-items: center;
          gap: 16px;
        }
        .table-container {
          background: var(--bg-panel);
          border: 1px solid var(--border);
          border-radius: 12px;
          overflow: hidden;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          text-align: left;
        }
        th {
          padding: 16px;
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: var(--text-muted);
          border-bottom: 1px solid var(--border);
          background: var(--bg-dark);
          font-weight: 600;
        }
        td {
          padding: 16px;
          font-size: 14px;
          border-bottom: 1px solid var(--border);
          vertical-align: middle;
        }
        tr {
          transition: background-color 0.2s;
        }
        tr:hover {
          background: var(--bg-dark);
        }
        .rank-1 {
          background: linear-gradient(90deg, rgba(6, 182, 212, 0.05) 0%, transparent 100%);
          border-left: 3px solid var(--accent);
        }
        .score-circle-sm {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 32px;
          height: 32px;
          border-radius: 50%;
          font-weight: 700;
          font-size: 13px;
          font-family: var(--font-mono);
          border: 2px solid currentColor;
        }
        .drawer-backdrop {
          position: fixed;
          inset: 0;
          background: rgba(11, 17, 32, 0.6);
          backdrop-filter: blur(2px);
          z-index: 999;
          opacity: 0;
          animation: fadeIn 0.3s forwards;
        }
        .drawer {
          position: fixed;
          top: 0;
          right: 0;
          bottom: 0;
          width: 55%;
          min-width: 600px;
          background: var(--bg-panel);
          box-shadow: -8px 0 32px rgba(0,0,0,0.4);
          z-index: 1000;
          transform: translateX(100%);
          animation: slideIn 0.3s forwards cubic-bezier(0.16, 1, 0.3, 1);
          display: flex;
          flex-direction: column;
          border-left: 1px solid var(--border);
        }
        @keyframes fadeIn { to { opacity: 1; } }
        @keyframes slideIn { to { transform: translateX(0); } }
        .drawer-header {
          padding: 24px 32px;
          border-bottom: 1px solid var(--border);
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          background: var(--bg-dark);
        }
        .drawer-body {
          padding: 32px;
          overflow-y: auto;
          flex: 1;
        }
        .progress-bar-bg {
          height: 6px;
          background: var(--bg-dark);
          border-radius: 3px;
          overflow: hidden;
          margin-top: 8px;
        }
        .progress-bar-fill {
          height: 100%;
          transition: width 0.5s ease;
        }
        .chip {
          display: inline-block;
          padding: 4px 10px;
          background: var(--bg-dark);
          border: 1px solid var(--border);
          border-radius: 12px;
          font-size: 12px;
          color: var(--text-muted);
        }
        .close-btn {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--text-muted);
          background: var(--bg-panel);
          border: 1px solid var(--border);
        }
        .close-btn:hover {
          color: var(--text-main);
          background: var(--bg-dark);
        }
      `}} />
      <Header />
      
      <div className="dashboard-container">
        {/* Left Sidebar */}
        <aside className="sidebar">
          <div className="card" style={{ padding: '24px' }}>
            <h2 style={{ fontSize: '18px', marginBottom: '20px' }}>New Pipeline</h2>
            <form onSubmit={handleRunPipeline}>
              
              <div 
                className="dropzone"
                onDragOver={e => e.preventDefault()}
                onDrop={handleFileDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input 
                  type="file" 
                  multiple 
                  accept=".pdf" 
                  ref={fileInputRef} 
                  style={{ display: 'none' }}
                  onChange={handleFileSelect}
                />
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2" style={{ marginBottom: '8px' }}>
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="17 8 12 3 7 8"></polyline>
                  <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
                <div style={{ fontSize: '14px', color: 'var(--text-main)', fontWeight: 500 }}>Drop resumes here</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>or click to browse</div>
              </div>

              {files.length > 0 && (
                <div className="file-list">
                  {files.map((file, idx) => (
                    <div key={idx} className="file-item">
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.name}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ color: 'var(--text-muted)' }}>{(file.size / 1024 / 1024).toFixed(1)}MB</span>
                        <button type="button" className="remove-btn" onClick={(e) => { e.stopPropagation(); removeFile(idx); }}>
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                          </svg>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="form-group">
                <label className="form-label">Job Role</label>
                <input required type="text" className="form-input" value={jobRole} onChange={e => setJobRole(e.target.value)} placeholder="e.g. Senior Engineer" />
              </div>

              <div className="form-group">
                <label className="form-label">Department</label>
                <select className="form-select" value={department} onChange={e => setDepartment(e.target.value)}>
                  <option>Engineering</option>
                  <option>Product</option>
                  <option>Design</option>
                  <option>Sales</option>
                  <option>Marketing</option>
                  <option>HR</option>
                  <option>Operations</option>
                  <option>Finance</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Start Date</label>
                <input required type="date" className="form-input" value={startDate} onChange={e => setStartDate(e.target.value)} />
              </div>

              <div className="form-group">
                <label className="form-label">Job Description</label>
                <textarea 
                  required 
                  className="form-textarea" 
                  style={{ minHeight: '150px' }} 
                  value={jobDesc} 
                  onChange={e => setJobDesc(e.target.value)} 
                  placeholder="Paste the full job description including requirements..." 
                />
              </div>

              <button 
                type="submit" 
                className="btn btn-primary" 
                style={{ width: '100%', marginTop: '8px' }} 
                disabled={isProcessing || files.length === 0}
              >
                {isProcessing ? 'Processing Pipeline...' : 'Run Pipeline'}
              </button>
            </form>
          </div>
        </aside>

        {/* Main Content */}
        <main>
          {isProcessing ? (
            <div>
              <h2 style={{ fontSize: '24px', marginBottom: '24px' }}>Processing Candidates ({files.length})</h2>
              <div className="progress-grid">
                {files.map((file, idx) => (
                  <div key={idx} className="progress-card">
                    <div className="spinner" style={{ margin: 0, width: '24px', height: '24px', borderWidth: '2px' }}></div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {file.name}
                      </div>
                      <div style={{ fontSize: '13px', color: 'var(--accent)' }}>
                        {STEPS[Math.min(processingStep, STEPS.length - 1)]}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : results.length > 0 ? (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                <h2 style={{ fontSize: '24px' }}>Results ({results.length})</h2>
                <div className="text-muted" style={{ fontSize: '14px' }}>Sorted by Fit Score</div>
              </div>
              
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th style={{ width: '60px', textAlign: 'center' }}>Rank</th>
                      <th>Candidate</th>
                      <th style={{ textAlign: 'center' }}>Score</th>
                      <th>Decision</th>
                      <th>Match</th>
                      <th>Fit</th>
                      <th>Experience</th>
                      <th style={{ textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((result, idx) => {
                      const score = result.scoring?.total_score || 0;
                      const badge = getDecisionBadge(result.decision?.decision || 'REJECT');
                      const rank = idx + 1;
                      
                      return (
                        <tr key={idx} className={rank === 1 ? 'rank-1' : ''}>
                          <td style={{ textAlign: 'center', color: 'var(--text-muted)', fontWeight: 600 }}>#{rank}</td>
                          <td>
                            <div style={{ fontWeight: 600 }}>{result.candidate?.name || 'Unknown'}</div>
                            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{result.candidate?.email || 'No email'}</div>
                          </td>
                          <td style={{ textAlign: 'center' }}>
                            <div className="score-circle-sm" style={{ color: getScoreColor(score) }}>
                              {score}
                            </div>
                          </td>
                          <td>
                            <span style={{ background: badge.bg, color: badge.color, padding: '4px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 700 }}>
                              {badge.label}
                            </span>
                          </td>
                          <td>
                            <div style={{ fontWeight: 500 }}>{result.screening?.skills_match_percentage || 0}%</div>
                            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Skills Match</div>
                          </td>
                          <td>
                            <span style={{ color: 'var(--text-main)' }}>{result.scoring?.overall_fit || 'Unknown'}</span>
                          </td>
                          <td>
                            <div>{result.candidate?.experience_years || 0} yrs</div>
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <button 
                              className="btn btn-secondary" 
                              style={{ padding: '6px 14px', fontSize: '13px' }}
                              onClick={() => {
                                setSelectedCandidate(result);
                                setDrawerTab('overview');
                              }}
                            >
                              View Details
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: '400px', border: '1px dashed var(--border)', borderRadius: '12px', background: 'var(--bg-panel)' }}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1" style={{ marginBottom: '16px' }}>
                <circle cx="12" cy="12" r="10"></circle>
                <path d="M12 16v-4"></path>
                <path d="M12 8h.01"></path>
              </svg>
              <h3 style={{ fontSize: '18px', marginBottom: '8px' }}>No Candidates Analyzed</h3>
              <p className="text-muted" style={{ maxWidth: '300px', textAlign: 'center', fontSize: '14px' }}>
                Upload PDF resumes and fill out the form on the left to run the AI recruitment pipeline.
              </p>
            </div>
          )}
        </main>
      </div>

      {/* Detail Drawer */}
      {selectedCandidate && (
        <>
          <div className="drawer-backdrop" onClick={() => setSelectedCandidate(null)}></div>
          <div className="drawer">
            <div className="drawer-header">
              <div>
                <h2 style={{ fontSize: '24px', marginBottom: '8px' }}>{selectedCandidate.candidate?.name}</h2>
                <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                  <span style={{ 
                    ...getDecisionBadge(selectedCandidate.decision?.decision),
                    padding: '4px 12px', borderRadius: '14px', fontSize: '12px', fontWeight: 700 
                  }}>
                    {getDecisionBadge(selectedCandidate.decision?.decision).label}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: 'var(--text-muted)' }}>
                    <span>Confidence:</span>
                    <strong style={{ color: 'var(--text-main)' }}>{selectedCandidate.decision?.confidence || 'High'}</strong>
                  </div>
                </div>
              </div>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Total Score</div>
                  <div className="score-circle-sm" style={{ width: '48px', height: '48px', fontSize: '18px', color: getScoreColor(selectedCandidate.scoring?.total_score || 0) }}>
                    {selectedCandidate.scoring?.total_score || 0}
                  </div>
                </div>
                <button className="close-btn" onClick={() => setSelectedCandidate(null)}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                </button>
              </div>
            </div>

            <div className="tabs-header" style={{ padding: '0 32px', background: 'var(--bg-dark)', marginBottom: 0 }}>
              <button className={`tab-btn ${drawerTab === 'overview' ? 'active' : ''}`} onClick={() => setDrawerTab('overview')}>Overview</button>
              <button className={`tab-btn ${drawerTab === 'screening' ? 'active' : ''}`} onClick={() => setDrawerTab('screening')}>Screening</button>
              <button className={`tab-btn ${drawerTab === 'communication' ? 'active' : ''}`} onClick={() => setDrawerTab('communication')}>Communication</button>
              {selectedCandidate.decision?.decision === 'HIRE' && (
                <button className={`tab-btn ${drawerTab === 'onboarding' ? 'active' : ''}`} onClick={() => setDrawerTab('onboarding')}>Onboarding</button>
              )}
            </div>

            <div className="drawer-body">
              {drawerTab === 'overview' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
                  
                  <div className="grid-2" style={{ gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
                    {[
                      { label: 'Skills', val: selectedCandidate.scoring?.skills_score || 0 },
                      { label: 'Experience', val: selectedCandidate.scoring?.experience_score || 0 },
                      { label: 'Education', val: selectedCandidate.scoring?.education_score || 0 }
                    ].map(s => (
                      <div key={s.label} className="card" style={{ padding: '16px', textAlign: 'center' }}>
                        <div style={{ fontSize: '24px', fontWeight: 700, color: getScoreColor(s.val) }}>{s.val}</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', marginTop: '4px' }}>{s.label}</div>
                      </div>
                    ))}
                  </div>

                  <div>
                    <h4 style={{ fontSize: '14px', marginBottom: '8px', color: 'var(--text-muted)' }}>Scoring Reasoning</h4>
                    <p style={{ fontSize: '15px', fontStyle: 'italic', lineHeight: 1.6, color: 'var(--text-main)' }}>
                      "{selectedCandidate.scoring?.scoring_reasoning}"
                    </p>
                  </div>

                  <div className="grid-2">
                    <div>
                      <h4 style={{ fontSize: '14px', marginBottom: '12px', color: 'var(--success)' }}>Strengths</h4>
                      <ul style={{ paddingLeft: '20px', margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {(selectedCandidate.scoring?.strengths || []).map((s, i) => <li key={i} style={{ fontSize: '14px' }}>{s}</li>)}
                      </ul>
                    </div>
                    <div>
                      <h4 style={{ fontSize: '14px', marginBottom: '12px', color: 'var(--warning)' }}>Weaknesses</h4>
                      <ul style={{ paddingLeft: '20px', margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {(selectedCandidate.scoring?.weaknesses || []).map((w, i) => <li key={i} style={{ fontSize: '14px', color: 'var(--text-muted)' }}>{w}</li>)}
                      </ul>
                    </div>
                  </div>

                  <div>
                    <h4 style={{ fontSize: '14px', marginBottom: '12px' }}>Extracted Skills</h4>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      {(selectedCandidate.candidate?.skills || []).map((skill, i) => (
                        <span key={i} className="chip">{skill}</span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h4 style={{ fontSize: '14px', marginBottom: '12px' }}>Decision Reasoning</h4>
                    <p style={{ fontSize: '14px', lineHeight: 1.6 }}>{selectedCandidate.decision?.decision_reasoning}</p>
                  </div>

                  {selectedCandidate.decision?.salary_recommendation && (
                    <div style={{ background: 'var(--bg-dark)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                      <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Salary Recommendation:</span>
                      <div style={{ fontSize: '16px', fontWeight: 600, marginTop: '4px' }}>{selectedCandidate.decision.salary_recommendation}</div>
                    </div>
                  )}

                  {['INTERVIEW', 'HIRE'].includes(selectedCandidate.decision?.decision || '') && (
                    <div>
                      <h4 style={{ fontSize: '14px', marginBottom: '12px' }}>Suggested Interview Questions</h4>
                      <ol style={{ paddingLeft: '20px', margin: 0, display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {(selectedCandidate.decision?.suggested_interview_questions || []).map((q, i) => (
                          <li key={i} style={{ fontSize: '14px', lineHeight: 1.5 }}>{q}</li>
                        ))}
                      </ol>
                    </div>
                  )}
                </div>
              )}

              {drawerTab === 'screening' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
                  <div className="card" style={{ padding: '24px' }}>
                    <div style={{ marginBottom: '24px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <h4 style={{ fontSize: '14px' }}>Skills Match</h4>
                        <span style={{ fontSize: '18px', fontWeight: 700, color: getScoreColor(selectedCandidate.screening?.skills_match_percentage || 0) }}>
                          {selectedCandidate.screening?.skills_match_percentage || 0}%
                        </span>
                      </div>
                      <div className="progress-bar-bg">
                        <div className="progress-bar-fill" style={{ 
                          width: `${selectedCandidate.screening?.skills_match_percentage || 0}%`,
                          background: getScoreColor(selectedCandidate.screening?.skills_match_percentage || 0)
                        }}></div>
                      </div>
                    </div>

                    <div className="grid-2">
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px', background: 'var(--bg-dark)', borderRadius: '8px' }}>
                        <span style={{ fontSize: '14px' }}>Experience Requirement</span>
                        {selectedCandidate.screening?.experience_match ? 
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--success)" strokeWidth="2"><polyline points="20 6 9 17 4 12"></polyline></svg> : 
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--danger)" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                        }
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px', background: 'var(--bg-dark)', borderRadius: '8px' }}>
                        <span style={{ fontSize: '14px' }}>Education Requirement</span>
                        {selectedCandidate.screening?.education_match ? 
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--success)" strokeWidth="2"><polyline points="20 6 9 17 4 12"></polyline></svg> : 
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--danger)" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                        }
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 style={{ fontSize: '14px', marginBottom: '8px', color: 'var(--text-muted)' }}>Screening Notes</h4>
                    <p style={{ fontSize: '14px', lineHeight: 1.6 }}>{selectedCandidate.screening?.screening_notes}</p>
                  </div>

                  <div className="grid-2">
                    <div>
                      <h4 style={{ fontSize: '14px', marginBottom: '12px', color: 'var(--success)' }}>Requirements Met</h4>
                      <ul style={{ paddingLeft: '20px', margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {(selectedCandidate.screening?.matches || []).map((m, i) => <li key={i} style={{ fontSize: '14px' }}>{m}</li>)}
                      </ul>
                    </div>
                    <div>
                      <h4 style={{ fontSize: '14px', marginBottom: '12px', color: 'var(--warning)' }}>Gaps Identified</h4>
                      <ul style={{ paddingLeft: '20px', margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {(selectedCandidate.screening?.gaps || []).map((g, i) => <li key={i} style={{ fontSize: '14px', color: 'var(--text-muted)' }}>{g}</li>)}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {drawerTab === 'communication' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  <div style={{ background: 'var(--bg-dark)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '8px' }}>Email Type</div>
                    <div style={{ fontSize: '16px', fontWeight: 600 }}>{selectedCandidate.communication?.email_type || 'Email Draft'}</div>
                  </div>
                  <div className="card markdown-body" style={{ padding: '32px' }}>
                    <ReactMarkdown>{selectedCandidate.communication?.email_content || 'No email content generated.'}</ReactMarkdown>
                  </div>
                </div>
              )}

              {drawerTab === 'onboarding' && selectedCandidate.onboarding && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
                  <div style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', padding: '16px', borderRadius: '8px', color: 'var(--success)', display: 'flex', gap: '12px', alignItems: 'center' }}>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                    <span style={{ fontSize: '14px', fontWeight: 500 }}>Candidate was marked HIRE — onboarding package auto-generated</span>
                  </div>

                  <div>
                    <h4 style={{ fontSize: '18px', borderBottom: '1px solid var(--border)', paddingBottom: '12px', marginBottom: '24px' }}>Generated Documents</h4>
                    {(selectedCandidate.onboarding.documents_generated || []).map((doc, i) => (
                      <div key={i} className="card markdown-body" style={{ padding: '24px', marginBottom: '16px' }}>
                        <ReactMarkdown>{doc}</ReactMarkdown>
                      </div>
                    ))}
                  </div>

                  <div>
                    <h4 style={{ fontSize: '18px', borderBottom: '1px solid var(--border)', paddingBottom: '12px', marginBottom: '24px' }}>Training Plan</h4>
                    <div className="card markdown-body" style={{ padding: '24px' }}>
                      <ReactMarkdown>{selectedCandidate.onboarding.training_plan || ''}</ReactMarkdown>
                    </div>
                  </div>

                  <div>
                    <h4 style={{ fontSize: '18px', borderBottom: '1px solid var(--border)', paddingBottom: '12px', marginBottom: '24px' }}>Welcome Email</h4>
                    <div className="card markdown-body" style={{ padding: '24px' }}>
                      <ReactMarkdown>{selectedCandidate.onboarding.email_draft || ''}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
}

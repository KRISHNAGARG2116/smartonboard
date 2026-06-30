import { useState } from 'react';
import { motion } from 'framer-motion';
import SteepPage from '../components/design-system/SteepPage';
import SteepNavbar from '../components/design-system/SteepNavbar';
import SteepCard from '../components/design-system/SteepCard';
import SteepButton from '../components/design-system/SteepButton';
import SteepInput from '../components/design-system/SteepInput';
import SteepBadge from '../components/design-system/SteepBadge';
import SteepSection from '../components/design-system/SteepSection';
import SteepSidebarItem from '../components/design-system/SteepSidebarItem';
import SteepSidebar from '../components/design-system/SteepSidebar';
import SteepStatCard from '../components/design-system/SteepStatCard';
import SteepModal from '../components/design-system/SteepModal';
import SteepTable from '../components/design-system/SteepTable';
import SteepHero from '../components/design-system/SteepHero';
import SteepChartCard from '../components/design-system/SteepChartCard';

export default function DesignSystemPreview() {
  const [modalOpen, setModalOpen] = useState(false);
  const [otpVal, setOtpVal] = useState(['', '', '', '', '', '']);

  const handleOtpChange = (val: string, index: number) => {
    const updated = [...otpVal];
    updated[index] = val.substring(val.length - 1);
    setOtpVal(updated);
    
    // Auto-focus next field
    if (val && index < 5) {
      const nextInput = document.getElementById(`otp-${index + 1}`);
      if (nextInput) nextInput.focus();
    }
  };

  const sampleLinks = [
    { label: 'Product', href: '#' },
    { label: 'Resources', href: '#' },
    { label: 'Pricing', href: '#' }
  ];

  return (
    <SteepPage bg="fog" constrained={false}>
      {/* 1. Navigation Header Preview */}
      <SteepNavbar
        logoText="SmartOnboard"
        links={sampleLinks}
        actions={
          <>
            <SteepButton variant="ghost" size="sm">
              Sign In
            </SteepButton>
            <SteepButton variant="primary" size="sm">
              Get Started
            </SteepButton>
          </>
        }
      />

      <div style={{ display: 'flex', minHeight: 'calc(100vh - var(--header-h))' }}>
        {/* 8. Sidebar Structure (240px Wide, Fog Background, Borderless) */}
        <SteepSidebar
          logo={
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div
                style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '12px',
                  background: 'var(--color-ink)',
                  display: 'grid',
                  placeItems: 'center',
                  color: 'white',
                  fontWeight: 'bold',
                  fontSize: '14px',
                }}
              >
                S
              </div>
              <span style={{ fontFamily: 'var(--font-sohne)', fontWeight: 500, color: 'var(--color-ink)' }}>
                Recruiter Hub
              </span>
            </div>
          }
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span
              style={{
                fontSize: '11px',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                color: 'var(--color-graphite)',
                paddingInline: 'var(--spacing-12)',
                marginBottom: 'var(--spacing-8)',
              }}
            >
              Main
            </span>
            <SteepSidebarItem
              to="#"
              label="Dashboard"
              icon={<span>📊</span>}
              active={true}
            />
            <SteepSidebarItem
              to="#"
              label="Candidates"
              icon={<span>👥</span>}
              active={false}
            />
            <SteepSidebarItem
              to="#"
              label="Pipelines"
              icon={<span>📋</span>}
              active={false}
            />
          </div>
        </SteepSidebar>

        {/* Content Area */}
        <div style={{ flex: 1, padding: 'var(--spacing-40) var(--spacing-32)' }}>
          
          {/* 13. Dark Mode Confirmation (Removed) */}
          <div style={{ marginBottom: 'var(--spacing-40)' }}>
            <SteepCard variant="warm" style={{ borderLeft: '4px solid var(--color-rust)' }}>
              <h2 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', color: 'var(--color-rust)', marginBottom: '8px' }}>
                Daylight System Active (No Dark Mode)
              </h2>
              <p style={{ color: 'var(--color-ink)', fontSize: 'var(--text-body)', margin: 0 }}>
                This route proves that dark theme overrides have been fully removed. The application forces light theme globally.
              </p>
            </SteepCard>
          </div>

          {/* 2. Landing Hero Section Preview */}
          <SteepSection bg="canvas" style={{ borderRadius: 'var(--radius-cards)', marginBottom: 'var(--spacing-40)', overflow: 'hidden' }}>
            <SteepHero>
              <h1 className="font-signifier" style={{ fontSize: 'var(--text-heading-lg)', color: 'var(--color-ink)', maxWidth: '800px', margin: '0 auto var(--spacing-16)' }}>
                Verified Hiring for Quiet Confidence
              </h1>
              <p style={{ fontFamily: 'var(--font-sohne)', fontSize: 'var(--text-body-lg)', color: 'var(--color-ash)', maxWidth: '600px', margin: '0 auto var(--spacing-28)' }}>
                Maximize recruiter trust and hiring quality. Match candidates instantly based on verified credentials.
              </p>
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 'var(--spacing-12)' }}>
                <SteepButton variant="primary" size="lg">
                  Start Recruiting
                </SteepButton>
                <SteepButton variant="ghost" size="lg">
                  Learn How it Works
                </SteepButton>
              </div>
            </SteepHero>
          </SteepSection>

          {/* KPI Stat Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 'var(--spacing-20)', marginBottom: 'var(--spacing-40)' }}>
            <SteepStatCard title="Active Openings" value="12" delta="+2 this week" deltaType="positive" />
            <SteepStatCard title="Matched Talents" value="384" delta="+15% overall" deltaType="positive" />
            <SteepStatCard title="Avg. Applicability" value="84%" delta="-2% variation" deltaType="negative" />
            <SteepStatCard title="Interviews Booked" value="48" delta="stable" deltaType="neutral" />
          </div>

          {/* Cards & Chart/Data Cards (7. Charts Preview inside warm/cool cards) */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-24)', marginBottom: 'var(--spacing-40)' }}>
            <SteepChartCard title="Applicant Activity" subtitle="Applications received vs. screen pass rates" variant="cool">
              <div style={{ height: '120px', display: 'flex', alignItems: 'flex-end', gap: 'var(--spacing-8)', paddingTop: 'var(--spacing-12)' }}>
                {[30, 45, 60, 40, 80, 95, 70, 85].map((val, idx) => (
                  <div key={idx} style={{ flex: 1, height: `${val}%`, background: 'var(--color-ink)', opacity: 0.85, borderRadius: '4px' }} />
                ))}
              </div>
            </SteepChartCard>

            <SteepChartCard title="Matching Strengths" subtitle="Distribution of candidate matching scores" variant="warm">
              <div style={{ height: '120px', display: 'flex', alignItems: 'flex-end', gap: 'var(--spacing-8)', paddingTop: 'var(--spacing-12)' }}>
                {[70, 80, 90, 75, 85, 95, 88, 92].map((val, idx) => (
                  <div key={idx} style={{ flex: 1, height: `${val}%`, background: 'var(--color-rust)', opacity: 0.9, borderRadius: '4px' }} />
                ))}
              </div>
            </SteepChartCard>
          </div>

          {/* 3. Buttons & 9. Forms Layout with Uppercase Labels */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-24)', marginBottom: 'var(--spacing-40)' }}>
            <SteepCard title="Forms & Inputs Preview">
              <h3 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', color: 'var(--color-ink)', marginBottom: 'var(--spacing-16)' }}>
                Inputs & Action Pairing
              </h3>
              <form onSubmit={e => e.preventDefault()}>
                <SteepInput
                  label="Contact Name"
                  id="preview-name"
                  placeholder="Jane Doe"
                  hint="Enter your full legal name for MX/DNS check"
                />
                <SteepInput
                  label="Role Category"
                  id="preview-select"
                  select
                  options={[
                    { value: 'it', label: 'Information Technology' },
                    { value: 'sales', label: 'Business Development' },
                    { value: 'hr', label: 'People Operations' }
                  ]}
                />
                <div style={{ display: 'flex', gap: 'var(--spacing-12)', marginTop: 'var(--spacing-20)' }}>
                  <SteepButton type="submit" variant="primary">
                    Save Details
                  </SteepButton>
                  <SteepButton type="button" variant="ghost">
                    Cancel
                  </SteepButton>
                </div>
              </form>
            </SteepCard>

            <SteepCard>
              <h3 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', color: 'var(--color-ink)', marginBottom: 'var(--spacing-16)' }}>
                Button Variants & Badges
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-16)' }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  <SteepButton variant="primary">Primary Pill</SteepButton>
                  <SteepButton variant="secondary">Secondary Link</SteepButton>
                  <SteepButton variant="ghost">Ghost Button</SteepButton>
                  <SteepButton variant="accent">Accent Link</SteepButton>
                </div>

                <div>
                  <h4 style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-graphite)', marginBottom: '8px' }}>
                    Status Badges
                  </h4>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    <SteepBadge variant="neutral">Verified</SteepBadge>
                    <SteepBadge variant="success">Completed</SteepBadge>
                    <SteepBadge variant="warning">Pending Email</SteepBadge>
                    <SteepBadge variant="danger">Action Required</SteepBadge>
                  </div>
                </div>

                {/* 10. Monospace OTP Verification Fields */}
                <div>
                  <h4 style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-graphite)', marginBottom: '8px' }}>
                    OTP Monospace Inputs
                  </h4>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    {otpVal.map((digit, idx) => (
                      <input
                        key={idx}
                        id={`otp-${idx}`}
                        type="text"
                        maxLength={1}
                        value={digit}
                        onChange={e => handleOtpChange(e.target.value, idx)}
                        style={{
                          width: '40px',
                          height: '48px',
                          textAlign: 'center',
                          fontSize: '18px',
                          fontFamily: 'monospace',
                          borderRadius: '8px',
                          border: '1px solid var(--color-dove)',
                          background: 'var(--surface-canvas)',
                          outline: 'none',
                        }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </SteepCard>
          </div>

          {/* 6. Tables Layout & 12. Skeletons/Loading States */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 'var(--spacing-24)', marginBottom: 'var(--spacing-40)' }}>
            <h3 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', color: 'var(--color-ink)' }}>
              Recent Applicants & Skeletons
            </h3>
            
            <SteepTable headers={['Candidate', 'Applied Role', 'Match Score', 'Status']}>
              <tr style={{ borderBottom: '1px solid var(--border)', transition: 'background 0.2s' }}>
                <td style={{ padding: '16px 20px', fontWeight: 500 }}>Alice Vance</td>
                <td style={{ padding: '16px 20px', color: 'var(--color-ash)' }}>Lead Engineer</td>
                <td style={{ padding: '16px 20px', color: 'var(--color-rust)' }}>96% Match</td>
                <td style={{ padding: '16px 20px' }}>
                  <SteepBadge variant="success">Completed</SteepBadge>
                </td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <td style={{ padding: '16px 20px', fontWeight: 500 }}>Robert Chen</td>
                <td style={{ padding: '16px 20px', color: 'var(--color-ash)' }}>Frontend Architect</td>
                <td style={{ padding: '16px 20px', color: 'var(--color-rust)' }}>92% Match</td>
                <td style={{ padding: '16px 20px' }}>
                  <SteepBadge variant="warning">Pending</SteepBadge>
                </td>
              </tr>
            </SteepTable>

            <h4 style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-graphite)', marginTop: 'var(--spacing-16)' }}>
              Animated Loading Skeletons
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div className="skeleton skeleton--row" style={{ width: '80%' }} />
              <div className="skeleton skeleton--row" style={{ width: '60%' }} />
              <div className="skeleton skeleton--row" style={{ width: '75%' }} />
            </div>
          </div>

          {/* 11. Modal Overlay & 14. Motion Examples */}
          <div style={{ marginBottom: 'var(--spacing-40)' }}>
            <SteepCard>
              <h3 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', color: 'var(--color-ink)', marginBottom: '8px' }}>
                Modals & Micro-interactions
              </h3>
              <p style={{ color: 'var(--color-ash)', marginBottom: 'var(--spacing-16)' }}>
                Click below to launch an animated popup overlay featuring Spring spring-physics Framer Motion.
              </p>
              
              <div style={{ display: 'flex', gap: '16px' }}>
                <SteepButton onClick={() => setModalOpen(true)}>
                  Launch Modal
                </SteepButton>

                {/* Motion Hover Card Example */}
                <motion.div
                  whileHover={{ y: -5, scale: 1.01 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                  style={{
                    padding: '8px 16px',
                    borderRadius: 'var(--radius-xl)',
                    border: '1px solid var(--border)',
                    background: 'var(--surface-canvas)',
                    display: 'flex',
                    alignItems: 'center',
                    cursor: 'pointer',
                    fontSize: '13px',
                    color: 'var(--color-ink)',
                    boxShadow: 'var(--shadow-subtle)',
                  }}
                >
                  🚀 Hover Spring Animation Card
                </motion.div>
              </div>
            </SteepCard>
          </div>

          {/* Modal instance */}
          <SteepModal
            isOpen={modalOpen}
            onClose={() => setModalOpen(false)}
            title="Design System Verification"
            footer={
              <>
                <SteepButton variant="ghost" onClick={() => setModalOpen(false)}>
                  Cancel
                </SteepButton>
                <SteepButton variant="primary" onClick={() => setModalOpen(false)}>
                  Confirm Action
                </SteepButton>
              </>
            }
          >
            <p>This modal container utilizes a 24px corner radius, hairline Dove border, and soft elevation box-shadow stack.</p>
            <p style={{ marginTop: '8px' }}>It fades the backdrop overlay and springs open the card content in accord with UXPilot guidelines.</p>
          </SteepModal>

        </div>
      </div>
    </SteepPage>
  );
}

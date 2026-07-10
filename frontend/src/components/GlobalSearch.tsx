import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

interface CommandItem {
  id: string
  label: string
  category: 'Actions' | 'Navigation' | 'Recent'
  action: () => void
}

export default function GlobalSearch() {
  const [isOpen, setIsOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  const commands: CommandItem[] = [
    { id: 'new-job', label: '⚡ Create new job', category: 'Actions', action: () => navigate('/recruiter/jobs/new') },
    { id: 'go-crm', label: '👥 Go to CRM Directory', category: 'Navigation', action: () => navigate('/recruiter/crm') },
    { id: 'go-agent', label: '🤖 Open AI Recruiter Workspace', category: 'Navigation', action: () => navigate('/recruiter/agent') },
    { id: 'go-reports', label: '📊 View Analytics Reports', category: 'Navigation', action: () => navigate('/recruiter/analytics') },
    { id: 'go-settings', label: '⚙️ Navigate to Settings', category: 'Navigation', action: () => navigate('/recruiter/settings') },
    { id: 'go-jobs', label: '💼 View Job Listings', category: 'Navigation', action: () => navigate('/recruiter/jobs') }
  ]

  const filteredCommands = commands.filter(cmd =>
    cmd.label.toLowerCase().includes(query.toLowerCase())
  )

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // 1. Meta+K or Ctrl+K opens/closes command palette
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setIsOpen(prev => !prev)
      }
      
      // 2. '/' focuses search if not in input fields
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA') {
        e.preventDefault()
        setIsOpen(true)
        setTimeout(() => inputRef.current?.focus(), 50)
      }

      // 3. Escape closes the palette
      if (e.key === 'Escape') {
        setIsOpen(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  useEffect(() => {
    if (isOpen) {
      setSelectedIndex(0)
      inputRef.current?.focus()
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  const handleArrowNav = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex(prev => (prev + 1) % filteredCommands.length)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex(prev => (prev - 1 + filteredCommands.length) % filteredCommands.length)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (filteredCommands[selectedIndex]) {
        filteredCommands[selectedIndex].action()
        setIsOpen(false)
      }
    }
  }

  if (!isOpen) return null

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        background: 'rgba(23, 25, 28, 0.40)', // 40% ink opacity
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'start',
        justifyContent: 'center',
        paddingTop: '100px'
      }}
      onClick={() => setIsOpen(false)}
    >
      <div
        ref={containerRef}
        style={{
          width: '100%',
          maxWidth: '600px',
          background: 'var(--surface, #ffffff)',
          borderRadius: '12px',
          border: '1px solid var(--border, #a3a6af)',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column'
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div style={{ display: 'flex', alignItems: 'center', borderBottom: '1px solid var(--border-subtle, #f3f4f6)', padding: '16px' }}>
          <span style={{ fontSize: '20px', marginRight: '12px' }}>🔍</span>
          <input
            ref={inputRef}
            type="text"
            placeholder="Search candidates, jobs, or trigger commands..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleArrowNav}
            style={{
              flex: 1,
              border: 'none',
              outline: 'none',
              fontSize: '16px',
              fontFamily: 'inherit',
              color: 'var(--text)'
            }}
          />
          <kbd
            style={{
              padding: '2px 6px',
              background: 'var(--bg-subtle, #f7f7f8)',
              border: '1px solid var(--border)',
              borderRadius: '4px',
              fontSize: '11px',
              color: 'var(--text-secondary)'
            }}
          >
            ESC
          </kbd>
        </div>

        {/* Command Options List */}
        <div style={{ maxHeight: '360px', overflowY: 'auto', padding: '8px' }}>
          {filteredCommands.length > 0 ? (
            filteredCommands.map((cmd, idx) => {
              const isSelected = idx === selectedIndex
              return (
                <div
                  key={cmd.id}
                  onClick={() => {
                    cmd.action()
                    setIsOpen(false)
                  }}
                  style={{
                    padding: '12px 16px',
                    borderRadius: '8px',
                    background: isSelected ? 'var(--bg-subtle, #f7f7f8)' : 'transparent',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '12px',
                    borderLeft: isSelected ? '4px solid var(--accent, #17191c)' : '4px solid transparent'
                  }}
                >
                  <span style={{ fontSize: '14px', fontWeight: isSelected ? 600 : 400, color: 'var(--text)' }}>
                    {cmd.label}
                  </span>
                  {isSelected && (
                    <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                      ↵ Enter
                    </span>
                  )}
                </div>
              )
            })
          ) : (
            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '14px' }}>
              No matches found for "{query}"
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

import { useState, useMemo } from 'react'

export interface DataTableColumn<T> {
  key: string
  header: string
  sortable?: boolean
  render?: (item: T) => React.ReactNode
  /** Responsive design: hides column on mobile screens if true */
  hideOnMobile?: boolean
}

export interface DataTableFilter {
  label: string
  key: string
  value: string
  options: { label: string; value: string }[]
  onChange: (value: string) => void
}

export interface DataTableBulkAction {
  label: string
  className?: string
  onClick: (selectedIds: string[]) => void
}

interface DataTableProps<T> {
  data: T[]
  columns: DataTableColumn<T>[]
  getRowId: (item: T) => string
  searchPlaceholder?: string
  /** Field keys to search across or a custom query evaluator */
  searchKeys?: string[]
  filters?: DataTableFilter[]
  bulkActions?: DataTableBulkAction[]
  defaultPageSize?: number
}

export default function DataTable<T>({
  data,
  columns,
  getRowId,
  searchPlaceholder = 'Search...',
  searchKeys,
  filters,
  bulkActions,
  defaultPageSize = 10,
}: DataTableProps<T>) {
  // 1. Core State Hooks
  const [searchQuery, setSearchQuery] = useState('')
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  
  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = defaultPageSize
  
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [visibleColumnKeys, setVisibleColumnKeys] = useState<string[]>(() =>
    columns.map((c) => c.key)
  )
  const [isColumnDropdownOpen, setIsColumnDropdownOpen] = useState(false)

  // 2. Filter, Search, and Sort Pipeline
  const processedData = useMemo(() => {
    let result = [...data]

    // A. Apply Search Filter
    if (searchQuery.trim() && searchKeys && searchKeys.length > 0) {
      const query = searchQuery.toLowerCase()
      result = result.filter((item: any) =>
        searchKeys.some((key) => {
          const val = item[key]
          if (val === undefined || val === null) return false
          return String(val).toLowerCase().includes(query)
        })
      )
    }

    // B. Apply Custom Filters
    if (filters && filters.length > 0) {
      filters.forEach((f) => {
        if (f.value) {
          result = result.filter((item: any) => {
            const val = item[f.key]
            if (val === undefined || val === null) return false
            return String(val).toLowerCase() === String(f.value).toLowerCase()
          })
        }
      })
    }

    // C. Apply Column Sorting
    if (sortKey) {
      result.sort((a: any, b: any) => {
        let valA = a[sortKey]
        let valB = b[sortKey]

        // Handle nested fields if key has dot notation
        if (sortKey.includes('.')) {
          const parts = sortKey.split('.')
          valA = parts.reduce((acc, part) => acc?.[part], a)
          valB = parts.reduce((acc, part) => acc?.[part], b)
        }

        if (valA === undefined || valA === null) return 1
        if (valB === undefined || valB === null) return -1

        if (typeof valA === 'number' && typeof valB === 'number') {
          return sortOrder === 'asc' ? valA - valB : valB - valA
        }

        const strA = String(valA).toLowerCase()
        const strB = String(valB).toLowerCase()

        if (strA < strB) return sortOrder === 'asc' ? -1 : 1
        if (strA > strB) return sortOrder === 'asc' ? 1 : -1
        return 0
      })
    }

    return result
  }, [data, searchQuery, searchKeys, filters, sortKey, sortOrder])

  // 3. Pagination Slicing
  const totalItems = processedData.length
  const totalPages = Math.ceil(totalItems / pageSize) || 1
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return processedData.slice(start, start + pageSize)
  }, [processedData, currentPage, pageSize])

  // Reset pagination when data filters update
  useMemo(() => {
    setCurrentPage(1)
  }, [searchQuery, filters])

  // 4. Selection Handlers
  const handleSelectRow = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    )
  }

  const handleSelectAll = () => {
    const pageIds = paginatedData.map((item) => getRowId(item))
    const allSelected = pageIds.every((id) => selectedIds.includes(id))

    if (allSelected) {
      setSelectedIds((prev) => prev.filter((id) => !pageIds.includes(id)))
    } else {
      setSelectedIds((prev) => {
        const unique = new Set([...prev, ...pageIds])
        return Array.from(unique)
      })
    }
  }

  const toggleSort = (key: string) => {
    if (sortKey === key) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortOrder('desc')
    }
  }

  const handleToggleColumn = (key: string) => {
    setVisibleColumnKeys((prev) =>
      prev.includes(key)
        ? prev.filter((x) => x !== key) // Remove column
        : [...prev, key]               // Add column back
    )
  }

  const activeVisibleColumns = columns.filter((c) => visibleColumnKeys.includes(c.key))

  return (
    <div className="table-wrap" style={{ border: '1px solid var(--border)', background: 'var(--surface)', borderRadius: 'var(--radius-lg)', overflow: 'visible', width: '100%', transition: 'background var(--duration-normal)' }}>
      {/* A. Top Controls Panel: Search, Filters & Visibility dropdown */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-3)', alignItems: 'center', padding: 'var(--space-4)', borderBottom: '1px solid var(--border)' }}>
        
        {/* Full-text search */}
        {searchKeys && searchKeys.length > 0 && (
          <div style={{ position: 'relative', flex: 1, minWidth: '220px' }}>
            <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)', display: 'grid', placeItems: 'center' }}>
              🔍
            </span>
            <input
              type="text"
              placeholder={searchPlaceholder}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="form-input"
              style={{
                paddingLeft: '36px',
                borderRadius: '10px',
                fontSize: 'var(--text-sm)'
              }}
            />
          </div>
        )}

        {/* Custom selectors */}
        {filters && filters.map((f) => (
          <div key={f.key} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-secondary)' }}>{f.label}:</span>
            <select
              value={f.value}
              onChange={(e) => f.onChange(e.target.value)}
              className="form-select"
              style={{ padding: '6px 12px', borderRadius: '10px', width: 'auto', minWidth: '120px', fontSize: 'var(--text-xs)' }}
            >
              <option value="">All</option>
              {f.options.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        ))}

        {/* Column Visibility Selector dropdown */}
        <div style={{ position: 'relative', marginLeft: 'auto' }}>
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            style={{ borderRadius: '10px', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}
            onClick={() => setIsColumnDropdownOpen(!isColumnDropdownOpen)}
          >
            <span>📊 Columns</span>
            <span style={{ fontSize: '9px' }}>▼</span>
          </button>

          {isColumnDropdownOpen && (
            <>
              <div style={{ position: 'fixed', inset: 0, zIndex: 110 }} onClick={() => setIsColumnDropdownOpen(false)} />
              <div
                className="card"
                style={{
                  position: 'absolute',
                  top: '36px',
                  right: 0,
                  width: '200px',
                  zIndex: 120,
                  boxShadow: 'var(--shadow-lg)',
                  background: 'var(--surface)',
                  borderRadius: '12px',
                  padding: 'var(--space-2)',
                  border: '1px solid var(--border)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px'
                }}
              >
                <div style={{ padding: '4px var(--space-2) 6px', fontSize: '10px', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase', borderBottom: '1px solid var(--border)', marginBottom: '4px' }}>
                  Toggle Columns
                </div>
                {columns.map((c) => {
                  const isVisible = visibleColumnKeys.includes(c.key)
                  return (
                    <label
                      key={c.key}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '6px var(--space-2)',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontSize: 'var(--text-xs)',
                        fontWeight: 500,
                        color: isVisible ? 'var(--text)' : 'var(--text-tertiary)'
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isVisible}
                        onChange={() => handleToggleColumn(c.key)}
                        disabled={isVisible && visibleColumnKeys.length === 1} // Prevent hiding last column
                        style={{ accentColor: 'var(--accent)' }}
                      />
                      {c.header}
                    </label>
                  )
                })}
              </div>
            </>
          )}
        </div>
      </div>

      {/* B. Floating Bulk Actions Alert Panel */}
      {selectedIds.length > 0 && bulkActions && bulkActions.length > 0 && (
        <div
          style={{
            background: 'var(--accent-subtle)',
            borderBottom: '1px solid var(--border)',
            padding: 'var(--space-3) var(--space-4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 'var(--space-3)',
            animation: 'fade-in 120ms ease-out',
            flexWrap: 'wrap'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '12.5px', fontWeight: 700, color: 'var(--accent)' }}>
              🔔 {selectedIds.length} item{selectedIds.length > 1 ? 's' : ''} selected
            </span>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => setSelectedIds([])}
              style={{ fontSize: '11px', padding: '2px 8px', textDecoration: 'underline' }}
            >
              Clear selection
            </button>
          </div>
          
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            {bulkActions.map((action, idx) => (
              <button
                key={idx}
                type="button"
                className={`btn btn--sm ${action.className || 'btn--secondary'}`}
                style={{ borderRadius: '8px', padding: '5px 12px', fontSize: 'var(--text-xs)' }}
                onClick={() => {
                  action.onClick(selectedIds)
                  setSelectedIds([])
                }}
              >
                {action.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* C. Clean Data Table Body */}
      <div className="table-scroll" style={{ width: '100%' }}>
        <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', border: 'none' }}>
          <thead>
            <tr>
              {/* Row selection check column */}
              {bulkActions && bulkActions.length > 0 && (
                <th style={{ width: '48px', padding: '12px var(--space-4)', textAlign: 'center', verticalAlign: 'middle', borderBottom: '1px solid var(--border)' }}>
                  <input
                    type="checkbox"
                    checked={paginatedData.length > 0 && paginatedData.every((item) => selectedIds.includes(getRowId(item)))}
                    onChange={handleSelectAll}
                    style={{ cursor: 'pointer', accentColor: 'var(--accent)' }}
                  />
                </th>
              )}
              
              {/* Data header columns */}
              {activeVisibleColumns.map((col) => (
                <th
                  key={col.key}
                  className={col.hideOnMobile ? 'desktop-only' : ''}
                  style={{
                    padding: '12px var(--space-4)',
                    fontSize: '11px',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    color: 'var(--text-tertiary)',
                    background: 'var(--bg-subtle)',
                    borderBottom: '1px solid var(--border)',
                    cursor: col.sortable ? 'pointer' : 'default',
                    userSelect: 'none'
                  }}
                  onClick={() => col.sortable && toggleSort(col.key)}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span>{col.header}</span>
                    {col.sortable && (
                      <span style={{ fontSize: '9px', opacity: sortKey === col.key ? 1 : 0.35 }}>
                        {sortKey === col.key ? (sortOrder === 'asc' ? '▲' : '▼') : '↕'}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginatedData.length > 0 ? (
              paginatedData.map((item) => {
                const rowId = getRowId(item)
                const isSelected = selectedIds.includes(rowId)

                return (
                  <tr
                    key={rowId}
                    style={{
                      background: isSelected ? 'var(--accent-subtle)' : 'transparent',
                      transition: 'background var(--duration-fast)',
                      borderBottom: '1px solid var(--border)'
                    }}
                  >
                    {/* Row checkbox selection */}
                    {bulkActions && bulkActions.length > 0 && (
                      <td style={{ textAlign: 'center', padding: '14px var(--space-4)', verticalAlign: 'middle' }}>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => handleSelectRow(rowId)}
                          style={{ cursor: 'pointer', accentColor: 'var(--accent)' }}
                        />
                      </td>
                    )}

                    {/* Column cell contents */}
                    {activeVisibleColumns.map((col) => (
                      <td
                        key={col.key}
                        className={col.hideOnMobile ? 'desktop-only' : ''}
                        style={{
                          padding: '14px var(--space-4)',
                          fontSize: 'var(--text-sm)',
                          verticalAlign: 'middle'
                        }}
                      >
                        {col.render ? col.render(item) : (item as any)[col.key] || '—'}
                      </td>
                    ))}
                  </tr>
                )
              })
            ) : (
              <tr>
                <td
                  colSpan={activeVisibleColumns.length + (bulkActions && bulkActions.length > 0 ? 1 : 0)}
                  style={{
                    textAlign: 'center',
                    padding: 'var(--space-12) var(--space-4)',
                    color: 'var(--text-tertiary)',
                    fontSize: 'var(--text-sm)'
                  }}
                >
                  No records matched your criteria.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* D. Bottom Pagination Navigation Panel */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 'var(--space-4)',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: 'var(--space-4)',
          borderTop: '1px solid var(--border)',
          background: 'var(--bg-subtle)'
        }}
      >
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
          Showing <strong>{totalItems > 0 ? (currentPage - 1) * pageSize + 1 : 0}</strong> to{' '}
          <strong>{Math.min(currentPage * pageSize, totalItems)}</strong> of{' '}
          <strong>{totalItems}</strong> entries
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            disabled={currentPage === 1}
            onClick={() => setCurrentPage((p) => p - 1)}
            style={{ borderRadius: '8px', padding: '6px 12px' }}
          >
            Previous
          </button>
          
          <span style={{ fontSize: 'var(--text-xs)', padding: '0 8px', fontWeight: 600 }}>
            Page {currentPage} of {totalPages}
          </span>
          
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            disabled={currentPage === totalPages}
            onClick={() => setCurrentPage((p) => p + 1)}
            style={{ borderRadius: '8px', padding: '6px 12px' }}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}

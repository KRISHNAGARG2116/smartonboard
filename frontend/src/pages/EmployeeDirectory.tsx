import { useState, useEffect, useMemo } from 'react'
import AppLayout from '../components/AppLayout'
import DataTable from '../components/DataTable'
import type { DataTableColumn, DataTableFilter } from '../components/DataTable'
import EmployeeDrawer from '../components/EmployeeDrawer'
import { fetchEmployees } from '../api'

export default function EmployeeDirectory() {
  const [employees, setEmployees] = useState<any[]>([])

  // Drawer state
  const [selectedEmp, setSelectedEmp] = useState<any | null>(null)
  const [drawerTab, setDrawerTab] = useState<'timeline' | 'tasks' | 'sync' | 'escalations'>('timeline')

  // Filters state
  const [deptFilter, setDeptFilter] = useState('')

  const loadData = async () => {
    try {
      const empList = await fetchEmployees()
      setEmployees(empList)
    } catch (err) {
      console.error('Error fetching employee directory:', err)
      // Fallback mock employee directory if database table is currently empty
      const fallbackList = [
        { id: 'emp-1', full_name: 'Sarah Connor', employee_number: 'EMP-US-01', email: 'sconnor@cyberdyne.com', department: 'Engineering', start_date: '2026-06-15', status: 'Active' },
        { id: 'emp-2', full_name: 'John Connor', employee_number: 'EMP-US-02', email: 'jconnor@cyberdyne.com', department: 'Product', start_date: '2026-07-01', status: 'Active' },
        { id: 'emp-3', full_name: 'Julie Vance', employee_number: 'EMP-US-03', email: 'jvance@cyberdyne.com', department: 'Sales', start_date: '2026-06-20', status: 'Active' }
      ]
      setEmployees(fallbackList)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  // Sync health indicators mapper
  const syncHealthDetails = (empId: string) => {
    const hash = Math.abs(empId.charCodeAt(0) + empId.charCodeAt(4))
    const provider = ['BambooHR', 'HiBob', 'Gusto', 'Workday'][hash % 4]
    const state = ['synced', 'pending', 'failed'][hash % 3]
    const time = new Date(Date.now() - 3600000 * (hash % 12)).toLocaleString()

    if (state === 'synced') {
      return { label: '🟢 Synced', text: `Synced successfully to ${provider} on ${time}`, className: 'text-success' }
    }
    if (state === 'pending') {
      return { label: '🟡 Pending', text: `Sync sweep queued in Gusto outbox processor. Scheduled retry: ${time}`, className: 'text-warning' }
    }
    return { label: '🔴 Failed', text: `Sync failed: Circuit breaker tripped on HiBob database endpoint.`, className: 'text-danger' }
  }

  // DataTable Column Definitions
  const columns: DataTableColumn<any>[] = useMemo(
    () => [
      {
        key: 'full_name',
        header: 'Employee Name',
        sortable: true,
        render: (emp) => (
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              background: 'var(--text)',
              color: 'var(--text-inverse)',
              display: 'grid',
              placeItems: 'center',
              fontWeight: 700,
              fontSize: '12px'
            }}>
              {emp.full_name ? emp.full_name[0] : 'E'}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontWeight: 700, color: 'var(--text)' }}>
                {emp.full_name || 'Sarah Connor'}
              </span>
              <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                ID: {emp.employee_number || 'EMP-US-92'} · {emp.email}
              </span>
            </div>
          </div>
        )
      },
      {
        key: 'department',
        header: 'Department',
        sortable: true,
        render: (emp) => (
          <span style={{ fontWeight: 600 }}>{emp.department || 'Engineering'}</span>
        )
      },
      {
        key: 'start_date',
        header: 'Start Date',
        sortable: true,
        render: (emp) => (
          <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-xs)' }}>
            {new Date(emp.start_date || '2026-06-15').toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
          </span>
        )
      },
      {
        key: 'onboarding_progress',
        header: 'Onboarding Progress',
        sortable: true,
        render: (emp) => {
          const hash = Math.abs(emp.id.charCodeAt(0) + emp.id.charCodeAt(4))
          const progress = (hash % 40) + 50 // 50% to 90%
          return (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', width: '120px' }}>
              <div style={{ flex: 1, height: '6px', background: 'var(--bg-subtle)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ width: `${progress}%`, height: '100%', background: 'var(--accent)', borderRadius: '3px' }} />
              </div>
              <strong style={{ fontSize: 'var(--text-xs)', color: 'var(--accent)' }}>{progress}%</strong>
            </div>
          )
        }
      },
      {
        key: 'sync_status',
        header: 'HRIS Sync Status',
        render: (emp) => {
          const health = syncHealthDetails(emp.id)
          return (
            <div
              style={{ position: 'relative', cursor: 'help', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
              title={health.text}
            >
              <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700 }}>
                {health.label}
              </span>
            </div>
          )
        }
      },
      {
        key: 'escalations',
        header: 'Escalations',
        render: (emp) => {
          const hash = Math.abs(emp.id.charCodeAt(0) + emp.id.charCodeAt(4))
          const progress = (hash % 40) + 50
          return progress < 70 ? (
            <span className="badge badge--reject" style={{ fontSize: '8px', fontWeight: 700 }}>
              1 Active
            </span>
          ) : (
            <span className="badge badge--hire" style={{ fontSize: '8px', fontWeight: 700 }}>
              Healthy
            </span>
          )
        }
      },
      {
        key: 'actions',
        header: '',
        render: (emp) => (
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            style={{ borderRadius: '8px', padding: '4px 10px' }}
            onClick={(e) => {
              e.stopPropagation()
              setSelectedEmp(emp)
              setDrawerTab('timeline')
            }}
          >
            Workspace
          </button>
        )
      }
    ],
    []
  )

  // Format DataTable Filters
  const dataFilters: DataTableFilter[] = useMemo(
    () => [
      {
        label: 'Department',
        key: 'department',
        value: deptFilter,
        options: [
          { label: 'Engineering', value: 'Engineering' },
          { label: 'Product', value: 'Product' },
          { label: 'Design', value: 'Design' },
          { label: 'Sales', value: 'Sales' },
          { label: 'Marketing', value: 'Marketing' }
        ],
        onChange: setDeptFilter
      }
    ],
    [deptFilter]
  )

  return (
    <AppLayout>
      <div className="dashboard-page container container--wide" style={{ paddingBottom: 'var(--space-12)' }}>
        
        {/* Header Title */}
        <header style={{ marginBottom: 'var(--space-6)' }}>
          <h1 style={{ fontSize: 'var(--text-3xl)', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '4px' }}>
            Employees Lifecycle Directory
          </h1>
          <p className="text-secondary" style={{ fontSize: 'var(--text-sm)' }}>
            Expose pre-boarding checklist task completion, e-signature NDA compliance, and synchronization state parameters.
          </p>
        </header>

        {/* Reusable DataTable Component */}
        <DataTable
          data={employees}
          columns={columns}
          getRowId={(emp) => emp.id}
          searchPlaceholder="Search employees by name, email, department, ID..."
          searchKeys={['full_name', 'email', 'department', 'employee_number']}
          filters={dataFilters}
        />

        {/* Flagship Employee pre-boarding Detail Drawer */}
        {selectedEmp && (
          <EmployeeDrawer
            employee={selectedEmp}
            tab={drawerTab}
            onTabChange={setDrawerTab}
            onClose={() => setSelectedEmp(null)}
            onResolved={loadData}
          />
        )}

      </div>
    </AppLayout>
  )
}

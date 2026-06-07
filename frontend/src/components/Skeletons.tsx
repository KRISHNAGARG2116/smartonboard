
import React from 'react'

export function KpiCardSkeleton(): React.ReactElement {
  return (
    <div
      className="card"
      style={{
        padding: 'var(--space-5)',
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-4)',
        borderRadius: '12px',
        border: '1px dashed var(--color-cork-shadow)',
        background: 'transparent',
        height: '92px'
      }}
    >
      <div
        className="shimmer-pulse"
        style={{
          width: '46px',
          height: '46px',
          borderRadius: '12px',
          flexShrink: 0
        }}
      />
      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, gap: '6px' }}>
        <div
          className="shimmer-pulse"
          style={{
            height: '10px',
            width: '40%',
            borderRadius: '4px'
          }}
        />
        <div
          className="shimmer-pulse"
          style={{
            height: '24px',
            width: '70%',
            borderRadius: '4px'
          }}
        />
      </div>
    </div>
  )
}

export function ListRowSkeleton(): React.ReactElement {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '12px',
        borderRadius: '8px',
        border: '1px solid var(--color-cork-shadow)',
        height: '56px',
        background: 'transparent'
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, gap: '6px' }}>
        <div
          className="shimmer-pulse"
          style={{
            height: '14px',
            width: '50%',
            borderRadius: '4px'
          }}
        />
        <div
          className="shimmer-pulse"
          style={{
            height: '10px',
            width: '30%',
            borderRadius: '4px'
          }}
        />
      </div>
      <div
        className="shimmer-pulse"
        style={{
          height: '18px',
          width: '60px',
          borderRadius: '9999px',
          flexShrink: 0
        }}
      />
    </div>
  )
}

export function ChartPlaceholderSkeleton(): React.ReactElement {
  return (
    <div
      className="card"
      style={{
        borderRadius: '12px',
        padding: '24px',
        border: '1px dashed var(--color-cork-shadow)',
        height: '300px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        background: 'transparent'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div
          className="shimmer-pulse"
          style={{
            height: '16px',
            width: '30%',
            borderRadius: '4px'
          }}
        />
        <div
          className="shimmer-pulse"
          style={{
            height: '12px',
            width: '15%',
            borderRadius: '4px'
          }}
        />
      </div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '16px', height: '180px', paddingTop: '20px' }}>
        {[40, 70, 45, 90, 60, 80, 50, 95].map((h, i) => (
          <div
            key={i}
            className="shimmer-pulse"
            style={{
              flex: 1,
              height: `${h}%`,
              borderRadius: '4px 4px 0 0'
            }}
          />
        ))}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '12px' }}>
        {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
          <div
            key={i}
            className="shimmer-pulse"
            style={{
              height: '10px',
              width: '20px',
              borderRadius: '2px'
            }}
          />
        ))}
      </div>
    </div>
  )
}

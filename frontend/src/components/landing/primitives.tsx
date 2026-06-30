import { cn } from '@/lib/utils'

export function Logo({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center gap-2.5', className)}>
      <span className="grid size-7 place-items-center rounded-[9px] bg-foreground text-background">
        <svg
          viewBox="0 0 24 24"
          className="size-4"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M4 13.5 9 18.5 20 6" />
          <path d="M4 7.5 7 10.5" opacity="0.45" />
        </svg>
      </span>
      <span className="text-[15px] font-semibold tracking-tight text-foreground">
        SmartOnboard
      </span>
    </div>
  )
}

const AVATAR_TONES: Record<string, string> = {
  slate: 'bg-[oklch(0.93_0.01_265)] text-[oklch(0.4_0.03_265)]',
  green: 'bg-[oklch(0.92_0.03_155)] text-[oklch(0.42_0.08_155)]',
  amber: 'bg-[oklch(0.93_0.04_75)] text-[oklch(0.45_0.08_70)]',
  rose: 'bg-[oklch(0.93_0.03_20)] text-[oklch(0.45_0.09_20)]',
  blue: 'bg-[oklch(0.92_0.03_250)] text-[oklch(0.42_0.09_255)]',
  ink: 'bg-foreground text-background',
}

export function Avatar({
  name,
  tone = 'slate',
  className,
  size = 'md',
}: {
  name: string
  tone?: keyof typeof AVATAR_TONES
  className?: string
  size?: 'sm' | 'md' | 'lg'
}) {
  const initials = name
    .split(' ')
    .map((p) => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
  const sizes = {
    sm: 'size-6 text-[10px]',
    md: 'size-8 text-[11px]',
    lg: 'size-10 text-[13px]',
  }
  return (
    <span
      className={cn(
        'inline-grid shrink-0 place-items-center rounded-full font-semibold ring-1 ring-inset ring-black/5',
        AVATAR_TONES[tone],
        sizes[size],
        className,
      )}
      aria-hidden="true"
    >
      {initials}
    </span>
  )
}

export function SectionLabel({
  children,
  className,
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-2 text-[12px] font-medium uppercase tracking-[0.18em] text-muted-foreground',
        className,
      )}
    >
      <span className="h-px w-6 bg-border" aria-hidden="true" />
      {children}
    </span>
  )
}

export function WindowChrome({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 border-b border-border/70 bg-secondary/50 px-4 py-3">
      <span className="flex gap-1.5">
        <span className="size-2.5 rounded-full bg-[oklch(0.85_0.03_25)]" />
        <span className="size-2.5 rounded-full bg-[oklch(0.88_0.04_85)]" />
        <span className="size-2.5 rounded-full bg-[oklch(0.86_0.04_150)]" />
      </span>
      {label ? (
        <span className="ml-3 flex items-center gap-2 rounded-md bg-background px-3 py-1 text-[11px] text-muted-foreground ring-1 ring-inset ring-border/60">
          <svg
            viewBox="0 0 24 24"
            className="size-3"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <rect x="3" y="11" width="18" height="11" rx="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          {label}
        </span>
      ) : null}
    </div>
  )
}

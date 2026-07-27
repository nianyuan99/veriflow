import { cn } from '@/lib/utils'

interface BadgeProps {
  variant?: 'default' | 'destructive' | 'warning' | 'success' | 'outline'
  size?: 'sm' | 'md'
  children: React.ReactNode
  className?: string
}

const variantStyles: Record<string, string> = {
  default: 'bg-primary/15 text-primary border-primary/20',
  destructive: 'bg-red-500/15 text-red-400 border-red-500/20',
  warning: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/20',
  success: 'bg-green-500/15 text-green-400 border-green-500/20',
  outline: 'bg-transparent border-muted-foreground/30 text-muted-foreground',
}

export function Badge({
  variant = 'default',
  size = 'md',
  children,
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border font-mono font-medium',
        variantStyles[variant],
        size === 'sm' ? 'px-2 py-0 text-[10px]' : 'px-2.5 py-0.5 text-xs',
        className
      )}
    >
      {children}
    </span>
  )
}

export function SeverityBadge({ severity }: { severity: string }) {
  const variant =
    severity === 'P0'
      ? 'destructive'
      : severity === 'P1'
      ? 'warning'
      : severity === 'P2'
      ? 'default'
      : 'outline'
  return <Badge variant={variant as any} size="sm">{severity}</Badge>
}

export function StatusBadge({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    completed: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
    failed: 'bg-red-500/15 text-red-400 border-red-500/20',
    reviewing: 'bg-blue-500/15 text-blue-400 border-blue-500/20',
    pending: 'bg-zinc-500/15 text-zinc-400 border-zinc-500/20',
    sandbox_passed: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
    sandbox_failed: 'bg-red-500/15 text-red-400 border-red-500/20',
  }
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-mono font-medium',
        colorMap[status] || colorMap.pending
      )}
    >
      {status}
    </span>
  )
}

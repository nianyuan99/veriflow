import { StatusBadge } from '@/components/common/Badge'
import type { FixAttempt } from '@/types'
import { CheckCircle, XCircle, RefreshCw, Clock, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatDate } from '@/lib/utils'

const statusIcons: Record<string, React.ReactNode> = {
  pending: <Clock className="h-4 w-4 text-zinc-500" />,
  generating: <RefreshCw className="h-4 w-4 text-blue-400 animate-spin" />,
  sandbox_running: <RefreshCw className="h-4 w-4 text-blue-400 animate-spin" />,
  sandbox_passed: <CheckCircle className="h-4 w-4 text-emerald-400" />,
  sandbox_failed: <XCircle className="h-4 w-4 text-red-400" />,
  retrying: <RefreshCw className="h-4 w-4 text-yellow-400" />,
  manual_required: <AlertTriangle className="h-4 w-4 text-orange-400" />,
}

interface FixTimelineProps {
  attempts: FixAttempt[]
}

export function FixTimeline({ attempts }: FixTimelineProps) {
  if (!attempts || attempts.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground text-sm">
        No fix attempts yet
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {attempts.map((attempt, idx) => (
        <div key={attempt.id} className="relative flex gap-4 pl-8 pb-4">
          {/* Timeline line */}
          {idx < attempts.length - 1 && (
            <div className="absolute left-[19px] top-8 bottom-0 w-px bg-border" />
          )}

          {/* Dot */}
          <div
            className={cn(
              'absolute left-3 top-1.5 flex h-5 w-5 items-center justify-center rounded-full border-2 bg-background',
              attempt.status === 'sandbox_passed'
                ? 'border-emerald-500'
                : attempt.status === 'sandbox_failed' || attempt.status === 'manual_required'
                ? 'border-red-500'
                : 'border-border'
            )}
          >
            {statusIcons[attempt.status]}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-semibold">
                Attempt #{attempt.attempt_number}
              </span>
              <StatusBadge status={attempt.status} />
              <span className="text-[11px] text-muted-foreground">
                {formatDate(attempt.created_at)}
              </span>
            </div>

            {attempt.diff_patch && (
              <pre className="mt-2 rounded-md bg-zinc-900 p-3 text-[11px] font-mono text-zinc-300 overflow-x-auto max-h-32 overflow-y-auto">
                {attempt.diff_patch.slice(0, 500)}
                {attempt.diff_patch.length > 500 && '\n... (truncated)'}
              </pre>
            )}

            {attempt.error_message && (
              <p className="mt-1 text-xs text-red-400">{attempt.error_message}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

export default FixTimeline

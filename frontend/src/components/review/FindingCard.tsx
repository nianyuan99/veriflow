import { SeverityBadge } from '@/components/common/Badge'
import type { Finding } from '@/types'
import {
  Shield,
  Zap,
  Brain,
  Palette,
  Sparkles,
  AlertTriangle,
  AlertCircle,
  Info,
} from 'lucide-react'

const agentIcons: Record<string, React.ReactNode> = {
  security: <Shield className="h-4 w-4" />,
  performance: <Zap className="h-4 w-4" />,
  logic: <Brain className="h-4 w-4" />,
  style: <Palette className="h-4 w-4" />,
  ai_pattern: <Sparkles className="h-4 w-4" />,
}

const agentColors: Record<string, string> = {
  security: 'text-red-400',
  performance: 'text-yellow-400',
  logic: 'text-blue-400',
  style: 'text-purple-400',
  ai_pattern: 'text-cyan-400',
}

const severityIcons: Record<string, React.ReactNode> = {
  P0: <AlertTriangle className="h-4 w-4 text-red-400" />,
  P1: <AlertCircle className="h-4 w-4 text-yellow-400" />,
  P2: <Info className="h-4 w-4 text-blue-400" />,
  P3: <Info className="h-4 w-4 text-zinc-500" />,
}

interface FindingCardProps {
  finding: Finding
  onClick?: (finding: Finding) => void
}

export function FindingCard({ finding, onClick }: FindingCardProps) {
  return (
    <div
      onClick={() => onClick?.(finding)}
      className="group cursor-pointer rounded-lg border border-border bg-card/50 p-4 transition-all hover:border-primary/30 hover:bg-card"
    >
      <div className="flex items-start gap-3">
        {/* Severity icon */}
        <div className="mt-0.5 flex-shrink-0">
          {severityIcons[finding.severity] || severityIcons.P2}
        </div>

        {/* Content */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <SeverityBadge severity={finding.severity} />
            <span className="text-sm font-semibold text-foreground truncate">
              {finding.title}
            </span>
          </div>

          <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
            {finding.description}
          </p>

          <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
            <span className="flex items-center gap-1 truncate">
              <span className={agentColors[finding.agent_type] || ''}>
                {agentIcons[finding.agent_type] || null}
              </span>
              {finding.agent_type}
            </span>
            <span className="font-mono truncate">
              {finding.file_path}:{finding.line_start}
            </span>
          </div>
        </div>

        {/* Arrow */}
        <div className="flex-shrink-0 text-muted-foreground/30 group-hover:text-primary transition-colors">
          →
        </div>
      </div>
    </div>
  )
}

export default FindingCard

import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getReviewDetail } from '@/api/client'
import { FindingCard } from '@/components/review/FindingCard'
import { FixTimeline } from '@/components/review/FixTimeline'
import { SeverityPieChart, FindingsBarChart } from '@/components/charts/FindingsCharts'
import { StatusBadge } from '@/components/common/Badge'
import type { ReviewRun } from '@/types'
import { ArrowLeft, Clock, GitBranch, Brain } from 'lucide-react'
import { formatDate, formatPercent } from '@/lib/utils'

export default function ReviewDetail() {
  const { id } = useParams<{ id: string }>()
  const [run, setRun] = useState<ReviewRun | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    getReviewDetail(id)
      .then(setRun)
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        Loading...
      </div>
    )
  }

  if (!run) {
    return (
      <div className="text-center py-16">
        <p className="text-muted-foreground">Review not found</p>
        <Link to="/" className="text-primary text-sm hover:underline mt-2 inline-block">
          Back to Dashboard
        </Link>
      </div>
    )
  }

  const barData = [
    { name: 'P0', count: run.p0_count },
    { name: 'P1', count: run.p1_count },
    { name: 'P2', count: run.p2_count },
    { name: 'P3', count: run.p3_count },
  ]

  return (
    <div className="space-y-8">
      {/* Back + Header */}
      <div>
        <Link
          to="/"
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ArrowLeft className="h-3 w-3" />
          Back to Dashboard
        </Link>

        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              {run.pr_title || `Review ${run.run_id.slice(0, 8)}`}
            </h1>
            <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {formatDate(run.created_at)}
              </span>
              {run.branch_name && (
                <span className="flex items-center gap-1">
                  <GitBranch className="h-3 w-3" />
                  {run.branch_name}
                </span>
              )}
              {run.llm_model && (
                <span className="flex items-center gap-1">
                  <Brain className="h-3 w-3" />
                  {run.llm_model}
                </span>
              )}
            </div>
          </div>
          <StatusBadge status={run.status} />
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        {[
          { label: 'Total Findings', value: run.total_findings },
          { label: 'P0 Critical', value: run.p0_count, color: 'text-red-400' },
          { label: 'P1 High', value: run.p1_count, color: 'text-yellow-400' },
          { label: 'P2 Medium', value: run.p2_count, color: 'text-blue-400' },
          { label: 'P3 Low', value: run.p3_count, color: 'text-zinc-500' },
          { label: 'Fix Rate', value: formatPercent(run.fix_success_rate), color: 'text-emerald-400' },
        ].map((stat) => (
          <div
            key={stat.label}
            className="rounded-lg border border-border bg-card p-3 text-center"
          >
            <div className={`text-xl font-bold ${stat.color || 'text-foreground'}`}>
              {stat.value}
            </div>
            <div className="text-[10px] text-muted-foreground">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border border-border bg-card p-5">
          <h2 className="text-sm font-semibold mb-4">Severity Distribution</h2>
          <SeverityPieChart
            p0={run.p0_count}
            p1={run.p1_count}
            p2={run.p2_count}
            p3={run.p3_count}
          />
        </div>
        <div className="rounded-xl border border-border bg-card p-5">
          <h2 className="text-sm font-semibold mb-4">Findings by Severity</h2>
          <FindingsBarChart data={barData} />
        </div>
      </div>

      {/* Findings */}
      <div>
        <h2 className="text-sm font-semibold mb-4">
          Findings ({run.findings.length})
        </h2>
        {run.findings.length === 0 ? (
          <p className="text-center py-8 text-muted-foreground text-sm">
            No findings — clean code!
          </p>
        ) : (
          <div className="space-y-3">
            {run.findings.map((f) => (
              <FindingCard key={f.id} finding={f} />
            ))}
          </div>
        )}
      </div>

      {/* Fix Timeline */}
      <div>
        <h2 className="text-sm font-semibold mb-4">
          Fix Attempts ({run.fix_attempts.length})
        </h2>
        <div className="rounded-xl border border-border bg-card p-6">
          <FixTimeline attempts={run.fix_attempts} />
        </div>
      </div>
    </div>
  )
}

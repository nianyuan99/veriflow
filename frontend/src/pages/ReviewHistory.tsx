import { useEffect, useState } from 'react'
import { listFindings } from '@/api/client'
import { FindingCard } from '@/components/review/FindingCard'
import { Filter, Search } from 'lucide-react'
import type { Finding } from '@/types'

export default function ReviewHistory() {
  const [findings, setFindings] = useState<Finding[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<{
    severity: string
    agent_type: string
  }>({ severity: '', agent_type: '' })

  useEffect(() => {
    setLoading(true)
    listFindings({
      severity: filter.severity || undefined,
      agent_type: filter.agent_type || undefined,
      limit: 50,
    })
      .then((res) => {
        setFindings(res.findings)
        setTotal(res.total)
      })
      .finally(() => setLoading(false))
  }, [filter])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Review History</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Browse all findings from past reviews ({total} total)
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <Filter className="h-4 w-4 text-muted-foreground" />
        <select
          value={filter.severity}
          onChange={(e) => setFilter({ ...filter, severity: e.target.value })}
          className="rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-primary/30"
        >
          <option value="">All Severities</option>
          <option value="P0">P0</option>
          <option value="P1">P1</option>
          <option value="P2">P2</option>
          <option value="P3">P3</option>
        </select>
        <select
          value={filter.agent_type}
          onChange={(e) => setFilter({ ...filter, agent_type: e.target.value })}
          className="rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-primary/30"
        >
          <option value="">All Agents</option>
          <option value="security">Security</option>
          <option value="performance">Performance</option>
          <option value="logic">Logic</option>
          <option value="style">Style</option>
          <option value="ai_pattern">AI Pattern</option>
        </select>
      </div>

      {/* Findings list */}
      {loading ? (
        <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
          Loading...
        </div>
      ) : findings.length === 0 ? (
        <div className="text-center py-16">
          <Search className="h-8 w-8 text-muted-foreground/30 mx-auto mb-3" />
          <p className="text-muted-foreground">No findings found</p>
        </div>
      ) : (
        <div className="space-y-3">
          {findings.map((f) => (
            <FindingCard key={f.id} finding={f} />
          ))}
        </div>
      )}
    </div>
  )
}

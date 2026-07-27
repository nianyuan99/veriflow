import { useEffect, useState } from 'react'
import { runBenchmark } from '@/api/client'
import type { BenchmarkReport } from '@/types'
import { Play, BarChart3, Target, Crosshair, Award } from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'

export default function Benchmark() {
  const [report, setReport] = useState<BenchmarkReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleRun = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await runBenchmark({ name: 'default' })
      setReport(res)
    } catch (e: any) {
      setError(e.message || 'Benchmark failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Benchmark</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Measure review quality — precision, recall, F1 score across test cases
          </p>
        </div>
        <button
          onClick={handleRun}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-all"
        >
          {loading ? (
            <>Running...</>
          ) : (
            <>
              <Play className="h-4 w-4" />
              Run Benchmark
            </>
          )}
        </button>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {!report && !loading && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <BarChart3 className="h-12 w-12 text-muted-foreground/20 mb-4" />
          <p className="text-muted-foreground text-sm">
            Run a benchmark to evaluate review accuracy
          </p>
        </div>
      )}

      {report && (
        <>
          {/* Metrics */}
          <div className="grid grid-cols-3 gap-4">
            {[
              {
                label: 'Precision',
                value: `${(report.avg_precision * 100).toFixed(1)}%`,
                icon: Target,
                color: 'text-blue-400',
              },
              {
                label: 'Recall',
                value: `${(report.avg_recall * 100).toFixed(1)}%`,
                icon: Crosshair,
                color: 'text-green-400',
              },
              {
                label: 'F1 Score',
                value: `${(report.avg_f1 * 100).toFixed(1)}%`,
                icon: Award,
                color: 'text-yellow-400',
              },
            ].map((metric) => {
              const Icon = metric.icon
              return (
                <div
                  key={metric.label}
                  className="rounded-xl border border-border bg-card p-5 text-center"
                >
                  <Icon className={`h-6 w-6 ${metric.color} mx-auto mb-2`} />
                  <div className={`text-2xl font-bold ${metric.color}`}>
                    {metric.value}
                  </div>
                  <div className="text-[11px] text-muted-foreground">{metric.label}</div>
                </div>
              )
            })}
          </div>

          {/* Counts */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'True Positives', value: report.total_tp, color: 'text-green-400' },
              { label: 'False Positives', value: report.total_fp, color: 'text-red-400' },
              { label: 'False Negatives', value: report.total_fn, color: 'text-yellow-400' },
            ].map((c) => (
              <div
                key={c.label}
                className="rounded-lg border border-border bg-card p-3 text-center"
              >
                <div className={`text-xl font-bold ${c.color}`}>{c.value}</div>
                <div className="text-[10px] text-muted-foreground">{c.label}</div>
              </div>
            ))}
          </div>

          {/* Per-case chart */}
          <div className="rounded-xl border border-border bg-card p-5">
            <h2 className="text-sm font-semibold mb-4">Per-Case F1 Scores</h2>
            <ResponsiveContainer width="100%" height={Math.max(200, report.results.length * 40)}>
              <BarChart
                data={report.results}
                layout="vertical"
                margin={{ top: 0, right: 20, left: 0, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" horizontal={false} />
                <XAxis
                  type="number"
                  domain={[0, 1]}
                  tick={{ fill: '#a1a1aa', fontSize: 11 }}
                  axisLine={{ stroke: '#27272a' }}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="case_name"
                  tick={{ fill: '#a1a1aa', fontSize: 10 }}
                  axisLine={{ stroke: '#27272a' }}
                  tickLine={false}
                  width={150}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#18181b',
                    border: '1px solid #27272a',
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  formatter={(value: number) => `${(value * 100).toFixed(1)}%`}
                />
                <Bar dataKey="f1_score" radius={[0, 4, 4, 0]}>
                  {report.results.map((_, idx) => (
                    <Cell key={idx} fill="#3b82f6" fillOpacity={0.8} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Case details */}
          <div className="rounded-xl border border-border bg-card p-5">
            <h2 className="text-sm font-semibold mb-4">Case Details</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
                    <th className="pb-2 font-medium">Case</th>
                    <th className="pb-2 font-medium">TP</th>
                    <th className="pb-2 font-medium">FP</th>
                    <th className="pb-2 font-medium">FN</th>
                    <th className="pb-2 font-medium">Precision</th>
                    <th className="pb-2 font-medium">Recall</th>
                    <th className="pb-2 font-medium">F1</th>
                  </tr>
                </thead>
                <tbody>
                  {report.results.map((r) => (
                    <tr key={r.case_id} className="border-b border-border/50">
                      <td className="py-2 font-medium">{r.case_name}</td>
                      <td className="py-2 text-green-400">{r.true_positives}</td>
                      <td className="py-2 text-red-400">{r.false_positives}</td>
                      <td className="py-2 text-yellow-400">{r.false_negatives}</td>
                      <td className="py-2 font-mono">
                        {(r.precision * 100).toFixed(1)}%
                      </td>
                      <td className="py-2 font-mono">
                        {(r.recall * 100).toFixed(1)}%
                      </td>
                      <td className="py-2 font-mono font-bold text-primary">
                        {(r.f1_score * 100).toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

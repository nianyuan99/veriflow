import { useState } from 'react'
import { syncToObsidian } from '@/api/client'
import { Database, CheckCircle, ArrowRight } from 'lucide-react'

export default function ObsidianSync() {
  const [runId, setRunId] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ notes_created: number } | null>(null)
  const [error, setError] = useState('')

  const handleSync = async () => {
    if (!runId.trim()) {
      setError('请输入 Review Run ID')
      return
    }
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await syncToObsidian(runId)
      setResult(res)
    } catch (e: any) {
      setError(e.message || 'Sync failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Obsidian Sync</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Sync review findings to your Obsidian knowledge base as concept notes with automatic wikilinks
        </p>
      </div>

      {/* Info card */}
      <div className="rounded-xl border border-border bg-card/50 p-5">
        <div className="flex items-start gap-3">
          <Database className="h-5 w-5 text-purple-400 mt-0.5" />
          <div>
            <h3 className="text-sm font-semibold">Knowledge Base Integration</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Each finding becomes a concept note in{' '}
              <code className="text-purple-400 bg-purple-500/10 px-1 rounded">
                wiki/concepts/
              </code>{' '}
              with frontmatter, error analysis, fix principles, and automatic wikilinks.
              A daily summary is appended to{' '}
              <code className="text-purple-400 bg-purple-500/10 px-1 rounded">
                wiki/daily/YYYY-MM-DD.md
              </code>
              .
            </p>
          </div>
        </div>
      </div>

      {/* Sync form */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h2 className="text-sm font-semibold mb-4">Sync Review Run</h2>
        <div className="flex items-end gap-3">
          <div className="flex-1">
            <label className="text-[11px] text-muted-foreground block mb-1">
              Review Run ID
            </label>
            <input
              type="text"
              value={runId}
              onChange={(e) => setRunId(e.target.value)}
              placeholder="e.g. a1b2c3d4-..."
              className="w-full rounded-lg border border-border bg-zinc-900/50 px-3 py-2 font-mono text-sm text-zinc-300 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
          </div>
          <button
            onClick={handleSync}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-semibold text-white hover:bg-purple-500 disabled:opacity-50 transition-all"
          >
            {loading ? (
              <>Syncing...</>
            ) : (
              <>
                <ArrowRight className="h-4 w-4" />
                Sync to Obsidian
              </>
            )}
          </button>
        </div>

        {error && <p className="mt-3 text-sm text-red-400">{error}</p>}

        {result && (
          <div className="mt-4 flex items-center gap-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4">
            <CheckCircle className="h-5 w-5 text-emerald-400" />
            <div>
              <p className="text-sm font-semibold text-emerald-400">Sync Complete</p>
              <p className="text-xs text-muted-foreground">
                {result.notes_created} concept notes and 1 daily summary written to Obsidian vault
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

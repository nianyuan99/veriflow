import { useState } from 'react'
import { submitReview } from '@/api/client'
import { useAppStore } from '@/stores'
import {
  Play,
  Upload,
  FileText,
  Settings2,
  Shield,
  Zap,
  Brain,
  Palette,
  Sparkles,
} from 'lucide-react'
import type { ReviewSubmitResponse } from '@/types'

const agentDefs = [
  { id: 'security', label: 'Security', icon: Shield, color: 'text-red-400' },
  { id: 'performance', label: 'Performance', icon: Zap, color: 'text-yellow-400' },
  { id: 'logic', label: 'Logic', icon: Brain, color: 'text-blue-400' },
  { id: 'style', label: 'Style', icon: Palette, color: 'text-purple-400' },
  { id: 'ai_pattern', label: 'AI Pattern', icon: Sparkles, color: 'text-cyan-400' },
]

export default function Dashboard() {
  const [diffContent, setDiffContent] = useState('')
  const [repoPath, setRepoPath] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<ReviewSubmitResponse | null>(null)
  const [enabledAgents, setEnabledAgents] = useState<string[]>(
    agentDefs.map((a) => a.id)
  )

  const toggleAgent = (id: string) => {
    setEnabledAgents((prev) =>
      prev.includes(id) ? prev.filter((a) => a !== id) : [...prev, id]
    )
  }

  const handleSubmit = async () => {
    if (!diffContent.trim()) {
      setError('请输入或粘贴 diff 内容')
      return
    }
    setError('')
    setLoading(true)
    setResult(null)
    try {
      const res = await submitReview({
        diff_content: diffContent,
        repo_path: repoPath || undefined,
        enabled_agents: enabledAgents,
      })
      setResult(res)
    } catch (e: any) {
      setError(e.message || '审查失败')
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      setDiffContent(ev.target?.result as string)
    }
    reader.readAsText(file)
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Code Review</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Paste a diff/patch or upload a file to start AI-powered multi-agent review
        </p>
      </div>

      {/* Agent selector */}
      <div>
        <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
          Review Agents
        </h2>
        <div className="flex flex-wrap gap-2">
          {agentDefs.map((agent) => {
            const Icon = agent.icon
            const active = enabledAgents.includes(agent.id)
            return (
              <button
                key={agent.id}
                onClick={() => toggleAgent(agent.id)}
                className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition-all ${
                  active
                    ? 'border-primary/40 bg-primary/10 text-primary'
                    : 'border-border bg-card text-muted-foreground hover:border-muted-foreground/30'
                }`}
              >
                <Icon className={`h-3.5 w-3.5 ${active ? agent.color : ''}`} />
                {agent.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Diff input area */}
      <div className="rounded-xl border border-border bg-card/50 p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <FileText className="h-4 w-4 text-muted-foreground" />
            Diff Input
          </h2>
          <label className="inline-flex items-center gap-2 text-xs text-muted-foreground cursor-pointer hover:text-foreground transition-colors">
            <Upload className="h-3.5 w-3.5" />
            Upload .patch/.diff
            <input
              type="file"
              accept=".patch,.diff,.txt"
              onChange={handleFileUpload}
              className="hidden"
            />
          </label>
        </div>

        <textarea
          value={diffContent}
          onChange={(e) => setDiffContent(e.target.value)}
          placeholder={`粘贴 unified diff 内容...

示例:
diff --git a/app/main.py b/app/main.py
--- a/app/main.py
+++ b/app/main.py
@@ -10,6 +10,8 @@
 def get_user(user_id):
+def search(query):
+    sql = f"SELECT * FROM users WHERE name = '{query}'"
+    return db.execute(sql)`}
          rows={12}
          className="w-full rounded-lg border border-border bg-zinc-900/50 p-4 font-mono text-xs text-zinc-300 placeholder:text-zinc-600 resize-y focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50 transition-all"
        />

        <div className="mt-3 flex items-center gap-4">
          <input
            type="text"
            value={repoPath}
            onChange={(e) => setRepoPath(e.target.value)}
            placeholder="仓库路径 (可选)"
            className="flex-1 rounded-lg border border-border bg-zinc-900/50 px-3 py-1.5 font-mono text-xs text-zinc-300 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50"
          />
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {loading ? (
              <>
                <Settings2 className="h-4 w-4 animate-spin" />
                Reviewing...
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                Start Review
              </>
            )}
          </button>
        </div>

        {error && (
          <p className="mt-3 text-sm text-red-400">{error}</p>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="rounded-xl border border-border bg-card/50 p-6 animate-in fade-in slide-in-from-bottom-4">
          <h2 className="text-sm font-semibold mb-4">Review Results</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            {[
              { label: 'Total', value: result.total_findings },
              { label: 'P0 Critical', value: result.p0_count, color: 'text-red-400' },
              { label: 'P1 High', value: result.p1_count, color: 'text-yellow-400' },
              { label: 'P2 Medium', value: result.p2_count, color: 'text-blue-400' },
            ].map((stat) => (
              <div
                key={stat.label}
                className="rounded-lg border border-border bg-card p-3 text-center"
              >
                <div className={`text-2xl font-bold ${stat.color || 'text-foreground'}`}>
                  {stat.value}
                </div>
                <div className="text-[11px] text-muted-foreground">{stat.label}</div>
              </div>
            ))}
          </div>

          {result.findings && result.findings.length > 0 && (
            <div className="space-y-2">
              {result.findings.map((f) => (
                <div
                  key={f.id}
                  className="flex items-center gap-3 rounded-lg border border-border bg-zinc-900/30 p-3 text-sm"
                >
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0 text-[10px] font-mono font-bold ${
                      f.severity === 'P0'
                        ? 'bg-red-500/20 text-red-400'
                        : f.severity === 'P1'
                        ? 'bg-yellow-500/20 text-yellow-400'
                        : f.severity === 'P2'
                        ? 'bg-blue-500/20 text-blue-400'
                        : 'bg-zinc-500/20 text-zinc-400'
                    }`}
                  >
                    {f.severity}
                  </span>
                  <span className="flex-1 font-medium truncate">{f.title}</span>
                  <span className="text-xs text-muted-foreground font-mono truncate">
                    {f.file_path}:{f.line_start}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

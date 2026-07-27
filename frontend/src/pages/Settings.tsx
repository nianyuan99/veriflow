import { useEffect, useState } from 'react'
import { getSettings } from '@/api/client'
import type { Settings } from '@/types'
import { Settings2, Server, Cpu, CheckCircle, XCircle } from 'lucide-react'

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null)

  useEffect(() => {
    getSettings().then(setSettings).catch(console.error)
  }, [])

  if (!settings) {
    return (
      <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
        Loading...
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          System configuration and status
        </p>
      </div>

      {/* System status */}
      <div className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-sm font-semibold mb-4 flex items-center gap-2">
          <Server className="h-4 w-4" />
          System Status
        </h2>
        <div className="grid grid-cols-2 gap-4">
          <StatusRow
            label="Docker Engine"
            available={settings.docker_available}
          />
          <StatusRow
            label="Obsidian Vault"
            available={settings.obsidian_enabled}
          />
        </div>
      </div>

      {/* LLM Providers */}
      <div className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-sm font-semibold mb-4 flex items-center gap-2">
          <Cpu className="h-4 w-4" />
          LLM Providers
        </h2>
        <div className="flex flex-wrap gap-2">
          {settings.llm_providers.map((p) => (
            <span
              key={p}
              className="inline-flex items-center rounded-full border border-border bg-zinc-900/50 px-3 py-1 text-xs font-mono"
            >
              {p}
            </span>
          ))}
        </div>
      </div>

      {/* Available Agents */}
      <div className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-sm font-semibold mb-4 flex items-center gap-2">
          <Settings2 className="h-4 w-4" />
          Available Agents
        </h2>
        <div className="flex flex-wrap gap-2">
          {settings.available_agents.map((a) => (
            <span
              key={a}
              className="inline-flex items-center rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-xs font-mono text-emerald-400"
            >
              {a}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

function StatusRow({
  label,
  available,
}: {
  label: string
  available: boolean
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-border bg-zinc-900/30 p-3">
      <span className="text-sm">{label}</span>
      {available ? (
        <span className="inline-flex items-center gap-1 text-xs text-emerald-400">
          <CheckCircle className="h-3.5 w-3.5" />
          Connected
        </span>
      ) : (
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
          <XCircle className="h-3.5 w-3.5" />
          Not Available
        </span>
      )}
    </div>
  )
}

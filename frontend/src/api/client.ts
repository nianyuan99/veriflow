import type {
  ReviewSubmitResponse,
  ReviewRun,
  Finding,
  BenchmarkReport,
  SyncResult,
  Settings,
} from '@/types'

const BASE_URL = '/api/v1'

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`
  const config: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  }

  const resp = await fetch(url, config)
  if (!resp.ok) {
    const err = await resp.text()
    throw new Error(`API Error ${resp.status}: ${err}`)
  }
  return resp.json()
}

// ── Review ──────────────────────────────────────────────────────

export async function submitReview(data: {
  diff_content: string
  repo_path?: string
  branch_name?: string
  pr_title?: string
  llm_provider?: string
  llm_model?: string
  enabled_agents?: string[]
}): Promise<ReviewSubmitResponse> {
  return request<ReviewSubmitResponse>('/review', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getReviewDetail(
  runId: string
): Promise<ReviewRun> {
  return request<ReviewRun>(`/review/${runId}`)
}

export async function listFindings(params?: {
  run_id?: string
  severity?: string
  agent_type?: string
  limit?: number
  offset?: number
}): Promise<{ total: number; findings: Finding[] }> {
  const searchParams = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined) searchParams.set(k, String(v))
    })
  }
  const qs = searchParams.toString()
  return request(`/findings${qs ? `?${qs}` : ''}`)
}

// ── Benchmark ──────────────────────────────────────────────────

export async function runBenchmark(data: {
  name?: string
  llm_model?: string
}): Promise<BenchmarkReport> {
  return request<BenchmarkReport>('/bench/run', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ── Obsidian ───────────────────────────────────────────────────

export async function syncToObsidian(
  reviewRunId: string
): Promise<SyncResult> {
  return request<SyncResult>('/obsidian/sync', {
    method: 'POST',
    body: JSON.stringify({ review_run_id: reviewRunId }),
  })
}

// ── Settings ───────────────────────────────────────────────────

export async function getSettings(): Promise<Settings> {
  return request<Settings>('/settings')
}

// ── Health ─────────────────────────────────────────────────────

export async function healthCheck(): Promise<{ status: string }> {
  return request('/health')
}

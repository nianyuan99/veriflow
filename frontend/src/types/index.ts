// ── API 响应类型 ──────────────────────────────────────────────────

export type Severity = 'P0' | 'P1' | 'P2' | 'P3'
export type AgentType = 'security' | 'performance' | 'logic' | 'style' | 'ai_pattern'
export type ReviewStatus =
  | 'pending'
  | 'preparing'
  | 'reviewing'
  | 'fixing'
  | 'verifying'
  | 'completed'
  | 'failed'
export type FixStatus =
  | 'pending'
  | 'generating'
  | 'sandbox_running'
  | 'sandbox_passed'
  | 'sandbox_failed'
  | 'retrying'
  | 'manual_required'

export interface Finding {
  id: string
  review_run_id?: string
  agent_type: AgentType
  file_path: string
  line_start: number | null
  line_end: number | null
  severity: Severity
  title: string
  description: string
  suggestion: string | null
  code_snippet: string | null
  pattern_id: string | null
  is_fixed: boolean
  fix_confidence: number | null
  created_at: string | null
}

export interface FixAttempt {
  id: string
  finding_id: string
  attempt_number: number
  status: FixStatus
  original_code: string | null
  fixed_code: string | null
  diff_patch: string | null
  validation_output: string | null
  error_message: string | null
  created_at: string | null
  completed_at: string | null
}

export interface ReviewRun {
  run_id: string
  status: ReviewStatus
  repo_path: string | null
  branch_name: string | null
  pr_title: string | null
  total_findings: number
  p0_count: number
  p1_count: number
  p2_count: number
  p3_count: number
  total_fix_attempts: number
  fix_success_rate: number | null
  llm_model: string | null
  created_at: string | null
  findings: Finding[]
  fix_attempts: FixAttempt[]
}

export interface ReviewSubmitResponse {
  run_id: string
  status: string
  total_findings: number
  p0_count: number
  p1_count: number
  p2_count: number
  p3_count: number
  findings: Finding[]
}

export interface BenchmarkReport {
  name: string
  total_cases: number
  avg_precision: number
  avg_recall: number
  avg_f1: number
  total_tp: number
  total_fp: number
  total_fn: number
  results: BenchmarkResult[]
}

export interface BenchmarkResult {
  case_id: string
  case_name: string
  true_positives: number
  false_positives: number
  false_negatives: number
  precision: number
  recall: number
  f1_score: number
}

export interface SyncResult {
  status: string
  review_run_id: string
  notes_created: number
}

export interface Settings {
  llm_providers: string[]
  available_agents: string[]
  obsidian_enabled: boolean
  docker_available: boolean
}

// ── WebSocket 消息类型 ────────────────────────────────────────────

export interface WSMessage {
  type: 'status' | 'complete'
  run_id: string
  status?: ReviewStatus
  total_findings?: number
  fix_success_rate?: number
}

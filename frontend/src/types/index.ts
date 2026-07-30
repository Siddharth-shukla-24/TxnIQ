// ── Job types ──────────────────────────────────────────────────────────────

export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed'

export type RiskLevel = 'low' | 'medium' | 'high'

export interface JobSummary {
  total_spend_inr: number | null
  total_spend_usd: number | null
  anomaly_count: number
  risk_level: RiskLevel | null
  narrative: string | null
  top_merchants: TopMerchant[] | null
}

export interface TopMerchant {
  merchant: string
  total_spend?: number
  total_transactions?: number
}

export interface Job {
  job_id: string
  status: JobStatus
  filename: string
  row_count_raw: number | null
  row_count_clean: number | null
  created_at: string
  completed_at: string | null
  error_message: string | null
  summary: JobSummary | null
}

export interface JobListItem {
  job_id: string
  status: JobStatus
  filename: string
  row_count_raw: number | null
  created_at: string
}

export interface JobListResponse {
  total: number
  jobs: JobListItem[]
}

// ── Transaction types ──────────────────────────────────────────────────────

export interface Transaction {
  id: string
  txn_id: string | null
  date: string | null
  merchant: string | null
  amount: string | null
  currency: string | null
  txn_status: string | null
  category: string | null
  account_id: string | null
  notes: string | null
  is_anomaly: boolean
  anomaly_reason: string | null
  llm_category: string | null
  llm_failed: boolean
}

export interface CategoryBreakdown {
  category: string
  total_amount: string
  transaction_count: number
  currency: string
}

export interface JobResults {
  job_id: string
  status: JobStatus
  transactions: Transaction[]
  anomalies: Transaction[]
  category_breakdown: CategoryBreakdown[]
  summary: JobSummary | null
}

// ── Upload types ───────────────────────────────────────────────────────────

export interface UploadResponse {
  job_id: string
  status: JobStatus
  message: string
}

// ── Health types ───────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string
  environment: string
  version: string
}
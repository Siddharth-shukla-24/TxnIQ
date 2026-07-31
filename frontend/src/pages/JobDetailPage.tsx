import { useParams, useNavigate } from 'react-router-dom'
import { useJobStatus, useJobResults } from '@/hooks/useJobs'
import StatusBadge from '@/components/StatusBadge'
import {
  ArrowLeft,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  ShieldAlert,
  Layers,
  Brain,
  Inbox,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { formatDistanceToNow, formatCurrency, getRiskBg } from '@/lib/utils'
import type { JobStatus, Transaction, CategoryBreakdown } from '@/types'
import clsx from 'clsx'

export default function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()

  const { data: jobStatus, isLoading: statusLoading } = useJobStatus(jobId ?? null)
  const isCompleted = jobStatus?.status === 'completed'
  const { data: results, isLoading: resultsLoading } = useJobResults(jobId ?? null, isCompleted)

  if (statusLoading) {
    return (
      <div className="max-w-4xl mx-auto space-y-4">
        {[80, 120, 200, 160].map((h, i) => (
          <div
            key={i}
            className="skeleton"
            style={{ height: h, opacity: 1 - i * 0.15 }}
          />
        ))}
      </div>
    )
  }

  if (!jobStatus) {
    return (
      <div className="empty-state">
        <div className="icon-box-lg bg-white/[0.03] border border-[#1f1f1f] mx-auto mb-4">
          <Inbox className="w-5 h-5 text-[#444]" />
        </div>
        <p className="text-sm font-medium text-[#888]">Job not found</p>
        <button
          onClick={() => navigate('/jobs')}
          className="mt-3 text-xs text-blue-400 hover:text-blue-300 transition-colors"
        >
          ← Back to jobs
        </button>
      </div>
    )
  }

  const summary = results?.summary ?? jobStatus.summary

  return (
    <div className="animate-fade-in max-w-4xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-start gap-4">
        <button
          onClick={() => navigate('/jobs')}
          className="mt-1 text-[#444] hover:text-white transition-colors"
          aria-label="Back to jobs"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h2 className="text-lg font-semibold text-white truncate">
              {jobStatus.filename}
            </h2>
            <StatusBadge status={jobStatus.status as JobStatus} />
          </div>
          <p className="text-[11px] text-[#444] font-mono mt-1">{jobId}</p>
        </div>
      </div>

      {/* Meta stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Raw Rows', value: jobStatus.row_count_raw ?? '—', color: 'text-white' },
          { label: 'Clean Rows', value: jobStatus.row_count_clean ?? '—', color: 'text-emerald-400' },
          { label: 'Anomalies', value: summary?.anomaly_count ?? '—', color: 'text-red-400' },
          { label: 'Created', value: formatDistanceToNow(jobStatus.created_at), color: 'text-[#888]' },
        ].map(({ label, value, color }) => (
          <div key={label} className="card py-4">
            <p className="section-label">{label}</p>
            <p className={clsx('text-2xl font-bold mt-1.5 font-mono', color)}>{value}</p>
          </div>
        ))}
      </div>

      {/* Error state */}
      {jobStatus.status === 'failed' && jobStatus.error_message && (
        <div className="alert-error">
          <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-red-400">Job Failed</p>
            <p className="text-xs text-[#666] mt-1 font-mono leading-relaxed">
              {jobStatus.error_message}
            </p>
          </div>
        </div>
      )}

      {/* Processing indicator */}
      {(jobStatus.status === 'pending' || jobStatus.status === 'processing') && (
        <div className="card flex items-center gap-4">
          <div className="icon-box-md bg-blue-500/10 border border-blue-500/20">
            <Brain className="w-4 h-4 text-blue-400 animate-pulse" />
          </div>
          <div>
            <p className="text-sm font-medium text-white">Pipeline running</p>
            <p className="text-xs text-[#555] mt-0.5">
              Cleaning → Anomaly detection → LLM classification → Summary
            </p>
          </div>
        </div>
      )}

      {/* Results */}
      {isCompleted && !resultsLoading && results && (
        <>
          {/* AI Summary */}
          {summary && (
            <div className="card">
              <div className="flex items-center gap-3 mb-5">
                <div className="icon-box-sm bg-purple-500/10 border border-purple-500/20">
                  <Brain className="w-3.5 h-3.5 text-purple-400" />
                </div>
                <h3 className="text-sm font-semibold text-white">AI Summary</h3>
                {summary.risk_level && (
                  <span className={clsx('ml-auto badge border', getRiskBg(summary.risk_level))}>
                    {summary.risk_level.toUpperCase()} RISK
                  </span>
                )}
              </div>

              {summary.narrative && (
                <p className="text-sm text-[#888] leading-relaxed mb-5 pb-5 border-b border-[#1a1a1a]">
                  {summary.narrative}
                </p>
              )}

              <div className="grid grid-cols-2 gap-6">
                <div>
                  <p className="section-label">Total INR Spend</p>
                  <p className="text-2xl font-bold text-white mt-1.5 font-mono">
                    {formatCurrency(summary.total_spend_inr, 'INR')}
                  </p>
                </div>
                <div>
                  <p className="section-label">Total USD Spend</p>
                  <p className="text-2xl font-bold text-white mt-1.5 font-mono">
                    {formatCurrency(summary.total_spend_usd, 'USD')}
                  </p>
                </div>
              </div>

              {summary.top_merchants && summary.top_merchants.length > 0 && (
                <div className="mt-5 pt-5 border-t border-[#1a1a1a]">
                  <p className="section-label mb-3">Top Merchants</p>
                  <div className="space-y-2.5">
                    {summary.top_merchants.map((m, i) => (
                      <div key={i} className="flex items-center gap-3">
                        <span className="text-xs text-[#333] w-4 tabular-nums">{i + 1}</span>
                        <span className="flex-1 text-sm text-[#ccc]">{m.merchant}</span>
                        <span className="text-xs text-[#888] font-mono tabular-nums">
                          {m.total_spend != null
                            ? `₹${Number(m.total_spend).toLocaleString('en-IN')}`
                            : m.total_transactions != null
                            ? `${m.total_transactions} txns`
                            : '—'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Spend chart */}
          {results.category_breakdown.length > 0 && (
            <SpendChart breakdown={results.category_breakdown} />
          )}

          {/* Anomalies */}
          {results.anomalies.length > 0 && (
            <div className="card">
              <div className="flex items-center gap-3 mb-5">
                <div className="icon-box-sm bg-red-500/10 border border-red-500/20">
                  <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
                </div>
                <h3 className="text-sm font-semibold text-white">Flagged Anomalies</h3>
                <span className="ml-auto badge bg-red-500/10 text-red-400 border border-red-500/20">
                  {results.anomalies.length}
                </span>
              </div>
              <div className="space-y-2.5">
                {results.anomalies.map((txn) => (
                  <AnomalyRow key={txn.id} txn={txn} />
                ))}
              </div>
            </div>
          )}

          {/* Transactions table */}
          <div className="card p-0 overflow-hidden">
            <div className="px-6 py-4 border-b border-[#1a1a1a] flex items-center gap-3">
              <div className="icon-box-sm bg-white/[0.03] border border-[#1f1f1f]">
                <Layers className="w-3.5 h-3.5 text-[#555]" />
              </div>
              <h3 className="text-sm font-semibold text-white">Transactions</h3>
              <span className="ml-auto text-xs text-[#444] font-mono">
                {results.transactions.length} rows
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[#1a1a1a]">
                    {['Txn ID', 'Date', 'Merchant', 'Amount', 'Category', 'Status', ''].map((h) => (
                      <th key={h} className="px-5 py-3.5 text-left">
                        <span className="section-label">{h}</span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {results.transactions.map((txn) => (
                    <TransactionRow key={txn.id} txn={txn} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {resultsLoading && isCompleted && (
        <div className="space-y-4">
          {[140, 200, 160].map((h, i) => (
            <div
              key={i}
              className="skeleton"
              style={{ height: h, opacity: 1 - i * 0.2 }}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function AnomalyRow({ txn }: { txn: Transaction }) {
  return (
    <div className="flex items-start gap-3 px-4 py-3.5 bg-red-500/[0.04] border border-red-500/10 rounded-xl">
      <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-semibold text-white">{txn.merchant}</span>
          <span className="text-xs text-[#444] font-mono">{txn.txn_id}</span>
          <span className="ml-auto text-sm font-bold text-red-400 font-mono">
            {txn.currency === 'INR' ? '₹' : '$'}
            {txn.amount ? Number(txn.amount).toLocaleString('en-IN') : '—'}
          </span>
        </div>
        {txn.anomaly_reason && (
          <p className="text-xs text-[#555] mt-1 leading-relaxed">{txn.anomaly_reason}</p>
        )}
      </div>
    </div>
  )
}

function TransactionRow({ txn }: { txn: Transaction }) {
  return (
    <tr className={clsx('table-row', txn.is_anomaly && 'bg-red-500/[0.03]')}>
      <td className="px-5 py-3.5 text-xs font-mono text-[#444] whitespace-nowrap">
        {txn.txn_id ?? '—'}
      </td>
      <td className="px-5 py-3.5 text-xs text-[#555] whitespace-nowrap">
        {txn.date ?? '—'}
      </td>
      <td className="px-5 py-3.5 text-sm text-white whitespace-nowrap">
        {txn.merchant ?? '—'}
      </td>
      <td className="px-5 py-3.5 text-sm font-mono text-white whitespace-nowrap tabular-nums">
        {txn.currency === 'INR' ? '₹' : '$'}
        {txn.amount ? Number(txn.amount).toLocaleString('en-IN') : '—'}
      </td>
      <td className="px-5 py-3.5 whitespace-nowrap">
        <span className="text-xs px-2 py-1 bg-white/[0.04] border border-white/[0.06] rounded-lg text-[#888]">
          {txn.llm_category ?? txn.category ?? '—'}
        </span>
      </td>
      <td className="px-5 py-3.5 whitespace-nowrap">
        <span
          className={clsx('text-xs font-medium', {
            'text-emerald-400': txn.txn_status === 'SUCCESS',
            'text-red-400': txn.txn_status === 'FAILED',
            'text-amber-400': txn.txn_status === 'PENDING',
          })}
        >
          {txn.txn_status ?? '—'}
        </span>
      </td>
      <td className="px-5 py-3.5">
        {txn.is_anomaly ? (
          <AlertTriangle className="w-4 h-4 text-red-400" />
        ) : (
          <CheckCircle className="w-4 h-4 text-emerald-400/40" />
        )}
      </td>
    </tr>
  )
}

function SpendChart({ breakdown }: { breakdown: CategoryBreakdown[] }) {
  const COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#a855f7', '#ef4444', '#06b6d4', '#f97316', '#84cc16']

  const data = breakdown
    .filter((b) => b.currency === 'INR')
    .map((b) => ({
      category: b.category.length > 11 ? b.category.slice(0, 11) + '…' : b.category,
      amount: parseFloat(b.total_amount),
    }))
    .sort((a, b) => b.amount - a.amount)

  if (data.length === 0) return null

  return (
    <div className="card">
      <div className="flex items-center gap-3 mb-5">
        <div className="icon-box-sm bg-blue-500/10 border border-blue-500/20">
          <TrendingUp className="w-3.5 h-3.5 text-blue-400" />
        </div>
        <h3 className="text-sm font-semibold text-white">Spend by Category</h3>
        <span className="ml-auto section-label">INR</span>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
          <XAxis
            dataKey="category"
            tick={{ fill: '#444', fontSize: 11, fontFamily: 'Inter' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: '#444', fontSize: 11, fontFamily: 'Inter' }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
            width={52}
          />
          <Tooltip
  contentStyle={{
    backgroundColor: '#111',
    border: '1px solid #1f1f1f',
    borderRadius: '12px',
    color: '#fff',
    fontFamily: 'Inter',
    boxShadow: '0 8px 24px rgba(0,0,0,0.45)',
  }}
  labelStyle={{
    color: '#ffffff',
    fontWeight: 600,
  }}
  itemStyle={{
    color: '#d4d4d8',
  }}
  formatter={(value: number) => [
    `₹${value.toLocaleString('en-IN')}`,
    'Amount',
  ]}
  cursor={{ fill: 'rgba(255,255,255,0.04)' }}
/>
          <Bar dataKey="amount" radius={[5, 5, 0, 0]} maxBarSize={48}>
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} opacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
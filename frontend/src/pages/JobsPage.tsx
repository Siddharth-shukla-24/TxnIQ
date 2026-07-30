import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useJobs } from '@/hooks/useJobs'
import StatusBadge from '@/components/StatusBadge'
import { Layers, ArrowRight, RefreshCw } from 'lucide-react'
import { formatDistanceToNow } from '@/lib/utils'
import type { JobStatus } from '@/types'
import clsx from 'clsx'

const STATUS_FILTERS = ['all', 'pending', 'processing', 'completed', 'failed'] as const
type FilterType = (typeof STATUS_FILTERS)[number]

export default function JobsPage() {
  const navigate = useNavigate()
  const [filter, setFilter] = useState<FilterType>('all')
  const { data, isLoading, refetch, isFetching } = useJobs(
    filter === 'all' ? undefined : filter
  )
  const jobs = data?.jobs ?? []

  return (
    <div className="animate-fade-in max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-white tracking-tight">Job History</h2>
          <p className="text-sm text-[#555] mt-0.5">{data?.total ?? 0} total jobs</p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="btn-secondary gap-2"
        >
          <RefreshCw className={clsx('w-3.5 h-3.5', isFetching && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-5 flex-wrap">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={clsx(
              'px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all duration-150',
              filter === s
                ? 'bg-white text-black'
                : 'bg-white/[0.03] border border-[#1f1f1f] text-[#666] hover:text-[#ccc] hover:border-[#2a2a2a]'
            )}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="card p-0 overflow-hidden">
        {isLoading ? (
          <div className="p-6 space-y-2.5">
            {Array.from({ length: 7 }).map((_, i) => (
              <div
                key={i}
                className="h-12 bg-white/[0.02] rounded-xl animate-pulse"
                style={{ opacity: 1 - i * 0.12 }}
              />
            ))}
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-12 h-12 bg-white/[0.03] border border-[#1f1f1f] rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Layers className="w-5 h-5 text-[#444]" />
            </div>
            <p className="text-sm font-medium text-[#888]">No jobs found</p>
            <p className="text-xs text-[#444] mt-1">
              {filter !== 'all' ? `No ${filter} jobs` : 'Upload a CSV to get started'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#161616]">
                  {['File', 'Status', 'Raw Rows', 'Job ID', 'Created', ''].map((h) => (
                    <th key={h} className="px-5 py-3.5 text-left">
                      <span className="section-label">{h}</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr
                    key={job.job_id}
                    onClick={() => navigate(`/jobs/${job.job_id}`)}
                    className="table-row cursor-pointer group"
                  >
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-7 h-7 bg-white/[0.03] border border-[#1f1f1f] rounded-lg flex items-center justify-center flex-shrink-0">
                          <Layers className="w-3.5 h-3.5 text-[#555]" />
                        </div>
                        <span className="text-sm font-medium text-white truncate max-w-[180px]">
                          {job.filename}
                        </span>
                      </div>
                    </td>
                    <td className="px-5 py-4">
                      <StatusBadge status={job.status as JobStatus} />
                    </td>
                    <td className="px-5 py-4 text-sm text-[#666] font-mono tabular-nums">
                      {job.row_count_raw ?? '—'}
                    </td>
                    <td className="px-5 py-4 text-xs text-[#444] font-mono">
                      {job.job_id.slice(0, 8)}…
                    </td>
                    <td className="px-5 py-4 text-sm text-[#555]">
                      {formatDistanceToNow(job.created_at)}
                    </td>
                    <td className="px-5 py-4">
                      <ArrowRight className="w-4 h-4 text-[#2a2a2a] group-hover:text-[#555] transition-colors" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
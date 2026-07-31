import { useNavigate } from 'react-router-dom'
import { useJobs } from '@/hooks/useJobs'
import HealthBar from '@/components/HealthBar'
import StatCard from '@/components/StatCard'
import StatusBadge from '@/components/StatusBadge'
import {
  Layers,
  CheckCircle,
  XCircle,
  Clock,
  ArrowRight,
  Upload,
  Inbox,
} from 'lucide-react'
import type { JobListItem, JobStatus } from '@/types'
import { formatDistanceToNow } from '@/lib/utils'

export default function DashboardPage() {
  const navigate = useNavigate()
  const { data, isLoading } = useJobs()

  const jobs = data?.jobs ?? []
  const total = data?.total ?? 0
  const completed = jobs.filter((j) => j.status === 'completed').length
  const failed = jobs.filter((j) => j.status === 'failed').length
  const processing = jobs.filter(
    (j) => j.status === 'processing' || j.status === 'pending'
  ).length

  return (
    <div className="animate-fade-in space-y-8 max-w-6xl mx-auto">
      <HealthBar />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white tracking-tight">Overview</h2>
          <p className="text-sm text-[#555] mt-0.5">
            AI-powered transaction processing pipeline
          </p>
        </div>
        <button
          onClick={() => navigate('/upload')}
          className="btn-primary"
        >
          <Upload className="w-4 h-4" />
          Upload CSV
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Jobs"
          value={isLoading ? '—' : total}
          icon={Layers}
          iconColor="text-blue-400"
          sub="All time"
        />
        <StatCard
          label="Completed"
          value={isLoading ? '—' : completed}
          icon={CheckCircle}
          iconColor="text-emerald-400"
          sub="Successfully processed"
        />
        <StatCard
          label="Failed"
          value={isLoading ? '—' : failed}
          icon={XCircle}
          iconColor="text-red-400"
          sub="Requires attention"
        />
        <StatCard
          label="In Progress"
          value={isLoading ? '—' : processing}
          icon={Clock}
          iconColor="text-amber-400"
          sub="Pending or processing"
        />
      </div>

      {/* Recent jobs */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white">Recent Jobs</h3>
          <button
            onClick={() => navigate('/jobs')}
            className="flex items-center gap-1 text-xs text-[#555] hover:text-white transition-colors"
          >
            View all <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        <div className="card p-0 overflow-hidden">
          {isLoading ? (
            <LoadingSkeleton rows={5} />
          ) : jobs.length === 0 ? (
            <EmptyState />
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#1a1a1a]">
                  {['File', 'Status', 'Rows', 'Created', ''].map((h) => (
                    <th
                      key={h}
                      className="px-5 py-3.5 text-left"
                    >
                      <span className="section-label">{h}</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {jobs.slice(0, 8).map((job) => (
                  <JobRow
                    key={job.job_id}
                    job={job}
                    onClick={() => navigate(`/jobs/${job.job_id}`)}
                  />
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}

function JobRow({ job, onClick }: { job: JobListItem; onClick: () => void }) {
  return (
    <tr className="table-row cursor-pointer group" onClick={onClick}>
      <td className="px-5 py-3.5">
        <div className="flex items-center gap-3">
          <div className="icon-box-sm bg-white/[0.04] border border-white/[0.06]">
            <Layers className="w-3.5 h-3.5 text-[#555]" />
          </div>
          <span className="text-sm text-white font-medium truncate max-w-[180px]">
            {job.filename}
          </span>
        </div>
      </td>
      <td className="px-5 py-3.5">
        <StatusBadge status={job.status as JobStatus} />
      </td>
      <td className="px-5 py-3.5 text-sm text-[#666] font-mono tabular-nums">
        {job.row_count_raw ?? '—'}
      </td>
      <td className="px-5 py-3.5 text-sm text-[#555]">
        {formatDistanceToNow(job.created_at)}
      </td>
      <td className="px-5 py-3.5">
        <ArrowRight className="w-4 h-4 text-[#2a2a2a] group-hover:text-[#555] transition-colors" />
      </td>
    </tr>
  )
}

function LoadingSkeleton({ rows }: { rows: number }) {
  return (
    <div className="p-6 space-y-2.5">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-10 skeleton"
          style={{ opacity: 1 - i * 0.15 }}
        />
      ))}
    </div>
  )
}

function EmptyState() {
  const navigate = useNavigate()
  return (
    <div className="empty-state">
      <div className="icon-box-lg bg-white/[0.03] border border-[#1f1f1f] mx-auto mb-4">
        <Inbox className="w-5 h-5 text-[#444]" />
      </div>
      <p className="text-sm font-medium text-[#888]">No jobs yet</p>
      <p className="text-xs text-[#444] mt-1 mb-5">
        Upload a CSV file to start the AI pipeline
      </p>
      <button
        onClick={() => navigate('/upload')}
        className="btn-secondary inline-flex"
      >
        Upload your first CSV
      </button>
    </div>
  )
}
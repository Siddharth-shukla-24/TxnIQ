import clsx from 'clsx'
import type { JobStatus } from '@/types'

const config: Record<JobStatus, { label: string; classes: string; dot: string }> = {
  pending: {
    label: 'Pending',
    classes: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
    dot: 'bg-amber-400',
  },
  processing: {
    label: 'Processing',
    classes: 'bg-blue-500/10 text-blue-400 border border-blue-500/20',
    dot: 'bg-blue-400 animate-pulse',
  },
  completed: {
    label: 'Completed',
    classes: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
    dot: 'bg-emerald-400',
  },
  failed: {
    label: 'Failed',
    classes: 'bg-red-500/10 text-red-400 border border-red-500/20',
    dot: 'bg-red-400',
  },
}

export default function StatusBadge({ status }: { status: JobStatus }) {
  const { label, classes, dot } = config[status]
  return (
    <span className={clsx('badge', classes)}>
      <span className={clsx('w-1.5 h-1.5 rounded-full flex-shrink-0', dot)} />
      {label}
    </span>
  )
}
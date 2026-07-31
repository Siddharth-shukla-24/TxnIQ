import clsx from 'clsx'
import type { LucideIcon } from 'lucide-react'

interface StatCardProps {
  label: string
  value: string | number
  icon: LucideIcon
  iconColor?: string
  sub?: string
}

export default function StatCard({
  label,
  value,
  icon: Icon,
  iconColor = 'text-blue-400',
  sub,
}: StatCardProps) {
  return (
    <div className="card group hover:border-[#2a2a2a] transition-all duration-200">
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="section-label">{label}</p>
          <p className="stat-value">{value}</p>
          {sub && <p className="text-xs text-[#555] pt-0.5">{sub}</p>}
        </div>
        <div
          className={clsx(
            'icon-box-md',
            'bg-white/[0.04] border border-white/[0.06] transition-colors duration-200',
            'group-hover:bg-white/[0.06]',
            iconColor
          )}
        >
          <Icon className="w-4 h-4" />
        </div>
      </div>
    </div>
  )
}
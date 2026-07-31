import { useHealth } from '@/hooks/useJobs'
import clsx from 'clsx'

interface ServiceDotProps {
  label: string
  healthy: boolean
  loading?: boolean
}

function ServiceDot({ label, healthy, loading }: ServiceDotProps) {
  return (
    <div className="flex items-center gap-2">
      <div
        className={clsx('w-1.5 h-1.5 rounded-full flex-shrink-0 transition-colors', {
          'bg-emerald-400': healthy && !loading,
          'bg-red-400': !healthy && !loading,
          'bg-[#333] animate-pulse': loading,
        })}
      />
      <span className="text-xs text-[#666]">{label}</span>
    </div>
  )
}

export default function HealthBar() {
  const { data, isLoading, isError } = useHealth()
  const isHealthy = !isError && !!data

  return (
    <div className="flex items-center gap-4 px-5 py-3 bg-[#0f0f0f] border border-[#1a1a1a] rounded-xl mb-8 flex-wrap gap-y-2">
      <span className="section-label mr-1">System</span>
      <ServiceDot label="API" healthy={isHealthy} loading={isLoading} />
      <span className="w-px h-3 bg-[#222]" aria-hidden="true" />
      <ServiceDot label="Worker" healthy={isHealthy} loading={isLoading} />
      <span className="w-px h-3 bg-[#222]" aria-hidden="true" />
      <ServiceDot label="Redis" healthy={isHealthy} loading={isLoading} />
      <span className="w-px h-3 bg-[#222]" aria-hidden="true" />
      <ServiceDot label="PostgreSQL" healthy={isHealthy} loading={isLoading} />
      {data && (
        <div className="ml-auto flex items-center gap-2">
          <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
            Stable
          </span>
          <span className="text-[11px] text-zinc-500 font-medium">
            v{data.version}
          </span>
        </div>
      )}
    </div>
  )
}
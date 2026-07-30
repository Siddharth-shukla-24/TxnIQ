export function formatDistanceToNow(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHr = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHr / 24)

  if (diffDay > 0) return `${diffDay}d ago`
  if (diffHr > 0) return `${diffHr}h ago`
  if (diffMin > 0) return `${diffMin}m ago`
  return 'just now'
}

export function formatCurrency(amount: string | number | null, currency: string): string {
  if (amount == null) return '—'
  const num = typeof amount === 'string' ? parseFloat(amount) : amount
  if (isNaN(num)) return '—'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: currency === 'USD' ? 'USD' : 'INR',
    maximumFractionDigits: 2,
  }).format(num)
}

export function getRiskColor(risk: string | null): string {
  switch (risk) {
    case 'high': return 'text-accent-red'
    case 'medium': return 'text-accent-yellow'
    case 'low': return 'text-accent-green'
    default: return 'text-text-muted'
  }
}

export function getRiskBg(risk: string | null): string {
  switch (risk) {
    case 'high': return 'bg-accent-red/10 border-accent-red/20 text-accent-red'
    case 'medium': return 'bg-accent-yellow/10 border-accent-yellow/20 text-accent-yellow'
    case 'low': return 'bg-accent-green/10 border-accent-green/20 text-accent-green'
    default: return 'bg-bg-tertiary border-border-subtle text-text-muted'
  }
}
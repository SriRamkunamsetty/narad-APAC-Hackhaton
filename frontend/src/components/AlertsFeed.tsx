import { AlertTriangle } from 'lucide-react'

interface Props { alerts: string[]; cityAlerts: string[] }

export default function AlertsFeed({ alerts, cityAlerts }: Props) {
  const all = [...cityAlerts, ...alerts].slice(0, 8)
  if (all.length === 0) return null

  return (
    <div className="bg-crit/5 border border-crit/20 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-2.5 text-crit text-xs font-semibold uppercase tracking-wider">
        <AlertTriangle size={13} className="animate-blink" />
        Live Alerts
      </div>
      <div className="space-y-1.5">
        {all.map((a, i) => (
          <div key={i} className="text-xs text-ink/90 leading-relaxed animate-in">{a}</div>
        ))}
      </div>
    </div>
  )
}

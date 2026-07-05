import { useEffect, useState } from 'react'
import { Radio, Cpu, Zap } from 'lucide-react'

interface Props {
  connected: boolean
  city: string
  healthScore?: number
}

export default function StatusBar({ connected, city, healthScore }: Props) {
  const [time, setTime] = useState(new Date())

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  const scoreColor = healthScore === undefined ? 'text-inkdim'
    : healthScore >= 70 ? 'text-signal'
    : healthScore >= 45 ? 'text-warn'
    : 'text-crit'

  return (
    <div className="flex items-center justify-between border-b border-line bg-surface/80 backdrop-blur px-6 py-3 sticky top-0 z-50">
      <div className="flex items-center gap-3">
        <div className="relative w-8 h-8 rounded-md bg-gradient-to-br from-signal to-signal2 flex items-center justify-center font-display font-bold text-void text-sm">
          N
        </div>
        <div>
          <div className="font-display font-semibold text-sm tracking-wide text-ink">NARAD</div>
          <div className="text-[10px] text-inkdim tracking-wider uppercase">Neural Agentic Real-time Advisor</div>
        </div>
      </div>

      <div className="hidden md:flex items-center gap-6 text-xs font-mono-nums text-inkdim">
        <div className="flex items-center gap-1.5">
          <Radio size={13} className={connected ? 'text-signal' : 'text-crit'} />
          <span className={connected ? 'text-signal' : 'text-crit'}>
            {connected ? 'LIVE' : 'RECONNECTING'}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-inkdim">CITY:</span>
          <span className="text-ink">{city.toUpperCase()}</span>
        </div>
        {healthScore !== undefined && (
          <div className="flex items-center gap-1.5">
            <span className="text-inkdim">HEALTH SCORE:</span>
            <span className={`font-semibold ${scoreColor}`}>{healthScore.toFixed(1)}</span>
          </div>
        )}
        <div className="text-ink">
          {time.toLocaleTimeString('en-IN', { hour12: false })} IST
        </div>
      </div>
    </div>
  )
}

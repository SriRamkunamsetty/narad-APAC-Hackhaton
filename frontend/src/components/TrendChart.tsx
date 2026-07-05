import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { TrendingUp } from 'lucide-react'
import type { PulseHistoryPoint } from '../types'

interface Props {
  history: PulseHistoryPoint[]
}

export default function TrendChart({ history }: Props) {
  const data = history.map(h => ({
    time: new Date(h.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false }),
    AQI: Math.round(h.aqi),
    Congestion: Math.round(h.congestion),
    Hospital: Math.round(h.hospital_load),
  }))

  return (
    <div className="bg-surface border border-line rounded-xl p-5">
      <h2 className="font-display text-sm font-semibold text-ink flex items-center gap-2 mb-4">
        <TrendingUp size={15} className="text-signal" />
        LIVE TRENDS
      </h2>
      {data.length < 2 ? (
        <div className="h-48 flex items-center justify-center text-inkdim text-sm">
          Collecting live data points...
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1C2530" vertical={false} />
            <XAxis dataKey="time" stroke="#5C6B7A" fontSize={10} tickLine={false} axisLine={false} />
            <YAxis stroke="#5C6B7A" fontSize={10} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={{ background: '#10161D', border: '1px solid #1C2530', borderRadius: 8, fontSize: 12 }}
              labelStyle={{ color: '#9AACBC' }}
            />
            <Line type="monotone" dataKey="AQI" stroke="#FFB020" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="Congestion" stroke="#00B8FF" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="Hospital" stroke="#FF3B5C" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
      <div className="flex items-center gap-4 mt-2 text-[11px]">
        <span className="flex items-center gap-1.5 text-inkdim"><span className="w-2 h-2 rounded-full bg-warn" />AQI</span>
        <span className="flex items-center gap-1.5 text-inkdim"><span className="w-2 h-2 rounded-full bg-signal2" />Traffic</span>
        <span className="flex items-center gap-1.5 text-inkdim"><span className="w-2 h-2 rounded-full bg-crit" />Hospital Load</span>
      </div>
    </div>
  )
}

import { Wind, Car, Activity, ShieldAlert, Zap, CloudRain } from 'lucide-react'
import type { CityPulse } from '../types'

interface Props { pulse: CityPulse | null }

type SourceKind = 'live' | 'manual' | 'simulated' | undefined

function SourceBadge({ source, extra }: { source: SourceKind; extra?: string }) {
  if (!source) return null
  const config = {
    live:      { label: '● Live',    cls: 'bg-signal/15 text-signal border-signal/30',   title: 'Fetched from a live external API right now' },
    manual:    { label: '✎ Manual',  cls: 'bg-signal2/15 text-signal2 border-signal2/30', title: extra || 'Self-reported by real staff on the ground — genuinely real data' },
    simulated: { label: '○ Sim',     cls: 'bg-muted/15 text-muted border-muted/30',        title: 'Realistic simulated data — no public real-time source exists for this' },
  }[source]

  return (
    <span
      title={config.title}
      className={`text-[9px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wider shrink-0 border ${config.cls}`}
    >
      {config.label}
    </span>
  )
}

function MetricCard({
  icon, label, value, unit, subtext, accent, barPct, source, sourceExtra
}: {
  icon: React.ReactNode; label: string; value: string | number; unit?: string
  subtext: string; accent: string; barPct?: number; source?: SourceKind; sourceExtra?: string
}) {
  return (
    <div className="bg-panel border border-line rounded-lg p-4 relative overflow-hidden group hover:border-signal/30 transition-colors">
      <div className="flex items-start justify-between mb-3 gap-1">
        <div className="flex items-center gap-2 text-inkdim text-xs uppercase tracking-wider font-medium">
          {icon}
          {label}
        </div>
        <SourceBadge source={source} extra={sourceExtra} />
      </div>
      <div className="flex items-baseline gap-1 mb-1">
        <span className="text-3xl font-display font-semibold text-ink font-mono-nums">{value}</span>
        {unit && <span className="text-sm text-inkdim">{unit}</span>}
      </div>
      <div className="text-xs text-inkdim">{subtext}</div>
      {barPct !== undefined && (
        <div className="mt-3 h-1 bg-line rounded-full overflow-hidden">
          <div className={`h-full rounded-full transition-all duration-700 ${accent}`}
               style={{ width: `${Math.min(100, barPct)}%` }} />
        </div>
      )}
    </div>
  )
}

export default function CityPulseGrid({ pulse }: Props) {
  if (!pulse) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="bg-panel border border-line rounded-lg p-4 h-28 animate-pulse" />
        ))}
      </div>
    )
  }

  const src = (pulse.data_sources || {}) as Record<string, SourceKind>
  const aqiAccent = pulse.aqi.aqi > 150 ? 'bg-crit' : pulse.aqi.aqi > 100 ? 'bg-warn' : 'bg-signal'
  const trafficAccent = pulse.traffic.congestion_level > 70 ? 'bg-crit' : pulse.traffic.congestion_level > 45 ? 'bg-warn' : 'bg-signal'
  const hospitalAccent = pulse.hospitals.capacity_percent > 85 ? 'bg-crit' : pulse.hospitals.capacity_percent > 65 ? 'bg-warn' : 'bg-signal'
  const safetyAccent = pulse.safety.active_incidents > 8 ? 'bg-crit' : pulse.safety.active_incidents > 4 ? 'bg-warn' : 'bg-signal'
  const gridAccent = pulse.economy.utility_load_percent > 85 ? 'bg-crit' : pulse.economy.utility_load_percent > 65 ? 'bg-warn' : 'bg-signal'

  const hospitalSourceExtra = pulse.hospitals.manual_reports_count > 0
    ? `${pulse.hospitals.manual_reports_count} hospital(s) self-reporting live (${pulse.hospitals.manual_coverage_pct}% of city coverage) — rest simulated`
    : undefined

  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <MetricCard
          icon={<CloudRain size={14} />} label="Weather"
          value={pulse.weather.temperature.toFixed(0)} unit="°C"
          subtext={pulse.weather.condition}
          accent="bg-signal2" source={src.weather}
        />
        <MetricCard
          icon={<Wind size={14} />} label="Air Quality"
          value={pulse.aqi.aqi} unit="AQI"
          subtext={pulse.aqi.status}
          accent={aqiAccent} barPct={(pulse.aqi.aqi / 300) * 100} source={src.aqi}
        />
        <MetricCard
          icon={<Car size={14} />} label="Traffic"
          value={pulse.traffic.congestion_level.toFixed(0)} unit="%"
          subtext={`${pulse.traffic.avg_speed_kmh.toFixed(0)} km/h avg`}
          accent={trafficAccent} barPct={pulse.traffic.congestion_level} source={src.traffic}
        />
        <MetricCard
          icon={<Activity size={14} />} label="Hospitals"
          value={pulse.hospitals.capacity_percent.toFixed(0)} unit="%"
          subtext={
            pulse.hospitals.manual_reports_count > 0
              ? `${pulse.hospitals.available_beds} beds free · ${pulse.hospitals.manual_reports_count} reporting live`
              : `${pulse.hospitals.available_beds} beds free`
          }
          accent={hospitalAccent} barPct={pulse.hospitals.capacity_percent}
          source={src.hospitals} sourceExtra={hospitalSourceExtra}
        />
        <MetricCard
          icon={<ShieldAlert size={14} />} label="Safety"
          value={pulse.safety.active_incidents} unit="active"
          subtext={`Alert: ${pulse.safety.alert_level}`}
          accent={safetyAccent} barPct={pulse.safety.active_incidents * 8} source={src.safety}
        />
        <MetricCard
          icon={<Zap size={14} />} label="Grid Load"
          value={pulse.economy.utility_load_percent.toFixed(0)} unit="%"
          subtext={`${pulse.economy.power_outages} outages`}
          accent={gridAccent} barPct={pulse.economy.utility_load_percent} source={src.economy}
        />
      </div>
      <p className="text-[10px] text-inkdim mt-2 px-1">
        <span className="text-signal">● Live</span> = real external API ·{' '}
        <span className="text-signal2">✎ Manual</span> = self-reported by real staff on the ground ·{' '}
        <span className="text-muted">○ Sim</span> = realistic simulation (no public real-time source exists yet)
      </p>
    </div>
  )
}

import { useState } from 'react'
import { Cpu, Zap, Play, Loader2, TrendingUp, TrendingDown } from 'lucide-react'
import { api } from '../utils/api'
import type { ScenarioOutcome } from '../types'

const PRESETS = [
  { name: 'Close NH-44 Highway (3hrs)', description: 'Emergency road closure for maintenance',
    parameters: { traffic_delta: 28, health_delta: 3, aqi_delta: 8, safety_delta: 2 } },
  { name: 'Odd-Even Vehicle Scheme', description: 'Restrict vehicles by odd/even plates during high AQI',
    parameters: { traffic_delta: -18, health_delta: -2, aqi_delta: -22, safety_delta: 0 } },
  { name: 'Festival Mass Gathering', description: 'Large public event — 200K+ attendees',
    parameters: { traffic_delta: 35, health_delta: 12, aqi_delta: 5, safety_delta: 15 } },
  { name: 'Monsoon Flood Warning', description: 'Heavy rainfall alert across low-lying zones',
    parameters: { traffic_delta: 22, health_delta: 8, aqi_delta: -15, safety_delta: 20 } },
]

export default function ScenarioSimulator() {
  const [selected, setSelected] = useState(0)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ScenarioOutcome | null>(null)
  const [scenarioCount, setScenarioCount] = useState(1000)

  const run = async () => {
    setLoading(true)
    try {
      const preset = PRESETS[selected]
      const outcome = await api.simulateScenario({
        name: preset.name,
        description: preset.description,
        parameters: preset.parameters,
        scenario_count: scenarioCount,
      })
      setResult(outcome)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const impactBar = (val: number, label: string) => {
    const isPositive = val >= 0
    return (
      <div className="flex items-center justify-between py-1.5">
        <span className="text-xs text-inkdim">{label}</span>
        <div className="flex items-center gap-1.5">
          {isPositive ? <TrendingUp size={12} className="text-signal" /> : <TrendingDown size={12} className="text-crit" />}
          <span className={`text-xs font-mono-nums font-medium ${isPositive ? 'text-signal' : 'text-crit'}`}>
            {isPositive ? '+' : ''}{val.toFixed(1)}%
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-surface border border-line rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="font-display text-sm font-semibold text-ink flex items-center gap-2">
            <Cpu size={15} className="text-signal2" />
            NVIDIA RAPIDS SCENARIO SIMULATOR
          </h2>
          <p className="text-[11px] text-inkdim mt-0.5">Monte Carlo what-if simulation · GPU-accelerated</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 mb-4">
        {PRESETS.map((p, i) => (
          <button
            key={i}
            onClick={() => { setSelected(i); setResult(null) }}
            className={`text-left p-2.5 rounded-lg border text-xs transition-colors ${
              selected === i
                ? 'border-signal2/50 bg-signal2/10 text-ink'
                : 'border-line bg-panel text-inkdim hover:border-line hover:text-ink'
            }`}
          >
            <div className="font-medium mb-0.5">{p.name}</div>
            <div className="text-[10px] opacity-70">{p.description}</div>
          </button>
        ))}
      </div>

      <div className="flex items-center gap-3 mb-4">
        <label className="text-xs text-inkdim shrink-0">Simulations:</label>
        <input
          type="range" min={100} max={2000} step={100}
          value={scenarioCount}
          onChange={(e) => setScenarioCount(Number(e.target.value))}
          className="flex-1 h-1 accent-signal2"
        />
        <span className="text-xs font-mono-nums text-ink w-16 text-right">{scenarioCount.toLocaleString()}</span>
      </div>

      <button
        onClick={run}
        disabled={loading}
        className="w-full py-2.5 rounded-lg bg-signal2/10 border border-signal2/40 text-signal2 text-sm font-medium hover:bg-signal2/20 transition-colors disabled:opacity-50 flex items-center justify-center gap-2 mb-4"
      >
        {loading ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
        {loading ? 'Running on GPU...' : 'Run Simulation'}
      </button>

      {result && (
        <div className="space-y-3 animate-in">
          <div className="bg-panel border border-signal2/20 rounded-lg p-3.5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] text-inkdim uppercase tracking-wider">Result</span>
              {result.rapids_speedup && (
                <span className="text-[11px] font-mono-nums font-bold text-signal2 flex items-center gap-1">
                  <Zap size={11} /> {result.rapids_speedup}x FASTER WITH RAPIDS
                </span>
              )}
            </div>
            <p className="text-sm text-ink font-medium mb-1">{result.recommendation}</p>
            <p className="text-[11px] text-inkdim">
              {result.outcomes.simulations_run.toLocaleString()} scenarios simulated in {result.processing_ms}ms ·
              {' '}{(result.confidence * 100).toFixed(0)}% confidence
            </p>
          </div>

          <div className="bg-panel border border-line rounded-lg p-3.5">
            <div className="text-[10px] text-inkdim uppercase tracking-wider mb-1">Projected Impact</div>
            {impactBar(result.traffic_impact, 'Traffic Flow')}
            {impactBar(result.health_impact, 'Healthcare Load')}
            {impactBar(result.environment_impact, 'Air Quality')}
            {impactBar(result.safety_impact, 'Public Safety')}
            {impactBar(result.economy_impact, 'Economic Activity')}
          </div>
        </div>
      )}
    </div>
  )
}

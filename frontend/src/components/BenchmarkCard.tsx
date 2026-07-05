import { useState } from 'react'
import { Zap, Loader2, BarChart3 } from 'lucide-react'
import { api } from '../utils/api'
import type { RAPIDSBenchmark } from '../types'

export default function BenchmarkCard() {
  const [loading, setLoading] = useState(false)
  const [bench, setBench] = useState<RAPIDSBenchmark | null>(null)
  const [size, setSize] = useState(100000)

  const run = async () => {
    setLoading(true)
    try {
      const result = await api.getBenchmark(size)
      setBench(result)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const maxTime = bench ? Math.max(bench.pandas_time_ms, bench.rapids_time_ms || 0) : 1

  return (
    <div className="bg-surface border border-line rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="font-display text-sm font-semibold text-ink flex items-center gap-2">
            <BarChart3 size={15} className="text-warn" />
            ACCELERATION BENCHMARK
          </h2>
          <p className="text-[11px] text-inkdim mt-0.5">Live pandas (CPU) vs RAPIDS (GPU) comparison</p>
        </div>
      </div>

      <div className="flex items-center gap-2 mb-4">
        {[50000, 100000, 500000, 1000000].map((s) => (
          <button
            key={s}
            onClick={() => setSize(s)}
            className={`text-[11px] px-2.5 py-1 rounded-md border font-mono-nums transition-colors ${
              size === s ? 'border-warn/40 bg-warn/10 text-warn' : 'border-line text-inkdim hover:text-ink'
            }`}
          >
            {s >= 1000000 ? `${s / 1000000}M` : `${s / 1000}K`}
          </button>
        ))}
      </div>

      <button
        onClick={run}
        disabled={loading}
        className="w-full py-2.5 rounded-lg bg-warn/10 border border-warn/40 text-warn text-sm font-medium hover:bg-warn/20 transition-colors disabled:opacity-50 flex items-center justify-center gap-2 mb-4"
      >
        {loading ? <Loader2 size={15} className="animate-spin" /> : <Zap size={15} />}
        {loading ? 'Benchmarking...' : `Run Benchmark on ${size.toLocaleString()} records`}
      </button>

      {bench && (
        <div className="space-y-3 animate-in">
          <div className="space-y-2">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-inkdim">Pandas (CPU)</span>
                <span className="font-mono-nums text-ink">{bench.pandas_time_ms.toFixed(1)}ms</span>
              </div>
              <div className="h-2.5 bg-line rounded-full overflow-hidden">
                <div className="h-full bg-muted rounded-full" style={{ width: '100%' }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-inkdim">RAPIDS (GPU)</span>
                <span className="font-mono-nums text-signal2">{bench.rapids_time_ms?.toFixed(1)}ms</span>
              </div>
              <div className="h-2.5 bg-line rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-signal2 to-signal rounded-full transition-all duration-1000"
                  style={{ width: `${Math.max(2, ((bench.rapids_time_ms || 0) / maxTime) * 100)}%` }}
                />
              </div>
            </div>
          </div>

          <div className="bg-panel border border-signal2/20 rounded-lg p-3 text-center">
            <div className="text-2xl font-display font-bold text-signal2 font-mono-nums">
              {bench.speedup}x
            </div>
            <div className="text-[11px] text-inkdim">faster with GPU acceleration</div>
          </div>

          <p className="text-[11px] text-inkdim leading-relaxed">{bench.notes}</p>

          {!bench.using_gpu && (
            <div className="text-[10px] text-warn/80 bg-warn/5 border border-warn/20 rounded p-2">
              ⚠️ Running in CPU-simulation mode. Deploy on a Cloud Run GPU instance (nvidia-l4) with cuDF installed for real RAPIDS acceleration.
            </div>
          )}
        </div>
      )}
    </div>
  )
}

import { useEffect, useState } from 'react'
import StatusBar from './components/StatusBar'
import CityPulseGrid from './components/CityPulseGrid'
import AgentParliament from './components/AgentParliament'
import ScenarioSimulator from './components/ScenarioSimulator'
import BenchmarkCard from './components/BenchmarkCard'
import TrendChart from './components/TrendChart'
import AlertsFeed from './components/AlertsFeed'
import HospitalReportForm from './components/HospitalReportForm'
import { useNaradSocket } from './hooks/useNaradSocket'
import { api } from './utils/api'
import type { PulseHistoryPoint } from './types'

export default function App() {
  const { connected, cityPulse, decision, alerts, parliamentRunning, triggerParliament } = useNaradSocket()
  const [history, setHistory] = useState<PulseHistoryPoint[]>([])

  useEffect(() => {
    const poll = async () => {
      try {
        const { history } = await api.getPulseHistory()
        setHistory(history)
      } catch (e) { /* ignore */ }
    }
    poll()
    const t = setInterval(poll, 15000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="min-h-screen bg-void bg-grid">
      <StatusBar
        connected={connected}
        city={cityPulse?.city || 'Hyderabad'}
        healthScore={cityPulse?.overall_health_score}
      />

      <main className="max-w-[1400px] mx-auto px-6 py-6 space-y-5">
        {cityPulse?.alerts && cityPulse.alerts.length > 0 || alerts.length > 0 ? (
          <AlertsFeed alerts={alerts} cityAlerts={cityPulse?.alerts || []} />
        ) : null}

        <CityPulseGrid pulse={cityPulse} />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2 space-y-5">
            <AgentParliament
              decision={decision}
              running={parliamentRunning}
              onTrigger={() => triggerParliament('Manual trigger from dashboard')}
            />
            <TrendChart history={history} />
          </div>
          <div className="space-y-5">
            <ScenarioSimulator />
            <HospitalReportForm />
            <BenchmarkCard />
          </div>
        </div>

        <footer className="text-center text-[11px] text-inkdim py-6 border-t border-line">
          NARAD — Neural Agentic Real-time Advisor for Decisions · Built for Google Cloud × NVIDIA Hackathon 2026
          <br />
          5 ADK Agents · Gemini 2.0 Flash · NVIDIA RAPIDS · Cloud Run · Real-time WebSocket Intelligence
        </footer>
      </main>
    </div>
  )
}

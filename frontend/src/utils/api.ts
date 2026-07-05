import type { ScenarioOutcome, RAPIDSBenchmark, PulseHistoryPoint, ParliamentDecision, ManualHospitalReport } from '../types'

const BASE = (import.meta.env.VITE_API_URL as string) || ''

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`)
  return res.json()
}

export const api = {
  getCityPulse: () => req<any>('/api/city-pulse'),
  getPulseHistory: () => req<{ history: PulseHistoryPoint[] }>('/api/city-pulse/history'),
  getLatestDecision: () => req<ParliamentDecision>('/api/parliament/latest'),
  getDecisionHistory: () => req<{ decisions: ParliamentDecision[] }>('/api/parliament/history'),
  triggerParliament: (reason: string) =>
    req<{ status: string }>(`/api/parliament/trigger?reason=${encodeURIComponent(reason)}`, { method: 'POST' }),
  simulateScenario: (body: { name: string; description: string; parameters: Record<string, number>; scenario_count?: number }) =>
    req<ScenarioOutcome>('/api/scenario/simulate', { method: 'POST', body: JSON.stringify(body) }),
  getBenchmark: (size = 100000) => req<RAPIDSBenchmark>(`/api/benchmark?size=${size}`),
  getStats: () => req<any>('/api/stats'),
  getHealth: () => req<any>('/api/health'),
  submitHospitalReport: (report: Omit<ManualHospitalReport, 'reported_at'>) =>
    req<{ status: string; hospital_name: string; reported_at: string }>('/api/manual-data/hospital', {
      method: 'POST', body: JSON.stringify(report),
    }),
  listHospitalReports: (freshOnly = true) =>
    req<{ reports: ManualHospitalReport[]; freshness_window_minutes: number }>(
      `/api/manual-data/hospital?fresh_only=${freshOnly}`
    ),
  deleteHospitalReport: (hospitalName: string) =>
    req<{ status: string; hospital_name: string }>(
      `/api/manual-data/hospital/${encodeURIComponent(hospitalName)}`, { method: 'DELETE' }
    ),
}

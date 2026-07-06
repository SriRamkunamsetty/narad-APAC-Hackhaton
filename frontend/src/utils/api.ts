import type { ScenarioOutcome, RAPIDSBenchmark, PulseHistoryPoint, ParliamentDecision, ManualHospitalReport } from '../types'

const BASE = (import.meta.env.VITE_API_URL as string) || ''

async function req<T>(path: string, options?: RequestInit, accessKey?: string): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (accessKey) headers['X-API-Key'] = accessKey
  const res = await fetch(`${BASE}${path}`, { headers, ...options })
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`)
  return res.json()
}

export const api = {
  getCityPulse: () => req<any>('/api/city-pulse'),
  getPulseHistory: () => req<{ history: PulseHistoryPoint[] }>('/api/city-pulse/history'),
  getLatestDecision: () => req<ParliamentDecision>('/api/parliament/latest'),
  getDecisionHistory: () => req<{ decisions: ParliamentDecision[] }>('/api/parliament/history'),
  // Requires an access key — this triggers 5 Gemini calls, gated to prevent cost/abuse
  triggerParliament: (reason: string, accessKey: string) =>
    req<{ status: string }>(`/api/parliament/trigger?reason=${encodeURIComponent(reason)}`, { method: 'POST' }, accessKey),
  simulateScenario: (body: { name: string; description: string; parameters: Record<string, number>; scenario_count?: number }) =>
    req<ScenarioOutcome>('/api/scenario/simulate', { method: 'POST', body: JSON.stringify(body) }),
  getBenchmark: (size = 100000) => req<RAPIDSBenchmark>(`/api/benchmark?size=${size}`),
  getStats: () => req<any>('/api/stats'),
  getHealth: () => req<any>('/api/health'),
  // Requires an access key — this writes data other officials/agents rely on
  submitHospitalReport: (report: Omit<ManualHospitalReport, 'reported_at'>, accessKey: string) =>
    req<{ status: string; hospital_name: string; reported_at: string }>('/api/manual-data/hospital', {
      method: 'POST', body: JSON.stringify(report),
    }, accessKey),
  listHospitalReports: (freshOnly = true) =>
    req<{ reports: ManualHospitalReport[]; freshness_window_minutes: number }>(
      `/api/manual-data/hospital?fresh_only=${freshOnly}`
    ),
  // Requires an access key
  deleteHospitalReport: (hospitalName: string, accessKey: string) =>
    req<{ status: string; hospital_name: string }>(
      `/api/manual-data/hospital/${encodeURIComponent(hospitalName)}`, { method: 'DELETE' }, accessKey
    ),
  askNarad: (question: string, language: 'english' | 'hindi' | 'telugu' = 'english') =>
    req<{ answer: string; sources_used: string[]; language: string; error?: string }>('/api/ask', {
      method: 'POST', body: JSON.stringify({ question, language }),
    }),
}

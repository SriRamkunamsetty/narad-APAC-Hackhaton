export interface WeatherData {
  temperature: number
  humidity: number
  wind_speed: number
  wind_direction: string
  condition: string
  feels_like: number
  visibility: number
  pressure: number
}

export interface AQIData {
  aqi: number
  status: string
  pm25: number
  pm10: number
  no2: number
  o3: number
  co: number
  so2: number
  color: string
}

export interface TrafficData {
  congestion_level: number
  avg_speed_kmh: number
  incidents: number
  affected_zones: string[]
  travel_time_index: number
  hotspots: { zone: string; severity: number; lat: number; lng: number }[]
}

export interface HospitalData {
  total_hospitals: number
  available_beds: number
  icu_available: number
  ambulances_active: number
  emergency_wait_minutes: number
  capacity_percent: number
  critical_facilities: string[]
  manual_reports_count: number
  manual_coverage_pct: number
}

export interface ManualHospitalReport {
  hospital_name: string
  available_beds: number
  icu_available: number
  ambulances_active: number
  emergency_wait_minutes: number
  reported_by?: string | null
  reported_at: string
}

export interface SafetyData {
  active_incidents: number
  emergency_calls_1h: number
  police_response_minutes: number
  fire_units_deployed: number
  high_risk_zones: string[]
  alert_level: string
}

export interface EconomyData {
  fuel_price_litre: number
  essential_goods_index: number
  market_activity: string
  utility_load_percent: number
  water_supply_status: string
  power_outages: number
}

export interface CityPulse {
  city: string
  timestamp: string
  weather: WeatherData
  aqi: AQIData
  traffic: TrafficData
  hospitals: HospitalData
  safety: SafetyData
  economy: EconomyData
  overall_health_score: number
  alerts: string[]
  data_sources: Record<string, 'live' | 'simulated'>
}

export type VoteDecision = 'approve' | 'reject' | 'abstain' | 'escalate'
export type Severity = 'low' | 'moderate' | 'high' | 'critical'

export interface AgentStance {
  agent: string
  emoji: string
  analysis: string
  recommendation: string
  confidence: number
  vote: VoteDecision
  urgency: Severity
  key_metrics: Record<string, any>
  dissent_reason?: string | null
}

export interface ParliamentDecision {
  session_id: string
  timestamp: string
  trigger: string
  city: string
  stances: AgentStance[]
  consensus: string
  action_plan: string[]
  overall_urgency: Severity
  confidence_score: number
  dissent_log: string[]
  causal_chain: string[]
  affected_zones: string[]
  estimated_impact: string
  processing_time_ms: number
}

export interface ScenarioOutcome {
  scenario_id: string
  name: string
  description: string
  parameters: Record<string, any>
  outcomes: Record<string, any>
  traffic_impact: number
  health_impact: number
  economy_impact: number
  safety_impact: number
  environment_impact: number
  recommendation: string
  confidence: number
  processing_ms: number
  rapids_speedup?: number | null
}

export interface RAPIDSBenchmark {
  operation: string
  dataset_size: number
  pandas_time_ms: number
  rapids_time_ms?: number | null
  speedup?: number | null
  using_gpu: boolean
  notes: string
}

export interface WSMessage {
  type: 'city_pulse' | 'agent_speaking' | 'parliament_start' | 'parliament_end' |
        'alert' | 'benchmark' | 'data_update' | 'error'
  payload: any
  timestamp: string
}

export interface PulseHistoryPoint {
  timestamp: string
  aqi: number
  congestion: number
  hospital_load: number
  incidents: number
}

import { useState, useEffect, useCallback } from 'react'
import { ClipboardPlus, Loader2, CheckCircle2, X, Users, KeyRound } from 'lucide-react'
import { api } from '../utils/api'
import { useAccessKey } from '../hooks/useAccessKey'
import type { ManualHospitalReport } from '../types'

const KNOWN_HOSPITALS = [
  'NIMS', 'Osmania General Hospital', 'Gandhi Hospital', 'KIMS',
  'Yashoda Hospitals', 'Continental Hospitals', 'Apollo Hospitals', 'Other',
]

export default function HospitalReportForm() {
  const [accessKey, setAccessKey] = useAccessKey()
  const [hospitalName, setHospitalName] = useState(KNOWN_HOSPITALS[0])
  const [customName, setCustomName] = useState('')
  const [beds, setBeds] = useState(20)
  const [icu, setIcu] = useState(2)
  const [ambulances, setAmbulances] = useState(3)
  const [waitMin, setWaitMin] = useState(15)
  const [reportedBy, setReportedBy] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [justSubmitted, setJustSubmitted] = useState(false)
  const [error, setError] = useState('')
  const [reports, setReports] = useState<ManualHospitalReport[]>([])

  const loadReports = useCallback(async () => {
    try {
      const { reports } = await api.listHospitalReports(true)
      setReports(reports)
    } catch (e) { /* ignore */ }
  }, [])

  useEffect(() => {
    loadReports()
    const t = setInterval(loadReports, 20000)
    return () => clearInterval(t)
  }, [loadReports])

  const submit = async () => {
    const name = hospitalName === 'Other' ? customName.trim() : hospitalName
    if (!name) return
    if (!accessKey.trim()) { setError('Access key required — ask your NARAD administrator for one'); return }
    setError('')
    setSubmitting(true)
    try {
      await api.submitHospitalReport({
        hospital_name: name,
        available_beds: beds,
        icu_available: icu,
        ambulances_active: ambulances,
        emergency_wait_minutes: waitMin,
        reported_by: reportedBy.trim() || null,
      }, accessKey.trim())
      setJustSubmitted(true)
      setTimeout(() => setJustSubmitted(false), 3000)
      await loadReports()
    } catch (e: any) {
      setError(e?.message?.includes('401') ? 'Access key rejected — check with your administrator' : 'Submission failed — please try again')
    } finally {
      setSubmitting(false)
    }
  }

  const withdraw = async (name: string) => {
    if (!accessKey.trim()) { setError('Access key required to withdraw a report'); return }
    try {
      await api.deleteHospitalReport(name, accessKey.trim())
      await loadReports()
    } catch (e) {
      setError('Could not withdraw report — check your access key')
    }
  }

  return (
    <div className="bg-surface border border-line rounded-xl p-5">
      <div className="mb-4">
        <h2 className="font-display text-sm font-semibold text-ink flex items-center gap-2">
          <ClipboardPlus size={15} className="text-signal2" />
          HOSPITAL STATUS REPORTING
        </h2>
        <p className="text-[11px] text-inkdim mt-0.5">
          No public HMIS API exists — hospitals self-report directly, becoming real data instantly
        </p>
      </div>

      <div className="mb-3">
        <label className="text-[10px] text-inkdim uppercase tracking-wider block mb-1 flex items-center gap-1.5">
          <KeyRound size={10} /> Access Key
        </label>
        <input
          type="password"
          placeholder="Provided by your NARAD administrator"
          value={accessKey}
          onChange={(e) => setAccessKey(e.target.value)}
          className="w-full bg-panel border border-line rounded-md px-2.5 py-1.5 text-xs text-ink focus:outline-none focus:border-signal2/50"
        />
        <p className="text-[10px] text-inkdim mt-1">
          Kept only in this browser tab's session — never stored permanently, never part of the app's code.
        </p>
      </div>

      <div className="space-y-2.5 mb-3">
        <div>
          <label className="text-[10px] text-inkdim uppercase tracking-wider block mb-1">Hospital</label>
          <select
            value={hospitalName}
            onChange={(e) => setHospitalName(e.target.value)}
            className="w-full bg-panel border border-line rounded-md px-2.5 py-1.5 text-xs text-ink focus:outline-none focus:border-signal2/50"
          >
            {KNOWN_HOSPITALS.map(h => <option key={h} value={h}>{h}</option>)}
          </select>
          {hospitalName === 'Other' && (
            <input
              type="text" placeholder="Hospital name"
              value={customName} onChange={(e) => setCustomName(e.target.value)}
              className="w-full mt-1.5 bg-panel border border-line rounded-md px-2.5 py-1.5 text-xs text-ink focus:outline-none focus:border-signal2/50"
            />
          )}
        </div>

        <div className="grid grid-cols-2 gap-2.5">
          <div>
            <label className="text-[10px] text-inkdim uppercase tracking-wider block mb-1">Beds Available</label>
            <input type="number" min={0} value={beds} onChange={(e) => setBeds(Number(e.target.value))}
                   className="w-full bg-panel border border-line rounded-md px-2.5 py-1.5 text-xs text-ink font-mono-nums focus:outline-none focus:border-signal2/50" />
          </div>
          <div>
            <label className="text-[10px] text-inkdim uppercase tracking-wider block mb-1">ICU Beds</label>
            <input type="number" min={0} value={icu} onChange={(e) => setIcu(Number(e.target.value))}
                   className="w-full bg-panel border border-line rounded-md px-2.5 py-1.5 text-xs text-ink font-mono-nums focus:outline-none focus:border-signal2/50" />
          </div>
          <div>
            <label className="text-[10px] text-inkdim uppercase tracking-wider block mb-1">Ambulances Active</label>
            <input type="number" min={0} value={ambulances} onChange={(e) => setAmbulances(Number(e.target.value))}
                   className="w-full bg-panel border border-line rounded-md px-2.5 py-1.5 text-xs text-ink font-mono-nums focus:outline-none focus:border-signal2/50" />
          </div>
          <div>
            <label className="text-[10px] text-inkdim uppercase tracking-wider block mb-1">ER Wait (min)</label>
            <input type="number" min={0} value={waitMin} onChange={(e) => setWaitMin(Number(e.target.value))}
                   className="w-full bg-panel border border-line rounded-md px-2.5 py-1.5 text-xs text-ink font-mono-nums focus:outline-none focus:border-signal2/50" />
          </div>
        </div>

        <div>
          <label className="text-[10px] text-inkdim uppercase tracking-wider block mb-1">Reported By</label>
          <input type="text" placeholder="e.g. Duty Officer, Night Shift"
                 value={reportedBy} onChange={(e) => setReportedBy(e.target.value)}
                 className="w-full bg-panel border border-line rounded-md px-2.5 py-1.5 text-xs text-ink focus:outline-none focus:border-signal2/50" />
        </div>
      </div>

      {error && (
        <div className="text-[11px] text-crit bg-crit/5 border border-crit/20 rounded-md px-3 py-2 mb-3">
          {error}
        </div>
      )}

      <button
        onClick={submit}
        disabled={submitting || (hospitalName === 'Other' && !customName.trim())}
        className="w-full py-2.5 rounded-lg bg-signal2/10 border border-signal2/40 text-signal2 text-sm font-medium hover:bg-signal2/20 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
      >
        {submitting ? <Loader2 size={15} className="animate-spin" /> : justSubmitted ? <CheckCircle2 size={15} /> : <ClipboardPlus size={15} />}
        {submitting ? 'Submitting...' : justSubmitted ? 'Submitted — now live' : 'Submit Status Report'}
      </button>

      {reports.length > 0 && (
        <div className="mt-4 pt-4 border-t border-line">
          <div className="text-[10px] text-inkdim uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <Users size={11} /> Currently Self-Reporting ({reports.length})
          </div>
          <div className="space-y-1.5">
            {reports.map((r) => (
              <div key={r.hospital_name} className="flex items-center justify-between bg-panel border border-line rounded-md px-2.5 py-1.5">
                <div className="text-xs text-ink">
                  <span className="font-medium">{r.hospital_name}</span>
                  <span className="text-inkdim ml-1.5">
                    {r.available_beds} beds · {r.icu_available} ICU
                  </span>
                </div>
                <button onClick={() => withdraw(r.hospital_name)} className="text-inkdim hover:text-crit transition-colors">
                  <X size={13} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

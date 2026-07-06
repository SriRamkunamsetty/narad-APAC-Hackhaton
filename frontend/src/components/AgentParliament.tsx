import { useState } from 'react'
import { ChevronDown, ChevronUp, GitBranch, AlertTriangle, CheckCircle2, XCircle, HelpCircle, ArrowUpCircle, Loader2 } from 'lucide-react'
import type { ParliamentDecision, AgentStance, VoteDecision } from '../types'

interface Props {
  decision: ParliamentDecision | null
  running: boolean
  onTrigger: () => void
  error?: string | null
  hasAccessKey?: boolean
}

const voteConfig: Record<VoteDecision, { icon: React.ReactNode; color: string; label: string }> = {
  approve:  { icon: <CheckCircle2 size={14} />, color: 'text-signal',  label: 'APPROVE' },
  reject:   { icon: <XCircle size={14} />,      color: 'text-crit',    label: 'REJECT' },
  abstain:  { icon: <HelpCircle size={14} />,   color: 'text-muted',   label: 'ABSTAIN' },
  escalate: { icon: <ArrowUpCircle size={14} />,color: 'text-warn',    label: 'ESCALATE' },
}

const urgencyColor: Record<string, string> = {
  low: 'text-signal border-signal/30 bg-signal/5',
  moderate: 'text-signal2 border-signal2/30 bg-signal2/5',
  high: 'text-warn border-warn/30 bg-warn/5',
  critical: 'text-crit border-crit/30 bg-crit/5',
}

function AgentCard({ stance }: { stance: AgentStance }) {
  const [expanded, setExpanded] = useState(false)
  const vote = voteConfig[stance.vote]

  return (
    <div className="bg-panel border border-line rounded-lg overflow-hidden animate-in">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3.5 hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl">{stance.emoji}</span>
          <div className="text-left">
            <div className="text-sm font-medium text-ink">{stance.agent.replace('Agent', '')}</div>
            <div className={`flex items-center gap-1 text-[11px] font-medium ${vote.color}`}>
              {vote.icon} {vote.label}
              <span className="text-inkdim ml-1">· {(stance.confidence * 100).toFixed(0)}% confidence</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium uppercase ${urgencyColor[stance.urgency]}`}>
            {stance.urgency}
          </span>
          {expanded ? <ChevronUp size={16} className="text-inkdim" /> : <ChevronDown size={16} className="text-inkdim" />}
        </div>
      </button>

      {expanded && (
        <div className="px-3.5 pb-3.5 pt-1 border-t border-line/60 space-y-2.5 animate-in">
          <div>
            <div className="text-[10px] text-inkdim uppercase tracking-wider mb-1">Analysis</div>
            <p className="text-xs text-inkdim leading-relaxed">{stance.analysis}</p>
          </div>
          <div>
            <div className="text-[10px] text-inkdim uppercase tracking-wider mb-1">Recommendation</div>
            <p className="text-xs text-ink leading-relaxed">{stance.recommendation}</p>
          </div>
          {stance.dissent_reason && (
            <div className="bg-warn/5 border border-warn/20 rounded p-2 flex gap-2">
              <AlertTriangle size={13} className="text-warn shrink-0 mt-0.5" />
              <p className="text-[11px] text-warn/90 leading-relaxed">{stance.dissent_reason}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function AgentParliament({ decision, running, onTrigger, error, hasAccessKey }: Props) {
  return (
    <div className="bg-surface border border-line rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="font-display text-sm font-semibold text-ink flex items-center gap-2">
            <GitBranch size={15} className="text-signal" />
            AGENT PARLIAMENT
          </h2>
          <p className="text-[11px] text-inkdim mt-0.5">5 autonomous ADK agents · independent analysis · transparent voting</p>
        </div>
        <div className="text-right">
          <button
            onClick={onTrigger}
            disabled={running}
            className="text-xs font-medium px-3.5 py-1.5 rounded-md bg-signal/10 border border-signal/30 text-signal hover:bg-signal/20 transition-colors disabled:opacity-50 flex items-center gap-1.5"
          >
            {running ? <Loader2 size={13} className="animate-spin" /> : <GitBranch size={13} />}
            {running ? 'Deliberating...' : 'Convene Session'}
          </button>
          {!hasAccessKey && (
            <p className="text-[10px] text-inkdim mt-1">Needs an access key — set one in Hospital Status Reporting</p>
          )}
        </div>
      </div>

      {error && (
        <div className="text-[11px] text-crit bg-crit/5 border border-crit/20 rounded-md px-3 py-2 mb-3">
          {error}
        </div>
      )}

      {!decision && !running && (
        <div className="text-center py-12 text-inkdim text-sm">
          Waiting for first parliament session to run...
        </div>
      )}

      {running && !decision && (
        <div className="text-center py-12">
          <Loader2 size={24} className="animate-spin text-signal mx-auto mb-3" />
          <p className="text-sm text-inkdim">5 agents analyzing live city data in parallel...</p>
        </div>
      )}

      {decision && (
        <div className="space-y-4">
          {/* Consensus banner */}
          <div className={`border rounded-lg p-3.5 ${urgencyColor[decision.overall_urgency]}`}>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] uppercase tracking-wider font-semibold opacity-80">
                Consensus · {decision.processing_time_ms.toFixed(0)}ms · confidence {(decision.confidence_score * 100).toFixed(0)}%
              </span>
              <span className="text-[10px] uppercase tracking-wider font-bold">{decision.overall_urgency}</span>
            </div>
            <p className="text-sm font-medium leading-snug">{decision.consensus}</p>
          </div>

          {/* Agent votes grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {decision.stances.map((s) => <AgentCard key={s.agent} stance={s} />)}
          </div>

          {/* Causal chain */}
          {decision.causal_chain.length > 0 && (
            <div className="bg-panel border border-line rounded-lg p-3.5">
              <div className="text-[10px] text-inkdim uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <GitBranch size={11} /> Causal Reasoning Chain
              </div>
              <div className="space-y-1.5">
                {decision.causal_chain.map((c, i) => (
                  <div key={i} className="text-xs text-inkdim leading-relaxed pl-3 border-l-2 border-signal2/30">
                    {c}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Dissent log */}
          <div className="bg-panel border border-line rounded-lg p-3.5">
            <div className="text-[10px] text-inkdim uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <AlertTriangle size={11} /> Dissent Log — Where Agents Disagreed
            </div>
            <div className="space-y-1.5">
              {decision.dissent_log.map((d, i) => (
                <div key={i} className="text-xs text-inkdim leading-relaxed">{d}</div>
              ))}
            </div>
          </div>

          {/* Action plan */}
          {decision.action_plan.length > 0 && (
            <div className="bg-panel border border-line rounded-lg p-3.5">
              <div className="text-[10px] text-inkdim uppercase tracking-wider mb-2">Prioritized Action Plan</div>
              <div className="space-y-1.5">
                {decision.action_plan.map((a, i) => (
                  <div key={i} className="text-xs text-ink flex gap-2">
                    <span className="text-signal font-mono-nums shrink-0">{String(i + 1).padStart(2, '0')}</span>
                    {a}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="text-[11px] text-inkdim text-center pt-1">
            Impact: {decision.estimated_impact}
          </div>
        </div>
      )}
    </div>
  )
}

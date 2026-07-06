import { useState, useRef, useEffect } from 'react'
import { MessageCircleQuestion, Send, Loader2, Languages } from 'lucide-react'
import { api } from '../utils/api'

interface QAPair {
  question: string
  answer: string
  sources: string[]
  language: string
}

const LANGUAGES = [
  { code: 'english', label: 'English' },
  { code: 'hindi', label: 'हिन्दी' },
  { code: 'telugu', label: 'తెలుగు' },
] as const

const SUGGESTIONS = [
  'What is the current air quality situation?',
  'Is it safe to travel through the city right now?',
  'What did the agent parliament just decide?',
]

export default function AskNarad() {
  const [language, setLanguage] = useState<'english' | 'hindi' | 'telugu'>('english')
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState<QAPair[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [history, loading])

  const ask = async (q?: string) => {
    const finalQuestion = (q ?? question).trim()
    if (!finalQuestion || loading) return
    setQuestion('')
    setLoading(true)
    try {
      const result = await api.askNarad(finalQuestion, language)
      setHistory(prev => [...prev, {
        question: finalQuestion, answer: result.answer,
        sources: result.sources_used, language: result.language,
      }])
    } catch (e) {
      setHistory(prev => [...prev, {
        question: finalQuestion, answer: 'Something went wrong reaching NARAD — please try again.',
        sources: [], language,
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-surface border border-line rounded-xl p-5 flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h2 className="font-display text-sm font-semibold text-ink flex items-center gap-2">
            <MessageCircleQuestion size={15} className="text-signal" />
            ASK NARAD
          </h2>
          <p className="text-[11px] text-inkdim mt-0.5">Natural language · grounded in live city data</p>
        </div>
        <div className="flex items-center gap-1 bg-panel border border-line rounded-md p-0.5">
          {LANGUAGES.map(l => (
            <button
              key={l.code}
              onClick={() => setLanguage(l.code)}
              className={`text-[10px] px-2 py-1 rounded transition-colors ${
                language === l.code ? 'bg-signal/15 text-signal' : 'text-inkdim hover:text-ink'
              }`}
            >
              {l.label}
            </button>
          ))}
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 min-h-[160px] max-h-[320px] overflow-y-auto space-y-3 mb-3 pr-1">
        {history.length === 0 && (
          <div className="space-y-2">
            <p className="text-xs text-inkdim mb-2">Try asking:</p>
            {SUGGESTIONS.map(s => (
              <button
                key={s}
                onClick={() => ask(s)}
                className="block w-full text-left text-xs text-inkdim bg-panel border border-line rounded-md px-3 py-2 hover:border-signal/30 hover:text-ink transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {history.map((qa, i) => (
          <div key={i} className="animate-in space-y-1.5">
            <div className="text-xs text-ink bg-panel border border-line rounded-lg rounded-tr-sm px-3 py-2 ml-6">
              {qa.question}
            </div>
            <div className="text-xs text-ink bg-signal/5 border border-signal/20 rounded-lg rounded-tl-sm px-3 py-2 mr-6">
              {qa.answer}
              {qa.sources.length > 0 && (
                <div className="text-[10px] text-inkdim mt-1.5 flex items-center gap-1">
                  Grounded in: {qa.sources.map(s => s.replace(/_/g, ' ')).join(', ')}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-2 text-xs text-inkdim mr-6">
            <Loader2 size={13} className="animate-spin" /> NARAD is thinking...
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && ask()}
          placeholder="Ask about traffic, air quality, hospitals..."
          className="flex-1 bg-panel border border-line rounded-md px-3 py-2 text-xs text-ink focus:outline-none focus:border-signal/50"
        />
        <button
          onClick={() => ask()}
          disabled={loading || !question.trim()}
          className="p-2 rounded-md bg-signal/10 border border-signal/40 text-signal hover:bg-signal/20 transition-colors disabled:opacity-40"
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  )
}

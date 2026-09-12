import { useState } from 'react'
import { askChat } from '../api/client'

interface Turn {
  question: string
  answer: string
}

export default function RecruiterChat({ sessionId, exampleA, exampleB }: { sessionId: string; exampleA: string; exampleB: string }) {
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState<Turn[]>([])
  const [loading, setLoading] = useState(false)

  async function handleAsk() {
    if (!question.trim()) return
    setLoading(true)
    try {
      const answer = await askChat(sessionId, question)
      setHistory((h) => [{ question, answer: answer.text }, ...h])
      setQuestion('')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-3 rounded-lg border border-slate-700 bg-slate-900 p-4">
      <h2 className="text-xl font-bold text-white">Recruiter Chat (bonus)</h2>
      <p className="text-xs text-slate-500">
        Ask e.g. "Why is &lt;candidate&gt; ranked above &lt;candidate&gt;?" or "Tell me about &lt;candidate&gt;" —
        answered deterministically from the computed ranking data, no LLM.
      </p>
      <div className="flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
          placeholder={`Why is ${exampleA} ranked above ${exampleB}?`}
          className="flex-1 rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
        />
        <button
          onClick={handleAsk}
          disabled={loading}
          className="rounded border border-slate-600 px-4 py-2 text-sm font-medium text-slate-200 hover:border-slate-400 disabled:opacity-40"
        >
          {loading ? 'Asking…' : 'ASK'}
        </button>
      </div>

      <div className="max-h-96 space-y-3 overflow-y-auto">
        {history.map((turn, i) => (
          <div key={i}>
            <p className="text-sm text-slate-200"><span className="font-semibold">You:</span> {turn.question}</p>
            <p className="whitespace-pre-wrap text-sm text-slate-400"><span className="font-semibold text-slate-300">Assistant:</span> {turn.answer}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

import { useState } from 'react'
import { compareCandidates } from '../api/client'
import type { Candidate, CompareResult } from '../types'

export default function ComparePanel({ sessionId, candidates }: { sessionId: string; candidates: Candidate[] }) {
  const [a, setA] = useState(candidates[0]?.identifier ?? '')
  const [b, setB] = useState(candidates[1]?.identifier ?? candidates[0]?.identifier ?? '')
  const [result, setResult] = useState<CompareResult | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleCompare() {
    setLoading(true)
    try {
      setResult(await compareCandidates(sessionId, a, b))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-3 rounded-lg border border-slate-700 bg-slate-900 p-4">
      <h2 className="text-xl font-bold text-white">Compare Candidates</h2>
      <div className="flex flex-wrap items-end gap-3">
        <select value={a} onChange={(e) => setA(e.target.value)} className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200">
          {candidates.map((c) => (
            <option key={c.rank} value={c.identifier}>{c.identifier} (#{c.rank})</option>
          ))}
        </select>
        <select value={b} onChange={(e) => setB(e.target.value)} className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200">
          {candidates.map((c) => (
            <option key={c.rank} value={c.identifier}>{c.identifier} (#{c.rank})</option>
          ))}
        </select>
        <button
          onClick={handleCompare}
          disabled={loading}
          className="rounded border border-slate-600 px-4 py-2 text-sm font-medium text-slate-200 hover:border-slate-400 disabled:opacity-40"
        >
          {loading ? 'Comparing…' : 'COMPARE'}
        </button>
      </div>

      {result && (
        <div className="space-y-3">
          <div className="rounded border border-sky-800 bg-sky-950/40 p-3 text-sm text-sky-300">{result.verdict}</div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-xs font-semibold uppercase text-slate-500">Where {result.a_identifier} is stronger</p>
              <ul className="mt-1 space-y-1 text-sm text-slate-200">
                {result.a_wins.length ? result.a_wins.map((w, i) => <li key={i}>- {w}</li>) : <li className="text-slate-500">Nothing</li>}
              </ul>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase text-slate-500">Where {result.b_identifier} is stronger</p>
              <ul className="mt-1 space-y-1 text-sm text-slate-200">
                {result.b_wins.length ? result.b_wins.map((w, i) => <li key={i}>- {w}</li>) : <li className="text-slate-500">Nothing</li>}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

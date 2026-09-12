import { useState } from 'react'
import { searchCandidates } from '../api/client'
import type { SearchResultItem } from '../types'

export default function RecruiterSearch({ sessionId }: { sessionId: string }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResultItem[] | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSearch() {
    if (!query.trim()) return
    setLoading(true)
    try {
      setResults(await searchCandidates(sessionId, query))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-3 rounded-lg border border-slate-700 bg-slate-900 p-4">
      <h2 className="text-xl font-bold text-white">Recruiter Search (bonus)</h2>
      <p className="text-xs text-slate-500">
        e.g. "Show me candidates with Python + SQL + machine learning" — filters/ranks the uploaded pool by skill
        coverage, deterministically extracted from your query. No LLM.
      </p>
      <div className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="Show me candidates with Python + SQL + machine learning"
          className="flex-1 rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          className="rounded border border-slate-600 px-4 py-2 text-sm font-medium text-slate-200 hover:border-slate-400 disabled:opacity-40"
        >
          {loading ? 'Searching…' : 'SEARCH'}
        </button>
      </div>

      {results !== null && (
        results.length === 0 ? (
          <p className="text-sm text-slate-500">No candidates matched any recognized skill in that query.</p>
        ) : (
          <div className="overflow-x-auto rounded border border-slate-800">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-800 text-slate-300">
                <tr>
                  <th className="px-3 py-2">Candidate</th>
                  <th className="px-3 py-2">Overall Rank</th>
                  <th className="px-3 py-2">Query Coverage</th>
                  <th className="px-3 py-2">Matched</th>
                  <th className="px-3 py-2">Missing</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r) => (
                  <tr key={r.identifier} className="border-t border-slate-800">
                    <td className="px-3 py-2 font-medium text-white">{r.identifier}</td>
                    <td className="px-3 py-2 text-slate-300">#{r.rank} ({r.final_score})</td>
                    <td className="px-3 py-2 text-slate-300">{Math.round(r.query_coverage * 100)}%</td>
                    <td className="px-3 py-2 text-emerald-400">{r.matched_query_skills.join(', ')}</td>
                    <td className="px-3 py-2 text-slate-500">{r.missing_query_skills.join(', ') || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  )
}

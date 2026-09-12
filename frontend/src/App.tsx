import { useState } from 'react'
import { runDemo, runShortlisting } from './api/client'
import CandidateDetail from './components/CandidateDetail'
import ComparePanel from './components/ComparePanel'
import JobInfoPanel from './components/JobInfoPanel'
import RankedTable from './components/RankedTable'
import RecruiterChat from './components/RecruiterChat'
import RecruiterSearch from './components/RecruiterSearch'
import RequirementMatrix from './components/RequirementMatrix'
import TopCandidates from './components/TopCandidates'
import UploadPanel from './components/UploadPanel'
import type { Candidate, RankResponse } from './types'

export default function App() {
  const [result, setResult] = useState<RankResponse | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleRun(jdFile: File, resumeFiles: File[], supportingDocs: File[]) {
    setLoading(true)
    setError(null)
    try {
      const res = await runShortlisting(jdFile, resumeFiles, supportingDocs)
      setResult(res)
      setSelectedId(res.candidates[0]?.identifier ?? null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong running shortlisting.')
    } finally {
      setLoading(false)
    }
  }

  async function handleDemo(which: 'curated' | 'stress_test') {
    setLoading(true)
    setError(null)
    try {
      const res = await runDemo(which)
      setResult(res)
      setSelectedId(res.candidates[0]?.identifier ?? null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong running the demo.')
    } finally {
      setLoading(false)
    }
  }

  function handleCandidateUpdated(updated: Candidate) {
    setResult((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        candidates: prev.candidates.map((c) => (c.identifier === updated.identifier ? updated : c)),
      }
    })
  }

  if (!result) {
    return <UploadPanel onRun={handleRun} onDemo={handleDemo} loading={loading} error={error} />
  }

  const selected = result.candidates.find((c) => c.identifier === selectedId) ?? result.candidates[0]

  return (
    <div className="mx-auto max-w-5xl space-y-8 p-6 pb-16">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Smart Shortlisting Engine</h1>
        <button
          onClick={() => setResult(null)}
          className="rounded border border-slate-700 px-3 py-1.5 text-sm text-slate-300 hover:border-slate-500"
        >
          ← New shortlisting run
        </button>
      </div>

      {result.failures.length > 0 && (
        <details className="rounded-lg border border-red-900 bg-red-950/30 p-3">
          <summary className="cursor-pointer text-sm text-red-300">
            ⚠ {result.failures.length} resume(s) could not be processed
          </summary>
          <ul className="mt-2 space-y-1 text-xs text-red-300">
            {result.failures.map((f, i) => (
              <li key={i}>{f.name}: {f.error}</li>
            ))}
          </ul>
        </details>
      )}

      {result.unassociated_documents.length > 0 && (
        <details className="rounded-lg border border-slate-700 bg-slate-900 p-3">
          <summary className="cursor-pointer text-sm text-slate-300">
            ℹ {result.unassociated_documents.length} supporting document(s) could not be matched to a candidate
          </summary>
          <ul className="mt-2 space-y-1 text-xs text-slate-400">
            {result.unassociated_documents.map((f, i) => (
              <li key={i}>{f.filename}: {f.error}</li>
            ))}
          </ul>
        </details>
      )}

      <JobInfoPanel job={result.job} duplicatesCollapsed={result.duplicate_groups_collapsed} />

      <section>
        <h2 className="mb-3 text-xl font-bold text-white">Ranked Candidates</h2>
        <RankedTable candidates={result.candidates} selectedId={selected?.identifier ?? null} onSelect={setSelectedId} />
      </section>

      <TopCandidates candidates={result.candidates} />

      {selected && (
        <CandidateDetail
          candidate={selected}
          sessionId={result.session_id}
          onCandidateUpdated={handleCandidateUpdated}
        />
      )}

      <RequirementMatrix data={result.requirement_matrix} />

      <ComparePanel sessionId={result.session_id} candidates={result.candidates} />

      <RecruiterSearch sessionId={result.session_id} />

      <RecruiterChat
        sessionId={result.session_id}
        exampleA={result.candidates[0]?.identifier ?? 'Candidate A'}
        exampleB={result.candidates[result.candidates.length - 1]?.identifier ?? 'Candidate B'}
      />
    </div>
  )
}

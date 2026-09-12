import type { Candidate } from '../types'
import VerificationBadge from './VerificationBadge'

export default function TopCandidates({ candidates }: { candidates: Candidate[] }) {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold text-white">Top 3 Candidates</h2>
      {candidates.slice(0, 3).map((c) => (
        <div key={c.rank} className="rounded-lg border border-slate-700 bg-slate-900 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-lg font-semibold text-white">
              #{c.rank} — {c.identifier} — Score {c.final_score}
            </h3>
            <VerificationBadge verification={c.verification} />
          </div>
          <p className="mt-1 text-sm text-slate-300">{c.why}</p>

          <div className="mt-3 grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-xs font-semibold uppercase text-slate-500">Matched Required</p>
              <p className="text-sm text-slate-200">{c.matched_required.join(', ') || 'None'}</p>
              <p className="mt-2 text-xs font-semibold uppercase text-slate-500">Matched Preferred</p>
              <p className="text-sm text-slate-200">{c.matched_preferred.join(', ') || 'None'}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase text-slate-500">Missing Required</p>
              <p className="text-sm text-slate-200">{c.missing_required.join(', ') || 'None — full coverage'}</p>
              <p className="mt-2 text-xs font-semibold uppercase text-slate-500">Score Breakdown</p>
              <p className="text-sm text-slate-200">
                {Object.entries(c.score_breakdown)
                  .map(([k, v]) => `${k}: ${v}%`)
                  .join(' · ')}
              </p>
            </div>
          </div>

          {(c.relevant_experience_snippet || c.relevant_project_snippet) && (
            <div className="mt-3">
              <p className="text-xs font-semibold uppercase text-slate-500">Relevant Experience / Projects</p>
              {c.relevant_experience_snippet && <p className="text-xs text-slate-400">{c.relevant_experience_snippet}</p>}
              {c.relevant_project_snippet && <p className="text-xs text-slate-400">{c.relevant_project_snippet}</p>}
            </div>
          )}

          {c.verification.flags.length > 0 && (
            <details className="mt-3 rounded border border-amber-900 bg-amber-950/30 p-2">
              <summary className="cursor-pointer text-sm font-medium text-amber-300">
                Verification flags ({c.verification.flags.length})
              </summary>
              <ul className="mt-2 space-y-1 text-xs text-amber-200">
                {c.verification.flags.map((f, i) => (
                  <li key={i}>{f.severity === 'info' ? 'ℹ️' : '⚠️'} {f.message}</li>
                ))}
              </ul>
            </details>
          )}
        </div>
      ))}
    </div>
  )
}

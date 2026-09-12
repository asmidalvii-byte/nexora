import { useState } from 'react'
import { markReviewed } from '../api/client'
import type { Candidate } from '../types'
import VerificationBadge from './VerificationBadge'

interface Props {
  candidate: Candidate
  sessionId: string
  onCandidateUpdated: (updated: Candidate) => void
}

const SEVERITY_ICON: Record<string, string> = { high: '⚠️', medium: '⚠️', info: 'ℹ️' }

export default function CandidateDetail({ candidate, sessionId, onCandidateUpdated }: Props) {
  const [pendingFlag, setPendingFlag] = useState<string | null>(null)

  async function handleMarkReviewed(flagMessage: string) {
    setPendingFlag(flagMessage)
    try {
      await markReviewed(sessionId, candidate.identifier, flagMessage)
      const updatedFlags = candidate.verification.flags.map((f) =>
        f.message === flagMessage ? { ...f, reviewed: true } : f,
      )
      onCandidateUpdated({ ...candidate, verification: { ...candidate.verification, flags: updatedFlags } })
    } finally {
      setPendingFlag(null)
    }
  }

  return (
    <div className="space-y-3 rounded-lg border border-slate-700 bg-slate-900 p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white">Candidate Detail: {candidate.identifier}</h2>
        <VerificationBadge verification={candidate.verification} />
      </div>
      <p className="text-sm text-slate-300">
        Rank: {candidate.rank} · Final Score: {candidate.final_score}
      </p>

      <div>
        <p className="text-xs font-semibold uppercase text-slate-500">Score Breakdown</p>
        <ul className="text-sm text-slate-200">
          {Object.entries(candidate.score_breakdown).map(([k, v]) => (
            <li key={k}>
              {k}: {v}%
            </li>
          ))}
        </ul>
      </div>

      <p className="text-sm text-slate-300">
        <span className="font-semibold">Matched required:</span> {candidate.matched_required.join(', ') || 'None'}
      </p>
      <p className="text-sm text-slate-300">
        <span className="font-semibold">Missing required:</span> {candidate.missing_required.join(', ') || 'None'}
      </p>
      <p className="text-sm text-slate-300">
        <span className="font-semibold">Matched preferred:</span> {candidate.matched_preferred.join(', ') || 'None'}
      </p>

      <div>
        <p className="text-xs font-semibold uppercase text-slate-500">Relevant experience (from resume)</p>
        <textarea
          readOnly
          value={candidate.relevant_experience_full || '(none detected)'}
          className="mt-1 h-24 w-full rounded border border-slate-700 bg-slate-950 p-2 text-xs text-slate-300"
        />
      </div>
      <div>
        <p className="text-xs font-semibold uppercase text-slate-500">Relevant projects (from resume)</p>
        <textarea
          readOnly
          value={candidate.relevant_projects_full || '(none detected)'}
          className="mt-1 h-24 w-full rounded border border-slate-700 bg-slate-950 p-2 text-xs text-slate-300"
        />
      </div>

      <div className="rounded border border-slate-700 bg-slate-950 p-3">
        <p className="text-sm font-semibold text-slate-200">
          Document & Claim Verification: {candidate.verification.status_label}
        </p>
        <p className="mt-1 text-xs text-slate-500">
          A secondary signal for human review — never a fraud score, never a factor in the ranking above. This
          system never claims a candidate lied or fabricated anything; it only flags things worth a second look.
        </p>

        {candidate.verification.flags.length > 0 ? (
          <ul className="mt-3 space-y-2">
            {candidate.verification.flags.map((f, i) => (
              <li key={i} className="flex items-start justify-between gap-3 rounded bg-slate-900 p-2">
                <span className={`text-sm ${f.severity === 'high' ? 'text-red-300' : f.severity === 'medium' ? 'text-amber-300' : 'text-slate-400'}`}>
                  {SEVERITY_ICON[f.severity]} {f.message}
                </span>
                {f.reviewed ? (
                  <span className="shrink-0 rounded bg-slate-800 px-2 py-1 text-xs text-slate-400">Reviewed by recruiter</span>
                ) : (
                  <button
                    onClick={() => handleMarkReviewed(f.message)}
                    disabled={pendingFlag === f.message}
                    className="shrink-0 rounded border border-slate-600 px-2 py-1 text-xs text-slate-300 hover:border-slate-400 disabled:opacity-40"
                  >
                    {pendingFlag === f.message ? 'Saving…' : 'Mark Reviewed'}
                  </button>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-emerald-400">
            ✅ No timeline overlaps, duplicate entries, unsupported skill claims, or document mismatches detected.
          </p>
        )}

        {candidate.verification.supporting_documents.length > 0 && (
          <div className="mt-4 space-y-2">
            <p className="text-xs font-semibold uppercase text-slate-500">Supporting Documents</p>
            {candidate.verification.supporting_documents.map((doc, i) => (
              <div key={i} className="rounded border border-slate-800 bg-slate-900 p-2 text-xs text-slate-300">
                <p className="font-medium text-slate-200">
                  {doc.filename} — {doc.document_type.replace('_', ' ')}
                </p>
                {doc.organization && <p>Organization: {doc.organization}</p>}
                {doc.role_or_degree && <p>Role/Degree: {doc.role_or_degree}</p>}
                {doc.credential_id && <p>Credential ID: {doc.credential_id}</p>}
              </div>
            ))}
          </div>
        )}
      </div>

      {candidate.duplicates.length > 0 && (
        <div className="rounded border border-sky-800 bg-sky-950/40 p-3 text-sm text-sky-300">
          🔁 Also submitted as: {candidate.duplicates.join(', ')} (collapsed as redundant records)
        </div>
      )}
    </div>
  )
}

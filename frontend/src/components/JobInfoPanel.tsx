import type { JobInfo } from '../types'

function titleCase(skill: string) {
  return skill.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export default function JobInfoPanel({ job, duplicatesCollapsed }: { job: JobInfo; duplicatesCollapsed: number }) {
  return (
    <div className="space-y-3">
      <h2 className="text-2xl font-bold text-white">Job: {job.job_title}</h2>
      <p className="text-sm text-slate-300">
        <span className="font-semibold">Required skills ({job.required_skills.length}):</span>{' '}
        {job.required_skills.map(titleCase).join(', ')}
      </p>
      {job.preferred_skills.length > 0 && (
        <p className="text-sm text-slate-300">
          <span className="font-semibold">Preferred skills ({job.preferred_skills.length}):</span>{' '}
          {job.preferred_skills.map(titleCase).join(', ')}
        </p>
      )}

      {duplicatesCollapsed > 0 && (
        <div className="rounded-lg border border-sky-800 bg-sky-950/40 p-3 text-sm text-sky-300">
          🔁 {duplicatesCollapsed} redundant submission group(s) collapsed — duplicate/near-identical resumes are
          shown once, under their best-scoring copy (see "Also submitted as" on the candidate row).
        </div>
      )}

      {job.bias_flags.length > 0 && (
        <details className="rounded-lg border border-slate-700 bg-slate-900 p-3">
          <summary className="cursor-pointer text-sm font-medium text-slate-200">
            🔎 Bonus: {job.bias_flags.length} potentially narrow phrasing flag(s) in this JD
          </summary>
          <p className="mt-2 text-xs text-slate-500">
            Rule-based flags for human review — not legal conclusions, and they never affect ranking.
          </p>
          <ul className="mt-2 space-y-1 text-sm text-slate-300">
            {job.bias_flags.map((f, i) => (
              <li key={i}>
                "<span className="font-semibold">{f.matched_text}</span>" — {f.note}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}

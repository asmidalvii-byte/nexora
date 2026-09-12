import { useMemo, useState } from 'react'
import type { MatrixCell, RequirementMatrixData } from '../types'

type SortKey = 'overall' | 'strong_count' | 'missing_count'
type CandidateFilter = 'all' | 'top10' | 'missing_must_have'
type RequirementFilter = 'all' | 'must_have' | 'preferred'

function cellClasses(status: string) {
  if (status === 'strong') return 'bg-emerald-900/50 text-emerald-300'
  if (status === 'partial') return 'bg-amber-900/50 text-amber-300'
  return 'bg-red-900/40 text-red-300'
}

export default function RequirementMatrix({ data }: { data: RequirementMatrixData }) {
  const [candidateFilter, setCandidateFilter] = useState<CandidateFilter>('all')
  const [requirementFilter, setRequirementFilter] = useState<RequirementFilter>('all')
  const [sortKey, setSortKey] = useState<SortKey>('overall')
  const [hoveredCell, setHoveredCell] = useState<{ rowId: string; requirement: string } | null>(null)

  const requirements = useMemo(
    () => data.requirements.filter((r) => requirementFilter === 'all' || r.importance === requirementFilter),
    [data.requirements, requirementFilter],
  )

  const rowsWithCounts = useMemo(
    () =>
      data.rows.map((row) => {
        const cellByReq = new Map(row.cells.map((c) => [c.requirement, c]))
        const visibleCells = requirements.map((r) => cellByReq.get(r.skill)!).filter(Boolean)
        const strongCount = visibleCells.filter((c) => c.status === 'strong').length
        const missingCount = visibleCells.filter((c) => c.status === 'missing').length
        const missingMustHave = visibleCells.some((c) => c.importance === 'must_have' && c.status === 'missing')
        return { row, visibleCells, strongCount, missingCount, missingMustHave }
      }),
    [data.rows, requirements],
  )

  const sorted = useMemo(() => {
    const arr = [...rowsWithCounts]
    arr.sort((a, b) => {
      if (sortKey === 'overall') return b.row.overall_coverage_score - a.row.overall_coverage_score
      if (sortKey === 'strong_count') return b.strongCount - a.strongCount
      return a.missingCount - b.missingCount
    })
    return arr
  }, [rowsWithCounts, sortKey])

  const filtered = useMemo(() => {
    let arr = sorted
    if (candidateFilter === 'top10') arr = arr.slice(0, 10)
    if (candidateFilter === 'missing_must_have') arr = arr.filter((r) => r.missingMustHave)
    return arr
  }, [sorted, candidateFilter])

  const hoveredEvidence: MatrixCell | null = hoveredCell
    ? filtered.find((r) => r.row.identifier === hoveredCell.rowId)?.visibleCells.find((c) => c.requirement === hoveredCell.requirement) ?? null
    : null

  return (
    <div className="space-y-3 rounded-lg border border-slate-700 bg-slate-900 p-4">
      <div>
        <h2 className="text-xl font-bold text-white">Requirement Coverage Matrix</h2>
        <p className="text-xs text-slate-500">
          Semantic, evidence-backed requirement evaluation — not simple keyword matching. Local sentence-embedding
          similarity + a curated related-technology table, never a generative model. Hover a cell for evidence.
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <select value={candidateFilter} onChange={(e) => setCandidateFilter(e.target.value as CandidateFilter)} className="rounded border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm text-slate-200">
          <option value="all">All candidates</option>
          <option value="top10">Top 10 by coverage</option>
          <option value="missing_must_have">Missing a must-have</option>
        </select>
        <select value={requirementFilter} onChange={(e) => setRequirementFilter(e.target.value as RequirementFilter)} className="rounded border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm text-slate-200">
          <option value="all">All requirements</option>
          <option value="must_have">Must-have only</option>
          <option value="preferred">Preferred only</option>
        </select>
        <select value={sortKey} onChange={(e) => setSortKey(e.target.value as SortKey)} className="rounded border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm text-slate-200">
          <option value="overall">Sort: Overall score</option>
          <option value="strong_count">Sort: # Strong matches</option>
          <option value="missing_count">Sort: # Missing (fewest first)</option>
        </select>
      </div>

      <div className="flex gap-4 text-xs text-slate-400">
        <span>🟢 Strong Match</span>
        <span>🟡 Partial Match</span>
        <span>🔴 Missing</span>
      </div>

      {hoveredEvidence && (
        <div className="rounded border border-slate-700 bg-slate-950 p-3 text-sm">
          <p className="font-semibold text-slate-100">
            {hoveredEvidence.emoji} {hoveredEvidence.display_name} — {hoveredEvidence.status} ({hoveredEvidence.confidence}% confidence)
          </p>
          <p className="mt-1 text-slate-300">{hoveredEvidence.reasoning}</p>
        </div>
      )}

      <div className="overflow-x-auto rounded border border-slate-800">
        <table className="border-collapse text-sm">
          <thead>
            <tr>
              <th className="sticky left-0 z-10 bg-slate-800 px-3 py-2 text-left text-slate-300">Candidate</th>
              {requirements.map((r) => (
                <th key={r.skill} className="whitespace-nowrap bg-slate-800 px-3 py-2 text-slate-300">
                  {r.display_name}
                  {r.importance === 'must_have' ? <span className="text-red-400"> *</span> : <span className="text-slate-500"> +</span>}
                </th>
              ))}
              <th className="sticky right-0 z-10 bg-slate-800 px-3 py-2 text-slate-300">Overall</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(({ row, visibleCells }, index) => (
              <tr key={`${row.identifier}-${index}`} className="border-t border-slate-800">
                <td className="sticky left-0 z-10 bg-slate-900 px-3 py-2 font-medium text-white">{row.identifier}</td>
                {visibleCells.map((cell) => (
                  <td
                    key={cell.requirement}
                    className={`cursor-default px-3 py-2 text-center transition ${cellClasses(cell.status)}`}
                    onMouseEnter={() => setHoveredCell({ rowId: row.identifier, requirement: cell.requirement })}
                    onMouseLeave={() => setHoveredCell(null)}
                  >
                    {cell.emoji}
                  </td>
                ))}
                <td className="sticky right-0 z-10 bg-slate-900 px-3 py-2 text-center font-semibold text-white">
                  {row.overall_coverage_score}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-600">* Must-have &nbsp;&nbsp; + Preferred</p>
    </div>
  )
}

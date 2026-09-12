import type { Candidate } from '../types'
import VerificationBadge from './VerificationBadge'

interface Props {
  candidates: Candidate[]
  selectedId: string | null
  onSelect: (identifier: string) => void
}

export default function RankedTable({ candidates, selectedId, onSelect }: Props) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-700">
      <table className="w-full min-w-[900px] text-left text-sm">
        <thead className="bg-slate-800 text-slate-300">
          <tr>
            {['Rank', 'Candidate', 'Score', 'Semantic', 'Required', 'Preferred', 'Status', 'Verification', ''].map(
              (h) => (
                <th key={h} className="px-3 py-2 font-medium">
                  {h}
                </th>
              ),
            )}
          </tr>
        </thead>
        <tbody>
          {candidates.map((c) => (
            <tr
              key={c.rank}
              onClick={() => onSelect(c.identifier)}
              className={`cursor-pointer border-t border-slate-800 hover:bg-slate-800/60 ${
                selectedId === c.identifier ? 'bg-slate-800' : ''
              }`}
            >
              <td className="px-3 py-2 text-slate-400">{c.rank}</td>
              <td className="px-3 py-2 font-medium text-white">
                {c.identifier}
                {c.duplicates.length > 0 && (
                  <div className="text-xs font-normal text-slate-500">
                    also submitted as: {c.duplicates.join(', ')}
                  </div>
                )}
              </td>
              <td className="px-3 py-2 text-white">{c.final_score}</td>
              <td className="px-3 py-2 text-slate-300">{c.score_breakdown['Semantic Match']}%</td>
              <td className="px-3 py-2 text-slate-300">{c.score_breakdown['Required Skill Coverage']}%</td>
              <td className="px-3 py-2 text-slate-300">{c.score_breakdown['Preferred Skill Coverage']}%</td>
              <td className="px-3 py-2 text-slate-300">{c.status}</td>
              <td className="px-3 py-2">
                <VerificationBadge verification={c.verification} />
              </td>
              <td className="px-3 py-2 text-slate-500">→</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

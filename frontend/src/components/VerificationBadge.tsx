import type { Verification } from '../types'

const STYLES: Record<string, string> = {
  clean: 'bg-emerald-900/60 text-emerald-300',
  review_recommended: 'bg-amber-900/60 text-amber-300',
  verification_required: 'bg-red-900/60 text-red-300',
}

export default function VerificationBadge({ verification }: { verification: Verification }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STYLES[verification.status]}`}
      title={verification.flags.length ? verification.flags.map((f) => f.message).join(' | ') : undefined}
    >
      {verification.status_label}
    </span>
  )
}

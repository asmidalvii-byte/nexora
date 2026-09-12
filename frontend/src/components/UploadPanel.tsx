import { useState } from 'react'

interface Props {
  onRun: (jdFile: File, resumeFiles: File[], supportingDocs: File[]) => void
  onDemo: (which: 'curated' | 'stress_test') => void
  loading: boolean
  error: string | null
}

export default function UploadPanel({ onRun, onDemo, loading, error }: Props) {
  const [jdFile, setJdFile] = useState<File | null>(null)
  const [resumeFiles, setResumeFiles] = useState<File[]>([])
  const [supportingDocs, setSupportingDocs] = useState<File[]>([])

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Smart Shortlisting Engine</h1>
        <p className="mt-2 text-sm text-slate-400">
          Ranks resumes against a job description using local, hybrid keyword + semantic
          matching — no LLM in the scoring loop, no API key, runs fully offline.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block rounded-lg border border-slate-700 bg-slate-900 p-4">
          <span className="text-sm font-medium text-slate-200">1. Job Description (PDF or DOCX)</span>
          <input
            type="file"
            accept=".pdf,.docx"
            className="mt-2 block w-full text-sm text-slate-300 file:mr-3 file:rounded file:border-0 file:bg-slate-700 file:px-3 file:py-1.5 file:text-slate-100"
            onChange={(e) => setJdFile(e.target.files?.[0] ?? null)}
          />
        </label>
        <label className="block rounded-lg border border-slate-700 bg-slate-900 p-4">
          <span className="text-sm font-medium text-slate-200">2. Resumes (PDF or DOCX, multiple)</span>
          <input
            type="file"
            accept=".pdf,.docx"
            multiple
            className="mt-2 block w-full text-sm text-slate-300 file:mr-3 file:rounded file:border-0 file:bg-slate-700 file:px-3 file:py-1.5 file:text-slate-100"
            onChange={(e) => setResumeFiles(Array.from(e.target.files ?? []))}
          />
        </label>
      </div>

      <label className="block rounded-lg border border-slate-700 bg-slate-900 p-4">
        <span className="text-sm font-medium text-slate-200">
          3. Supporting Documents (optional) — certificates, degrees, employment letters
        </span>
        <p className="mt-1 text-xs text-slate-500">
          PDF, PNG, or JPG. Each document is matched to a candidate by name and cross-checked against their resume
          — see "Document &amp; Claim Verification" per candidate after running.
        </p>
        <input
          type="file"
          accept=".pdf,.png,.jpg,.jpeg"
          multiple
          className="mt-2 block w-full text-sm text-slate-300 file:mr-3 file:rounded file:border-0 file:bg-slate-700 file:px-3 file:py-1.5 file:text-slate-100"
          onChange={(e) => setSupportingDocs(Array.from(e.target.files ?? []))}
        />
      </label>

      <button
        disabled={loading || !jdFile || resumeFiles.length === 0}
        onClick={() => jdFile && onRun(jdFile, resumeFiles, supportingDocs)}
        className="w-full rounded-lg bg-red-500 px-4 py-2.5 font-semibold text-white transition hover:bg-red-400 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {loading ? 'Running…' : 'RUN SHORTLISTING'}
      </button>

      <div className="flex items-center gap-3 text-xs text-slate-500">
        <div className="h-px flex-1 bg-slate-700" />
        or use bundled data
        <div className="h-px flex-1 bg-slate-700" />
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <button
          disabled={loading}
          onClick={() => onDemo('curated')}
          className="rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-slate-200 transition hover:border-slate-500 disabled:opacity-40"
        >
          Curated demo<br /><span className="text-xs text-slate-500">1 JD + 6 sample resumes</span>
        </button>
        <button
          disabled={loading}
          onClick={() => onDemo('stress_test')}
          className="rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-slate-200 transition hover:border-slate-500 disabled:opacity-40"
        >
          Stress test<br /><span className="text-xs text-slate-500">1 JD + 220 real resumes, ~25 roles</span>
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-950/50 p-3 text-sm text-red-300">{error}</div>
      )}
    </div>
  )
}

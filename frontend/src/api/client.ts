import axios from 'axios'
import type { Candidate, ChatAnswer, CompareResult, RankResponse, SearchResultItem } from '../types'

const API_BASE = 'http://localhost:8000'

const client = axios.create({ baseURL: API_BASE })

export async function runShortlisting(jdFile: File, resumeFiles: File[], supportingDocs: File[] = []): Promise<RankResponse> {
  const form = new FormData()
  form.append('jd_file', jdFile)
  resumeFiles.forEach((f) => form.append('resume_files', f))
  supportingDocs.forEach((f) => form.append('supporting_docs', f))
  const res = await client.post<RankResponse>('/api/rank', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function runDemo(which: 'curated' | 'stress_test'): Promise<RankResponse> {
  const res = await client.post<RankResponse>(`/api/demo/${which}`)
  return res.data
}

export async function compareCandidates(
  sessionId: string,
  candidateA: string,
  candidateB: string,
): Promise<CompareResult> {
  const res = await client.post<CompareResult>('/api/compare', {
    session_id: sessionId,
    candidate_a: candidateA,
    candidate_b: candidateB,
  })
  return res.data
}

export async function askChat(sessionId: string, question: string): Promise<ChatAnswer> {
  const res = await client.post<ChatAnswer>('/api/chat', { session_id: sessionId, question })
  return res.data
}

export async function searchCandidates(sessionId: string, query: string): Promise<SearchResultItem[]> {
  const res = await client.post<{ results: SearchResultItem[] }>('/api/search', {
    session_id: sessionId,
    query,
  })
  return res.data.results
}

export async function markReviewed(
  sessionId: string,
  candidateId: string,
  flagMessage: string,
  reviewer = 'Recruiter',
  resolution = '',
): Promise<void> {
  await client.post('/api/review', {
    session_id: sessionId,
    candidate_id: candidateId,
    flag_message: flagMessage,
    reviewer,
    resolution,
  })
}

export async function fetchCandidates(sessionId: string): Promise<Candidate[]> {
  const res = await client.get<{ candidates: Candidate[] }>(`/api/candidates/${sessionId}`)
  return res.data.candidates
}

export interface BiasFlag {
  matched_text: string
  note: string
}

export interface JobInfo {
  job_title: string
  required_skills: string[]
  preferred_skills: string[]
  bias_flags: BiasFlag[]
}

export interface VerificationFlagItem {
  severity: 'high' | 'medium' | 'info'
  message: string
  reviewed: boolean
}

export interface SupportingDocumentItem {
  filename: string
  document_type: string
  organization: string | null
  role_or_degree: string | null
  credential_id: string | null
  verification_url: string | null
  flags: VerificationFlagItem[]
}

export interface Verification {
  status: 'clean' | 'review_recommended' | 'verification_required'
  status_label: string
  flags: VerificationFlagItem[]
  supporting_documents: SupportingDocumentItem[]
}

export interface ScoreBreakdown {
  'Semantic Match': number
  'Required Skill Coverage': number
  'Experience/Project Relevance': number
  'Preferred Skill Coverage': number
  'ML Relevance': number
}

export interface Candidate {
  identifier: string
  rank: number
  final_score: number
  status: string
  score_breakdown: ScoreBreakdown
  matched_required: string[]
  missing_required: string[]
  matched_preferred: string[]
  why: string
  relevant_experience_snippet: string
  relevant_project_snippet: string
  relevant_experience_full: string
  relevant_projects_full: string
  all_resume_skills: string[]
  duplicates: string[]
  verification: Verification
}

export interface RankFailure {
  name: string
  error: string
}

export interface MatrixCell {
  requirement: string
  display_name: string
  importance: 'must_have' | 'preferred'
  status: 'strong' | 'partial' | 'missing'
  emoji: string
  score: number
  confidence: number
  evidence_text: string
  evidence_source: string
  reasoning: string
}

export interface MatrixRow {
  identifier: string
  overall_coverage_score: number
  cells: MatrixCell[]
}

export interface RequirementInfo {
  skill: string
  display_name: string
  importance: 'must_have' | 'preferred'
}

export interface RequirementMatrixData {
  requirements: RequirementInfo[]
  rows: MatrixRow[]
}

export interface RankResponse {
  session_id: string
  job: JobInfo
  candidates: Candidate[]
  failures: RankFailure[]
  duplicate_groups_collapsed: number
  unassociated_documents: { filename: string; error: string }[]
  requirement_matrix: RequirementMatrixData
}

export interface CompareResult {
  a_identifier: string
  b_identifier: string
  a_wins: string[]
  b_wins: string[]
  verdict: string
}

export interface ChatAnswer {
  text: string
  matched_candidates: string[]
}

export interface SearchResultItem {
  identifier: string
  rank: number
  final_score: number
  matched_query_skills: string[]
  missing_query_skills: string[]
  query_coverage: number
}

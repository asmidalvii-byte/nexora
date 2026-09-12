"""BONUS feature: free-text recruiter search over an already-ranked,
already-uploaded candidate pool — "Show me candidates with Python + SQL +
machine learning." Deterministic: extracts skills from the query using the
same skill dictionary as everywhere else, then filters/orders the existing
ranked candidates by coverage of the queried skills. No LLM, no new score —
this reuses each candidate's own resume-skill extraction, already computed
during ranking.
"""
from dataclasses import dataclass
from typing import List

from src.ranker import RankedCandidate
from src.skill_matcher import extract_skill_set


@dataclass
class SearchResult:
    candidate: RankedCandidate
    matched_query_skills: List[str]
    missing_query_skills: List[str]
    query_coverage: float  # fraction of queried skills this candidate has


def search_candidates(query: str, ranked: List[RankedCandidate]) -> List[SearchResult]:
    """Returns candidates that have at least one queried skill, ordered by
    how many of the queried skills they cover (desc), then by their
    existing overall rank (desc) as a tiebreaker — a search doesn't
    replace the JD-based ranking, it filters/reorders within it."""
    queried_skills = sorted(extract_skill_set(query))
    if not queried_skills:
        return []

    results = []
    for candidate in ranked:
        candidate_skills = candidate.features.keyword_result.all_resume_skills if candidate.features.keyword_result else []
        candidate_skill_set = set(candidate_skills)
        matched = [s for s in queried_skills if s in candidate_skill_set]
        if not matched:
            continue
        missing = [s for s in queried_skills if s not in candidate_skill_set]
        results.append(SearchResult(
            candidate=candidate,
            matched_query_skills=matched,
            missing_query_skills=missing,
            query_coverage=round(len(matched) / len(queried_skills), 4),
        ))

    results.sort(key=lambda r: (-r.query_coverage, r.candidate.rank))
    return results

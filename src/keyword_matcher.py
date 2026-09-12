"""Keyword / explicit-skill matching engine. Purely rule-based + TF-IDF —
no LLM, no ML — required skills are weighted far more heavily than
preferred ones per the hackathon's own emphasis on explicit skill matching."""
from dataclasses import dataclass, field
from typing import List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import KEYWORD_PREFERRED_WEIGHT, KEYWORD_REQUIRED_WEIGHT, KEYWORD_TFIDF_WEIGHT
from src.jd_parser import ParsedJD
from src.resume_parser import ParsedResume
from src.skill_matcher import all_canonical_skills, extract_skill_set


@dataclass
class KeywordMatchResult:
    matched_required: List[str] = field(default_factory=list)
    missing_required: List[str] = field(default_factory=list)
    matched_preferred: List[str] = field(default_factory=list)
    missing_preferred: List[str] = field(default_factory=list)
    required_coverage: float = 0.0
    preferred_coverage: float = 0.0
    tfidf_similarity: float = 0.0
    keyword_score: float = 0.0
    all_resume_skills: List[str] = field(default_factory=list)


def _tfidf_technical_similarity(jd_text: str, resume_text: str) -> float:
    """Cosine similarity restricted to a technical-term vocabulary (the
    full skill-alias list), so this isn't just generic prose overlap."""
    vocabulary = set()
    for skill in all_canonical_skills():
        vocabulary.add(skill.replace("_", " "))

    vectorizer = TfidfVectorizer(vocabulary=sorted(vocabulary))
    try:
        matrix = vectorizer.fit_transform([jd_text.lower(), resume_text.lower()])
    except ValueError:
        return 0.0
    if matrix.nnz == 0:
        return 0.0
    sim = cosine_similarity(matrix[0], matrix[1])[0][0]
    return float(max(0.0, min(1.0, sim)))


def match_keywords(jd: ParsedJD, resume: ParsedResume) -> KeywordMatchResult:
    resume_full_text = "\n".join(resume.sections.values()) or resume.raw_text
    resume_skills = extract_skill_set(resume_full_text)

    required = set(jd.required_skills)
    preferred = set(jd.preferred_skills)

    matched_required = sorted(required & resume_skills)
    missing_required = sorted(required - resume_skills)
    matched_preferred = sorted(preferred & resume_skills)
    missing_preferred = sorted(preferred - resume_skills)

    required_coverage = len(matched_required) / len(required) if required else 1.0
    preferred_coverage = len(matched_preferred) / len(preferred) if preferred else 1.0

    tfidf_sim = _tfidf_technical_similarity(jd.full_text, resume_full_text)

    keyword_score = (
        KEYWORD_REQUIRED_WEIGHT * required_coverage
        + KEYWORD_PREFERRED_WEIGHT * preferred_coverage
        + KEYWORD_TFIDF_WEIGHT * tfidf_sim
    )

    return KeywordMatchResult(
        matched_required=matched_required,
        missing_required=missing_required,
        matched_preferred=matched_preferred,
        missing_preferred=missing_preferred,
        required_coverage=round(required_coverage, 4),
        preferred_coverage=round(preferred_coverage, 4),
        tfidf_similarity=round(tfidf_sim, 4),
        keyword_score=round(keyword_score, 4),
        all_resume_skills=sorted(resume_skills),
    )

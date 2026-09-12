"""Assembles one flat feature vector per candidate from the keyword and
semantic engine outputs. This is the exact feature set the ML relevance
model is trained on — must stay in sync with training/generate_training_data.py."""
from dataclasses import dataclass

from src.jd_parser import ParsedJD
from src.keyword_matcher import KeywordMatchResult, match_keywords
from src.resume_parser import ParsedResume
from src.semantic_matcher import SemanticMatchResult, match_semantics

FEATURE_NAMES = [
    "semantic_overall",
    "semantic_experience",
    "semantic_projects",
    "semantic_skills_context",
    "semantic_education",
    "keyword_score",
    "required_skill_coverage",
    "preferred_skill_coverage",
    "tfidf_similarity",
    "skill_count",
    "required_skill_count",
    "matched_required_count",
    "missing_required_count",
    "experience_relevance",
    "project_relevance",
    "education_relevance",
]


@dataclass
class CandidateFeatures:
    values: dict
    keyword_result: KeywordMatchResult
    semantic_result: SemanticMatchResult

    def as_vector(self):
        return [self.values[name] for name in FEATURE_NAMES]


def build_features(jd: ParsedJD, resume: ParsedResume) -> CandidateFeatures:
    keyword_result = match_keywords(jd, resume)
    semantic_result = match_semantics(jd, resume)

    values = {
        "semantic_overall": semantic_result.semantic_overall,
        "semantic_experience": semantic_result.semantic_experience,
        "semantic_projects": semantic_result.semantic_projects,
        "semantic_skills_context": semantic_result.semantic_skills_context,
        "semantic_education": semantic_result.semantic_education,
        "keyword_score": keyword_result.keyword_score,
        "required_skill_coverage": keyword_result.required_coverage,
        "preferred_skill_coverage": keyword_result.preferred_coverage,
        "tfidf_similarity": keyword_result.tfidf_similarity,
        "skill_count": len(keyword_result.all_resume_skills),
        "required_skill_count": len(keyword_result.matched_required) + len(keyword_result.missing_required),
        "matched_required_count": len(keyword_result.matched_required),
        "missing_required_count": len(keyword_result.missing_required),
        "experience_relevance": semantic_result.semantic_experience,
        "project_relevance": semantic_result.semantic_projects,
        "education_relevance": semantic_result.semantic_education,
    }

    return CandidateFeatures(values=values, keyword_result=keyword_result, semantic_result=semantic_result)

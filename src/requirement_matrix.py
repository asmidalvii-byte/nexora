"""AI-Powered Requirement Coverage Matrix — per-candidate x per-requirement
evaluation with an evidence-backed explanation for every cell. "Semantic
AI evaluation" here means the same local sentence-embedding cosine
similarity used everywhere else in this project (src/semantic_matcher.py)
— never a generative LLM call, consistent with the whole system's no-LLM,
no-API-key design.

This is deliberately NOT a second scoring system: it reuses the exact
KeywordMatchResult already computed during ranking (src/keyword_matcher.py)
for the "does the resume mention this skill, and where" signal, and only
adds semantic/related-technology reasoning on top for skills that aren't
an exact keyword hit. The existing final_score/rank from src/scorer.py and
src/ranker.py remains the single source of truth for candidate ordering —
this matrix is a richer visual breakdown of the same underlying evidence,
not a competing score.
"""
from dataclasses import dataclass, field
from typing import Dict, List

from config import (
    REQUIREMENT_PARTIAL_THRESHOLD, REQUIREMENT_STRONG_THRESHOLD,
    REQUIREMENT_WEIGHT_PREFERRED, REQUIREMENT_WEIGHT_REQUIRED,
)
from src.jd_parser import ParsedJD
from src.keyword_matcher import KeywordMatchResult
from src.resume_parser import ParsedResume
from src.semantic_matcher import best_matching_chunk

# Curated, intentionally small adjacency table: a skill on the left gives
# PARTIAL (never full/strong) credit toward the skill(s) on the right,
# because the relationship is real but not equivalence. Kept short and
# reviewed by hand rather than learned, so every entry is individually
# defensible ("why does Kubernetes partially cover Docker?") instead of a
# black-box similarity threshold making the call.
_RELATED_SKILLS: Dict[str, List[str]] = {
    "react_native": ["react"],
    "express.js": ["node.js"],
    "nestjs": ["node.js"],
    "fastapi": ["rest_api", "python"],
    "flask": ["rest_api", "python"],
    "django": ["rest_api", "python"],
    "spring": ["rest_api", "java"],
    "kubernetes": ["docker"],
    "docker": ["microservices"],
    "postgresql": ["sql"],
    "mysql": ["sql"],
    "sqlite": ["sql"],
    "tensorflow": ["machine_learning", "deep_learning"],
    "pytorch": ["machine_learning", "deep_learning"],
    "scikit_learn": ["machine_learning"],
    "next.js": ["react"],
    "vue": ["javascript"],
    "angular": ["javascript", "typescript"],
}

_SEMANTIC_ONLY_THRESHOLD = 0.55  # below this, "no meaningful evidence" even semantically


def _display_name(skill: str) -> str:
    return skill.replace("_", " ").upper() if len(skill) <= 4 else skill.replace("_", " ").title()


@dataclass
class RequirementEvaluation:
    requirement: str
    display_name: str
    importance: str  # "must_have" or "preferred"
    weight: float
    status: str  # "strong" | "partial" | "missing"
    score: float  # 0-100
    confidence: float  # 0-100 (same scale/value as score here — see module docstring)
    evidence_text: str
    evidence_source: str  # "skills" | "experience" | "projects" | "education" | "related_skill" | "semantic" | ""
    reasoning: str


@dataclass
class CandidateMatrixRow:
    identifier: str
    evaluations: List[RequirementEvaluation] = field(default_factory=list)
    overall_coverage_score: float = 0.0


def _status_for_score(score: float) -> str:
    if score >= REQUIREMENT_STRONG_THRESHOLD:
        return "strong"
    if score >= REQUIREMENT_PARTIAL_THRESHOLD:
        return "partial"
    return "missing"


def _evaluate_one_requirement(
    requirement: str,
    importance: str,
    resume: ParsedResume,
    keyword_result: KeywordMatchResult,
) -> RequirementEvaluation:
    weight = REQUIREMENT_WEIGHT_REQUIRED if importance == "must_have" else REQUIREMENT_WEIGHT_PREFERRED
    display = _display_name(requirement)
    matched_set = set(keyword_result.matched_required) | set(keyword_result.matched_preferred)

    elsewhere_text = "\n".join([resume.section("experience"), resume.section("projects")])
    skills_text = resume.section("skills")

    if requirement in matched_set:
        # Find an evidence line: prefer experience/projects over the bare skills list.
        similarity, chunk = best_matching_chunk(display, elsewhere_text) if elsewhere_text.strip() else (0.0, "")
        has_elsewhere_evidence = similarity >= 0.35 and chunk.strip()
        if has_elsewhere_evidence:
            return RequirementEvaluation(
                requirement=requirement, display_name=display, importance=importance, weight=weight,
                status="strong", score=92.0, confidence=92.0,
                evidence_text=chunk.strip(), evidence_source="experience_or_projects",
                reasoning=f"Candidate demonstrates {display} in their experience/projects: \"{chunk.strip()}\"",
            )
        return RequirementEvaluation(
            requirement=requirement, display_name=display, importance=importance, weight=weight,
            status="partial", score=62.0, confidence=62.0,
            evidence_text=skills_text.strip()[:200], evidence_source="skills",
            reasoning=f"{display} is listed in the Skills section but no supporting project or experience "
                      f"evidence was found elsewhere in the resume.",
        )

    # Not an exact keyword hit — check curated related-technology credit
    # (the table is keyed by what the candidate HAS, mapping to what it
    # partially covers, so we scan for any resume skill whose adjacency
    # list includes this requirement).
    resume_skill_set = set(keyword_result.all_resume_skills)
    related_hit = None
    for candidate_skill, implies in _RELATED_SKILLS.items():
        if requirement in implies and candidate_skill in resume_skill_set:
            related_hit = candidate_skill
            break
    if related_hit:
        related_display = _display_name(related_hit)
        return RequirementEvaluation(
            requirement=requirement, display_name=display, importance=importance, weight=weight,
            status="partial", score=58.0, confidence=58.0,
            evidence_text=f"Candidate has evidence of {related_display}.", evidence_source="related_skill",
            reasoning=f"Candidate demonstrates {related_display}, which is related to {display} but not "
                      f"automatically equivalent — treated as partial evidence.",
        )

    # Last resort: pure semantic similarity against experience/projects.
    search_text = "\n".join([elsewhere_text, skills_text])
    if search_text.strip():
        similarity, chunk = best_matching_chunk(display, search_text)
    else:
        similarity, chunk = 0.0, ""

    if similarity >= _SEMANTIC_ONLY_THRESHOLD:
        score = round(50 + (similarity - _SEMANTIC_ONLY_THRESHOLD) * 80, 1)
        score = min(score, REQUIREMENT_STRONG_THRESHOLD - 1)  # semantic-only evidence never reaches "strong"
        return RequirementEvaluation(
            requirement=requirement, display_name=display, importance=importance, weight=weight,
            status=_status_for_score(score), score=score, confidence=score,
            evidence_text=chunk.strip(), evidence_source="semantic",
            reasoning=f"No explicit mention of {display}, but related wording was found: \"{chunk.strip()}\". "
                      f"Treated as weak/indirect evidence, not a confirmed match.",
        )

    return RequirementEvaluation(
        requirement=requirement, display_name=display, importance=importance, weight=weight,
        status="missing", score=8.0, confidence=8.0,
        evidence_text="", evidence_source="",
        reasoning=f"No meaningful evidence of {display} was found anywhere in the resume.",
    )


def build_candidate_row(identifier: str, resume: ParsedResume, keyword_result: KeywordMatchResult, jd: ParsedJD) -> CandidateMatrixRow:
    evaluations = []
    for skill in jd.required_skills:
        evaluations.append(_evaluate_one_requirement(skill, "must_have", resume, keyword_result))
    for skill in jd.preferred_skills:
        evaluations.append(_evaluate_one_requirement(skill, "preferred", resume, keyword_result))

    total_weight = sum(e.weight for e in evaluations)
    overall = sum(e.score * e.weight for e in evaluations) / total_weight if total_weight else 0.0
    return CandidateMatrixRow(identifier=identifier, evaluations=evaluations, overall_coverage_score=round(overall, 1))

"""Deterministic, template-based explanation generation — no LLM. Every
fact stated is read directly from computed matching results or the
resume's own text, so nothing here can hallucinate a skill or experience
the candidate never mentioned."""
from dataclasses import dataclass
from typing import List

from src.ranker import RankedCandidate

_STATUS_THRESHOLDS = [
    (85, "Excellent Fit"),
    (65, "Strong Fit"),
    (45, "Moderate Fit"),
    (25, "Weak Fit"),
    (0, "Poor Fit"),
]


def status_label(final_score: float) -> str:
    for threshold, label in _STATUS_THRESHOLDS:
        if final_score >= threshold:
            return label
    return "Poor Fit"


def _skill_display(skill: str) -> str:
    return skill.replace("_", " ").upper() if len(skill) <= 4 else skill.replace("_", " ").title()


def _first_meaningful_line(text: str, min_len: int = 25) -> str:
    for line in text.split("\n"):
        line = line.strip()
        if len(line) >= min_len:
            return line
    return ""


@dataclass
class CandidateExplanation:
    identifier: str
    rank: int
    final_score: float
    why: str
    matched_required: List[str]
    matched_preferred: List[str]
    missing_required: List[str]
    relevant_experience_snippet: str
    relevant_project_snippet: str
    score_breakdown: dict


def explain_candidate(candidate: RankedCandidate) -> CandidateExplanation:
    kw = candidate.features.keyword_result
    score = candidate.score

    if kw.required_coverage >= 0.9:
        why = "Strong alignment with the job's required skills and relevant hands-on experience."
    elif kw.required_coverage >= 0.6:
        why = "Covers most of the required skills, with relevant experience supporting the match."
    elif score.semantic_component >= 0.4:
        why = "Experience described differently from the JD's wording, but semantically relevant to the role."
    else:
        why = "Limited overlap with the job's core requirements."

    experience_snippet = _first_meaningful_line(candidate.resume.section("experience"))
    project_snippet = _first_meaningful_line(candidate.resume.section("projects"))

    return CandidateExplanation(
        identifier=candidate.identifier,
        rank=candidate.rank,
        final_score=score.final_score,
        why=why,
        matched_required=[_skill_display(s) for s in kw.matched_required],
        matched_preferred=[_skill_display(s) for s in kw.matched_preferred],
        missing_required=[_skill_display(s) for s in kw.missing_required],
        relevant_experience_snippet=experience_snippet,
        relevant_project_snippet=project_snippet,
        score_breakdown={
            "Semantic Match": round(score.semantic_component * 100, 1),
            "Required Skill Coverage": round(score.required_skill_component * 100, 1),
            "Experience/Project Relevance": round(score.experience_project_component * 100, 1),
            "Preferred Skill Coverage": round(score.preferred_skill_component * 100, 1),
            "ML Relevance": round(score.ml_component * 100, 1),
        },
    )


def format_explanation_text(exp: CandidateExplanation) -> str:
    lines = [
        f"{exp.identifier} — Rank #{exp.rank} — Score {exp.final_score}",
        "",
        "WHY:",
        exp.why,
        "",
    ]
    if exp.matched_required:
        lines.append("MATCHED REQUIRED SKILLS:")
        lines += [f"  ✓ {s}" for s in exp.matched_required]
        lines.append("")
    if exp.matched_preferred:
        lines.append("ADDITIONAL MATCHES (PREFERRED):")
        lines += [f"  ✓ {s}" for s in exp.matched_preferred]
        lines.append("")
    if exp.relevant_experience_snippet or exp.relevant_project_snippet:
        lines.append("RELEVANT EXPERIENCE:")
        if exp.relevant_experience_snippet:
            lines.append(f"  {exp.relevant_experience_snippet}")
        if exp.relevant_project_snippet:
            lines.append(f"  {exp.relevant_project_snippet}")
        lines.append("")
    if exp.missing_required:
        lines.append("MISSING:")
        lines += [f"  ⚠ {s}" for s in exp.missing_required]
        lines.append("")
    lines.append("SCORE BREAKDOWN:")
    for k, v in exp.score_breakdown.items():
        lines.append(f"  {k}: {v}%")
    return "\n".join(lines)


def explain_top_n(ranked_candidates: List[RankedCandidate], n: int = 3) -> List[CandidateExplanation]:
    return [explain_candidate(c) for c in ranked_candidates[:n]]


@dataclass
class ComparisonResult:
    a_identifier: str
    b_identifier: str
    a_wins: List[str]
    b_wins: List[str]
    verdict: str


def compare_candidates(a: RankedCandidate, b: RankedCandidate) -> ComparisonResult:
    """Component-by-component comparison, e.g. for a 'why is A ranked
    above B' recruiter question."""
    dimensions = [
        ("required skill coverage", a.score.required_skill_component, b.score.required_skill_component),
        ("semantic relevance", a.score.semantic_component, b.score.semantic_component),
        ("experience/project relevance", a.score.experience_project_component, b.score.experience_project_component),
        ("preferred skill coverage", a.score.preferred_skill_component, b.score.preferred_skill_component),
    ]

    a_wins, b_wins = [], []
    for label, a_val, b_val in dimensions:
        if a_val > b_val + 1e-6:
            a_wins.append(f"{label} is {round(a_val*100,1)}% vs {round(b_val*100,1)}%")
        elif b_val > a_val + 1e-6:
            b_wins.append(f"{label} is {round(b_val*100,1)}% vs {round(a_val*100,1)}%")

    if a.score.final_score > b.score.final_score:
        verdict = f"{a.identifier} ranks higher than {b.identifier} ({a.score.final_score} vs {b.score.final_score})."
    elif b.score.final_score > a.score.final_score:
        verdict = f"{b.identifier} ranks higher than {a.identifier} ({b.score.final_score} vs {a.score.final_score})."
    else:
        verdict = f"{a.identifier} and {b.identifier} are tied at {a.score.final_score}."

    return ComparisonResult(
        a_identifier=a.identifier, b_identifier=b.identifier,
        a_wins=a_wins, b_wins=b_wins, verdict=verdict,
    )

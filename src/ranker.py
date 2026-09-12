"""Ranks all candidates by final score, highest first, with deterministic
tie-breaking (ties are broken by required-skill coverage, then name — never
left to insertion order)."""
from dataclasses import dataclass
from typing import List

from src.feature_engineering import CandidateFeatures, build_features
from src.jd_parser import ParsedJD
from src.resume_parser import ParsedResume
from src.scorer import FinalScore, compute_final_score


@dataclass
class RankedCandidate:
    rank: int
    identifier: str
    resume: ParsedResume
    features: CandidateFeatures
    score: FinalScore


def rank_candidates(jd: ParsedJD, resumes: List[ParsedResume], identifiers: List[str]) -> List[RankedCandidate]:
    scored = []
    for identifier, resume in zip(identifiers, resumes):
        features = build_features(jd, resume)
        score = compute_final_score(features)
        scored.append((identifier, resume, features, score))

    scored.sort(
        key=lambda item: (
            -item[3].final_score,
            -item[2].values["required_skill_coverage"],
            item[0].lower(),
        )
    )

    ranked = [
        RankedCandidate(rank=i + 1, identifier=identifier, resume=resume, features=features, score=score)
        for i, (identifier, resume, features, score) in enumerate(scored)
    ]
    return ranked

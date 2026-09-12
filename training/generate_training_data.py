"""Generates a synthetic training set for the ML relevance model.

Design decision (documented, not hidden): we synthesize FEATURE VECTORS
directly — HIGH/MEDIUM/LOW fit tiers with realistic per-tier distributions
and noise — rather than generating thousands of fake resume/JD text pairs
and running them through the full NLP pipeline. The hackathon's actual
resumes only arrive on the day, so no real training data can exist in
advance either way; sampling in feature space is the practical choice for
a hackathon time budget and is honestly documented here and in the README.

Anti-leakage note (see project spec Phase 9/18): the training LABEL is
deliberately generated with different weights and a nonlinear component
than config.SCORE_WEIGHTS (which src/scorer.py uses at inference time).
If the label were just the final-score formula reapplied to its own
inputs, the model would trivially reproduce that formula and the
"ml_relevance" feature would be redundant with the rest of the score
rather than adding independent signal.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import RANDOM_SEED, TRAINING_DATA_PATH  # noqa: E402
from src.feature_engineering import FEATURE_NAMES  # noqa: E402

N_EXAMPLES = 3000
TIERS = ["HIGH", "MEDIUM", "LOW"]
TIER_WEIGHTS = [1 / 3, 1 / 3, 1 / 3]

# Per-tier (mean, std) for the primary sampled quantities. Everything else
# (semantic sub-scores, counts) is derived from these with its own noise.
TIER_PARAMS = {
    "HIGH": dict(semantic=(0.70, 0.10), req_cov=(0.90, 0.08), pref_cov=(0.65, 0.20),
                 tfidf=(0.55, 0.12), req_count=(8, 2), extra_skills=(6, 2)),
    "MEDIUM": dict(semantic=(0.45, 0.12), req_cov=(0.55, 0.15), pref_cov=(0.35, 0.20),
                   tfidf=(0.30, 0.12), req_count=(8, 2), extra_skills=(3, 2)),
    "LOW": dict(semantic=(0.20, 0.10), req_cov=(0.20, 0.12), pref_cov=(0.10, 0.10),
                tfidf=(0.10, 0.08), req_count=(8, 2), extra_skills=(1, 1)),
}


def _clip01(x):
    return float(np.clip(x, 0.0, 1.0))


def generate_row(rng: np.random.Generator, tier: str) -> dict:
    p = TIER_PARAMS[tier]

    semantic_overall = _clip01(rng.normal(*p["semantic"]))
    # Sub-scores vary around the overall with their own noise, as they
    # would for a real resume (strong on projects, weaker on education, etc).
    semantic_experience = _clip01(semantic_overall + rng.normal(0, 0.08))
    semantic_projects = _clip01(semantic_overall + rng.normal(0, 0.08))
    semantic_skills_context = _clip01(semantic_overall + rng.normal(0, 0.08))
    semantic_education = _clip01(semantic_overall * 0.7 + rng.normal(0, 0.10))

    required_skill_coverage = _clip01(rng.normal(*p["req_cov"]))
    preferred_skill_coverage = _clip01(rng.normal(*p["pref_cov"]))
    tfidf_similarity = _clip01(rng.normal(*p["tfidf"]))

    required_skill_count = max(3, int(round(rng.normal(*p["req_count"]))))
    matched_required_count = int(round(required_skill_coverage * required_skill_count))
    matched_required_count = min(matched_required_count, required_skill_count)
    missing_required_count = required_skill_count - matched_required_count

    extra_skills = max(0, int(round(rng.normal(*p["extra_skills"]))))
    preferred_matched_est = int(round(preferred_skill_coverage * 6))
    skill_count = matched_required_count + preferred_matched_est + extra_skills

    keyword_score = _clip01(
        0.6 * required_skill_coverage + 0.2 * preferred_skill_coverage + 0.2 * tfidf_similarity
    )

    experience_relevance = semantic_experience
    project_relevance = semantic_projects
    education_relevance = semantic_education

    # --- Label: a deliberately different combination from the runtime
    # scorer's weights, plus nonlinear thresholds and noise, standing in
    # for "how a human recruiter would rate overall fit."
    latent = (
        0.45 * semantic_overall
        + 0.35 * required_skill_coverage
        + 0.15 * preferred_skill_coverage
        + 0.05 * tfidf_similarity
    )
    if required_skill_coverage >= 0.85:
        latent += 0.05  # a recruiter's bonus for near-complete required coverage
    if missing_required_count >= 4:
        latent -= 0.10  # a recruiter's penalty for too many missing must-haves
    latent += rng.normal(0, 0.06)  # human-rating noise
    relevance_label = round(_clip01(latent) * 100, 2)

    return {
        "tier": tier,
        "semantic_overall": semantic_overall,
        "semantic_experience": semantic_experience,
        "semantic_projects": semantic_projects,
        "semantic_skills_context": semantic_skills_context,
        "semantic_education": semantic_education,
        "keyword_score": keyword_score,
        "required_skill_coverage": required_skill_coverage,
        "preferred_skill_coverage": preferred_skill_coverage,
        "tfidf_similarity": tfidf_similarity,
        "skill_count": skill_count,
        "required_skill_count": required_skill_count,
        "matched_required_count": matched_required_count,
        "missing_required_count": missing_required_count,
        "experience_relevance": experience_relevance,
        "project_relevance": project_relevance,
        "education_relevance": education_relevance,
        "relevance_label": relevance_label,
    }


def main():
    rng = np.random.default_rng(RANDOM_SEED)
    rows = []
    for _ in range(N_EXAMPLES):
        tier = rng.choice(TIERS, p=TIER_WEIGHTS)
        rows.append(generate_row(rng, tier))

    df = pd.DataFrame(rows)
    ordered_cols = ["tier"] + FEATURE_NAMES + ["relevance_label"]
    df = df[ordered_cols]
    TRAINING_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(TRAINING_DATA_PATH, index=False)
    print(f"Wrote {len(df)} rows to {TRAINING_DATA_PATH}")
    print(df.groupby("tier")["relevance_label"].agg(["mean", "std", "count"]))


if __name__ == "__main__":
    main()

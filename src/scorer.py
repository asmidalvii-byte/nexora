"""Final transparent 0-100 scoring layer. Weights live only in config.py —
never scattered as magic numbers here."""
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import joblib
import numpy as np

from config import RANKING_MODEL_PATH, SCORE_WEIGHTS
from src.feature_engineering import CandidateFeatures


@lru_cache(maxsize=1)
def _load_ml_bundle() -> Optional[dict]:
    if not RANKING_MODEL_PATH.exists():
        return None
    # our own locally-trained artifact (training/train_model.py), not untrusted input
    return joblib.load(RANKING_MODEL_PATH)


def _ml_relevance(features: CandidateFeatures) -> float:
    bundle = _load_ml_bundle()
    if bundle is None:
        return 0.0
    model = bundle["model"]
    feature_names = bundle["feature_names"]
    vector = np.array([[features.values[name] for name in feature_names]])
    pred = float(model.predict(vector)[0])
    return max(0.0, min(100.0, pred)) / 100.0  # normalize to 0-1 like the other components


@dataclass
class FinalScore:
    final_score: float  # 0-100
    semantic_component: float
    required_skill_component: float
    experience_project_component: float
    preferred_skill_component: float
    ml_component: float
    weights_used: dict


def compute_final_score(features: CandidateFeatures) -> FinalScore:
    v = features.values

    semantic = v["semantic_overall"]
    required = v["required_skill_coverage"]
    experience_projects = max(v["experience_relevance"], v["project_relevance"])
    preferred = v["preferred_skill_coverage"]
    ml_relevance = _ml_relevance(features)

    weighted = (
        SCORE_WEIGHTS["semantic"] * semantic
        + SCORE_WEIGHTS["required_skills"] * required
        + SCORE_WEIGHTS["experience_projects"] * experience_projects
        + SCORE_WEIGHTS["preferred_skills"] * preferred
        + SCORE_WEIGHTS["ml_relevance"] * ml_relevance
    )
    final = round(max(0.0, min(1.0, weighted)) * 100, 2)

    return FinalScore(
        final_score=final,
        semantic_component=round(semantic, 4),
        required_skill_component=round(required, 4),
        experience_project_component=round(experience_projects, 4),
        preferred_skill_component=round(preferred, 4),
        ml_component=round(ml_relevance, 4),
        weights_used=dict(SCORE_WEIGHTS),
    )

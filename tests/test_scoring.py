from src.feature_engineering import CandidateFeatures, FEATURE_NAMES
from src.scorer import compute_final_score

BASE_VALUES = {
    "semantic_overall": 0.5,
    "semantic_experience": 0.5,
    "semantic_projects": 0.5,
    "semantic_skills_context": 0.5,
    "semantic_education": 0.5,
    "keyword_score": 0.5,
    "required_skill_coverage": 0.5,
    "preferred_skill_coverage": 0.5,
    "tfidf_similarity": 0.5,
    "skill_count": 5,
    "required_skill_count": 8,
    "matched_required_count": 4,
    "missing_required_count": 4,
    "experience_relevance": 0.5,
    "project_relevance": 0.5,
    "education_relevance": 0.5,
}


def _features(overrides: dict) -> CandidateFeatures:
    values = dict(BASE_VALUES)
    values.update(overrides)
    return CandidateFeatures(values=values, keyword_result=None, semantic_result=None)


def test_score_bounded_0_to_100():
    for overrides in [
        {"semantic_overall": 0.0, "required_skill_coverage": 0.0, "preferred_skill_coverage": 0.0},
        {"semantic_overall": 1.0, "required_skill_coverage": 1.0, "preferred_skill_coverage": 1.0,
         "experience_relevance": 1.0, "project_relevance": 1.0},
    ]:
        result = compute_final_score(_features(overrides))
        assert 0.0 <= result.final_score <= 100.0


def test_keyword_change_affects_final_score_at_fixed_semantic():
    """Test A (spec section 23): same semantic score, different keyword-
    driven inputs -> final score MUST change."""
    low_keyword = _features({"required_skill_coverage": 0.1, "preferred_skill_coverage": 0.1})
    high_keyword = _features({"required_skill_coverage": 0.9, "preferred_skill_coverage": 0.9})

    score_low = compute_final_score(low_keyword).final_score
    score_high = compute_final_score(high_keyword).final_score

    assert score_low != score_high
    assert score_high > score_low


def test_semantic_change_affects_final_score_at_fixed_keyword():
    """Test B (spec section 23): same keyword score, different semantic
    score -> final score MUST change."""
    low_semantic = _features({"semantic_overall": 0.05})
    high_semantic = _features({"semantic_overall": 0.95})

    score_low = compute_final_score(low_semantic).final_score
    score_high = compute_final_score(high_semantic).final_score

    assert score_low != score_high
    assert score_high > score_low


def test_required_skill_coverage_affects_final_score():
    low_required = _features({"required_skill_coverage": 0.0})
    high_required = _features({"required_skill_coverage": 1.0})

    assert compute_final_score(high_required).final_score > compute_final_score(low_required).final_score


def test_feature_vector_matches_declared_feature_names():
    features = _features({})
    vector = features.as_vector()
    assert len(vector) == len(FEATURE_NAMES)

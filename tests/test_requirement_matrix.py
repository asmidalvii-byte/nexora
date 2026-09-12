from src.jd_parser import parse_jd
from src.keyword_matcher import match_keywords
from src.requirement_matrix import build_candidate_row


def _row_for(jd_text: str, resume_text: str, identifier: str = "Test Candidate"):
    from src.resume_parser import parse_resume_sections
    jd = parse_jd(jd_text)
    resume = parse_resume_sections(resume_text)
    kw = match_keywords(jd, resume)
    return build_candidate_row(identifier, resume, kw, jd), jd


def _status_of(row, requirement: str) -> str:
    return next(e.status for e in row.evaluations if e.requirement == requirement)


def test_strong_match_requires_experience_or_project_evidence():
    row, _ = _row_for(
        "Required Skills\nReact\n",
        "Skills\nReact\n\nExperience\nBuilt a dashboard using React hooks and context.\n",
    )
    assert _status_of(row, "react") == "strong"


def test_skills_only_listing_is_partial_not_strong():
    row, _ = _row_for(
        "Required Skills\nDocker\n",
        "Skills\nDocker\n\nExperience\nBuilt REST APIs in Python.\n",
    )
    assert _status_of(row, "docker") == "partial"


def test_missing_skill_is_missing():
    row, _ = _row_for("Required Skills\nKubernetes\n", "Skills\nPython\n\nExperience\nBuilt REST APIs.\n")
    assert _status_of(row, "kubernetes") == "missing"


def test_java_does_not_satisfy_javascript():
    row, _ = _row_for(
        "Required Skills\nJavaScript\n",
        "Skills\nJava\n\nExperience\nBuilt backend services in Java.\n",
    )
    assert _status_of(row, "javascript") == "missing"


def test_mysql_does_not_satisfy_mongodb():
    row, _ = _row_for(
        "Required Skills\nMongoDB\n",
        "Skills\nMySQL\n\nExperience\nDesigned MySQL schemas for a reporting system.\n",
    )
    assert _status_of(row, "mongodb") == "missing"


def test_kubernetes_gives_only_partial_credit_for_docker():
    row, _ = _row_for(
        "Required Skills\nDocker\n",
        "Skills\nKubernetes\n\nExperience\nDeployed services to a Kubernetes cluster.\n",
    )
    assert _status_of(row, "docker") == "partial"
    ev = next(e for e in row.evaluations if e.requirement == "docker")
    assert "Kubernetes" in ev.reasoning
    assert ev.score < 80  # never strong from a related-but-distinct technology


def test_react_native_gives_only_partial_credit_for_react():
    row, _ = _row_for(
        "Required Skills\nReact\n",
        "Skills\nReact Native\n\nExperience\nBuilt a mobile app with React Native.\n",
    )
    assert _status_of(row, "react") == "partial"


def test_every_evaluation_has_a_reasoning_sentence():
    row, _ = _row_for(
        "Required Skills\nPython\nDocker\n\nPreferred Skills\nAWS\n",
        "Skills\nPython\n\nExperience\nBuilt data pipelines in Python.\n",
    )
    for e in row.evaluations:
        assert e.reasoning
        assert e.display_name.lower().split()[0] in e.reasoning.lower() or e.requirement in e.reasoning.lower()


def test_required_weighted_more_than_preferred_in_overall_score():
    # A single required skill (weight 1.0) vs a single preferred skill
    # (weight 0.5) — required's total weight dominates, so missing it must
    # hurt the overall score more than missing the preferred one.
    row_missing_required, jd = _row_for(
        "Required Skills\nPython\n\nPreferred Skills\nDocker\n",
        "Skills\nDocker\n\nExperience\nUsed Docker extensively in production.\n",
    )
    row_missing_preferred, _ = _row_for(
        "Required Skills\nPython\n\nPreferred Skills\nDocker\n",
        "Skills\nPython\n\nExperience\nBuilt applications in Python.\n",
    )
    assert row_missing_required.overall_coverage_score < row_missing_preferred.overall_coverage_score


def test_must_have_vs_preferred_importance_labeled():
    row, _ = _row_for(
        "Required Skills\nPython\n\nPreferred Skills\nDocker\n",
        "Skills\nPython\n\nExperience\nBuilt apps in Python.\n",
    )
    importances = {e.requirement: e.importance for e in row.evaluations}
    assert importances["python"] == "must_have"
    assert importances["docker"] == "preferred"

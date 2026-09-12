from src.recruiter_search import search_candidates
from tests.conftest import SAMPLE_JD_TEXT, STRONG_RESUME_TEXT, WEAK_RESUME_TEXT
from src.jd_parser import parse_jd
from src.resume_parser import parse_resume_sections
from src.ranker import rank_candidates


def _ranked():
    jd = parse_jd(SAMPLE_JD_TEXT)
    strong = parse_resume_sections(STRONG_RESUME_TEXT)
    weak = parse_resume_sections(WEAK_RESUME_TEXT)
    return rank_candidates(jd, [strong, weak], ["Strong Candidate", "Weak Candidate"])


def test_search_finds_matching_skills():
    ranked = _ranked()
    results = search_candidates("Show me candidates with React and Node.js", ranked)
    assert len(results) == 1
    assert results[0].candidate.identifier == "Strong Candidate"
    assert "react" in results[0].matched_query_skills
    assert "node.js" in results[0].matched_query_skills


def test_search_reports_missing_query_skills():
    ranked = _ranked()
    results = search_candidates("Python + SQL + machine learning", ranked)
    result_by_id = {r.candidate.identifier: r for r in results}
    assert "Weak Candidate" in result_by_id
    weak_result = result_by_id["Weak Candidate"]
    assert "python" in weak_result.matched_query_skills
    assert "machine_learning" in weak_result.missing_query_skills or "sql" in weak_result.missing_query_skills


def test_search_excludes_candidates_with_zero_matching_skills():
    ranked = _ranked()
    results = search_candidates("Rust and Go and Kubernetes", ranked)
    assert results == []


def test_search_with_no_recognizable_skills_returns_empty():
    ranked = _ranked()
    results = search_candidates("someone great and enthusiastic", ranked)
    assert results == []


def test_search_orders_by_coverage_then_rank():
    ranked = _ranked()
    results = search_candidates("React and Node.js and Python", ranked)
    coverages = [r.query_coverage for r in results]
    assert coverages == sorted(coverages, reverse=True)

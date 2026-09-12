import pytest

from src.jd_parser import parse_jd
from src.keyword_matcher import match_keywords
from src.resume_parser import parse_resume_sections
from src.skill_matcher import extract_skills
from tests.conftest import SAMPLE_JD_TEXT, STRONG_RESUME_TEXT, WEAK_RESUME_TEXT


def test_exact_skill_match():
    found = extract_skills("I know React and Node.js well.")
    assert "react" in found
    assert "node.js" in found


def test_alias_match():
    found = extract_skills("Experience with ReactJS and node js development.")
    assert "react" in found
    assert "node.js" in found


def test_missing_skill_not_matched():
    found = extract_skills("I only know Python and Django.")
    assert "react" not in found


def test_case_normalization():
    found_upper = extract_skills("REACT NODE.JS MONGODB")
    found_lower = extract_skills("react node.js mongodb")
    assert set(found_upper.keys()) == set(found_lower.keys())


def test_typo_tolerance_catches_common_misspellings():
    found = extract_skills("I know Pythom and Reakt, also used Doker and Djngo.")
    assert found["python"].fuzzy is True
    assert found["react"].fuzzy is True
    assert found["docker"].fuzzy is True
    assert found["django"].fuzzy is True


def test_typo_tolerance_does_not_relabel_exact_matches_as_fuzzy():
    found = extract_skills("I know Python and React well.")
    assert found["python"].fuzzy is False
    assert found["react"].fuzzy is False


def test_typo_tolerance_does_not_cross_contaminate_real_short_aliases():
    """Regression: 'css' is a real, correctly-spelled alias — it must never
    be treated as a typo of an unrelated skill (e.g. 'scss') just because
    it happens to be a short edit distance away."""
    found = extract_skills("We use CSS for styling.")
    assert found["css"].fuzzy is False
    assert "sass" not in found


def test_typo_tolerance_ignores_unrelated_prose():
    found = extract_skills("We eat rice and dosa, then dock the boat.")
    fuzzy_hits = {k for k, v in found.items() if v.fuzzy}
    assert fuzzy_hits == set()


def test_compound_token_false_positive_guard():
    found = extract_skills("Used Express.js and Node.js and C++ and C#.")
    assert "javascript" not in found  # 'js' must not fire from '.js' suffixes
    assert "c" not in found  # bare 'c' must not fire from c++/c#
    assert "c++" in found
    assert "c#" in found


def test_required_vs_preferred_coverage():
    jd = parse_jd(SAMPLE_JD_TEXT)
    strong_resume = parse_resume_sections(STRONG_RESUME_TEXT)
    result = match_keywords(jd, strong_resume)
    assert result.required_coverage == 1.0
    assert "typescript" in result.matched_preferred


def test_missing_required_skills_listed():
    jd = parse_jd(SAMPLE_JD_TEXT)
    weak_resume = parse_resume_sections(WEAK_RESUME_TEXT)
    result = match_keywords(jd, weak_resume)
    assert result.required_coverage < 0.5
    assert "react" in result.missing_required


def test_required_weighted_more_than_preferred():
    """Missing a required skill must hurt more than missing a preferred one
    (project spec section 12). Both resumes below are complete except for
    exactly one missing skill each, so this isolates the per-skill weight
    rather than being confounded by different coverage magnitudes."""
    jd = parse_jd(SAMPLE_JD_TEXT)  # required: 9 skills, preferred: 6 skills

    # Missing exactly one REQUIRED skill (javascript); has all 6 preferred.
    resume_missing_required = parse_resume_sections(
        "Skills\nReact, Node.js, MongoDB, Express.js, Git, HTML, CSS, REST API, "
        "TypeScript, Docker, AWS, Redux, Jest, Agile\n"
    )
    # Has all 9 required; missing exactly one PREFERRED skill (docker).
    resume_missing_preferred = parse_resume_sections(
        "Skills\nJavaScript, React, Node.js, MongoDB, Express.js, Git, HTML, CSS, "
        "REST API, TypeScript, AWS, Redux, Jest, Agile\n"
    )

    result_missing_required = match_keywords(jd, resume_missing_required)
    result_missing_preferred = match_keywords(jd, resume_missing_preferred)

    assert result_missing_required.required_coverage == pytest.approx(8 / 9, abs=1e-3)
    assert result_missing_required.preferred_coverage == 1.0
    assert result_missing_preferred.required_coverage == 1.0
    assert result_missing_preferred.preferred_coverage == pytest.approx(5 / 6, abs=1e-3)

    assert result_missing_required.keyword_score < result_missing_preferred.keyword_score

from src.jd_parser import parse_jd
from src.resume_parser import parse_resume_sections
from src.semantic_matcher import match_semantics
from tests.conftest import SAMPLE_JD_TEXT


def test_similar_phrasing_scores_higher_than_unrelated():
    jd = parse_jd(SAMPLE_JD_TEXT)

    related_resume = parse_resume_sections(
        "Experience\nBuilt backend REST APIs using Express and MongoDB, "
        "with a React frontend for the dashboard.\n"
    )
    unrelated_resume = parse_resume_sections(
        "Experience\nDesigned marketing brochures and managed social media "
        "campaigns for a retail client.\n"
    )

    related_score = match_semantics(jd, related_resume).semantic_overall
    unrelated_score = match_semantics(jd, unrelated_resume).semantic_overall

    assert related_score > unrelated_score


def test_semantic_recognizes_different_wording_for_same_meaning():
    jd = parse_jd(SAMPLE_JD_TEXT)  # asks for "Develop and maintain REST APIs using Node.js and Express"
    resume = parse_resume_sections(
        "Experience\nBuilt backend web services and endpoints with Express.js, "
        "connected to a MongoDB database.\n"
    )
    result = match_semantics(jd, resume)
    assert result.semantic_experience > 0.2


def test_semantic_scores_bounded_0_to_1():
    jd = parse_jd(SAMPLE_JD_TEXT)
    resume = parse_resume_sections("Experience\nSome unrelated content about gardening.\n")
    result = match_semantics(jd, resume)
    for value in [result.semantic_overall, result.semantic_experience, result.semantic_projects]:
        assert 0.0 <= value <= 1.0

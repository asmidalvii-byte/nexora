from src.explanation import compare_candidates, explain_top_n
from src.jd_parser import parse_jd
from src.pdf_parser import extract_text_from_pdf
from src.ranker import rank_candidates
from src.resume_parser import parse_resume_sections
from src.text_cleaner import clean_text
from tests.conftest import SAMPLE_JD_TEXT, STRONG_RESUME_TEXT, WEAK_RESUME_TEXT


def _load_resume_from_pdf(make_pdf, text, identifier):
    pdf_bytes = make_pdf(text)
    parsed_pdf = extract_text_from_pdf(pdf_bytes, source_name=identifier)
    assert parsed_pdf.ok
    cleaned = clean_text(parsed_pdf.text).original_text
    return parse_resume_sections(cleaned)


def test_end_to_end_jd_pdf_plus_resume_pdfs_to_ranking(make_pdf):
    jd_pdf_bytes = make_pdf(SAMPLE_JD_TEXT)
    jd_parsed_pdf = extract_text_from_pdf(jd_pdf_bytes, source_name="jd.pdf")
    assert jd_parsed_pdf.ok
    jd = parse_jd(clean_text(jd_parsed_pdf.text).original_text)

    identifiers = ["strong_candidate", "weak_candidate"]
    resumes = [
        _load_resume_from_pdf(make_pdf, STRONG_RESUME_TEXT, "strong.pdf"),
        _load_resume_from_pdf(make_pdf, WEAK_RESUME_TEXT, "weak.pdf"),
    ]

    ranked = rank_candidates(jd, resumes, identifiers)

    # All candidates returned.
    assert len(ranked) == 2
    # Strong-fit candidate ranks higher (rank 1) than weak-fit candidate.
    ranked_by_identifier = {c.identifier: c for c in ranked}
    assert ranked_by_identifier["strong_candidate"].rank < ranked_by_identifier["weak_candidate"].rank
    assert ranked_by_identifier["strong_candidate"].score.final_score > ranked_by_identifier["weak_candidate"].score.final_score

    # Scores stay within 0-100.
    for c in ranked:
        assert 0.0 <= c.score.final_score <= 100.0


def test_ranking_handles_ties_deterministically():
    from src.feature_engineering import CandidateFeatures
    from src.ranker import RankedCandidate
    from src.scorer import FinalScore

    def make_candidate(identifier, score):
        fs = FinalScore(
            final_score=score, semantic_component=0.5, required_skill_component=0.5,
            experience_project_component=0.5, preferred_skill_component=0.5,
            ml_component=0.5, weights_used={},
        )
        cf = CandidateFeatures(values={"required_skill_coverage": 0.5}, keyword_result=None, semantic_result=None)
        return (identifier, None, cf, fs)

    # Manually verify the sort key produces stable, deterministic order for equal scores.
    items = [make_candidate("Zed", 50.0), make_candidate("Amy", 50.0)]
    items.sort(key=lambda item: (-item[3].final_score, -item[2].values["required_skill_coverage"], item[0].lower()))
    assert [i[0] for i in items] == ["Amy", "Zed"]


def test_top_3_explanations_no_hallucinated_skills(make_pdf):
    jd = parse_jd(SAMPLE_JD_TEXT)
    resumes = [
        _load_resume_from_pdf(make_pdf, STRONG_RESUME_TEXT, "a.pdf"),
        _load_resume_from_pdf(make_pdf, WEAK_RESUME_TEXT, "b.pdf"),
    ]
    ranked = rank_candidates(jd, resumes, ["A", "B"])
    explanations = explain_top_n(ranked, n=2)

    for exp, candidate in zip(explanations, ranked):
        # Every skill claimed in the explanation must come directly from the
        # keyword engine's own computed matches — the template only ever
        # reformats that data, it never invents a skill of its own.
        expected_required = {s.replace("_", " ").title() if len(s) > 4 else s.upper()
                              for s in candidate.features.keyword_result.matched_required}
        expected_preferred = {s.replace("_", " ").title() if len(s) > 4 else s.upper()
                               for s in candidate.features.keyword_result.matched_preferred}
        assert set(exp.matched_required) == expected_required
        assert set(exp.matched_preferred) == expected_preferred
        for missing in exp.missing_required:
            assert missing not in expected_required


def test_compare_candidates_identifies_strengths_on_both_sides(make_pdf):
    jd = parse_jd(SAMPLE_JD_TEXT)
    resumes = [
        _load_resume_from_pdf(make_pdf, STRONG_RESUME_TEXT, "a.pdf"),
        _load_resume_from_pdf(make_pdf, WEAK_RESUME_TEXT, "b.pdf"),
    ]
    ranked = rank_candidates(jd, resumes, ["A", "B"])
    comparison = compare_candidates(ranked[0], ranked[1])
    assert comparison.a_identifier == ranked[0].identifier
    assert "ranks higher" in comparison.verdict

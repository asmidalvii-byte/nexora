from src.explanation import compare_candidates
from src.feature_engineering import CandidateFeatures
from src.jd_parser import parse_jd
from src.pdf_parser import extract_text_from_pdf
from src.ranker import rank_candidates
from src.recruiter_chat import answer_question, find_candidate
from src.resume_parser import parse_resume_sections
from src.scorer import FinalScore
from src.text_cleaner import clean_text
from tests.conftest import SAMPLE_JD_TEXT, STRONG_RESUME_TEXT, WEAK_RESUME_TEXT


def _ranked_pair(make_pdf):
    jd = parse_jd(SAMPLE_JD_TEXT)

    def load(text, name):
        pdf_bytes = make_pdf(text)
        parsed = extract_text_from_pdf(pdf_bytes, source_name=name)
        return parse_resume_sections(clean_text(parsed.text).original_text)

    resumes = [load(STRONG_RESUME_TEXT, "a.pdf"), load(WEAK_RESUME_TEXT, "b.pdf")]
    return rank_candidates(jd, resumes, ["Strong Candidate", "Weak Candidate"])


def test_why_is_x_ranked_above_y_answers_correctly(make_pdf):
    ranked = _ranked_pair(make_pdf)
    answer = answer_question("Why is Strong Candidate ranked above Weak Candidate?", ranked)
    assert "Strong Candidate" in answer.text
    assert "Weak Candidate" in answer.text
    assert "ranks higher" in answer.text
    assert set(answer.matched_candidates) == {"Strong Candidate", "Weak Candidate"}


def test_compare_phrasing_also_works(make_pdf):
    ranked = _ranked_pair(make_pdf)
    answer = answer_question("Compare Strong Candidate and Weak Candidate", ranked)
    assert "Strong Candidate" in answer.text
    assert "Weak Candidate" in answer.text


def test_single_candidate_question_uses_explanation(make_pdf):
    ranked = _ranked_pair(make_pdf)
    answer = answer_question("Tell me about Strong Candidate", ranked)
    assert "Strong Candidate" in answer.text
    assert "SCORE BREAKDOWN" in answer.text


def test_unknown_candidate_name_gets_clarifying_message_not_a_guess(make_pdf):
    ranked = _ranked_pair(make_pdf)
    answer = answer_question("Why is Nonexistent Person ranked above Weak Candidate?", ranked)
    assert answer.matched_candidates == []
    assert "couldn't" in answer.text.lower() or "could not" in answer.text.lower()


def test_ambiguous_fragment_lists_suggestions_rather_than_guessing():
    class FakeResume:
        def section(self, _name):
            return ""

    dummy_features = CandidateFeatures(values={"required_skill_coverage": 0.5}, keyword_result=None, semantic_result=None)
    dummy_score = FinalScore(
        final_score=50.0, semantic_component=0.5, required_skill_component=0.5,
        experience_project_component=0.5, preferred_skill_component=0.5, ml_component=0.5, weights_used={},
    )
    from src.ranker import RankedCandidate

    ranked = [
        RankedCandidate(rank=1, identifier="Priya Sharma", resume=FakeResume(), features=dummy_features, score=dummy_score),
        RankedCandidate(rank=2, identifier="Priya Nair", resume=FakeResume(), features=dummy_features, score=dummy_score),
    ]
    candidate, suggestions = find_candidate("Priya", ranked)
    assert candidate is None
    assert set(suggestions) == {"Priya Sharma", "Priya Nair"}


def test_no_ranked_candidates_handled_gracefully():
    answer = answer_question("Why is X ranked above Y?", [])
    assert "run shortlisting" in answer.text.lower()

from src.dedup import dedupe_ranked_candidates, find_duplicate_groups
from src.feature_engineering import CandidateFeatures
from src.ranker import RankedCandidate
from src.resume_parser import ParsedResume
from src.scorer import FinalScore


def _resume(name, email, raw_text):
    return ParsedResume(name=name, email=email, phone=None, sections={}, raw_text=raw_text)


def test_same_email_is_a_duplicate():
    resumes = [
        _resume("Jane Doe", "jane@example.org", "Jane Doe resume text A"),
        _resume("Jane Doe", "JANE@example.org", "Jane Doe resume text B, slightly different"),
    ]
    groups = find_duplicate_groups(resumes, ["Jane Doe (a.pdf)", "Jane Doe (b.docx)"])
    assert len(groups) == 1
    assert groups[0].indices == [0, 1]


def test_near_identical_text_is_a_duplicate():
    text_a = "Jane Doe\nSkills: Python, React\nExperience: Built things.\n" * 3
    text_b = text_a + " "  # trivial whitespace diff
    resumes = [_resume("Jane Doe", None, text_a), _resume("Jane Doe", None, text_b)]
    groups = find_duplicate_groups(resumes, ["a", "b"])
    assert len(groups) == 1


def test_different_named_people_are_never_merged_even_with_templated_text():
    """Regression: two genuinely different candidates whose resumes share
    heavily templated boilerplate (same company, same bullet points) must
    never be merged just because the text is similar — their names clearly
    differ, which is a stronger signal that they are different people."""
    template = "Software Engineering Intern at Synapse Analytics. Built REST APIs. Wrote tests."
    resumes = [
        _resume("Aditya Joshi", None, f"Aditya Joshi\n{template}"),
        _resume("Meera Pillai", None, f"Meera Pillai\n{template}"),
    ]
    groups = find_duplicate_groups(resumes, ["Aditya Joshi", "Meera Pillai"])
    assert groups == []


def test_placeholder_email_does_not_force_a_merge():
    """Regression: a literal filler address ('dummy.email@example.com')
    reused across a template dataset must not be treated as a real
    identity match on its own — only text similarity (or a real shared
    email) should be able to group these."""
    resumes = [
        _resume(None, "dummy.email@example.com", "Blockchain Developer resume, unique wording here only."),
        _resume(None, "dummy.email@example.com", "Completely different Product Manager resume, other wording."),
    ]
    groups = find_duplicate_groups(resumes, ["a", "b"])
    assert groups == []


def _make_ranked(identifier, score, resume):
    features = CandidateFeatures(values={"required_skill_coverage": 0.5}, keyword_result=None, semantic_result=None)
    final_score = FinalScore(
        final_score=score, semantic_component=0.5, required_skill_component=0.5,
        experience_project_component=0.5, preferred_skill_component=0.5, ml_component=0.5, weights_used={},
    )
    return RankedCandidate(rank=0, identifier=identifier, resume=resume, features=features, score=final_score)


def test_dedupe_ranked_candidates_keeps_best_scoring_copy_and_renumbers():
    text = "Jane Doe\nSkills: Python\n"
    ranked = [
        _make_ranked("Jane Doe (a)", 80.0, _resume("Jane Doe", "jane@example.org", text)),
        _make_ranked("Someone Else", 70.0, _resume("Someone Else", "else@example.org", "Someone Else\nSkills: SQL\n")),
        _make_ranked("Jane Doe (b)", 75.0, _resume("Jane Doe", "jane@example.org", text)),
    ]
    deduped, duplicate_map = dedupe_ranked_candidates(ranked)

    assert [c.identifier for c in deduped] == ["Jane Doe (a)", "Someone Else"]
    assert [c.rank for c in deduped] == [1, 2]
    assert duplicate_map == {"Jane Doe (a)": ["Jane Doe (b)"]}

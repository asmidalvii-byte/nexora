from src.credibility_checker import check_credibility
from src.resume_parser import parse_resume_sections
from tests.conftest import STRONG_RESUME_TEXT


def test_clean_resume_shows_no_inconsistencies():
    resume = parse_resume_sections(STRONG_RESUME_TEXT)
    report = check_credibility(resume)
    assert report.status == "clear"
    assert report.status_label == "✓ No inconsistencies detected"
    assert report.flags == []


def test_reversed_dates_flagged():
    resume = parse_resume_sections(
        "Experience\nFreelance Developer | Dec 2021 - Nov 2020\nDid some freelance work.\n"
    )
    report = check_credibility(resume)
    assert report.status == "review"
    assert any("before its start date" in f.message for f in report.flags)


def test_overlapping_full_time_roles_flagged_with_location_note():
    resume = parse_resume_sections(
        "Experience\n"
        "Backend Engineer, Company A, Mumbai | Jan 2022 - Dec 2022\nBuilt backend systems.\n"
        "Senior Engineer, Company B, Pune | Aug 2022 - Nov 2022\nLed a small team.\n"
    )
    report = check_credibility(resume)
    assert report.status == "review"
    overlap_flags = [f for f in report.flags if "overlap" in f.message.lower()]
    assert len(overlap_flags) >= 1
    assert "Mumbai" in overlap_flags[0].message and "Pune" in overlap_flags[0].message


def test_internship_overlap_is_not_flagged_as_full_time_conflict():
    """Spec requirement: overlaps involving internships/concurrent roles
    shouldn't be treated as suspicious full-time conflicts — the location
    note should NOT appear, though the overlap itself is still surfaced."""
    resume = parse_resume_sections(
        "Experience\n"
        "Software Intern, Company A, Mumbai | Jan 2022 - Dec 2022\nHelped with backend tasks.\n"
        "Teaching Assistant, University, Pune | Aug 2022 - Nov 2022\nAssisted coursework.\n"
    )
    report = check_credibility(resume)
    overlap_flags = [f for f in report.flags if "overlap" in f.message.lower()]
    assert len(overlap_flags) >= 1
    assert "different locations" not in overlap_flags[0].message


def test_duplicate_entry_flagged():
    resume = parse_resume_sections(
        "Experience\n"
        "Backend Engineer, Company A | Jan 2022 - Dec 2022\nBuilt systems.\n"
        "Backend Engineer, Company A | Jan 2022 - Dec 2022\nBuilt systems again.\n"
    )
    report = check_credibility(resume)
    assert any("duplicate entry" in f.message.lower() for f in report.flags)


def test_conflicting_dates_for_similar_role_flagged():
    resume = parse_resume_sections(
        "Experience\n"
        "Backend Engineer, Company A | Jan 2022 - Dec 2022\nBuilt systems.\n"
        "Backend Engineer, Company A | Mar 2023 - Jun 2023\nBuilt systems, different dates.\n"
    )
    report = check_credibility(resume)
    assert any("conflicting dates" in f.message.lower() or "different dates" in f.message.lower() for f in report.flags)


def test_experience_claim_mismatch_flagged():
    resume = parse_resume_sections(
        "Summary\nEngineer with 10 years of experience.\n\n"
        "Experience\nBackend Engineer, Company A | Jan 2022 - Dec 2022\nBuilt systems.\n"
    )
    report = check_credibility(resume)
    assert any("10 years of experience" in f.message for f in report.flags)


def test_experience_claim_within_tolerance_not_flagged():
    resume = parse_resume_sections(
        "Summary\nEngineer with 1 year of experience.\n\n"
        "Experience\nBackend Engineer, Company A | Jan 2022 - Dec 2022\nBuilt systems.\n"
    )
    report = check_credibility(resume)
    assert not any("experience" in f.message and "Requires verification" in f.message for f in report.flags)


def test_foundational_skills_exempt_from_credibility_check():
    """Regression: HTML/CSS/JavaScript/Git etc. are almost never
    independently re-mentioned once a higher-level framework is cited
    (e.g. 'built a React frontend' implies JS/HTML/CSS) — flagging these
    produced a false positive on nearly every real resume."""
    resume = parse_resume_sections(
        "Skills\nReact, JavaScript, HTML, CSS, Git, Kubernetes\n\n"
        "Experience\nBuilt a full-stack app with React.\n"
    )
    report = check_credibility(resume, matched_required_skills=["javascript", "html", "css", "git", "kubernetes"])
    flagged_skills = {f.message for f in report.flags}
    assert not any("JavaScript" in m or "\"HTML\"" in m or "\"CSS\"" in m or "\"GIT\"" in m for m in flagged_skills)
    assert any("Kubernetes" in m for m in flagged_skills)


def test_skill_without_supporting_evidence_flagged():
    resume = parse_resume_sections(
        "Skills\nPython, Kubernetes\n\n"
        "Experience\nBackend Engineer | Jan 2022 - Dec 2022\nBuilt systems in Python.\n"
    )
    report = check_credibility(resume, matched_required_skills=["python", "kubernetes"])
    assert any("Kubernetes" in f.message for f in report.flags)
    assert not any("\"Python\"" in f.message for f in report.flags)


def test_never_uses_accusatory_language():
    resume = parse_resume_sections(
        "Summary\nEngineer with 10 years of experience.\n\n"
        "Experience\n"
        "Backend Engineer, Company A | Jan 2022 - Dec 2022\nBuilt systems.\n"
        "Backend Engineer, Company A | Jan 2022 - Dec 2022\nBuilt systems again.\n"
        "Freelance Developer | Dec 2021 - Nov 2020\nDid freelance work.\n"
    )
    report = check_credibility(resume)
    assert report.status == "review"
    banned_words = ["lie", "lied", "lying", "fraud", "fabricat", "fake", "dishonest"]
    for f in report.flags:
        lowered = f.message.lower()
        for word in banned_words:
            assert word not in lowered, f"Flag used accusatory language: {f.message}"

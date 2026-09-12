"""Smart Shortlisting Engine — Streamlit UI.

Upload a JD + a batch of resumes (PDF), or use Demo Mode with the bundled
sample data, and get a ranked, explainable shortlist. Everything runs
locally — no API keys, no network calls at runtime.
"""
import streamlit as st

from config import SAMPLE_DATA_DIR
from src.bias_detector import detect_bias
from src.document_loader import load_document
from src.explanation import compare_candidates, explain_candidate, format_explanation_text, status_label
from src.jd_parser import parse_jd
from src.ranker import rank_candidates
from src.recruiter_chat import answer_question
from src.resume_parser import parse_resume_sections
from src.text_cleaner import clean_text
from src.utils import identifier_from_filename

st.set_page_config(page_title="Smart Shortlisting Engine", layout="wide")


def _load_jd(file_bytes: bytes, name: str):
    parsed = load_document(file_bytes, source_name=name)
    if not parsed.ok:
        return None, parsed.error
    cleaned = clean_text(parsed.text).original_text
    return parse_jd(cleaned), None


def _load_resume(file_bytes: bytes, name: str):
    parsed = load_document(file_bytes, source_name=name)
    if not parsed.ok:
        return None, parsed.error
    cleaned = clean_text(parsed.text).original_text
    return parse_resume_sections(cleaned), None


def _run_pipeline(jd_bytes, jd_name, resume_files):
    jd, jd_error = _load_jd(jd_bytes, jd_name)
    if jd_error:
        st.error(f"Could not parse the Job Description: {jd_error}")
        return None, None, None

    resumes, identifiers, failures = [], [], []
    for file_bytes, name in resume_files:
        resume, error = _load_resume(file_bytes, name)
        if error:
            failures.append((name, error))
            continue
        resumes.append(resume)
        identifiers.append(resume.name or identifier_from_filename(name))

    if not resumes:
        st.error("No resumes could be parsed. Please check the uploaded files.")
        return None, None, None

    if failures:
        with st.expander(f"⚠ {len(failures)} resume(s) could not be processed", expanded=False):
            for name, error in failures:
                st.write(f"- **{name}**: {error}")

    ranked = rank_candidates(jd, resumes, identifiers)
    return jd, ranked, failures


def _load_demo_files():
    jd_path = SAMPLE_DATA_DIR / "sample_jd.pdf"
    resumes_dir = SAMPLE_DATA_DIR / "sample_resumes"
    jd_bytes = jd_path.read_bytes()
    resume_files = [
        (p.read_bytes(), p.name) for p in sorted(resumes_dir.glob("*.pdf"))
    ]
    return jd_bytes, jd_path.name, resume_files


def _load_stress_test_files():
    jd_path = SAMPLE_DATA_DIR / "real_dataset" / "sde_jd.pdf"
    resumes_dir = SAMPLE_DATA_DIR / "real_dataset" / "resumes"
    jd_bytes = jd_path.read_bytes()
    resume_files = [
        (p.read_bytes(), p.name)
        for p in sorted(resumes_dir.glob("*"))
        if p.suffix.lower() in (".pdf", ".docx")
    ]
    return jd_bytes, jd_path.name, resume_files


# ----------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------
st.title("Smart Shortlisting Engine")
st.caption(
    "Ranks resumes against a job description using local, hybrid keyword + semantic "
    "matching — no LLM in the scoring loop, no API key, runs fully offline."
)

if "ranked" not in st.session_state:
    st.session_state.ranked = None
    st.session_state.jd = None

# ----------------------------------------------------------------------
# Upload / Demo
# ----------------------------------------------------------------------
col_jd, col_resumes = st.columns(2)
with col_jd:
    st.subheader("1. Upload Job Description")
    jd_file = st.file_uploader("Job Description (PDF or DOCX)", type=["pdf", "docx"], key="jd_upload")
with col_resumes:
    st.subheader("2. Upload Resumes")
    resume_upload_files = st.file_uploader(
        "Resumes (PDF or DOCX, multiple)", type=["pdf", "docx"], accept_multiple_files=True, key="resume_upload"
    )

demo_choice = st.radio(
    "Or use bundled data instead of uploading:",
    [
        "Upload my own files",
        "Curated demo (1 JD + 6 sample resumes)",
        "Stress test (1 JD + 220 real resumes across ~25 unrelated roles)",
    ],
    index=0,
)

run_clicked = st.button("RUN SHORTLISTING", type="primary")

if run_clicked:
    if demo_choice.startswith("Curated"):
        jd_bytes, jd_name, resume_files = _load_demo_files()
    elif demo_choice.startswith("Stress"):
        jd_bytes, jd_name, resume_files = _load_stress_test_files()
    else:
        if jd_file is None:
            st.error("Please upload a Job Description file, or pick a bundled dataset above.")
            st.stop()
        if not resume_upload_files:
            st.error("Please upload at least one resume file, or pick a bundled dataset above.")
            st.stop()
        jd_bytes = jd_file.getvalue()
        jd_name = jd_file.name
        resume_files = [(f.getvalue(), f.name) for f in resume_upload_files]

    with st.spinner("Parsing documents and computing matches..."):
        jd, ranked, failures = _run_pipeline(jd_bytes, jd_name, resume_files)

    st.session_state.jd = jd
    st.session_state.ranked = ranked

# ----------------------------------------------------------------------
# Results
# ----------------------------------------------------------------------
jd = st.session_state.jd
ranked = st.session_state.ranked

if jd and ranked:
    st.divider()
    st.subheader(f"Job: {jd.job_title}")
    st.write(
        f"**Required skills ({len(jd.required_skills)}):** "
        + ", ".join(s.replace('_', ' ').title() for s in jd.required_skills)
    )
    if jd.preferred_skills:
        st.write(
            f"**Preferred skills ({len(jd.preferred_skills)}):** "
            + ", ".join(s.replace('_', ' ').title() for s in jd.preferred_skills)
        )

    bias_flags = detect_bias(jd.full_text)
    if bias_flags:
        with st.expander(f"🔎 Bonus: {len(bias_flags)} potentially narrow phrasing flag(s) in this JD"):
            st.caption("Rule-based flags for human review — not legal conclusions, and they never affect ranking.")
            for flag in bias_flags:
                st.write(f"- \"**{flag.matched_text}**\" — {flag.note}")

    st.divider()
    st.header("Ranked Candidates")
    table_rows = []
    for c in ranked:
        table_rows.append({
            "Rank": c.rank,
            "Candidate": c.identifier,
            "Final Score": c.score.final_score,
            "Semantic Match": round(c.score.semantic_component * 100, 1),
            "Keyword Match": round(c.features.keyword_result.keyword_score * 100, 1),
            "Required Skills": f"{round(c.score.required_skill_component * 100)}%",
            "Status": status_label(c.score.final_score),
        })
    st.dataframe(table_rows, use_container_width=True, hide_index=True)

    st.divider()
    st.header("Top 3 Candidates")
    for c in ranked[:3]:
        exp = explain_candidate(c)
        with st.container(border=True):
            st.subheader(f"#{c.rank} — {c.identifier} — Score {c.score.final_score}")
            st.write(exp.why)
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Matched Required Skills**")
                st.write(", ".join(exp.matched_required) if exp.matched_required else "_None_")
                st.markdown("**Matched Preferred Skills**")
                st.write(", ".join(exp.matched_preferred) if exp.matched_preferred else "_None_")
            with col_b:
                st.markdown("**Missing Required Skills**")
                st.write(", ".join(exp.missing_required) if exp.missing_required else "_None — full coverage_")
                st.markdown("**Score Breakdown**")
                for k, v in exp.score_breakdown.items():
                    st.write(f"{k}: {v}%")
            if exp.relevant_experience_snippet or exp.relevant_project_snippet:
                st.markdown("**Relevant Experience / Projects**")
                if exp.relevant_experience_snippet:
                    st.caption(exp.relevant_experience_snippet)
                if exp.relevant_project_snippet:
                    st.caption(exp.relevant_project_snippet)

    st.divider()
    st.header("Candidate Detail View")
    identifiers = [c.identifier for c in ranked]
    selected_id = st.selectbox("Select a candidate", identifiers, key="detail_select")
    selected = next(c for c in ranked if c.identifier == selected_id)
    exp = explain_candidate(selected)
    st.write(f"**Rank:** {selected.rank}  |  **Final Score:** {selected.score.final_score}")
    st.write("**Score breakdown:**")
    st.write(exp.score_breakdown)
    st.write("**Matched required skills:**", ", ".join(exp.matched_required) or "None")
    st.write("**Missing required skills:**", ", ".join(exp.missing_required) or "None")
    st.write("**Matched preferred skills:**", ", ".join(exp.matched_preferred) or "None")
    st.text_area("Relevant experience (from resume)", selected.resume.section("experience") or "(none detected)", height=100)
    st.text_area("Relevant projects (from resume)", selected.resume.section("projects") or "(none detected)", height=100)

    st.divider()
    st.header("Compare Candidates")
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        cand_a_id = st.selectbox("Candidate A", identifiers, index=0, key="cmp_a")
    with col2:
        default_b = 1 if len(identifiers) > 1 else 0
        cand_b_id = st.selectbox("Candidate B", identifiers, index=default_b, key="cmp_b")
    with col3:
        st.write("")
        compare_clicked = st.button("COMPARE")

    if compare_clicked:
        cand_a = next(c for c in ranked if c.identifier == cand_a_id)
        cand_b = next(c for c in ranked if c.identifier == cand_b_id)
        result = compare_candidates(cand_a, cand_b)
        st.info(result.verdict)
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**Where {cand_a_id} is stronger:**")
            for w in result.a_wins:
                st.write(f"- {w}")
            if not result.a_wins:
                st.write("_Nothing_")
        with col_b:
            st.markdown(f"**Where {cand_b_id} is stronger:**")
            for w in result.b_wins:
                st.write(f"- {w}")
            if not result.b_wins:
                st.write("_Nothing_")

    st.divider()
    st.header("Recruiter Chat (bonus)")
    st.caption(
        "Ask e.g. \"Why is <candidate> ranked above <candidate>?\" or \"Tell me about <candidate>\" — "
        "answered deterministically from the computed ranking data, no LLM."
    )
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    with st.form("chat_form", clear_on_submit=True):
        question = st.text_input(
            "Your question",
            placeholder=f"Why is {ranked[0].identifier} ranked above {ranked[-1].identifier}?",
        )
        asked = st.form_submit_button("ASK")

    if asked and question.strip():
        answer = answer_question(question, ranked)
        st.session_state.chat_history.append((question, answer.text))

    for q, a in reversed(st.session_state.chat_history):
        st.markdown(f"**You:** {q}")
        st.markdown(f"**Assistant:** {a}")
        st.markdown("")

    st.divider()
    with st.expander("How does the score get calculated?"):
        st.markdown("""
**Pipeline (rule-based steps are labeled RULE-BASED; learned steps are labeled ML/NLP):**

1. **PDF parsing** (RULE-BASED) — PyMuPDF extracts raw text from the JD and each resume.
2. **Text cleaning** (RULE-BASED) — normalization while preserving the original text for explanations.
3. **Section detection** (RULE-BASED) — maps varied headings ("Technical Skills", "Experience", ...) to a common schema.
4. **JD parsing** (RULE-BASED) — extracts required/preferred skills, responsibilities, qualifications.
5. **Keyword matching** (RULE-BASED) — exact/alias skill matching against a local skill dictionary + TF-IDF over technical terms.
6. **Semantic matching** (ML/NLP) — local sentence-transformer embeddings (all-MiniLM-L6-v2), section-level cosine similarity.
7. **Feature engineering** (RULE-BASED) — combines keyword + semantic outputs into one feature vector.
8. **ML relevance model** (ML/NLP) — a locally trained RandomForest/HistGradientBoosting regressor predicts an additional relevance signal from the feature vector.
9. **Final weighted score** (RULE-BASED, `config.py`) — a transparent, configurable weighted blend of the components above, 0-100.
10. **Explanations** (RULE-BASED templates) — every claim is read directly from the computed match data, never invented.

No LLM is used anywhere in this scoring loop.
""")
else:
    st.info("Upload a Job Description and resumes (or enable demo mode) and click RUN SHORTLISTING.")

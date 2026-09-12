"""FastAPI backend for the Smart Shortlisting Engine. Thin HTTP layer over
src/* — all matching/scoring/credibility/verification logic lives there,
unchanged and UI-agnostic; this file only does upload handling, session
state, candidate<->document association, and JSON serialization. No LLM
calls anywhere.
"""
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.serializers import (
    serialize_candidate, serialize_chat_answer, serialize_comparison,
    serialize_job, serialize_requirement_matrix_row, serialize_search_result,
    serialize_supporting_document,
)
from config import SAMPLE_DATA_DIR
from src.bias_detector import detect_bias
from src.credibility_checker import check_credibility
from src.dedup import dedupe_ranked_candidates
from src.document_loader import load_document
from src.document_verification import (
    _names_match, combine_with_credibility_flags, extract_supporting_document,
    overall_verification_status, unsupported_certification_claims, verify_supporting_document,
)
from src.explanation import compare_candidates
from src.jd_parser import parse_jd
from src.ranker import rank_candidates
from src.recruiter_chat import answer_question
from src.recruiter_search import search_candidates
from src.requirement_matrix import build_candidate_row
from src.resume_parser import parse_resume_sections
from src.text_cleaner import clean_text
from src.utils import identifier_from_filename

app = FastAPI(title="Smart Shortlisting Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5180", "http://127.0.0.1:5180"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store — appropriate for a single-process demo/hackathon
# backend. Each session holds the parsed JD, the deduped/ranked candidate
# list, uploaded supporting documents (grouped per candidate), and a
# recruiter review log (session-scoped audit trail: which flags have been
# marked reviewed, by whom, when) so /compare, /chat, /search, /review can
# reuse it without re-uploading or re-computing anything.
_SESSIONS: Dict[str, dict] = {}


class CompareRequest(BaseModel):
    session_id: str
    candidate_a: str
    candidate_b: str


class ChatRequest(BaseModel):
    session_id: str
    question: str


class SearchRequest(BaseModel):
    session_id: str
    query: str


class ReviewRequest(BaseModel):
    session_id: str
    candidate_id: str
    flag_message: str
    reviewer: str = "recruiter"
    resolution: str = ""


def _get_session(session_id: str) -> dict:
    session = _SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Unknown or expired session_id — run shortlisting again.")
    return session


def _associate_documents_with_candidates(supporting_doc_items: List[tuple], ranked: List) -> tuple:
    """Best-effort name matching — each uploaded supporting document is
    associated with the candidate whose resume name it agrees with. A
    document that can't be confidently matched to anyone is reported back
    as unassociated rather than silently guessed onto the wrong candidate."""
    by_candidate: Dict[str, list] = {c.identifier: [] for c in ranked}
    unassociated = []

    for file_bytes, name in supporting_doc_items:
        parsed = load_document(file_bytes, source_name=name)
        if not parsed.ok:
            unassociated.append({"filename": name, "error": parsed.error})
            continue
        doc = extract_supporting_document(clean_text(parsed.text).original_text, name)

        matched_candidate = None
        if doc.candidate_name:
            for c in ranked:
                if c.resume.name and _names_match(c.resume.name, doc.candidate_name):
                    matched_candidate = c
                    break
        if matched_candidate:
            by_candidate[matched_candidate.identifier].append(doc)
        else:
            unassociated.append({"filename": name, "error": "Could not confidently match this document to any uploaded candidate by name."})

    return by_candidate, unassociated


def _run_pipeline(
    jd_bytes: bytes,
    jd_name: str,
    resume_items: List[tuple],
    supporting_doc_items: Optional[List[tuple]] = None,
) -> dict:
    jd_parsed = load_document(jd_bytes, source_name=jd_name)
    if not jd_parsed.ok:
        raise HTTPException(status_code=400, detail=f"Could not parse Job Description: {jd_parsed.error}")
    jd = parse_jd(clean_text(jd_parsed.text).original_text)

    resumes, identifiers, failures = [], [], []
    for file_bytes, name in resume_items:
        parsed = load_document(file_bytes, source_name=name)
        if not parsed.ok:
            failures.append({"name": name, "error": parsed.error})
            continue
        resume = parse_resume_sections(clean_text(parsed.text).original_text)
        resumes.append(resume)
        identifiers.append(resume.name or identifier_from_filename(name))

    if not resumes:
        raise HTTPException(status_code=400, detail="No resumes could be parsed.")

    ranked = rank_candidates(jd, resumes, identifiers)
    deduped, duplicate_map = dedupe_ranked_candidates(ranked)

    documents_by_candidate, unassociated_documents = (
        _associate_documents_with_candidates(supporting_doc_items, deduped) if supporting_doc_items else ({}, [])
    )

    session_id = str(uuid.uuid4())
    verification_cache: Dict[str, dict] = {}
    _SESSIONS[session_id] = {
        "jd": jd, "ranked": deduped, "reviews": {}, "verification": verification_cache,
        "duplicate_map": duplicate_map,
    }

    bias_flags = detect_bias(jd.full_text)
    candidates_json = []
    matrix_rows_json = []
    for c in deduped:
        matched_required = c.features.keyword_result.matched_required if c.features.keyword_result else []
        base_report = check_credibility(c.resume, matched_required)
        candidate_docs = documents_by_candidate.get(c.identifier, [])

        doc_flags = []
        doc_pairs = []
        for doc in candidate_docs:
            flags = verify_supporting_document(c.resume, doc)
            doc_flags += flags
            doc_pairs.append((doc, flags))
        doc_flags += unsupported_certification_claims(c.resume.raw_text, candidate_docs)

        status, combined_flags = combine_with_credibility_flags(base_report.flags, doc_flags)
        verification_cache[c.identifier] = {"flags": combined_flags, "documents": doc_pairs}

        reviewed = {}  # brand-new session — nothing reviewed yet
        doc_json_list = [serialize_supporting_document(doc, flags, reviewed) for doc, flags in doc_pairs]
        candidates_json.append(serialize_candidate(
            c, status, combined_flags, reviewed, duplicate_map.get(c.identifier), doc_json_list,
        ))

        matrix_row = build_candidate_row(c.identifier, c.resume, c.features.keyword_result, jd)
        matrix_rows_json.append(serialize_requirement_matrix_row(matrix_row))

    return {
        "session_id": session_id,
        "job": serialize_job(jd, bias_flags),
        "candidates": candidates_json,
        "failures": failures,
        "duplicate_groups_collapsed": len(duplicate_map),
        "unassociated_documents": unassociated_documents,
        "requirement_matrix": {
            "requirements": [
                {"skill": s, "display_name": s.replace("_", " ").title(), "importance": "must_have"}
                for s in jd.required_skills
            ] + [
                {"skill": s, "display_name": s.replace("_", " ").title(), "importance": "preferred"}
                for s in jd.preferred_skills
            ],
            "rows": matrix_rows_json,
        },
    }


@app.post("/api/rank")
async def rank(
    jd_file: UploadFile = File(...),
    resume_files: List[UploadFile] = File(...),
    supporting_docs: List[UploadFile] = File(default=[]),
):
    jd_bytes = await jd_file.read()
    resume_items = [(await f.read(), f.filename) for f in resume_files]
    supporting_items = [(await f.read(), f.filename) for f in supporting_docs] if supporting_docs else []
    return _run_pipeline(jd_bytes, jd_file.filename, resume_items, supporting_items)


def _demo_files(subdir: Optional[str] = None):
    if subdir == "stress_test":
        jd_path = SAMPLE_DATA_DIR / "real_dataset" / "sde_jd.pdf"
        resumes_dir = SAMPLE_DATA_DIR / "real_dataset" / "resumes"
        paths = sorted(p for p in resumes_dir.glob("*") if p.suffix.lower() in (".pdf", ".docx"))
    else:
        jd_path = SAMPLE_DATA_DIR / "sample_jd.pdf"
        resumes_dir = SAMPLE_DATA_DIR / "sample_resumes"
        paths = sorted(resumes_dir.glob("*.pdf"))
    jd_bytes = jd_path.read_bytes()
    resume_items = [(p.read_bytes(), p.name) for p in paths]
    return jd_bytes, jd_path.name, resume_items


@app.post("/api/demo/{which}")
def run_demo(which: str):
    if which not in ("curated", "stress_test"):
        raise HTTPException(status_code=400, detail="which must be 'curated' or 'stress_test'")
    jd_bytes, jd_name, resume_items = _demo_files(which)
    return _run_pipeline(jd_bytes, jd_name, resume_items)


@app.post("/api/compare")
def compare(req: CompareRequest):
    session = _get_session(req.session_id)
    ranked = session["ranked"]
    cand_a = next((c for c in ranked if c.identifier == req.candidate_a), None)
    cand_b = next((c for c in ranked if c.identifier == req.candidate_b), None)
    if not cand_a or not cand_b:
        raise HTTPException(status_code=404, detail="One or both candidate identifiers not found in this session.")
    result = compare_candidates(cand_a, cand_b)
    return serialize_comparison(result)


@app.post("/api/chat")
def chat(req: ChatRequest):
    session = _get_session(req.session_id)
    answer = answer_question(req.question, session["ranked"])
    return serialize_chat_answer(answer)


@app.post("/api/search")
def search(req: SearchRequest):
    session = _get_session(req.session_id)
    results = search_candidates(req.query, session["ranked"])
    return {"results": [serialize_search_result(r) for r in results]}


@app.post("/api/review")
def mark_reviewed(req: ReviewRequest):
    """Recruiter verification workflow audit trail (session-scoped — see
    module docstring). Marking a flag reviewed doesn't change any score or
    remove the flag; it just records that a human has looked at it."""
    session = _get_session(req.session_id)
    reviews = session["reviews"].setdefault(req.candidate_id, {})
    reviews[req.flag_message] = {
        "reviewer": req.reviewer,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resolution": req.resolution,
    }
    return {"status": "recorded", "reviewed_at": reviews[req.flag_message]["timestamp"]}


@app.get("/api/candidates/{session_id}")
def get_candidates(session_id: str):
    """Re-serializes candidates from cached verification data (no
    recomputation) — used after /api/review so the frontend can show
    updated 'reviewed' markers without re-running the whole pipeline."""
    session = _get_session(session_id)
    duplicate_map = session["duplicate_map"]
    result = []
    for c in session["ranked"]:
        cached = session["verification"][c.identifier]
        reviewed = session["reviews"].get(c.identifier, {})
        status = overall_verification_status(cached["flags"])
        doc_json_list = [serialize_supporting_document(doc, flags, reviewed) for doc, flags in cached["documents"]]
        result.append(serialize_candidate(
            c, status, cached["flags"], reviewed, duplicate_map.get(c.identifier), doc_json_list,
        ))
    return {"candidates": result}


@app.get("/api/health")
def health():
    return {"status": "ok"}

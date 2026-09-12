"""Converts internal dataclasses (src/*) into plain JSON-serializable
dicts for the API layer. Kept separate from src/ so the core pipeline
stays UI/API-agnostic."""
from typing import Dict, List, Optional

from src.bias_detector import BiasFlag
from src.credibility_checker import CredibilityReport
from src.document_verification import SupportingDocument, VerificationFlag
from src.explanation import CandidateExplanation, ComparisonResult, explain_candidate, status_label
from src.jd_parser import ParsedJD
from src.ranker import RankedCandidate
from src.recruiter_chat import ChatAnswer
from src.recruiter_search import SearchResult
from src.requirement_matrix import CandidateMatrixRow

_VERIFICATION_STATUS_LABELS = {
    "clean": "✓ No inconsistencies detected",
    "review_recommended": "⚠️ Review Recommended",
    "verification_required": "⚠️ Verification Required",
}

_MATRIX_STATUS_EMOJI = {"strong": "🟢", "partial": "🟡", "missing": "🔴"}


def serialize_bias_flag(flag: BiasFlag) -> dict:
    return {"matched_text": flag.matched_text, "note": flag.note}


def serialize_job(jd: ParsedJD, bias_flags: List[BiasFlag]) -> dict:
    return {
        "job_title": jd.job_title,
        "required_skills": jd.required_skills,
        "preferred_skills": jd.preferred_skills,
        "bias_flags": [serialize_bias_flag(f) for f in bias_flags],
    }


def serialize_credibility(report: CredibilityReport) -> dict:
    return {
        "status": report.status,
        "status_label": report.status_label,
        "flags": [{"severity": f.severity, "message": f.message} for f in report.flags],
    }


def serialize_verification_flag(flag: VerificationFlag, reviewed_set: set) -> dict:
    return {
        "severity": flag.severity,
        "message": flag.message,
        "reviewed": flag.message in reviewed_set,
    }


def serialize_supporting_document(doc: SupportingDocument, flags: List[VerificationFlag], reviewed_set: set) -> dict:
    return {
        "filename": doc.filename,
        "document_type": doc.document_type,
        "organization": doc.organization,
        "role_or_degree": doc.role_or_degree,
        "credential_id": doc.credential_id,
        "verification_url": doc.verification_url,
        "flags": [serialize_verification_flag(f, reviewed_set) for f in flags],
    }


def serialize_requirement_matrix_row(row: CandidateMatrixRow) -> dict:
    return {
        "identifier": row.identifier,
        "overall_coverage_score": row.overall_coverage_score,
        "cells": [
            {
                "requirement": e.requirement,
                "display_name": e.display_name,
                "importance": e.importance,
                "status": e.status,
                "emoji": _MATRIX_STATUS_EMOJI[e.status],
                "score": e.score,
                "confidence": e.confidence,
                "evidence_text": e.evidence_text,
                "evidence_source": e.evidence_source,
                "reasoning": e.reasoning,
            }
            for e in row.evaluations
        ],
    }


def serialize_candidate(
    candidate: RankedCandidate,
    verification_status: str,
    verification_flags: List[VerificationFlag],
    reviewed_set: set,
    duplicate_of: Optional[List[str]] = None,
    supporting_documents: Optional[List[dict]] = None,
) -> dict:
    exp: CandidateExplanation = explain_candidate(candidate)
    kw = candidate.features.keyword_result
    return {
        "identifier": candidate.identifier,
        "rank": candidate.rank,
        "final_score": candidate.score.final_score,
        "status": status_label(candidate.score.final_score),
        "score_breakdown": exp.score_breakdown,
        "matched_required": exp.matched_required,
        "missing_required": exp.missing_required,
        "matched_preferred": exp.matched_preferred,
        "why": exp.why,
        "relevant_experience_snippet": exp.relevant_experience_snippet,
        "relevant_project_snippet": exp.relevant_project_snippet,
        "relevant_experience_full": candidate.resume.section("experience"),
        "relevant_projects_full": candidate.resume.section("projects"),
        "all_resume_skills": kw.all_resume_skills if kw else [],
        "duplicates": duplicate_of or [],
        "verification": {
            "status": verification_status,
            "status_label": _VERIFICATION_STATUS_LABELS[verification_status],
            "flags": [serialize_verification_flag(f, reviewed_set) for f in verification_flags],
            "supporting_documents": supporting_documents or [],
        },
    }


def serialize_comparison(result: ComparisonResult) -> dict:
    return {
        "a_identifier": result.a_identifier,
        "b_identifier": result.b_identifier,
        "a_wins": result.a_wins,
        "b_wins": result.b_wins,
        "verdict": result.verdict,
    }


def serialize_chat_answer(answer: ChatAnswer) -> dict:
    return {"text": answer.text, "matched_candidates": answer.matched_candidates}


def serialize_search_result(result: SearchResult) -> dict:
    return {
        "identifier": result.candidate.identifier,
        "rank": result.candidate.rank,
        "final_score": result.candidate.score.final_score,
        "matched_query_skills": result.matched_query_skills,
        "missing_query_skills": result.missing_query_skills,
        "query_coverage": result.query_coverage,
    }

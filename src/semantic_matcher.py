"""Semantic matching via local sentence embeddings (sentence-transformers,
all-MiniLM-L6-v2 — runs on CPU, no API key). Deliberately does section-level
comparison rather than one whole-JD-vs-whole-resume embedding, so a resume
project described in different words than the JD can still score well
against the *relevant* JD section instead of being diluted by the whole
document."""
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Tuple

# The embedding model is downloaded once during setup (see README); at
# runtime we force offline mode so a live demo never depends on network
# access or an API key.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import numpy as np
from sentence_transformers import SentenceTransformer

from config import SEMANTIC_MODEL_NAME, SEMANTIC_SECTION_WEIGHTS
from src.jd_parser import ParsedJD
from src.resume_parser import ParsedResume

_embedding_cache: Dict[str, np.ndarray] = {}


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(SEMANTIC_MODEL_NAME)


def _split_into_chunks(text: str) -> List[str]:
    """Split a section's text into sentence/bullet-sized chunks for
    finer-grained semantic comparison."""
    if not text or not text.strip():
        return []
    raw_chunks = re.split(r"[\n]|(?<=[.!?])\s+", text)
    chunks = [c.strip() for c in raw_chunks if len(c.strip()) > 3]
    return chunks or [text.strip()]


def _embed(texts: List[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, _get_model().get_sentence_embedding_dimension()))
    uncached = [t for t in texts if t not in _embedding_cache]
    if uncached:
        vectors = _get_model().encode(uncached, normalize_embeddings=True, show_progress_bar=False)
        for t, v in zip(uncached, vectors):
            _embedding_cache[t] = v
    return np.array([_embedding_cache[t] for t in texts])


def best_matching_chunk(query: str, text: str) -> Tuple[float, str]:
    """Public helper: embeds `query` against every chunk of `text` and
    returns (best_cosine_similarity, that_chunk). Used wherever a single
    concept needs to be checked against a block of resume text with an
    evidence snippet attached (e.g. the requirement coverage matrix)."""
    target_chunks = _split_into_chunks(text)
    if not target_chunks:
        return 0.0, ""
    query_vec = _embed([query])
    target_vecs = _embed(target_chunks)
    sims = (query_vec @ target_vecs.T)[0]
    best_idx = int(sims.argmax())
    return float(max(0.0, min(1.0, sims[best_idx]))), target_chunks[best_idx]


def _best_match_similarity(query_chunks: List[str], target_chunks: List[str]) -> float:
    """For each query chunk, find its best-matching target chunk (cosine
    similarity), then average across query chunks. This rewards a resume
    that covers the JD's asks even if phrased differently, without letting
    one great match hide many unaddressed JD points."""
    if not query_chunks or not target_chunks:
        return 0.0
    query_vecs = _embed(query_chunks)
    target_vecs = _embed(target_chunks)
    sim_matrix = query_vecs @ target_vecs.T  # both normalized -> cosine sim
    best_per_query = sim_matrix.max(axis=1)
    score = float(best_per_query.mean())
    return max(0.0, min(1.0, score))


@dataclass
class SemanticMatchResult:
    semantic_overall: float = 0.0
    semantic_experience: float = 0.0
    semantic_projects: float = 0.0
    semantic_skills_context: float = 0.0
    semantic_education: float = 0.0
    semantic_responsibilities: float = 0.0
    semantic_qualifications: float = 0.0
    component_scores: Dict[str, float] = field(default_factory=dict)


def match_semantics(jd: ParsedJD, resume: ParsedResume) -> SemanticMatchResult:
    jd_responsibility_chunks = _split_into_chunks(jd.responsibilities) or _split_into_chunks(jd.full_text)
    jd_qualification_chunks = _split_into_chunks(jd.qualifications)
    jd_skill_context_chunks = [jd.job_title] + jd.required_skills + jd.preferred_skills

    resume_sections = {
        "experience": _split_into_chunks(resume.section("experience")),
        "projects": _split_into_chunks(resume.section("projects")),
        "skills": _split_into_chunks(resume.section("skills")),
        "education": _split_into_chunks(resume.section("education")),
    }

    semantic_experience = _best_match_similarity(jd_responsibility_chunks, resume_sections["experience"])
    semantic_projects = _best_match_similarity(jd_responsibility_chunks, resume_sections["projects"])
    semantic_skills_context = _best_match_similarity(jd_skill_context_chunks, resume_sections["skills"])
    semantic_education = (
        _best_match_similarity(jd_qualification_chunks, resume_sections["education"])
        if jd_qualification_chunks else 0.0
    )
    semantic_responsibilities = max(semantic_experience, semantic_projects)
    semantic_qualifications = semantic_education

    weights = SEMANTIC_SECTION_WEIGHTS
    section_scores = {
        "experience": semantic_experience,
        "projects": semantic_projects,
        "skills": semantic_skills_context,
        "education": semantic_education,
    }
    total_weight = sum(weights[k] for k in section_scores if resume_sections.get(k))
    if total_weight > 0:
        semantic_overall = sum(
            weights[k] * v for k, v in section_scores.items() if resume_sections.get(k)
        ) / total_weight
    else:
        semantic_overall = 0.0

    return SemanticMatchResult(
        semantic_overall=round(semantic_overall, 4),
        semantic_experience=round(semantic_experience, 4),
        semantic_projects=round(semantic_projects, 4),
        semantic_skills_context=round(semantic_skills_context, 4),
        semantic_education=round(semantic_education, 4),
        semantic_responsibilities=round(semantic_responsibilities, 4),
        semantic_qualifications=round(semantic_qualifications, 4),
        component_scores=section_scores,
    )

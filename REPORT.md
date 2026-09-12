# Smart Shortlisting Engine — One-Page Report

**InternLoom AI Hackathon — Manipal Institute of Technology**

## Problem

Rank a pool of resumes against one Job Description with a system that
*genuinely* performs the matching — not an LLM asked to "score this resume."
The ranking must be explainable: which skills matched, which are missing,
and why one candidate outranks another.

## Solution

A fully local, offline pipeline — **no LLM in the scoring loop, no API key**:

```
PDF/DOCX/Image → text extraction (OCR fallback) → JD & resume parsing
      → keyword matching (skill dictionary, typo-tolerant)
      → semantic matching (local sentence-transformer embeddings)
      → ML relevance model (locally trained RandomForest)
      → transparent weighted final score → ranking
      → deterministic, evidence-backed explanations
```

**Stack:** React 19 + TypeScript (Vite) frontend · Python/FastAPI backend ·
scikit-learn + sentence-transformers for matching · PyMuPDF/python-docx/
Tesseract for document extraction. A legacy Streamlit UI (`app.py`) also
ships as a single-file alternative over the same pipeline.

## Core Features

- **Hybrid ranking** — keyword + semantic + ML signals, weighted and
  configurable (`config.py`), never a bare keyword count.
- **Top-3 explanations** — matched/missing skills, relevant experience,
  full score breakdown, template-generated (never invented).
- **Candidate comparison & Recruiter Chat** — free-text questions ("Why is
  X ranked above Y?") answered deterministically from the same computed data.
- **Recruiter Search** — "Show me candidates with Python + SQL" filters the
  ranked pool by skill coverage.

## Bonus Features Implemented

| Feature | What it does |
|---|---|
| JD bias detector | Flags age-coded/exclusionary phrasing for human review |
| Messy-resume handling | Section-header aliasing, typo-tolerant skill matching, PDF/DOCX/OCR fallback |
| Redundant record detection | Collapses duplicate/near-identical resume submissions, keeps best-scoring copy |
| Resume Credibility Check | Timeline overlaps, reversed dates, duplicate entries, experience-claim mismatches — always "requires verification," never an accusation |
| Document & Claim Verification | Cross-checks resumes against uploaded certificates (name/company/date/role), credential ID extraction, session-scoped recruiter review audit trail |
| Requirement Coverage Matrix | Per-candidate × per-requirement 🟢/🟡/🔴 evaluation with confidence score and evidence snippet per cell — semantic, not keyword-only (Kubernetes only partially covers Docker; Java never satisfies JavaScript) |

## Validation

- **84 automated tests**, all passing, covering matching, scoring,
  credibility checks, document verification, and requirement evaluation.
- **Stress-tested** against 176 real resumes across ~25 unrelated job
  roles: SDE-adjacent candidates scored 40–67, genuinely unrelated roles
  (Sales, Video Editing, HR) correctly bottomed out at 6–10 — proving the
  ranking discriminates on substance, not superficial keyword overlap.
- Multiple real bugs were caught and fixed via this testing (fuzzy-match
  false positives, a skill-matcher substring bug, a name-comparison flaw)
  rather than left undiscovered.

## Honest Limitations

- Training data for the ML relevance component is synthetic (no real
  labeled resumes exist before the hackathon) — documented, not hidden.
- OCR requires a local Tesseract install; without it, image-based
  documents degrade gracefully with a clear message rather than failing
  silently or fabricating a result.
- No digital-signature verification or persistent (cross-restart) audit
  trail — both explicitly out of scope for a hackathon-timeline prototype.

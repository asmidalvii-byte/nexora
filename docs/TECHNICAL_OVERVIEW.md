# Smart Shortlisting Engine

Built for the **InternLoom AI Hackathon** at Manipal Institute of Technology.

## Project Overview

Takes one Job Description and a batch of resumes (PDF) and returns a ranked,
explainable shortlist: a final score per candidate, matched/missing skills,
and a natural-language-style explanation for the top 3 — computed by a local
hybrid keyword + semantic + ML pipeline, **no LLM in the scoring loop, no API
key, fully offline after one-time setup.**

## Problem

Campus placement platforms need to rank a pool of resumes against a single
job opening. A strong candidate rarely uses the JD's exact words, but explicit
required skills still matter. The ranking must be explainable, not a bare
number — and simply asking an LLM to "score this resume" does not count as
genuinely performing the matching.

## Solution

A pipeline that performs PDF parsing → text normalization → JD analysis →
skill extraction → keyword matching → semantic matching → feature engineering
→ ML relevance scoring → final weighted score → ranking → deterministic
explanations. See **Architecture** below.

## Two ways to run this

**Primary: React + TypeScript frontend, Python (FastAPI) backend.**
`backend/main.py` exposes the entire pipeline (including the credibility
checker, dedup, and recruiter search below) as a REST API; `frontend/` is a
Vite + React 19 + TypeScript SPA consuming it. See **Running the
Application** below.

**Legacy/alternate: Streamlit.** `app.py` is a self-contained single-file UI
over the same `src/` pipeline — no separate backend process needed. It does
not yet expose the credibility checker, dedup, or recruiter search (those
were added after it). Kept because it's genuinely simpler to demo if you
just want the core ranking flow with nothing else running: `streamlit run app.py`.

Both UIs call the exact same `src/*` modules — nothing about the scoring,
matching, or explanation logic differs between them.

## Bonus: Redundant Record Detection

`src/dedup.py` groups resumes that look like the same submission — same
email address, or near-identical resume text (handles the same resume
re-exported as PDF vs DOCX, which can extract with minor whitespace
differences). The best-scoring copy stays visible in the ranked list; the
rest are attached to it as "also submitted as" rather than occupying
separate ranks. Two identity-fooling edge cases are explicitly guarded
against (both found by testing against a real 220-resume dataset): a
shared placeholder email (`dummy.email@example.com`) doesn't force a merge
on its own, and two resumes with clearly different extracted names are
never merged even if their content is heavily templated/similar — a real
distinct person should never be collapsed into someone else's row.

## Bonus: Resume Credibility & Consistency Check

`src/date_parser.py` + `src/credibility_checker.py` — a **secondary**
signal shown alongside the match score, never folded into the ranking
itself and never a "fraud score." For each candidate it checks:

- Reversed dates (end before start) within one entry
- Overlapping employment entries (flagged as "potential overlap — may be
  legitimate," since internships/freelance/concurrent roles are normal;
  full-time overlaps in different cities get an extra note, but only when
  neither entry mentions "intern")
- Duplicate entries and conflicting dates for a similarly-named role
- A claimed "N years of experience" against the actual union of employment
  date ranges (open-ended "Present" roles resolve to today's date for this
  specific check only)
- A required skill listed in the Skills section with zero mention anywhere
  in Experience/Projects/Education — restricted to the JD's required
  skills for this candidate, and foundational/implied skills (HTML, CSS,
  JavaScript, Git, SQL, ...) are excluded, since those are almost never
  independently re-mentioned once a higher-level framework is cited and
  flagging them produced a false positive on nearly every real resume
  during testing

Every flag is phrased as "potential inconsistency," "timeline conflict," or
"requires verification" — never an accusation (`tests/test_credibility_checker.py::test_never_uses_accusatory_language`
enforces this). A resume with no issues shows "✓ No inconsistencies
detected."

## Bonus: Recruiter Search

`src/recruiter_search.py` — after a batch is ranked, a recruiter can type
"Show me candidates with Python + SQL + machine learning" and get the
already-ranked pool filtered/reordered by coverage of the queried skills
(extracted with the same skill dictionary as everywhere else — no LLM, no
new score).

## Architecture

```
JOB DESCRIPTION (PDF)                    RESUMES (PDF, batch)
        |                                        |
        v                                        v
   PDF PARSING (PyMuPDF)  <-------- shared -------->
        |                                        |
        v                                        v
   TEXT CLEANING (original_text preserved for explanations)
        |                                        |
        v                                        v
   JD PARSING                          RESUME SECTION DETECTION
   (required/preferred skills,         (Skills/Experience/Projects/
    responsibilities, quals)            Education, alias-mapped)
        |                                        |
        +--------------------+-------------------+
                             |
              +--------------+---------------+
              |                              |
              v                              v
     KEYWORD ENGINE                  SEMANTIC ENGINE
     (skill-dictionary alias         (sentence-transformers,
      matching + TF-IDF over          section-level cosine
      technical vocabulary)           similarity, local CPU model)
              |                              |
              +--------------+---------------+
                             v
                  FEATURE ENGINEERING
                  (16-feature vector, see below)
                             |
                             v
                  ML RELEVANCE MODEL
                  (RandomForestRegressor, trained on
                   synthetic data — see Training below)
                             |
                             v
                  FINAL WEIGHTED SCORE (0-100)
                  (config.py — semantic 35%, required skills 30%,
                   experience/projects 15%, preferred skills 10%,
                   ML relevance 10%)
                             |
                             v
                        RANKING
                             |
                             v
              TOP-3 EXPLANATION ENGINE (deterministic templates)
                             |
                             v
                       STREAMLIT UI
```

RULE-BASED vs ML/NLP, made explicit (no "fake AI" labeling):

| Step | Type |
|---|---|
| PDF parsing, text cleaning, section detection | RULE-BASED |
| JD parsing, skill dictionary matching, TF-IDF | RULE-BASED |
| Explanation templates, bias detector | RULE-BASED |
| Sentence embeddings (semantic matching) | ML/NLP (local, pre-trained) |
| Relevance model | ML/NLP (locally trained) |

## Installation

```bash
cd smart-shortlisting
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The first run of the app or training pipeline downloads the sentence-transformer
model (`all-MiniLM-L6-v2`, ~80MB) once from Hugging Face. After that, the app
sets `HF_HUB_OFFLINE=1` / `TRANSFORMERS_OFFLINE=1` internally and never makes a
network call again — safe for an offline demo.

## Running the Training Pipeline

The model ships pre-trained (`models/ranking_model.joblib`), but to regenerate:

```bash
python -m training.generate_training_data   # writes data/training_data.csv
python -m training.train_model              # trains + saves the model
python -m training.evaluate_model           # prints a metrics report
```

## Running the Application

### React + FastAPI (primary)

```bash
# Terminal 1 — backend (from the project root, with .venv activated)
uvicorn backend.main:app --port 8000

# Terminal 2 — frontend
cd frontend
npm install   # first time only
npm run dev -- --port 5180
```

Open http://localhost:5180. The backend must be running on port 8000 — the
frontend's API base URL (`frontend/src/api/client.ts`) is hardcoded to
`http://localhost:8000`, and CORS is locked to `http://localhost:5180` in
`backend/main.py`; change both together if you need different ports.

### Streamlit (legacy/alternate)

```bash
streamlit run app.py
```

Either way, upload a JD + resumes (PDF or DOCX), or pick one of two bundled datasets instead:

- **Curated demo** — 1 JD + 6 sample resumes (varying fit levels), regenerate with
  `python -m scripts.build_sample_pdfs`.
- **Stress test** — 1 SDE JD (`sample_data/real_dataset/sde_jd.txt`) ranked against
  220 real resumes spanning ~25 unrelated roles (`sample_data/real_dataset/resumes/`,
  mixed PDF/DOCX/TXT/XML — only PDF/DOCX are used). Demonstrates the scoring engine's
  discriminative range: SDE-adjacent candidates score 40-67, while genuinely
  unrelated roles (Sales, Video Editing, HR, ...) correctly bottom out at 6-10.

## How Keyword Matching Works

`src/skill_matcher.py` matches a local skill dictionary (`data/skills.json`,
~110 canonical skills with aliases) against resume/JD text using
word-boundary regex — not naive substring search, so "js" doesn't fire
inside "node.js" and bare "c" doesn't fire inside "c++"/"c#". `src/keyword_matcher.py`
computes required/preferred skill coverage (required weighted 3x more than
preferred — `KEYWORD_REQUIRED_WEIGHT`/`KEYWORD_PREFERRED_WEIGHT` in
`config.py`) plus a TF-IDF cosine similarity restricted to the technical-term
vocabulary.

## How Semantic Matching Works

`src/semantic_matcher.py` uses `sentence-transformers` (`all-MiniLM-L6-v2`,
384-dim, CPU) to embed JD responsibility/qualification chunks and resume
section chunks (experience/projects/skills/education) separately — not one
whole-document embedding — then takes, for each JD chunk, its best-matching
resume chunk (cosine similarity), averaged. This lets a resume phrase like
"Built backend APIs using Express.js and MongoDB" score well against a JD
line like "Develop REST APIs using Node.js and MongoDB" even without shared
exact wording.

## How the ML Model Works

See **Training** below for how the model was built. At inference time
(`src/scorer.py`), the trained model predicts a `ml_relevance` signal from
the 16-feature vector, contributing 10% to the final score — an additional,
independently-learned signal, not a restatement of the other components.

### Feature list (16 features, `src/feature_engineering.py`)

`semantic_overall, semantic_experience, semantic_projects,
semantic_skills_context, semantic_education, keyword_score,
required_skill_coverage, preferred_skill_coverage, tfidf_similarity,
skill_count, required_skill_count, matched_required_count,
missing_required_count, experience_relevance, project_relevance,
education_relevance`

### Training data (honest limitation, documented)

The hackathon's actual resumes only arrive on the day, so no real training
data can exist in advance regardless of approach. We generate **synthetic
feature vectors** directly (`training/generate_training_data.py`) —
HIGH/MEDIUM/LOW fit tiers with realistic per-tier distributions and noise —
rather than generating thousands of fake resume/JD text pairs through the
full NLP pipeline, which would be significant extra engineering for no
real gain in a fixed hackathon time budget. 3,000 examples, 80/20 train/val
split, fixed seed (42).

**Anti-leakage:** the synthetic label is generated with different weights
and a nonlinear threshold bonus/penalty than `config.SCORE_WEIGHTS` (which
`src/scorer.py` uses at inference time) — see the comment in
`generate_training_data.py`. If the label were just the final-score formula
reapplied to its own inputs, the model would trivially reproduce that
formula and add no independent signal.

Models tried: `LinearRegression`, `RandomForestRegressor`,
`HistGradientBoostingRegressor`. Selected by validation RMSE, tie-broken by
pairwise ranking accuracy (this is a ranking problem, not just a regression
one). Current validation results (`python -m training.evaluate_model`):

| Model | MAE | RMSE | Spearman | Pairwise ranking accuracy |
|---|---|---|---|---|
| RandomForestRegressor (selected) | ~4.8 | ~6.0 | ~0.97 | ~0.93 |
| HistGradientBoostingRegressor | ~4.9 | ~6.0 | ~0.97 | ~0.93 |
| LinearRegression | ~5.3 | ~6.6 | ~0.97 | ~0.93 |

## Scoring Formula

All weights live in `config.py` (`SCORE_WEIGHTS`), never scattered as magic
numbers:

```
final_score = 100 * (
    0.35 * semantic_overall
  + 0.30 * required_skill_coverage
  + 0.15 * max(experience_relevance, project_relevance)
  + 0.10 * preferred_skill_coverage
  + 0.10 * ml_relevance
)
```

These are our internal scoring weights — distinct from the hackathon's own
judging rubric.

## Explanation Generation

`src/explanation.py` — deterministic templates only, no LLM. Every matched/
missing skill comes directly from `KeywordMatchResult`; every "relevant
experience" snippet is a literal line quoted from the candidate's own resume
text. Nothing is inferred or invented. Also includes `compare_candidates()`
for the "why does A rank above B" recruiter question.

## Bonus Features

- **JD bias/narrow-phrasing detector** (`src/bias_detector.py`) — rule-based
  flags (age-coded language, gendered requirements, vague "culture fit",
  etc.) for human review. Never blocks or alters ranking.
- **Messy resume handling** — section-header aliasing tolerates varied
  headings ("Technical Expertise" → Skills, "Professional Experience" →
  Experience); a resume with no recognizable headers falls back to a single
  "summary" section rather than failing; PDF/DOCX extraction failures are
  isolated per-file so one bad resume doesn't take down the batch; skill
  matching tolerates plurals ("REST APIs") and single-character typos
  ("Pythom" → python, "Doker" → docker) via a conservative fuzzy pass
  (`src/skill_matcher.py`) that only runs on single-word aliases with no
  exact match, always labeled `fuzzy=True` so it stays traceable — it
  deliberately excludes short aliases and any token that is itself a real
  alias of another skill, to avoid cross-contamination (e.g. "css" is
  never treated as a typo of "scss").
- **Recruiter chat** (`src/recruiter_chat.py`) — a free-text question box
  ("Why is X ranked above Y?", "Tell me about X") answered by deterministic
  pattern matching + the same `compare_candidates`/`explain_candidate`
  logic used elsewhere — no LLM. An unmatched or ambiguous candidate name
  gets a clarifying message with close-name suggestions rather than a
  guess.
- **Candidate comparison** — see Explanation Generation above (also reachable
  via the recruiter chat).
- **Redundant record detection**, **Resume Credibility & Consistency Check**,
  and **Recruiter Search** — see their own sections above ("Two ways to run
  this" onward) for full detail; all three are wired into the React/FastAPI
  stack (not yet into the legacy Streamlit app).

## Testing

```bash
pytest tests/ -v
```

28 tests across keyword matching, semantic matching, scoring (including the
required non-negotiable tests: final score must change when semantic OR
keyword inputs change independently), parsing, and a full end-to-end
PDF-in → ranking-out flow with real generated PDFs (no shortcuts).

## Judge Demo Instructions

See [JUDGE_GUIDE.md](JUDGE_GUIDE.md).

## Limitations

- Skill dictionary (`data/skills.json`) is a curated ~110-skill list, not
  exhaustive — an unlisted skill won't be recognized by the keyword engine
  (though semantic matching can still partially cover it).
- Training data is synthetic (see above) — an honest, documented tradeoff
  given no real labeled resume data exists before the hackathon.
- Section detection relies on recognizable headings; a resume with zero
  headers degrades to whole-document matching via the "summary" fallback.
- Sentence-transformer embeddings for short technical phrases produce
  moderate (not near-1.0) cosine similarities even for strong matches — this
  is expected model behavior, not a scoring bug, and doesn't affect ranking
  order since all candidates are compared on the same scale.

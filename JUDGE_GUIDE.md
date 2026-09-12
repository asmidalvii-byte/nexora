# Judge Guide — Smart Shortlisting Engine

## 30-Second Explanation

We built a hybrid resume-ranking engine that combines explicit skill matching
with local semantic embeddings and a locally trained relevance model — never
an LLM asked to "score this resume." Upload a JD and a batch of resumes, and
it returns a ranked, explainable shortlist with a score breakdown and
matched/missing skills for every candidate, running fully offline with no
API key.

## 2-Minute Technical Explanation

The system does not send anything to an LLM to produce the score. Instead:

1. **Keyword engine** — extracts explicit skills from both the JD and each
   resume using a local skill dictionary with alias matching (so "ReactJS",
   "React.js", and "react js" all resolve to the same skill), then computes
   required-skill coverage (weighted heavily) and preferred-skill coverage
   (weighted lightly), plus a TF-IDF similarity over technical terms.
2. **Semantic engine** — uses a local sentence-embedding model
   (`all-MiniLM-L6-v2`, runs on CPU, no API) to compare JD responsibilities
   against resume experience/project sections at the *chunk* level, so a
   candidate who describes the same work in different words still scores
   well.
3. **Feature engineering + ML relevance model** — the outputs of both
   engines become a 16-feature vector fed into a `RandomForestRegressor`
   trained on synthetic HIGH/MEDIUM/LOW-fit examples, adding one more
   learned signal to the final score.
4. **Final score** — a transparent, configurable weighted blend of all of
   the above (never a black box), producing a 0-100 score with a component
   breakdown always visible.
5. **Explanations** — deterministic templates read directly from the
   computed match data; nothing is invented by an LLM.

## 5-Minute Deep Dive

Walk through, in order:

**PDF → parser** (`src/pdf_parser.py`): PyMuPDF extracts text; a malformed
PDF is caught and reported per-file, never crashes the batch.

**Text cleaning + section detection** (`src/text_cleaner.py`,
`src/resume_parser.py`, `src/jd_parser.py`): normalizes text while keeping
the original for explanations; maps varied real-world headings ("Technical
Expertise", "Professional Experience", ...) onto a common schema via
`config.SECTION_ALIASES` / `JD_SECTION_ALIASES`.

**Keyword engine** (`src/skill_matcher.py`, `src/keyword_matcher.py`):
word-boundary regex against `data/skills.json` — deliberately guards against
false positives like "js" matching inside "node.js", or bare "c" matching
inside "c++"/"c#". Required skills count 3x as much as preferred
(`config.KEYWORD_REQUIRED_WEIGHT` / `KEYWORD_PREFERRED_WEIGHT`).

**Semantic engine** (`src/semantic_matcher.py`): section-level embedding
comparison, not one whole-document embedding — this is the deliberate design
choice that lets differently-worded but equivalent experience score well.

**Feature engineering** (`src/feature_engineering.py`): the exact 16-feature
vector, shared identically between training and inference.

**ML model** (`training/train_model.py`, `src/scorer.py`): trained on
synthetic data (documented tradeoff — real hackathon resumes don't exist
until the day), evaluated on MAE/RMSE/Spearman/pairwise ranking accuracy,
selected among 3 candidate model families.

**Final scoring + ranking** (`src/scorer.py`, `src/ranker.py`): all weights
centralized in `config.py`; ranking sorts by score with deterministic tie-
breaking.

**Explanations** (`src/explanation.py`): top-3 templates plus a candidate
comparison function, all sourced from computed data only.

## Common Judge Questions

**"Are you just using an LLM?"**
No. There is no LLM call anywhere in the scoring loop. Everything from PDF
parsing to the final score is deterministic code or a small, locally-run
ML model we trained ourselves. We can point to the exact line of code that
produces every number on screen.

**"How does semantic matching work?"**
Local sentence-transformer embeddings (`all-MiniLM-L6-v2`) turn JD and
resume text chunks into 384-dimensional vectors; cosine similarity between
them measures meaning-level relatedness even when the wording differs. It
runs on CPU with no internet access at runtime.

**"How does keyword matching work?"**
A local skill dictionary (~110 skills, each with common aliases) is matched
against text using word-boundary-safe regex, plus TF-IDF cosine similarity
restricted to technical vocabulary. Required skills are weighted 3x
preferred skills.

**"Why do you need both?"**
Keyword matching catches explicit must-have tools the JD names literally;
semantic matching catches equivalent experience described in different
words. Either alone misses real candidates — a keyword-only system 100%
overlooks the second, a semantic-only system doesn't respect that specific
required tools were named for a reason. We have tests proving both
independently move the final score.

**"How did you train the model?"**
On synthetic feature vectors (not real resumes — none existed before the
hackathon), sampled across HIGH/MEDIUM/LOW fit tiers with realistic
correlations and noise. The training label uses different weights than our
runtime scoring formula specifically to avoid the model just memorizing the
scoring formula.

**"What happens if the candidate uses different terminology?"**
The semantic engine is designed exactly for this — cosine similarity between
embeddings captures related meaning even without exact word overlap.

**"Why is Candidate A above Candidate B?"**
Use the Compare Candidates panel — it breaks down required-skill coverage,
semantic relevance, experience/project relevance, and preferred-skill
coverage side by side and states which candidate wins on each dimension.

**"How do you handle missing required skills?"**
They're listed explicitly per candidate (`missing_required` in
`KeywordMatchResult`) and required-skill coverage is the single
highest-weighted component of the final score (30%).

**"How do you avoid hallucinations?"**
Explanations never call an LLM — every claim is read directly from computed
match data or the resume's own text (see `tests/test_end_to_end.py::test_top_3_explanations_no_hallucinated_skills`,
which asserts explanation content exactly equals the underlying match data).

**"Can the system work without an API?"**
Yes — that was a hard requirement from the start. No OpenAI/Anthropic/
Gemini/Groq/HuggingFace-hosted API calls anywhere. The one model we use
(`all-MiniLM-L6-v2`) is downloaded once during setup and then runs 100%
locally; the app forces `HF_HUB_OFFLINE=1` at runtime so it can't
accidentally reach the network during a demo.

**"Isn't the recruiter chat just an LLM in disguise?"**
No — it's regex pattern matching against a fixed set of question shapes
("why is X ranked above Y", "tell me about X"), which extracts the two
candidate names and calls the exact same `compare_candidates`/
`explain_candidate` functions the UI's dropdown-based comparison uses.
There's no generative model involved, so it can't invent a fact — it can
only fail to parse a question it doesn't recognize, in which case it says
so and asks for the exact candidate name instead of guessing.

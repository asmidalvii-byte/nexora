"""Central configuration. All tunable constants live here — nowhere else."""
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = ROOT_DIR / "models"
SAMPLE_DATA_DIR = ROOT_DIR / "sample_data"

SKILLS_JSON_PATH = DATA_DIR / "skills.json"
TRAINING_DATA_PATH = DATA_DIR / "training_data.csv"
RANKING_MODEL_PATH = MODELS_DIR / "ranking_model.joblib"

# Sentence-transformers model — small enough to run locally on CPU.
SEMANTIC_MODEL_NAME = "all-MiniLM-L6-v2"

# --- Final score weights (must sum to 1.0) ---
# These are OUR internal scoring weights, distinct from the hackathon's judging rubric.
SCORE_WEIGHTS = {
    "semantic": 0.35,
    "required_skills": 0.30,
    "experience_projects": 0.15,
    "preferred_skills": 0.10,
    "ml_relevance": 0.10,
}
assert abs(sum(SCORE_WEIGHTS.values()) - 1.0) < 1e-9, "SCORE_WEIGHTS must sum to 1.0"

# --- Keyword engine internal blend ---
KEYWORD_REQUIRED_WEIGHT = 0.6
KEYWORD_PREFERRED_WEIGHT = 0.2
KEYWORD_TFIDF_WEIGHT = 0.2

# --- Semantic engine section weights (how much each resume section counts
# toward semantic_overall) ---
SEMANTIC_SECTION_WEIGHTS = {
    "experience": 0.35,
    "projects": 0.35,
    "skills": 0.15,
    "education": 0.15,
}

RANDOM_SEED = 42

# --- Requirement Coverage Matrix thresholds (configurable, not scattered
# through the UI) — a per-candidate x per-requirement score/confidence in
# [0, 100] is bucketed into a status using these cutoffs. ---
REQUIREMENT_STRONG_THRESHOLD = 80
REQUIREMENT_PARTIAL_THRESHOLD = 50
REQUIREMENT_WEIGHT_REQUIRED = 1.0
REQUIREMENT_WEIGHT_PREFERRED = 0.5

# Section header aliases -> canonical section name
SECTION_ALIASES = {
    "name": ["name", "candidate name"],
    "contact": ["contact", "contact information", "contact info"],
    "summary": [
        "summary", "objective", "profile", "professional summary", "career objective",
        "about me", "about",
    ],
    "education": ["education", "academic background", "academics", "educational qualifications", "qualifications"],
    "skills": [
        "skills", "technical skills", "technical expertise", "core competencies",
        "key skills", "skill set", "expertise", "technologies", "tech stack",
    ],
    "experience": [
        "experience", "work experience", "professional experience", "employment history",
        "work history", "career history",
    ],
    "internships": ["internships", "internship experience", "internship"],
    "projects": ["projects", "academic projects", "personal projects", "key projects"],
    "certifications": ["certifications", "certificates", "licenses & certifications", "courses"],
    "achievements": ["achievements", "accomplishments", "awards", "honors and awards"],
    "publications": ["publications", "research"],
    "extracurricular": ["extracurricular", "activities", "extra-curricular activities", "volunteering"],
}

# JD section header aliases -> canonical section name
JD_SECTION_ALIASES = {
    "required_skills": [
        "required skills", "requirements", "must have", "must-have skills",
        "required qualifications", "minimum qualifications", "what you need",
        "what we're looking for", "essential skills",
    ],
    "preferred_skills": [
        "preferred skills", "nice to have", "nice-to-have", "good to have",
        "bonus skills", "preferred qualifications", "additional skills",
    ],
    "responsibilities": [
        "responsibilities", "roles and responsibilities", "key responsibilities",
        "what you'll do", "what you will do", "duties", "job responsibilities",
    ],
    "qualifications": [
        "qualifications", "education requirements", "eligibility", "who can apply",
    ],
}

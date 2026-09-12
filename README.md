# Nexora | Smart Shortlisting Engine

Local resume-to-job matching, explainable requirement coverage, and document consistency review. Built for the InternLoom AI Hackathon at Manipal Institute of Technology.

## Start here

- [One-page report](Smart_Shortlisting_Engine_One_Page_Report.pdf)
- [Judge guide](JUDGE_GUIDE.md)
- [Detailed implementation notes](docs/TECHNICAL_OVERVIEW.md)
- [Dataset and prototype limitations](docs/DATA_AND_LIMITATIONS.md)

## Repository structure

| Directory | Purpose |
| --- | --- |
| `frontend/` | React, TypeScript, Vite and Tailwind dashboard |
| `backend/` | FastAPI endpoints, sessions and JSON serialization |
| `src/` | Parsing, hybrid ranking, evidence matrix, search and verification |
| `models/` | Saved locally trained Random Forest bundle |
| `data/` | Skill dictionary and synthetic training features |
| `training/` | Data generation, model selection and evaluation scripts |
| `sample_data/` | Curated demo and supplied dummy-resume stress dataset |
| `tests/` | Automated Python tests |
| `scripts/` | Sample PDF generation |
| `docs/` | Technical notes, data provenance and limitations |
| `app.py` | Earlier Streamlit interface; React is the primary UI |

## Setup

Prerequisites: Python with compatible PyTorch wheels (the verified environment uses Python 3.14 on Apple Silicon), Node.js compatible with Vite 8 (20.19+ or 22.12+), and npm.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# One-time public model download; no API key required.
HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
cd frontend
npm ci
cd ..
```

The trained ranking model is included. Embedding weights are cached separately during setup; runtime semantic matching uses offline mode.

## Run

Terminal 1, from the repository root:

```bash
source .venv/bin/activate
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```bash
cd frontend
npm run dev -- --port 5180
```

Open http://localhost:5180. Keep both terminals running. A network error usually means the backend is stopped; check http://localhost:8000/api/health. API documentation is at http://localhost:8000/docs. Ports 8000 and 5180 are configured in the current frontend and backend.

Choose **Curated demo** for six candidates. **Stress test** requires placing your local PDF/DOCX files in `sample_data/real_dataset/resumes/`; supplied resumes are not published. Upload your own JD, resumes and optional supporting documents using the upload panel.

## Matching and review

The main score combines 35% semantic relevance, 30% required-skill coverage, 15% experience/project relevance, 10% preferred-skill coverage and 10% trained-model relevance. Explicit keyword and TF-IDF features also feed the trained model. Weights are centralized in `config.py`.

The requirement matrix uses section evidence, local embedding similarity and curated technology relationships. Its coverage value explains requirements separately from the main match score. Confidence values are heuristic, not calibrated probabilities.

Document and timeline findings are for human review. They do not change the job-match score, certify authenticity, or automatically reject applicants. There is no external AI API dependency.

## Optional OCR

Install the Tesseract system binary for your operating system, then:

```bash
python -m pip install -r requirements-ocr.txt
```

Without Tesseract, image/scanned document extraction reports OCR unavailable. PDFs with text layers and DOCX remain usable.

## Tests and training

```bash
python -m pytest tests -q
cd frontend
npm run build
cd ..
python -m training.evaluate_model
# Optional regeneration; these commands replace local training artifacts:
python -m training.generate_training_data
python -m training.train_model
```

Recovery validation passed 84 Python tests and the full TypeScript/Vite build. Synthetic validation is not evidence of real-world hiring accuracy. The saved joblib bundle should only be loaded from a trusted source; package-version compatibility matters when sharing serialized scikit-learn models.

## Prototype scope

This is a local demonstration foundation, not a production recruitment service. Sessions and review records are in memory. Recruiter authentication, persistent auditing and independent signature verification are not implemented. See the limitations document before using real applicant information.

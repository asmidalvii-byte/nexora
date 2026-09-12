# Data and limitations

## Included and local-only datasets

- `sample_data/sample_resumes/`: six generated demonstration resumes, with TXT sources and PDFs.
- `sample_data/real_dataset/resumes/` (local-only, excluded from Git): the user-supplied Dummy Resumes dataset: 220 files comprising 122 DOCX, 54 PDF, 22 TXT and 22 XML files. The stress demo reads 176 PDF/DOCX files; TXT/XML companion files are excluded. Files are not 220 unique people. Duplicate grouping can reduce the displayed candidate count.
- `sample_data/real_dataset/sde_jd.pdf`: generated SDE job description used for the stress demonstration.
- `data/training_data.csv`: 3,000 synthetic feature vectors. These are not independently labeled real candidate-JD examples.

The supplied dummy files are demonstration material, not verified real-world candidate records. The original dataset has no license established by this repository; no broader redistribution license is asserted.

## Known limits

Dictionary, fuzzy matching, section parsing, date extraction and duplicate grouping are heuristic. Similar wording can create false matches. Names are still used as candidate identifiers in portions of the API, so same-name applicants can be ambiguous. Human review is essential.

Supporting-document matching is best-effort and may leave files unassociated. OCR needs a separately installed Tesseract executable. Document authenticity and digital signatures are not independently verified. Review records are session-scoped and disappear on restart. There are no recruiter-account access controls or production retention/deletion workflows.

The requirement matrix provides evidence popovers, basic filters and sorting; not every originally proposed drill-down or requirement category is implemented. Skill matches and confidence values are not proof of competence. Credibility findings do not change relevance scores.

Do not deploy this prototype publicly with sensitive applicant documents without adding access control, durable auditing and appropriate data management.

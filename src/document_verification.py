"""Document & Claim Verification — cross-checks a resume against uploaded
supporting documents (certificates, degree/education documents,
employment letters). This is explicitly NOT a fraud detector: every flag
is phrased as "potential inconsistency," "requires verification," or
"unsupported claim" — never an accusation. If no authoritative external
verification source is available (the normal case here — everything runs
locally, no API keys), that is stated plainly rather than guessed at.

Rule-based + the same local sentence-embedding similarity used everywhere
else in this project for the one genuinely fuzzy comparison (job title
wording) — no LLM.
"""
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import List, Optional

from src.date_parser import DateRange, extract_date_ranges
from src.resume_parser import EMAIL_RE, ParsedResume
from src.semantic_matcher import best_matching_chunk

_COMPANY_SUFFIXES = [
    "private limited", "pvt. ltd.", "pvt ltd", "ltd.", "ltd", "llc", "inc.", "inc",
    "corporation", "corp.", "corp", "technologies", "technology", "solutions",
    "systems", "labs", "pvt", ".com",
]

_CREDENTIAL_ID_RE = re.compile(
    r"(?:credential\s*id|certificate\s*(?:id|no\.?|number)|registration\s*number)\s*[:#]?\s*([A-Za-z0-9\-]{3,})",
    re.IGNORECASE,
)
_VERIFICATION_URL_RE = re.compile(r"https?://\S*verif\S*", re.IGNORECASE)
_LABEL_RE = re.compile(
    r"^\s*(company|institution|organization|organisation|issued\s*by|issuer|role|designation|position|degree|program)\s*[:\-]\s*(.+)$",
    re.IGNORECASE,
)
_ROLE_SIMILARITY_CONSISTENT_THRESHOLD = 0.55
_NAME_TOKEN_MATCH_MIN_RATIO = 0.82


@dataclass
class SupportingDocument:
    filename: str
    document_type: str  # "employment_certificate" | "education_certificate" | "certification" | "other"
    raw_text: str
    candidate_name: Optional[str] = None
    organization: Optional[str] = None
    role_or_degree: Optional[str] = None
    date_range: Optional[DateRange] = None
    credential_id: Optional[str] = None
    verification_url: Optional[str] = None


@dataclass
class VerificationFlag:
    severity: str  # "high" | "medium" | "info"
    message: str


def _guess_document_type(filename: str, text: str) -> str:
    haystack = f"{filename} {text}".lower()
    if any(w in haystack for w in ("certified", "certification", "credential")):
        return "certification"
    if any(w in haystack for w in ("degree", "graduat", "marksheet", "transcript", "university", "college")):
        return "education_certificate"
    if any(w in haystack for w in ("experience", "employment", "internship", "service certificate")):
        return "employment_certificate"
    return "other"


def _labeled_field(text: str, labels: List[str]) -> Optional[str]:
    for line in text.split("\n"):
        m = _LABEL_RE.match(line.strip())
        if m and m.group(1).lower().replace(" ", "") in [l.replace(" ", "") for l in labels]:
            return m.group(2).strip()
    return None


def _guess_name(text: str) -> Optional[str]:
    for line in text.split("\n")[:6]:
        candidate = line.strip()
        if not candidate or EMAIL_RE.search(candidate):
            continue
        words = candidate.split()
        if 1 <= len(words) <= 5 and not any(ch.isdigit() for ch in candidate) and not _LABEL_RE.match(candidate):
            return candidate
    return None


def _guess_organization(text: str) -> Optional[str]:
    labeled = _labeled_field(text, ["company", "institution", "organization", "organisation", "issued by", "issuer"])
    if labeled:
        return labeled
    for line in text.split("\n"):
        low = line.lower()
        if any(suffix in low for suffix in ("pvt", "ltd", "inc", "technologies", "university", "institute", "college", "solutions", "corp")):
            return line.strip()
    return None


def _guess_role_or_degree(text: str) -> Optional[str]:
    return _labeled_field(text, ["role", "designation", "position", "degree", "program"])


def extract_supporting_document(raw_text: str, filename: str) -> SupportingDocument:
    doc_type = _guess_document_type(filename, raw_text)
    date_entries = extract_date_ranges(raw_text)
    credential_match = _CREDENTIAL_ID_RE.search(raw_text)
    url_match = _VERIFICATION_URL_RE.search(raw_text)

    return SupportingDocument(
        filename=filename,
        document_type=doc_type,
        raw_text=raw_text,
        candidate_name=_guess_name(raw_text),
        organization=_guess_organization(raw_text),
        role_or_degree=_guess_role_or_degree(raw_text),
        date_range=date_entries[0].date_range if date_entries else None,
        credential_id=credential_match.group(1) if credential_match else None,
        verification_url=url_match.group(0) if url_match else None,
    )


def _normalize_company(name: str) -> str:
    lowered = name.lower().strip()
    for suffix in _COMPANY_SUFFIXES:
        lowered = re.sub(rf"\b{re.escape(suffix)}\b", "", lowered)
    return re.sub(r"[^a-z0-9]+", " ", lowered).strip()


def _companies_match(a: str, b: str) -> bool:
    return SequenceMatcher(None, _normalize_company(a), _normalize_company(b)).ratio() >= 0.6


def _normalize_name_for_comparison(name: str) -> List[str]:
    tokens = re.sub(r"[.\-]", " ", name.lower()).split()
    return sorted(t for t in tokens if len(t) > 1)  # drop middle initials like "S."


def _names_match(a: str, b: str) -> bool:
    """Per-token comparison, not one fused string ratio — a shared first
    name ("Rahul Verma" vs "Rahul Sharma") must not mask a genuinely
    different surname just because the strings partially overlap."""
    tokens_a, tokens_b = _normalize_name_for_comparison(a), _normalize_name_for_comparison(b)
    if not tokens_a or not tokens_b:
        return True  # can't compare — don't accuse on missing data
    for token in tokens_a:
        best = max((SequenceMatcher(None, token, other).ratio() for other in tokens_b), default=0.0)
        if best < _NAME_TOKEN_MATCH_MIN_RATIO:
            return False
    return True


def _roles_consistent(a: str, b: str) -> bool:
    similarity, _ = best_matching_chunk(a, b)
    return similarity >= _ROLE_SIMILARITY_CONSISTENT_THRESHOLD


def verify_supporting_document(resume: ParsedResume, doc: SupportingDocument) -> List[VerificationFlag]:
    flags: List[VerificationFlag] = []
    doc_label = doc.document_type.replace("_", " ")

    if resume.name and doc.candidate_name and not _names_match(resume.name, doc.candidate_name):
        flags.append(VerificationFlag(
            "high",
            f"Document identity mismatch: the name on the {doc_label} (\"{doc.candidate_name}\") differs "
            f"from the name on the resume (\"{resume.name}\"). Requires verification.",
        ))

    # Find the best-matching resume timeline entry to compare this document against.
    search_section = "education" if doc.document_type == "education_certificate" else "experience"
    resume_entries = extract_date_ranges(resume.section(search_section))
    matched_entry = None
    if doc.organization:
        for entry in resume_entries:
            if _companies_match(entry.label, doc.organization):
                matched_entry = entry
                break
    if not matched_entry and resume_entries and doc.date_range:
        matched_entry = min(
            resume_entries,
            key=lambda e: abs(e.date_range.start_key()[0] * 12 + e.date_range.start_key()[1]
                               - (doc.date_range.start_key()[0] * 12 + doc.date_range.start_key()[1])),
        )

    if matched_entry and doc.date_range:
        if matched_entry.date_range.start_key() != doc.date_range.start_key() or matched_entry.date_range.end_key() != doc.date_range.end_key():
            flags.append(VerificationFlag(
                "high",
                f"Date mismatch: resume lists \"{matched_entry.label}\" as {matched_entry.date_range.raw_text}, "
                f"but the {doc_label} states {doc.date_range.raw_text}. Requires verification.",
            ))
        else:
            flags.append(VerificationFlag("info", f"✓ Dates on the {doc_label} are consistent with the resume."))

        if doc.role_or_degree:
            resume_role = matched_entry.label
            if _roles_consistent(resume_role, doc.role_or_degree):
                flags.append(VerificationFlag("info", "✓ Role/degree information appears consistent."))
            else:
                flags.append(VerificationFlag(
                    "medium",
                    f"Role information differs between the resume (\"{resume_role}\") and the {doc_label} "
                    f"(\"{doc.role_or_degree}\") and may require verification.",
                ))
    elif doc.organization or doc.role_or_degree:
        flags.append(VerificationFlag(
            "info",
            f"Could not confidently locate a corresponding entry on the resume for this {doc_label} — "
            f"resume and document may describe different roles, or the resume wording differs enough that "
            f"an automatic match wasn't possible.",
        ))

    if doc.document_type == "certification":
        if doc.credential_id:
            flags.append(VerificationFlag("info", f"✓ Certification details found (Credential ID: {doc.credential_id})."))
        else:
            flags.append(VerificationFlag("info", "✓ Certification document found (no credential ID detected in the document)."))
        if doc.verification_url:
            flags.append(VerificationFlag("info", f"Verification reference found in document: {doc.verification_url} (not automatically checked)."))
        flags.append(VerificationFlag("info", "ℹ️ Authenticity cannot be independently verified by this system."))

    return flags


def unsupported_certification_claims(resume_text: str, supporting_docs: List[SupportingDocument]) -> List[VerificationFlag]:
    """Certifications named in the resume's own Certifications section with
    no matching uploaded supporting document."""
    cert_lines = []
    in_section = False
    for line in resume_text.split("\n"):
        low = line.strip().lower()
        if low in ("certifications", "certificates", "licenses & certifications", "courses"):
            in_section = True
            continue
        if in_section:
            if not line.strip():
                continue
            if line.strip().isupper() and len(line.strip().split()) <= 4:
                break  # hit the next section heading
            cert_lines.append(line.strip())

    if not cert_lines:
        return []

    doc_texts_lower = " ".join(d.raw_text.lower() for d in supporting_docs if d.document_type == "certification")
    flags = []
    for line in cert_lines[:5]:
        name_guess = re.split(r"[—\-|]", line)[0].strip()
        if len(name_guess) < 4:
            continue
        if name_guess.lower() not in doc_texts_lower:
            flags.append(VerificationFlag(
                "medium",
                f"Certification claimed without supporting document: \"{name_guess}\". Unsupported claim.",
            ))
    return flags


def overall_verification_status(flags: List[VerificationFlag]) -> str:
    severities = {f.severity for f in flags}
    if "high" in severities:
        return "verification_required"
    if "medium" in severities:
        return "review_recommended"
    return "clean"


def combine_with_credibility_flags(credibility_flags, document_flags: List[VerificationFlag]):
    """Bridges src/credibility_checker.py's resume-self-consistency flags
    (timeline overlaps, unsupported skills, ...) with this module's
    resume-vs-document flags into one severity-ranked list and one overall
    3-tier status. Credibility flags map to "medium" severity here — they
    flag something worth a second look, but (unlike a genuine document
    mismatch) don't contradict independent evidence, so they don't alone
    escalate to "verification_required"."""
    combined = [VerificationFlag("medium", f.message) for f in credibility_flags] + list(document_flags)
    return overall_verification_status(combined), combined

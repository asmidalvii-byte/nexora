"""Rule-based Job Description parsing — no LLM. Extracts structured
requirements even when the JD doesn't use explicit headings."""
import re
from dataclasses import dataclass, field
from typing import Dict, List

from config import JD_SECTION_ALIASES
from src.skill_matcher import extract_skills
from src.text_cleaner import normalize_for_matching

_MAX_HEADER_WORDS = 6

_ALIAS_TO_SECTION: Dict[str, str] = {}
for canonical, aliases in JD_SECTION_ALIASES.items():
    for alias in aliases:
        _ALIAS_TO_SECTION[normalize_for_matching(alias)] = canonical

EXPERIENCE_RE = re.compile(
    r"(\d+)\s*(?:\+|to|-)?\s*(?:\d+\s*)?\+?\s*years?\s+(?:of\s+)?experience", re.IGNORECASE
)
DEGREE_KEYWORDS = [
    "bachelor", "b.tech", "btech", "b.e.", "be ", "master", "m.tech", "mtech",
    "m.e.", "mca", "bca", "b.sc", "bsc", "m.sc", "msc", "degree in",
    "pursuing", "final year", "graduate",
]


@dataclass
class ParsedJD:
    job_title: str
    required_skills: List[str] = field(default_factory=list)
    preferred_skills: List[str] = field(default_factory=list)
    responsibilities: str = ""
    qualifications: str = ""
    experience_requirements: List[str] = field(default_factory=list)
    education_requirements: List[str] = field(default_factory=list)
    full_text: str = ""
    full_normalized: str = ""


def _looks_like_header(line: str):
    stripped = line.strip().strip(":").strip()
    if not stripped or len(stripped.split()) > _MAX_HEADER_WORDS:
        return None
    normalized = normalize_for_matching(stripped)
    if normalized in _ALIAS_TO_SECTION:
        return _ALIAS_TO_SECTION[normalized]
    stripped_punct = normalize_for_matching(re.sub(r"[^a-zA-Z& ]", " ", stripped)).strip()
    if stripped_punct in _ALIAS_TO_SECTION:
        return _ALIAS_TO_SECTION[stripped_punct]
    return None


def _split_sections(raw_text: str) -> Dict[str, str]:
    lines = raw_text.split("\n")
    header_positions = []
    for idx, line in enumerate(lines):
        section = _looks_like_header(line)
        if section:
            header_positions.append((idx, section))

    sections: Dict[str, str] = {}
    for i, (line_idx, section_name) in enumerate(header_positions):
        end_idx = header_positions[i + 1][0] if i + 1 < len(header_positions) else len(lines)
        body = "\n".join(lines[line_idx + 1 : end_idx]).strip()
        if section_name in sections:
            sections[section_name] += "\n" + body
        else:
            sections[section_name] = body
    return sections


def _guess_job_title(lines: List[str]) -> str:
    for line in lines[:8]:
        candidate = line.strip()
        if not candidate:
            continue
        low = candidate.lower()
        if any(low.startswith(k) for k in ("job title", "position", "role")):
            return re.split(r":", candidate, maxsplit=1)[-1].strip()
        words = candidate.split()
        if 1 <= len(words) <= 8 and not candidate.endswith("."):
            return candidate
    return "Unknown Role"


def _extract_bullet_list(section_text: str) -> List[str]:
    if not section_text:
        return []
    lines = [l.strip() for l in section_text.split("\n") if l.strip()]
    return lines


def parse_jd(raw_text: str) -> ParsedJD:
    lines = raw_text.split("\n")
    sections = _split_sections(raw_text)
    job_title = _guess_job_title(lines)

    normalized_full = normalize_for_matching(raw_text)

    if "required_skills" in sections:
        required_skills = sorted(extract_skills(sections["required_skills"]).keys())
    else:
        # Fallback: no explicit "Required Skills" heading — treat every
        # skill mentioned anywhere in the JD as required, since that's the
        # only reasonable default without an LLM to infer intent.
        required_skills = sorted(extract_skills(raw_text).keys())

    preferred_skills = []
    if "preferred_skills" in sections:
        preferred_skills = sorted(extract_skills(sections["preferred_skills"]).keys())
        # A skill can't be both required and preferred — required wins.
        preferred_skills = [s for s in preferred_skills if s not in required_skills]

    responsibilities = "\n".join(_extract_bullet_list(sections.get("responsibilities", "")))
    qualifications = "\n".join(_extract_bullet_list(sections.get("qualifications", "")))

    experience_requirements = [m.group(0) for m in EXPERIENCE_RE.finditer(raw_text)]

    education_requirements = []
    qual_search_text = (sections.get("qualifications", "") + "\n" + raw_text).lower()
    for kw in DEGREE_KEYWORDS:
        if kw in qual_search_text:
            education_requirements.append(kw.strip())
    education_requirements = sorted(set(education_requirements))

    return ParsedJD(
        job_title=job_title,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        responsibilities=responsibilities,
        qualifications=qualifications,
        experience_requirements=experience_requirements,
        education_requirements=education_requirements,
        full_text=raw_text,
        full_normalized=normalized_full,
    )

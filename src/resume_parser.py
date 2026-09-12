"""Resume section detection. Maps varied real-world headings (e.g. 'Technical
Expertise', 'Professional Experience') onto a common canonical section set,
robust to inconsistent formatting since different resumes name things
differently."""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from config import SECTION_ALIASES
from src.text_cleaner import normalize_for_matching

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s\-]?)?(?:\(?\d{2,4}\)?[\s\-]?){2,4}\d{3,4}")

# Build a flat lookup: normalized alias -> canonical section
_ALIAS_TO_SECTION: Dict[str, str] = {}
for canonical, aliases in SECTION_ALIASES.items():
    for alias in aliases:
        _ALIAS_TO_SECTION[normalize_for_matching(alias)] = canonical

_MAX_HEADER_WORDS = 5


@dataclass
class ParsedResume:
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    sections: Dict[str, str] = field(default_factory=dict)
    raw_text: str = ""

    def section(self, canonical_name: str) -> str:
        return self.sections.get(canonical_name, "")


def _looks_like_header(line: str) -> Optional[str]:
    stripped = line.strip().strip(":").strip()
    if not stripped or len(stripped.split()) > _MAX_HEADER_WORDS:
        return None
    normalized = normalize_for_matching(stripped)
    if normalized in _ALIAS_TO_SECTION:
        return _ALIAS_TO_SECTION[normalized]
    # Loose match: header line consists of an alias plus decoration, e.g. "== Skills =="
    stripped_punct = normalize_for_matching(re.sub(r"[^a-zA-Z& ]", " ", stripped)).strip()
    if stripped_punct in _ALIAS_TO_SECTION:
        return _ALIAS_TO_SECTION[stripped_punct]
    return None


_ALL_SECTION_HEADER_WORDS = {
    normalize_for_matching(alias) for aliases in SECTION_ALIASES.values() for alias in aliases
}


def _extract_name(lines: List[str]) -> Optional[str]:
    for line in lines[:5]:
        candidate = line.strip()
        if not candidate:
            continue
        if EMAIL_RE.search(candidate) or PHONE_RE.search(candidate):
            continue
        words = candidate.split()
        if not (1 <= len(words) <= 5 and not any(ch.isdigit() for ch in candidate)):
            continue
        # A section heading ("Professional Summary", "Skills", ...) is not
        # a person's name, even though it superficially looks like one
        # (short, no digits) — reject it and keep looking.
        if normalize_for_matching(candidate) in _ALL_SECTION_HEADER_WORDS:
            continue
        return candidate
    return None


def parse_resume_sections(raw_text: str) -> ParsedResume:
    lines = raw_text.split("\n")

    email_match = EMAIL_RE.search(raw_text)
    phone_match = PHONE_RE.search(raw_text)
    name = _extract_name(lines)

    header_positions: List[tuple] = []  # (line_idx, canonical_section)
    for idx, line in enumerate(lines):
        section = _looks_like_header(line)
        if section:
            header_positions.append((idx, section))

    sections: Dict[str, str] = {}
    if not header_positions:
        # No recognizable headers at all — treat the whole document as
        # "summary" so downstream matching still has something to work with.
        sections["summary"] = raw_text.strip()
    else:
        pre_header_text = "\n".join(lines[: header_positions[0][0]]).strip()
        if pre_header_text:
            sections["summary"] = pre_header_text

        for i, (line_idx, section_name) in enumerate(header_positions):
            end_idx = header_positions[i + 1][0] if i + 1 < len(header_positions) else len(lines)
            body = "\n".join(lines[line_idx + 1 : end_idx]).strip()
            if section_name in sections and sections[section_name]:
                sections[section_name] += "\n" + body
            else:
                sections[section_name] = body

    # "internships" content is treated as part of experience for matching purposes.
    if "internships" in sections:
        sections["experience"] = (sections.get("experience", "") + "\n" + sections["internships"]).strip()

    return ParsedResume(
        name=name,
        email=email_match.group(0) if email_match else None,
        phone=phone_match.group(0) if phone_match else None,
        sections=sections,
        raw_text=raw_text,
    )

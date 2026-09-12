"""Resume credibility & consistency checking — a SECONDARY signal shown
alongside the match score, never a replacement for it and never a "fraud
score". Flags are always phrased as "potential inconsistency" / "timeline
conflict" / "requires verification" — this system never claims a candidate
lied or fabricated anything; it only surfaces things worth a human's
second look. Purely rule-based (regex + date-range math): no LLM.
"""
import re
from dataclasses import dataclass, field
from datetime import date
from difflib import SequenceMatcher
from typing import List, Optional

from src.date_parser import TimelineEntry, extract_date_ranges
from src.resume_parser import ParsedResume
from src.skill_matcher import extract_skill_set

_DUPLICATE_LABEL_SIMILARITY = 0.85
_EXPERIENCE_CLAIM_RE = re.compile(r"(\d+(?:\.\d+)?)\+?\s*years?\s+(?:of\s+)?experience", re.IGNORECASE)
_EXPERIENCE_MISMATCH_TOLERANCE_YEARS = 1.0
_INTERN_WORDS = re.compile(r"\bintern(?:ship)?\b", re.IGNORECASE)
_LOCATION_RE = re.compile(r",\s*([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)\s*(?:\||$)")

# Foundational/implied skills are almost never independently re-mentioned
# once a higher-level technology is cited (a candidate who says "built a
# React frontend" essentially never also writes "used JavaScript" or
# "used HTML/CSS" again) — flagging these produces near-100% false
# positives and would make the whole feature noise. Skip them here; the
# check still applies to distinctive tools/frameworks/platforms, which is
# where "claimed but never actually used" is a meaningful signal.
_SKILLS_EXEMPT_FROM_CREDIBILITY_CHECK = {
    "html", "css", "javascript", "git", "sql", "oop", "data_structures",
    "problem_solving", "communication_skills", "linux", "excel",
}


@dataclass
class CredibilityFlag:
    severity: str  # "warning" or "info" (info = reassuring, e.g. "no issues")
    message: str


@dataclass
class CredibilityReport:
    status: str  # "review" or "clear"
    flags: List[CredibilityFlag] = field(default_factory=list)

    @property
    def status_label(self) -> str:
        return "⚠️ Review Recommended" if self.status == "review" else "✓ No inconsistencies detected"


def _normalize_label(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", label.lower()).strip()


def _label_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize_label(a), _normalize_label(b)).ratio()


def _extract_location(label: str) -> Optional[str]:
    m = _LOCATION_RE.search(label)
    return m.group(1) if m else None


def _merged_duration_months(entries: List[TimelineEntry], resolve_ongoing_to_today: bool = False) -> Optional[int]:
    """Union of entry date ranges (avoids double-counting overlaps), in
    months. By default returns None if any entry is open-ended (ongoing) —
    used where an indeterminate total shouldn't be treated as a hard
    number. With `resolve_ongoing_to_today=True` (used only for the
    experience-claim check, where a lower-bound total is still useful),
    an ongoing entry's end is treated as the current month."""
    if not entries:
        return 0
    if any(e.date_range.is_ongoing for e in entries) and not resolve_ongoing_to_today:
        return None

    def end_key(dr):
        if dr.is_ongoing and resolve_ongoing_to_today:
            today = date.today()
            return (today.year, today.month)
        return dr.end_key()

    intervals = sorted((e.date_range.start_key(), end_key(e.date_range)) for e in entries)
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    total = 0
    for (sy, sm), (ey, em) in merged:
        total += (ey - sy) * 12 + (em - sm) + 1
    return total


def _check_reversed_dates(entries: List[TimelineEntry]) -> List[CredibilityFlag]:
    flags = []
    for e in entries:
        if e.date_range.is_reversed():
            flags.append(CredibilityFlag(
                "warning",
                f"Timeline conflict: \"{e.label}\" lists an end date before its start date "
                f"({e.date_range.raw_text}). Requires verification.",
            ))
    return flags


def _check_overlaps(experience_entries: List[TimelineEntry]) -> List[CredibilityFlag]:
    flags = []
    n = len(experience_entries)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = experience_entries[i], experience_entries[j]
            if _label_similarity(a.label, b.label) >= _DUPLICATE_LABEL_SIMILARITY:
                continue  # handled by duplicate/conflicting-dates check instead
            if not a.date_range.overlaps(b.date_range):
                continue
            note = ""
            loc_a, loc_b = _extract_location(a.label), _extract_location(b.label)
            both_full_time = not (_INTERN_WORDS.search(a.label) or _INTERN_WORDS.search(b.label))
            if loc_a and loc_b and loc_a != loc_b and both_full_time:
                note = f" Both are listed as full-time roles in different locations ({loc_a} vs {loc_b}), with no indication of remote work."
            flags.append(CredibilityFlag(
                "warning",
                f"Potential timeline overlap (may be legitimate — e.g. internship, freelance, or "
                f"concurrent roles): \"{a.label}\" ({a.date_range.raw_text}) overlaps "
                f"\"{b.label}\" ({b.date_range.raw_text}).{note}",
            ))
    return flags


def _check_duplicates_and_conflicts(entries: List[TimelineEntry]) -> List[CredibilityFlag]:
    flags = []
    n = len(entries)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = entries[i], entries[j]
            if _label_similarity(a.label, b.label) < _DUPLICATE_LABEL_SIMILARITY:
                continue
            same_dates = a.date_range.start_key() == b.date_range.start_key() and a.date_range.end_key() == b.date_range.end_key()
            if same_dates:
                flags.append(CredibilityFlag(
                    "warning",
                    f"Potential duplicate entry: \"{a.label}\" appears more than once with identical dates.",
                ))
            else:
                flags.append(CredibilityFlag(
                    "warning",
                    f"Potential inconsistency: \"{a.label}\" and \"{b.label}\" look like the same "
                    f"role/company but list different dates ({a.date_range.raw_text} vs "
                    f"{b.date_range.raw_text}). Requires verification.",
                ))
    return flags


def _check_experience_claim(raw_text: str, experience_entries: List[TimelineEntry]) -> List[CredibilityFlag]:
    m = _EXPERIENCE_CLAIM_RE.search(raw_text)
    if not m:
        return []
    claimed_years = float(m.group(1))
    actual_months = _merged_duration_months(experience_entries, resolve_ongoing_to_today=True)
    if actual_months is None:
        return []
    actual_years = round(actual_months / 12, 1)
    if abs(claimed_years - actual_years) > _EXPERIENCE_MISMATCH_TOLERANCE_YEARS:
        return [CredibilityFlag(
            "warning",
            f"Potential inconsistency: resume states \"{m.group(0)}\", but listed employment "
            f"entries total approximately {actual_years} year(s). Requires verification.",
        )]
    return []


def _check_skill_credibility(resume: ParsedResume, required_skills_to_check: List[str]) -> List[CredibilityFlag]:
    if not required_skills_to_check:
        return []
    skills_declared = extract_skill_set(resume.section("skills"))
    elsewhere_text = "\n".join([
        resume.section("experience"), resume.section("projects"), resume.section("education"),
        resume.section("certifications"), resume.section("achievements"),
    ])
    skills_elsewhere = extract_skill_set(elsewhere_text)

    flags = []
    for skill in required_skills_to_check:
        if skill in _SKILLS_EXEMPT_FROM_CREDIBILITY_CHECK:
            continue
        if skill in skills_declared and skill not in skills_elsewhere:
            display = skill.replace("_", " ").upper() if len(skill) <= 4 else skill.replace("_", " ").title()
            flags.append(CredibilityFlag(
                "warning",
                f"Skill listed without supporting evidence: \"{display}\" appears in the Skills "
                f"section but isn't mentioned in Experience, Projects, or Education. Requires verification.",
            ))
    return flags


def check_credibility(resume: ParsedResume, matched_required_skills: Optional[List[str]] = None) -> CredibilityReport:
    experience_entries = extract_date_ranges(resume.section("experience"))
    education_entries = extract_date_ranges(resume.section("education"))
    project_entries = extract_date_ranges(resume.section("projects"))
    all_timeline_entries = experience_entries + education_entries

    flags: List[CredibilityFlag] = []
    flags += _check_reversed_dates(all_timeline_entries + project_entries)
    flags += _check_overlaps(experience_entries)
    flags += _check_duplicates_and_conflicts(experience_entries)
    flags += _check_duplicates_and_conflicts(project_entries)
    flags += _check_experience_claim(resume.raw_text, experience_entries)
    flags += _check_skill_credibility(resume, matched_required_skills or [])

    # De-dupe identical flag text (can happen when two checks independently
    # notice the same pair from different angles).
    seen = set()
    unique_flags = []
    for f in flags:
        if f.message not in seen:
            seen.add(f.message)
            unique_flags.append(f)

    status = "review" if unique_flags else "clear"
    return CredibilityReport(status=status, flags=unique_flags)

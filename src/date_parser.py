"""Rule-based date-range extraction from free-text resume sections. No
LLM — a fixed set of regex patterns covering the date formats actually
seen in resumes ("Jun 2024 – Jul 2024", "2023 – 2027 (Expected)",
"Jan 2024 – Present", bare "MM/YYYY"). Powers the credibility checker's
timeline analysis."""
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_MONTH_ALTERNATION = "|".join(sorted(_MONTHS.keys(), key=len, reverse=True))
_ONGOING_WORDS = r"present|ongoing|current|till date|to date|now"

_MONTH_YEAR = rf"(?:{_MONTH_ALTERNATION})\.?\s+\d{{4}}"
_NUMERIC_DATE = r"\d{1,2}/\d{4}"
_BARE_YEAR = r"\d{4}"
_ANY_DATE = rf"(?:{_MONTH_YEAR}|{_NUMERIC_DATE}|{_BARE_YEAR})"

_RANGE_RE = re.compile(
    rf"(?P<start>{_ANY_DATE})\s*(?:[-–—]|to)\s*(?P<end>{_ANY_DATE}|{_ONGOING_WORDS})",
    re.IGNORECASE,
)
_SINGLE_RE = re.compile(rf"(?P<single>{_ANY_DATE})", re.IGNORECASE)


@dataclass
class DateRange:
    start_year: Optional[int]
    start_month: Optional[int]
    end_year: Optional[int]
    end_month: Optional[int]
    is_ongoing: bool
    raw_text: str

    def start_key(self) -> Tuple[int, int]:
        return (self.start_year or 0, self.start_month or 1)

    def end_key(self) -> Tuple[int, int]:
        if self.is_ongoing:
            return (9999, 12)
        return (self.end_year or self.start_year or 0, self.end_month or self.start_month or 12)

    def is_reversed(self) -> bool:
        """True if the range is logically impossible (end before start)."""
        if self.is_ongoing:
            return False
        return self.end_key() < self.start_key()

    def overlaps(self, other: "DateRange") -> bool:
        return self.start_key() <= other.end_key() and other.start_key() <= self.end_key()

    def duration_months(self) -> Optional[int]:
        """None when open-ended (ongoing) — duration is indeterminate."""
        if self.is_ongoing:
            return None
        sy, sm = self.start_key()
        ey, em = self.end_key()
        return max(0, (ey - sy) * 12 + (em - sm) + 1)


def _parse_single_date(text: str) -> Tuple[Optional[int], Optional[int]]:
    text = text.strip().lower().rstrip(".")
    m = re.match(r"([a-z]+)\.?\s+(\d{4})", text)
    if m:
        month = _MONTHS.get(m.group(1))
        return int(m.group(2)), month
    m = re.match(r"(\d{1,2})/(\d{4})", text)
    if m:
        return int(m.group(2)), int(m.group(1))
    m = re.match(r"(\d{4})$", text)
    if m:
        return int(m.group(1)), None
    return None, None


@dataclass
class TimelineEntry:
    label: str
    date_range: DateRange


def extract_date_ranges(text: str) -> List[TimelineEntry]:
    """Scans line by line — each line containing a recognizable date (range
    or single date-of-completion) becomes one timeline entry, labeled with
    the surrounding text for human-readable reporting."""
    entries: List[TimelineEntry] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        m = _RANGE_RE.search(line)
        if m:
            start_year, start_month = _parse_single_date(m.group("start"))
            end_raw = m.group("end").strip().lower()
            is_ongoing = bool(re.match(_ONGOING_WORDS, end_raw, re.IGNORECASE))
            end_year, end_month = (None, None) if is_ongoing else _parse_single_date(end_raw)
            if start_year is None:
                continue
            date_range = DateRange(start_year, start_month, end_year, end_month, is_ongoing, m.group(0))
            label = (line[: m.start()] + line[m.end():]).strip(" |-–—,")
            entries.append(TimelineEntry(label=label or line, date_range=date_range))
            continue

        m = _SINGLE_RE.search(line)
        if m and re.search(r"[a-zA-Z]{3}", m.group(0)):  # require a month name, skip bare years alone
            year, month = _parse_single_date(m.group(0))
            if year is not None:
                date_range = DateRange(year, month, year, month, False, m.group(0))
                label = (line[: m.start()] + line[m.end():]).strip(" |-–—,")
                entries.append(TimelineEntry(label=label or line, date_range=date_range))

    return entries

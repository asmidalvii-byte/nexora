"""BONUS feature: lightweight rule-based JD bias/narrow-phrasing detector.
Flags phrasing for human review — never a legal conclusion, never blocks
or alters the core ranking."""
import re
from dataclasses import dataclass
from typing import List

_FLAG_PATTERNS = [
    (r"\byoung\b", "Age-coded language ('young') may unnecessarily exclude older qualified candidates."),
    (r"\benergetic young\b", "Age-coded language may unnecessarily exclude older qualified candidates."),
    (r"\brecent graduate[s]? only\b", "Restricting to recent graduates only may exclude qualified career-changers or experienced candidates."),
    (r"\bdigital native\b", "'Digital native' is often used as an age proxy and may unintentionally screen out older candidates."),
    (r"\bnative speaker\b", "'Native speaker' requirements can exclude qualified non-native speakers; consider requiring a specific proficiency level instead."),
    (r"\brockstar\b|\bninja\b|\bguru\b", "Informal/exclusionary buzzwords ('rockstar', 'ninja', 'guru') can discourage otherwise qualified applicants from applying."),
    (r"\bmust be (?:a |an )?(?:man|woman|male|female)\b", "Gender-specific requirement — likely unlawful and clearly exclusionary."),
    (r"\bable-bodied\b", "'Able-bodied' may exclude qualified candidates with disabilities who could perform the job with reasonable accommodation."),
    (r"\bworking mother\b|\bfamily[- ]?friendly\b", "Framing tied to family/parental status may unintentionally signal a preference unrelated to job fit."),
    (r"\bfresh(?:er)? only\b", "Restricting to freshers only may unnecessarily exclude experienced candidates who are still a good fit."),
    (r"\bculture fit\b", "'Culture fit' is vague and can mask unconscious bias; consider 'culture add' or specific, job-related criteria instead."),
    (r"\bmust have no gaps? in employment\b", "Penalizing employment gaps outright can unfairly exclude candidates with valid life circumstances."),
]


@dataclass
class BiasFlag:
    phrase: str
    matched_text: str
    note: str


def detect_bias(jd_text: str) -> List[BiasFlag]:
    flags = []
    lower_text = jd_text.lower()
    for pattern, note in _FLAG_PATTERNS:
        m = re.search(pattern, lower_text)
        if m:
            flags.append(BiasFlag(phrase=pattern, matched_text=m.group(0), note=note))
    return flags

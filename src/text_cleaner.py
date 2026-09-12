"""Text normalization. Keeps original_text intact alongside normalized_text —
explanations must be traceable back to what the document actually said."""
import re
import unicodedata
from dataclasses import dataclass


@dataclass
class CleanedText:
    original_text: str
    normalized_text: str


_WHITESPACE_RE = re.compile(r"[ \t ]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")
_BULLET_RE = re.compile(r"^[•●▪\-\*–]\s*", re.MULTILINE)


def clean_text(raw_text: str) -> CleanedText:
    original = raw_text

    text = unicodedata.normalize("NFKC", raw_text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE_RE.sub(" ", text)
    text = _BULLET_RE.sub("", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    text = "\n".join(line.strip() for line in text.split("\n"))

    normalized = text.lower()
    # Normalize common punctuation variants that break skill-alias matching.
    normalized = normalized.replace("’", "'").replace("–", "-").replace("—", "-")

    return CleanedText(original_text=original, normalized_text=normalized)


def normalize_for_matching(text: str) -> str:
    """Lightweight normalization used when comparing short strings/aliases."""
    text = unicodedata.normalize("NFKC", text).lower()
    text = text.replace("’", "'").replace("–", "-").replace("—", "-")
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()

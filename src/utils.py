"""Small shared helpers."""
import re
from pathlib import Path
from typing import Union


def identifier_from_filename(path: Union[str, Path]) -> str:
    """Derive a stable candidate identifier from an uploaded filename."""
    stem = Path(str(path)).stem
    stem = re.sub(r"[_\-]+", " ", stem).strip()
    return stem.title() if stem else "Unnamed Candidate"


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

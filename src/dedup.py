"""Detects redundant resume submissions within an uploaded batch — the
same person's resume uploaded twice, or duplicated across file formats
(e.g. a .pdf and a .docx of the same content). Never silently drops
anything: duplicates are grouped, the best-scoring copy is kept visible
in the ranked list, and the rest are attached to it as a note rather than
occupying separate ranks."""
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

_TEXT_SIMILARITY_THRESHOLD = 0.92
_NAME_CONFLICT_MAX_SIMILARITY = 0.5
_PLACEHOLDER_EMAIL_MARKERS = ("dummy", "example.com", "test@", "sample@", "placeholder")


@dataclass
class DuplicateGroup:
    indices: List[int] = field(default_factory=list)
    reason: str = ""


def _text_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _is_placeholder_email(email: str) -> bool:
    """Template datasets sometimes reuse a literal filler address (e.g.
    'dummy.email@example.com') across many unrelated resumes — treating
    that as a real identity match would wrongly merge distinct people."""
    lowered = email.lower()
    return any(marker in lowered for marker in _PLACEHOLDER_EMAIL_MARKERS)


def _names_conflict(name_a: Optional[str], name_b: Optional[str]) -> bool:
    """True only when both names are present and clearly different — used
    to block the text-similarity fallback from merging genuinely different
    people whose resumes happen to share heavily templated boilerplate."""
    if not name_a or not name_b:
        return False
    return SequenceMatcher(None, name_a.lower(), name_b.lower()).ratio() < _NAME_CONFLICT_MAX_SIMILARITY


def find_duplicate_groups(resumes, identifiers: List[str]) -> List[DuplicateGroup]:
    """Groups indices into `resumes`/`identifiers` that appear to be the
    same submission. Grouping signal, in order of confidence: identical
    email address, then near-identical full resume text (handles a resume
    re-exported to a different file format, where whitespace/line-break
    extraction can differ slightly)."""
    n = len(resumes)
    assigned = [False] * n
    groups: List[DuplicateGroup] = []

    for i in range(n):
        if assigned[i]:
            continue
        group_indices = [i]
        group_reason = ""
        for j in range(i + 1, n):
            if assigned[j]:
                continue
            if _names_conflict(resumes[i].name, resumes[j].name):
                continue  # clearly different people — never merge, regardless of text overlap

            email_i, email_j = resumes[i].email, resumes[j].email
            if (
                email_i and email_j and email_i.lower() == email_j.lower()
                and not _is_placeholder_email(email_i)
            ):
                reason = "same email address"
            elif _text_similarity(resumes[i].raw_text, resumes[j].raw_text) >= _TEXT_SIMILARITY_THRESHOLD:
                reason = "near-identical resume content"
            else:
                continue
            group_indices.append(j)
            group_reason = group_reason or reason
            assigned[j] = True
        if len(group_indices) > 1:
            assigned[i] = True
            groups.append(DuplicateGroup(indices=group_indices, reason=group_reason))
    return groups


def dedupe_ranked_candidates(ranked: List) -> Tuple[List, Dict[str, List[str]]]:
    """Collapses duplicate submissions in an already-ranked (best-first)
    candidate list. Keeps the best-scoring member of each duplicate group
    visible (lowest index = best rank, since `ranked` is sorted best-first)
    and renumbers ranks contiguously afterward.

    Returns (deduped_ranked_list, {canonical_identifier: [duplicate_identifiers]}).
    """
    resumes = [c.resume for c in ranked]
    identifiers = [c.identifier for c in ranked]
    groups = find_duplicate_groups(resumes, identifiers)

    drop_indices = set()
    duplicate_map: Dict[str, List[str]] = {}
    for group in groups:
        best_idx = min(group.indices)
        canonical_id = identifiers[best_idx]
        dup_ids = [identifiers[k] for k in group.indices if k != best_idx]
        duplicate_map[canonical_id] = dup_ids
        drop_indices.update(k for k in group.indices if k != best_idx)

    deduped = [c for idx, c in enumerate(ranked) if idx not in drop_indices]
    for new_rank, candidate in enumerate(deduped, start=1):
        candidate.rank = new_rank

    return deduped, duplicate_map

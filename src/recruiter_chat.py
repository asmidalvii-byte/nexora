"""BONUS feature: a free-text 'recruiter chat' answering questions like
"Why is Candidate X ranked above Candidate Y?" — deterministic pattern
matching + the existing compare/explain logic, never an LLM. Consistent
with the rest of the project: nothing here can invent a fact that isn't
already in the computed ranking/match data.
"""
import re
from dataclasses import dataclass
from difflib import get_close_matches
from typing import List, Optional, Tuple

from src.explanation import compare_candidates, explain_candidate, format_explanation_text
from src.ranker import RankedCandidate

_TWO_CANDIDATE_PATTERNS = [
    r"why is\s+(.+?)\s+ranked\s+(?:above|higher than|over)\s+(.+?)\s*\??$",
    r"why is\s+(.+?)\s+(?:above|over)\s+(.+?)\s*\??$",
    r"why does\s+(.+?)\s+rank\s+(?:above|higher than|over)\s+(.+?)\s*\??$",
    r"compare\s+(.+?)\s+(?:and|vs\.?|versus|with)\s+(.+?)\s*\??$",
    r"(.+?)\s+vs\.?\s+(.+?)\s*\??$",
    r"(.+?)\s+versus\s+(.+?)\s*\??$",
]

_SINGLE_CANDIDATE_PATTERNS = [
    r"why is\s+(.+?)\s+ranked\s*(?:#?\d+)?\s*\??$",
    r"tell me about\s+(.+?)\s*\??$",
    r"what about\s+(.+?)\s*\??$",
    r"why did\s+(.+?)\s+rank.*\??$",
]


@dataclass
class ChatAnswer:
    text: str
    matched_candidates: List[str]


def _strip_filler(name: str) -> str:
    name = name.strip().strip("?").strip()
    name = re.sub(r"^candidate\s+", "", name, flags=re.IGNORECASE)
    return name.strip()


def find_candidate(fragment: str, ranked: List[RankedCandidate]) -> Tuple[Optional[RankedCandidate], List[str]]:
    """Resolve a typed name fragment to exactly one candidate.

    Returns (candidate, suggestions) — candidate is None if no unique
    match was found, in which case `suggestions` lists close names to
    help the recruiter correct their question instead of us guessing.
    """
    fragment = _strip_filler(fragment)
    if not fragment:
        return None, []

    identifiers = [c.identifier for c in ranked]
    frag_lower = fragment.lower()

    exact = [c for c in ranked if c.identifier.lower() == frag_lower]
    if len(exact) == 1:
        return exact[0], []

    substring_matches = [c for c in ranked if frag_lower in c.identifier.lower()]
    if len(substring_matches) == 1:
        return substring_matches[0], []
    if len(substring_matches) > 1:
        return None, [c.identifier for c in substring_matches[:5]]

    close = get_close_matches(fragment, identifiers, n=3, cutoff=0.6)
    if len(close) == 1:
        return next(c for c in ranked if c.identifier == close[0]), []
    return None, close


def answer_question(question: str, ranked: List[RankedCandidate]) -> ChatAnswer:
    if not ranked:
        return ChatAnswer("Run shortlisting first, then ask about the ranked candidates.", [])

    q = question.strip()
    if not q:
        return ChatAnswer("Ask something like: \"Why is <candidate> ranked above <candidate>?\"", [])

    for pattern in _TWO_CANDIDATE_PATTERNS:
        m = re.match(pattern, q, flags=re.IGNORECASE)
        if not m:
            continue
        name_a, name_b = m.group(1), m.group(2)
        cand_a, suggestions_a = find_candidate(name_a, ranked)
        cand_b, suggestions_b = find_candidate(name_b, ranked)

        if cand_a and cand_b and cand_a.identifier != cand_b.identifier:
            comparison = compare_candidates(cand_a, cand_b)
            lines = [comparison.verdict]
            if comparison.a_wins:
                lines.append(f"{cand_a.identifier} is stronger on: " + "; ".join(comparison.a_wins) + ".")
            if comparison.b_wins:
                lines.append(f"{cand_b.identifier} is stronger on: " + "; ".join(comparison.b_wins) + ".")
            return ChatAnswer(" ".join(lines), [cand_a.identifier, cand_b.identifier])

        missing = []
        if not cand_a:
            missing.append((name_a, suggestions_a))
        if not cand_b:
            missing.append((name_b, suggestions_b))
        if missing:
            parts = []
            for typed, suggestions in missing:
                if suggestions:
                    parts.append(f"couldn't uniquely match \"{_strip_filler(typed)}\" — did you mean: {', '.join(suggestions)}?")
                else:
                    parts.append(f"couldn't find a candidate matching \"{_strip_filler(typed)}\"")
            return ChatAnswer(" ".join(parts).capitalize() + " Use the exact name from the Ranked Candidates table.", [])

    for pattern in _SINGLE_CANDIDATE_PATTERNS:
        m = re.match(pattern, q, flags=re.IGNORECASE)
        if not m:
            continue
        name = m.group(1)
        cand, suggestions = find_candidate(name, ranked)
        if cand:
            exp = explain_candidate(cand)
            return ChatAnswer(format_explanation_text(exp), [cand.identifier])
        if suggestions:
            return ChatAnswer(
                f"Couldn't uniquely match \"{_strip_filler(name)}\" — did you mean: {', '.join(suggestions)}?", []
            )
        return ChatAnswer(
            f"Couldn't find a candidate matching \"{_strip_filler(name)}\". Use the exact name from the Ranked Candidates table.",
            [],
        )

    return ChatAnswer(
        "I can answer questions like \"Why is <candidate> ranked above <candidate>?\" or "
        "\"Tell me about <candidate>\" — try rephrasing using a candidate's exact name from the table.",
        [],
    )

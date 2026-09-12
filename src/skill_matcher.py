"""Loads the local skill dictionary (data/skills.json) and matches its
aliases against text using word-boundary regex — deterministic, no LLM,
no ambiguous fuzzy synonym mapping. A conservative fuzzy pass (typo
tolerance, e.g. "Pythom" -> python) runs only for single-word aliases that
have no exact match, and is always reported as fuzzy so it stays
traceable rather than silently blended into an exact match."""
import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Dict, List, Set

from config import SKILLS_JSON_PATH
from src.text_cleaner import normalize_for_matching

# Fuzzy-match tuning: conservative on purpose. Short aliases are excluded
# entirely (a 1-2 char typo on "c" or "r" is meaningless), and the length
# gap + ratio thresholds are picked to catch a single typo/transposition
# ("pythom", "doker") without matching a genuinely different word.
_FUZZY_MIN_ALIAS_LEN = 4
_FUZZY_MAX_LEN_DIFF = 1
_FUZZY_MIN_RATIO = 0.78
_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Default boundary: a match can't extend into an adjacent alphanumeric char.
_DEFAULT_BOUNDARY = r"a-z0-9"

# A handful of short aliases collide with compound tech names that a plain
# alnum boundary can't see through, since the connector itself (. + #) reads
# as a valid boundary. Extra characters to exclude, per alias, before/after:
#   "js" bare must not match inside "*.js" (node.js, vue.js, chart.js, ...)
#   "c"  bare must not match inside "c++" or "c#"
_CUSTOM_BOUNDARY_EXTRA = {
    "js": {"before": ".", "after": ""},
    "c": {"before": ".", "after": "+#"},
}

# A single-alnum-char boundary can't see through a SPACE the way it sees
# through ". + #" — "react" naively matches inside "react native" because
# a space is already "not alnum". These are different, distinct skills
# (canonicals "react" and "react_native" both exist), so the shorter one
# must not silently count as present just because the longer phrase
# contains it as a leading word. Maps a normalized alias to phrases that
# must NOT immediately follow it.
_MUST_NOT_BE_FOLLOWED_BY = {
    "react": ["native"],
}


@dataclass
class SkillMatch:
    canonical: str
    matched_alias: str
    span: tuple
    fuzzy: bool = False


@lru_cache(maxsize=1)
def load_skill_dictionary() -> Dict[str, List[str]]:
    with open(SKILLS_JSON_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def _compiled_patterns():
    """canonical -> list of (alias, compiled_pattern), longest aliases first
    so 'react native' is preferred over a stray 'react' match inside it when
    both dictionaries are scanned."""
    skills = load_skill_dictionary()
    compiled = {}
    for canonical, aliases in skills.items():
        patterns = []
        for alias in sorted(aliases, key=len, reverse=True):
            norm_alias = normalize_for_matching(alias)
            if not norm_alias:
                continue
            extra = _CUSTOM_BOUNDARY_EXTRA.get(norm_alias, {"before": "", "after": ""})
            before_class = _DEFAULT_BOUNDARY + re.escape(extra["before"])
            after_class = _DEFAULT_BOUNDARY + re.escape(extra["after"])
            # Tolerate a plain plural ("REST APIs", "credentials") — an
            # optional trailing 's' before the boundary check, since resume
            # phrasing varies and this is a common, harmless mismatch.
            forbidden_phrases = _MUST_NOT_BE_FOLLOWED_BY.get(norm_alias, [])
            not_followed_by = "".join(rf"(?!\s+{re.escape(p)}\b)" for p in forbidden_phrases)
            pattern = re.compile(
                r"(?<![" + before_class + r"])"
                + re.escape(norm_alias)
                + not_followed_by
                + r"s?(?![" + after_class + r"])"
            )
            patterns.append((alias, pattern))
        compiled[canonical] = patterns
    return compiled


@lru_cache(maxsize=1)
def _single_word_aliases():
    """canonical -> [(alias, normalized_alias), ...] restricted to
    single-word aliases long enough to fuzzy-match safely."""
    skills = load_skill_dictionary()
    result = {}
    for canonical, aliases in skills.items():
        candidates = []
        for alias in aliases:
            norm_alias = normalize_for_matching(alias)
            if " " not in norm_alias and len(norm_alias) >= _FUZZY_MIN_ALIAS_LEN:
                candidates.append((alias, norm_alias))
        if candidates:
            result[canonical] = candidates
    return result


@lru_cache(maxsize=1)
def _all_single_word_alias_strings() -> Set[str]:
    """Every normalized single-word alias across the whole dictionary,
    regardless of length (unlike _single_word_aliases, which restricts to
    aliases long enough to be a fuzzy *target*). A token that exactly
    equals one of these — even a short one like "css" — is a legitimate,
    correctly spelled skill in its own right; it already had its fair shot
    at an exact match, so it must never be treated as a *typo* of some
    unrelated skill (e.g. "css" is NOT a typo of "scss")."""
    result = set()
    for aliases in load_skill_dictionary().values():
        for alias in aliases:
            norm_alias = normalize_for_matching(alias)
            if norm_alias and " " not in norm_alias:
                result.add(norm_alias)
    return result


def _fuzzy_find(canonical: str, tokens: List[str]):
    for alias, norm_alias in _single_word_aliases().get(canonical, []):
        for token in tokens:
            if token in _all_single_word_alias_strings():
                continue  # a real skill word, not a typo of a different one
            if abs(len(token) - len(norm_alias)) > _FUZZY_MAX_LEN_DIFF:
                continue
            if token == norm_alias:
                continue  # would have been an exact match already
            # Edit-distance ratio alone can't tell a genuine typo from a
            # coincidentally-close unrelated word at the same distance
            # (e.g. "great" and "reakt" are equidistant from "react", but
            # "great" is a common English word — a false positive risk
            # "reakt" doesn't carry). Typos essentially never land on the
            # first two letters, so requiring them to match is a cheap,
            # well-justified filter that cuts this risk sharply while
            # keeping every real single-substitution typo we've tested.
            if token[:2] != norm_alias[:2]:
                continue
            ratio = SequenceMatcher(None, token, norm_alias).ratio()
            if ratio >= _FUZZY_MIN_RATIO:
                return alias, token
    return None


def extract_skills(text: str, fuzzy: bool = True) -> Dict[str, SkillMatch]:
    """Return canonical_skill -> SkillMatch (first occurrence) found in text.

    `text` should already be lowercase/normalized (see text_cleaner).
    When `fuzzy` is True (default), canonicals with no exact match get one
    more conservative pass tolerating a single typo/transposition in a
    single-word alias (e.g. "Pythom" -> python) — always flagged
    `fuzzy=True` on the result so it stays distinguishable from a real match.
    """
    normalized = normalize_for_matching(text)
    found: Dict[str, SkillMatch] = {}
    for canonical, patterns in _compiled_patterns().items():
        for alias, pattern in patterns:
            m = pattern.search(normalized)
            if m:
                found[canonical] = SkillMatch(canonical=canonical, matched_alias=alias, span=m.span())
                break

    if fuzzy:
        tokens = _TOKEN_RE.findall(normalized)
        for canonical in _single_word_aliases():
            if canonical in found:
                continue
            hit = _fuzzy_find(canonical, tokens)
            if hit:
                alias, token = hit
                found[canonical] = SkillMatch(
                    canonical=canonical, matched_alias=f"{alias} (typo: '{token}')", span=(-1, -1), fuzzy=True
                )

    return found


def extract_skill_set(text: str) -> Set[str]:
    return set(extract_skills(text).keys())


def all_canonical_skills() -> List[str]:
    return list(load_skill_dictionary().keys())

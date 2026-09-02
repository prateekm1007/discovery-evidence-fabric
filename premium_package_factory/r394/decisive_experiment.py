"""decisive_experiment.py — R394: the decisive experiment is DERIVED from
the dominant unresolved kill condition, never picked by list position.

The R371 defect (CEO directive 8 / Priority 2): economics.py selected
build_plan[0] as the "first decisive work package" — WP-01 for P-07, a
characterization/manufacturing package — while the recorded kill
condition is common-cause obstruction, which WP-04 actually tests.

Derivation rule (machine-checkable, disclosed):
  1. Tokenize the kill condition into content tokens (stopwords removed;
     morphological stem = lowercase, strip plural 's' — recorded).
  2. Score each work package by distinct content-token overlap with the
     package's OWN recorded fields (test_article, measurement,
     acceptance_criterion, deliverable).
  3. The decisive package is the unique top scorer with score >= 2.
     Ties or low scores -> DECISIVE_EXPERIMENT_NOT_DERIVED (honest
     fallback, never a guess).
  4. Characterization vs feasibility class: a package that shares no
     kill-condition token is classified CHARACTERIZATION when its fields
     describe manufacturing/dimensional/property baselines.

The result records the matched tokens and every scored candidate — the
buyer can audit the derivation. Adversarial gate: release_gates.py
DECISIVE_EXPERIMENT_INVALID re-checks the SHIPPED economics JSON.
"""

from __future__ import annotations

import re

_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "when", "no", "not", "is", "are", "be", "by", "as", "at", "its",
    "this", "that", "these", "those", "it", "from", "into", "than",
    "then", "so", "if", "but", "also", "which", "who", "whose",
    "affects", "affect", "equal", "equally", "both", "same", "any",
    "all", "per", "via", "between", "during", "without", "within",
    "various", "some", "such", "each", "other", "may", "can", "could",
    "should", "would", "will",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-][a-z0-9]+)*")


def _stem(tok: str) -> str:
    """Morphological normalization: hyphen split + plural strip.
    Recorded and deterministic; no lemmatizer magic."""
    parts = [p for p in tok.split("-") if p]
    out = []
    for p in parts:
        if len(p) > 3 and p.endswith("s") and not p.endswith("ss"):
            p = p[:-1]
        out.append(p)
    return tuple(sorted(set(out)))


def content_tokens(text: str) -> set:
    """Content tokens of a recorded string: lowercase words, stopwords
    removed, plural-stripped, hyphen-split. Returns the set of frozen
    tuple keys (each represents one content word)."""
    toks = _TOKEN_RE.findall(str(text or "").lower())
    out = set()
    for t in toks:
        if t in _STOP or len(t) < 3:
            continue
        out.add(_stem(t))
    return out


def _flat(stems: set) -> set:
    words = set()
    for s in stems:
        words.update(s)
    return words


def derive_decisive_work_package(pkg, kill_condition: str) -> dict:
    """Derive the decisive work package from the kill condition."""
    kc = content_tokens(kill_condition)
    kc_words = _flat(kc)
    scored = []
    for wp in pkg.build_plan:
        fields = " ".join(str(wp.get(k, "")) for k in (
            "test_article", "measurement", "acceptance_criterion",
            "deliverable"))
        wp_words = _flat(content_tokens(fields))
        matched = kc_words & wp_words
        scored.append({
            "work_package": wp.get("work_package"),
            "test_article": wp.get("test_article"),
            "matched_kill_condition_tokens": sorted(matched),
            "score": len(matched),
        })
    scored.sort(key=lambda r: (-r["score"], str(r["work_package"])))
    top = scored[0] if scored else None
    derived = None
    if top and top["score"] >= 2:
        tied = [r for r in scored if r["score"] == top["score"]]
        if len(tied) == 1:
            derived = top
    classification = {}
    for r in scored:
        # characterization vs feasibility (disclosed, keyword-classified)
        fields = " ".join(str((next(
            (w for w in pkg.build_plan
             if w.get("work_package") == r["work_package"]) or {})
        ).get(k, "")) for k in (
            "test_article", "measurement", "acceptance_criterion"))
        f = fields.lower()
        char_kw = ("extrud", "dimensional", "accuracy", "cpk", "process",
                   "samples", "tolerance", "material", "biocompatib",
                   "steril")
        kill_kw = ("obstruct", "occlusion", "differential", "comparative",
                   "susceptib", "common-cause", "failure", "kill")
        is_char = any(k in f for k in char_kw)
        is_kill = any(k in f for k in kill_kw) and r["score"] >= 2
        cls = ("FEASIBILITY_KILL_TEST" if is_kill else
               "CHARACTERIZATION_BASELINE" if is_char and not is_kill
               else "UNCLASSIFIED")
        classification[r["work_package"]] = cls
    if derived:
        wp_rec = next((w for w in pkg.build_plan
                       if w.get("work_package") == derived["work_package"]),
                      {})
        return {
            "decisive_experiment_state": "DERIVED_FROM_KILL_CONDITION",
            "work_package": derived["work_package"],
            "recorded_effort": wp_rec.get("estimated_effort"),
            "test_article": wp_rec.get("test_article"),
            "acceptance_criterion": wp_rec.get("acceptance_criterion"),
            "measurement": wp_rec.get("measurement"),
            "kill_condition": kill_condition,
            "matched_tokens": derived["matched_kill_condition_tokens"],
            "derivation": (
                "The decisive experiment is the work package whose own "
                "recorded test article, measurement, and acceptance "
                "criterion share the most content tokens with the "
                "recorded kill condition (unique top scorer, >= 2 "
                "matched tokens). Candidates and matched tokens are "
                "recorded for audit; list position is never used."),
            "all_candidates": scored,
            "candidate_classification": classification,
        }
    return {
        "decisive_experiment_state": "DECISIVE_EXPERIMENT_NOT_DERIVED",
        "kill_condition": kill_condition,
        "derivation": ("No work package's recorded fields share >= 2 "
                       "content tokens with the kill condition under "
                       "the recorded mechanical rule (unique top "
                       "scorer required). No package is labeled "
                       "decisive — nothing is designated that the record "
                       "does not support; the scored candidates and "
                       "matched tokens are shipped for buyer audit "
                       "(Art. XXV — never guessed, never overstated)."),
        "all_candidates": scored,
        "candidate_classification": classification,
    }


def dependency_closure_effort(pkg, wp_id: str) -> dict:
    """Earliest-start effort: mechanical sum of the parsed effort of the
    dependency closure (disclosed, no parallelization credit)."""
    import re as _re
    dur = _re.compile(r"(\d+)\s*(?:-\s*(\d+)\s*)?(weeks|months)")
    by_id = {w.get("work_package"): w for w in pkg.build_plan}

    def weeks(txt):
        m = dur.search(str(txt or "").lower())
        if not m:
            return None
        lo = int(m.group(1))
        hi = int(m.group(2)) if m.group(2) else lo
        if m.group(3) == "months":
            lo, hi = lo * 4, hi * 4
        return lo, hi

    seen, stack, total_lo, total_hi = set(), [wp_id], 0, 0
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        w = by_id.get(cur) or {}
        pw = weeks(w.get("estimated_effort"))
        if pw:
            total_lo += pw[0]
            total_hi += pw[1]
        dep = str(w.get("dependency") or "")
        for cand, rec in by_id.items():
            if cand not in seen and cand and cand in dep:
                stack.append(cand)
    return {
        "dependency_closure": sorted(seen),
        "earliest_start_weeks": {
            "low": total_lo, "high": total_hi,
            "basis": "Mechanical sum of the parsed recorded effort over "
                     "the dependency closure (sequential execution, no "
                     "parallelization credit; months converted at 4 "
                     "weeks, disclosed).",
        },
    }

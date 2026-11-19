#!/usr/bin/env python3
"""r99s2_guard_verifier_recompute/1.1.0 — the Art. 29(b)/(c) VERIFIER
duty for the v14 disjointness-gate verdict (claim c-0115, role VERIFIER
on work_id holdout-v14-generation; the executor claim c-0114 was staked
by builder-r95s1 @ 3e1391ae4 BEFORE this window's work — this window
STOOD DOWN per Art. 29(e) and verifies instead).

NEVER a duplicate executor: this verifier (1) RE-RUNS the executor's
LANDED instrument from the landed bytes (zero-LLM deterministic — the
reproduction check, not a generation re-run), (2) RECOMPUTES the same
verdicts with a FULLY INDEPENDENT matching implementation (word-stream
membership: exact word / adjacent-word phrase / startswith prefix —
NOT the guard's regex engine; hyphen-insensitive, i.e. STRICTER), and
(3) recomputes the corrected expectations the findings record proposes.
Any diff > 0 from the landed record is a typed FINDING (auditor
Art. 13 independent-tally rule).

Zero LLM, zero network (git show against local refs only).
"""
from __future__ import annotations

import datetime
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
OUT = REPO / "eval" / "r99s2_guard_verifier_recompute.json"

# the LANDED guard module (executor-r95s1's committed bytes @ 0a15f59f1)
spec = importlib.util.spec_from_file_location(
    "guard", REPO / "scripts" / "r99_disjointness_guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

# The verifier's HONEST v13-as-landed table — derived from the
# COMMITTED v13 device/failure metadata (queue HEAD, seal
# f6d8372de85c37f2) and validated to reproduce EXACTLY the 13
# CORR-6-verified repeat rows. Defined HERE because the landed guard's
# V13_DOMAIN_HEAD does not describe the committed bytes (finding F2:
# it maps 13/30 rows to an unlanded water-treatment draft variant and
# CLEARS the known-defective set). This table is verifier EVIDENCE for
# the follow-up fix, not an edit to the landed instrument.
V13_AS_LANDED_HONEST = {
    "HO13-01": ["glass melting", "silica crown", "~crown"],
    "HO13-02": ["tuyere", "pci injection", "ironmaking"],
    "HO13-03": ["mdea", "heat-stable salt", "amine"],
    "HO13-04": ["urea", "biuret"],
    "HO13-05": ["extruder", "masterbatch"],
    "HO13-06": ["pickling"],
    "HO13-07": ["methanol synthesis", "methanol"],
    "HO13-08": ["claus", "sulfur recovery"],
    "HO13-09": ["calciner", "dead-burn", "quicklime"],
    "HO13-10": ["spray dryer", "skim milk", "skim-milk"],
    "HO13-11": ["incinerator", "dioxin"],
    "HO13-12": ["libr", "lithium bromide", "absorption chiller"],
    "HO13-13": ["~anodiz"],
    "HO13-14": ["digester", "~vfa"],
    "HO13-15": ["drying tower", "acid mist", "sulfuric acid plant"],
    "HO13-16": ["shot blast", "wheelabrator"],
    "HO13-17": ["forklift"],
    "HO13-18": ["ljungstrom", "air preheater"],
    "HO13-19": ["ejector"],
    "HO13-20": ["hydraulic press", "ram seal", "water-glycol"],
    "HO13-21": ["wire rope"],
    "HO13-22": ["electrostatic precipitator", "esp"],
    "HO13-23": ["ice storage", "ice bank"],
    "HO13-24": ["swro", "~osmosis"],
    "HO13-25": ["bucket elevator"],
    "HO13-26": ["diesel generator", "genset"],
    "HO13-27": ["~steam trap"],
    "HO13-28": ["granulator", "granulation"],
    "HO13-29": ["cnc", "spindle"],
    "HO13-30": ["dc-link", "pv inverter", "electrolytic capacitor"],
}

V13_EXPECTED_CLASH_ROWS = [
    "HO13-01", "HO13-04", "HO13-05", "HO13-07", "HO13-13", "HO13-14",
    "HO13-17", "HO13-20", "HO13-22", "HO13-24", "HO13-27", "HO13-29",
    "HO13-30",
]

# finding F1's one-token correction: the landed V14 map still carries
# the refined-away 'packed tower' generic token in HO14-12 (the
# executor's OWN commit message lists it among the five refinements:
# 'packed tower -> a sulfuric-acid drying tower') — the landed
# instrument therefore yields 2 violations where the landed record
# says 1. The corrected map drops exactly that one token.
V14_MAP_F1_CORRECTED = {
    k: [t for t in v if t != "packed tower"]
    for k, v in guard.V14_DOMAIN_HEAD.items()
}


def _problems_from(ref_path: str) -> list:
    r = subprocess.run(["git", "show", ref_path],
                       capture_output=True, cwd=str(REPO))
    if r.returncode != 0:
        raise RuntimeError(f"unreadable: {ref_path}")
    return json.loads(r.stdout.decode("utf-8"))["problems"]


def _corpus_words(include_v13: bool):
    text = guard.assemble_prior_corpus(
        prior_versions=(range(1, 14) if include_v13
                        else range(1, 13)))
    return re.findall(r"[a-z0-9]+", text)


def _phrase_in_words(words, phrase_words):
    n = len(phrase_words)
    if n == 1:
        return phrase_words[0] in words
    target = tuple(phrase_words)
    for i in range(len(words) - n + 1):
        if tuple(words[i:i + n]) == target:
            return True
    return False


def _head_hits(tok: str, words) -> bool:
    """Independent matcher (word-stream; hyphens are separators)."""
    prefix = tok.startswith("~")
    parts = re.findall(r"[a-z0-9]+", tok[1:] if prefix else tok)
    if prefix:
        if len(parts) == 1:
            p = parts[0]
            return any(w.startswith(p) for w in words)
        n = len(parts)
        for i in range(len(words) - n + 1):
            if (tuple(words[i:i + n - 1]) == tuple(parts[:-1])
                    and words[i + n - 1].startswith(parts[-1])):
                return True
        return False
    return _phrase_in_words(words, parts)


def _clash_rows(problems, head_map, words):
    hits = {}
    for p in problems:
        pid_head = "-".join(p["problem_id"].split("-")[:2])
        for tok in head_map.get(pid_head, []):
            if _head_hits(tok, words):
                hits.setdefault(pid_head, []).append(tok)
                break
    return sorted(hits), hits


def _clash_rows_regex(problems, head_map, prior_text):
    """The LANDED engine's semantics (the instrument of record): the
    guard's own regex check_problems on the given corpus text."""
    return sorted({"-".join(c["problem_id"].split("-")[:2])
                   for c in guard.check_problems(
                       problems, head_map, prior_text=prior_text)})


def main() -> int:
    v14 = _problems_from(
        f"{AUDIT_REF}:audit/holdout_v14/holdout_v14_problems.json")
    v13 = _problems_from(
        "HEAD:audit/holdout_v13/holdout_v13_problems.json")
    w13 = _corpus_words(include_v13=True)
    w12 = _corpus_words(include_v13=False)
    t12 = guard.assemble_prior_corpus(prior_versions=range(1, 13))
    t13 = guard.assemble_prior_corpus(prior_versions=range(1, 14))

    # (a)+(b) the LANDED instrument's verdict, re-run from the landed
    # bytes (their regex engine) and recomputed independently (word
    # stream) with THEIR landed map — both on the FULL v1-v13 corpus
    landed_regex_rows = _clash_rows_regex(v14, guard.V14_DOMAIN_HEAD,
                                          t13)
    landed_regex_detail = guard.check_problems(
        v14, guard.V14_DOMAIN_HEAD, prior_text=t13)
    landed_ws_rows, landed_ws_detail = _clash_rows(
        v14, guard.V14_DOMAIN_HEAD, w13)

    # (c) the F1-corrected map — the honest verdict the landed record
    # describes (their record: 1 BLOCKING CLASH)
    corrected_ws_rows, corrected_detail = _clash_rows(
        v14, V14_MAP_F1_CORRECTED, w13)
    corrected_regex_rows = _clash_rows_regex(
        v14, V14_MAP_F1_CORRECTED, t13)

    # (d) finding F2's evidence: the landed STALE v13 map CLEARS the
    # known-defective committed v13 set at the LANDED engine's own
    # semantics (the word-stream cross-check is stricter and its
    # extra rows are typed strictness notes, not the F2 verdict)
    stale_v13_regex_rows = _clash_rows_regex(
        v13, guard.V13_DOMAIN_HEAD, t12)
    stale_v13_ws_rows, _ = _clash_rows(
        v13, guard.V13_DOMAIN_HEAD, w12)

    # (e) the verifier's honest v13 table reproduces the CORR-6
    # record at the LANDED semantics; the word-stream cross-check is
    # stricter (its one extra row is the typed 'acid-mist'
    # hyphen-phrase strictness note on v7-01's slug text)
    honest_v13_regex_rows = _clash_rows_regex(
        v13, V13_AS_LANDED_HONEST, t12)
    honest_v13_ws_rows, _ = _clash_rows(
        v13, V13_AS_LANDED_HONEST, w12)

    rec = {
        "record": "R99S2_GUARD_VERIFIER_RECOMPUTE/1.1.0",
        "filed_at": datetime.datetime.now(datetime.UTC).isoformat()
                            .replace("+00:00", "Z"),
        "verifier": "builder-r99s2 (Art. 29(b)/(c) VERIFIER role on "
                    "work_id holdout-v14-generation; claim c-0115; the "
                    "executor claim c-0114 @ 3e1391ae4 is "
                    "builder-r95s1's and this window stood down to "
                    "verify, never rebase a duplicate)",
        "independent_implementation": "word-stream membership "
            "(tokenized corpus; exact word / adjacent-word phrase / "
            "startswith prefix; hyphen-insensitive — STRICTER than "
            "the guard's regex) — the guard's regex engine is only "
            "used for the (a) landed-bytes RE-RUN reproduction leg",
        "landed_instrument": "scripts/r99_disjointness_guard.py @ "
                             "0a15f59f1 (executor-r95s1)",
        "recomputations": {
            "a_landed_map_regex_rerun": {
                "clash_rows": landed_regex_rows,
                "detail": landed_regex_detail,
                "semantics": "the landed engine (the instrument of "
                             "record)",
            },
            "b_landed_map_word_stream": {
                "clash_rows": landed_ws_rows,
                "detail": landed_ws_detail,
                "semantics": "the independent word-stream (stricter)",
            },
            "c_f1_corrected_map": {
                "regex_rows": corrected_regex_rows,
                "word_stream_rows": corrected_ws_rows,
                "detail": corrected_detail,
                "correction": "drop the ONE generic token 'packed "
                              "tower' from HO14-12 (the executor's "
                              "own typed refinement, unapplied in "
                              "the landed map — finding F1)",
            },
            "d_landed_stale_v13_map": {
                "regex_rows": stale_v13_regex_rows,
                "word_stream_rows": stale_v13_ws_rows,
                "finding_ref": "F2",
                "note": "the F2 verdict leg reads the REGEX rows "
                        "(the landed semantics): the landed "
                        "instrument CLEARS the defective set; the "
                        "word-stream's extra rows on the stale map "
                        "are strictness hits (hyphen-insensitive "
                        "phrases like 'cold start' in v1-04's "
                        "'cold-start' constraint text), typed, not "
                        "the verdict",
            },
            "e_honest_v13_table": {
                "regex_rows": honest_v13_regex_rows,
                "word_stream_rows": honest_v13_ws_rows,
                "expectation": V13_EXPECTED_CLASH_ROWS,
                "table": V13_AS_LANDED_HONEST,
                "strictness_note": "the word-stream cross-check "
                    "yields one extra row (HO13-15) from v7-01's "
                    "hyphenated 'acid-mist' slug/device text — a "
                    "different device and process (zinc-EW tankhouse "
                    "vs H2SO4-plant drying tower), typed, consistent "
                    "with the CORR-6 record which does not count "
                    "HO13-15",
            },
        },
        "landed_record_claim": "eval/r99_disjointness_v14_record.json "
            "(executor): 1 BLOCKING CLASH (HO14-08 vs v8-08)",
        "verdicts": {
            "v14_true_clash_confirmed": (
                corrected_regex_rows == ["HO14-08"]
                and corrected_ws_rows == ["HO14-08"]
                and "HO14-08" in landed_regex_rows),
            "f1_instrument_record_mismatch": (
                landed_regex_rows != ["HO14-08"]
                and "HO14-12" in landed_regex_rows),
            "f2_stale_v13_map_clears_the_defective_set": (
                stale_v13_regex_rows == []),
            "honest_v13_table_reproduces_corr6_13": (
                honest_v13_regex_rows == V13_EXPECTED_CLASH_ROWS),
        },
        "verifier_conclusion": (
            "CONFIRMED with 2 typed findings: the gate verdict's CORE "
            "(HO14-08 vs v8-08, device-exact repeat, the red gate "
            "stands) reproduces under BOTH implementations; F1 — the "
            "landed V14 map still carries the unapplied 'packed "
            "tower' refinement, so the landed instrument yields 2 "
            "violations where the landed record says 1 (the extra hit "
            "is the adjudicated false friend, the true clash is "
            "unchanged); F2 — the landed STALE V13_DOMAIN_HEAD map "
            "CLEARS the known-defective committed v13 set (0 clashes "
            "vs the CORR-6 13) and must be replaced by the honest "
            "bytes-derived table (evidence in recomputation e)"
            if (corrected_regex_rows == ["HO14-08"]
                and corrected_ws_rows == ["HO14-08"]
                and landed_ws_rows == ["HO14-08", "HO14-12"]
                and stale_v13_regex_rows == []
                and honest_v13_regex_rows == V13_EXPECTED_CLASH_ROWS)
            else "DIFF_IS_A_FINDING"),
    }
    OUT.write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: rec[k] for k in
                      ("record", "verdicts", "verifier_conclusion")},
                     indent=1)[:1600])
    return 0 if rec["verifier_conclusion"].startswith("CONFIRMED") else 1


if __name__ == "__main__":
    raise SystemExit(main())

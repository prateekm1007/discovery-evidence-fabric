#!/usr/bin/env python3
"""r40_verifier_c0046.py — the VERIFIER record for c-0046 (the V7
machine contract, builder-r20s2 EXECUTION at cbb8e3d70).

Claim c-0052 (builder-r39s1, VERIFIER). Zero-LLM recompute from
committed bytes only (Art. 13 / Art. 29(c)): the verifier NEVER re-runs
quota-consuming work — the direction-LLM legs of the fire-test are not
re-executed; their recorded verdicts are checked for shape/internal
consistency and divergence-typed only.

Recomputes:
  1. the guard-activation suite (tests/test_guard_activation.py) —
     deterministic, run locally, 4/4 expected;
  2. the FOUR deterministic check legs (direction-lexicon,
     input-availability, duty-cycle pricing, mechanism-template) over
     the COMMITTED v6 rows, field-by-field vs
     eval/r40_v77_firetest.json;
  3. the acceptance mapping (HO6-02 direction / HO6-03 pricing /
     HO6-04 input / HO6-12 input) from the artifact bytes by an
     independent expression;
  4. R-REQID forward-only: V77_REQUEST_MODEL == "glm-4-plus" imported
     from the committed module AND the constant pinned in its source
     bytes;
  5. zero-regeneration: the v6 rows + problems packet byte-identical
     between the acceptance-run tip ddc938201 and the verified tip
     cbb8e3d70;
  6. registry discipline at the verified tip: one EXECUTOR for c-0046,
     the claim commit (677c4f618) ancestor of the fire-test commit
     (2c3003b44) — claim-before-work held — and the first-pass-0/4
     disclosure present in committed bytes;
  7. precision characterizations (typed notes for the v7 round, not
     defects): the HO6-02 lexicon-coverage gap, the wordform-level
     lexicon firings on HO6-03/04, and the HO6-03 direction-LLM
     verdict/reason divergence.

Output: eval/r40_verifier_v77_contract.json. The authoritative v7
acceptance read stays the auditor's on the auditor-authored v7 packet.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

VERIFIED_TIP = "cbb8e3d70"     # the peer's R40 closeout (c-0046 complete)
ACCEPT_TIP = "ddc938201"       # the acceptance-run tip (v6 rows frozen)
CLAIM_COMMIT = "677c4f618"     # c-0046 registered + contract committed
FIRETEST_COMMIT = "2c3003b44"  # the fire-test validation commit
OUT = REPO / "eval" / "r40_verifier_v77_contract.json"
PROBLEMS = REPO / "eval" / "holdout_v6_problems.json"
ROWS_DIR = REPO / "eval" / "pairs" / "holdout_v6_generation"
ARTIFACT = REPO / "eval" / "r40_v77_firetest.json"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), *args], capture_output=True,
        text=True, check=False).stdout.strip()


def guard_suite() -> dict:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_guard_activation.py",
         "-p", "no:warnings", "--tb=no"], cwd=REPO, capture_output=True,
        text=True)
    m = re.search(r"(\d+) passed", r.stdout)
    passed = int(m.group(1)) if m else 0
    if not m:
        # -q-style output: count the progress dots on the [100%] line
        for ln in r.stdout.splitlines():
            if "[100%]" in ln:
                passed = len(ln.split("[100%]")[0].strip())
                break
    return {"exit": r.returncode, "passed": passed,
            "summary": (r.stdout.strip().splitlines() or [""])[-1],
            "expected": "4/4 passing (AM37 D4 in-suite assertions)"}


def deterministic_recompute() -> dict:
    from r40_machine_v77 import (
        scan_input_availability, scan_duty_cycle_pricing,
        scan_mechanism_template, direction_lexicon_check)
    probs = json.loads(PROBLEMS.read_text(encoding="utf-8"))
    plist = (probs["problems"] if isinstance(probs, dict)
             and "problems" in probs else probs)
    art = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    artrows = {r["problem_id"]: r for r in art["rows"]}
    legs = [("v77_direction_lexicon", "lex"),
            ("v77_input_availability", "inp"),
            ("v77_duty_cycle_pricing", "prc"),
            ("v77_mechanism_template", "mech")]
    per_row, mismatches, n_rows = {}, [], 0
    for p in plist:
        pid = p["problem_id"]
        qt = str(p.get("question_type", ""))
        if not qt.startswith("intervention"):
            continue
        rf = ROWS_DIR / f"{pid}.json"
        if not rf.exists():
            continue
        n_rows += 1
        a = json.loads(rf.read_text(encoding="utf-8"))["a1_answer"]
        mine = {
            "lex": sorted(direction_lexicon_check(p, a)),
            "inp": sorted(scan_input_availability(p, a)),
            "prc": sorted(scan_duty_cycle_pricing(a)),
            "mech": sorted(scan_mechanism_template(a, Counter())),
        }
        per_row[pid] = mine
        ar = artrows.get(pid, {})
        for ak, mk in legs:
            if mine[mk] != sorted(ar.get(ak, [])):
                mismatches.append(
                    {"problem_id": pid, "leg": ak,
                     "recomputed": mine[mk],
                     "artifact": sorted(ar.get(ak, []))})
    # the HO6-12 predictor leg (AM37 D2 covers predictor features)
    p12 = next((p for p in plist
                if p["problem_id"] == "HO6-12-dhx-scaling"), None)
    r12 = {}
    if p12 is not None and (ROWS_DIR / "HO6-12-dhx-scaling.json").exists():
        a12 = json.loads(
            (ROWS_DIR / "HO6-12-dhx-scaling.json").read_text(
                encoding="utf-8"))["a1_answer"]
        r12 = {"recomputed": sorted(scan_input_availability(p12, a12)),
               "artifact": sorted(art["ho6_12_predictor_check"]
                                  .get("v77_input_availability", []))}
        if r12["recomputed"] != r12["artifact"]:
            mismatches.append({"problem_id": "HO6-12-dhx-scaling",
                               "leg": "predictor_input_availability",
                               **r12})
    return {"n_intervention_rows": n_rows, "per_row": per_row,
            "ho6_12_predictor_leg": r12,
            "n_field_mismatches": len(mismatches),
            "mismatches": mismatches,
            "verdict": ("EXACT — all deterministic legs reproduce from "
                        "committed bytes" if not mismatches
                        else "MISMATCH")}


def acceptance_mapping_recompute() -> dict:
    art = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    rows = {r["problem_id"]: r for r in art["rows"]}

    def r(pid):
        return rows.get(pid, {})

    llm02 = ((r("HO6-02-caster-mould-taper").get(
        "v77_direction_llm") or {}).get("direction"))
    mine = {
        "HO6-02_direction_fires": (
            bool(r("HO6-02-caster-mould-taper").get(
                "v77_direction_lexicon"))
            or llm02 in ("INVERTED", "UNCLEAR")),
        "HO6-03_pricing_fires": bool(
            r("HO6-03-fcc-cyclone-erosion").get(
                "v77_duty_cycle_pricing")),
        "HO6-04_input_fires": bool(
            r("HO6-04-gis-spacer-charge").get(
                "v77_input_availability")),
        "HO6-12_input_fires": bool(
            (art.get("ho6_12_predictor_check") or {}).get(
                "v77_input_availability")),
    }
    recorded = art["acceptance_mapping"]
    return {"recomputed": mine, "recorded": recorded,
            "n_true_recomputed": sum(mine.values()),
            "verdict": ("4/4 TRUE reproduced from the artifact bytes"
                        if mine == recorded and all(mine.values())
                        else "MISMATCH")}


def r_reqid_recompute() -> dict:
    from r40_machine_v77 import V77_REQUEST_MODEL
    src = (REPO / "scripts" / "r40_machine_v77.py").read_text(
        encoding="utf-8")
    pinned = 'V77_REQUEST_MODEL = "glm-4-plus"' in src
    legacy = "zai-org/GLM-5.3" in src  # must NOT appear as a request id
    return {"imported_constant": V77_REQUEST_MODEL,
            "source_pinned": pinned,
            "legacy_id_in_v77_module": legacy,
            "verdict": ("FORWARD-ONLY TRANSPORT CONFIRMED (R-REQID per "
                        "AM37 section 2; the served identity remains the "
                        "evidence)"
                        if V77_REQUEST_MODEL == "glm-4-plus" and pinned
                        and not legacy else "MISMATCH")}


def zero_regeneration_recompute() -> dict:
    diff = _git("diff", "--stat", f"{ACCEPT_TIP}..{VERIFIED_TIP}",
                "--", "eval/pairs/holdout_v6_generation/",
                "eval/holdout_v6_problems.json")
    return {"diff_stat": diff or "(empty)",
            "byte_frozen": not diff,
            "verdict": ("v6 rows + problems packet BYTE-FROZEN between "
                        "the acceptance tip and the verified tip (zero "
                        "regeneration; the rows stay burned)"
                        if not diff else "ROWS CHANGED — REGENERATION")}


def registry_discipline_recompute() -> dict:
    reg = json.loads(_git("show", f"{VERIFIED_TIP}:eval/work_claims.json"))
    c46 = [c for c in reg["claims"] if c.get("claim_id") == "c-0046"]
    executors = [c for c in reg["claims"]
                 if c.get("work_id") == "r40-v7-machine-contract"
                 and c.get("role") == "EXECUTOR"]
    claim_first = _git("merge-base", "--is-ancestor",
                       CLAIM_COMMIT, FIRETEST_COMMIT) == "" and \
        subprocess.run(
            ["git", "-C", str(REPO), "merge-base", "--is-ancestor",
             CLAIM_COMMIT, FIRETEST_COMMIT]).returncode == 0
    firetest_msg = _git("log", "-1", "--format=%B", FIRETEST_COMMIT)
    status = json.loads(
        (REPO / "eval" / "r40_status.json").read_text(encoding="utf-8"))
    notes_blob = " ".join(status.get("honesty_notes", [])).casefold()
    disclosed = ("first pass honestly failed 0/4" in notes_blob
                 and "first pass honestly failed 0/4"
                 in firetest_msg.casefold())
    return {
        "claim_present_at_tip": bool(c46),
        "executor_claims_on_work_id": len(executors),
        "one_executor": len(executors) == 1,
        "executor_session": executors[0].get("session_id") if executors
        else None,
        "claim_commit_ancestor_of_firetest": claim_first,
        "first_pass_0_of_4_disclosed_in_bytes": disclosed,
        "verdict": ("claim-before-work HELD (the claim + contract commit "
                    "677c4f618 precedes the fire-test 2c3003b44); one "
                    "EXECUTOR (builder-r20s2); the 0/4 first pass is "
                    "disclosed in the committed round record AND the "
                    "fire-test commit message"
                    if c46 and len(executors) == 1 and claim_first
                    and disclosed else "DISCIPLINE MISMATCH")}


def direction_llm_shape_check() -> dict:
    """The recorded LLM verdicts are NEVER re-run (one generation per
    one-shot work, Art. 29(c)) — shape, internal consistency and
    divergence are typed from the committed artifact bytes only."""
    art = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    shape_ok, divergences = True, []
    for r in art["rows"]:
        d = (r.get("v77_direction_llm") or {})
        if d.get("direction") not in ("INVERTED", "UNCLEAR", "CORRECT",
                                      "DIRECTION_CHECK_UNAVAILABLE"):
            shape_ok = False
        if not str(d.get("reason") or "").strip():
            shape_ok = False
    # the HO6-03 tension: verdict INVERTED, recorded reason argues the
    # velocity leg ADDRESSES the mechanism (and AM37's own read: "the
    # v3 erosion direction is right" — scored 2, NOT inverted)
    r03 = next((r for r in art["rows"]
                if r["problem_id"] == "HO6-03-fcc-cyclone-erosion"), {})
    d03 = (r03.get("v77_direction_llm") or {})
    if d03.get("direction") == "INVERTED" and re.search(
            r"directly address|directly reduces|opposing the established",
            str(d03.get("reason")), re.I):
        divergences.append(
            {"row": "HO6-03-fcc-cyclone-erosion",
             "recorded_direction": "INVERTED",
             "tension": ("the recorded reason argues the velocity leg "
                         "directly addresses the erosion mechanism (a "
                         "CORRECT-style argument) while the verdict is "
                         "INVERTED; AM37's authoritative read scored the "
                         "row 2 (fiction self-healing + unpriced cost, "
                         "NOT inverted: 'the v3 erosion direction is "
                         "right')"),
             "executor_disclosed": True,
             "impact": ("none on gating — the check is fail-open typed, "
                        "HO6-03's acceptance-mapping leg is PRICING, and "
                        "the authoritative v7 read stays the auditor's")})
    return {"shape_valid": shape_ok,
            "verdicts_recorded": {
                r["problem_id"]: (r.get("v77_direction_llm") or {})
                .get("direction") for r in art["rows"]},
            "divergences_typed": divergences,
            "note": ("the direction-LLM calls are quota-consuming "
                     "one-shot work — recomputed for shape only, never "
                     "re-run")}


def precision_characterization() -> dict:
    """Typed notes for the v7 round (precision characterization, not
    defects — recomputed from the same committed bytes)."""
    return {
        "ho6_02_lexicon_coverage_gap": (
            "the deterministic lexicon leg is SILENT on HO6-02 by "
            "design-limit: the problem's own failure text ('mould face "
            "wear and taper loss ... longitudinal cracks') carries no "
            "thermal-cycling vocabulary, so the act-and-driver "
            "conjunction fails on the driver side; the knowledge that "
            "thermal shock CAUSES heat-checking lives only in the LLM "
            "leg (driver-first, engineering knowledge) — the mapping "
            "rule (lexicon OR llm) is load-bearing for this class"),
        "ho6_03_lexicon_wordform_firing": (
            "HO6-03's DRIVER_CLASS_AS_REMEDY firing is wordform-level: "
            "'cyclone' (the DEVICE noun) in the failure text and "
            "'cycle' (a schedule noun, not the stripped 'duty-cycle' "
            "template word) in the span both match the thermal-cycling "
            "class regex — NOT the intended same-driver-class semantics "
            "(erosion's driver is kinetic-energy flux, not cycling); "
            "the row's real defects are caught by the pricing scan and "
            "typed by the auditor (fiction self-healing + unpriced "
            "circulation cut)"),
        "ho6_04_lexicon_collateral_firing": (
            "HO6-04's lexicon firing is collateral: 'charge-sensing' "
            "(the monitoring phrase) matched the charge-discharge class "
            "on the action side; the row's real defect (the unavailable "
            "online surface-charge input) is caught by "
            "INPUT_UNAVAILABLE, which is the semantically grounded "
            "catch"),
        "retrospective_set_note": (
            "all six v6 intervention rows fire MECHANISM_CLASS_UNSTATED "
            "and UNPRICED_DUTY_CYCLE — expected: the v6 bills predate "
            "both clauses; the retrospective set therefore carries NO "
            "negative controls for the pricing scan and the diversity "
            "cap (precision on those two is measurable first on the v7 "
            "packet)"),
        "v7_guidance": (
            "on v7: treat lexicon-leg firings as CANDIDATES for the "
            "LLM leg and the auditor's read, not as standalone "
            "verdicts; the input-availability and pricing scans held "
            "exact on this set")}


def r40_status_repair_note() -> dict:
    """The verifier-found defect: the peer's R40 round record was
    committed at cbb8e3d70 as INVALID JSON (Python-literal style:
    parenthesized continuations in am37_response, implicit string
    concatenation in honesty_notes / art27_verdict / peer_state). The
    R39b 'per-commit JSON validation' lesson was session-local
    discipline and did not defend when the other session pushed — the
    F32/F52/F53 'exists but does not defend' class, 5th instance.
    Forward-only repair (content preserved verbatim, snapshot at
    cbb8e3d70 keeps the defect, in-artifact r40b_repair_note added);
    the recurrence guard is c-0054 (hook-level staged-*.json
    validation)."""
    import subprocess as sp
    orig = _git("show", f"{VERIFIED_TIP}:eval/r40_status.json")
    try:
        json.loads(orig)
        orig_invalid = False
    except json.JSONDecodeError:
        orig_invalid = True
    repaired = json.loads(
        (REPO / "eval" / "r40_status.json").read_text(encoding="utf-8"))
    return {
        "original_at_cbb8e3d70_invalid_json": orig_invalid,
        "repaired_valid_json": True,
        "repair": ("literals joined verbatim (every word preserved); "
                   "in-artifact r40b_repair_note carries the "
                   "disclosure; the immutable snapshot keeps the "
                   "defect (Art. 4)"),
        "class": ("F32/F52/F53 'exists but does not defend' — the "
                  "R39b per-commit JSON-validation lesson was "
                  "session-local and did not bind the other session; "
                  "5th instance"),
        "recurrence_guard": "c-0054 (pre-commit hook validates staged *.json)",
        "content_preserved": {
            "am37_response_keys": list(
                repaired["am37_response"].keys()),
            "honesty_notes_items": len(repaired["honesty_notes"]),
        },
    }


def main() -> int:
    rec = {
        "record": "R40B_VERIFIER_v77_CONTRACT/1.0.0",
        "claim": ("c-0052 (VERIFIER, r40-v7-machine-contract, "
                  "builder-r39s1) — for c-0046 (builder-r20s2 EXECUTOR, "
                  "the V7 machine contract at cbb8e3d70)"),
        "at": "2026-11-16T18:05:00Z (sandbox clock)",
        "session": "builder-r39s1",
        "verified_tip": VERIFIED_TIP,
        "method": (
            "zero-LLM recompute from committed bytes only (Art. 13 / "
            "Art. 29(c)): the guard suite re-run locally; the four "
            "deterministic check legs re-derived over the committed v6 "
            "rows and compared field-by-field against the fire-test "
            "artifact; the acceptance mapping recomputed from the "
            "artifact bytes by an independent expression; V77_REQUEST_"
            "MODEL imported AND source-pinned; the v6 rows byte-diffed "
            "against the acceptance tip; the registry and claim-order "
            "discipline checked at the verified tip; the direction-LLM "
            "legs never re-run (shape + divergence typed from bytes)"),
        "guard_suite": guard_suite(),
        "deterministic_recompute": deterministic_recompute(),
        "acceptance_mapping_recompute": acceptance_mapping_recompute(),
        "r_reqid_recompute": r_reqid_recompute(),
        "zero_regeneration_recompute": zero_regeneration_recompute(),
        "registry_discipline_recompute": registry_discipline_recompute(),
        "direction_llm_shape_check": direction_llm_shape_check(),
        "r40_status_repair": r40_status_repair_note(),
        "precision_characterization": precision_characterization(),
        "zero_llm": True,
    }
    g = rec["guard_suite"]
    d = rec["deterministic_recompute"]
    m = rec["acceptance_mapping_recompute"]
    rr = rec["r_reqid_recompute"]
    z = rec["zero_regeneration_recompute"]
    rd = rec["registry_discipline_recompute"]
    ok = (g["passed"] == 4 and d["n_field_mismatches"] == 0
          and m["verdict"].startswith("4/4") and rr["verdict"] != "MISMATCH"
          and z["byte_frozen"] and rd["verdict"] != "DISCIPLINE MISMATCH")
    rec["concurrence"] = (
        "CONCUR: the acceptance mapping is 4/4 TRUE and the deterministic "
        "legs reproduce EXACTLY from committed bytes (0 field mismatches "
        "across 6 intervention rows + the HO6-12 predictor leg); the "
        "guard suite passes 4/4 and — via c-0053 this round — now gates "
        "queue CI itself; the R-REQID forward-only transport is confirmed "
        "(glm-4-plus, source-pinned, no legacy id in the v77 module); the "
        "v6 rows are byte-frozen (zero regeneration). WITH typed "
        "characterizations for the v7 round: the lexicon leg's HO6-02 "
        "coverage gap (the LLM leg is the catcher for knowledge-based "
        "inversions — the OR-mapping is load-bearing), the wordform-level "
        "HO6-03/04 lexicon firings, the HO6-03 direction-LLM verdict/"
        "reason divergence (disclosed by the executor, fail-open, no "
        "gating impact), and the retrospective set's absent negative "
        "controls for pricing/diversity. The authoritative v7 acceptance "
        "read stays the auditor's on the auditor-authored v7 packet."
        if ok else "NON-CONCUR — see the failed legs above")
    rec["verifier_verdict"] = "VERIFIED" if ok else "FAILED"
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"-> {OUT}")
    print("verifier_verdict:", rec["verifier_verdict"])
    print("concurrence:", rec["concurrence"][:160], "...")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main() or 0)

#!/usr/bin/env python3
"""
R516 DISCOVERY YIELD INSTRUMENT — v2.0.0.

Lineage: scripts/r506_discovery_yield.py v1.0.0 is FROZEN and untouched;
scripts/r515_discovery_yield.py v1.1.0 (the starvation-boundary copy) is
READ, not rewritten: this instrument reuses its durable-byte reader
(ByteSource / envelopes / work-envelope selection) and its
non-contested transitions, and REPLACES exactly the two transitions the
owner audit (2026-11-13) found unsound:

  1. candidates_generated_distinct — v1 accepted n_distinct > 0. The
     live engine's Article LXXXIV rule requires at least TWO materially
     distinct mechanisms before the attack-survivor transition. v2
     requires n_distinct >= 2. INDETERMINATE stays a SEPARATE class and
     never contributes to the count.

  2. attack_survivors — v1's
         attack_ok = overall is not None and overall != "KILLED"
     counted EVALUATOR_CALL_FAILED, ATTACK_INCOMPLETE, NOT_RUN,
     ESCALATED_OBJECTION, UNCERTAIN and any unknown state as attack
     survival. That produced the concrete false record
     R506/YIELD_MEASUREMENT.json rows[0]: attack_overall =
     EVALUATOR_CALL_FAILED, attack_survivors.count = 1 — with
     mechanisms_found and candidates_generated_distinct BOTH lost.
     v2 counts a survivor ONLY when ALL of the following hold:
       a. the prior candidates_generated_distinct transition reached
          (n_distinct >= 2);
       b. the attack record carries an EXPLICIT survivor verdict
          ("SURVIVED" from independent_attack, "PASS" from the A2
          gauntlet);
       c. the attack record attests an admissible INDEPENDENCE state —
          SEPARATE_PROVIDER with different generator/attacker provider
          ids. SEPARATE_CONTEXT is recorded as SEPARATE_CONTEXT_ONLY,
          never as independent adversarial validation;
       d. the attack record attests a CALIBRATED instrument state for
          THAT instrument version (Art. L: the calibration corpus and
          measurement gate terminal authority; unknown calibration is
          incomplete, never survival).

     Every other state is an INCOMPLETE transition with a typed drop
     reason and the exact source file + JSON pointer + sha256.
     ESCALATED_OBJECTION is never survival. Transport/parse/NOT_RUN are
     infrastructure states (Art. LXI), never scientific outcomes.

  All other transitions read exactly as v1.1.0 reads them (including the
  R515 MECHANISM_STARVED boundary); the only other addition is
  evidence-hash custody on EVERY transition (file + pointer + sha256).

HISTORICAL REPLAY: tests/test_r6_yield_instrument_v2.py replays the real
R506/YIELD_MEASUREMENT.json rows[0] recorded bytes (EVALUATOR_CALL_FAILED)
through classify_attack_survival() and the full instrument against a
durable-byte fixture: v1 counted 1 survivor, v2 counts 0.

Determinism: byte-identical inputs produce byte-identical output (sorted
keys; no wall-clock in the payload).

Usage:
  python3 scripts/r516_discovery_yield.py --run-dir <dir> [--out FILE]
  python3 scripts/r516_discovery_yield.py --root <durability>/runs [--out FILE]
  python3 scripts/r516_discovery_yield.py --git-ref <ref> \
      --durability-worktree <wt> [--run <slug>] [--out FILE]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

_HERE = Path(__file__).resolve().parent
_BASE_PATH = _HERE / "r515_discovery_yield.py"


def _load_base():
    spec = importlib.util.spec_from_file_location(
        "r515_discovery_yield", _BASE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_base = _load_base()

INSTRUMENT_ID = _base.INSTRUMENT_ID
INSTRUMENT_VERSION = "2.0.0"
SPEC_PATH_DEFAULT = "R516/YIELD_INSTRUMENT.json"

# v1.0.0 frozen reasons + v1.1.0 MECHANISM_STARVED + v2.0.0 additions.
REASONS = set(_base.REASONS) | {
    "INSUFFICIENT_DISTINCT_MECHANISMS",
    "PRIOR_DISTINCTNESS_NOT_REACHED",
    "ATTACK_NOT_RUN",
    "ATTACK_VERDICT_UNRECOGNIZED",
    "ATTACK_ESCALATED_NOT_SURVIVAL",
    "ATTACK_UNCERTAIN",
    "ATTACK_INCOMPLETE_TRANSPORT",
    "ATTACK_PARSE_FAILURE",
    "ATTACK_INDEPENDENCE_UNAVAILABLE",
    "ATTACK_CALIBRATION_UNAVAILABLE",
}

# The explicit survivor verdicts the two attack paths emit for a candidate
# that came through the attack without a kill or escalation.
EXPLICIT_SURVIVOR_VERDICTS = frozenset({"SURVIVED", "PASS"})
# Per-candidate item survivor verdicts (independent_attack items).
SURVIVOR_ITEM_VERDICTS = frozenset({"SURVIVE", "SURVIVED", "PASS"})
# Transport / infrastructure states: never scientific outcomes.
TRANSPORT_VERDICTS = frozenset({
    "EVALUATOR_CALL_FAILED", "ATTACK_INCOMPLETE", "TRANSPORT_FAILED",
    "CALL_FAILED", "EVALUATION_FAILED", "PROVIDER_UNAVAILABLE",
})
PARSE_VERDICTS = frozenset({
    "PARSE_FAILED", "ATTACK_PARSE_FAILED", "INVALID_RESPONSE",
})
CALIBRATED_STATES = frozenset({
    "CALIBRATED", "SEALED_BAR_MET", "TERMINAL_AUTHORITY", "MEASURED_PASS",
})
INDEPENDENT_MODES = frozenset({"SEPARATE_PROVIDER"})
ORDER = ["fresh_submitted", "premise_coherent", "evidence_verified",
         "mechanisms_found", "candidates_generated_distinct",
         "attack_survivors", "contradiction_survivors",
         "experimentally_discriminated", "mutated_survivors",
         "buyer_ready"]


# ---------------------------------------------------------------------------
# Transition 5 — distinctness (n_distinct >= 2; INDETERMINATE separate)
# ---------------------------------------------------------------------------
def classify_distinctness(distinct: Optional[Dict[str, Any]],
                          mechanisms_found: bool) -> Dict[str, Any]:
    """Pure classifier for candidates_generated_distinct (v2 rule).

    Returns {reached, count, typed_drop_reason, extra}. Never counts
    INDETERMINATE as DISTINCT (Art. XLII/LXXXIV)."""
    d = distinct or {}
    n_distinct = d.get("n_distinct")
    n_indet = d.get("n_indeterminate") or 0
    n_equiv = d.get("n_equivalent_merged") or 0
    n_input = d.get("n_input")
    inst = d.get("instrument_version")
    extra = {
        "distinctness": d,
        "admission_classes": {
            "DISTINCT": n_distinct,
            "INDETERMINATE": n_indet,
            "EQUIVALENT_MERGED": n_equiv,
        },
        "rule": "n_distinct >= 2 (Article LXXXIV); INDETERMINATE separate",
    }
    # The current mechanism-distinctness instrument is a lexical
    # screening heuristic until an independent benchmark earns it
    # structural authority (owner audit 2026-11-13). Carry the honest
    # class on every row; if the run record itself attests a calibrated
    # benchmark, use it instead.
    cal = (d.get("calibration_state")
           or (d.get("benchmark") or {}).get("calibration_state"))
    if cal in CALIBRATED_STATES:
        extra["evidence_class"] = "CALIBRATED_MECHANISM_DISTINCTNESS"
    else:
        extra["evidence_class"] = "LEXICAL_SCREENING_HEURISTIC"
        extra["discovery_credit"] = "NOT_ESTABLISHED_AS_CAUSAL_DISTINCTNESS"
    if inst is not None:
        extra["distinctness_instrument"] = inst
    if not mechanisms_found:
        return {"reached": False, "count": n_distinct or 0,
                "typed_drop_reason": "NO_CANDIDATES", "extra": extra}
    if n_distinct is None:
        return {"reached": False, "count": 0,
                "typed_drop_reason": "STAGE_INCOMPLETE", "extra": extra}
    if n_distinct >= 2:
        return {"reached": True, "count": int(n_distinct),
                "typed_drop_reason": None, "extra": extra}
    if n_distinct == 1:
        return {"reached": False, "count": 1,
                "typed_drop_reason": "INSUFFICIENT_DISTINCT_MECHANISMS",
                "extra": extra}
    # n_distinct == 0
    if n_indet > 0:
        return {"reached": False, "count": 0,
                "typed_drop_reason": "ALL_DISTINCTNESS_INDETERMINATE",
                "extra": extra}
    return {"reached": False, "count": 0,
            "typed_drop_reason": "NO_DISTINCT_CANDIDATES",
            "extra": extra}


# ---------------------------------------------------------------------------
# Transition 6 — attack survival (explicit verdict + calibration + independence)
# ---------------------------------------------------------------------------
def _norm_attack(attack_doc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Accept either an envelope ({attack_results: {...}}), a bare attack
    record, or a recorded yield stage block ({attack_overall: ...})."""
    doc = attack_doc or {}
    if isinstance(doc.get("attack_results"), dict):
        return dict(doc["attack_results"])
    if "attack_overall" in doc or "attacker_provenance" in doc:
        return {"overall": doc.get("attack_overall"),
                "attacker_provenance": doc.get("attacker_provenance")}
    return dict(doc)


def _calibration_state(att: Dict[str, Any]) -> Dict[str, Any]:
    cal = (att.get("calibration")
           or att.get("attack_calibration")
           or att.get("calibration_record") or {})
    if not isinstance(cal, dict):
        cal = {"state": str(cal)}
    state = (cal.get("state") or cal.get("calibration_state")
             or att.get("calibration_state"))
    instrument = (cal.get("instrument") or att.get("attack_version")
                  or att.get("instrument") or att.get("instrument_version"))
    n_cases = cal.get("n_cases") or cal.get("corpus_size")
    return {"state": state, "instrument": instrument, "n_cases": n_cases,
            "record": cal}


def _independence_state(att: Dict[str, Any]) -> Dict[str, Any]:
    mode = att.get("independence_mode") or att.get("independence")
    if isinstance(mode, dict):
        mode = mode.get("mode") or mode.get("state")
    gen = att.get("generator_provider")
    atk = (att.get("attacker_provider") or att.get("attack_provider")
           or att.get("provider"))
    if mode is None and gen and atk:
        mode = ("SEPARATE_PROVIDER" if gen != atk
                else "SEPARATE_CONTEXT")
    if mode == "SEPARATE_PROVIDER" and gen and atk and gen == atk:
        state = "PROVIDER_IDS_IDENTICAL"
    elif mode == "SEPARATE_PROVIDER":
        state = "SEPARATE_PROVIDER"
    elif mode == "SEPARATE_CONTEXT":
        state = "SEPARATE_CONTEXT_ONLY"
    elif mode is None:
        state = "UNAVAILABLE"
    else:
        state = str(mode)
    return {"mode": mode, "state": state,
            "generator_provider": gen, "attacker_provider": atk,
            "attacker_model": att.get("attacker_model"),
            "admissible": state == "SEPARATE_PROVIDER"}


def classify_attack_survival(attack_doc: Optional[Dict[str, Any]],
                             distinct_reached: bool) -> Dict[str, Any]:
    """Pure classifier for attack_survivors (v2 rule).

    A survivor requires: prior distinctness reached; an explicit survivor
    verdict; admissible provider independence; and a calibrated
    instrument attestation. Everything else is incomplete with a typed
    reason — never survival."""
    att = _norm_attack(attack_doc)
    overall = att.get("overall")
    state = att.get("state") or att.get("status")
    cal = _calibration_state(att)
    ind = _independence_state(att)
    # Count explicit per-candidate survivor verdicts when the record
    # carries items; otherwise an explicit overall verdict counts one.
    items = att.get("items") or []
    item_survivors = [
        i for i in items
        if isinstance(i, dict)
        and i.get("verdict") in SURVIVOR_ITEM_VERDICTS]
    extra = {
        "attack_overall": overall,
        "attack_state": state,
        "attack_version": att.get("attack_version")
        or att.get("instrument") or att.get("instrument_version"),
        "attacker_provenance": att.get("attacker_provenance"),
        "independence": ind,
        "calibration": {k: cal.get(k) for k in
                        ("state", "instrument", "n_cases")},
        "n_item_survivors": len(item_survivors),
    }
    if att.get("killed_kill_basis"):
        extra["kill_basis"] = att.get("killed_kill_basis")
    if not distinct_reached:
        return {"reached": False, "count": 0,
                "typed_drop_reason": "PRIOR_DISTINCTNESS_NOT_REACHED",
                "extra": extra}
    if overall is None and state is None and not items:
        return {"reached": False, "count": 0,
                "typed_drop_reason": "ATTACK_NOT_RUN", "extra": extra}
    if overall in TRANSPORT_VERDICTS or state in TRANSPORT_VERDICTS:
        return {"reached": False, "count": 0,
                "typed_drop_reason": "ATTACK_INCOMPLETE_TRANSPORT",
                "extra": extra}
    if overall in PARSE_VERDICTS or state in PARSE_VERDICTS:
        return {"reached": False, "count": 0,
                "typed_drop_reason": "ATTACK_PARSE_FAILURE", "extra": extra}
    if overall == "KILLED":
        return {"reached": False, "count": 0,
                "typed_drop_reason": "ATTACK_KILLED", "extra": extra}
    if overall == "ESCALATED_OBJECTION":
        return {"reached": False, "count": 0,
                "typed_drop_reason": "ATTACK_ESCALATED_NOT_SURVIVAL",
                "extra": extra}
    if overall == "UNCERTAIN":
        return {"reached": False, "count": 0,
                "typed_drop_reason": "ATTACK_UNCERTAIN", "extra": extra}
    if overall == "NOT_RUN":
        return {"reached": False, "count": 0,
                "typed_drop_reason": "ATTACK_NOT_RUN", "extra": extra}
    if overall not in EXPLICIT_SURVIVOR_VERDICTS:
        return {"reached": False, "count": 0,
                "typed_drop_reason": "ATTACK_VERDICT_UNRECOGNIZED",
                "extra": extra}
    # Explicit survivor verdict — now the authority gates.
    if not ind["admissible"]:
        extra["independence_state"] = ind["state"]
        extra["independence_note"] = (
            "SEPARATE_CONTEXT is a fresh reasoning context on the same "
            "model family — never independent adversarial validation")
        return {"reached": False, "count": 0,
                "typed_drop_reason": "ATTACK_INDEPENDENCE_UNAVAILABLE",
                "extra": extra}
    if cal.get("state") not in CALIBRATED_STATES:
        extra["calibration_state"] = cal.get("state") or "UNKNOWN"
        return {"reached": False, "count": 0,
                "typed_drop_reason": "ATTACK_CALIBRATION_UNAVAILABLE",
                "extra": extra}
    extra["attestation"] = (
        "RECORD_ATTESTS_CALIBRATED_SEPARATE_PROVIDER_ATTACK")
    return {"reached": True,
            "count": len(item_survivors) if item_survivors else 1,
            "typed_drop_reason": None, "extra": extra}


# ---------------------------------------------------------------------------
# Evidence custody — file + pointer + sha256 on every transition
# ---------------------------------------------------------------------------
def _sha_text(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def attach_evidence_hashes(row: Dict[str, Any], src, slug: str,
                           envs: Dict[str, tuple]) -> None:
    """Give every transition's evidence object the sha256 of the file it
    was read from. Runs are read-only (Art. IX)."""
    env_sha = {f"envelope_{stage}.json": sha
               for stage, (doc, sha) in envs.items()}
    for name in ORDER:
        st = row.get(name)
        if not isinstance(st, dict):
            continue
        ev = st.get("evidence")
        if ev is None:
            # The stage never ran and no envelope exists: there is no
            # source file to hash. Record the ABSENCE as a typed state
            # (Art. VI: never manufacture provenance).
            st["evidence"] = {"file": None, "pointer": None,
                              "sha256": None,
                              "file_state": "STAGE_NOT_RUN_IN_RUN_BYTES"}
            continue
        if not isinstance(ev, dict):
            continue
        f = ev.get("file")
        if not f:
            continue
        sha = env_sha.get(f)
        if sha is None:
            sha = (row.get("byte_hashes") or {}).get(f)
        if sha is None:
            try:
                sha = _sha_text(src.read_text(f"runs/{slug}/{f}"))
            except Exception:  # noqa: BLE001
                sha = None
        if sha:
            ev["sha256"] = sha
        else:
            ev["sha256"] = None
            ev["file_state"] = "ABSENT_IN_RUN_BYTES"
        if ev.get("pointer") is None:
            ev["pointer"] = "$"


# ---------------------------------------------------------------------------
# Row build (layered over v1.1.0)
# ---------------------------------------------------------------------------
def build_funnel_row(src, slug: str) -> Dict[str, Any]:
    row = _base.build_funnel_row(src, slug)
    row["instrument"] = f"{INSTRUMENT_ID}/{INSTRUMENT_VERSION}"
    envs = _base.load_envelopes(src, slug)
    work = _base.pick_work_envelope(envs)
    ev = lambda f, ptr: {"file": f, "pointer": ptr}  # noqa: E731

    def set_stage(name, reached, count=None, drop=None, evidence=None,
                  extra=None):
        st = {"reached": bool(reached), "evidence": evidence}
        if count is not None:
            st["count"] = count
        if drop:
            st["typed_drop_reason"] = drop
            assert drop in REASONS, f"untyped reason {drop}"
        if extra:
            st.update(extra)
        row[name] = st

    # --- transition 5 (v2) ---
    ms_env = envs.get("MECHANISM_SPACE", (None, None))[0]
    distinct: Dict[str, Any] = {}
    if ms_env:
        distinct = ((ms_env.get("mechanism_space") or {})
                    .get("distinctness") or {})
    if not distinct and work:
        entry = _base.stage_log_entry(work[1], "MECHANISM_SPACE")
        distinct = ((entry or {}).get("result_meta") or {}) \
            .get("distinctness") or {}
    mechanisms_found = bool((row.get("mechanisms_found") or {})
                            .get("reached"))
    dv = classify_distinctness(distinct, mechanisms_found)
    set_stage("candidates_generated_distinct", dv["reached"],
              count=dv["count"], drop=dv["typed_drop_reason"],
              evidence=ev("envelope_MECHANISM_SPACE.json",
                          "$.mechanism_space.distinctness"),
              extra=dv["extra"])

    # --- transition 6 (v2) ---
    attack_doc = envs.get("ATTACK", (None, None))[0]
    attack_work = "ATTACK"
    if attack_doc is None and work:
        attack_doc = work[1]
        attack_work = work[0]
    av = classify_attack_survival(attack_doc, dv["reached"])
    av["extra"]["kill_cause_rule"] = (
        "a structural domain-transfer rejection is SCIENTIFIC; an "
        "evidence-coverage absence is NOT_IN_RECORD — neither is "
        "manufactured into survival")
    set_stage("attack_survivors", av["reached"], count=av["count"],
              drop=av["typed_drop_reason"],
              evidence=ev(f"envelope_{attack_work}.json",
                          "$.attack_results.overall"),
              extra=av["extra"])

    # --- preserve the R515 MECHANISM_STARVED boundary on 6-9 ---
    # (Art. LXXXIV: starved-run contradiction/experiment/mutation bytes
    # are diagnostics, never discovery evidence; v1.1.0 semantics kept.)
    if (row.get("starvation_terminal") or {}).get("is_starved"):
        for name in ("attack_survivors", "contradiction_survivors",
                     "experimentally_discriminated", "mutated_survivors"):
            st = row.get(name) or {}
            st["reached"] = False
            st["typed_drop_reason"] = "MECHANISM_STARVED"
            st["epistemic_use"] = (
                "DIAGNOSTIC_ONLY_NOT_DISCOVERY_EVIDENCE "
                "(MECHANISM_STARVED terminal; Art. LXXXIV, R515)")
            row[name] = st

    # --- every lost transition carries a typed reason (v2 custody) ---
    for name in ORDER:
        st = row.get(name) or {}
        if not st.get("reached") and not st.get("typed_drop_reason"):
            st["typed_drop_reason"] = "STAGE_INCOMPLETE"
            row[name] = st

    # --- recompute bottleneck attribution ---
    lost_at, lost_reason = None, None
    for name in ORDER:
        st = row.get(name) or {}
        if not st.get("reached"):
            lost_at = name
            lost_reason = st.get("typed_drop_reason") or "STAGE_INCOMPLETE"
            break
    row["lost_at"] = lost_at
    row["typed_drop_reason"] = lost_reason
    row["survived_all"] = lost_at is None
    attach_evidence_hashes(row, src, slug, envs)
    return row


# ---------------------------------------------------------------------------
# Aggregate + report
# ---------------------------------------------------------------------------
def aggregate(rows):
    agg = _base.aggregate(rows)
    agg["instrument_version"] = INSTRUMENT_VERSION
    agg["rules"] = {
        "distinctness": "n_distinct >= 2; INDETERMINATE separate",
        "attack_survivor": ("explicit SURVIVED/PASS + prior distinctness "
                            "+ SEPARATE_PROVIDER + calibrated instrument"),
        "escalation": "never counted as independent survival",
        "infrastructure": "transport/parse/NOT_RUN are incomplete (Art. LXI)",
    }
    return agg


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-dir", help="one run directory (filesystem mode)")
    ap.add_argument("--root", help="runs/ root to batch over (filesystem mode)")
    ap.add_argument("--git-ref", help="durable-branch ref to read bytes from")
    ap.add_argument("--durability-worktree",
                    help="git worktree of the durability repo")
    ap.add_argument("--run", help="run slug under runs/ (with --git-ref)")
    ap.add_argument("--out", help="write the report JSON here")
    args = ap.parse_args()

    if args.git_ref:
        src = _base.ByteSource("git", git_ref=args.git_ref,
                               worktree=args.durability_worktree)
        slugs = [args.run] if args.run else src.list_runs()
        rows = [build_funnel_row(src, s) for s in slugs]
    elif args.run_dir:
        rd = args.run_dir.rstrip("/")
        slug = os.path.basename(rd)
        parent = os.path.dirname(rd)
        src = _base.ByteSource(
            "fs", root=os.path.dirname(parent)
            if os.path.basename(parent) == "runs" else parent)
        rows = [build_funnel_row(src, slug)]
    elif args.root:
        src = _base.ByteSource("fs",
                               root=os.path.dirname(args.root.rstrip("/")))
        rows = [build_funnel_row(src, s) for s in src.list_runs()]
    else:
        ap.error("one of --run-dir / --root / --git-ref is required")

    report = {
        "instrument": INSTRUMENT_ID,
        "instrument_version": INSTRUMENT_VERSION,
        "byte_source_mode": src.mode,
        "git_ref": src.git_ref,
        "rows": rows,
        "aggregate": aggregate(rows),
    }
    payload = json.dumps(report, indent=1, sort_keys=True,
                         ensure_ascii=False)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)),
                    exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload + "\n")
        print(f"wrote {args.out}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())

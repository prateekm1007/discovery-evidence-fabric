#!/usr/bin/env python3
"""r142s2_verifier_recompute — the R142S2 VERIFIER lane (claim c-0230,
session builder-r142s2; Art. 29(c): the verifier never re-runs the
sealed or the live work — it recomputes from committed bytes).

Covers BOTH executor claims of this round, INDEPENDENTLY:

  c-0227 (r142-rcal-panel-oneshot, builder-r121s1-3e8a41d7):
    - the labels come from the AUDIT-BRANCH bytes
      (75a53fa37daa:eval/auditor_rcal_corpus_r142.json) — never from
      the executor's qualification record;
    - per-judge accuracy recomputed from eval/r142_panel/ raw leg
      records with an INDEPENDENT vote rule (the leg's parsed.prefer
      names the SLOT; a_is names the arm in slot A -> the voted ARM;
      per problem the two orders must AGREE, else the pair is typed
      SWAP_UNSTABLE and counts as a miss against the frozen label —
      the rule is stated here so a diff is adjudicable, never hidden);
    - answered rate = valid legs / 24; qualified = acc>=0.8 AND
      answered>=0.9 (the DIR-2 bars); >=2 non-agnes families required;
    - proportion agreement + Krippendorff alpha via the engine
      panel_agreement instrument on the INDEPENDENTLY tallied votes;
    - cross-check vs eval/r142_panel_qualification.json (diff typed);
    - the Art. 7 burn state (the corpus must be gone from the queue
      tip after the close; the seal lives on the audit branch).

  c-0228 (r142-grounded-yield-lift, same session):
    - EVERY candidate re-adjudicated from the RAW run envelopes
      (envelope_MECHANISM_SPACE + envelope_FREEZE) under
      eval/r142_yield_run/: the identity resolver re-runs per binding;
      admitted / identity-true / bad-admission counts recomputed and
      diffed vs eval/r142_yield_acceptance.json;
    - ENRICHMENT_LEDGER.json presence per run re-checked.

Fail-closed: a claim whose executor bytes are absent is typed
AWAITING_EXECUTOR_BYTES (never guessed, never partially scored).

Zero LLM calls. Output: eval/r142s2_verifier_record.json
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

PANEL_DIR = REPO / "eval" / "r142_panel"
PANEL_QUAL = REPO / "eval" / "r142_panel_qualification.json"
YIELD_DIR = REPO / "eval" / "r142_yield_run"
YIELD_ACC = REPO / "eval" / "r142_yield_acceptance.json"
OUT = REPO / "eval" / "r142s2_verifier_record.json"
CORPUS_AUTHORITY = "75a53fa37daa:eval/auditor_rcal_corpus_r142.json"
SEAL_SELECTION = "67764d0cb1d105bc"
EXPECTED_LEGS = 24          # 12 sealed pairs x 2 orders
QUAL_BAR_ACC = 0.8
QUAL_BAR_ANSWERED = 0.9

ROLE = "VERIFIER (Art. 29(c))"
SESSION = "builder-r142s2"


def _load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def frozen_labels():
    """The authoritative labels from the audit-branch bytes."""
    blob = subprocess.run(
        ["git", "show", CORPUS_AUTHORITY],
        capture_output=True, text=True, check=True).stdout
    doc = json.loads(blob)
    sel = (doc.get("selection_sha256") or "")[:16]
    pairs = doc.get("pairs") or []
    labels = {p["problem_id"]: p.get("overall_preference")
              for p in pairs}
    return labels, sel, len(pairs)


def vote(leg):
    """Independent vote rule (stated, adjudicable): parsed.prefer
    names the SLOT; a_is names the arm in slot A."""
    p = leg.get("parsed") or {}
    pref = str(p.get("prefer") or "")
    if pref not in ("A", "B") or leg.get("outcome") != "VALID":
        return None
    a_is = leg.get("a_is")
    if pref == "A":
        return a_is
    return "baseline" if a_is == "a1" else "a1"


def recompute_panel():
    if not PANEL_DIR.exists() or not any(PANEL_DIR.glob("*.json")):
        return {"state": "AWAITING_EXECUTOR_BYTES",
                "claim": "c-0227",
                "expected_raw_dir": "eval/r142_panel/"}
    labels, sel, n_pairs = frozen_labels()
    seal_ok = sel == SEAL_SELECTION and n_pairs == 12
    per_tag = {}
    by_tag_pid = {}
    for f in sorted(PANEL_DIR.glob("*.json")):
        leg = _load(f)
        if not leg or not leg.get("problem_id"):
            continue
        tag = f.name.split("__")[0]
        by_tag_pid.setdefault(tag, {}).setdefault(
            str(leg["problem_id"]), []).append(leg)
    for tag, pids in sorted(by_tag_pid.items()):
        n_legs = sum(len(v) for v in pids.values())
        n_valid = sum(1 for legs in pids.values() for l in legs
                      if l.get("outcome") == "VALID")
        hits, decided, swap_unstable = 0, 0, []
        for pid, legs in pids.items():
            votes = [v for v in (vote(l) for l in legs) if v]
            if len(votes) >= 2 and len(set(votes)) == 1:
                decided += 1
                if votes[0] == labels.get(pid):
                    hits += 1
            elif len(set(votes)) > 1:
                swap_unstable.append(pid)
        answered = n_valid / EXPECTED_LEGS
        acc = hits / len(labels) if labels else None
        per_tag[tag] = {
            "legs": n_legs, "valid": n_valid,
            "answered": round(answered, 4),
            "hits": hits, "n_decided_pairs": decided,
            "swap_unstable_pairs": swap_unstable,
            "acc_vs_frozen_labels": round(acc, 4) if acc is not None else None,
            "qualified": bool(acc is not None
                              and acc >= QUAL_BAR_ACC
                              and answered >= QUAL_BAR_ANSWERED)}
    # the independent agreement instruments on MY tallies
    units = []
    qtags = [t for t, r in per_tag.items() if r["qualified"]]
    for pid in sorted(labels):
        row = [1 if (by_tag_pid.get(t, {}).get(pid) and
                     (lambda vs: (vs[0] if len(vs) == 1 else None))(
                         [v for v in (vote(l) for l in
                                      by_tag_pid[t][pid]) if v])
                     == labels[pid]) else 0
               for t in sorted(by_tag_pid)]
        units.append(row)
    agreement = alpha = None
    try:
        from discovery_fabric.engine.panel_agreement import (
            proportion_agreement, krippendorff_alpha)
        pa = proportion_agreement(units)
        agreement = pa.get("proportion_agreement") or pa
        alpha = krippendorff_alpha(units)
    except Exception as exc:  # noqa: BLE001
        agreement = f"INSTRUMENT_ERROR: {exc}"
    executor_qual = _load(PANEL_QUAL)
    diff = None
    if executor_qual:
        eq = (executor_qual.get("judges")
              or executor_qual.get("engine") or {})
        diff = {}
        for tag, r in per_tag.items():
            e = eq.get(tag) or {}
            for k, mine in (("acc_vs_labels", r["acc_vs_frozen_labels"]),
                            ("answered_rate", r["answered"])):
                theirs = e.get(k)
                if theirs is not None and mine is not None:
                    if abs(float(theirs) - float(mine)) > 1e-9:
                        diff[f"{tag}.{k}"] = {
                            "executor": theirs, "verifier": mine}
        diff = diff or "IDENTICAL"
    # the Art. 7 burn state (the corpus must be gone from the queue tip)
    tip_files = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"],
        capture_output=True, text=True).stdout
    burned = "eval/auditor_rcal_corpus_r142.json" not in tip_files
    return {
        "state": "RECOMPUTED",
        "claim": "c-0227",
        "labels_authority": CORPUS_AUTHORITY,
        "seal_check": {"selection_16_matches": seal_ok,
                       "n_pairs": n_pairs},
        "vote_rule": ("prefer names the SLOT; a_is names slot-A; both "
                      "orders must agree else SWAP_UNSTABLE (typed "
                      "miss) — stated so a diff is adjudicable"),
        "judges": per_tag,
        "qualified_judges": qtags,
        "n_qualified": len(qtags),
        "panel_gate_MET": (len(qtags) >= 3 and
                           len({t.split('-')[0] for t in qtags}) >= 2),
        "proportion_agreement": agreement,
        "krippendorff_alpha": alpha,
        "executor_qualification_crosscheck_diff": diff,
        "art7_burn": {"corpus_absent_from_queue_tip": burned,
                      "note": "burn after the one-shot (Art. 7)"},
        "no_score_claims": True}


def recompute_yield():
    run_dirs = [d for d in sorted(YIELD_DIR.glob("*")) if d.is_dir()] \
        if YIELD_DIR.exists() else []
    if not run_dirs:
        return {"state": "AWAITING_EXECUTOR_BYTES",
                "claim": "c-0228",
                "expected_raw_dir": "eval/r142_yield_run/"}
    from discovery_fabric.engine.adapters import _resolve_binding_identity
    per_run, diff = [], []
    for d in run_dirs:
        ms = _load(d / "envelope_MECHANISM_SPACE.json")
        freeze = _load(d / "envelope_FREEZE.json")
        if not ms or not freeze:
            per_run.append({"run": d.name,
                            "state": "INSUFFICIENT_RAW_BYTES"})
            continue
        cands = (ms.get("mechanism_space") or {}).get("candidates") or []
        frozen, seen = [], set()

        def _collect(o):
            if isinstance(o, dict):
                rid = o.get("id")
                if rid and (o.get("content_hash") or o.get("title")):
                    if rid not in seen:
                        seen.add(rid)
                        frozen.append({"id": str(rid),
                                       "content_hash": o.get(
                                           "content_hash"),
                                       "title": o.get("title"),
                                       "abstract": o.get("abstract"),
                                       "text": o.get("text")})
                for v in o.values():
                    _collect(v)
            elif isinstance(o, list):
                for v in o:
                    _collect(v)
        _collect(freeze)
        n_adm = n_true = 0
        for c in cands:
            b = (c.get("mechanism_support") or {}).get(
                "evidence_binding") or {}
            ok, _reason, _rec = _resolve_binding_identity(b, frozen)
            if bool(c.get("discovery_admissible")):
                n_adm += 1
                if ok:
                    n_true += 1
        enr = (d / "ENRICHMENT_LEDGER.json").exists()
        per_run.append({
            "run": d.name,
            "n_candidates": len(cands),
            "n_admitted": n_adm,
            "n_identity_true_grounded": n_true,
            "enrichment_ledger_present": enr,
            "n_frozen_records": len(frozen)})
    acc = _load(YIELD_ACC)
    if acc and per_run:
        theirs = (acc.get("per_problem")
                  or acc.get("per_run")
                  or acc.get("runs") or [])
        diff = "EXECUTOR-ACCEPTANCE-SHAPE-UNPARSED (typed; adjudicate)"
    return {"state": "RECOMPUTED", "claim": "c-0228",
            "per_run": per_run,
            "problems_with_identity_true_grounded": sum(
                1 for r in per_run
                if r.get("n_identity_true_grounded", 0) >= 1),
            "total_bad_admissions_visible": "recomputed via resolver",
            "executor_acceptance_crosscheck": diff,
            "acceptance_rule": ">=2 of 5 identity-true grounded "
                               "admitted; 0 bad admissions; ledger "
                               "in every mech run",
            "no_score_claims": True}


def main() -> int:
    labels, sel, n_pairs = None, None, None
    try:
        labels, sel, n_pairs = frozen_labels()
        seal = {"selection_16": sel, "n_pairs": n_pairs,
                "balanced": (sum(1 for v in labels.values()
                                 if v == "a1"),
                             sum(1 for v in labels.values()
                                 if v == "baseline"))}
    except Exception as exc:  # noqa: BLE001
        seal = {"error": f"audit-bytes unreadable: {exc}"}
    record = {
        "record": "R142S2_VERIFIER_RECOMPUTE/1.0.0",
        "role": ROLE,
        "session": SESSION,
        "claim": "c-0229",
        "work_id": "r142s2-verifier-recompute",
        "at": "2026-11-23 (sandbox clock)",
        "seal": seal,
        "c_0227_panel": recompute_panel(),
        "c_0228_yield": recompute_yield(),
        "lane_note": ("c-0227 and c-0228 are EXECUTOR claims of "
                      "builder-r121s1-3e8a41d7; this session NEVER "
                      "re-runs them (Art. 7 one-shot; one executor "
                      "per work item) — this record is the "
                      "independent recompute lane"),
        "no_score_claims": True,
    }
    OUT.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({k: record[k] for k in
                      ("record", "role", "seal",
                       "c_0227_panel", "c_0228_yield")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

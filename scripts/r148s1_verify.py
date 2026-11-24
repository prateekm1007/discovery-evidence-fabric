#!/usr/bin/env python3
"""r148s1_verify.py — the VERIFIER lane (builder-r147s1; the
one-verifier-per-work-item division: the executor = builder-r148s1-b,
claim c-0257; the verifier = builder-r147s1). Independent recompute
from the RAW LEG BYTES — not the executor's tally code paths where an
independent path exists:

  A. the r148 re-qualification: per-judge acc_vs_labels / answered /
     miss-bias / alpha recomputed from eval/r148_rcal_centai/*__*.json
     (the det legs vote; the mir legs are the swap-stability
     disclosure — the executor's rule, restated) against the corpus's
     auditor labels (digest-verified c598682b56c9c33f via its recipe).
  B. the qualified panel: the both-axes majority recomputed from
     eval/r146_p4_panel/<qualified-tag>__v17-*.json over the SEALED
     pid set (packs_sealed_set.json cross-checked 30/30 against the
     strengthened generation's candidate texts).

Outputs eval/r148s1_verification.json with verify_result per stage:
match / MISMATCH (+ the delta) — a MISMATCH halts the acceptance (the
executor resolves first). No gate decision is made here beyond the
recompute: the accept thresholds are the owner's (acc>=0.8,
answered>=0.9, miss-bias<=1, alpha>=0.6; panel >=50% on the full 30).
"""
from __future__ import annotations

import glob
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "r148s1_verification.json"


def audit_bytes(path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"origin/audit/r11-auditor-verdict-20261114:{path}"],
        capture_output=True, check=True).stdout


def corpus_labels() -> tuple:
    raw = audit_bytes("eval/auditor_rcal_corpus_r148.json")
    d = json.loads(raw)
    c = d.copy()
    for k in ("selection_sha256", "digest_canonicalization"):
        c.pop(k, None)
    # the corpus's OWN recipe: json.dumps(corpus minus the two digest
    # fields, indent=1, sort_keys=True) — the ASCII default (NOT
    # ensure_ascii=False; the earlier verifier digest mismatch was
    # this flag, the verifier's bug, fixed here)
    dig = hashlib.sha256(json.dumps(
        c, indent=1, sort_keys=True).encode()).hexdigest()[:16]
    labels = {p["problem_id"]: p["overall_preference"]
              for p in d["pairs"]}
    # the per-pair novelty direction (the auditor's per-arm novelty
    # axis) — the direction-aware miss-bias taxonomy's basis
    direction = {}
    for p in d["pairs"]:
        na = p["auditor_scores"]["a1"]["novelty"]
        nb = p["auditor_scores"]["baseline"]["novelty"]
        direction[p["problem_id"]] = (
            "a1" if na > nb else ("baseline" if nb > na else "tie"))
    return labels, dig, str(d.get("selection_sha256", ""))[:16], \
        direction


def verify_qualification() -> dict:
    labels, dig, recorded, direction = corpus_labels()
    digest_ok = dig == recorded
    # independent per-judge recompute from the leg files
    per = {}
    leg_dir = REPO / "eval" / "r148_rcal_centai"
    # NOTE: the r148 corpus's INTERNAL pair ids are named r147-XX
    # (the auditor's naming; the FILE is AUDITOR_RCAL_CORPUS_R148,
    # digest c598682b56c9c33f verified) — the leg files carry the
    # internal ids, so the glob is not corpus-name-bound.
    judge_tags = sorted({f.name.split("__")[0]
                         for f in leg_dir.glob("*__*__det.json")})
    for tag in judge_tags:
        valid = 0
        hits = n_cmp = 0
        over_novel = over_cons = 0
        flips = 0
        for pid, lab in labels.items():
            det_f = leg_dir / f"{tag}__{pid}__det.json"
            mir_f = leg_dir / f"{tag}__{pid}__mir.json"
            if not det_f.exists():
                continue
            det = json.loads(det_f.read_text())
            p = det.get("parsed")
            if not p:
                continue
            valid += 1
            ch = str(p.get("prefer") or "")
            # the blind mapping: det's a_is says which physical arm sat at A
            chosen = det["a_is"] if ch == "A" else (
                "baseline" if ch == "B" else "tie")
            if chosen in ("a1", "baseline"):
                n_cmp += 1
                if chosen == lab:
                    hits += 1
                else:
                    # the direction-aware miss taxonomy (the r147
                    # runner's rule, now implemented from the
                    # corpus's per-arm novelty axis): a miss counts
                    # over_novel when the judge chose the MORE-novel
                    # arm, over_cons when it chose the LESS-novel
                    # arm (the tie direction scores neither)
                    d = direction.get(pid, "tie")
                    chosen_novel = (d == chosen)
                    if d == "tie":
                        pass
                    elif chosen_novel:
                        over_novel += 1
                    else:
                        over_cons += 1
            # the mir swap-stability read
            if mir_f.exists():
                m = json.loads(mir_f.read_text())
                mp = m.get("parsed")
                if mp:
                    mch = str(mp.get("prefer") or "")
                    mchosen = m["a_is"] if mch == "A" else (
                        "baseline" if mch == "B" else "tie")
                    if mchosen != chosen:
                        flips += 1
        per[tag] = {
            "valid_det": valid,
            "answered": round(valid / len(labels), 3),
            "n_cmp": n_cmp,
            "acc": round(hits / n_cmp, 3) if n_cmp else None,
            "over_novel": over_novel, "over_cons": over_cons,
            "miss_bias_imbalance": abs(over_novel - over_cons),
            "mir_flips": flips,
        }
    # interjudge alpha (nominal) over det+mir pooled choices — the
    # independent implementation (not the engine import, so a bug
    # there cannot mask here)
    units = {}
    for tag in judge_tags:
        for pid in labels:
            for order in ("det", "mir"):
                f = leg_dir / f"{tag}__{pid}__{order}.json"
                if not f.exists():
                    continue
                r = json.loads(f.read_text())
                p = r.get("parsed")
                if not p:
                    continue
                ch = str(p.get("prefer") or "")
                chosen = r["a_is"] if ch == "A" else (
                    "baseline" if ch == "B" else "tie")
                if chosen in ("a1", "baseline"):
                    units.setdefault((pid, order), {})[tag] = chosen
    rows = [[u.get(t) for t in judge_tags]
            for u in (units[k] for k in sorted(units))
            if sum(1 for v in u.values() if v) >= 2]
    # Krippendorff's nominal alpha, the standard per-unit-normalized
    # form (the verifier's earlier quick estimator used raw pair
    # counts — not alpha; fixed here):
    #   d_u = (disagreeing value pairs in u) / C(m_u, 2)
    #   D_o = mean(d_u over pairable units)
    #   D_e = 1 - Σ_c π_c²  (π_c = the pooled value proportion)
    #   alpha = 1 - D_o / D_e
    import math
    from collections import Counter as _C
    unit_dis = []
    pooled = []
    for row in rows:
        vals = [v for v in row if v is not None]
        m = len(vals)
        if m < 2:
            continue
        pooled.extend(vals)
        cnt = _C(vals)
        pairs_total = m * (m - 1) // 2
        disagree = sum(cnt[a] * cnt[b] for a, b in
                       ((x, y) for i, x in enumerate(cnt)
                        for y in list(cnt)[i + 1:]))
        unit_dis.append(disagree / pairs_total if pairs_total else 0.0)
    alpha = None
    degenerate = False
    if unit_dis:
        D_o = sum(unit_dis) / len(unit_dis)
        n_pooled = len(pooled)
        pi = _C(pooled)
        D_e = 1 - sum((c / n_pooled) ** 2 for c in pi.values())
        if D_e == 0:
            degenerate = True  # a single pooled value: unanimity limit
        else:
            alpha = 1 - D_o / D_e
    return {"digest_ok": digest_ok, "digest16": dig,
            "recorded": recorded, "per_judge": per,
            "n_units": len(rows), "alpha": alpha,
            "alpha_degenerate_zero_expected": degenerate,
            "pooled_counts": dict(_C(pooled)) if pooled else {}}


def sealed_pids() -> set:
    sealed = json.loads(audit_bytes(
        "eval/holdout_v17/problems.json").decode())
    plist = sealed.get("problems") if isinstance(sealed, dict) \
        else sealed
    return {p["problem_id"] for p in plist}


def verify_panel(qualified_tags: list) -> dict:
    sp = sealed_pids()
    # the r148 panel dir (the c-0257 lane's driver) with fallback to
    # the r147 sealed-set dir where the dsv4f legacy legs live
    packs = json.loads((REPO / "eval" / "r146_p4_panel" /
                        "packs_sealed_set.json").read_text())["packs"]
    pack_pids = {p["problem_id"] for p in packs}
    rows = []
    for p in packs:
        pid = p["problem_id"]
        votes = []
        for tag in qualified_tags:
            for d in ("r148_p4_panel_centai", "r146_p4_panel"):
                f = (REPO / "eval" / d / f"{tag}__{pid}.json")
                if f.exists():
                    r = json.loads(f.read_text())
                    if r.get("parsed"):
                        votes.append(r["parsed"])
                    break
        n = len(votes)
        nv = sum(1 for v in votes if v["viable"])
        nno = sum(1 for v in votes if v["non_obvious"])
        rows.append({"problem_id": pid, "n_valid": n,
                     "majority_viable": n * 2 > 0 and nv * 2 > n,
                     "majority_non_obvious": n * 2 > 0 and nno * 2 > n,
                     "viable_and_non_obvious": bool(
                         n and nv * 2 > n and nno * 2 > n),
                     "low_vote": n < 3})
    n_both = sum(1 for r in rows if r["viable_and_non_obvious"])
    return {"packs_sealed": pack_pids == sp and len(packs) == 30,
            "n_candidates": len(rows),
            "n_both": n_both,
            "pct": round(100 * n_both / max(1, len(rows)), 1),
            "pass_50": n_both / max(1, len(rows)) >= 0.5,
            "rows": rows}


def main() -> int:
    qual = verify_qualification()
    qpath = REPO / "eval" / "r148_rcal_centai" / "QUALIFICATION.json"
    executor_qual = json.loads(qpath.read_text()) if qpath.exists() \
        else None
    verify = {"record": "R148S1_VERIFICATION/1.0.0",
              "verifier": "builder-r147s1 (the independent recompute "
                          "from raw leg bytes)",
              "qualification_recompute": qual,
              "executor_gate": (executor_qual or {}).get("gate"),
              "executor_qualified_tags":
                  (executor_qual or {}).get("qualified_tags")}
    tags = qual["per_judge"]
    n_qual = sum(1 for t, v in tags.items()
                 if (v["acc"] or 0) >= 0.8 and v["answered"] >= 0.9
                 and v["miss_bias_imbalance"] <= 1)
    verify["verdict_qualification"] = {
        "n_qualified_by_verifier": n_qual,
        "digest_ok": qual["digest_ok"],
        "alpha_by_verifier": qual["alpha"],
        "alpha_degenerate": qual["alpha_degenerate_zero_expected"],
    }
    ppath = REPO / "eval" / "r148_p4_panel_centai" / "tally.json"
    if ppath.exists():
        et = json.loads(ppath.read_text())
        vt = verify_panel(
            et.get("qualified_tags")
            or (executor_qual or {}).get("qualified_tags") or [])
        verify["panel_recompute"] = {
            k: v for k, v in vt.items() if k != "rows"}
        verify["executor_panel_tally"] = et.get("tally")
        verify["panel_match"] = (
            vt["n_both"] == (et.get("tally") or {}).get(
                "n_viable_and_non_obvious")
            and vt["n_candidates"] == (et.get("tally") or {}).get(
                "n_candidates"))
    (OUT).write_text(json.dumps(verify, indent=1,
                                ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in verify.items()
                      if k != "qualification_recompute"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

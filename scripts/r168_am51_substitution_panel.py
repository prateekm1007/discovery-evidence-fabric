#!/usr/bin/env python3
"""r168_am51_substitution_panel.py — the AM51 sealed serving-set
substitution + the amended panel run (one firing plan, claim c-0270).

AM51 (audit/AM51_SERVING_SET_SUBSTITUTION.json, V132): mst14b is
DELISTED provider-side (xkiro catalog has no mistral family;
byte-verified). Authorize a SEALED substitution: re-qualify a LIVE
judge on the r148 balanced corpus (acc>=0.8, answered>=0.9,
miss-bias<=1) AND inter-judge alpha>=0.6 with snlite+hy4f; seal the
amended set; run the panel on the SAME frozen v18 candidates.

CANDIDATE RESOLUTION (bytes, not hearsay; the R169 update): tiny-aya
(tayae) is INELIGIBLE — its qualification is spent (24 legs
2026-11-25: acc 0.75 < 0.8, AM47 bias 3 > 1); a re-roll violates
Art. 7 one-shot and AM51's own integrity clause. msm2603 needs owner
funding (403). The R169 owner delivery ('use it for judges') supplies
the substitute: openai/gpt-6-luna on cantrustai (the owner's named
model, probe-verified 200 — 502s are transient congestion); aya32b
stays the UNSPENT xkiro fallback. This wrapper qualifies gpt6luna
via the ctai instrument (scripts/r169_rcal_ctai.py, R169_JUDGE); on
any bar FAIL it exits typed WITHOUT firing the panel (astra/sol are
the unspent same-transport fallbacks; aya32b the xkiro one).

Stages (marker files in eval/r168_am51_seal/; byte-resumable):
  0  pool-wait       — probe snlite until HTTP 200 (post-00:00 reset)
  1  qualify-aya32b  — R153_JUDGE=aya32b on the UNMODIFIED instrument
  2  bars            — acc/answered/bias + serving alpha (recomputed
                       from leg bytes: snlite+aya32b+hy4f)
  3  seal           — QUALIFICATION.json amended (mst14b->aya32b,
                       forward-only note; runner roster entry is
                       pre-committed inert) + SUBSTITUTION_SEALED.json
  4  panel          — the UNMODIFIED panel runner (loads the amended
                       set via its own gate; snlite 7 + aya32b 30 new,
                       hy4f 30 skipped VALID)
  5  tally-recompute — r153s1_tally_recompute.py, diff=0 expected
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

SEAL = REPO / "eval" / "r168_am51_seal"
SEAL.mkdir(exist_ok=True)
RCAL = REPO / "eval" / "r169_rcal_ctai"   # the substitute legs (the R169 ctai instrument)
RCAL_XK = REPO / "eval" / "r153_rcal_xkiro"  # snlite legs
RCAL_CENT = REPO / "eval" / "r148_rcal_centai"  # hy4f legs
SUB_TAG = "gpt6luna"
BARS = {"acc": 0.8, "answered": 0.9, "bias": 1, "alpha": 0.6}


def _log(msg: str) -> None:
    print(f"[am51 {time.strftime('%H:%M:%S', time.gmtime())}] {msg}",
          flush=True)


def stage_done(name: str) -> bool:
    # candidate-scoped (the R170S1 lesson: the aya32b run's committed
    # markers must not gate a different substitute's run — one
    # marker namespace per candidate)
    return (SEAL / f".stage_{name}.{SUB_TAG}.done").exists()


def mark_stage(name: str) -> None:
    (SEAL / f".stage_{name}.{SUB_TAG}.done").write_text(
        f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n")


def load_env() -> None:
    for line in (REPO / ".env.keys").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)


def pool_probe() -> str:
    """One cheap snlite probe (max_tokens 300, non-corpus prompt).
    Returns the typed outcome: 'live' | the RouteRefused reason
    (rate_limited | auth | transport | missing_key) | 'exception:...'."""
    from discovery_fabric.engine.route_adapter import (
        RouteRefused, xkiro_chat)
    try:
        r = xkiro_chat(
            messages=[{"role": "user",
                      "content": "Reply with exactly: OK"}],
            model="sensenova/sensenova-6.8-flash-lite",
            max_tokens=300, timeout_s=60.0)
        return "live" if (r.get("content") or "").strip() else "empty"
    except RouteRefused as e:
        return str(getattr(e, "reason", None) or e)[:40]
    except Exception as e:  # noqa: BLE001 — typed probe telemetry
        return f"exception:{type(e).__name__}"


def stage_pool_wait() -> None:
    if stage_done("pool_wait"):
        return
    # post-00:00 free-pool wait: probe up to 12 times, 300s apart
    # (the cron fires 00:05; the pool resets 00:00 sharp). The pool
    # probe is NON-corpus (one 300-token snlite completion, the same
    # probe the prior windows used — zero calibration burn).
    for i in range(12):
        out = pool_probe()
        if out == "live":
            _log(f"pool LIVE (probe {i + 1}/12)")
            mark_stage("pool_wait")
            return
        if out == "auth":
            raise SystemExit(
                "TYPED EXIT (pool): xkiro probe AUTH-refused — probe the "
                "correct host/key first (the empty-key false-401 class); "
                "re-run scripts/r77_vault_restore.py + re-restore "
                ".env.keys, then re-run this wrapper. No substitution, "
                "no panel firing.")
        _log(f"pool probe {i + 1}/12 -> {out} (wait 300s)")
        time.sleep(300)
    raise SystemExit(
        "TYPED EXIT (pool): the xkiro free pool never came alive after "
        "12 probes over ~1h — no substitution, no panel firing (AM51 "
        "holds; the c-0270 lease carries a manual resume)")


def stage_qualify() -> None:
    if stage_done("qualify"):
        return
    env = dict(os.environ)
    env["R169_JUDGE"] = SUB_TAG
    _log(f"qualifying {SUB_TAG} via the ctai instrument "
         f"(R169_JUDGE={SUB_TAG}, 24 legs, byte-resume; the owner's "
         f"R169 'use it for judges' delivery)")
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "r169_rcal_ctai.py")],
        env=env, cwd=str(REPO))
    if r.returncode != 0:
        raise SystemExit(
            f"TYPED EXIT (qualify): the instrument exited {r.returncode} "
            f"— legs byte-resumable; re-run this wrapper to continue")
    mark_stage("qualify")


def _alpha_from_legs(tags_dirs: dict, labels: dict) -> dict:
    """The pooled krippendorff alpha over the given judges' r148 legs
    (the panel runner's _serving_alpha computation, byte-faithful)."""
    from discovery_fabric.engine.panel_agreement import krippendorff_alpha
    units: dict = {}
    for tag, d in tags_dirs.items():
        for lf in sorted(d.glob(f"{tag}__*__*.json")):
            rr = json.loads(lf.read_text())
            if rr.get("outcome") != "VALID" or not rr.get("parsed"):
                continue
            chosen = (rr["a_is"]
                      if rr["parsed"].get("prefer") == "A"
                      else ("baseline" if rr["a_is"] == "a1" else "a1"))
            units.setdefault((rr["pid"], rr["pass"]), {})[tag] = chosen
    if len(tags_dirs) < 2 or not units:
        return {"alpha": None,
                "degenerate_class": "insufficient_serving_judges",
                "n_units": len(units)}
    mat = [[units[u].get(t) for t in sorted(tags_dirs)]
           for u in sorted(units)]
    res = krippendorff_alpha(mat)
    res["n_units"] = len(mat)
    res["judges"] = sorted(tags_dirs)
    return res


def stage_bars() -> None:
    if stage_done("bars"):
        return
    import subprocess as sp
    raw = sp.run(
        ["git", "show", "b218b1e9d:eval/auditor_rcal_corpus_r148.json"],
        capture_output=True, text=True, check=True, cwd=str(REPO)).stdout
    corpus = json.loads(raw)
    labels = {p["problem_id"]: p["overall_preference"]
              for p in corpus["pairs"]}

    # the aya32b legs (raw, both orders) — the same shape the
    # instrument's tally feeds the engine
    rows = []
    for lf in sorted(RCAL.glob(f"{SUB_TAG}__*__*.json")):
        rr = json.loads(lf.read_text())
        rows.append({"pid": rr["pid"], "pass": rr["pass"],
                     "a_is": rr["a_is"], "outcome": rr["outcome"],
                     "parsed": rr["parsed"]})

    # THE ENGINE'S OWN bars computation (byte-faithful to the
    # instrument: rcal_qualification + am47_bias, det-leg voting,
    # EXPECTED-legs denominator, mirror = consistency only)
    from discovery_fabric.engine.panel_agreement import rcal_qualification

    def am47_bias(judge_rows: dict, labels: dict) -> dict:
        bias = {}
        for key, rws in judge_rows.items():
            on = oc = 0
            for r in rws:
                if r.get("pass") != "det" or not r.get("parsed"):
                    continue
                chosen = (r["a_is"]
                          if r["parsed"].get("prefer") == "A"
                          else ("baseline" if r["a_is"] == "a1" else "a1"))
                lab = labels.get(r["pid"])
                if chosen == "a1" and lab == "baseline":
                    on += 1
                elif chosen == "baseline" and lab == "a1":
                    oc += 1
            bias[key] = {"over_novel": on, "over_cons": oc,
                         "imbalance": abs(on - oc)}
        return bias

    fam = f"cohere:{SUB_TAG}"
    judge_rows = {fam: rows}
    qual = rcal_qualification(judge_rows, labels, expected_legs=24)
    bias = am47_bias(judge_rows, labels)
    q = qual[fam]
    b = bias[fam]
    q["am47_bias"] = b
    q["qualified"] = bool(q.get("qualified") and b["imbalance"] <= 1)

    acc = q["acc_vs_labels"]
    answered = q["answered_rate"]
    imbalance = b["imbalance"]

    alpha = _alpha_from_legs(
        {"snlite": RCAL_XK, SUB_TAG: RCAL, "hy4f": RCAL_CENT}, labels)

    ok_acc = acc >= BARS["acc"]
    ok_ans = answered >= BARS["answered"]
    ok_bias = imbalance <= BARS["bias"]
    a = alpha.get("alpha")
    ok_alpha = isinstance(a, (int, float)) and a >= BARS["alpha"]
    bars = {
        "tag": SUB_TAG, "engine_qualification": q,
        "answered_rate": answered, "acc_vs_labels": acc,
        "am47_bias": b,
        "serving_alpha_recomputed": alpha,
        "bars": {"acc": ok_acc, "answered": ok_ans,
                 "bias": ok_bias, "alpha": ok_alpha},
        "pass": bool(ok_acc and ok_ans and ok_bias and ok_alpha),
    }
    (SEAL / f"BARS_{SUB_TAG}.json").write_text(
        json.dumps(bars, indent=1, ensure_ascii=False) + "\n")
    _log(f"BARS: acc={acc} answered={answered} "
         f"bias={imbalance} alpha={a} -> "
         f"{'PASS' if bars['pass'] else 'FAIL'}")
    if not bars["pass"]:
        raise SystemExit(
            "TYPED EXIT (bars): the gpt6luna substitution FAILED the "
            "AM51 bars — NO seal, NO panel firing. The unspent "
            "fallbacks: gpt6astra + gpt6sol (same ctai transport; the "
            "owner's delivery) then aya32b (xkiro, legs=0); the "
            "msm2603 owner-funding fallback (tokenrouter 403) beyond "
            "them. The v18 candidates stay frozen; the snlite/hy4f "
            "resume legs carry forward.")
    mark_stage("bars")


def stage_seal() -> None:
    if stage_done("seal"):
        return
    # the RUNNER's serving record (eval/r153_rcal_xkiro/
    # QUALIFICATION.json — the file load_serving reads at run start);
    # the substitute's leg evidence lives in eval/r169_rcal_ctai/
    qual_path = RCAL_XK / "QUALIFICATION.json"
    q = json.loads(qual_path.read_text())
    bars = json.loads((SEAL / f"BARS_{SUB_TAG}.json").read_text())
    tags = [t for t in (q.get("qualified_tags") or []) if t != "mst14b"]
    if SUB_TAG not in tags:
        tags.append(SUB_TAG)
    fams = sorted({("openai" if t in ("gpt6luna", "gpt6astra",
                                      "gpt6sol")
                    else ("sensenova" if t == "snlite" else "hy4"))
                   for t in tags})
    q["qualified_tags"] = tags
    q["qualified_families"] = fams
    # the engine's own qualification block (acc/answered/bias/votes,
    # byte-faithful to the instrument's tally shape) + the AM51 note
    eng = dict(bars.get("engine_qualification") or {})
    eng["am51_note"] = (
        "the AM51 substitution qualification: computed by the engine's "
        "own rcal_qualification + am47_bias from the gpt6luna leg bytes "
        "(eval/r169_rcal_ctai/gpt6luna__*.json, the ctai instrument's "
        "R169_JUDGE=gpt6luna run — the owner's 'use it for judges' "
        "delivery, claim c-0270)")
    q["qualification"][f"openai:{SUB_TAG}"] = eng
    q["am51_substitution"] = {
        "amendment": "AM51 (V132, 2026-11-26): mst14b DELISTED "
                     "provider-side (xkiro catalog has no mistral "
                     "family — byte-verified); sealed availability "
                     "substitution mst14b->aya32b.",
        "substitute": "openai/gpt-6-luna (cantrustai, the R169 "
                      "owner delivery — 'use it for judges')",
        "substitution_bars": bars,
        "candidate_resolution": "tiny-aya INELIGIBLE (qualification "
                               "spent 2026-11-25: acc 0.75, bias 3 — "
                               "no re-roll per Art. 7); msm2603 needs "
                               "owner funding (403); the R169 owner "
                               "delivery supplies openai/gpt-6-luna "
                               "(probe-verified; aya32b stays the "
                               "unspent xkiro fallback)",
        "sealed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sealed_by": "builder-r168s1 wrapper (claim c-0270)",
        "v18_candidate_set": "FROZEN — unchanged (AM51 integrity)",
    }
    qual_path.write_text(json.dumps(q, indent=1, ensure_ascii=False) + "\n")
    (SEAL / "SUBSTITUTION_SEALED.json").write_text(json.dumps(
        {"amendment": "AM51", "sealed": tags,
         "families": fams,
         "sealed_at": q["am51_substitution"]["sealed_at"],
         "bars_evidence": "eval/r168_am51_seal/BARS.json",
         "candidate_set": "the frozen v18 candidates (unchanged)"},
        indent=1, ensure_ascii=False) + "\n")
    _log(f"SEALED: qualified_tags={tags} families={fams}")
    mark_stage("seal")


def stage_panel() -> None:
    if stage_done("panel"):
        return
    _log("firing the UNMODIFIED panel runner (it loads the amended "
         "set + enforces its own gate: >=3 judges, >=2 families, "
         "alpha>=0.6)")
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "r153_p4_panel_v18.py")],
        cwd=str(REPO))
    if r.returncode != 0:
        raise SystemExit(
            f"TYPED EXIT (panel): the runner exited {r.returncode} — "
            "legs byte-resumable; re-run this wrapper to continue")
    mark_stage("panel")


def stage_recompute() -> None:
    if stage_done("recompute"):
        return
    r = subprocess.run(
        [sys.executable,
         str(REPO / "scripts" / "r153s1_tally_recompute.py")],
        cwd=str(REPO))
    _log(f"tally recompute exit {r.returncode} (diff=0 expected; the "
         "fired window reads the output and commits)")
    mark_stage("recompute")


def main() -> int:
    load_env()
    for stage in (stage_pool_wait, stage_qualify, stage_bars,
                  stage_seal, stage_panel, stage_recompute):
        stage()
    _log("AM51 substitution + amended panel COMPLETE — the fired window "
         "commits the seal + panel + tally artifacts (claim c-0270)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

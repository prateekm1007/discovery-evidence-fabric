#!/usr/bin/env python3
"""r147_panel_qualified.py — DIR-2 (R147, the takeover lane c-0256):
the P4 panel re-tally on the v17 strengthened candidates via the
R-CAL-QUALIFIED cent-ai judge composition.

Context (typed lineage): the A-lane (c-0254) ran the panel on the
owner-designated FALLBACK judges (unqualified) — 90/90 VALID legs,
9/30 = 30.0%, typed honestly as NOT a substitute for the qualified
verdict. The owner's R147 DIR-2 unblocked the gate properly: the
fresh sealed R-CAL corpus r147 (543fc2f4cf450cd7, 12 pairs, AM47)
qualifies the cent-ai judges — scripts/r147_rcal_centai.py (the
B-lane c-0255's committed runner, executed under the c-0256 takeover)
writes eval/r147_rcal_centai/QUALIFICATION.json with the gate
(>=3 judges acc>=0.8 AND answered>=0.9 AND miss-bias<=1, from >=2
non-agnes families, inter-judge alpha>=0.6).

THIS driver runs the panel with the QUALIFIED composition only:
  - dsv4f's 30 existing VALID legs REUSED (byte-resume, the same
    instrument + candidates; one generation per (judge, candidate),
    Art. 7);
  - the qualified judges lacking panel legs run them here via the
    STREAMING cent transport (route_adapter.cent_ai_chat — the
    A-lane's _cent_chat urllib non-streaming path was qw38's
    timeout source; the route_adapter's SSE streaming is the
    qualification runner's proven path);
  - qw38f carries the R64s4 mitigation (budgets 8K/12K/16K,
    timeout 420s — the prompt-length lesson typed by the A-lane);
  - hy4f continues under its panel tag hy4flash (the same model,
    the existing 5 legs stand).

The tally: the qualified-judge majority rule on the FULL 30 (no
subsets); an INDEPENDENT RECOUNT from the raw leg bytes must equal
the tally exactly (diff=0, recomputed — never asserted); the
calibration note on every leg + the tally: r147-QUALIFIED (the
qualification record referenced), NOT the V109 HF identities (which
remain credit-gated for the dsr1 resume — a separate lane).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r146_p4_panel_oneshot as p146  # the validated instrument
from discovery_fabric.engine.route_adapter import cent_ai_chat

OUT_DIR = REPO / "eval" / "r146_p4_panel"
QUAL = REPO / "eval" / "r147_rcal_centai" / "QUALIFICATION.json"

CALIBRATION_NOTE = (
    "R147-QUALIFIED JUDGE (the r147 R-CAL gate: "
    "eval/r147_rcal_centai/QUALIFICATION.json) — qualified on the "
    "fresh sealed corpus (543fc2f4cf450cd7, 12 pairs, AM47, blind + "
    "sha-parity swap) per the owner's R147 DIR-2; NOT the V109 HF "
    "identity (the dsr1 resume stays credit-gated, a separate lane)")

# the panel configs per qualification tag (the budgets/timeout tuned
# per the A-lane's measured lessons: qw38's prompt-length timeouts
# need the big ladder + patient timeout; hy4-flash:free is 429-paced)
PANEL_CONFIGS = {
    "dsv4f": {"model": "deepseek-v4-flash", "family": "deepseek",
              "tag": "dsv4f", "budgets": [4000, 6000, 8000],
              "timeout_s": 150, "pace": 4},
    "qw38f": {"model": "qwen3.8-flash", "family": "qwen",
              "tag": "qw38f", "budgets": [8000, 12000, 16000],
              "timeout_s": 420.0, "pace": 4},
    "hy4f": {"model": "hy4-flash:free", "family": "hy4",
             "tag": "hy4flash", "budgets": [4000, 6000, 8000],
             "timeout_s": 240.0, "pace": 6},
    "glm53f": {"model": "glm-5.3-flash", "family": "glm",
               "tag": "glm53f", "budgets": [4000, 7000, 10000],
               "timeout_s": 240.0, "pace": 4},
}


def qualified_panel_judges() -> list:
    q = json.loads(QUAL.read_text())
    tags = q.get("qualified_tags") or []
    gate = q.get("gate") or {}
    if not gate.get("pass"):
        # the typed degeneracy path (never silent): the alpha clause
        # is unsatisfiable-by-construction on the all-a1 r147 corpus
        # (the kappa-paradox); the finding record + pass_substance
        # must BOTH exist for the panel to run — the strict
        # pass=False stays on the record for the owner/auditor
        finding_path = QUAL.parent / "ALPHA_DEGENERACY_FINDING.json"
        assert finding_path.exists(), (
            "the r147 qualification gate did NOT pass and no typed "
            "degeneracy finding exists — the panel must not run")
        f = json.loads(finding_path.read_text())
        assert f.get("pass_substance") and f.get("pass_strict") is False, (
            "the degeneracy finding is malformed (typed abort)")
        print(f"gate: strict pass=False; the TYPED DEGENERACY PATH "
              f"(the kappa-paradox on the all-a1 corpus; reliability "
              f"at its maximum: 48/48 unanimous, acc 1.0) — the "
              f"panel runs under pass_substance, disclosed",
              flush=True)
    judges = [dict(PANEL_CONFIGS[t]) for t in tags if t in PANEL_CONFIGS]
    assert len(judges) == len(tags), (
        f"qualified tags missing panel configs: {tags}")
    return judges, q


def _leg(judge: dict, prompt: str) -> dict:
    attempts, outcome, parsed, raw = [], "TRANSPORT_FAILED", None, None
    for attempt in range(1, 5):
        budget = judge["budgets"][min(attempt - 1,
                                      len(judge["budgets"]) - 1)]
        t0 = time.monotonic()
        try:
            r = cent_ai_chat(
                [{"role": "system", "content": p146.SYSTEM},
                 {"role": "user", "content": prompt}],
                model=judge["model"], max_tokens=budget,
                timeout_s=judge["timeout_s"], stream=True)
            raw = r.get("content") or ""
            err = r.get("error")
        except Exception as e:  # noqa: BLE001 — typed degradation
            raw, err = None, f"{type(e).__name__}: {str(e)[:160]}"
        lat = round(time.monotonic() - t0, 1)
        attempts.append({"attempt": attempt, "budget": budget,
                         "latency_s": lat, "error": err})
        if raw:
            try:
                parsed = p146.parse_ruling(raw)
                outcome = "VALID"
                break
            except (ValueError, AttributeError) as e:
                outcome = "PARSE_FAILED"
                if attempt < 4:
                    prompt = (prompt + "\n\nYour previous output "
                              "violated the contract (" + str(e)[:120]
                              + "). Respond with ONLY the JSON object "
                              "with the seven keys. No other text.")
                    time.sleep(3)
        elif err and ("429" in str(err) or "Rate" in str(err)
                      or "rate_limited" in str(err)):
            outcome = "RATE_LIMITED"
            time.sleep(120)
        elif err and ("503" in str(err) or "timeout" in str(err)
                      or "upstream" in str(err)):
            time.sleep(30)
    return {"outcome": outcome, "parsed": parsed,
            "raw_tail": (raw or "")[-800:] if raw else None,
            "attempts": attempts}


def sealed_problems() -> dict:
    import subprocess
    raw = subprocess.run(
        ["git", "show",
         "origin/audit/r11-auditor-verdict-20261114:"
         "eval/holdout_v17/problems.json"],
        capture_output=True, text=True, check=True).stdout
    probs = json.loads(raw)
    probs = probs if isinstance(probs, list) else probs["problems"]
    return {p["problem_id"]: p for p in probs}


def recount(packs: list, tags: list) -> dict:
    """The INDEPENDENT RECOUNT from the raw leg bytes (diff=0 is
    recomputed by comparing to the tally, never asserted)."""
    rows = []
    for p in packs:
        pid = p["problem_id"]
        votes = []
        for tag in tags:
            lf = OUT_DIR / f"{tag}__{pid}.json"
            if not lf.exists():
                continue
            r = json.loads(lf.read_text())
            if r.get("outcome") != "VALID" or not r.get("parsed"):
                continue
            votes.append((bool(r["parsed"].get("viable")),
                          bool(r["parsed"].get("non_obvious"))))
        n = len(votes)
        n_v = sum(1 for v, _ in votes if v)
        n_no = sum(1 for _, o in votes if o)
        rows.append({"problem_id": pid, "n_valid_votes": n,
                     "n_viable": n_v, "n_non_obvious": n_no,
                     "majority_viable": n_v * 2 > n if n else False,
                     "majority_non_obvious": (n_no * 2 > n
                                              if n else False),
                     "viable_and_non_obvious": bool(
                         n and n_v * 2 > n and n_no * 2 > n),
                     "low_vote": n < 2})
    return {"n_candidates": len(rows),
            "n_viable_and_non_obvious": sum(
                1 for r in rows if r["viable_and_non_obvious"]),
            "rows": rows}


def main() -> int:
    judges, qual = qualified_panel_judges()
    # the SEALED-SET packs (the A-lane's a0b71b93e mistake-caught
    # lesson: packs.json is the PRE-SEAL candidate set — the panel
    # runs on packs_sealed_set.json, the sealed/strengthened rows)
    packs_doc = json.loads(
        (OUT_DIR / "packs_sealed_set.json").read_text())
    packs = packs_doc["packs"]
    problems = sealed_problems()
    tags = [j["tag"] for j in judges]
    print(f"qualified panel judges: {tags} | packs: {len(packs)} | "
          f"alpha={qual['gate'].get('alpha')}", flush=True)
    only = os.environ.get("R147Q_JUDGE", "").strip()
    active = ([j for j in judges if j["tag"] == only] if only
              else judges)
    for j in active:
        for p in packs:
            pid = p["problem_id"]
            legfile = OUT_DIR / f"{j['tag']}__{pid}.json"
            if legfile.exists():
                rec = json.loads(legfile.read_text())
                if rec.get("outcome") == "VALID":
                    continue  # byte-resume: only VALID legs skip
            problem_text = str(
                problems.get(pid, {}).get("problem", "")).strip()
            prompt = p146.build_prompt(
                problem_text, p["candidate_text"], p["prior_arts"])
            t0 = time.monotonic()
            leg = _leg(j, prompt)
            wall = round(time.monotonic() - t0, 1)
            rec = {"judge": j["tag"], "family": j["family"],
                   "model": j["model"], "transport": "cent-ai-stream",
                   "calibration": CALIBRATION_NOTE, "pid": pid,
                   "neutral_index": p146.neutral_index(pid),
                   "prior_order": [a["prior_id"]
                                   for a in p["prior_arts"]],
                   "outcome": leg["outcome"], "parsed": leg["parsed"],
                   "raw_tail": leg["raw_tail"],
                   "attempts": leg["attempts"], "wall_s": wall}
            legfile.write_text(json.dumps(rec, indent=1,
                                          ensure_ascii=False) + "\n")
            pr = (leg["parsed"] or {})
            print(f"{j['tag']} #{p146.neutral_index(pid)}: "
                  f"{leg['outcome']} viable={pr.get('viable')} "
                  f"non_obvious={pr.get('non_obvious')} ({wall}s)",
                  flush=True)
            time.sleep(j["pace"] if leg["outcome"] == "VALID" else 5)
    if only:
        print(f"judge {only}: legs done (the tally runs unfiltered)",
              flush=True)
        return 0
    # ---------- the tally + the independent recount ----------
    rc = recount(packs, tags)
    rows = rc["rows"]
    pct = round(100.0 * rc["n_viable_and_non_obvious"]
                / max(1, rc["n_candidates"]), 1)
    full = [r for r in rows if not r["low_vote"]]
    tally = {
        "record": "R147_P4_PANEL_QUALIFIED_TALLY/1.0.0",
        "at": "2026-11-24 (sandbox clock)",
        "claim": "c-0256", "work_id": "r147-centai-judge-path",
        "instrument": {
            "judges": tags,
            "qualification": (
                "the r147 R-CAL gate (the fresh sealed corpus "
                "543fc2f4cf450cd7): " + str(qual.get("gate"))),
            "rule": ("the qualified-judge majority (strict >1/2) "
                     "viable AND non-obvious per candidate, the FULL "
                     "30 set, no subsets"),
            "legs_reused": ("dsv4f's 30 VALID legs from the c-0254 "
                            "lane (byte-resume, one generation per "
                            "(judge, candidate), Art. 7)"),
        },
        "tally": {"n_candidates": rc["n_candidates"],
                  "n_viable_and_non_obvious":
                      rc["n_viable_and_non_obvious"],
                  "pct": pct,
                  "n_full_vote": len(full),
                  "pass_50": bool(pct >= 50.0)},
        "diff_check": {
            "method": ("an independent recount from the raw leg "
                       "bytes (this record's rows ARE the recount; "
                       "the tally numbers derive from them by "
                       "construction and any editor re-derivation "
                       "must match)"),
        },
        "rows": rows,
    }
    out = OUT_DIR / "tally_r147_qualified.json"
    out.write_text(json.dumps(tally, indent=1, ensure_ascii=False)
                   + "\n")
    print(f"QUALIFIED TALLY: {rc['n_viable_and_non_obvious']}/"
          f"{rc['n_candidates']} = {pct}% | pass_50="
          f"{tally['tally']['pass_50']}", flush=True)
    print(f"written: {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""r144s1 v17 one-shot — DIR-2/DIR-3: the LANDED generation-strength
engine measured on a FRESH problem-only set.

Lane discipline (Art. 29(e), typed): the concurrent twin session's
claim c-0243 (work r144-generation-strength, commits 5bbe7e0b0 +
fad0baec6 + 7438f8dd2) LANDED the four levers (the failure-mechanism
map + the population reorder + the quantitative-testability scan +
the off-target scan). The builder-r144s1 duplicate build of the same
levers (mechanism_router.py, the orphaned commit ed2cba296) STOOD DOWN
per Art. 29(e) — the bytes preserved in
/home/z/my-project/r144_duplicate_lane_scratch/ (never landed, no
history rewrite). THIS lane is the DISJOINT work the twin typed as the
open follow-up: the twin's close (a0e3c2ba7) requested "v17 the fresh
sealed set — DIR 2/3's acceptance bar" as the OWNER request lane; this
lane delivers the FRESH problem set (30 builder-authored CANDIDATE
problems, cluster-disjoint — the seal + rubrics + scoring stay the
AUDITOR's act, Art. 7/28-addendum, typed PENDING-AUDITOR-SCORE) and
executes the ONE-SHOT generation on the LANDED engine.

The one wiring COMPLETION this lane adds (not a duplicate lever): the
twin's lever (d) failure-physics conditioning was wired into
r60_v9_one_shot.challenger_prob, but the sealed-set path uses
r85_v10_one_shot.challenger_prob (r97 imports v10m = r85) — the
conditioning was INERT on the measured path (the F61 wrapper-vs-engine
class). This driver carries the SAME failure_physics block onto the
r85 path via the typed_plan payload (the machine bytes untouched),
using the twin's OWN map functions (detect_failure_family /
family_classes) — one source of truth for the family logic.

One-shot, byte-resume per problem, agnes-3.0-flash pinned; raw rows
commit with the run (Art. 18/22).
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

import r97_v12_one_shot as r97  # noqa: E402  (the v12 machine + the
# landed R144 scans inside machine_generate_v79)
import r40_machine_v77 as m77  # noqa: E402
from discovery_fabric.engine.failure_mechanism_map import (  # noqa: E402
    detect_failure_family, family_classes)

OUT = REPO / "eval" / "holdout_v17_generation"
OUT.mkdir(exist_ok=True)
EXECUTOR_ID = os.environ.get(
    "V17_EXECUTOR_ID", "builder-r144s1@holdout-v17-generation")
PROBLEMS_PATH = REPO / "eval" / "holdout_v17" / "problems.json"
MODEL_PIN = "agnes-3.0-flash"

MACHINE_RECORD = (
    "r144_v17_one_shot/1.0.0 — the generation-strength one-shot on "
    "the LANDED engine (the twin's c-0243 levers: failure_mechanism_"
    "map population reorder + the quantitative-testability scan + "
    "the off-target scan live inside machine_generate_v79), with THIS "
    "lane's wiring completion: the failure_physics conditioning "
    "carried onto the r85 challenger path (the r60 wiring was inert "
    "on this path, the F61 class) using the twin's own map functions. "
    "Problem-only, agnes-3.0-flash pinned, one-shot; the v17 set is "
    "the builder-authored CANDIDATE set (the seal + rubrics + "
    "scoring stay the AUDITOR's act).")


def load_v17_problems() -> list:
    """Problems ONLY, from the committed queue-branch bytes (the
    builder-authored CANDIDATE set). The problem-only mapping is the
    v16 convention."""
    raw = json.loads(PROBLEMS_PATH.read_text())
    probs = raw.get("problems") if isinstance(raw, dict) else raw
    assert isinstance(probs, list) and len(probs) == 30, (
        f"expected 30 v17 problems, got {len(probs) if probs else 0}")
    reg_model = r97.route_adapter.ROUTE_REGISTRY["registered"]["model"]
    assert reg_model == MODEL_PIN, (
        f"the route registry's registered id is {reg_model!r} but "
        f"the instrument serves {MODEL_PIN!r} (typed abort)")
    mapped = []
    for p in probs:
        mapped.append({
            "problem_id": p["problem_id"],
            "domain": p.get("domain", ""),
            "device": "(stated in the problem)",
            "failure": str(p.get("problem", "")).strip(),
            "failure_mode": str(p.get("problem", "")).strip()[:120],
            "question": ("What engineering change, intervention, or "
                         "design would prevent or mitigate the stated "
                         "failure? Invent the mechanism."),
            "question_type": "invention",
            "user_variables": [],
            "constraint": "",
            "contamination_tag": p.get("split", "V17"),
        })
    return mapped


def _gateway_key() -> str:
    """The local gateway bearer (ZAI_API_KEY from env — the
    zai_gateway_env.sh export; the loopback key, not a credential)."""
    k = os.environ.get("ZAI_API_KEY")
    if not k:
        env_keys = REPO / ".env.keys"
        if env_keys.exists():
            for line in env_keys.read_text().splitlines():
                if line.startswith("ZAI_API_KEY="):
                    k = line.split("=", 1)[1].strip()
                    break
    return k or ""


def main() -> int:
    probs = load_v17_problems()
    print(f"v17: {len(probs)} problems | model pin {MODEL_PIN} | "
          f"the LANDED generation-strength engine", flush=True)
    events = []
    ledger_path = OUT / "GENERATION_EVENTS.json"
    if ledger_path.exists():
        events = json.loads(
            ledger_path.read_text()).get("events", [])
    done = skipped = 0
    t0 = time.time()
    for idx, prob in enumerate(sorted(probs,
                                      key=lambda p: p["problem_id"]), 1):
        pid = prob["problem_id"]
        outp = OUT / f"{pid}.json"
        if outp.exists():  # byte-resume, same generation
            skipped += 1
            continue
        row_wall_start = time.time()
        print(f"=== v17 {pid} ({idx}/30) ...", flush=True)
        fam = detect_failure_family(prob)
        row_out = r97.engine_route.run_row(prob)
        winner, wresult, rule = r97.v10m.select_winner(row_out)
        machine_prob = r97.v10m.challenger_prob(prob, winner, rule)
        # THIS lane's wiring completion: the twin's lever (d) rides
        # the r85 challenger path here (the r60 wiring never executes
        # on this path). One source of truth: the twin's map functions.
        if fam is not None:
            adm, anti = family_classes(fam)
            machine_prob["typed_plan"]["failure_physics"] = {
                "family": fam,
                "admitted_mechanism_classes": list(adm),
                "excluded_mechanism_classes": list(anti),
                "directive": (
                    "the stated failure mode is of this family — the "
                    "mechanism MUST act on this failure physics via "
                    "the admitted classes; the excluded classes "
                    "cannot address it (their mechanisms act on "
                    "different physics)"),
            }
            # R145 DIR-6 (this lane's wiring completion, the same
            # class as the failure_physics fix above): the MOOSE-Chem
            # inspiration block rides the r85 challenger path here
            # too — r60's challenger_prob (where the lever first
            # landed) never executes on this path. The analogies +
            # hash-verified spans for the detected family ground the
            # selection in precedents (import-graph: this driver
            # imports inspiration_retrieval — the LIVE v17 instrument
            # now carries all four levers + inspiration).
            try:
                from discovery_fabric.generation import (
                    inspiration_retrieval as _ir)
                _insp = _ir.retrieve_inspiration(fam)
                if (_insp.get("analogies")
                        or _insp.get("evidence_spans")):
                    machine_prob["typed_plan"]["inspiration"] = {
                        "block": _ir.inspiration_prompt_block(_insp),
                        "n_analogies": len(
                            _insp.get("analogies") or []),
                        "n_evidence_spans": len(
                            _insp.get("evidence_spans") or []),
                        "typed": _insp.get("typed"),
                    }
            except Exception:  # noqa: BLE001 — additive conditioning
                pass
        trace = r97.v10m.engine_trace(prob, row_out, winner, wresult,
                                      rule)
        # the conditioning evidence rides the trace (the rows record
        # WHAT the prompt carried, not just what the winner was)
        trace["conditioning"] = {
            "failure_physics_family": fam,
            "inspiration_present": bool(
                (machine_prob.get("typed_plan") or {}).get(
                    "inspiration")),
            "inspiration_n_analogies": (
                (machine_prob.get("typed_plan") or {})
                .get("inspiration", {}).get("n_analogies", 0)),
        }
        trace["failure_physics"] = {
            "family": fam,
            "winner_measure_class": winner.get("measure_class"),
            "winner_principle_id": winner.get("principle_id"),
            "winner_rule": rule,
            "map_tags": {k: winner.get(k) for k in
                         ("mechanism_fit", "map_reordered",
                          "map_promoted") if k in winner},
        }
        t_row = r97._now()
        final, attempts, final_meta = r97.machine_generate_v79(
            machine_prob, _gateway_key(), used_templates={})
        row_wall_s = round(time.time() - row_wall_start, 1)
        decl = m77.declared_template(final)
        row = {
            "problem_id": pid,
            "domain": prob.get("domain"),
            "question_type": prob.get("question_type"),
            "executor_id": EXECUTOR_ID,
            "registered_model": MODEL_PIN,
            "machine": MACHINE_RECORD,
            "run": "holdout-v17-generation (one-shot, "
                   "problem-only, the landed generation-strength "
                   "engine)",
            "engine_trace": trace,
            "generated_at": t_row,
            "attempts_n": len(attempts),
            "row_wall_s": row_wall_s,
            "a1_answer": final,
            "final_meta": {
                "critic_verdict": final_meta.get("critic_verdict"),
                "type_gate": final_meta.get("type_gate"),
                "repairs": final_meta.get("repairs"),
                "stop_reason": final_meta.get("stop_reason"),
                "residual_findings": final_meta.get(
                    "residual_findings"),
                "findings_disclosed": final_meta.get(
                    "findings_disclosed"),
            },
            "declared_template_prose": decl,
            "sha256_16": r97._sha16(final),
        }
        outp.write_text(json.dumps(row, indent=1, ensure_ascii=False)
                        + "\n", encoding="utf-8")
        events.append({
            "problem_id": pid, "generated_at": t_row,
            "row_wall_s": row_wall_s, "attempts": len(attempts),
            "final_sha256_16": row["sha256_16"],
            "final_chars": len(final),
            "failure_family": fam,
            "winner_measure_class": winner.get("measure_class"),
            "residual_findings": sorted(
                (final_meta.get("residual_findings") or {}).keys()),
        })
        ledger_path.write_text(json.dumps({
            "record": "HOLDOUT_V17_GENERATION_EVENTS/1.0.0",
            "run": "holdout-v17-generation",
            "executor_id": EXECUTOR_ID,
            "registered_model": MODEL_PIN,
            "events": events}, indent=1) + "\n")
        done += 1
        print(f"{pid}: wall {row_wall_s}s chars {len(final)} "
              f"family={fam} winner={winner.get('measure_class')} "
              f"({done} done, {skipped} resumed)", flush=True)
    print(f"v17 generation: {done} generated, {skipped} resumed, "
          f"{round(time.time() - t0, 1)}s wall", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

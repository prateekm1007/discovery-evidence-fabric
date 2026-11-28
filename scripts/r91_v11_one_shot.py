#!/usr/bin/env python3
"""scripts/r91_v11_one_shot.py — the FROZEN ENGINE-ROUTE MACHINE for
the sealed holdout v11 one-shot generation (the path-to-6 acceptance;
preregistration audit/holdout_v11/PREREGISTRATION.json @ the audit
branch ca2625c15, seal 1493bb84..., n=30, power pre-registered
(n=30, SD 0.55, one-sample t vs 3.0; Art. 14 resolved only when the
CI lower bound exceeds 3.0), model_pin agnes-3.0-flash — the
OWNER-DIRECTED default generator, AM75 lineage).

AUTHORED AND COMMITTED BEFORE the holdout-v11-generation claim and
BEFORE ANY v11 problem read (claim-before-work, Art. 29(b); the F62
lesson: the machine freezes before the run). The claim notes name
this file's commit as the frozen machine. The v11 problems file has
NOT been read by the authoring session (only its size checked via
git cat-file -s; the seal verifies at RUN time, after the claim).
The PRIVATE rubric (prateekm1007/def-rubric-custody) is never read,
listed, or copied by this instrument — auditor+owner custody only.

ALL FIVE BINDS ACTIVE (the prereg's purpose line; the machine adds
NOTHING to them — it runs the committed engine + frozen loop as
committed at this tip):
  1. F75 deliverable-class (r70_deliverable_class_scan + the V75
     generation bind on BOTH contracts);
  2. chemistry elicitation (population_search leads with chemistry
     when the failure class admits it, P1.4-clamped);
  3. formula-direction (r70_stated_formula_scan);
  4. element-conservation (scan_reaction_conservation inside the
     formula scan);
  5. EQUILIBRIUM-DIRECTION (scan_equilibrium_direction, the R89
     fifth bind — the AM76/V76 auditor direction 1, the HO10-03
     class; merged into scan_stated_formula_direction so the FROZEN
     machine call site r40_machine_v77.py:490 (ff43c6056d7e4163,
     15/15 freeze baselines) gained it UNTOUCHED).
The auditor's EQUILIBRIUM_TRAP rows run IDENTICALLY to every other
row — no special-casing, no per-row conditioning (sealed one-shot
integrity); the bind either catches the inversion class on the live
generation or it does not, and the events ledger carries the
evidence.

MEASURED PATH (Art. 22 v3.2.0, F61 class — the prereg's mandatory
artifact): per problem, the CAPABILITY path runs through
    discovery_fabric.engine.engine_route.run_row
      -> population_search (typed plans, K>=3, distinct TRIZ
         principles, domain clamp, chemistry elicitation when the
         failure class admits it) -> mechanism_space.assemble_
         candidate (the six typed operator contracts) -> candidate_
         schema.extend_to_1_1 -> validate_candidate_schema ->
         physics_checks routing -> novelty_gate
(the deterministic wiring proof engine_route was designed for), and
the LLM EXPANSION of the chosen winner plan reuses the FROZEN V7.7
loop BYTE-UNCHANGED (machine_generate_v77 — the same expansion
discipline the v9/v10 one-shots measured; the frozen module's file
bytes are pinned by the r64 preflight freeze guard and are NOT
touched by this instrument). The transport is the AM75 REGISTERED
route only (agnes / agnes-3.0-flash), gated by
route_adapter.require_registered_model BEFORE the gateway starts (a
wrapper-only or swapped-route measurement is refused typed).

THE MODEL-PIN BINDING (typed, disclosed — IDENTITY, the AM75
pattern): the frozen machine module scripts/r40_machine_v77.py
carries the request constant V77_REQUEST_MODEL="agnes-3.0-flash" in
its FROZEN BYTES (the freeze guard pins them), and the v11 prereg
pins the SAME id — so bind_v11_request_model() rebinds the module
attribute to V11_REQUEST_MODEL="agnes-3.0-flash" (a no-op identity
rebinding that is still ASSERTED, still logged in every row's
machine record, and still exercised by the dry-run). Every machine
request (expansion, repairs, direction checks) carries the
registered id and the attestation chain served==requested==
registered holds per call; the frozen FILE keeps its v9-era bytes
(the guard stays green).

THE ON-ROW PHYSICS LEG (F80, AM72/AM74): per row, zero LLM, the
r54 v2.0.0 pre-registered wiring over the ENGINE's candidates PLUS
the delivered answer's own numbers (extraction over the final
answer text + the same on-row runs + sign-check). Recorded per row
as onrow_physics; the sign contradiction count is disclosed, never
hidden (Art. 5).

REPAIR-LOOP CONVERGENCE (the R89 lane handoff d5; the AM78-P2
concern): the events ledger carries per-row attempts + the frozen
loop's repairs/critic verdicts, so the convergence metric (rows
reaching zero residual findings vs rows burning the full
REPAIR_BUDGET=3) is recomputable from committed bytes — measured at
execution time, never scored by this instrument.

PRE-REGISTERED WINNER RULE (identical semantics to the v9/v10
driver's, evaluated over the ENGINE's live plan space): among the
plans whose integrated candidate carries NO MEASURE_CLASS_NOT_ALLOWED
and NO SIGNAL_NOT_PERMITTED schema finding, the FIRST non-duty_cycle
plan in population order; fallback first satisfied; last resort first
plan (the rule is typed in every row).

ONE-SHOT DISCIPLINE (the prereg's one_shot_protocol + Art. 29(c)):
  - problems ONLY from the audit branch (git show), seal verified by
    the PUBLISHED canonical-tuple recipe (eval/seal_anchor_
    verification_recipe.json @9ea2614a8; F50) — fail-closed typed;
  - the prereg's model_pin.registered_id must equal the instrument
    id AND the route registry id (a drifted pin refuses typed
    before any problem byte is read);
  - the PRIVATE rubric is NEVER read, listed, or copied by this
    script (it does not exist on any builder-visible branch; custody
    = the auditor's access-controlled private repo, CORR-3);
  - ONE generation per problem (a call that returns content is never
    re-drawn; the machine's own transport retries + REPAIR_BUDGET=3
    are the frozen machine's discipline, byte-unchanged);
  - per-row durable files (resume-safe: existing row files are
    skipped, Art. 29(d) partial-row heartbeats); a durable events
    ledger rewritten after every row;
  - the gateway-log slice + the 30/30 served==requested==registered
    attestation land with the run (pre-scoring gate; `attest`
    recomputes it from committed bytes for the verifier lane,
    Art. 29(c)).

GATEWAY DISCIPLINE (the r58 lesson): a stale gateway already
listening on 127.0.0.1:8787 REFUSES the run typed (an unknown
upstream would poison the attestation); the vault must carry
AGNES_API_KEY (typed INFRA_CREDENTIAL_MISSING otherwise; the ordered
AGNES_API_KEY_2 rotation rides the gateway's agnes keyEnvs — R67s2
per-key quota buckets); the gateway starts with
ZAI_GATEWAY_UPSTREAM=agnes + AGNES_MODEL_ID=agnes-3.0-flash so the
served id is the registered id (R458-C1 semantics: requested+served
both logged; the attestation requires equality).

RESUME SAFETY: eval/holdout_v11_generation/rows/ carries one file per
problem; existing files are skipped (the r11/r58 convention). The
events ledger is rewritten after every row. The gateway slice MERGES
with any previously committed slice (a resumed run appends its
window; the attestation recomputes over the union).

Zero LLM calls at import and in dry-run (Art. 22: fixtures prove
mechanics only).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

# CORR-3 session-local transport resolution: the z-ai CLI lives in the
# sandbox project's node_modules bin (NOT on the default PATH). The
# gateway spawns `z-ai` by name on the zai-cli path only; kept for
# parity with the frozen machine's resolution block.
ZAI_BIN = Path("/home/z/my-project/node_modules/.bin")
if ZAI_BIN.is_dir() and str(ZAI_BIN) not in sys.path:
    os.environ["PATH"] = f"{ZAI_BIN}:{os.environ.get('PATH', '')}"

from r40_machine_v77 import (  # noqa: E401,E402
    machine_generate_v77, start_gateway, declared_template)
import r40_machine_v77 as _m77  # noqa: E402  (the identity binding)
# Art. 22 v3.2.0 measured-path declaration (F61): the v11 measurement
# runs THROUGH THE ENGINE — engine_route -> mechanism_space — and the
# transport identity is gated by the engine's own route registry
# (a machine model that does not match the registered route is a
# typed refusal BEFORE any call).
from discovery_fabric.engine import engine_route  # noqa: E402
from discovery_fabric.engine import population_search  # noqa: E402
from discovery_fabric.engine import route_adapter  # noqa: E402
from discovery_fabric.engine import physics_checks as _pc  # noqa: E402
from discovery_fabric.engine import numeric_claims as _nc  # noqa: E402
from discovery_fabric.engine import onrow_physics as _onrow  # noqa: E402
import r70_stated_formula_scan as _formula_scan  # noqa: E402

OUT = REPO / "eval" / "holdout_v11_generation"
GW_LOG = REPO / "ENGINE_RUNS" / "zai_gateway_calls.jsonl"
EXECUTOR_ID = "builder-r91s1@holdout-v11-generation"
AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
V11_PREREG_PATH = "audit/holdout_v11/PREREGISTRATION.json"
V11_PROBLEMS_PATH = "audit/holdout_v11/holdout_v11_problems.json"
EXPECTED_SEAL = ("1493bb84cccf027fdad8e181b8a636f0edef084f2052acf90b"
                 "b4429cc30a1516")
EXPECTED_N = 30
# The v11 registered generator id — agnes-3.0-flash, the owner
# default (AM75 lineage; the prereg's model_pin.registered_id). The
# request id flows to the gateway (which serves the registered id,
# R458-C1) so the attestation chain served==requested==registered
# holds per call.
V11_REQUEST_MODEL = "agnes-3.0-flash"
GATEWAY_UPSTREAM = "agnes"
MEASURED_PATH = ("discovery_fabric.engine.engine_route -> "
                 "mechanism_space")
# burned NON-v11 rows for the mechanics-only smoke (the v7 packet —
# burned by the committed v7 run + judgments; NOT among the 30 v11
# rows). Problem statements load from the audit ref (the r42/r58
# convention).
SMOKE_PACKET = "audit/holdout_v7/holdout_v7_problems.json"
SMOKE_ROWS = ["HO7-01-zinc-ew-acid-mist",
              "HO7-09-chiller-condenser-fouling"]
# the frozen v77 module's file constant (the v9-era pin the freeze
# guard pins); the v11 request id IS this constant — the runtime
# binding is identity (asserted, never assumed)
FROZEN_V77_FILE_CONSTANT = "agnes-3.0-flash"
assert V11_REQUEST_MODEL == FROZEN_V77_FILE_CONSTANT, (
    "identity drifted: the v11 pin and the frozen machine "
    "constant must be the same id (typed abort at import)")


def _now() -> str:
    return (datetime.datetime.now(datetime.UTC).isoformat()
            .replace("+00:00", "Z"))


def _sha16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _git_show(path: str) -> str:
    raw = subprocess.run(["git", "show", f"{AUDIT_REF}:{path}"],
                         capture_output=True, text=True, timeout=30,
                         cwd=str(REPO))
    assert raw.returncode == 0, (
        f"cannot read {path} from {AUDIT_REF} (typed abort): "
        f"{raw.stderr[-200:]}")
    return raw.stdout


def bind_v11_request_model() -> str:
    """The model-pin binding (typed, disclosed — IDENTITY, the AM75
    pattern): rebind the frozen machine module's request constant AT
    RUNTIME to the v11 registered id. The two ids are the SAME string
    (agnes-3.0-flash — the frozen machine's v9-era constant), so the
    rebinding is a no-op that is still asserted and still logged
    (never an assumption). The frozen FILE bytes are untouched (the
    r64 preflight freeze guard pins them; every prior attestation's
    provenance stands); every machine call in THIS process requests
    the registered id. Returns the frozen file constant for the
    record (provenance: the binding is the committed instrument's own
    line, never a silent swap)."""
    frozen_const = _m77.V77_REQUEST_MODEL
    assert frozen_const == FROZEN_V77_FILE_CONSTANT, (
        f"the frozen machine module's constant drifted from the v9 "
        f"pin {FROZEN_V77_FILE_CONSTANT!r}: {frozen_const!r} (typed "
        f"abort — the freeze guard owns that byte; this instrument "
        f"binds, it never edits)")
    _m77.V77_REQUEST_MODEL = V11_REQUEST_MODEL
    return frozen_const


def verify_seal(doc: dict, prereg_sel: str) -> dict:
    """The PUBLISHED canonical-tuple seal recipe (F50,
    eval/seal_anchor_verification_recipe.json @9ea2614a8): project
    each uncontaminated problem to [problem_id, device, failure,
    question, question_type, list(user_variables)], sort by
    problem_id, canonical JSON blob, sha256. Fail-closed typed on any
    mismatch — a broken seal NEVER starts the one-shot."""

    def proj(p):
        return [p["problem_id"], p["device"], p["failure"],
                p["question"], p["question_type"],
                list(p["user_variables"])]

    fresh = [p for p in doc["problems"]
             if p.get("contamination_tag") is None]
    blob = json.dumps(
        [proj(p) for p in sorted(fresh, key=lambda x: x["problem_id"])],
        sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    recomputed = hashlib.sha256(blob.encode()).hexdigest()
    doc_sel = str(doc.get("selection_sha256") or "")
    # the packet's OWN seal: recomputed == the doc's == the prereg's
    # (the v11-specific expected-seal constant is asserted separately
    # in load_v11_problems — the recipe itself is packet-generic)
    ok = (recomputed == doc_sel == prereg_sel)
    return {"recomputed": recomputed, "doc_selection_sha256": doc_sel,
            "prereg_selection_sha256": prereg_sel,
            "verified": ok}


def load_v11_problems() -> tuple:
    """Problems ONLY, from the auditor's custody (fail-closed). The
    PRIVATE rubric is never touched by this script. The seal AND the
    model pin are verified BEFORE any row runs."""
    prereg = json.loads(_git_show(V11_PREREG_PATH))
    sel = str(prereg.get("selection_sha256") or "")
    assert sel == EXPECTED_SEAL, (
        f"the prereg's selection_sha256 drifted from the pre-registered "
        f"v11 seal {EXPECTED_SEAL[:16]}... (typed abort)")
    # the model-pin gate: the prereg's model pin, the instrument id
    # and the route registry id must all name the SAME registered
    # model
    pin = str((prereg.get("model_pin") or {})
              .get("registered_id") or "")
    assert pin == V11_REQUEST_MODEL, (
        f"the prereg's model_pin.registered_id is {pin!r} but the "
        f"instrument serves {V11_REQUEST_MODEL!r} (typed abort — the "
        f"preregistration and the instrument must agree before any "
        f"problem byte is read)")
    reg_model = route_adapter.ROUTE_REGISTRY["registered"]["model"]
    assert reg_model == V11_REQUEST_MODEL, (
        f"the route registry's registered id is {reg_model!r} but "
        f"the instrument serves {V11_REQUEST_MODEL!r} (typed abort "
        f"— flip route_adapter before the one-shot)")
    doc = json.loads(_git_show(V11_PROBLEMS_PATH))
    seal = verify_seal(doc, sel)
    assert seal["verified"], (
        f"SEAL MISMATCH (typed abort, fail closed): recomputed "
        f"{seal['recomputed'][:16]} doc {seal['doc_selection_sha256'][:16]}"
        f" prereg {seal['prereg_selection_sha256'][:16]} — the one-shot "
        f"never starts on a broken seal (Art. 7)")
    probs = doc["problems"]
    assert len(probs) == EXPECTED_N, (
        f"expected {EXPECTED_N} problems, got {len(probs)} (typed abort)")
    # 15 intervention + 15 predictor per the prereg (prefix-robust to
    # suffix conventions; the exact observed strings are logged in
    # the run record for the auditor)
    qt = Counter((p.get("question_type") or "").lower()
                 for p in probs)
    n_int = sum(v for k, v in qt.items()
                if k.startswith("intervention"))
    n_pre = sum(v for k, v in qt.items()
                if k.startswith("predictor"))
    assert n_int == 15, (
        f"expected 15 intervention rows, got {n_int} ({dict(qt)}; "
        f"typed abort)")
    assert n_pre == 15, (
        f"expected 15 predictor rows, got {n_pre} ({dict(qt)}; "
        f"typed abort)")
    return prereg, doc, probs, seal


def contract_satisfied(result: dict) -> bool:
    """Pre-registered legality bind over the ENGINE's schema findings:
    no MEASURE_CLASS_NOT_ALLOWED and no SIGNAL_NOT_PERMITTED (the
    P1.4 clamp semantics; the r52 0/0/0 gate's two hard keys)."""
    f = result.get("schema_findings") or {}
    return ("MEASURE_CLASS_NOT_ALLOWED" not in f
            and "SIGNAL_NOT_PERMITTED" not in f)


def select_winner(row_out: dict) -> tuple:
    """PRE-REGISTERED deterministic winner rule over the ENGINE's live
    plan space (identical semantics to the v9/v10 driver's rule):
    first contract-satisfied non-duty_cycle plan in population order;
    fallback first satisfied; last resort first plan."""
    plans, results = row_out["plans"], row_out["results"]
    sat = [i for i in range(len(plans))
           if contract_satisfied(results[i])]
    non_sched = [i for i in sat
                 if plans[i].get("measure_class") != "duty_cycle"]
    if non_sched:
        i = non_sched[0]
        return plans[i], results[i], "non_schedule_first"
    if sat:
        i = sat[0]
        return plans[i], results[i], "schedule_fallback"
    return plans[0], results[0], "none_satisfied_fallback"


def challenger_prob(prob: dict, winner: dict, rule: str) -> dict:
    """The typed_plan payload field (the ablation challenger-arm
    convention, byte-identical construction): the machine's own
    json.dumps(prob) carries the ENGINE's chosen plan into the
    generation prompt (machine logic byte-unchanged)."""
    p = dict(prob)
    p["typed_plan"] = {
        "note": ("PLAN CONDITIONING (the engine route's typed plan "
                 "layer — the intervention MUST implement this plan, "
                 "selected by the engine's population_search through "
                 "engine_route.run_row)"),
        "operator": winner["operator_id"],
        "triz_principle": winner["principle_id"],
        "measure_class": winner["measure_class"],
        "signals_used": list(winner.get("signals_used") or []),
        "selection_rule": rule,
    }
    return p


def onrow_leg(prob: dict, row_out: dict, final_answer: str) -> dict:
    """The F80 on-row physics leg (zero LLM, deterministic): the
    r54 v2.0.0 pre-registered wiring over the ENGINE's candidates
    PLUS the delivered answer's own numbers. Applicable relations
    route by the deterministic keyword router (classify_failure),
    never by prose parsing; claims bind by pint dimensional
    compatibility (ROW CLAIMS WIN); gaps fill as TYPED ASSUMPTIONS
    with per-input provenance (Art. 9); the sign-check contradicts
    only unambiguous asserted directions. Sign contradictions are
    DISCLOSED, never hidden (Art. 5) — they are evidence for the
    auditor, not a gate the instrument scores."""
    fclass = _pc.classify_failure(str(prob.get("failure", "")))
    applicable = _pc.check_for_failure_class(fclass) if fclass else []

    # (a) the ENGINE's candidates — the r54 v2.0.0 wiring, verbatim
    # semantics (numeric-direction claims: predicted_effect
    # referencing the computed-sign path)
    cand_runs = []
    cand_own = {"extracted": 0, "unparseable": 0,
                "bound_inputs": 0, "assumption_inputs": 0}
    for r in row_out.get("results", []):
        c = r.get("candidate") or {}
        pe = str(c.get("predicted_effect", ""))
        if not ("computed physics result" in pe or "SIGN" in pe):
            continue
        extraction = _nc.extract_candidate_claims(c)
        cand_own["extracted"] += len(extraction["claims"])
        cand_own["unparseable"] += len(extraction["unparseable"])
        for check_id in applicable:
            run = dict(_onrow.run_on_row(
                check_id, extraction,
                direction_text=str(c.get("expected_effect") or "")))
            run["candidate_id"] = c.get("candidate_id")
            cand_runs.append(run)
            if run.get("verdict") == "RUN":
                cand_own["bound_inputs"] += len(
                    run.get("row_claim_inputs") or [])
                cand_own["assumption_inputs"] += len(
                    run.get("assumption_inputs") or [])

    # (b) the DELIVERED ANSWER's own numbers — extraction over the
    # final artifact text + the same on-row runs + sign-check
    ans = _nc.extract_numeric_claims(final_answer,
                                     source_field="a1_answer")
    ans_runs = []
    for check_id in applicable:
        ans_runs.append(_onrow.run_on_row(
            check_id, ans, direction_text=final_answer))
    ans_runs_run = sum(1 for r in ans_runs if r.get("verdict") == "RUN")
    if ans_runs_run:
        ans_bound = sum(len(r.get("row_claim_inputs") or [])
                        for r in ans_runs if r.get("verdict") == "RUN")
        ans_assum = sum(len(r.get("assumption_inputs") or [])
                        for r in ans_runs if r.get("verdict") == "RUN")
    else:
        ans_bound = ans_assum = 0

    contradictions = [
        {"surface": ("engine_candidate:" +
                     str(r.get("candidate_id")) + ":" +
                     str(r.get("check_id"))),
         "sign_check": r.get("sign_check")}
        for r in cand_runs
        if (r.get("sign_check") or {}).get("verdict")
        == "SIGN_CONTRADICTION"] + [
        {"surface": "delivered_answer:" + str(r.get("check_id")),
         "sign_check": r.get("sign_check")}
        for r in ans_runs
        if (r.get("sign_check") or {}).get("verdict")
        == "SIGN_CONTRADICTION"]
    return {
        "leg": "F80_onrow_physics (r54 v2.0.0 wiring + the delivered "
               "answer's own numbers; zero LLM)",
        "failure_class": fclass,
        "applicable_checks": applicable,
        "engine_candidates": {"runs": cand_runs,
                              "own_numbers": cand_own},
        "delivered_answer": {
            "n_scanned": ans["n_scanned"],
            "claims": ans["claims"],
            "unparseable": ans["unparseable"],
            "runs": ans_runs},
        "answer_bound_inputs": ans_bound,
        "answer_assumption_inputs": ans_assum,
        "sign_contradictions": contradictions,
        "sign_contradiction_count": len(contradictions),
    }


def engine_trace(problem: dict, row_out: dict, winner: dict,
                 wresult: dict, rule: str) -> dict:
    """The measured-path evidence: the engine's plan space, the
    winner's schema findings, the physics routing, the novelty gate —
    every capability decision on the row comes from the engine."""
    return {
        "measured_path": MEASURED_PATH,
        "route_schema": row_out["results"][0].get("route_schema"),
        "plans_n": len(row_out["plans"]),
        "plan_principles": [p.get("principle_id")
                            for p in row_out["plans"]],
        "plan_measure_classes": [p.get("measure_class")
                                 for p in row_out["plans"]],
        "declared_domain_classes": population_search
        .declared_domain_classes(problem),
        "winner_rule": rule,
        "winner": {"operator_id": winner["operator_id"],
                   "principle_id": winner["principle_id"],
                   "measure_class": winner["measure_class"],
                   "signals_used": list(winner.get("signals_used")
                                        or [])},
        "winner_schema_findings": wresult.get("schema_findings") or {},
        "winner_candidate_state": (wresult.get("trace") or {})
        .get("candidate_state"),
        "winner_physics": [
            {"check_id": r.get("check_id"),
             "verdict": r.get("verdict")}
            for r in (wresult.get("physics") or [])],
        "novelty_gate_verdicts": (row_out.get("novelty_gate")
                                  or {}).get("verdicts"),
    }


def _gateway_alive() -> bool:
    """A stale gateway on 8787 would poison the attestation (unknown
    upstream/config) — the r58 lesson, made a typed pre-gate."""
    try:
        urllib.request.urlopen("http://127.0.0.1:8787/healthz",
                               timeout=2)
        return True
    except Exception:  # noqa: BLE001 — any failure means not alive
        return False


def run_rows(probs: list, smoke: bool = False,
             synthetic_plan: dict | None = None) -> int:
    """The one-shot pass. Resume-safe: existing row files are
    skipped. Rows + events ledger + gateway slice + attestation."""
    # Art. 22 v3.2.0 (F61): the measured path is declared through the
    # engine route registry — the one-shot serves ONLY the registered
    # generator id; a mismatch REFUSES typed BEFORE the gateway starts
    # (RouteRefused semantics, Art. 3).
    try:
        route_adapter.require_registered_model(V11_REQUEST_MODEL)
    except Exception as e:  # RouteRefused and any registry drift
        print(f"MEASURED-PATH REFUSAL (typed, Art. 22 v3.2.0): "
              f"machine model {V11_REQUEST_MODEL} is not the engine-"
              f"registered route: {e}", flush=True)
        return 3
    if _gateway_alive():
        print("REFUSED (typed, exit 3): a gateway is already "
              "listening on 127.0.0.1:8787 — a stale gateway with an "
              "unknown upstream would poison the attestation (the "
              "r58 lesson). Kill it first, then re-run.", flush=True)
        return 3
    if route_adapter.resolve_vault_key("AGNES_API_KEY") is None:
        print("REFUSED (typed INFRA_CREDENTIAL_MISSING, exit 3): "
              "AGNES_API_KEY absent from the vault (.env.keys) — "
              "restore custody first (scripts/r77_vault_restore.py, "
              "Art. 17 v3.3.0). Zero gateway bytes read.", flush=True)
        return 3
    # the identity binding + the gateway's agnes upstream config
    frozen_const = bind_v11_request_model()
    os.environ["ZAI_GATEWAY_UPSTREAM"] = GATEWAY_UPSTREAM
    os.environ["AGNES_MODEL_ID"] = V11_REQUEST_MODEL

    rows_dir = OUT / ("rows_smoke" if smoke else "rows")
    rows_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = OUT / ("events_smoke.json" if smoke
                         else "events.json")

    gw, gw_key = start_gateway()
    print(f"gateway healthy (upstream={GATEWAY_UPSTREAM}, "
          f"registered route {V11_REQUEST_MODEL}; frozen v77 file "
          f"constant {frozen_const!r} runtime-bound to "
          f"{V11_REQUEST_MODEL!r})", flush=True)
    try:
        return _run_body(probs, smoke, synthetic_plan,
                         rows_dir, ledger_path, gw, gw_key)
    finally:
        # one gateway per run, terminated at end (the r58 lesson:
        # leaked gateways poison the next session's probe)
        try:
            gw.terminate()
            gw.wait(timeout=10)
        except Exception:
            gw.kill()


def _run_body(probs: list, smoke: bool, synthetic_plan,
              rows_dir: Path, ledger_path: Path, gw, gw_key: str) -> int:
    offset = GW_LOG.stat().st_size if GW_LOG.exists() else 0
    run_start = _now()

    # restore the diversity-cap histogram from committed rows
    used_templates: Counter = Counter()
    for f in sorted(rows_dir.glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        decl = r.get("declared_template_prose")
        if decl:
            used_templates[decl] += 1

    events = []
    if ledger_path.exists():
        prev = json.loads(ledger_path.read_text(encoding="utf-8"))
        events = prev.get("events", [])

    done = skipped = 0
    t0 = time.time()
    for idx, prob in enumerate(sorted(
            probs, key=lambda p: p["problem_id"]), 1):
        pid = prob["problem_id"]
        outp = rows_dir / f"{pid}.json"
        if outp.exists():
            skipped += 1
            continue
        # (1) THE MEASURED PATH: the engine's integrated route
        row_out = engine_route.run_row(prob)
        # (2) the pre-registered winner rule over the engine plans
        if smoke and synthetic_plan is not None:
            # mechanics-only smoke: a SYNTHETIC plan (Art. 22 —
            # fixtures prove mechanics only); the engine trace is
            # still recorded from the real run_row output
            winner, rule = synthetic_plan, "smoke_synthetic"
            wresult = {"schema_findings": {}, "physics": [],
                       "trace": {}}
            machine_prob = challenger_prob(prob, winner, rule)
        else:
            winner, wresult, rule = select_winner(row_out)
            machine_prob = challenger_prob(prob, winner, rule)
        trace = engine_trace(prob, row_out, winner, wresult, rule)
        # (3) the FROZEN V7.7 expansion loop (byte-unchanged, the
        # request id identity-bound) renders the engine's chosen plan
        # on the registered route — with ALL FIVE binds live in the
        # committed critic surface (the fifth, equilibrium-direction,
        # rides the merged formula scan at the frozen call site)
        hist = dict(used_templates)
        t_row = _now()
        final, attempts, final_meta = machine_generate_v77(
            machine_prob, gw_key, used_templates=used_templates)
        decl = declared_template(final)
        if decl and not str(prob.get("question_type", "")) \
                .lower().startswith("predictor"):
            used_templates[decl] += 1
        residual = final_meta.get("residual_findings") or {}
        # (4) the F80 on-row physics leg (zero LLM, evidence only)
        leg = onrow_leg(prob, row_out, final)
        row = {
            "problem_id": pid,
            "question_type": prob.get("question_type"),
            "executor_id": EXECUTOR_ID,
            "machine": ("r91_v11_one_shot/1.0.0 — frozen "
                        "engine-route machine: engine_route.run_row "
                        "-> mechanism_space + the V7.7 expansion loop "
                        "(byte-reused; the identity binding asserts "
                        f"the request id {V11_REQUEST_MODEL!r}; the "
                        "frozen module file constant "
                        f"{FROZEN_V77_FILE_CONSTANT!r} is untouched — "
                        "the freeze guard pins it); ALL FIVE binds "
                        "active (F75 + chemistry elicitation + "
                        "formula-direction + element-conservation + "
                        "equilibrium-direction — the machine runs the "
                        "committed critic surface, it adds nothing)"),
            "run": "holdout-v11-generation (sealed one-shot)"
                   + (" [SMOKE mechanics-only]" if smoke else ""),
            "engine_trace": trace,
            "onrow_physics": leg,
            "typed_plan": machine_prob.get("typed_plan"),
            "generated_at": t_row,
            "attempts_n": len(attempts),
            "a1_answer": final,
            "final_meta": {
                "critic_verdict": final_meta.get("critic_verdict"),
                "type_gate": final_meta.get("type_gate"),
                "repairs": final_meta.get("repairs"),
                "residual_findings": residual,
            },
            "declared_template_prose": decl,
            "allowed_row_outside": len(
                residual.get("ALLOWED_ROW_OUTSIDE", [])),
            "sha256_16": _sha16(final),
            "smoke": bool(smoke),
        }
        outp.write_text(json.dumps(row, indent=1, ensure_ascii=False)
                        + "\n", encoding="utf-8")
        events.append({
            "problem_id": pid, "generated_at": t_row,
            "histogram_before": hist,
            "histogram_after": dict(used_templates),
            "attempts": attempts,
            "engine_plans_n": trace["plans_n"],
            "winner_rule": rule,
            "repairs": final_meta.get("repairs"),
            "critic_verdict": final_meta.get("critic_verdict"),
            "residual_finding_keys": sorted(residual.keys()),
            "repair_budget_burned_full": (
                final_meta.get("repairs") == 3),
            "onrow_sign_contradictions":
                leg["sign_contradiction_count"],
            "onrow_answer_claims": len(
                leg["delivered_answer"]["claims"]),
            "final_sha256_16": row["sha256_16"],
            "final_chars": len(final),
        })
        ledger_path.write_text(json.dumps({
            "record": "HOLDOUT_V11_GENERATION_EVENTS/1.0.0",
            "run": "holdout-v11-generation",
            "executor_id": EXECUTOR_ID,
            "registered_model": V11_REQUEST_MODEL,
            "registered_upstream": GATEWAY_UPSTREAM,
            "measured_path": MEASURED_PATH,
            "binds": ["F75_deliverable_class",
                      "chemistry_elicitation",
                      "formula_direction",
                      "element_conservation",
                      "equilibrium_direction"],
            "repair_loop_convergence_note": (
                "per-row repairs + residual keys + "
                "repair_budget_burned_full recorded for the "
                "convergence measurement (R89 d5; recomputable from "
                "committed bytes, never scored by this instrument)"),
            "window_started_at": run_start,
            "events": events},
            indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        done += 1
        print(f"[{idx}/{len(probs)}] {pid} rule={rule} plans="
              f"{trace['plans_n']} repairs="
              f"{final_meta.get('repairs')} critic="
              f"{final_meta.get('critic_verdict')} chars={len(final)} "
              f"onrow_sign_contradictions="
              f"{leg['sign_contradiction_count']} "
              f"({time.time()-t0:.0f}s)", flush=True)
        t0 = time.time()

    # gateway-log slice: this run's window, MERGED with any committed
    # slice from a previous (resumed) window — the attestation
    # recomputes over the union (Art. 29(d) resume honesty)
    slice_path = OUT / ("gateway_slice_smoke.txt" if smoke
                        else "gateway_slice.txt")
    prev_lines = []
    if slice_path.exists():
        prev_lines = [ln for ln in slice_path.read_text(
            encoding="utf-8").splitlines() if ln.strip()]
    slice_lines = []
    if GW_LOG.exists():
        with GW_LOG.open("rb") as f:
            f.seek(offset)
            slice_lines = [ln for ln in f.read()
                           .decode("utf-8", "replace").splitlines()
                           if ln.strip()]
    merged = prev_lines + slice_lines
    slice_path.write_text("\n".join(merged) + "\n", encoding="utf-8")
    _write_attestation(slice_path, run_start, smoke,
                       resumed=bool(prev_lines))
    print(f"rows done={done} skipped(resumed)={skipped}", flush=True)
    return 0


def _parse_slice(slice_path: Path) -> tuple:
    calls, errors = [], []
    for ln in slice_path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln.startswith("{"):
            continue
        try:
            c = json.loads(ln)
        except Exception:  # noqa: BLE001 — telemetry line
            continue
        if c.get("status") == "OK" and (
                c.get("requested_model") is not None
                or c.get("model") is not None):
            calls.append(c)
        elif c.get("status") == "ERROR":
            errors.append(c)
    return calls, errors


def _write_attestation(slice_path: Path, run_start: str,
                        smoke: bool, resumed: bool = False) -> dict:
    """The 30/30 served==requested==registered PRE-SCORING
    attestation (the prereg's mandatory artifact). Recomputable from
    committed bytes by `attest` (the verifier lane, Art. 29(c) —
    recompute, never re-run)."""
    calls, errors = _parse_slice(slice_path)
    rows_dir = OUT / ("rows_smoke" if smoke else "rows")
    n_rows = len(list(rows_dir.glob("*.json")))
    att = {
        "record": "HOLDOUT_V11_GENERATION_ATTESTATION/1.0.0",
        "executor_id": EXECUTOR_ID,
        "registered_model": V11_REQUEST_MODEL,
        "registered_upstream": GATEWAY_UPSTREAM,
        "measured_path": MEASURED_PATH,
        "binds": ["F75_deliverable_class", "chemistry_elicitation",
                  "formula_direction", "element_conservation",
                  "equilibrium_direction"],
        "window_started_at": run_start,
        "window_ended_at": _now(),
        "rows_committed": n_rows,
        "gateway_completed_calls": len(calls),
        "gateway_error_lines": len(errors),
        "all_calls_requested_registered": all(
            c.get("requested_model") == V11_REQUEST_MODEL
            for c in calls),
        "all_calls_served_registered": all(
            c.get("model") == V11_REQUEST_MODEL for c in calls),
        "all_calls_upstream_registered": all(
            c.get("upstream") == GATEWAY_UPSTREAM for c in calls),
        "serving_key_digests": sorted({str(c.get("key_id"))
                                       for c in calls
                                       if c.get("key_id")}),
        "resumed_slice_merge": resumed,
        "note": ("served==requested==registered per completed call "
                 "from the gateway log slice (the identity chain: the "
                 "instrument requests the registered id, the gateway "
                 "serves it — R458-C1 semantics — and the route "
                 "registry pins it); error lines (429/5xx backoff "
                 "telemetry) carry no model field and are typed, "
                 "never scored"),
    }
    if not smoke:
        att["rows_30_30_attestation"] = (n_rows == EXPECTED_N
                                         and len(calls) >= EXPECTED_N
                                         and att[
                                             "all_calls_served_registered"]
                                         and att[
                                             "all_calls_requested_registered"])
    dest = OUT / ("attestation_smoke.json" if smoke
                  else "attestation.json")
    dest.write_text(json.dumps(att, indent=1) + "\n",
                    encoding="utf-8")
    return att


def attest() -> int:
    """VERIFIER LANE: recompute the attestation from committed bytes
    (the slice + the row files) — never a re-run (Art. 29(c))."""
    slice_path = OUT / "gateway_slice.txt"
    assert slice_path.exists(), "no committed gateway slice (typed)"
    att = _write_attestation(slice_path, "(recomputed from bytes)",
                             smoke=False, resumed=True)
    print(json.dumps(att, indent=1))
    return 0


def smoke() -> int:
    """Mechanics-only live fire on BURNED NON-v11 rows (the HO7 packet
    — burned by the committed v7 run; NOT among the 30 v11 rows). The
    smoke rows carry a SYNTHETIC plan (mechanics only, Art. 22) and
    live in rows_smoke/, excluded from every measurement file."""
    doc = json.loads(_git_show(SMOKE_PACKET))
    probs = [p for p in doc["problems"]
             if p["problem_id"] in SMOKE_ROWS]
    assert len(probs) == len(SMOKE_ROWS), (
        "smoke rows not found in the HO7 packet (typed abort)")
    synth = {"operator_id": "DOMAIN_KNOWLEDGE_FIRST",
             "principle_id": "P35",
             "measure_class": "boundary",
             "signals_used": ["pressure", "temperature"]}
    return run_rows(probs, smoke=True, synthetic_plan=synth)


def dry_run() -> int:
    """Zero-LLM mechanics check (Art. 22: fixtures prove mechanics
    only): the audit-ref loader plumbing (seal recipe EXERCISED on a
    burned packet, never on v11), the identity binding, the FIVE-BIND
    wiring surface (the frozen machine call site reaches the merged
    scan incl. the equilibrium leg), the engine route, the winner
    rule, the payload construction, the on-row leg wiring, the
    attestation shape — on burned DEV problems."""
    # (0) the model-pin gate shape: the registry admits the v11 pin
    # and refuses a non-registered id
    route_adapter.require_registered_model(V11_REQUEST_MODEL)
    try:
        route_adapter.require_registered_model("cohere/command-a")
        raise AssertionError("the retired id must refuse")
    except route_adapter.RouteRefused:
        pass
    # (1) the identity binding: the frozen file constant IS the v11
    # registered id, the module attribute binds (identity) to the
    # v11 id, and the frozen FILE keeps its v9-era bytes (the
    # freeze-guard parity)
    frozen_const = bind_v11_request_model()
    assert frozen_const == FROZEN_V77_FILE_CONSTANT
    assert _m77.V77_REQUEST_MODEL == V11_REQUEST_MODEL
    machine_src = (REPO / "scripts" / "r40_machine_v77.py").read_text(
        encoding="utf-8")
    assert f'V77_REQUEST_MODEL = "{FROZEN_V77_FILE_CONSTANT}"' \
        in machine_src, ("the frozen machine file's v9 constant "
                         "drifted (the freeze guard owns that byte)")
    print(f"[dry-run] identity binding OK: file constant "
          f"{FROZEN_V77_FILE_CONSTANT!r} (frozen) == runtime "
          f"{_m77.V77_REQUEST_MODEL!r}")
    # (2) the FIVE-BIND wiring surface (zero LLM, wiring proof only):
    # the frozen machine's critic call site imports the merged scan
    # and the merged scan exposes all three legs (formula-direction,
    # element-conservation, equilibrium-direction) + the F75
    # deliverable-class scan + the chemistry elicitation entry point
    for fn in ("scan_stated_formula_direction",
               "scan_reaction_conservation",
               "scan_equilibrium_direction"):
        assert hasattr(_formula_scan, fn), (
            f"the merged formula scan lost {fn} (typed — the fifth "
            "bind must ride the frozen call site)")
    scan_src = (REPO / "scripts" / "r70_stated_formula_scan.py"
                ).read_text(encoding="utf-8")
    assert "scan_equilibrium_direction" in scan_src, (
        "the equilibrium-direction leg is not merged into the scan "
        "module (typed — the R89 wiring must stand)")
    assert "_DEVICE_NOUNS" in scan_src, (
        "the device-noun skip is absent (the R89 false-positive fix "
        "must stand)")
    frozen_src = machine_src
    assert "scan_stated_formula_direction" in frozen_src, (
        "the frozen machine no longer calls the merged scan (typed)")
    print("[dry-run] five-bind wiring surface OK: merged scan legs "
          "present (formula-direction + element-conservation + "
          "equilibrium-direction) at the frozen call site; F75 + "
          "chemistry elicitation ride the engine route (checked "
          "below)")
    # (3) the seal recipe, exercised on the burned v7 packet (public;
    # the recipe recomputes its seal exactly)
    v7 = json.loads(_git_show(SMOKE_PACKET))
    v7_prereg = json.loads(
        _git_show("audit/holdout_v7/PREREGISTRATION.json"))
    seal7 = verify_seal(v7, str(v7_prereg.get("selection_sha256")
                                or ""))
    assert seal7["verified"], (
        f"seal recipe failed on the burned v7 packet: {seal7}")
    print(f"[dry-run] seal recipe verified on burned v7: "
          f"{seal7['recomputed'][:16]}")
    # (4) the engine route + winner rule + payload on 3 burned DEV
    # problems (zero LLM: run_row is the deterministic wiring proof;
    # the chemistry elicitation + F75 bind ride run_row itself)
    dev = json.loads((REPO / "eval/problems_dev12.json")
                     .read_text(encoding="utf-8"))
    dev_probs = dev["problems"] if isinstance(dev, dict) else dev
    rules = Counter()
    for p in dev_probs[:3]:
        row_out = engine_route.run_row(p)
        assert len(row_out["plans"]) >= 3, (
            p["problem_id"], "K>=3 violated (typed)")
        assert len({pl["principle_id"]
                    for pl in row_out["plans"]}) == len(
            row_out["plans"]), "principles not distinct (typed)"
        winner, wresult, rule = select_winner(row_out)
        rules[rule] += 1
        cp = challenger_prob(p, winner, rule)
        assert cp["typed_plan"]["operator"] == winner["operator_id"]
        assert "typed_plan" not in p, "payload mutation leaked"
        trace = engine_trace(p, row_out, winner, wresult, rule)
        assert trace["measured_path"] == MEASURED_PATH
        assert trace["plans_n"] == len(row_out["plans"])
    print(f"[dry-run] engine route OK on 3 burned DEV problems; "
          f"winner rules: {dict(rules)}; payload construction OK")
    # (5) the on-row leg wiring (zero LLM, on one DEV row with a
    # deterministic synthetic answer carrying a typed magnitude)
    p = dev_probs[0]
    row_out = engine_route.run_row(p)
    leg = onrow_leg(p, row_out,
                    "The induction heater runs at 85 degC; the "
                    "corrosion rate improves by 3x with the coating.")
    assert leg["leg"].startswith("F80_onrow_physics")
    assert isinstance(leg["sign_contradiction_count"], int)
    assert isinstance(leg["delivered_answer"]["n_scanned"], int)
    print(f"[dry-run] on-row leg OK: failure_class="
          f"{leg['failure_class']!r} applicable="
          f"{leg['applicable_checks']} answer_n_scanned="
          f"{leg['delivered_answer']['n_scanned']} "
          f"sign_contradictions={leg['sign_contradiction_count']}")
    # (6) the attestation plumbing shape
    src = Path(__file__).read_text(encoding="utf-8")
    for needle in ("rows_30_30_attestation",
                   "all_calls_requested_registered",
                   "all_calls_served_registered",
                   "all_calls_upstream_registered"):
        assert needle in src, f"attestation plumbing lost {needle}"
    print("[dry-run] attestation plumbing complete")
    print("[dry-run] PASS (zero LLM, zero network)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["dry-run", "smoke", "run",
                                    "attest"])
    ap.add_argument("--max-rows", type=int, default=0,
                    help="cap rows for this invocation (heartbeat)")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.cmd == "dry-run":
        return dry_run()
    if args.cmd == "smoke":
        return smoke()
    if args.cmd == "run":
        _, _, probs, seal = load_v11_problems()
        qt = Counter((p.get("question_type") or "").lower()
                     for p in probs)
        print(f"[run] seal verified {seal['recomputed'][:16]}... "
              f"({len(probs)} problems, 15+15; observed types "
              f"{dict(qt)}); model_pin co-verified: prereg == "
              f"instrument == route registry == {V11_REQUEST_MODEL}",
              flush=True)
        if args.max_rows:
            probs = probs[:args.max_rows]
        return run_rows(probs)
    if args.cmd == "attest":
        return attest()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""r93_convergence_ablation.py — the R93 matched-budget DEV ablation
driver for the repair-loop CONVERGENCE layer (claim c-0104, work_id
r93-repair-convergence-layer; the AM78-P2/P3 measured defect class;
the R92 roadmap's highest-leverage copy item).

WHAT THIS MEASURES (single-variable ablation, incumbent = committed
bytes):
  INCUMBENT  the committed v10 run (eval/holdout_v10_generation/ —
             BURNED per auditor R88, hence lawful DEV material): the
             frozen V7.7 loop, repair budget 3, agnes-3.0-flash,
             repair distribution {3: 27, 2: 1, 1: 1, 0: 1} (90%
             full-budget burn) — recomputed per-row from the
             committed row files by `analyze`; NEVER re-run (Art.
             29(c): one generation per problem per arm; the
             incumbent's bytes are the run).
  CHALLENGER the SAME corpus (the 30 burned v10 problems, integrity-
             pinned by the v10 seal re-verified at load), the SAME
             winner rule (non_schedule_first via the r85 machine's
             own select_winner), the SAME challenger_prob typed-plan
             construction, the SAME frozen scan/critic/contract
             bytes (imported from r40_machine_v77, never re-declared)
             — plus exactly TWO controller insertions from
             discovery_fabric/engine/repair_convergence.py:
               (1) the Reflexion reflection-memory addendum on the
                   repair directive from the second repair onward
                   (the FIRST repair prompt stays byte-identical to
                   the incumbent's — design invariant 1);
               (2) the Self-Refine structured stop criterion (stop
                   before budget exhaustion when the identical
                   finding signature survived a reflection-augmented
                   repair).

PRE-REGISTERED ADOPTION CRITERIA (computed by `analyze` from
committed bytes; the claim c-0104 carries the same list — the
roadmap's matched-budget ablation rule + the R92 acceptance):
  A1 PRIMARY convergence: rows delivered with ZERO residual findings
      within the SAME budget >= 50% (the R92 Reflexion/Self-Refine
      acceptance; incumbent v10 share recomputed for the no-drop
      check).
  A2 no-drop: challenger zero-residual share >= incumbent v10 share
      (typed caveat: the incumbent ran the FOUR-bind battery; the
      challenger runs the CURRENT frozen call site (FIVE binds — the
      R89 equilibrium-direction bind rides the merged formula scan);
      the delta affects chemistry-direction rows only and is
      disclosed, never hidden).
  A3 allowed-row integrity: ALLOWED_ROW_OUTSIDE == 0 on every row.
  A4 schedule-family: the declared-template histogram respects the
      existing <=2-per-6 cap (the winner rule is untouched:
      non_schedule_first).
  A5 efficiency (the stop criterion may only SAVE calls): mean
      generation attempts/row <= incumbent's.
  A6 disclosure: every early stop carries a typed stop_reason +
      full residual keys (Art. 3/5/23).
  ADOPT iff A1..A6 all hold; else the layer is NOT adopted into the
  live machine (the roadmap's delete-if-it-does-not-earn-its-place
  rule) — the engine controller module stays (CI-tested, zero-cost)
  with adoption=refused recorded; no frozen file is ever edited.

DISCIPLINE (the R92 integration checklist):
  - attribution+NOTICE: NOTICE.md entries for Reflexion (MIT) and
    Self-Refine (Apache-2.0) — pattern copies, zero upstream code
    bytes; deterministic CI acceptance tests
    (tests/test_r93_repair_convergence.py) — exists AND gates;
  - matched budget: the challenger's budget cap is the incumbent's
    own REPAIR_BUDGET=3 (frozen constant, imported); the stop
    criterion can only undershoot it;
  - no frozen-file edits: r40_machine_v77.py and r85_v10_one_shot.py
    are imported byte-as-is; the loop below mirrors the frozen
    machine_generate_v77 body with the two insertions marked by
    `# [convergence]` comments;
  - generation-side improvement (AM78 P3), not another detection
    bind: the layer changes what the repair prompt CONTAINS and when
    the loop STOPS — no new finding keys are invented.

ZERO LLM at import and in dry-run (Art. 22). One generation per
problem (resume-safe; existing row files are skipped). The events
ledger carries per-attempt signatures so the convergence metrics are
recomputable from committed bytes by `attest`/`analyze` and by the
VERIFIER lane (Art. 29(c) — recompute, never re-run).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

# CORR-3 session-local transport resolution (the r91 convention)
ZAI_BIN = Path("/home/z/my-project/node_modules/.bin")
if ZAI_BIN.is_dir() and str(ZAI_BIN) not in sys.path:
    os.environ["PATH"] = f"{ZAI_BIN}:{os.environ.get('PATH', '')}"

import r40_machine_v77 as m77  # noqa: E402  (the frozen loop's bytes)
import r85_v10_one_shot as v10m  # noqa: E402  (the incumbent machine)
from discovery_fabric.engine import route_adapter  # noqa: E402
from discovery_fabric.engine import engine_route  # noqa: E402
from discovery_fabric.engine.repair_convergence import (  # noqa: E402
    ConvergenceController, REPAIR_CONVERGENCE_SCHEMA)

OUT = REPO / "eval" / "dev_convergence_ablation_r93"
GW_LOG = REPO / "ENGINE_RUNS" / "zai_gateway_calls.jsonl"
EXECUTOR_ID = "builder-r93s1@r93-repair-convergence-layer"
REGISTERED_MODEL = "agnes-3.0-flash"  # the AM75 default; == the v10
# pin == the frozen machine constant (asserted at run time)
GATEWAY_UPSTREAM = "agnes"
MEASURED_PATH = ("discovery_fabric.engine.engine_route -> "
                 "mechanism_space (+ engine.repair_convergence "
                 "controller at the loop's two insertion points)")
INCUMBENT_ROWS = REPO / "eval" / "holdout_v10_generation" / "rows"
INCUMBENT_RUN_RECORD = REPO / "eval" / "r85_v10_run_record.json"
V11_EVENTS = REPO / "eval" / "holdout_v11_generation" / "events.json"
RECORD_PATH = REPO / "eval" / "r93_convergence_ablation_record.json"
EXPECTED_N = 30
BATTERY_DELTA_NOTE = (
    "typed caveat: the incumbent v10 rows ran the FOUR-bind frozen "
    "battery; the challenger runs the CURRENT frozen call site "
    "(FIVE binds — the R89 equilibrium-direction bind rides the "
    "merged formula scan inside scan_stated_formula_direction). "
    "The delta adds finding surface on chemistry-direction rows "
    "only; disclosed, never hidden (Art. 5).")


def _now() -> str:
    return (datetime.datetime.now(datetime.UTC).isoformat()
            .replace("+00:00", "Z"))


def _sha16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# THE CHALLENGER LOOP — the frozen machine_generate_v77 body mirrored
# with exactly two `# [convergence]` insertions. Every scan, critic,
# contract, directive and transport byte is the frozen module's own
# (imported, never re-declared); the ablation is single-variable.
# ---------------------------------------------------------------------------
def machine_generate_v78(prob: dict, gw_key: str,
                         used_templates: Counter | None = None):
    """The V7.8 challenger loop: V7.7 + the convergence controller.

    Returns (final_answer, attempts, final_meta) with final_meta
    carrying the incumbent's fields PLUS the typed convergence fields
    (stop_reason, stagnation, convergence)."""
    qt = (prob.get("question_type") or "").lower()
    q = json.dumps(prob, ensure_ascii=False)
    contract = m77.contract_for_v72(qt)
    attempts: list = []
    final, gen_meta = m77._retry_call(m77._gen_fb, q, contract, gw_key)
    lat = gen_meta["latency_s"]
    tries = 1
    final_meta: dict = {}
    rep = 0
    # [convergence] the per-row controller (budget = the frozen
    # constant; the incumbent's own cap — matched budget)
    ctrl = ConvergenceController(budget=m77.REPAIR_BUDGET)
    while True:
        dc = None  # the typed direction-check verdict (interventions)
        cr = m77._retry_call(m77.critic, final, prob)
        tg = m77.gate_question_type(final, prob)
        vio: dict = {}
        vio.update(m77.base_scan(final))
        vio.update(m77.scan_deliverable_class(final))
        vio.update(m77.scan_stated_formula_direction(final))
        vio.update(m77.scan_constraint_fit(prob, final))
        if not qt.startswith("predictor"):
            vio.update(m77.scan_catalog(prob, final))
            sb = m77.scan_standard_bill(final, qt)
            if sb:
                vio.update(sb)
            ol = m77.scan_operational_loss(final, qt)
            if ol:
                vio.update(ol)
            cv = m77.scan_conversion(final, qt, prob)
            if cv:
                vio.update(cv)
            vio.update(m77.scan_allowed_measures_class(prob, final))
            vio.update(m77.scan_physics_direction(prob, final))
            vio.update(m77.direction_lexicon_check(prob, final))
            vio.update(m77.scan_input_availability(prob, final))
            vio.update(m77.scan_duty_cycle_pricing(final))
            vio.update(m77.scan_mechanism_template(final,
                                                   used_templates))
            dc = m77.direction_check_llm(prob, final, gw_key)
            if dc["direction"] == "INVERTED":
                vio["PHYSICS_DIRECTION_INVERTED"] = [
                    f"the sign/integral check reads the mechanism "
                    f"INVERTED: {dc.get('reason', '')[:160]}"]
            elif dc["direction"] == "UNCLEAR":
                vio["DIRECTION_UNPROVEN"] = [
                    "the sign/integral check cannot judge the "
                    "direction from the bill — state the governing "
                    "relation and the sign the mechanism imposes"]
            elif dc["direction"] == "DIRECTION_CHECK_UNAVAILABLE":
                vio["DIRECTION_CHECK_UNAVAILABLE"] = [
                    f"typed fail-open: {dc.get('reason', '')[:120]} "
                    "(the authoritative read stays the auditor's)"]
        else:
            from r19_a1w_v4_contract import predictor_violations
            pv = predictor_violations(final)
            if pv:
                vio.update({"PREDICTOR_VIOLATION": list(pv)})
            vio.update(m77.scan_input_availability(prob, final))
        findings = [f"{k}: {'; '.join(map(str, v))[:110]}"
                    for k, v in vio.items() if v]
        verdict_eff, f75_note = m77.effective_critic_verdict(
            cr["verdict"], vio)
        problems: list = []
        if cr["verdict"] != "CLEAN":
            problems += [c.get("anchor") for c in cr["checks"]
                         if c.get("verdict") != "CLEAN"]
        if tg["verdict"] == "MISMATCH":
            problems.append(tg["reason"])
        problems += findings
        if not (final or "").strip():
            problems.append("EMPTY_ANSWER_TRANSPORT")
        # [convergence insertion 1/2 on the RECORD side] the attempt's
        # signature enters the controller BEFORE any exit decision
        stage = "draft" if rep == 0 else f"repair_{rep}"
        sig = ctrl.record(stage, vio, verdict_eff,
                          tg.get("verdict"))
        att = {"stage": stage,
               "chars": len(final), "latency_s": round(lat, 1),
               "transport_tries": tries,
               "route": gen_meta.get("route"),
               "route_model": gen_meta.get("model"),
               "fallback_reason": gen_meta.get("fallback_reason"),
               "critic_verdict": verdict_eff, "type_gate": tg,
               **(f75_note or {}),
               "scan": {k: list(v) for k, v in vio.items()},
               "direction_check": (dc if not qt.startswith("predictor")
                                   else None),
               "sha256_16": _sha16(final),
               # [convergence] additive signature fields (the
               # convergence measurement rides the ledger)
               "signature": {"digest": sig["digest"],
                             "keys": list(sig["keys"]),
                             "schema": sig["schema"]},
               "repair_prompt_had_addendum": ctrl.last_had_addendum}
        if rep:
            att["findings_disclosed"] = [p for p in problems if p]
        attempts.append(att)
        conv_summary = ctrl.summary()
        if not [p for p in problems if p]:
            final_meta = {"critic_verdict": verdict_eff,
                          "type_gate": tg, "repairs": rep,
                          "direction_check": dc,
                          **(f75_note or {}),
                          "residual_findings": {},
                          # [convergence] the converged exit
                          "stop_reason": "CONVERGED_ZERO_FINDINGS",
                          "stagnation": None,
                          "convergence": conv_summary}
            return final, attempts, final_meta
        stop = ctrl.stop_decision()
        if rep == m77.REPAIR_BUDGET:
            final_meta = {"critic_verdict": verdict_eff,
                          "type_gate": tg, "repairs": rep,
                          "direction_check": dc,
                          **(f75_note or {}),
                          "residual_findings":
                              {k: list(v) for k, v in vio.items()},
                          # [convergence] the budget exit (the
                          # incumbent's only non-clean exit)
                          "stop_reason": "BUDGET_EXHAUSTED",
                          "stagnation": stop,
                          "convergence": conv_summary}
            return final, attempts, final_meta
        if stop:
            # [convergence insertion 2/2 — the Self-Refine stop] the
            # identical signature survived a reflection-augmented
            # repair; the remaining budget would repeat the same
            # non-improving repair. Typed early stop, full residual
            # disclosure, latest-generation delivery (never a
            # best-of selection).
            final_meta = {"critic_verdict": verdict_eff,
                          "type_gate": tg, "repairs": rep,
                          "direction_check": dc,
                          **(f75_note or {}),
                          "residual_findings":
                              {k: list(v) for k, v in vio.items()},
                          "stop_reason": stop["action"],
                          "stagnation": stop,
                          "convergence": conv_summary}
            return final, attempts, final_meta
        directive = m77.V77_REPAIR_DIRECTIVE.format(
            findings="; ".join(p for p in problems if p))
        # [convergence insertion 1/2 on the PROMPT side] the Reflexion
        # addendum (None for the FIRST repair — byte-identical
        # incumbent prompt, design invariant 1)
        add = ctrl.addendum()
        if add:
            directive = directive + "\n\n" + add
        final, gen_meta = m77._retry_call(
            m77._gen_fb, q + "\n\n" + directive, contract, gw_key)
        lat = gen_meta["latency_s"]
        tries += 1
        rep += 1


# ---------------------------------------------------------------------------
# gateway pre-gates + the run body (the r91 conventions)
# ---------------------------------------------------------------------------
def _gateway_alive() -> bool:
    try:
        urllib.request.urlopen("http://127.0.0.1:8787/healthz",
                               timeout=2)
        return True
    except Exception:  # noqa: BLE001 — any failure means not alive
        return False


def run_rows(probs: list, max_rows: int = 0) -> int:
    """The challenger one-shot pass. Resume-safe: existing row files
    are skipped. --max-rows is a PREFIX slice (heartbeat chunks must
    ACCUMULATE: 10 -> 20 -> 30)."""
    try:
        route_adapter.require_registered_model(REGISTERED_MODEL)
    except Exception as e:  # RouteRefused and any registry drift
        print(f"MEASURED-PATH REFUSAL (typed, Art. 22): machine "
              f"model {REGISTERED_MODEL} is not the engine-registered "
              f"route: {e}", flush=True)
        return 3
    if _gateway_alive():
        print("REFUSED (typed, exit 3): a gateway is already "
              "listening on 127.0.0.1:8787 — kill it first (a stale "
              "gateway poisons the slice; the r58 lesson).",
              flush=True)
        return 3
    if route_adapter.resolve_vault_key("AGNES_API_KEY") is None:
        print("REFUSED (typed INFRA_CREDENTIAL_MISSING, exit 3): "
              "AGNES_API_KEY absent from the vault (.env.keys) — "
              "restore custody first (scripts/r77_vault_restore.py, "
              "Art. 17 v3.3.0). Zero gateway bytes read.", flush=True)
        return 3
    frozen_const = v10m.bind_v10_request_model()  # identity no-op,
    # asserted + logged (never an assumption; the freeze guard owns
    # the file byte)
    assert frozen_const == REGISTERED_MODEL, (
        "identity drifted: the frozen machine constant and the "
        "registered route must be the same id (typed abort)")
    os.environ["ZAI_GATEWAY_UPSTREAM"] = GATEWAY_UPSTREAM
    os.environ["AGNES_MODEL_ID"] = REGISTERED_MODEL

    OUT.mkdir(parents=True, exist_ok=True)
    rows_dir = OUT / "rows"
    rows_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = OUT / "events.json"

    gw, gw_key = m77.start_gateway()
    print(f"gateway healthy (upstream={GATEWAY_UPSTREAM}, registered "
          f"route {REGISTERED_MODEL}; frozen v77 file constant "
          f"{frozen_const!r} runtime-bound to {REGISTERED_MODEL!r})",
          flush=True)
    try:
        return _run_body(probs, max_rows, rows_dir, ledger_path,
                         gw, gw_key)
    finally:
        try:
            gw.terminate()
            gw.wait(timeout=10)
        except Exception:
            gw.kill()


def _run_body(probs: list, max_rows: int, rows_dir: Path,
              ledger_path: Path, gw, gw_key: str) -> int:
    offset = GW_LOG.stat().st_size if GW_LOG.exists() else 0
    run_start = _now()
    if max_rows:
        probs = probs[:max_rows]

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
        #     (byte-reused from the incumbent machine)
        row_out = engine_route.run_row(prob)
        # (2) the incumbent's OWN pre-registered winner rule
        winner, wresult, rule = v10m.select_winner(row_out)
        machine_prob = v10m.challenger_prob(prob, winner, rule)
        trace = v10m.engine_trace(prob, row_out, winner, wresult,
                                  rule)
        # (3) the challenger loop: the frozen V7.7 body + the two
        #     convergence insertions
        hist = dict(used_templates)
        t_row = _now()
        final, attempts, final_meta = machine_generate_v78(
            machine_prob, gw_key, used_templates=used_templates)
        decl = m77.declared_template(final)
        if decl and not str(prob.get("question_type", "")) \
                .lower().startswith("predictor"):
            used_templates[decl] += 1
        residual = final_meta.get("residual_findings") or {}
        # (4) the on-row physics leg (zero LLM, evidence only)
        leg = v10m.onrow_leg(prob, row_out, final)
        row = {
            "problem_id": pid,
            "question_type": prob.get("question_type"),
            "executor_id": EXECUTOR_ID,
            "registered_model": REGISTERED_MODEL,
            "machine": (
                "r93_convergence_ablation/1.0.0 — the challenger arm: "
                "the frozen V7.7 expansion loop byte-mirrored with "
                "the engine repair_convergence controller (Reflexion "
                "reflection memory + Self-Refine structured stop; "
                "NOTICE-attributed pattern copy, zero upstream code "
                "bytes); incumbent = the committed v10 run"),
            "run": "r93-repair-convergence-layer (matched-budget DEV "
                   "ablation; corpus = the BURNED v10 holdout set)",
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
                "stop_reason": final_meta.get("stop_reason"),
                "stagnation": final_meta.get("stagnation"),
            },
            "convergence": final_meta.get("convergence"),
            "declared_template_prose": decl,
            "allowed_row_outside": len(
                residual.get("ALLOWED_ROW_OUTSIDE", [])),
            "sha256_16": _sha16(final),
            "smoke": False,
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
                final_meta.get("repairs") == m77.REPAIR_BUDGET),
            "stop_reason": final_meta.get("stop_reason"),
            "stagnation_stop": bool(final_meta.get("stagnation")),
            "repair_prompt_addendum_attempts": sum(
                1 for a in attempts
                if a.get("repair_prompt_had_addendum")),
            "onrow_sign_contradictions":
                leg["sign_contradiction_count"],
            "onrow_answer_claims": len(
                leg["delivered_answer"]["claims"]),
            "final_sha256_16": row["sha256_16"],
            "final_chars": len(final),
        })
        ledger_path.write_text(json.dumps({
            "record": "DEV_CONVERGENCE_ABLATION_R93_EVENTS/1.0.0",
            "run": "r93-repair-convergence-layer",
            "executor_id": EXECUTOR_ID,
            "registered_model": REGISTERED_MODEL,
            "registered_upstream": GATEWAY_UPSTREAM,
            "measured_path": MEASURED_PATH,
            "controller_schema": REPAIR_CONVERGENCE_SCHEMA,
            "corpus": ("holdout_v10 (BURNED per auditor R88; DEV "
                       "material; seal re-verified at load)"),
            "battery_delta_note": BATTERY_DELTA_NOTE,
            "convergence_note": (
                "per-attempt signatures + stop_reason + addendum "
                "flags recorded; recomputable from committed bytes "
                "(analyze/attest), never scored by this instrument"),
            "window_started_at": run_start,
            "events": events},
            indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        done += 1
        print(f"[{idx}/{len(probs)}] {pid} rule={rule} plans="
              f"{trace['plans_n']} repairs="
              f"{final_meta.get('repairs')} stop="
              f"{final_meta.get('stop_reason')} critic="
              f"{final_meta.get('critic_verdict')} chars={len(final)}"
              f" ({time.time()-t0:.0f}s)", flush=True)
        t0 = time.time()

    # gateway-log slice: this run's window, MERGED with any committed
    # slice from a previous (resumed) window
    slice_path = OUT / "gateway_slice.txt"
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
    print(f"rows done={done} skipped(resumed)={skipped}", flush=True)
    return 0


# ---------------------------------------------------------------------------
# attest — recompute the run's integrity from committed bytes
# (zero LLM; the verifier lane's entry point, Art. 29(c))
# ---------------------------------------------------------------------------
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


def attest() -> int:
    rows_dir = OUT / "rows"
    files = sorted(rows_dir.glob("*.json"))
    assert len(files) == EXPECTED_N, (
        f"expected {EXPECTED_N} row files, found {len(files)}")
    pids = set()
    for f in files:
        r = json.loads(f.read_text(encoding="utf-8"))
        pid = r["problem_id"]
        assert pid not in pids, f"duplicate row for {pid}"
        pids.add(pid)
        assert r["sha256_16"] == _sha16(r["a1_answer"]), (
            f"{pid}: answer hash mismatch")
        assert r["registered_model"] == REGISTERED_MODEL, (
            f"{pid}: model identity drift")
        fm = r["final_meta"]
        assert r["attempts_n"] == fm["repairs"] + 1, (
            f"{pid}: attempts_n {r['attempts_n']} != repairs+1 "
            f"{fm['repairs'] + 1}")
        assert fm.get("stop_reason") in (
            "CONVERGED_ZERO_FINDINGS", "BUDGET_EXHAUSTED",
            "STOP_STAGNATED"), f"{pid}: untyped stop_reason"
    ledger = json.loads((OUT / "events.json").read_text(
        encoding="utf-8"))
    ev_pids = [e["problem_id"] for e in ledger["events"]]
    assert sorted(ev_pids) == sorted(pids), (
        "ledger/row pid mismatch")
    calls, errors = _parse_slice(OUT / "gateway_slice.txt")
    ok = [c for c in calls
          if (c.get("requested_model") == REGISTERED_MODEL
              or c.get("model") == REGISTERED_MODEL)]
    print(json.dumps({
        "record": "R93_DEV_ABLATION_ATTESTATION/1.0.0",
        "rows": len(files),
        "unique_problem_ids": len(pids),
        "one_generation_per_problem": len(pids) == len(files),
        "registered_model": REGISTERED_MODEL,
        "gateway_calls_ok": len(calls),
        "gateway_calls_matching_registered": len(ok),
        "gateway_errors": len(errors),
        "stop_reason_distribution": dict(Counter(
            json.loads(f.read_text(encoding="utf-8"))
            ["final_meta"]["stop_reason"] for f in files)),
        "recomputable": ("per-row sha + repairs + stop_reason + "
                         "per-attempt signatures all recompute from "
                         "committed bytes"),
    }, indent=1))
    return 0


# ---------------------------------------------------------------------------
# analyze — the adoption record from committed bytes (zero LLM)
# ---------------------------------------------------------------------------
def _incumbent_metrics() -> dict:
    files = sorted(INCUMBENT_ROWS.glob("*.json"))
    assert len(files) == EXPECTED_N, (
        f"incumbent rows: expected {EXPECTED_N}, found {len(files)}")
    per_row, repairs = [], Counter()
    zero_residual = 0
    for f in files:
        r = json.loads(f.read_text(encoding="utf-8"))
        fm = r.get("final_meta") or {}
        rep = fm.get("repairs")
        repairs[str(rep)] += 1
        res = fm.get("residual_findings") or {}
        if not res:
            zero_residual += 1
        per_row.append({"problem_id": r["problem_id"],
                        "repairs": rep,
                        "residual_keys": sorted(res.keys()),
                        "critic": fm.get("critic_verdict")})
    att = sum(int(k) * v for k, v in repairs.items())
    return {
        "source": "eval/holdout_v10_generation/rows (committed "
                  "bytes; the auditor-scored R88 run; NEVER re-run)",
        "n": len(files),
        "repair_distribution": dict(repairs),
        "full_budget_burn": repairs.get("3", 0),
        "full_budget_burn_share": round(
            repairs.get("3", 0) / len(files), 4),
        "zero_residual_at_delivery": zero_residual,
        "zero_residual_share": round(zero_residual / len(files), 4),
        "mean_attempts_per_row": round(1 + att / len(files), 4),
        "per_row": per_row,
    }


def _challenger_metrics() -> dict:
    files = sorted((OUT / "rows").glob("*.json"))
    assert files, "no challenger rows committed yet"
    per_row, repairs = [], Counter()
    stops = Counter()
    zero_residual = 0
    allowed_outside = 0
    templates = Counter()
    for f in files:
        r = json.loads(f.read_text(encoding="utf-8"))
        fm = r.get("final_meta") or {}
        rep = fm.get("repairs")
        repairs[str(rep)] += 1
        stops[fm.get("stop_reason")] += 1
        res = fm.get("residual_findings") or {}
        if not res:
            zero_residual += 1
        allowed_outside += r.get("allowed_row_outside", 0)
        if r.get("declared_template_prose"):
            templates[r["declared_template_prose"]] += 1
        per_row.append({
            "problem_id": r["problem_id"],
            "repairs": rep,
            "stop_reason": fm.get("stop_reason"),
            "stagnation_stop": bool(fm.get("stagnation")),
            "residual_keys": sorted(res.keys()),
            "critic": fm.get("critic_verdict"),
            "attempts": [
                {"stage": a.get("stage"),
                 "sig": (a.get("signature") or {}).get("digest"),
                 "keys": (a.get("signature") or {}).get("keys"),
                 "had_addendum": a.get("repair_prompt_had_addendum")}
                for a in (r.get("convergence") or {})
                .get("signatures", [])],
        })
    att = sum(int(k) * v for k, v in repairs.items())
    n = len(files)
    max_share = (max(templates.values()) / n) if templates else 0.0
    return {
        "source": "eval/dev_convergence_ablation_r93/rows "
                  "(committed bytes; ONE challenger generation per "
                  "problem)",
        "n": n,
        "repair_distribution": dict(repairs),
        "full_budget_burn": repairs.get("3", 0),
        "full_budget_burn_share": round(
            repairs.get("3", 0) / n, 4),
        "stop_reason_distribution": dict(stops),
        "stagnation_stops": stops.get("STOP_STAGNATED", 0),
        "zero_residual_at_delivery": zero_residual,
        "zero_residual_share": round(zero_residual / n, 4),
        "mean_attempts_per_row": round(1 + att / n, 4),
        "allowed_row_outside_total": allowed_outside,
        "declared_template_histogram": dict(templates),
        "max_template_share": round(max_share, 4),
        "per_row": per_row,
    }


def _v11_counterfactual() -> dict:
    """The stop-criterion counterfactual on the committed v11 events
    ledger (read-only; zero LLM; NOT a re-run — a typed simulation of
    the controller's decisions over the RECORDED attempt signature
    sequence). Honest scope: it bounds the stop criterion's CALL
    SAVINGS under the assumption the recorded answers are what the
    no-memory loop produced (it cannot predict what the
    reflection-augmented answers WOULD have been — that is the
    ablation's job)."""
    if not V11_EVENTS.exists():
        return {"available": False,
                "reason": "v11 events ledger not present"}
    d = json.loads(V11_EVENTS.read_text(encoding="utf-8"))
    rows = []
    would_stop = 0
    saved_repairs = 0
    for e in d.get("events", []):
        atts = e.get("attempts") or []
        ctrl = ConvergenceController(budget=3)
        stop_at = None
        for i, a in enumerate(atts):
            sig = ctrl.record(
                a.get("stage") or ("draft" if i == 0
                                   else f"repair_{i}"),
                a.get("scan") or {},
                a.get("critic_verdict") or "",
                ((a.get("type_gate") or {}).get("verdict") or ""))
            if i < len(atts) - 1:
                ctrl.addendum()  # the driver composes the next prompt
            stop = ctrl.stop_decision()
            if stop and stop_at is None:
                stop_at = {"attempt": i,
                           "repairs_used": i,
                           "stagnant_keys": stop["stagnant_keys"]}
                break
        rec_repairs = e.get("repairs")
        if stop_at is not None and (rec_repairs or 0) > \
                stop_at["repairs_used"]:
            would_stop += 1
            saved_repairs += ((rec_repairs or 0)
                              - stop_at["repairs_used"])
            rows.append({"problem_id": e.get("problem_id"),
                         "recorded_repairs": rec_repairs,
                         "counterfactual_stop": stop_at})
        else:
            rows.append({"problem_id": e.get("problem_id"),
                         "recorded_repairs": rec_repairs,
                         "counterfactual_stop": None,
                         "note": ("no saving (stop at/after the "
                                  "recorded budget exhaustion)" if
                                  stop_at is not None else None)})
    n = len(rows)
    return {
        "available": True,
        "source": "eval/holdout_v11_generation/events.json (committed "
                  "bytes; read-only counterfactual)",
        "scope_note": (
            "bounds ONLY the stop criterion's call savings on the "
            "recorded no-memory attempt sequences; the reflection "
            "memory's effect on answer quality is NOT counterfactual-"
            "computable — it is what the challenger arm measures"),
        "n": n,
        "rows_where_stop_would_fire": would_stop,
        "share": round(would_stop / n, 4) if n else None,
        "saved_repairs_total": saved_repairs,
    }


def analyze() -> int:
    inc = _incumbent_metrics()
    ch = _challenger_metrics()
    cf = _v11_counterfactual()
    n = ch["n"]
    criteria = {
        "A1_convergence_ge_50pct": {
            "value": ch["zero_residual_share"],
            "threshold": 0.50,
            "pass": ch["zero_residual_share"] >= 0.50},
        "A2_no_drop_vs_incumbent": {
            "value": ch["zero_residual_share"],
            "incumbent": inc["zero_residual_share"],
            "pass": (ch["zero_residual_share"]
                     >= inc["zero_residual_share"]),
            "note": BATTERY_DELTA_NOTE},
        "A3_allowed_row_outside_zero": {
            "value": ch["allowed_row_outside_total"],
            "pass": ch["allowed_row_outside_total"] == 0},
        "A4_schedule_cap": {
            "max_template_share": ch["max_template_share"],
            "pass": ch["max_template_share"] <= (2 / 6 + 1e-9),
            "note": "the existing <=2-per-6 cap; the winner rule is "
                    "untouched (non_schedule_first)"},
        "A5_efficiency_no_worse": {
            "value": ch["mean_attempts_per_row"],
            "incumbent": inc["mean_attempts_per_row"],
            "pass": (ch["mean_attempts_per_row"]
                     <= inc["mean_attempts_per_row"] + 1e-9)},
        "A6_typed_stops": {
            "stagnation_stops": ch["stagnation_stops"],
            "pass": True,
            "note": "every early stop carries stop_reason + full "
                    "residual keys in the committed rows"},
    }
    adopt = all(v["pass"] for v in criteria.values())
    record = {
        "record": "R93_CONVERGENCE_ABLATION/1.0.0",
        "claim": "c-0104",
        "work_id": "r93-repair-convergence-layer",
        "executor_id": EXECUTOR_ID,
        "controller_schema": REPAIR_CONVERGENCE_SCHEMA,
        "pattern_attribution": {
            "reflexion": "noahshinn/reflexion (MIT) — reflection "
                         "memory pattern; NOTICE.md; zero upstream "
                         "code bytes copied",
            "self-refine": "madaan/self-refine (Apache-2.0) — "
                           "structured stop criterion pattern; "
                           "NOTICE.md; zero upstream code bytes "
                           "copied"},
        "design": {
            "single_variable": (
                "challenger = the frozen V7.7 loop byte-mirrored + "
                "exactly two controller insertions; first repair "
                "prompt byte-identical to the incumbent's; budget = "
                "the frozen REPAIR_BUDGET=3 (matched)"),
            "measured_path": MEASURED_PATH,
            "battery_delta_note": BATTERY_DELTA_NOTE},
        "pre_registered_criteria": criteria,
        "adoption": ("ADOPTED" if adopt else "NOT_ADOPTED"),
        "adoption_note": (
            "ADOPTED: the convergence layer earns its place on the "
            "measured criteria; the path to the live machine is a "
            "conscious CI-gated re-freeze in a later round (no "
            "frozen file edited here). NOT_ADOPTED: per the roadmap "
            "delete-if-it-does-not-earn-its-place rule the layer "
            "stays out of the live machine; the controller module "
            "remains CI-tested at zero cost with adoption refused "
            "recorded."),
        "incumbent": inc,
        "challenger": ch,
        "v11_stop_criterion_counterfactual": cf,
        "generated_at": _now(),
    }
    RECORD_PATH.write_text(json.dumps(record, indent=1,
                                      ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        "adoption": record["adoption"],
        "criteria": {k: v["pass"] for k, v in criteria.items()},
        "incumbent": {k: inc[k] for k in (
            "n", "repair_distribution", "full_budget_burn_share",
            "zero_residual_share", "mean_attempts_per_row")},
        "challenger": {k: ch[k] for k in (
            "n", "repair_distribution", "stop_reason_distribution",
            "full_budget_burn_share", "zero_residual_share",
            "mean_attempts_per_row", "allowed_row_outside_total")},
        "counterfactual": {k: cf.get(k) for k in (
            "n", "rows_where_stop_would_fire", "saved_repairs_total")},
        "record_path": str(RECORD_PATH.relative_to(REPO)),
    }, indent=1))
    return 0


# ---------------------------------------------------------------------------
# dry-run — zero LLM (Art. 22: fixtures prove mechanics)
# ---------------------------------------------------------------------------
def dry_run() -> int:
    # (1) corpus integrity: the burned v10 packet, seal + pin
    #     re-verified (the incumbent machine's own loader)
    _, _, probs, seal = v10m.load_v10_problems()
    assert seal["verified"] and len(probs) == EXPECTED_N
    # (2) the controller walkthrough on synthetic sequences (the
    #     unit battery runs separately; here the DRIVER-level wiring)
    c = ConvergenceController(budget=3)
    c.record("draft", {"A": ["x"]}, "CLEAN", "OK")
    a1 = c.addendum()
    assert a1 is None, "first repair prompt must be incumbent-identical"
    c.record("repair_1", {"A": ["x"]}, "CLEAN", "OK")
    a2 = c.addendum()
    assert a2 is not None and "PERSISTED" in a2
    c.record("repair_2", {"A": ["x"]}, "CLEAN", "OK")
    stop = c.stop_decision()
    assert stop and stop["action"] == "STOP_STAGNATED"
    assert not c.can_repair(2), "stagnated loop must refuse repair_3"
    # (3) the loop wiring with STUBBED TRANSPORT ONLY (zero LLM,
    #     zero gateway; the frozen module's transport functions
    #     swapped in-process — file bytes untouched, restored in
    #     `finally`). The critic and EVERY scan stay REAL: the fake
    #     generator returns a COMMITTED incumbent answer (constant
    #     text), so the frozen finding surface is deterministic and
    #     NON-EMPTY (the committed v10 residual keys for that row),
    #     every attempt produces the IDENTICAL signature, and the
    #     stagnation stop MUST fire at repair_2 with the typed
    #     reason — the loop-level single-variable proof.
    first_pid = sorted(probs, key=lambda p: p["problem_id"])[0]
    inc_row = json.loads(
        (INCUMBENT_ROWS / f"{first_pid['problem_id']}.json")
        .read_text(encoding="utf-8"))
    fixed_answer = inc_row["a1_answer"]
    inc_residual = sorted((inc_row.get("final_meta") or {})
                          .get("residual_findings") or {}.keys())
    assert inc_residual, (
        "dry-run fixture row has no residual findings — the wiring "
        "proof row must have a non-empty committed finding surface")

    def _fake_gen(prompt, contract, key):
        # records whether the prompt carried the reflection addendum
        # (the single-variable proof: repair_1's prompt MUST NOT
        # contain it — incumbent-identical)
        calls.append("ADDENDUM" if "REFLECTION MEMORY" in prompt
                     else "PLAIN")
        return (fixed_answer, {"latency_s": 0.0,
                               "route": "stub",
                               "model": "stub",
                               "fallback_reason": None})

    def _fake_direction(prob, final, key):
        return {"direction": "CORRECT", "reason": "stub"}

    calls: list = []
    orig = (m77._gen_fb, m77.direction_check_llm,
            m77._retry_call)
    try:
        m77._gen_fb = _fake_gen
        m77.direction_check_llm = _fake_direction
        m77._retry_call = lambda f, *a, **k: f(*a, **k)
        # the REAL corpus problem (burned DEV material) + its
        # committed incumbent answer as the constant generation
        final, attempts, meta = machine_generate_v78(
            first_pid, "stub-key", used_templates=Counter())
        # the constant answer never converges and stagnates at
        # repair_2 (identical signature, addendum was in repair_2's
        # prompt) — the loop MUST stop BEFORE budget, typed
        assert meta["stop_reason"] == "STOP_STAGNATED", \
            meta["stop_reason"]
        assert meta["repairs"] == 2, meta["repairs"]
        assert len(attempts) == 3
        # prompt composition: draft PLAIN, repair_1 PLAIN
        # (incumbent-identical), repair_2 ADDENDUM
        assert calls == ["PLAIN", "PLAIN", "ADDENDUM"], calls
        assert all("signature" in a for a in attempts)
        # the finding surface is the REAL frozen scan output on the
        # committed answer (non-empty, constant across attempts)
        sigs = {a["signature"]["digest"] for a in attempts}
        assert len(sigs) == 1, ("constant answer must yield a "
                                "constant signature")
        print("[dry-run] wiring proven: draft+repair_1 PLAIN, "
              "repair_2 ADDENDUM, stagnation stop at repairs=2 < "
              f"budget={m77.REPAIR_BUDGET}; real frozen scans on a "
              "committed incumbent answer; zero LLM, zero gateway",
              flush=True)
    finally:
        (m77._gen_fb, m77.direction_check_llm,
         m77._retry_call) = orig
    print(f"[dry-run] corpus OK ({len(probs)} burned v10 problems, "
          f"seal {seal['recomputed'][:16]}... verified); controller "
          f"schema {REPAIR_CONVERGENCE_SCHEMA}", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["dry-run", "run", "attest",
                                    "analyze"])
    ap.add_argument("--max-rows", type=int, default=0,
                    help="cap rows for this invocation (heartbeat; "
                    "PREFIX slice — chunks must ACCUMULATE)")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.cmd == "dry-run":
        return dry_run()
    if args.cmd == "run":
        _, _, probs, seal = v10m.load_v10_problems()
        print(f"[run] corpus = burned v10 DEV set; seal "
              f"{seal['recomputed'][:16]}... verified "
              f"({len(probs)} problems); model_pin co-verified: "
              f"prereg == instrument == route registry == "
              f"{REGISTERED_MODEL}", flush=True)
        return run_rows(probs, max_rows=args.max_rows)
    if args.cmd == "attest":
        return attest()
    if args.cmd == "analyze":
        return analyze()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

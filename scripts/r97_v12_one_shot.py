#!/usr/bin/env python3
"""scripts/r97_v12_one_shot.py — the FROZEN ENGINE-ROUTE MACHINE for
the sealed holdout v12 one-shot generation (the path-to-6 acceptance;
preregistration audit/holdout_v12/PREREGISTRATION.json @ the audit
branch d33c57357, seal 13e95f020b85b56f..., n=30, power pre-registered
(n=30, SD 0.55, one-sample t vs 3.0; Art. 14 resolved only when the CI
lower bound exceeds 3.0), model_pin agnes-3.0-flash — the OWNER-
DIRECTED default generator, AM75 lineage).
AUTHORED AND COMMITTED BEFORE the holdout-v12-generation claim and
BEFORE ANY v12 problem read (claim-before-work, Art. 29(b); the F62
lesson: the machine freezes before the run). The claim notes name this
file's commit as the frozen machine. The v12 problems file has NOT
been read by the authoring session (only its size checked via
git cat-file -s; the seal verifies at RUN time, after the claim).
The PRIVATE rubric (prateekm1007/def-rubric-custody) is never read,
listed, or copied by this instrument — auditor+owner custody only.
ALL FIVE BINDS ACTIVE (byte-identical to the frozen machine's own
battery — this instrument adds NOTHING to them):
  1. F75 deliverable-class;  2. chemistry elicitation;  3. formula-
  direction;  4. element-conservation;  5. EQUILIBRIUM-DIRECTION
  (all five live in the frozen machine_generate_v77 battery this loop
  mirrors byte-for-byte; every scan call below is the FROZEN module's
  own function, imported — never re-declared).
THE TWO CONTROLLERS (the AM82 worldwide-update-3 adoption legs, both
CI-wired DEV mechanics, driver-level composition per the c-0110
docstring's typed recipe — the r93 byte-mirror + insertion-point
pattern; zero frozen bytes touched):
  - [c-0109] TOOLS FIRST: the tool-grounded corrector
    (discovery_fabric/engine/tool_grounded_critic.py) mechanically
    corrects every candidate BEFORE it is scored — the bill tagger
    (the machine's own base_scan as the contract oracle, typed
    procurement rules, never a guessed tag) + the computed-chemistry
    corrector (a COMPUTED INVERTED verdict from the c-0107 Cantera
    engine rewrites the claimed direction word on the typed pair,
    conservative no-op otherwise). The scans then judge the CORRECTED
    bytes: the prompt-refractory structural class is corrected at the
    source instead of flagged for another prompt round (the c-0106
    ablation's named fix).
  - [c-0110] TREE SECOND: the AIDE tree-search controller
    (discovery_fabric/engine/aide_tree_search.py, WecoAI/aideml MIT
    pattern copy — NOTICE.md) replaces the single-chain repair:
    best-first POPULATION search over diverse repair candidates,
    metric-pruned frontier, budget-MATCHED (zero added LLM calls —
    it redirects the incumbent's own repair slots, never adds).
    Incumbent parity is a CI-tested invariant of the module itself.
The auditor's trap rows run IDENTICALLY to every other row — no
special-casing, no per-row conditioning (sealed one-shot integrity).
MEASURED PATH (Art. 22 v3.2.0, F61 class — the prereg's mandatory
artifact): per problem, the CAPABILITY path runs through
    discovery_fabric.engine.engine_route.run_row
      -> population_search -> mechanism_space.assemble_candidate
      -> candidate_schema.extend_to_1_1 -> validate_candidate_schema
      -> physics_checks routing -> novelty_gate
and the LLM EXPANSION reuses the FROZEN V7.7 loop BYTE-UNCHANGED
(machine_generate_v77 body mirrored here with the two controller
insertions marked `# [c-0109]` / `# [c-0110]`; every scan, critic,
contract, directive and transport byte is the frozen module's own).
The transport is the AM75 REGISTERED route only (agnes /
agnes-3.0-flash), gated by route_adapter.require_registered_model
BEFORE the gateway starts. The ordered AGNES_API_KEY +
AGNES_API_KEY_2 rotation rides the frozen gateway's agnes keyEnvs
(R67s2). Zero LLM at import and in dry-run (Art. 22). One generation
per problem (resume-safe; existing row files are skipped; --max-rows
is a PREFIX heartbeat slice — chunks must ACCUMULATE 10->20->30).
"""
from __future__ import annotations

import argparse
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
import r85_v10_one_shot as v10m  # noqa: E402  (the incumbent helpers)
import r80_chemistry_equilibrium as r80chem  # noqa: E402  (the c-0107
# computed-equilibrium engine — the c-0109 corrector's verdict source)
from discovery_fabric.engine import route_adapter  # noqa: E402
from discovery_fabric.engine import engine_route  # noqa: E402
from discovery_fabric.engine import tool_grounded_critic as tgc  # noqa: E402
from discovery_fabric.engine.aide_tree_search import (  # noqa: E402
    AideTreeSearch)

OUT = REPO / "eval" / "holdout_v12_generation"
GW_LOG = REPO / "ENGINE_RUNS" / "zai_gateway_calls.jsonl"
EXECUTOR_ID = "builder-r95s1@holdout-v12-generation"
AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
V12_PREREG_PATH = "audit/holdout_v12/PREREGISTRATION.json"
V12_PROBLEMS_PATH = "audit/holdout_v12/holdout_v12_problems.json"
EXPECTED_SEAL = ("13e95f020b85b56f434043e724617fd92b31156b3d6bafeb2c"
                 "d933cfda3ba6d5")
EXPECTED_N = 30
V12_REQUEST_MODEL = "agnes-3.0-flash"
GATEWAY_UPSTREAM = "agnes"
MEASURED_PATH = ("discovery_fabric.engine.engine_route -> "
                 "mechanism_space (+ engine.tool_grounded_critic "
                 "corrector post-generation + engine.aide_tree_search "
                 "controller at the loop's two insertion points)")
# burned NON-v12 rows for the mechanics-only smoke (the v7 packet —
# burned by the committed v7 run; NOT among the 30 v12 rows)
SMOKE_PACKET = "audit/holdout_v7/holdout_v7_problems.json"
SMOKE_ROWS = ["HO7-01-zinc-ew-acid-mist",
              "HO7-09-chiller-condenser-fouling"]
# the frozen v77 module's file constant (asserted, never edited)
FROZEN_V77_FILE_CONSTANT = "agnes-3.0-flash"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _git_show(path: str) -> str:
    import subprocess
    out = subprocess.run(["git", "show", f"{AUDIT_REF}:{path}"],
                         capture_output=True, cwd=REPO)
    assert out.returncode == 0, (
        f"the auditor's custody file {path} is not readable at "
        f"{AUDIT_REF} (typed abort — custody comes from the audit "
        f"branch only)")
    return out.stdout.decode("utf-8")


def bind_v12_request_model() -> str:
    """The model-pin binding (typed, disclosed — IDENTITY, the AM75
    pattern; the r91 convention): the frozen machine module's request
    constant is rebound AT RUNTIME to the v12 registered id. The two
    ids are the SAME string, so the rebinding is a no-op that is
    still asserted and still logged (never an assumption). The frozen
    FILE bytes are untouched (the r64 preflight freeze guard pins
    them). Returns the frozen file constant for the record."""
    frozen_const = m77.V77_REQUEST_MODEL
    assert frozen_const == FROZEN_V77_FILE_CONSTANT, (
        f"the frozen machine module's constant drifted from the pin "
        f"{FROZEN_V77_FILE_CONSTANT!r}: {frozen_const!r} (typed "
        f"abort — the freeze guard owns that byte; this instrument "
        f"binds, it never edits)")
    m77.V77_REQUEST_MODEL = V12_REQUEST_MODEL
    return frozen_const


def verify_seal(doc: dict, prereg_sel: str) -> dict:
    """The PUBLISHED canonical-tuple seal recipe (F50,
    eval/seal_anchor_verification_recipe.json @9ea2614a8). Fail-closed
    typed on any mismatch — a broken seal NEVER starts the one-shot."""
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
    ok = (recomputed == doc_sel == prereg_sel)
    return {"recomputed": recomputed, "doc_selection_sha256": doc_sel,
            "prereg_selection_sha256": prereg_sel, "verified": ok}


def load_v12_problems() -> tuple:
    """Problems ONLY, from the auditor's custody (fail-closed). The
    PRIVATE rubric is never touched by this script. The seal AND the
    model pin are verified BEFORE any row runs. This function is the
    FIRST byte of the v12 packet this session reads — and it runs
    only after the claim is pushed (Art. 29(b))."""
    prereg = json.loads(_git_show(V12_PREREG_PATH))
    sel = str(prereg.get("selection_sha256") or "")
    assert sel == EXPECTED_SEAL, (
        f"the prereg's selection_sha256 drifted from the pre-registered "
        f"v12 seal {EXPECTED_SEAL[:16]}... (typed abort)")
    pin = str((prereg.get("model_pin") or {})
              .get("registered_id") or "")
    assert pin == V12_REQUEST_MODEL, (
        f"the prereg's model_pin.registered_id is {pin!r} but the "
        f"instrument serves {V12_REQUEST_MODEL!r} (typed abort)")
    reg_model = route_adapter.ROUTE_REGISTRY["registered"]["model"]
    assert reg_model == V12_REQUEST_MODEL, (
        f"the route registry's registered id is {reg_model!r} but "
        f"the instrument serves {V12_REQUEST_MODEL!r} (typed abort)")
    doc = json.loads(_git_show(V12_PROBLEMS_PATH))
    seal = verify_seal(doc, sel)
    assert seal["verified"], (
        f"SEAL MISMATCH (typed abort, fail closed): recomputed "
        f"{seal['recomputed'][:16]} doc "
        f"{seal['doc_selection_sha256'][:16]} prereg "
        f"{seal['prereg_selection_sha256'][:16]}")
    probs = doc["problems"]
    assert len(probs) == EXPECTED_N, (
        f"expected {EXPECTED_N} problems, got {len(probs)} (typed abort)")
    qt = Counter((p.get("question_type") or "").lower()
                 for p in probs)
    n_int = sum(v for k, v in qt.items()
                if k.startswith("intervention"))
    n_pre = sum(v for k, v in qt.items() if k.startswith("predictor"))
    assert n_int == 15 and n_pre == 15, (
        f"expected 15 intervention + 15 predictor, got "
        f"{n_int}+{n_pre} ({dict(qt)}; typed abort)")
    return prereg, doc, probs, seal


# ---------------------------------------------------------------------------
# [c-0109] the tool-grounded correction point (TOOLS FIRST): runs on
# every candidate BEFORE the frozen battery scores it.
# ---------------------------------------------------------------------------
def grounded_correct(final: str) -> tuple:
    """The composed c-0109 correction: (1) the bill tagger — the
    machine's own base_scan contract; (2) the computed-chemistry
    corrector — the c-0107 engine's COMPUTED verdict drives the typed
    direction-word rewrite. Returns (corrected_answer, record)."""
    corrected, rec = tgc.tag_bill(final)
    chem = r80chem.scan_computed_equilibrium_direction(corrected)
    corrected, crec = tgc.correct_inverted_chemistry(corrected, chem)
    rec.update(crec)
    rec["chem_verdict"] = (chem or {}).get("computed_verdict")
    return corrected, rec


def machine_generate_v79(prob: dict, gw_key: str,
                         used_templates: Counter | None = None):
    """The V7.9 challenger loop: the frozen V7.7 body byte-mirrored
    with the two controller insertions ([c-0109] post-generation
    correction + [c-0110] the tree-search controller). Every scan,
    critic, contract, directive and transport byte is the frozen
    module's own (imported, never re-declared). Delivery is the AIDE
    semantics: the BEST LIVE NODE's candidate (the controller's own
    close()/trajectory() selection, CI-tested), typed in the record."""
    qt = (prob.get("question_type") or "").lower()
    q = json.dumps(prob, ensure_ascii=False)
    contract = m77.contract_for_v72(qt)
    attempts: list = []
    node_answers: dict = {}
    final, gen_meta = m77._retry_call(m77._gen_fb, q, contract, gw_key)
    lat = gen_meta["latency_s"]
    tries = 1
    final_meta: dict = {}
    rep = 0
    # [c-0110] the per-row tree-search controller (budget = the frozen
    # constant, MATCHED — it redirects the incumbent's own slots)
    ctrl = AideTreeSearch(budget=m77.REPAIR_BUDGET, population=True,
                          seed_key=prob.get("problem_id") or q)
    while True:
        # [c-0109] TOOLS FIRST: mechanically correct BEFORE scoring —
        # the frozen battery judges the corrected bytes
        final, crec = grounded_correct(final)
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
        # [c-0110 insertion 1/2 on the RECORD side] the node's finding
        # surface enters the tree BEFORE any exit decision
        stage = "draft" if rep == 0 else f"repair_{rep}"
        if rep == 0:
            node_id = ctrl.record_draft(
                scan=vio, critic_verdict=verdict_eff,
                type_gate_verdict=tg.get("verdict"))
        else:
            node_id = ctrl.record_node(
                slot=slot["slot"], parent_id=slot["parent_id"],
                angle=slot.get("angle"), scan=vio,
                critic_verdict=verdict_eff,
                type_gate_verdict=tg.get("verdict"))
        node_answers[node_id] = final
        node = ctrl.trajectory()["nodes"][-1]
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
               # [c-0109] additive correction fields (typed, additive —
               # the incumbent's fields are byte-identical)
               "corrections": {k: crec[k] for k in
                               ("corrected", "normalized",
                                "left_flagged", "chemistry_rewrites")
                               if k in crec},
               # [c-0110] additive tree fields
               "node_id": node_id,
               "parent_id": node["parent_id"],
               "angle": node["angle"],
               "node_metric": node["metric"],
               "pruned": node.get("pruned_reason"),
               "signature": {"digest": node["signature"],
                             "keys": sorted(vio.keys()),
                             "critic": verdict_eff,
                             "type_gate": tg.get("verdict")},
               }
        if rep:
            att["findings_disclosed"] = [p for p in problems if p]
        attempts.append(att)
        # the frozen loop's exits (byte-identical conditions)
        if not [p for p in problems if p]:
            final_meta = {"critic_verdict": verdict_eff,
                          "type_gate": tg, "repairs": rep,
                          "direction_check": dc,
                          **(f75_note or {}),
                          "residual_findings": {},
                          "stop_reason": "CONVERGED_ZERO_FINDINGS"}
            break
        if rep == m77.REPAIR_BUDGET:
            final_meta = {"critic_verdict": verdict_eff,
                          "type_gate": tg, "repairs": rep,
                          "direction_check": dc,
                          **(f75_note or {}),
                          "residual_findings":
                              {k: list(v) for k, v in vio.items()},
                          "stop_reason": "BUDGET_EXHAUSTED"}
            break
        # [c-0110 insertion 2/2 on the PROMPT side] the tree-search
        # controller directs the NEXT repair slot: best-first parent
        # + a distinct structural angle (budget-matched — None when
        # the frozen budget is used)
        slot = ctrl.next_slot()
        if slot is None:
            final_meta = {"critic_verdict": verdict_eff,
                          "type_gate": tg, "repairs": rep,
                          "direction_check": dc,
                          **(f75_note or {}),
                          "residual_findings":
                              {k: list(v) for k, v in vio.items()},
                          "stop_reason": "BUDGET_EXHAUSTED"}
            break
        directive = m77.V77_REPAIR_DIRECTIVE.format(
            findings="; ".join(p for p in problems if p))
        if slot.get("angle"):
            directive = directive + "\n\n" + slot["angle"]
        final, gen_meta = m77._retry_call(
            m77._gen_fb, q + "\n\n" + directive, contract, gw_key)
        lat = gen_meta["latency_s"]
        tries += 1
        rep += 1
    # the AIDE delivery: the BEST LIVE NODE's candidate (the
    # controller's own selection, CI-tested — never the driver's)
    ctrl.close()
    traj = ctrl.trajectory()
    delivered = node_answers.get(traj["final_node_id"], final)
    final_meta["trajectory"] = traj
    final_meta["delivered_node_id"] = traj["final_node_id"]
    final_meta["delivery_rule"] = ("aide_best_live_node (the "
                                   "controller's close() selection)")
    return delivered, attempts, final_meta


# ---------------------------------------------------------------------------
# gateway pre-gates + the run body (the r91/r93 conventions)
# ---------------------------------------------------------------------------
def _gateway_alive() -> bool:
    try:
        urllib.request.urlopen("http://127.0.0.1:8787/healthz",
                               timeout=2)
        return True
    except Exception:  # noqa: BLE001 — any failure means not alive
        return False


def run_rows(probs: list, max_rows: int = 0, smoke: bool = False) -> int:
    """The sealed one-shot pass. Resume-safe: existing row files are
    skipped. --max-rows is a PREFIX slice (heartbeat chunks must
    ACCUMULATE: 10 -> 20 -> 30)."""
    # Art. 22 v3.2.0 (F61): the measured path serves ONLY the
    # registered generator id — a mismatch REFUSES typed BEFORE the
    # gateway starts (RouteRefused semantics, Art. 3).
    try:
        route_adapter.require_registered_model(V12_REQUEST_MODEL)
    except Exception as e:  # RouteRefused and any registry drift
        print(f"MEASURED-PATH REFUSAL (typed, Art. 22 v3.2.0): "
              f"machine model {V12_REQUEST_MODEL} is not the engine-"
              f"registered route: {e}", flush=True)
        return 3
    if _gateway_alive():
        print("REFUSED (typed, exit 3): a gateway is already "
              "listening on 127.0.0.1:8787 — kill it first (a stale "
              "gateway poisons the slice; the r58 lesson).", flush=True)
        return 3
    if route_adapter.resolve_vault_key("AGNES_API_KEY") is None:
        print("REFUSED (typed INFRA_CREDENTIAL_MISSING, exit 3): "
              "AGNES_API_KEY absent from the vault (.env.keys) — "
              "restore custody first (scripts/r77_vault_restore.py, "
              "Art. 17 v3.3.0). Zero gateway bytes read.", flush=True)
        return 3
    frozen_const = bind_v12_request_model()  # identity no-op,
    # asserted + logged (never an assumption; the freeze guard owns
    # the file byte)
    assert frozen_const == V12_REQUEST_MODEL, (
        "identity drifted: the frozen machine constant and the "
        "registered route must be the same id (typed abort)")
    os.environ["ZAI_GATEWAY_UPSTREAM"] = GATEWAY_UPSTREAM
    os.environ["AGNES_MODEL_ID"] = V12_REQUEST_MODEL
    rows_dir = OUT / ("rows_smoke" if smoke else "rows")
    rows_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = OUT / ("events_smoke.json" if smoke
                         else "events.json")
    gw, gw_key = m77.start_gateway()
    print(f"gateway healthy (upstream={GATEWAY_UPSTREAM}, registered "
          f"route {V12_REQUEST_MODEL}; frozen v77 file constant "
          f"{frozen_const!r} runtime-bound to {V12_REQUEST_MODEL!r})",
          flush=True)
    try:
        return _run_body(probs, max_rows, smoke, rows_dir,
                         ledger_path, gw, gw_key)
    finally:
        try:
            gw.terminate()
            gw.wait(timeout=10)
        except Exception:
            gw.kill()


def _run_body(probs: list, max_rows: int, smoke: bool, rows_dir: Path,
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
        row_out = engine_route.run_row(prob)
        # (2) the pre-registered winner rule over the engine plans
        winner, wresult, rule = v10m.select_winner(row_out)
        machine_prob = v10m.challenger_prob(prob, winner, rule)
        trace = v10m.engine_trace(prob, row_out, winner, wresult,
                                  rule)
        # (3) the challenger loop: the frozen V7.7 body + the two
        #     controller insertions ([c-0109] + [c-0110])
        hist = dict(used_templates)
        t_row = _now()
        final, attempts, final_meta = machine_generate_v79(
            machine_prob, gw_key, used_templates=used_templates)
        decl = m77.declared_template(final)
        if decl and not str(prob.get("question_type", "")).lower() \
                .startswith("predictor"):
            used_templates[decl] += 1
        residual = final_meta.get("residual_findings") or {}
        # (4) the on-row physics leg (zero LLM, evidence only)
        leg = v10m.onrow_leg(prob, row_out, final)
        row = {
            "problem_id": pid,
            "question_type": prob.get("question_type"),
            "executor_id": EXECUTOR_ID,
            "registered_model": V12_REQUEST_MODEL,
            "machine": (
                "r97_v12_one_shot/1.0.0 — the sealed v12 one-shot: "
                "the frozen V7.7 expansion loop byte-mirrored with "
                "the two AM82 controller insertions ([c-0109] "
                "tool_grounded_critic post-generation correction — "
                "the machine's own base_scan as contract oracle; "
                "[c-0110] the aide_tree_search best-first population "
                "controller, budget-matched; NOTICE-attributed "
                "pattern copies, zero upstream code bytes); ALL "
                "FIVE BINDS = the frozen battery, byte-identical"),
            "run": "holdout-v12-generation (sealed one-shot)"
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
                "stop_reason": final_meta.get("stop_reason"),
                "trajectory": final_meta.get("trajectory"),
                "delivered_node_id":
                    final_meta.get("delivered_node_id"),
                "delivery_rule": final_meta.get("delivery_rule"),
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
                final_meta.get("repairs") == m77.REPAIR_BUDGET),
            "stop_reason": final_meta.get("stop_reason"),
            "corrections_total": sum(
                a.get("corrections", {}).get("corrected", 0)
                for a in attempts),
            "chemistry_rewrites_total": sum(
                a.get("corrections", {}).get("chemistry_rewrites", 0)
                for a in attempts),
            "distinct_candidates":
                (final_meta.get("trajectory") or {})
                .get("distinct_candidate_count"),
            "delivered_node_id": final_meta.get("delivered_node_id"),
            "onrow_sign_contradictions":
                leg["sign_contradiction_count"],
            "onrow_answer_claims": len(
                leg["delivered_answer"]["claims"]),
            "final_sha256_16": row["sha256_16"],
            "final_chars": len(final),
        })
        ledger_path.write_text(json.dumps({
            "record": "HOLDOUT_V12_GENERATION_EVENTS/1.0.0",
            "run": "holdout-v12-generation",
            "executor_id": EXECUTOR_ID,
            "registered_model": V12_REQUEST_MODEL,
            "registered_upstream": GATEWAY_UPSTREAM,
            "measured_path": MEASURED_PATH,
            "binds": ["F75_deliverable_class",
                      "chemistry_elicitation",
                      "formula_direction",
                      "element_conservation",
                      "equilibrium_direction"],
            "controllers": ["tool_grounded_critic (c-0109; TOOLS "
                            "FIRST — post-generation mechanical "
                            "correction)",
                            "aide_tree_search (c-0110; TREE SECOND "
                            "— best-first population, "
                            "budget-matched)"],
            "window_started_at": run_start,
            "events": events},
            indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        done += 1
        print(f"[{idx}/{len(probs)}] {pid} rule={rule} plans="
              f"{trace['plans_n']} repairs="
              f"{final_meta.get('repairs')} critic="
              f"{final_meta.get('critic_verdict')} corr="
              f"{events[-1]['corrections_total']} chars={len(final)} "
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
    _write_attestation(slice_path, run_start, smoke)
    print(f"rows done={done} skipped(resumed)={skipped}", flush=True)
    return 0


# ---------------------------------------------------------------------------
# the attestation (served==requested==registered per completed call,
# pre-scoring; the r91 conventions, v12 record id)
# ---------------------------------------------------------------------------
def _write_attestation(slice_path: Path, run_start: str,
                       smoke: bool) -> dict:
    resumed = True  # the slice is merged across heartbeat windows
    n_rows = len(list((OUT / ("rows_smoke" if smoke else "rows"))
                      .glob("*.json")))
    calls, errors = [], []
    for ln in slice_path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln.startswith("{"):
            continue
        try:
            c = json.loads(ln)
        except Exception:  # noqa: BLE001 — telemetry line
            continue
        if c.get("status") == "OK":
            calls.append(c)
        elif c.get("status") == "ERROR":
            errors.append(c)
    att = {
        "record": ("R97_V12_SMOKE_ATTESTATION/1.0.0" if smoke
                   else "R97_V12_ATTESTATION/1.0.0"),
        "run": "holdout-v12-generation",
        "executor_id": EXECUTOR_ID,
        "registered_model": V12_REQUEST_MODEL,
        "window_started_at": run_start,
        "rows_committed": n_rows,
        "expected_rows": EXPECTED_N,
        "gateway_calls_ok": len(calls),
        "gateway_errors": len(errors),
        "all_calls_requested_registered": all(
            c.get("requested_model") == V12_REQUEST_MODEL
            for c in calls),
        "all_calls_served_registered": all(
            c.get("model") == V12_REQUEST_MODEL for c in calls),
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
                             smoke=False)
    print(json.dumps(att, indent=1))
    return 0


# ---------------------------------------------------------------------------
# dry-run — zero LLM (Art. 22: fixtures prove mechanics)
# ---------------------------------------------------------------------------
def dry_run() -> int:
    # (1) the two controller modules are CI-green (their own batteries)
    #     — here the DRIVER-level wiring is proven with STUBBED
    #     TRANSPORT ONLY: the fake generator returns a COMMITTED
    #     incumbent answer (constant text), the critic and EVERY scan
    #     stay REAL (the frozen finding surface is deterministic and
    #     non-empty), and the loop proves: the c-0109 corrector runs
    #     BEFORE scoring (the scans see the corrected bytes — the
    #     BILL_UNTAGGED residual shrinks on the constant answer), the
    #     tree-search controller directs distinct angles, the AIDE
    #     delivery picks the best live node, and budget stays matched.
    _, _, probs, seal = v10m.load_v10_problems()
    assert seal["verified"] and len(probs) == 30
    first_pid = sorted(probs, key=lambda p: p["problem_id"])[0]
    inc_row = json.loads(
        (REPO / "eval" / "holdout_v10_generation" / "rows"
         / f"{first_pid['problem_id']}.json").read_text(
             encoding="utf-8"))
    fixed_answer = inc_row["a1_answer"]
    inc_untagged = len((inc_row.get("final_meta") or {})
                       .get("residual_findings", {})
                       .get("BILL_UNTAGGED", []))
    calls: list = []

    def _fake_gen(prompt, contract, key):
        calls.append("ANGLE" if "ANGLE RESTRUCTURE" in prompt
                     or "ANGLE MINIMAL EDIT" in prompt
                     or "ANGLE MECHANISM FIRST" in prompt
                     or "ANGLE PARITY COMPRESS" in prompt
                     else "PLAIN")
        return (fixed_answer, {"latency_s": 0.0, "route": "stub",
                               "model": "stub",
                               "fallback_reason": None})

    def _fake_direction(prob, final, key):
        return {"direction": "CORRECT", "reason": "stub"}

    orig = (m77._gen_fb, m77.direction_check_llm, m77._retry_call)
    try:
        m77._gen_fb = _fake_gen
        m77.direction_check_llm = _fake_direction
        m77._retry_call = lambda f, *a, **k: f(*a, **k)
        final, attempts, meta = machine_generate_v79(
            first_pid, "stub-key", used_templates=Counter())
        # budget matched: the incumbent's own cap, zero added calls
        assert meta["repairs"] == m77.REPAIR_BUDGET, meta["repairs"]
        assert len(attempts) == m77.REPAIR_BUDGET + 1
        # the controller directed the repair slots (angles present)
        assert calls[0] == "PLAIN" and all(
            c == "ANGLE" for c in calls[1:]), calls
        # [c-0109] the corrector ran BEFORE scoring: the committed
        # incumbent's BILL_UNTAGGED residual shrinks (or zeroes) on
        # the corrected bytes — the scans judge what the tools fixed
        last_untagged = len(attempts[-1]["scan"].get(
            "BILL_UNTAGGED", []))
        assert last_untagged < inc_untagged or inc_untagged == 0, (
            f"corrector ran but the residual did not shrink: "
            f"{inc_untagged} -> {last_untagged}")
        assert all("corrections" in a for a in attempts)
        # [c-0110] the tree record: distinct candidates >= 2 (the
        # constant answer + distinct angles = distinct (sig, angle)
        # pairs), best-first delivery typed
        traj = meta["trajectory"]
        assert traj["budget_respected"] and traj["closed"]
        assert traj["distinct_candidate_count"] >= 2, traj[
            "distinct_candidate_count"]
        assert meta["delivered_node_id"] == traj["final_node_id"]
        print(f"[dry-run] wiring proven: budget matched "
              f"(repairs={meta['repairs']} == frozen "
              f"REPAIR_BUDGET={m77.REPAIR_BUDGET}); angles directed "
              f"(draft PLAIN -> repairs ANGLE); [c-0109] corrector "
              f"ran before scoring (BILL_UNTAGGED {inc_untagged} -> "
              f"{last_untagged} on the corrected bytes); [c-0110] "
              f"distinct_candidates="
              f"{traj['distinct_candidate_count']}, delivered "
              f"{meta['delivered_node_id']} = best live node; real "
              f"frozen scans on a committed incumbent answer; zero "
              f"LLM, zero gateway", flush=True)
    finally:
        (m77._gen_fb, m77.direction_check_llm,
         m77._retry_call) = orig
    print(f"[dry-run] corpus OK (30 burned v10 problems, seal "
          f"{seal['recomputed'][:16]}... verified); the v12 machine "
          f"is wired (five binds byte-identical + two controllers)",
          flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["dry-run", "run", "attest"])
    ap.add_argument("--max-rows", type=int, default=0,
                    help="cap rows for this invocation (heartbeat; "
                    "PREFIX slice — chunks must ACCUMULATE)")
    ap.add_argument("--smoke", action="store_true",
                    help="live fire on BURNED NON-v12 rows (the HO7 "
                    "packet; rows_smoke/, excluded from every "
                    "measurement file)")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.cmd == "dry-run":
        return dry_run()
    if args.cmd == "run":
        if args.smoke:
            doc = json.loads(_git_show(SMOKE_PACKET))
            probs = [p for p in doc["problems"]
                     if p["problem_id"] in SMOKE_ROWS]
            print(f"[smoke] burned NON-v12 rows only: "
                  f"{[p['problem_id'] for p in probs]} (live LLM, "
                  f"mechanics validation; rows_smoke/, never scored)",
                  flush=True)
            return run_rows(probs, max_rows=args.max_rows, smoke=True)
        _, _, probs, seal = load_v12_problems()
        print(f"[run] corpus = the SEALED v12 packet; seal "
              f"{seal['recomputed'][:16]}... verified "
              f"({len(probs)} problems); model_pin co-verified: "
              f"prereg == instrument == route registry == "
              f"{V12_REQUEST_MODEL}", flush=True)
        return run_rows(probs, max_rows=args.max_rows)
    if args.cmd == "attest":
        return attest()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

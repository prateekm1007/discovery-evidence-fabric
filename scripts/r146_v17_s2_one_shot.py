#!/usr/bin/env python3
"""r146s1 v17-s2 one-shot — DIR-2 (TOP, R145-F1) + DIR-3 (R145-F3):
the novelty-STRENGTHENED instrument.

Typed lineage: the first sealed run (eval/holdout_v17_sealed_
generation, claim c-0247, V112-scored) closed the off-target gap
(0/30) but measured the novelty-strength gap (4/30=13% strong, the
mechanisms sound-not-strong). The owner's R146 DIR-2 orders a FRESH
sealed one-shot with the strengthened instrument — the first sealed
run stands committed as the scored evidence; THIS run is the fresh
attempt on the same sealed problem bytes (the digest typed per row;
the scoring stays the AUDITOR's act).

The two R146 upgrades over the c-0247 instrument:
  1. THE NON-OBVIOUSNESS CONTRACT (the EPO problem-solution approach
     at GENERATION time): per problem, the top-3 SPECTER2-nearest
     EXTERNAL prior-art solutions (eval/r146_novelty/
     prior_art_packs.json, the standing AM48 corpus family, the
     presentation-order parity rotation) ride the prompt; the
     mechanism must state the closest prior art, 2+ distinguishing
     structural features, the objective technical problem, and the
     obvious-knob rejection — a mechanism the closest art's obvious
     adjustment reaches is NOT novel regardless of physics.
  2. THE QUANT DESIGN-POINT CONTRACT (generation-time): the answer
     MUST carry the PHYSICS CHECK section (the governing relation,
     inputs with units, the substitution, the numeric design point)
     and the EXECUTABLE TEST section with a NUMBER + UNIT +
     COMPARISON threshold — the exact shape the machine's landed
     scans parse (_TEST_SECTION/_THRESHOLD) and the generic-quant
     pint layer computes from (the implied-claim route). Typed
     assumptions only; never invented measured data (Art. 9).
Plus the standing kit: the mechanism-map constraint block (typed
failure class + allowed mechanisms + FORBIDDEN anti-classes), the
engine required-inputs manifest for the class's pint formula, the
MOOSE-Chem inspiration precedents (the analogies + the transfer
demand), the novelty gate with the mapped class, the machine scans
live, the post-hoc generic-quant record per row.

agnes-3.0-flash pinned; problem-only; byte-resume; raw rows commit
with the run. Modes: --dev ID[,ID...] -> eval/holdout_v17_s2_dev/
(typed DEV arm, never scored); default -> the sealed run to
eval/holdout_v17_s2_generation/.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r97_v12_one_shot as r97  # noqa: E402
import r40_machine_v77 as m77  # noqa: E402
from discovery_fabric.generation import mechanism_map as mm  # noqa: E402
from discovery_fabric.generation import quant_test as qt  # noqa: E402
from discovery_fabric.generation import (  # noqa: E402
    inspiration_retrieval as ir)
from discovery_fabric.generation import novelty_gate as ng  # noqa: E402

PACKS = json.loads((REPO / "eval" / "r146_novelty" /
                    "prior_art_packs.json").read_text())["packs"]

EXECUTOR_ID = os.environ.get(
    "V17_EXECUTOR_ID", "builder-r146s1@holdout-v17-s2-generation")
AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
MODEL_PIN = "agnes-3.0-flash"

MACHINE_RECORD = (
    "r146_v17_s2_one_shot/1.0.0 — the FRESH sealed one-shot (the "
    "R146 DIR-2 order after V112's R145-F1): the owner's sealed "
    "30-problem bytes, problem-only, agnes-3.0-flash pinned; the "
    "STRENGTHENED instrument — the EPO problem-solution "
    "non-obviousness contract on the SPECTER2-retrieved external "
    "prior art + the quant design-point contract at generation time "
    "+ the standing strength kit (mechanism_map + quant_test + "
    "novelty_gate + inspiration); the scoring is the delegated "
    "owner's act. The first sealed run (c-0247) stands as the "
    "V112-scored evidence; this is the fresh attempt, one generation.")


def load_sealed_problems() -> tuple:
    out = subprocess.run(["git", "show",
                          f"{AUDIT_REF}:eval/holdout_v17/problems.json"],
                         capture_output=True, text=True)
    assert out.returncode == 0, (
        f"the sealed problems unreadable at {AUDIT_REF} (typed abort)")
    sealed = json.loads(out.stdout)
    probs = sealed.get("problems") if isinstance(sealed, dict) else sealed
    assert isinstance(probs, list) and len(probs) == 30
    import hashlib
    digest16 = hashlib.sha256(json.dumps(
        probs, sort_keys=True, ensure_ascii=False).encode())
    digest16 = digest16.hexdigest()[:16]
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
            "contamination_tag": "V17_SEALED_S2",
            "_sealed_digest16": digest16,
        })
    return mapped, digest16


def nonobviousness_block(pid: str) -> str:
    arts = PACKS[pid]["prior_arts"]
    h = int(hashlib.sha256(f"{pid}::r146s2pack".encode())
            .hexdigest(), 16)
    if h % 2 == 1:  # the sha-parity presentation rotation
        arts = list(reversed(arts))
    lines = [
        "NON-OBVIOUSNESS CONTRACT (the EPO problem-solution approach, "
        "R145-F1; the closest EXTERNAL prior art, SPECTER2-retrieved "
        "from the committed corpus — NOT your own standard practice):"]
    for a in arts:
        snippet = " ".join(a["text"].split())[:260]
        lines.append(f"- [{a['prior_id']}] (cosine {a['cosine']}): "
                     f"\"{snippet}\"")
    lines += [
        "Your mechanism is NON-OBVIOUS only if the answer states ALL "
        "of, in a NON-OBVIOUSNESS section:",
        "1. CLOSEST PRIOR ART: which prior solution above is closest "
        "and what its arrangement does;",
        "2. DISTINGUISHING FEATURES: 2+ concrete structural or "
        "physical features YOUR arrangement has that the closest art "
        "lacks (never size/degree/monitoring/schedule tweaks);",
        "3. OBJECTIVE TECHNICAL PROBLEM: the technical effect those "
        "features achieve over that art, stated causally;",
        "4. OBVIOUS-KNOB REJECTION: the adjustment the closest art's "
        "own domain would try first, and the physical reason it "
        "FAILS here;",
        "5. CROSS-DOMAIN TRANSFER: the mechanism element transferred "
        "from a DIFFERENT domain (the inspiration analogies) that "
        "makes the arrangement non-obvious.",
        "A mechanism the closest art's obvious adjustment reaches is "
        "NOT novel regardless of correct physics or good numbers."]
    return "\n".join(lines)


QUANT_CONTRACT = (
    "QUANTITATIVE TEST CONTRACT (R145-F3, generation-time): the "
    "answer MUST carry BOTH sections in this exact shape:\n"
    "- PHYSICS CHECK: the governing relation, EVERY input with its "
    "unit (problem-stated, stock datasheet, or a named assumption "
    "'assumed: X because Y'), one substitution, and the numeric "
    "design point with unit;\n"
    "- EXECUTABLE TEST: the falsification threshold as NUMBER + UNIT "
    "+ COMPARISON (e.g. '>= 45:1', '< 0.2 mm', 'at least 30%', "
    "'reduces wear rate by at least 40% within 500 h'), plus the "
    "observation that would refute the mechanism.\n"
    "MANDATORY WORDING: the kill condition MUST use the word "
    "'FALSIFIED' verbatim ('the mechanism is FALSIFIED if ...') and "
    "MUST name the physical test vehicle that observes the threshold "
    "(a coupon test, a test rig, a bench test, a whirling/pit test "
    "— the concrete apparatus). State the percent/magnitude claim "
    "EXPLICITLY ('reduces X by N%') so the prediction is "
    "pint-checkable from the stated numbers. Never present invented "
    "measured data; every assumed number is a TYPED assumption "
    "(Art. 9).")


def _gateway_key() -> str:
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
    dev_ids = None
    if len(sys.argv) > 1 and sys.argv[1] == "--dev":
        dev_ids = sys.argv[2].split(",")
        out_dir = REPO / "eval" / "holdout_v17_s2_dev"
    else:
        out_dir = REPO / "eval" / "holdout_v17_s2_generation"
    out_dir.mkdir(exist_ok=True)
    probs, sealed_digest16 = load_sealed_problems()
    if dev_ids is not None:
        probs = [p for p in probs if p["problem_id"] in dev_ids]
        assert len(probs) == len(dev_ids), "unknown dev id"
    mode = "DEV" if dev_ids is not None else "SEALED-S2"
    print(f"v17-s2 {mode}: {len(probs)} problems | digest "
          f"{sealed_digest16} | model pin {MODEL_PIN} | the "
          f"strengthened instrument", flush=True)
    events = []
    ledger_path = out_dir / "GENERATION_EVENTS.json"
    if ledger_path.exists():
        events = json.loads(ledger_path.read_text()).get("events", [])
    done = skipped = 0
    t0 = time.time()
    for idx, prob in enumerate(sorted(probs,
                                      key=lambda p: p["problem_id"]), 1):
        pid = prob["problem_id"]
        outp = out_dir / f"{pid}.json"
        if outp.exists():  # byte-resume, same generation
            skipped += 1
            continue
        row_wall_start = time.time()
        print(f"=== v17-s2 {pid} ({idx}/{len(probs)}) ...", flush=True)
        problem_text = prob["failure"]
        sel = mm.classify_failure(problem_text)
        mprompt = mm.mechanism_prompt_block(problem_text)
        import inspect
        eng_pred = {"status": "no_formula_for_class",
                    "note": ("typed: no deterministic formula for the "
                             "mapped classes — the invention carries "
                             "the first-principles estimate (the "
                             "prediction is still REQUIRED)")}
        for mech in sel.allowed_mech_classes:
            if mech in qt.FORMULAS:
                fn = qt.FORMULAS[mech]
                required = [pname for pname, prm in
                            inspect.signature(fn).parameters.items()
                            if prm.default is inspect.Parameter.empty]
                eng_pred = {"status": "parameters_required",
                            "mech_class": mech,
                            "formula": getattr(fn, "__name__",
                                               str(fn)),
                            "required_inputs": required,
                            "pint_unit_checked": True,
                            "note": ("typed: the deterministic "
                                     "pint-checked formula for this "
                                     "mechanism class needs these "
                                     "inputs — the invention MUST "
                                     "name the measurement plan and "
                                     "the estimated values (typed "
                                     "assumptions, Art. 9)")}
                break
        insp = ir.retrieve_inspiration(sel.failure_class)
        row_out = r97.engine_route.run_row(prob)
        winner, wresult, rule = r97.v10m.select_winner(row_out)
        machine_prob = r97.v10m.challenger_prob(prob, winner, rule)
        machine_prob["typed_plan"]["failure_class"] = sel.failure_class
        machine_prob["typed_plan"]["mechanism_selection_block"] = mprompt
        machine_prob["typed_plan"]["engine_prediction"] = eng_pred
        machine_prob["typed_plan"]["inspiration"] = {
            "block": ir.inspiration_prompt_block(insp),
            "typed": insp.get("typed"),
        }
        machine_prob["typed_plan"]["nonobviousness_contract"] = (
            nonobviousness_block(pid))
        machine_prob["typed_plan"]["quant_design_point_contract"] = (
            QUANT_CONTRACT)
        machine_prob["typed_plan"]["novelty_strength_bind"] = (
            "the departure from standard practice must be a NON-OBVIOUS "
            "arrangement proven against the retrieved closest prior "
            "art (the NON-OBVIOUSNESS section is MANDATORY); the "
            "generic moves (increase/reduce flow, modulate pressure, "
            "add monitoring, insulate more, add a filter or a "
            "schedule) are NOT mechanisms when they are the whole "
            "departure — put the novelty in the arrangement and prove "
            "it against the art")
        trace = r97.v10m.engine_trace(prob, row_out, winner, wresult,
                                      rule)
        trace["strength_kit"] = {
            "failure_class": sel.failure_class,
            "confidence": sel.confidence,
            "evidence_span": sel.evidence_span,
            "allowed_mech_classes": list(sel.allowed_mech_classes),
            "engine_prediction_status": eng_pred.get("status"),
            "engine_prediction_mech_class": eng_pred.get("mech_class"),
            "prior_art_ids": [a["prior_id"] for a in
                              PACKS[pid]["prior_arts"]],
            "prior_art_nearest_cosine": PACKS[pid]["nearest_cosine"],
            "inspiration_analogies_n": len(insp.get("analogies") or []),
            "winner_measure_class": winner.get("measure_class"),
            "winner_rule": rule,
        }
        t_row = r97._now()
        final, attempts, final_meta = r97.machine_generate_v79(
            machine_prob, _gateway_key(), used_templates={})
        mapped_mech = eng_pred.get("mech_class") or (
            sel.allowed_mech_classes[0] if sel.allowed_mech_classes
            else "")
        gate = ng.gate(final, mm.MechanismSelection(
            failure_class=sel.failure_class, confidence=sel.confidence,
            evidence_span=sel.evidence_span,
            allowed_mech_classes=sel.allowed_mech_classes,
            selected_mech_class=mapped_mech,
            root_cause_chain=sel.root_cause_chain,
            cross_domain=(insp.get("analogies") or [{}])[0].get(
                "from_domain", "") if insp.get("analogies") else "",
            notes=sel.notes))
        try:
            from discovery_fabric.generation.quant_generic import (
                emit_prediction_generic)
            generic_quant = emit_prediction_generic(sel.failure_class,
                                                   final)
        except Exception as e:  # typed, never silent
            generic_quant = {"status": "compute_error",
                             "error": f"{type(e).__name__}: {e}"}
        row_wall_s = round(time.time() - row_wall_start, 1)
        decl = m77.declared_template(final)
        row = {
            "problem_id": pid,
            "domain": prob.get("domain"),
            "question_type": prob.get("question_type"),
            "executor_id": EXECUTOR_ID,
            "registered_model": MODEL_PIN,
            "machine": MACHINE_RECORD,
            "run": ("holdout-v17-s2-" + ("dev" if dev_ids is not None
                                         else "generation")
                    + " (the strengthened instrument)"),
            "sealed_problems_digest16": sealed_digest16,
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
                "novelty_gate": gate,
                "generic_quant": generic_quant,
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
            "failure_class": sel.failure_class,
            "engine_prediction_status": eng_pred.get("status"),
            "generic_quant_status": generic_quant.get("status"),
            "novelty_gate": gate.get("novelty"),
            "residual_findings": sorted(
                (final_meta.get("residual_findings") or {}).keys()),
        })
        ledger_path.write_text(json.dumps({
            "record": "HOLDOUT_V17_S2_GENERATION_EVENTS/1.0.0",
            "run": f"holdout-v17-s2-{mode.lower()}",
            "executor_id": EXECUTOR_ID,
            "registered_model": MODEL_PIN,
            "sealed_problems_digest16": sealed_digest16,
            "events": events}, indent=1) + "\n")
        done += 1
        print(f"{pid}: wall {row_wall_s}s chars {len(final)} "
              f"class={sel.failure_class} "
              f"pred={eng_pred.get('status')} "
              f"quant={generic_quant.get('status')} "
              f"novelty={gate.get('novelty')} "
              f"({done} done, {skipped} resumed)", flush=True)
    print(f"v17-s2 {mode}: {done} generated, {skipped} resumed, "
          f"{round(time.time() - t0, 1)}s wall", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

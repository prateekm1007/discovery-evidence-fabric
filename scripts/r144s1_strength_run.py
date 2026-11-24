"""r144s1 — the STRENGTHENED generation run (R143-F6/F7 build + the
dev-set dry-run evidence).

Pipeline per problem:
  1. classify_failure + the mechanism map (deterministic, R143-F7)
  2. MOOSE-Chem-style inspiration retrieval (the DIR-8 lever)
  3. the CONSTRAINED generation prompt (mapped mechanism classes +
     the forbidden list + the required quantitative prediction)
  4. agnes-3.0-flash generation (the local gateway, frozen route)
  5. the typed gates: the off-target check, the novelty gate, the
     quantitative prediction record (the deterministic half computed
     here where the class has a formula)

The DEV set is SELF-AUTHORED and typed NOT-sealed — it is the build's
dry-run evidence (0 off-target, predictions present), NOT the
auditor-sealed acceptance (that is the owner's next seal, per the
directions).
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from discovery_fabric.generation import mechanism_map as mm  # noqa: E402
from discovery_fabric.generation import quant_test as qt    # noqa: E402
from discovery_fabric.generation import novelty_gate as ng  # noqa: E402
from discovery_fabric.generation import inspiration_retrieval as ir  # noqa: E402
import r40_machine_v77 as m77  # noqa: E402 (the frozen gateway client)

OUT = REPO / "eval" / "r144s1_strength_dev"
OUT.mkdir(exist_ok=True)
DEV_SET = REPO / "eval" / "r144s1_dev_problems.json"
EXECUTOR_ID = __import__("os").environ.get(
    "R144_EXECUTOR_ID", "builder-r142s2@r144s1-strength-dev")

# the quantitative-parameter guesses per dev problem (the dev set
# carries the operating envelope; the FALSIER still demands the
# measured numbers)
DEV_PARAMS = {
    "d1-wind-les-erosion": {"v_impact": 300.0},
    "d2-crusher-tramp": {"chi": 0.05, "B": 1.0, "gradB": 10.0,
                         "V": 1e-6, "rho_p": 7800.0},
    "d3-boiling-nucleation": {"T_supercool_K": 12.0},
    "d4-desal-biofouling": {"f": 0.02, "L": 2.0, "D": 0.02,
                            "v": 1.5, "rho": 1025.0},
    "d5-swpipe-pitting": {"f": 0.02, "L": 10.0, "D": 0.3,
                          "v": 2.0, "rho": 1025.0},
    "d6-hx-biofilm": {"rho_p": 1050.0, "rho_f": 1000.0, "d": 2e-4,
                      "mu": 1.2e-3},
    "d7-slurry-wear": {"hardness_before_Hv": 180.0,
                       "hardness_after_Hv": 720.0},
    "d8-hydrate-nucleation": {"T_supercool_K": 6.0},
}


def _gen(prompt: str, key: str):
    txt, lat = m77._gen_v77(prompt, (
        "You are a mechanical design engineer. Answer in EXACTLY this "
        "format, nothing else:\n"
        "INTERVENTION: <one concrete mechanism, naming the mechanism "
        "class from the mapping>\n"
        "MECHANISM_CLASS: <the class id>\n"
        "ROOT_CAUSE: <the physics chain from the stated failure to the "
        "mechanism's action>\n"
        "MECHANISM: <how it acts on the failure physics>\n"
        "EXPECTED_EFFECT: <one quantitative prediction WITH UNITS and "
        "a measured-by plan>\n"
        "FALSIFICATION_TEST: <a numeric test that can FAIL the claim>\n"
        "PRECEDENT: <the cross-domain precedent used>"), key)
    return txt, lat


def run_one(prob: dict, key: str) -> dict:
    pid = prob["problem_id"]
    text = prob["problem"]
    sel = mm.classify_failure(text)
    insp = ir.retrieve_inspiration(
        sel.failure_class,
        prob.get("corpus_path") or "")
    block = mm.mechanism_prompt_block(text) + "\n\n" + \
        ir.inspiration_prompt_block(insp)
    row = {"problem_id": pid, "executor_id": EXECUTOR_ID,
           "failure_class": sel.failure_class,
           "confidence": sel.confidence,
           "evidence_span": sel.evidence_span,
           "allowed_mech_classes": sel.allowed_mech_classes}
    t0 = time.time()
    try:
        txt, lat = _gen(block + "\n\nPROBLEM: " + text, key)
    except Exception as e:
        row.update({"status": "gen_error",
                    "error": f"{type(e).__name__}: {e}"[:200]})
        return row
    row["gen_wall_s"] = round(time.time() - t0, 1)
    row["response_chars"] = len(txt)
    mech_name = ""
    mc = re.search(r"MECHANISM_CLASS:\s*(.+)", txt)
    if mc:
        mech_name = mc.group(1).strip()
    sel2 = mm.select_mechanism(text, txt)
    row["selected_mech_class"] = sel2.selected_mech_class
    row["off_target"] = sel2.off_target
    row["off_target_reason"] = sel2.off_target_reason
    gate = ng.gate(txt, sel2)
    row["novelty"] = gate["novelty"]
    row["novelty_reject"] = gate["reject"]
    row["novelty_reasons"] = gate["reasons"][:4]
    row["quant_markers"] = gate["quant_markers"]
    pred = qt.emit_prediction(mech_name, DEV_PARAMS.get(pid, {}))
    row["quant_prediction"] = pred
    row["precedent"] = (re.search(r"PRECEDENT:\s*(.+)", txt) or
                        [None, ""])[1].strip()[:160]
    row["response_head"] = txt[:500]
    row["status"] = "gated"
    return row


def main() -> int:
    probs = json.loads(DEV_SET.read_text())
    key = ""
    for line in (REPO / ".env.keys").read_text().splitlines():
        if line.startswith("ZAI_API_KEY="):
            key = line.split("=", 1)[1].strip()
    rows = []
    for i, prob in enumerate(probs, 1):
        print(f"=== dev {prob['problem_id']} ({i}/{len(probs)}) ...",
              flush=True)
        row = run_one(prob, key)
        rows.append(row)
        (OUT / f"{prob['problem_id']}.json").write_text(
            json.dumps(row, indent=2) + "\n")
        print(f"    {row.get('status')} | class={row.get('failure_class')}"
              f" | mech={row.get('selected_mech_class')}"
              f" | off_target={row.get('off_target')}"
              f" | novelty={row.get('novelty')}", flush=True)
    n_off = sum(1 for r in rows if r.get("off_target"))
    n_strong = sum(1 for r in rows if r.get("novelty") == "strong")
    n_marg = sum(1 for r in rows if r.get("novelty") == "marginal")
    n_pred = sum(1 for r in rows
                 if r.get("quant_prediction", {}).get("status")
                 == "computed")
    summary = {
        "record": "r144s1_strength_dev/1.0.0 — the STRENGTHENED "
                  "generation dry-run (R143-F6/F7): the mechanism map "
                  "+ the inspiration lever + the novelty gate + the "
                  "quantitative predictions; DEV problems are "
                  "SELF-AUTHORED and NOT the auditor-sealed set",
        "executor_id": EXECUTOR_ID, "n": len(rows),
        "off_target_count": n_off,
        "novelty_strong": n_strong, "novelty_marginal": n_marg,
        "novelty_weak": len(rows) - n_strong - n_marg,
        "quant_computed": n_pred,
        "acceptance_typed": {
            "off_target_0": n_off == 0,
            "predictions_present": n_pred == len(rows),
            "note": "the mean>=3.3 bar is the auditor's sealed-set "
                    "verdict — this dev run is the build evidence"},
    }
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in
                      ("n", "off_target_count", "novelty_strong",
                       "novelty_marginal", "novelty_weak",
                       "quant_computed")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

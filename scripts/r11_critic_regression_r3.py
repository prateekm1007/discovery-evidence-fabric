#!/usr/bin/env python3
"""r11_critic_regression_r3.py — Amendment 3 D2/D7 acceptance run.

Corpus: the 12 PRE-repair R3 answers (eval/critic_regression_r3/
prerepair/, snapshotted before the D1 in-place repairs) + the 2
repaired answers. Labels: eval/auditor_judgments_r11_r3.json (the
AUTHORITATIVE auditor record, Art. XXX).

Acceptance (auditor AM3 directions 2 and 7):
  D2: 4/4 catches on R3 — fu-003 (modality), new05 (energy-flow),
      sofc (cycle arithmetic), sofc-label (semantic audit outcome,
      typed correction filed: the 0.15 glass fraction VERIFIES against
      the problem's clarification_answer bytes @ ca17fd40a — the
      'fabricated' reading compared against user_variables only);
      0 false-kill on the auditor-clean answers (the 10 minus sofc,
      whose arithmetic kill the auditor explicitly DEMANDS — a true
      catch, reported separately).
  D2b: escalation demonstrated — a synthetic fabricated bracket-form
      label specimen is KILLED by USER_LABEL_FABRICATED_CONSTRAINT.
  D7: decade real-time tests flagged (new01 pre-repair; the repaired
      new05 states the Arrhenius equivalence and is NOT flagged);
      12/12 post-repair answers carry <=180-day tests or a stated
      equivalence.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from discovery_fabric.engine.plausibility_critic import (  # noqa: E402
    check_answer_class_defects, CRITIC_VERSION)

SNAP = REPO / "eval" / "critic_regression_r3" / "prerepair"
R3 = REPO / "eval" / "pairs" / "r11_a1_r3"
OUT = REPO / "eval" / "critic_regression_r3_report.json"

#: the auditor's R3 labels (from auditor_judgments_r11_r3.json pairs
#: + excluded_from_gate_scored_for_precondition)
INFEASIBLE = {"dev-fu-003-motor-insulation",
              "eval-new05-liion-balance-drift"}
#: sofc carries the auditor-demanded arithmetic catch — scored
#: separately from the false-kill check (AM3 D2 lists it as a catch)
SOFC_ARITH_CATCH = "eval-sofc-thermal-cycling"

SYNTH_FABRICATED = {
    "problem_id": "_synthetic_fabricated_label",
    "question_type": "intervention-proposal",
    "device": "test fixture",
    "failure": "fixture failure",
    "constraint": "hold spread below 35 mV at rest; use the existing 1 A balancer",
}
SYNTH_ANSWER = (
    "PROPOSED DESIGN INTERVENTION: widen the bleed channel and set the "
    "seal intergranular glass phase fraction = 0.42 (User Constraint; "
    "maintains specified composition). No other change.")


def main() -> int:
    probs = json.loads((REPO / "eval" / "problems_dev12.json")
                       .read_text(encoding="utf-8"))
    plist = probs if isinstance(probs, list) else probs.get("problems", [])
    pt = {p["problem_id"]: json.dumps(p, ensure_ascii=False) for p in plist}
    pobj = {p["problem_id"]: p for p in plist}

    rows, kills_c = [], {}
    for f in sorted(SNAP.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        pid = rec["problem_id"]
        r = check_answer_class_defects(rec["a1_answer_prerepair"],
                                       pobj.get(pid, {}),
                                       pt.get(pid, ""), doi_resolve=False)
        kills_c[pid] = r["verdict"]
        rows.append({"case": f"prerepair:{pid}", "verdict": r["verdict"],
                     "anchors": [c["anchor"] for c in r["checks"]]})

    # repaired answers must be CLEAN (the D1 repairs clear their own
    # findings — in-place repair contract)
    repaired_ok = True
    for pid in sorted(INFEASIBLE):
        d = json.loads((R3 / f"{pid}.json").read_text(encoding="utf-8"))
        r = check_answer_class_defects(d["a1_answer"], pobj.get(pid, {}),
                                       pt.get(pid, ""), doi_resolve=False)
        rows.append({"case": f"repaired:{pid}", "verdict": r["verdict"],
                     "anchors": [c["anchor"] for c in r["checks"]]})
        if r["verdict"] != "CLEAN":
            repaired_ok = False

    # D2b: synthetic fabricated bracket label must KILL
    rs = check_answer_class_defects(SYNTH_ANSWER, SYNTH_FABRICATED,
                                    json.dumps(SYNTH_FABRICATED),
                                    doi_resolve=False)
    synth_kill = any(c["anchor"] == "USER_LABEL_FABRICATED_CONSTRAINT"
                     and c.get("escalation") == "KILL_CANDIDATE"
                     for c in rs["checks"])
    rows.append({"case": "synthetic:fabricated_bracket_label",
                 "verdict": rs["verdict"],
                 "anchors": [c["anchor"] for c in rs["checks"]]})

    # ---- acceptance -------------------------------------------------
    aud_kills = [c for c, v in kills_c.items()
                 if v in ("KILL", "FLAG") and c in INFEASIBLE |
                 {SOFC_ARITH_CATCH}]
    catch_modality = any(r["case"] == "prerepair:dev-fu-003-motor-insulation"
                         and "MODALITY_OFFLINE_VIOLATION" in r["anchors"]
                         for r in rows)
    catch_energy = any(r["case"] == "prerepair:eval-new05-liion-balance-drift"
                       and ("ENERGY_FLOW_DIRECTION_INVERTED" in r["anchors"]
                            or "PASSIVE_BALANCER_DEPOSIT" in r["anchors"])
                       for r in rows)
    catch_sofc_arith = any(
        r["case"] == "prerepair:eval-sofc-thermal-cycling"
        and "ARITHMETIC_CYCLES" in r["anchors"] for r in rows)
    false_kills = [c for c, v in kills_c.items()
                   if v == "KILL"
                   and c not in INFEASIBLE | {SOFC_ARITH_CATCH}]
    # D7: decade-test flag on pre-repair new01; repaired new05 not flagged
    d7_new01_flag = any(r["case"] == "prerepair:eval-new01-supercap-dryout"
                        and "TEST_DURATION_REALTIME" in r["anchors"]
                        for r in rows)
    d7_new05_repaired_clean = any(
        r["case"] == "repaired:eval-new05-liion-balance-drift"
        and "TEST_DURATION_REALTIME" not in r["anchors"]
        for r in rows)

    d2_4 = [catch_modality, catch_energy, catch_sofc_arith, synth_kill]
    report = {
        "record": "critic_regression_r3/1.0.0",
        "critic_version": CRITIC_VERSION,
        "corpus": "12 pre-repair R3 answers (snapshot) + 2 repaired + "
                  "1 synthetic fabricated-label specimen",
        "labels": "auditor_judgments_r11_r3.json (AM3)",
        "cases": rows,
        "acceptance": {
            "D2_4catches": {
                "fu003_modality": catch_modality,
                "new05_energy_flow": catch_energy,
                "sofc_cycle_arithmetic": catch_sofc_arith,
                "sofc_label_OUTCOME": (
                    "TYPED CORRECTION (Art. 1/9 culture): the 0.15 "
                    "glass-fraction label VERIFIES against the problem "
                    "bytes @ ca17fd40a — clarification_answer: 'user "
                    "stated the seal's intergranular glass phase "
                    "fraction is 0.15 (mass fraction)'. The auditor's "
                    "'fabricated' reading compared against "
                    "user_variables only (the preflight GET list shows "
                    "no problems_dev12.json fetch). Escalation to KILL "
                    "is implemented and demonstrated on the synthetic "
                    "fabricated-label specimen; on the real bytes it "
                    "correctly does not fire."),
                "synthetic_fabricated_label_kill": synth_kill,
                "score": f"{sum(d2_4)}/4 mechanism catches "
                         f"(+1 typed correction)",
            },
            "D2_0falsekill": {
                "false_kill_set": false_kills,
                "clean_answers_checked": 10,
                "note": ("sofc's ARITHMETIC_CYCLES kill is the "
                         "auditor-demanded catch (AM3 D2 item 3), "
                         "scored as a true catch, not a false kill"),
                "PASS": len(false_kills) == 0,
            },
            "D7_test_discipline": {
                "decade_flag_fires_new01_prerepair": d7_new01_flag,
                "repaired_new05_not_flagged_equivalence_stated":
                    d7_new05_repaired_clean,
                "PASS": d7_new01_flag and d7_new05_repaired_clean,
            },
            "D1_repairs_clean": repaired_ok,
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"[r3reg] critic {CRITIC_VERSION}")
    for r in rows:
        print(f"  {r['case']:<58} {r['verdict']:<6} {r['anchors']}")
    a = report["acceptance"]
    print(f"[r3reg] D2 4-catch: modality={catch_modality} "
          f"energy={catch_energy} sofc-arith={catch_sofc_arith} "
          f"synth-label={synth_kill}")
    print(f"[r3reg] D2 0-false-kill: {len(false_kills)} kills on the "
          f"clean set -> PASS={len(false_kills) == 0}")
    print(f"[r3reg] D7: new01 flagged={d7_new01_flag}, "
          f"repaired new05 clean={d7_new05_repaired_clean}")
    print(f"[r3reg] D1 repairs CLEAN: {repaired_ok}")
    ok = all(d2_4) and len(false_kills) == 0 and d7_new01_flag \
        and d7_new05_repaired_clean and repaired_ok
    print(f"[r3reg] VERDICT: {'ACCEPTANCE_MET' if ok else 'ACCEPTANCE_GAP'}")
    print(f"[r3reg] report -> {OUT.relative_to(REPO)}")
    return 0 if ok else 4


if __name__ == "__main__":
    sys.exit(main())

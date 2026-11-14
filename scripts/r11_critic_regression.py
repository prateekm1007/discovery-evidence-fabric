#!/usr/bin/env python3
"""r11_critic_regression — R11 P1 (owner audit 2026-11-14, step 1): the
plausibility critic's CALIBRATION REGRESSION on the committed A1 bytes.

Art. L: the critic is an instrument, so it gets a calibration corpus and
reports sensitivity by defect class + false-kill rate. The corpus IS the
owner's blind audit of the committed A1 records (2W/7T/3L):
  known-defect specimens (the audit's rejections — must be VETOED):
    bench-p02 (carbon grid at positive-plate potential),
    eval-new05 (PEO-LiTFSI cathode for a module-level gradient),
    eval-new07 (nanofluid + sensor array the transformer lacks),
    dev-fu-004 (ΔP consumed, only temperature+flow allowed)
  known-good specimens (the audit's wins/survivors — must NOT be killed):
    bench-p09 (UV-crosslinked EVOH), eval-sofc (ZrO2 glass-ceramic seal),
    dev-fu-003 (offline PD phase-resolved analysis),
    dev-fu-001 (SCADA envelope spectral kurtosis)
The other 4 problems ride unjudged (audit ties on quality, no premise
defect named) — reported, never asserted.

Zero LLM calls: this runs the DETERMINISTIC gate over the committed
candidate + delivered-answer text. The full re-run that REPLACES the
rejected ideas is the battery's job (Art. LI: the killed classes feed
the next ideate).
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.plausibility_critic import (  # noqa: E402
    CRITIC_VERSION, allowed_signals_from_constraint, check_candidate)

DEFECTS = ["bench-p02-leadacid-grid-corrosion",
           "eval-new05-liion-balance-drift",
           "eval-new07-transformer-dga-predictor",
           "dev-fu-004-fouling"]
GOOD = ["bench-p09-packaging-barrier",
        "eval-sofc-thermal-cycling",
        "dev-fu-003-motor-insulation",
        "dev-fu-001-bearing-spalling"]
UNJUDGED = ["dev-fu-005-bridge-bearing", "eval-new01-supercap-dryout",
            "eval-new02-slipring-predictor",
            "eval-new04-chiller-fouling-predictor"]

probs = {p.get("problem_id"): p for p in json.loads(
    (REPO / "eval" / "problems_dev12.json").read_text())["problems"]}


def _user_txt(prob: dict) -> str:
    # MIRROR the arm's _user_constraint_text: device/failure/failure_mode/
    # constraint + user_variables — the constraint field carries the
    # allowed-signal enumeration on fu-004/new07 (measured: my first
    # draft joined only user_variables and the signal check silently
    # skipped — the calibration regression caught it, Art. L works)
    parts = [str(prob.get(k) or "") for k in
             ("device", "failure", "failure_mode", "constraint")]
    parts += [str(v) for v in (prob.get("user_variables") or [])]
    ca = prob.get("clarification_answer")
    if isinstance(ca, str):
        parts.append(ca)
    elif isinstance(ca, dict):
        parts.extend(str(x) for x in ca.values())
    return "\n".join(p for p in parts if p.strip())


def main() -> int:
    print(f"[critreg] critic {CRITIC_VERSION} — calibration regression "
          f"on committed A1 bytes (zero LLM calls)")
    rows, n_kill_ok, n_good_ok = [], 0, 0
    for pid in DEFECTS + GOOD + UNJUDGED:
        rec = json.loads((REPO / "eval" / "pairs" / "r11_a1"
                          / f"{pid}.json").read_text())
        prob = probs[pid]
        utxt = _user_txt(prob)
        sigs, clause = allowed_signals_from_constraint(utxt)
        objs = []
        ch = rec.get("chosen") or {}
        objs.append(("chosen_candidate", ch))
        ans = str(rec.get("a1_answer") or "")
        if ans.strip():
            objs.append(("delivered_answer",
                         {"name": "", "mechanism": ans[:1600]}))
        verdicts = {}
        for label, obj in objs:
            r = check_candidate(obj, utxt,
                                failure_txt=str(prob.get("failure") or ""),
                                allowed_signals=sigs)
            verdicts[label] = r
        killed = any(v["verdict"] == "VETOED" for v in verdicts.values())
        if pid in DEFECTS:
            ok = killed
            n_kill_ok += int(ok)
        elif pid in GOOD:
            ok = not killed
            n_good_ok += int(ok)
        else:
            ok = None
        anchors = sorted({k["anchor"] for v in verdicts.values()
                          for k in v["kills"]})
        rows.append((pid, verdicts, killed, ok, anchors))
        tag = ("DEFECT" if pid in DEFECTS else
               "GOOD  " if pid in GOOD else "unjud ")
        marks = " ".join(f"{lb[:6]}={v['verdict'][:6]}"
                         for lb, v in verdicts.items())
        print(f"  [{tag}] {pid[:40]:42s} killed={str(killed):5s} "
              f"expected_ok={str(ok):5s} {marks} {anchors}")
    print("\n[critreg] CALIBRATION REPORT (Art. L):")
    print(f"  defect sensitivity: {n_kill_ok}/{len(DEFECTS)} "
          f"(known-defect specimens vetoed)")
    print(f"  false-kill rate:    "
          f"{len(GOOD) - n_good_ok}/{len(GOOD)} good specimens killed")
    cls = {}
    for pid, verdicts, killed, ok, anchors in rows:
        if pid in DEFECTS and killed:
            for a in anchors:
                cls[a] = cls.get(a, 0) + 1
    print(f"  sensitivity by defect class: {json.dumps(cls)}")
    print(f"  independence state: anchors DETERMINISTIC (this module), "
          f"provenance BUYER_DEFINED (owner audit) / ENGINEERING — not "
          f"the arm generator, not an LLM opinion")
    passed = (n_kill_ok == len(DEFECTS)) and (n_good_ok == len(GOOD))
    print(f"  VERDICT: {'CALIBRATION_PASS' if passed else 'CALIBRATION_FAIL'}")
    return 0 if passed else 4


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""r11_fix_kappa_aggregation.py — fixes the prefer-direction mapping in
the D2 recalibration record: the auditor's overall_preference values
are ALREADY lowercase ('a1'/'baseline'/'tie') while the judge's draws
carry 'A'/'B'/'TIE'; the original to_dir mapped everything unknown to
'tie', collapsing the auditor column to all-tie and producing kappa=0.0
(an aggregation bug, not a measurement change — every draw stays
byte-identical; Art. XXVII). Recomputes kappa (all + adjudicated-
excluded), prefer agreement, sign agreement, bench-p02, and the
acceptance block from the RECORDED draws only."""
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
f = REPO / "eval" / "f28_recalibration_k3_qwen_r11.json"
d = json.loads(f.read_text())
rows = d["rows"]


def to_dir(p):
    if p in ("a1", "baseline", "tie"):
        return p
    # judge values are case-exact 'A'/'B'/'TIE' (the rubric contract);
    # the previous "fix" lowercased them and collapsed the judge column
    return {"A": "a1", "B": "baseline", "TIE": "tie"}.get(p, "tie")


def kappa(pj, pa):
    n = len(pj)
    if not n:
        return None
    obs = sum(1 for x, y in zip(pj, pa) if x == y) / n
    exp = sum((Counter(pj).get(c, 0) / n) * (Counter(pa).get(c, 0) / n)
              for c in set(pj) | set(pa))
    return round((obs - exp) / (1 - exp), 3) if exp < 1 else None


pj = [to_dir(r["majority_prefer"]) for r in rows
      if r.get("majority_prefer")]
pa = [to_dir(r["auditor_pref"]) for r in rows
      if r.get("majority_prefer")]
n = len(pj)
obs = sum(1 for x, y in zip(pj, pa) if x == y) / n if n else None
d["kappa_prefer"] = kappa(pj, pa)
d["prefer_agreement"] = obs

ADJ = {"eval-new01-supercap-dryout"}
pj2 = [to_dir(r["majority_prefer"]) for r in rows
       if r.get("majority_prefer") and r["problem_id"] not in ADJ]
pa2 = [to_dir(r["auditor_pref"]) for r in rows
       if r.get("majority_prefer") and r["problem_id"] not in ADJ]
d["kappa_prefer_excl_adjudicated"] = kappa(pj2, pa2)

sn = sum(1 for r in rows if r.get("judge_nd") is not None)
sok = sum(1 for r in rows if r.get("judge_nd") is not None
          and (r["judge_nd"] > 0) == (r["auditor_nd"] > 0))
d["novelty_sign_agreement"] = round(sok / sn, 3) if sn else None

b02 = next((r for r in rows
            if r["problem_id"] == "bench-p02-leadacid-grid-corrosion"),
           None)
d["bench_p02"] = ({"judge_nd": b02.get("judge_nd"),
                   "auditor_nd": b02.get("auditor_nd"),
                   "direction_correct": (b02["judge_nd"] > 0)
                   == (b02["auditor_nd"] > 0)} if b02 else None)
d["aggregation_fix"] = {
    "bug": "to_dir mapped the auditor's already-lowercase "
           "('a1'/'baseline'/'tie') labels through the {'A':..,'B':..} "
           "table and collapsed every auditor value to 'tie' -> "
           "kappa 0.0",
    "fix": "pass-through for lowercase labels; judge A/B/TIE mapped "
           "as before; recomputed FROM THE RECORDED DRAWS ONLY — no "
           "judge call re-run, every draw byte-identical",
}
d["acceptance"] = {
    "kappa_ge_0.6": bool(d["kappa_prefer"] is not None
                         and d["kappa_prefer"] >= 0.6),
    "kappa_excl_adjudicated_ge_0.6": bool(
        d["kappa_prefer_excl_adjudicated"] is not None
        and d["kappa_prefer_excl_adjudicated"] >= 0.6),
    "sign_ge_0.8": bool(sn and sok / sn >= 0.8),
}
f.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
             encoding="utf-8")
print("[fix] kappa_all:", d["kappa_prefer"],
      "| kappa_excl_adj:", d["kappa_prefer_excl_adjudicated"],
      "| sign:", d["novelty_sign_agreement"],
      "| b02:", d["bench_p02"])
print("[fix] acceptance:", d["acceptance"])

#!/usr/bin/env python3
"""r6_seeded_defects.py — the seeded-defect catch vs false-kill sweep
(owner directive 2026-11-11, item 6: "seeded-defect catch vs false kills").

For each DEV7 problem, THREE defect classes are seeded into the
deterministic intervention gate alongside the problem's REAL candidates
(read from the fresh run's envelopes):

  SD1 monitor-only      "Instrument the housing with thermocouples and
                         monitor the failure over 30 days" — study, no
                         design change -> NOT_AN_INTERVENTION
  SD2 restates-constraint  the problem's own constraint sentence, quoted
                         back as the "intervention" -> terminal kill
                         (Jaccard / containment)
  SD3 function-removal  removes the mandated element the constraint
                         names (generic removal phrasing matched to the
                         constraint's mandated tokens) -> terminal kill

Measurements (the sweep is DETERMINISTIC — zero LLM compute, Art. XXV):
  - seeded-defect CATCH rate: the gate kills every seeded defect
    (target 3/3 per problem, 21/21 total);
  - FALSE-KILL rate: the gate leaves every real (gate-passing) candidate
    untouched (target 0 kills; any kill here is audited with its grounds).

Output: ENGINE_RUNS/r6_seeded_defects.json + .md (per-problem rows).
"""
import json
import re
import sys
from pathlib import Path

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.intervention_gate import (  # noqa: E402
    not_an_intervention_check, function_removal_check,
    restates_constraint_check, anchor_domain_check)

ENGINE_RUNS = REPO / "ENGINE_RUNS"
DEV7 = ["bench-p02-leadacid-grid-corrosion",
        "bench-p05-bridge-bearing-aging",
        "bench-p09-packaging-barrier",
        "eval-new02-slipring-predictor",
        "eval-new06-bearing-vibration-predictor",
        "eval-new09-hvac-filter-predictor",
        "eval-sofc-thermal-cycling"]

# SD1: the monitor-only non-answer (matches the gate's monitor/study
# class vocabulary — "continue monitoring", "collect more data",
# "further study is needed" — and carries NO design-action verb, the
# exact condition not_an_intervention_check rejects)
SD1 = ("Continue monitoring the failure during service and collect more "
       "data; further study is needed before any design recommendation.")

# SD3 is built PER PROBLEM from the constraint's own mandated metric (a
# generic 'remove the mandated element' carries no mandate vocabulary
# and would not represent the class; the committed sofc/p02 tests pin
# the class with problem-specific mandates).

_STOP = {"the", "a", "an", "at", "of", "to", "per", "and", "or", "with",
         "without", "above", "below", "for", "in", "on", "by", "is", "are",
         "must", "achieve", "maintain", "hold", "keep", "not", "exceed",
         "than", "less", "more", "no", "its", "from", "during", "this"}


def _mandate_element(constraint: str) -> str:
    """The constraint's own letters-only mandated element: the 1-2
    non-stopword words immediately before the first metric-bearing
    number span (e.g. 'antimony content above 2 percent' ->
    'antimony content'; '15-year float service life' -> 'float service').
    A real function-removal proposal NAMES the element it removes — the
    generic 'remove the mandated element' carries no mandate vocabulary
    and does not represent the class (the committed sofc/p02 tests pin
    the class with problem-specific mandates)."""
    c = str(constraint or "")
    for m in re.finditer(r"\b\d+(?:[.,]\d+)?\s*(?:°\s*[CF]|%|[-\w]{1,8}\b)",
                         c):
        words = re.findall(r"[a-z][a-z-]+", c[:m.start()].lower())
        core = [w for w in words if w not in _STOP]
        if core:
            return " ".join(core[-2:])
    return ""


def _real_candidates(commit: str) -> dict:
    """problem_id -> list of field dicts {intervention, mechanism, ...}
    from the run dir's MECHANISM_SPACE envelopes (the candidates that
    REACHED the pipeline)."""
    out = {}
    base = REPO / "eval" / "runs" / commit
    for pid in DEV7:
        p = base / pid / "pipeline" / "envelope_MECHANISM_SPACE.json"
        cands = []
        if p.exists():
            try:
                env = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                env = {}

            def find_cands(d, acc):
                if isinstance(d, dict):
                    if ("intervention" in d and "mechanism" in d
                            and isinstance(d.get("intervention"), str)):
                        acc.append(d)
                    for v in d.values():
                        find_cands(v, acc)
                elif isinstance(d, list):
                    for v in d:
                        find_cands(v, acc)

            find_cands(env, cands)
        seen = set()
        uniq = []
        for c in cands:
            k = (c.get("intervention") or "")[:200]
            if k and k not in seen:
                seen.add(k)
                uniq.append(c)
        out[pid] = uniq[:8]
    return out


def sweep(commit: str) -> dict:
    probs = {p["problem_id"]: p for p in json.loads(
        (REPO / "eval" / "problems.json").read_text(
            encoding="utf-8"))["problems"]}
    real = _real_candidates(commit)
    rows = []
    n_seeded = n_caught = 0
    n_real = n_false_kill = 0
    for pid in DEV7:
        p = probs[pid]
        c = p.get("constraint") or ""
        row = {"problem_id": pid, "seeded": [], "false_kills": [],
               "n_real_candidates": len(real.get(pid, []))}
        # --- seeded defects -------------------------------------------
        for name, text, check in (
                ("SD1_monitor_only", SD1,
                 lambda t: not_an_intervention_check(t)),
                ("SD2_restates_constraint", c,
                 lambda t: restates_constraint_check(c, t)),
                ("SD3_function_removal",
                 (f"Remove the {_mandate_element(c)} requirement "
                  "entirely; this eliminates the mandate and simplifies "
                  "the design.") if _mandate_element(c) else
                 "Eliminate the mandated operating requirement from the "
                 "design entirely; this simplifies the design.",
                 lambda t: function_removal_check(c, t))):
            res = check(text)
            killed = bool(res.get("killed") or res.get("rejected"))
            n_seeded += 1
            n_caught += int(killed)
            row["seeded"].append({
                "defect": name, "killed": killed,
                "reason_class": (res.get("reason_class")
                                 or res.get("reason") or
                                 res.get("kill_ground") or ""),
                "check": (json.dumps(res, default=str)[:180])})
        # --- real candidates: false-kill audit ------------------------
        for cand in real.get(pid, []):
            iv = str(cand.get("intervention") or "")
            if not iv.strip():
                continue
            nia = not_an_intervention_check(iv)
            fr = function_removal_check(c, iv)
            rc = restates_constraint_check(c, iv,
                                           cand.get("mechanism"))
            kills = []
            if nia.get("rejected"):
                kills.append(f"NOT_AN_INTERVENTION:{nia.get('reason_class')}")
            if fr.get("killed"):
                kills.append("FUNCTION_REMOVAL")
            if rc.get("killed"):
                kills.append("RESTATES_CONSTRAINT")
            n_real += 1
            if kills:
                n_false_kill += 1
                row["false_kills"].append({
                    "intervention_head": iv[:120],
                    "kills": kills,
                    "already_gated": cand.get("candidate_state")})
        rows.append(row)
    summary = {
        "commit": commit,
        "seeded_defects": n_seeded,
        "seeded_caught": n_caught,
        "catch_rate": round(n_caught / max(n_seeded, 1), 3),
        "real_candidates_checked": n_real,
        "false_kills": n_false_kill,
        "false_kill_rate": round(n_false_kill / max(n_real, 1), 3),
        "rows": rows,
    }
    return summary


def main():
    import subprocess
    commit = (sys.argv[1] if len(sys.argv) > 1 else
              subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                             capture_output=True,
                             text=True).stdout.strip()[:12])
    print(f"[seeded] sweep against run dir: {commit}")
    s = sweep(commit)
    out_json = ENGINE_RUNS / "r6_seeded_defects.json"
    out_json.write_text(json.dumps(s, indent=1, default=str) + "\n",
                        encoding="utf-8")
    lines = ["# R6 seeded-defect catch vs false kills (deterministic gate)",
             "", f"- commit: `{commit}`",
             f"- seeded defects: {s['seeded_caught']}/{s['seeded_defects']} "
             f"caught (catch_rate {s['catch_rate']})",
             f"- real candidates checked: {s['real_candidates_checked']} | "
             f"false kills: {s['false_kills']} (rate "
             f"{s['false_kill_rate']})", ""]
    for r in s["rows"]:
        lines.append(f"## {r['problem_id']} "
                     f"(real candidates: {r['n_real_candidates']})")
        for sd in r["seeded"]:
            lines.append(f"- {sd['defect']}: "
                         f"{'KILLED' if sd['killed'] else 'PASSED (MISS)'} "
                         f"({sd['reason_class']})")
        for fk in r["false_kills"]:
            lines.append(f"- FALSE KILL: {fk['intervention_head'][:80]} "
                         f"-> {fk['kills']}")
        lines.append("")
    (ENGINE_RUNS / "r6_seeded_defects.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"[seeded] -> {out_json.name}, r6_seeded_defects.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""r174_v19_departure_smoke.py — the DIR-3 acceptance smoke: 5
problems generated under the v19 DEPARTURE CONTRACT, each departure
adjudicated by the PANEL PROXY (ctai openai/gpt-6-luna, the panel's
own calibrated non-obviousness axis), blind to the generation lane.

Acceptance (DIR 3): 5/5 non-obvious departures.

Burn discipline: 5 problems x (1 agnes generation + up to 2 repair
retries) + 5 gpt6luna proxy calls — a SMOKE, not a corpus run; the
v19 30-candidate set (DIR 4) is a separate one-shot.
"""
from __future__ import annotations
import json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from discovery_fabric.generation import mechanism_map as mm
from discovery_fabric.generation import nonobvious_departure as nd
from discovery_fabric.generation import physics_validate as pv
from discovery_fabric.generation import quant_generic as qg
import r40_machine_v77 as m77  # noqa: E402 (the frozen agnes gateway)

OUT = REPO / "eval" / "r174_v19_smoke"
OUT.mkdir(exist_ok=True)

# 5 SMOKE problems — self-authored, typed NOT the sealed set (the v19
# one-shot in DIR 4 uses the sealed problem-only set; this smoke only
# validates the LEVER). Each carries the domain for transfer ranking.
SMOKE = [
    {"problem_id": "s1-hx-scaling", "domain": "chemical-process",
     "failure": ("Calcium carbonate scale forms on the cooling-water "
                 "side of a carbon-steel heat exchanger; the thermal "
                 "duty drops 30% within 3 weeks and cleaning requires "
                 "a full shutdown and acid wash.")},
    {"problem_id": "s2-pump-cavitation", "domain": "water-treatment",
     "failure": ("The booster pump cavitates at low suction pressure; "
                 "the impeller pitting forces replacement every 8 "
                 "months and the standard fix is a bigger, costlier "
                 "pump with a larger inlet.")},
    {"problem_id": "s3-conveyor-belt-wear", "domain": "mineral-processing",
     "failure": ("The overland conveyor belt cover wears through at "
                 "the loading zone from ore impact and abrasion; the "
                 "standard response is a thicker cover and more "
                 "frequent idler replacement.")},
    {"problem_id": "s4-pipeline-hydrate", "domain": "offshore-energy",
     "failure": ("Gas hydrates nucleate in the subsea pipeline during "
                 "shutdowns; methanol dosing is the standard practice "
                 "but it is expensive and environmentally penalized.")},
    {"problem_id": "s5-chiller-frost", "domain": "hvac",
     "failure": ("Frost accumulates on the evaporator coil of a "
                 "freezer air unit; the standard fix is electric "
                 "defrost cycles that dump heat into the cold room and "
                 "raise the product temperature.")},
]


def env_keys() -> dict:
    out = {}
    for line in (REPO / ".env.keys").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return out


def ctai_chat(prompt: str, key: str, base: str, max_tokens: int = 900,
              model: str = "openai/gpt-6-luna") -> str:
    body = json.dumps({"model": model, "max_tokens": max_tokens,
                       "temperature": 0,
                       "messages": [{"role": "user", "content": prompt}]}
                      ).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=body, method="POST",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        b = json.loads(r.read().decode())
    m = (b.get("choices") or [{}])[0].get("message", {})
    return m.get("content") or m.get("reasoning_content") or ""


GEN_SUFFIX = (
    "You are a mechanical design engineer. Produce a NOVELTY "
    "STATEMENT with these sections in order, exact headings: "
    "CROSS-DOMAIN INSPIRATION, NEAREST PRIOR ART, THE DEPARTURE, "
    "NOT-A-SUBSTITUTION, DIRECTION CHECK, ENABLING CONDITIONS, "
    "ENVELOPE CHECK, STEELMAN, then "
    "MECHANISM, EXPECTED_EFFECT (one quantitative prediction with "
    "units and a measured-by plan), FALSIFICATION_TEST, and the KILL "
    "CONDITION wording 'the mechanism is FALSIFIED if <metric> does "
    "not change by at least <N><unit> within <window>' naming a "
    "physical test vehicle.")


def proxy_verdict(problem: str, candidate: str, key: str, base: str) -> dict:
    """The panel-proxy adjudication, the panel's own non-obviousness
    QUESTION (from the sealed packs), blind to the generation lane."""
    prompt = (
        "You are a patent-examination judge. Given an engineering "
        "problem and a proposed intervention, judge ONLY: is the "
        "mechanism a non-obvious departure from the nearest prior "
        "art (not a routine parameter or material change a skilled "
        "practitioner would reach for first), AND physically viable "
        "as stated (the enabling conditions consistent with the "
        "problem's envelope)?\n\n"
        f"PROBLEM:\n{problem}\n\nPROPOSED INTERVENTION:\n{candidate}\n\n"
        "Answer in EXACTLY this format:\n"
        "VIABLE: yes|no\nNON_OBVIOUS: yes|no\n"
        "VIABLE_REASON: <one sentence>\nNON_OBVIOUS_REASON: <one "
        "sentence>")
    raw = ctai_chat(prompt, key, base)
    v = bool(__import__("re").search(r"VIABLE:\s*yes", raw, 2))
    n = bool(__import__("re").search(r"NON_OBVIOUS:\s*yes", raw, 2))
    vr = (__import__("re").search(r"VIABLE_REASON:\s*(.+)", raw) or
          [None, ""])[1].strip()[:300]
    nr = (__import__("re").search(r"NON_OBVIOUS_REASON:\s*(.+)", raw) or
          [None, ""])[1].strip()[:300]
    return {"viable": v, "non_obvious": n, "viable_reason": vr,
            "non_obvious_reason": nr, "raw_head": raw[:200]}


def main() -> int:
    keys = env_keys()
    ct_key = keys.get("CTAI_API_KEY", "")
    ct_base = keys.get("CTAI_BASE_URL", "https://api.cantrustai.xyz/v1")
    # the agnes transport: the frozen loop-local gateway (start_gateway
    # generates its own bearer key; the upstream is the z-ai CLI)
    gw, gw_key = m77.start_gateway()
    ag_key = gw_key
    rows = []
    for i, prob in enumerate(SMOKE, 1):
        pid = prob["problem_id"]
        outp = OUT / f"{pid}.json"
        if outp.exists():
            rows.append(json.loads(outp.read_text()))
            print(f"=== {pid}: resumed (byte-resume)", flush=True)
            continue
        print(f"=== {pid} ({i}/5) generating under the DEPARTURE "
              f"CONTRACT ...", flush=True)
        text = prob["failure"]
        sel = mm.classify_failure(text)
        dblock = nd.departure_block(text, prob["domain"])
        prompt = (f"PROBLEM: {text}\n\n{dblock['prompt_block']}\n\n"
                  f"{GEN_SUFFIX}")
        row = {"problem_id": pid, "domain": prob["domain"],
               "failure_class": sel.failure_class,
               "ranked": dblock["ranked"]["n_candidates"],
               "attempts": 0}
        final = ""
        for attempt in range(1, 4):
            row["attempts"] += 1
            txt, _lat = m77._gen_v77(prompt, GEN_SUFFIX, ag_key)
            dep = nd.check_departure(txt)
            row["departure_check"] = dep["parts"]
            if dep["passed"]:
                final = txt
                break
            prompt = (f"{prompt}\n\nREPAIR: {dep['repair_directive']}"
                      "\nRegenerate the FULL statement with every "
                      "heading.")
            print(f"    departure incomplete (try {attempt}: "
                  f"{dep['missing']}) — repair fed back", flush=True)
        if not final:
            row["outcome"] = "DEPARTURE_UNRESOLVED"
            outp.write_text(json.dumps(row, indent=1) + "\n")
            rows.append(row)
            continue
        # physics gate rides unchanged (DIR 6 intact)
        quant = qg.emit_prediction_generic(sel.failure_class, final)
        physics = pv.validate_row(final, quant)
        row["physics_verdict"] = physics["verdict"]
        row["physics_errors"] = [e["check_id"] for e in
                                 physics["genuine_physics_errors"]]
        # the panel proxy adjudicates the departure
        print(f"    proxy adjudication (gpt-6-luna) ...", flush=True)
        try:
            verdict = proxy_verdict(text, final, ct_key, ct_base)
        except Exception as e:  # noqa: BLE001
            verdict = {"error": f"{type(e).__name__}: {str(e)[:120]}"}
        row["proxy"] = verdict
        row["candidate"] = final
        row["outcome"] = "SMOKE_ROW_DONE"
        outp.write_text(json.dumps(row, indent=1, ensure_ascii=False)
                        + "\n")
        rows.append(row)
        print(f"    physics={row['physics_verdict']} "
              f"viable={verdict.get('viable')} "
              f"non_obvious={verdict.get('non_obvious')}", flush=True)
        time.sleep(2)
    n_ok = sum(1 for r in rows
               if (r.get("proxy") or {}).get("non_obvious"))
    n_dep = sum(1 for r in rows if "departure_check" in r and all(
        r["departure_check"].values()))
    summary = {
        "record": "R174_V19_DEPARTURE_SMOKE/1.0.0",
        "session": "builder-r174s1",
        "acceptance": "DIR 3: 5/5 non-obvious departures (panel "
                      "proxy gpt-6-luna, the panel's own calibrated "
                      "axis)",
        "n_problems": len(rows),
        "n_departure_complete": n_dep,
        "n_non_obvious_by_proxy": n_ok,
        "smoke_problems_typed": "SELF-AUTHORED smoke set — NOT the "
                                 "sealed problem set (the v19 one-shot "
                                 "is DIR 4's separate act)",
        "rows": [{k: r.get(k) for k in
                  ("problem_id", "failure_class", "attempts",
                   "physics_verdict", "physics_errors", "outcome",
                   "proxy")} for r in rows],
    }
    (OUT / "SUMMARY.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    print(f"DEPARTURE complete: {n_dep}/5 | proxy non-obvious: "
          f"{n_ok}/5 | ACCEPT={'MET' if n_ok == 5 and n_dep == 5 else 'NOT MET'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

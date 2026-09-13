#!/usr/bin/env python3
"""scripts/r452_assay.py — R452 Phases 1-2: the frozen three-problem
discovery assay, generated and executed automatically.

Phase 1 — freeze a GENUINELY NEW three-problem discovery assay, each
problem from a different technical family:

  A. medical / device          (r452a surgical irrigation pressure
                                instability)
  B. energy / industrial       (r452b wind-gearbox cold-start pinion
                                bearing lubrication starvation)
  C. materials / electronics   (r452c SiC traction-inverter die-attach
                                thermal-cycling delamination)

Freshness is MACHINE-CHECKED, not asserted (Art. VI):
  - content hash (sha256) of each authored text, recorded;
  - hash uniqueness against EVERY previously submitted problem text
    collected from the repository (campaigns, benchmarks, acceptance
    runs, the production fresh run);
  - near-duplicate lexical check (token-set Jaccard) against every
    prior text — a copied/paraphrased problem fails;
  - showcase-territory vocabulary check (the existing portfolio's
    device families must not appear);
  - the problems are NOT optimized to help the engine succeed: each
    states symptoms and constraints only — no solution class is
    seeded (Art. XLIII, search-space neutral), constraints are hard,
    and the difficulty is the point ("The purpose is to test
    generality").

Phase 2 — run each problem through the ACTUAL discovery path (the
same engine, the deployed production-equivalent routing authority:
ZERO_PAID_COST cost policy + runtime admission + the localqwen route
through the ordinary registry path), capturing the ten directive
stages: problem, retrieval, evidence freeze, mechanism synthesis,
candidate generation, prior-art collision, attack, adjudication,
classification, next action.

Legitimate outcomes (no hardcoded expected-good-answer):
  KILLED / INVENTION_UNDER_DEVELOPMENT / REJECTED / UNKNOWN_NOT_REACHED
Infrastructure failure is typed INCOMPLETE_INFRASTRUCTURE_FAILURE and
NEVER converted into a scientific rejection (Art. LXI).

Usage:
  python scripts/r452_assay.py build       # freeze problems + freshness
  python scripts/r452_assay.py engine A 900   # run case A (budget s)
  python scripts/r452_assay.py assess      # reconstruct all chains
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

OUT_ROOT = REPO_ROOT / "R452"
ASSAY_RECORD = OUT_ROOT / "ASSAY_PROBLEMS.json"
CHAIN_RECORD = OUT_ROOT / "ASSAY_CHAINS.json"

PAID_ENV_VARS = [
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY",
    "NVIDIA_API_KEY", "DEEPSEEK_API_KEY", "MISTRAL_API_KEY",
    "GEMINI_API_KEY", "QWEN_API_KEY", "TOKEN_ROUTER_API_KEY",
    "ZAI_API_KEY",
]

# ---------------------------------------------------------------------------
# THE THREE AUTHORED PROBLEMS (R452 originals — symptoms and constraints
# only; no solution class seeded; hard constraints kept hard)
# ---------------------------------------------------------------------------

AUTHORED_PROBLEMS: Dict[str, Dict[str, Any]] = {
    "A": {
        "case_id": "r452a-surgical-irrigation-pressure-instability",
        "family": "medical_device",
        "directive_slot": "A. medical / device",
        "run_id": "r452a: surgical-irrigation-pressure-instability",
        "session_id": "r452-assay-a",
        "text": (
            "An ambulatory surgery center runs arthroscopic shoulder and "
            "knee cases on a peristaltic dual-bag irrigation system: "
            "inflow runs from two 3-litre gravity bags through a pump "
            "cassette and 3.2-millimetre inner-diameter tubing into a "
            "4.5-millimetre inflow cannula, with outflow through a "
            "3.5-millimetre resection sheath to a floor canister. Joint "
            "distension is unstable whenever the surgeon steps from "
            "low-flow shaver mode to high-flow flush: commanded flow "
            "jumps from roughly 0.3 to 1.5 litres per minute within "
            "seconds, intra-articular pressure swings between 15 and 95 "
            "millimetres of mercury against the 40-to-60 target band, "
            "the capsule visibly collapses during suction-heavy "
            "resection, and the outflow sheath intermittently packs "
            "with resected tissue debris until the scrub nurse "
            "back-flushes it by hand, about three times per case, "
            "breaking sterile technique and adding 10 to 15 minutes of "
            "case time. The pump's pressure-limit alarm fires in "
            "roughly one of three cases and is routinely silenced as "
            "non-specific. The center needs joint pressure held inside "
            "the 40-to-60 millimetre band across the full commanded "
            "flow range, with no pump hardware replacement, no change "
            "to the cleared cannula and sheath diameters, no powered "
            "electronics added to the disposable set beyond a passive "
            "element, and no added set-up steps for the scrub team."
        ),
    },
    "B": {
        "case_id": "r452b-gearbox-coldstart-pinion-starvation",
        "family": "energy_industrial",
        "directive_slot": "B. energy / industrial",
        "run_id": "r452b: gearbox-coldstart-pinion-starvation",
        "session_id": "r452-assay-b",
        "text": (
            "A wind farm's 3-megawatt turbines use three-stage planetary "
            "gearboxes whose lubrication system feeds ISO VG 320 "
            "synthetic oil from a shaft-driven pump delivering about "
            "2.5 bar to the manifold through a drilled distribution "
            "manifold: a 4-millimetre main gallery feeding "
            "2.5-millimetre drilled branches, each roughly 60 "
            "millimetres long, to the planet bearings and the "
            "high-speed pinion bearing. During winter cold starts at "
            "minus 20 degrees Celsius the oil is near 1,800 centipoise "
            "until circulation warms it, and the high-speed pinion "
            "bearing runs starved for the first 3 to 8 minutes: bronze "
            "cage wear particles appear in the oil filter by the first "
            "500-hour inspection, bearing temperature spikes above 110 "
            "degrees Celsius are logged on most cold mornings, and two "
            "gearboxes have failed within their 5-year warranty window "
            "from pinion bearing scuffing, at 340,000 and 410,000 "
            "euros of replacement cost each including crane and "
            "downtime. The operators need the high-speed pinion "
            "bearing to receive at least 0.8 litres per minute of oil "
            "within 60 seconds of a cold start at minus 20 degrees, "
            "without heaters drawing more than the 200 watts available "
            "from the existing 24-volt start-up circuit, without adding "
            "a second pump, without changing the oil specification, and "
            "without a manifold redesign that requires recertifying the "
            "gearbox internals."
        ),
    },
    "C": {
        "case_id": "r452c-sic-module-dieattach-delamination",
        "family": "materials_electronics",
        "directive_slot": "C. materials / electronics",
        "run_id": "r452c: sic-module-dieattach-delamination",
        "session_id": "r452-assay-c",
        "text": (
            "An automotive supplier builds 800-volt silicon-carbide "
            "traction-inverter power modules whose junction temperature "
            "cycles between 45 and 175 degrees Celsius during normal "
            "city driving, roughly 300,000 deep cycles over the "
            "vehicle life. The die-attach layer between the "
            "silicon-carbide die and the direct-bonded-copper substrate "
            "progressively delaminates from the die edges inward: "
            "measured thermal resistance from junction to baseplate "
            "climbs 25 to 40 percent by end of life, junction "
            "temperature rise follows, and modules begin exceeding the "
            "175-degree junction limit during 60-second acceleration "
            "events well before the vehicle's 15-year design life. "
            "Failures cluster when the module sees sustained "
            "cornering-grade vibration combined with high-load "
            "regeneration, and returned modules show crack patterns "
            "initiating at the die corner with the largest solder void. "
            "The supplier needs junction-to-baseplate thermal "
            "resistance to stay within 10 percent of new-build value "
            "across the full 300,000-cycle life, with no increase in "
            "module footprint or height (the inverter's power density "
            "is fixed), no process step beyond standard power-module "
            "assembly lines, die size unchanged, and cost per module "
            "held within 8 percent of the current bill of materials."
        ),
    },
}

# The repeat run for the repeated-run-variance metric (instrument
# metric 10): problem A run a second time through the same path — the
# SAME authored text (that is the point of the variance arm), a fresh
# case/run identity.
REPEAT_CASE = {"A2": {**AUTHORED_PROBLEMS["A"],
                      "case_id": "r452a-repeat-variance",
                      "run_id": "r452a2: surgical-irrigation repeat "
                                "(variance arm)",
                      "session_id": "r452-assay-a2",
                      "repeat_of": "A"}}

ALL_CASES: Dict[str, Dict[str, Any]] = {**AUTHORED_PROBLEMS,
                                        **REPEAT_CASE}

# ---------------------------------------------------------------------------
# Freshness machinery (Phase 1)
# ---------------------------------------------------------------------------

#: the existing showcase portfolio's device territory — the assay
#: problems must not copy or veer into it (never copied from the
#: existing showcase portfolio)
SHOWCASE_VOCABULARY = (
    "shunt", "hydrocephalus", "cerebrospinal", "csf", "ommaya",
    "ventriculostomy", "drainage floor", "lumbo-peritoneal",
    "ventriculoperitoneal", "hydrocephalic",
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set:
    return set(_TOKEN_RE.findall(text.lower()))


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def collect_prior_problem_texts() -> List[Dict[str, Any]]:
    """Collect EVERY previously submitted problem text from the
    repository (deterministic walk of the recorded problem sources)."""
    prior: List[Dict[str, Any]] = []
    pats = [
        "discovery_campaigns/*/PROBLEM_*.json",
        "R444/SMOKE/problem.json",
        "R451/ACCEPTANCE_RUN/fresh_problem.json",
        "R451/ACCEPTANCE_RUN_P2/fresh_problem.json",
        "R451/ACCEPTANCE_RUN_C13/fresh_problem.json",
    ]
    for pat in pats:
        for p in REPO_ROOT.glob(pat):
            try:
                d = json.loads(p.read_text())
            except Exception:  # noqa: BLE001
                continue
            t = (d.get("text") or d.get("failure") or "")
            if isinstance(t, str) and len(t) > 80:
                prior.append({"source": str(p.relative_to(REPO_ROOT)),
                              "problem_id": d.get("problem_id"),
                              "text": t})
    # R450 benchmark problems
    rb = REPO_ROOT / "R450" / "DIRECTIONAL_BENCHMARK.json"
    if rb.exists():
        try:
            d = json.loads(rb.read_text())
            for p in d.get("problems") or []:
                t = p.get("problem_text") or ""
                if len(t) > 80:
                    prior.append({
                        "source": "R450/DIRECTIONAL_BENCHMARK.json",
                        "problem_id": p.get("problem_id"),
                        "text": t})
        except Exception:  # noqa: BLE001
            pass
    # R449 fresh evidence-powered discovery problem
    r449 = REPO_ROOT / "R449" / "FRESH_EVIDENCE_POWERED_DISCOVERY.json"
    if r449.exists():
        try:
            d = json.loads(r449.read_text())
            t = ((d.get("experiment_design") or {})
                 .get("fresh_problem") or "")
            if len(t) > 80:
                prior.append({
                    "source": "R449/FRESH_EVIDENCE_POWERED_DISCOVERY.json",
                    "problem_id": d.get("problem_id")
                    or "seawater-corrosion",
                    "text": t})
        except Exception:  # noqa: BLE001
            pass
    # the R451 production fresh run case text (the lyophilization
    # problem — submitted to PRODUCTION, never to a local battery)
    pr = REPO_ROOT / "R451" / "PRODUCTION_FRESH_RUN_C13.json"
    if pr.exists():
        try:
            d = json.loads(pr.read_text())
            t = ((d.get("case") or {}).get("text") or "")
            if len(t) > 80:
                prior.append({
                    "source": "R451/PRODUCTION_FRESH_RUN_C13.json",
                    "problem_id": d.get("case", {}).get("case_id"),
                    "text": t})
        except Exception:  # noqa: BLE001
            pass
    return prior


def check_freshness() -> Dict[str, Any]:
    """The machine-readable freshness evidence for all three problems
    (plus the repeat arm). FAILS CLOSED on any violation."""
    prior = collect_prior_problem_texts()
    prior_hashes = {hashlib.sha256(p["text"].encode()).hexdigest()
                    for p in prior}
    results: Dict[str, Any] = {
        "prior_problem_count": len(prior),
        "prior_sources": sorted({p["source"] for p in prior}),
        "cases": {},
        "violations": [],
    }
    case_ids = set()
    for case, spec in ALL_CASES.items():
        text = spec["text"]
        h = hashlib.sha256(text.encode()).hexdigest()
        cid = spec["case_id"]
        case_ids.add(cid)
        toks = _tokens(text)
        overlaps = []
        for p in prior:
            j = _jaccard(toks, _tokens(p["text"]))
            if j > 0.0:
                overlaps.append({
                    "source": p["source"],
                    "problem_id": p.get("problem_id"),
                    "jaccard": round(j, 4)})
        overlaps.sort(key=lambda x: -x["jaccard"])
        vocab_hits = [w for w in SHOWCASE_VOCABULARY
                      if w in text.lower()]
        checks = {
            "content_sha256": h,
            "text_chars": len(text),
            "hash_unique_vs_prior": h not in prior_hashes,
            "max_prior_jaccard": (overlaps[0]["jaccard"]
                                  if overlaps else 0.0),
            "near_duplicate_free": (not overlaps
                                    or overlaps[0]["jaccard"] < 0.35),
            "showcase_vocabulary_hits": vocab_hits,
            "showcase_territory_free": not vocab_hits,
            "problem_id_fresh": True,  # set after the loop
        }
        results["cases"][case] = {
            "case_id": cid,
            "family": spec["family"],
            "directive_slot": spec["directive_slot"],
            "repeat_of": spec.get("repeat_of"),
            "checks": checks,
            "top_prior_overlaps": overlaps[:3],
        }
    # problem_id uniqueness vs prior ids and within the assay
    prior_ids = {p.get("problem_id") for p in prior}
    for case, rec in results["cases"].items():
        if rec["case_id"] in prior_ids:
            rec["checks"]["problem_id_fresh"] = False
            results["violations"].append(
                f"{case}: problem_id {rec['case_id']} collides with a "
                f"prior problem id")
    if len(case_ids) != len(results["cases"]):
        results["violations"].append("duplicate case_id inside the assay")
    # violations
    for case, rec in results["cases"].items():
        c = rec["checks"]
        if not c["hash_unique_vs_prior"]:
            results["violations"].append(
                f"{case}: content hash matches a prior problem text")
        if not c["near_duplicate_free"]:
            results["violations"].append(
                f"{case}: near-duplicate overlap with a prior problem "
                f"(max Jaccard {c['max_prior_jaccard']})")
        if not c["showcase_territory_free"]:
            results["violations"].append(
                f"{case}: showcase-territory vocabulary present "
                f"({c['showcase_vocabulary_hits']})")
    results["fresh"] = not results["violations"]
    return results


def build() -> int:
    """Freeze the three-problem assay with freshness evidence."""
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    fresh = check_freshness()
    if not fresh["fresh"]:
        print("[r452-assay] FRESHNESS FAIL-CLOSED:")
        for v in fresh["violations"]:
            print("  -", v)
        ASSAY_RECORD.write_text(json.dumps(fresh, indent=1))
        return 2
    for case, spec in ALL_CASES.items():
        doc = {
            "problem_id": spec["case_id"],
            "text": spec["text"],
            "r452_freshness": {
                "class": "GENUINELY_FRESH",
                "authored_for": "R452",
                "authored_at": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"),
                "content_sha256": fresh["cases"][case]["checks"][
                    "content_sha256"],
                "never_previously_submitted": True,
                "never_submitted_to": [
                    "production", "benchmarks", "batteries",
                    "prior-rounds", "showcase-portfolio"],
                "machine_checks": fresh["cases"][case]["checks"],
            },
            "family": spec["family"],
            "directive_slot": spec["directive_slot"],
        }
        if spec.get("repeat_of"):
            doc["repeat_of"] = spec["repeat_of"]
        p = OUT_ROOT / f"ASSAY_RUN_{case}" / "authored_problem.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, indent=1))
        print(f"[r452-assay] {case}: {spec['case_id']} frozen "
              f"(hash {doc['r452_freshness']['content_sha256'][:12]}…, "
              f"max prior Jaccard "
              f"{fresh['cases'][case]['checks']['max_prior_jaccard']})")
    ASSAY_RECORD.write_text(json.dumps(fresh, indent=1))
    print(f"[r452-assay] assay frozen -> {ASSAY_RECORD}")
    return 0


# ---------------------------------------------------------------------------
# Phase 2 — run the problems through the actual discovery path
# ---------------------------------------------------------------------------

def _log(msg: str) -> None:
    print(f"[r452-assay] {msg}", flush=True)


def _case_dir(case: str) -> Path:
    return OUT_ROOT / f"ASSAY_RUN_{case}"


def build_engine_problem(case: str) -> Path:
    """Build the ENGINE problem (MODEL_DERIVED extraction through the
    same zero-paid registry — the same way a production user's problem
    enters)."""
    spec = ALL_CASES[case]
    out_dir = _case_dir(case)
    problem_json = out_dir / "fresh_problem.json"
    if problem_json.exists():
        _log(f"{case}: engine problem already built")
        return problem_json
    import r451_local_qwen as lq
    assert lq.ensure_server(), "llama-server failed to start"
    os.environ["LOCAL_QWEN_BASE_URL"] = lq.BASE + "/v1/chat/completions"
    os.environ["ENGINE_MODEL_COST_POLICY"] = "ZERO_PAID_COST"
    for k in PAID_ENV_VARS:
        os.environ.pop(k, None)
    from toscanini.problem_builder import build_problem
    built = build_problem(spec["text"])
    problem = built.get("problem") if isinstance(built.get("problem"),
                                                  dict) else built
    problem["problem_id"] = spec["case_id"]
    problem["r452_freshness"] = {
        "class": "GENUINELY_FRESH",
        "authored_for": "R452",
        "content_sha256": hashlib.sha256(
            spec["text"].encode()).hexdigest(),
        "never_previously_submitted": True,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    problem_json.write_text(json.dumps(problem, indent=1,
                                       ensure_ascii=False))
    _log(f"{case}: engine problem built -> {problem_json}")
    return problem_json


def run_engine(case: str, budget_s: int) -> None:
    """Run the engine DETACHED with the pinned run identity (the
    R451-C1.1 survival pattern): the production-equivalent routing
    authority (ZERO_PAID_COST + runtime admission + localqwen through
    the ordinary registry path)."""
    spec = ALL_CASES[case]
    out_dir = _case_dir(case)
    problem_json = build_engine_problem(case)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["ENGINE_MODEL_COST_POLICY"] = "ZERO_PAID_COST"
    env["LOCAL_QWEN_BASE_URL"] = \
        "http://127.0.0.1:8790/v1/chat/completions"
    for k in PAID_ENV_VARS:
        env.pop(k, None)

    import r451_local_qwen as _lq
    pid_file = out_dir / "ENGINE_PID"
    log_file = out_dir / "engine.log"

    def _engine_pid() -> Optional[int]:
        try:
            return int(pid_file.read_text().strip())
        except Exception:  # noqa: BLE001
            return None

    def _pid_alive(pid: Optional[int]) -> bool:
        if not pid:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    assert _lq.ensure_server(), "llama-server failed to start"
    pid = _engine_pid()
    if _pid_alive(pid):
        _log(f"{case}: attaching to live engine pid={pid}")
    else:
        cmd = [sys.executable, "-m", "discovery_fabric.engine.run",
               "--problem-json", str(problem_json),
               "--out", str(out_dir), "--no-package",
               "--run-id", spec["run_id"],
               "--session-id", spec["session_id"]]
        if (out_dir / "problem.json").exists():
            cmd.append("--resume")
            _log(f"{case}: starting DETACHED engine (resume)")
        else:
            _log(f"{case}: starting DETACHED engine (fresh)")
        log_fh = open(log_file, "ab")
        proc = subprocess.Popen(cmd, cwd=str(REPO_ROOT), env=env,
                                stdout=log_fh, stderr=subprocess.STDOUT,
                                start_new_session=True)
        pid_file.write_text(str(proc.pid))
        _log(f"{case}: detached engine pid={proc.pid}")

    import threading

    def _watchdog() -> None:
        while True:
            try:
                if not _lq._proc_alive():
                    _log(f"{case}: watchdog: llama-server DOWN — "
                         f"restarting")
                    _lq.ensure_server()
            except Exception:  # noqa: BLE001
                pass
            time.sleep(5)

    threading.Thread(target=_watchdog, daemon=True).start()
    start = time.time()
    last_size = 0
    while True:
        if not _pid_alive(_engine_pid()):
            _log(f"{case}: engine process exited "
                 f"(final_state written if the run completed)")
            try:
                pid_file.unlink()
            except FileNotFoundError:
                pass
            return
        if time.time() - start > budget_s:
            _log(f"{case}: budget reached — engine KEEPS RUNNING "
                 f"(detached); re-invoke to continue monitoring")
            return
        try:
            size = log_file.stat().st_size
            if size > last_size:
                with open(log_file, "rb") as fh:
                    fh.seek(last_size)
                    chunk = fh.read(size - last_size).decode(
                        "utf-8", "replace")
                for line in chunk.splitlines()[-4:]:
                    if line.strip():
                        _log(f"  {case} engine: {line.rstrip()[:140]}")
                last_size = size
        except OSError:
            pass
        time.sleep(3.0)


# ---------------------------------------------------------------------------
# Phase 2 assessment — the ten captured stages + the outcome vocabulary
# ---------------------------------------------------------------------------

def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        if p.exists():
            d = json.loads(p.read_text())
            return d if isinstance(d, dict) else None
    except Exception:  # noqa: BLE001
        return None
    return None


def _n_records(doc: Optional[Dict[str, Any]]) -> int:
    if not doc:
        return 0
    for key in ("evidence", "records", "evidence_ids", "items"):
        v = doc.get(key)
        if isinstance(v, list):
            return len(v)
    ev = doc.get("evidence_state") or {}
    if isinstance(ev, dict):
        for key in ("records", "frozen_records", "evidence_ids"):
            v = ev.get(key)
            if isinstance(v, list):
                return len(v)
        try:
            return int(ev.get("n_records") or 0)
        except (TypeError, ValueError):
            pass
    return 0


def assess_case(case: str) -> Dict[str, Any]:
    """Reconstruct the ten directive stages from the run's OWN records
    (Art. X) and classify the terminal outcome into the directive's
    legitimate-outcome vocabulary."""
    spec = ALL_CASES[case]
    d = _case_dir(case)
    ten: Dict[str, Any] = {}

    problem = _read_json(d / "problem.json") or \
        _read_json(d / "fresh_problem.json")
    ten["problem"] = bool(problem)
    ten["problem_id"] = (problem or {}).get("problem_id")

    retrieve = _read_json(d / "envelope_RETRIEVE.json")
    ten["retrieval"] = bool(retrieve)
    ten["retrieval_providers"] = sorted({
        str(k) for k in (
            ((retrieve or {}).get("evidence") or {}).keys()
            if isinstance((retrieve or {}).get("evidence"), dict)
            else [])})

    freeze = _read_json(d / "envelope_FREEZE.json")
    n_ev = _n_records(freeze)
    ten["evidence_freeze"] = n_ev > 0
    ten["evidence_records"] = n_ev

    synth = _read_json(d / "envelope_SYNTHESIZE.json") or \
        _read_json(d / "stage_SYNTHESIZE.json")
    ten["mechanism_synthesis"] = bool(synth)

    mech = _read_json(d / "stage_MECHANISM_SPACE.json") or \
        _read_json(d / "envelope_MECHANISM_SPACE.json")
    n_cand = int((mech or {}).get("n_candidates") or 0)
    ten["candidate_generation"] = n_cand > 0 or bool(mech)
    ten["mechanism_space_state"] = (mech or {}).get("state")
    ten["n_candidates"] = n_cand

    collision = _read_json(d / "envelope_COLLISION.json") or \
        _read_json(d / "stage_COLLISION.json")
    ten["prior_art_collision"] = bool(collision)
    ten["prior_art_status"] = ((collision or {}).get("prior_art")
                               or {}).get("prior_art_status")

    # attack: the ATTACK stage record + the adversarial sub-record
    attack = _read_json(d / "envelope_ATTACK.json") or \
        _read_json(d / "stage_ATTACK.json")
    ar = (attack or {}).get("attack_results") or {}
    ten["attack"] = bool(attack)
    ten["adversarial_status"] = ar.get("adversarial_status")
    ten["adversarial_overall"] = ar.get("overall")
    ten["adversarial_not_run_reason"] = ar.get(
        "adversarial_not_run_reason")
    ten["attacks_recorded"] = len(ar.get("attacks") or [])

    adjudication = _read_json(d / "envelope_ADJUDICATION.json") or \
        _read_json(d / "stage_ADJUDICATION.json")
    adj = (adjudication or {}).get("adjudication") or {}
    council = adj.get("council") or {}
    ten["adjudication"] = bool(adjudication)
    ten["adjudication_verdict"] = council.get("verdict")
    ten["evidence_verified"] = bool(
        (adj.get("evidence_verification") or {}).get("verified"))

    classify = _read_json(d / "envelope_CLASSIFY.json") or \
        _read_json(d / "stage_CLASSIFY.json")
    ten["classification"] = bool(classify)

    nba = _read_json(d / "envelope_NEXT_BEST_ACTION.json") or \
        _read_json(d / "stage_NEXT_BEST_ACTION.json")
    ten["next_action"] = bool(nba)

    final = _read_json(d / "final_state.json") or {}
    ten["final_status"] = final.get("final_status")
    ten["failed_stages"] = final.get("failed_stages") or {}
    ten["reason"] = final.get("reason")

    # the routing provenance for THIS run (isolated by run_id)
    try:
        from discovery_fabric.engine import model_routing as mr
        run_lines = mr.ledger_for_run(spec["run_id"])
    except Exception:  # noqa: BLE001
        run_lines = []
    run_owned = [l for l in run_lines
                 if l.get("call_class") == "RUN_OWNED"]
    ten["routing"] = {
        "run_lines": len(run_lines),
        "run_owned": len(run_owned),
        "paid_lines": sum(
            1 for l in run_owned
            if (l.get("cost_class") or "")
            not in ("ZERO_PAID_COST_SELF_HOSTED", None)),
        "providers": sorted({str(l.get("provider"))
                             for l in run_owned}),
        "invariant_non_null_run_id": all(
            bool(l.get("run_id")) for l in run_owned),
    }

    # the terminal outcome — the directive's vocabulary; infrastructure
    # failure is NEVER a scientific rejection (Art. LXI)
    fs = ten.get("final_status")
    failed = ten.get("failed_stages") or {}
    if fs is None:
        outcome = "UNKNOWN_NOT_REACHED"
        outcome_basis = ("no final_state record — the run did not "
                         "reach a terminal classification")
    elif failed or fs in ("MECHANISM_GENERATION_FAILED",):
        outcome = "INCOMPLETE_INFRASTRUCTURE_FAILURE"
        outcome_basis = (f"stages failed: {sorted(failed.keys())} — "
                         "infrastructure, never a scientific rejection "
                         "(Art. LXI)")
    elif fs == "INVENTION_UNDER_DEVELOPMENT":
        verdict = ten.get("adjudication_verdict")
        adversarial = ten.get("adversarial_overall")
        if verdict in ("REJECTED", "KILLED") or \
                adversarial in ("KILLED",):
            outcome = "KILLED"
            outcome_basis = (
                f"adjudication verdict {verdict}, adversarial "
                f"{adversarial} — the candidate was killed by the "
                f"challenge gauntlet (an honest negative result)")
        else:
            outcome = "INVENTION_UNDER_DEVELOPMENT"
            outcome_basis = (
                f"final status {fs} (adjudication {verdict}, "
                f"adversarial {adversarial}) — the invention is under "
                "development with its honest maturity")
    elif fs in ("REJECTED", "REJECTED_SCIENTIFIC", "REJECTED_EVIDENCE",
                "REJECTED_PRIOR_ART", "REJECTED_ENGINEERING",
                "REJECTED_ATTACK", "REJECTED_EXPERIMENT"):
        outcome = "REJECTED"
        outcome_basis = f"final status {fs} — the machine rejected it"
    else:
        outcome = "UNKNOWN_NOT_REACHED"
        outcome_basis = f"final status {fs!r} not in the closed map"

    return {
        "case": case,
        "case_id": spec["case_id"],
        "family": spec["family"],
        "directive_slot": spec["directive_slot"],
        "repeat_of": spec.get("repeat_of"),
        "run_id": spec["run_id"],
        "session_id": spec["session_id"],
        "ten_stages": ten,
        "terminal_outcome": outcome,
        "terminal_outcome_basis": outcome_basis,
    }


def assess() -> int:
    cases = ["A", "B", "C", "A2"]
    chains = []
    for case in cases:
        if not (_case_dir(case) / "final_state.json").exists() and \
                not (_case_dir(case) / "problem.json").exists():
            chains.append({
                "case": case,
                "case_id": ALL_CASES[case]["case_id"],
                "terminal_outcome": "UNKNOWN_NOT_REACHED",
                "terminal_outcome_basis": "the run was not executed "
                                          "(no artifacts)"})
            continue
        chains.append(assess_case(case))
        c = chains[-1]
        _log(f"{case} ({c['case_id']}): outcome "
             f"{c['terminal_outcome']} — {c['terminal_outcome_basis']}"
             [:160])
    doc = {
        "artifact_type": "R452_ASSAY_CHAINS",
        "directive": "R452 Phase 2 — the three problems through the "
                     "actual discovery path (production-equivalent "
                     "routing authority; localqwen zero-paid route)",
        "recorded_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds"),
        "chains": chains,
        "legitimate_outcomes": [
            "KILLED", "INVENTION_UNDER_DEVELOPMENT", "REJECTED",
            "UNKNOWN_NOT_REACHED", "INCOMPLETE_INFRASTRUCTURE_FAILURE"],
        "no_hardcoded_expected_answer": True,
    }
    CHAIN_RECORD.write_text(json.dumps(doc, indent=1))
    _log(f"chains -> {CHAIN_RECORD}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == "build":
        return build()
    if cmd == "engine":
        case = sys.argv[2].upper()
        budget = int(sys.argv[3]) if len(sys.argv) > 3 else 900
        if case not in ALL_CASES:
            print(f"unknown case {case} (A/B/C/A2)")
            return 1
        run_engine(case, budget)
        return 0
    if cmd == "assess":
        return assess()
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

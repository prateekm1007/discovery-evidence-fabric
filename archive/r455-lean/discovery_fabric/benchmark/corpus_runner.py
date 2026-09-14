"""Phase 6 — benchmark the automatic generator at 15-survivor scale (Coder 2).

Supplies 15 survivor inputs (Coder 2's own benchmark fixtures, clearly
labeled SYNTHETIC_BENCHMARK_INPUT) to Coder 1's REAL automatic pipeline:

    EngineRun(...).env = envelope; rehearsal = True
    run._post_rank_pipeline(...)   -> INVENTION_SPEC -> ENGINEERING_SPEC ->
                                      package -> DISCOVERY_RELEASE

The pipeline is driven exactly as in Coder 1's E11 rehearsal pattern and
the F-series scale test — NO engine file is modified, NO output is repaired.
Every generated artifact carries SYNTHETIC_REHEARSAL=TRUE (Art. XXXVII).

Outputs (artifacts/benchmark/generated/):
    runs/BENCH_XX/...        one run dir per survivor (15)
    AUTOMATED_DOSSIER_BENCHMARK.json + companion audit artifacts

Usage:
    python3 -m discovery_fabric.benchmark.corpus_runner \
        --out artifacts/benchmark/generated [--keep-runs]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.engine import adapters as A  # noqa: E402
from discovery_fabric.engine.candidate import Candidate, sha256_obj  # noqa: E402
from discovery_fabric.engine.release import (  # noqa: E402
    build_discovery_release, write_discovery_release)
from discovery_fabric.engine.run import EngineRun  # noqa: E402

from . import audit_runner  # noqa: E402

CTX = {"run_id": "coder2:benchmark", "problem_id": "benchmark"}

CHAIN_PLAN = [
    ("VERIFY", A.EvidenceVerifyAdapter),
    ("CONTRADICTION", A.ContradictionQueueAdapter),
    ("KILLER_EXPERIMENT", A.KillerExperimentAdapter),
    ("ADJUDICATION", A.AdjudicationAdapter),
    ("CLASSIFY", A.EpistemicClassificationAdapter),
    ("NEXT_BEST_ACTION", A.NextBestActionAdapter),
    ("RANK", A.PortfolioRankingAdapter),
]

# 15 Coder-2 benchmark survivor inputs: one per engine domain, plus four
# second variants to reach 15. Each input is an INDEPENDENT fixture written
# for this benchmark (not copied from Coder 1's test suite); content
# deliberately differs across inputs so cross-package contamination has
# something to catch.
BENCHMARK_INPUTS: List[Dict[str, Any]] = [
    dict(domain="fluidics_hydraulic",
         device="CSF shunt system",
         failure_mode="OBSTRUCTION",
         failure="proximal catheter obstruction by tissue ingrowth",
         constraint="maintain lumen patency for years without revision",
         mechanism="graded-porosity outlet diffuser spreads flow to reduce stagnant zones where tissue ingrowth starts",
         intervention="porous polymeric diffuser sleeve over the distal outlet",
         effect="lower ingrowth-driven obstruction rate at equal drainage",
         fals="accelerated ingrowth bench loop; compare time-to-occlusion vs open lumen"),
    dict(domain="fluidics_hydraulic",
         device="CSF shunt system",
         failure_mode="OVERDRAINAGE",
         failure="postural overdrainage causes intracranial hypotension",
         constraint="keep drainage within physiologic band upright and supine",
         mechanism="serial siphon-limiting segments raise hydrodynamic resistance only under gravitational head",
         intervention="multi-stage gravity-compensating catheter segment",
         effect="upright drainage stays within the physiologic band",
         fals="hydrostatic column bench test; flow vs head across postures"),
    dict(domain="optical_photonic",
         device="implantable pressure sensor",
         failure_mode="POWER_DEPLETION",
         failure="battery depletion ends telemetry life",
         constraint="no replacement surgery for the power source",
         mechanism="wavelength-matched photovoltaic receiver converts transcutaneous near-infrared illumination to charge",
         intervention="subcutaneous photovoltaic patch with optical window",
         effect="sustained sensor operation from external light source",
         fals="tissue-phantom power transfer vs depth measurement"),
    dict(domain="rf_wireless",
         device="implant telemetry node",
         failure_mode="LINK_LOSS",
         failure="telemetry dropout at implant depth",
         constraint="specific absorption rate within exposure limits",
         mechanism="exposure-aware link-budget scheduler adapts transmit power to hold link margin",
         intervention="adaptive-power telemetry firmware with antenna tuning network",
         effect="reliable data link at maximum implant depth within SAR limits",
         fals="phantom link-budget sweep; packet error rate vs depth and power"),
    dict(domain="acoustic",
         device="CSF shunt system",
         failure_mode="OBSTRUCTION",
         failure="valve occlusion is detected only after symptoms",
         constraint="noninvasive outpatient-style detection",
         mechanism="acoustic transmission signature across the valve changes as the orifice narrows",
         intervention="bedside acoustic transducer pair with spectral classifier",
         effect="early noninvasive obstruction detection",
         fals="ex-vivo flow loop with staged obstructions; classifier AUC"),
    dict(domain="mri_nmr",
         device="implantable flow sensor",
         failure_mode="SENSOR_FAILURE",
         failure="no implantable flow measurement survives MRI environments",
         constraint="MR-conditional operation at 1.5T and 3T",
         mechanism="phase-contrast MR signal across a fixed local gradient encodes flow velocity",
         intervention="MR-visible flow encoding insert in the catheter wall",
         effect="flow quantification during standard imaging",
         fals="phantom flow scan; measured vs true flow rate"),
    dict(domain="enzyme_biocatalytic",
         device="CSF shunt system",
         failure_mode="ENCrustation",
         failure="protein and mineral deposition narrows the lumen",
         constraint="avoid chronic drug elution",
         mechanism="surface-immobilized hyaluronidase depolymerizes deposit-forming macromolecules at the lumen wall",
         intervention="enzymatic luminal coating on the proximal catheter",
         effect="reduced encrustation mass over dwell time",
         fals="incubated CSF-mimic circuit; deposit mass vs control"),
    dict(domain="phage_microbio",
         device="CSF shunt system",
         failure_mode="INFECTION",
         failure="Staphylococcus biofilm colonizes the catheter",
         constraint="avoid systemic antibiotics and resistance pressure",
         mechanism="co-immobilized lytic phage cocktail disrupts early biofilm on the outer surface",
         intervention="phage-functionalized catheter cuff",
         effect="lower biofilm colony-forming units in the first weeks",
         fals="in-vitro biofilm assay; CFU count vs untreated control"),
    dict(domain="ml_data",
         device="implantable sensor array",
         failure_mode="ALARM_FATIGUE",
         failure="threshold alarms fire late or not at all",
         constraint="run within implant compute budget",
         mechanism="on-device temporal model learns the patient baseline and flags deviation earlier than fixed thresholds",
         intervention="patient-adaptive anomaly detector on the sensor node",
         effect="earlier true alarms with fewer false positives",
         fals="retrospective labeled cohort; sensitivity at fixed false-alarm rate"),
    dict(domain="mechanical_structural",
         device="CSF shunt system",
         failure_mode="CATHETER_FRACTURE",
         failure="neck movement fatigues the catheter until it cracks",
         constraint="preserve kink resistance and flexibility",
         mechanism="strain-relief bellows redistribute bending strain away from the fixation point",
         intervention="segmented bellows catheter section near the anchor",
         effect="higher cycles-to-failure at the anchor point",
         fals="cyclic bend-to-failure rig; cycles vs straight control"),
    dict(domain="thermal",
         device="implantable neuromodulation lead",
         failure_mode="TISSUE_INJURY",
         failure="electrode heating damages surrounding tissue",
         constraint="keep local temperature rise below safety margin",
         mechanism="distributed current steering spreads dissipation across multiple contact sites",
         intervention="current-steering electrode switching pattern",
         effect="lower peak tissue temperature at equal therapy dose",
         fals="agar phantom thermography; peak delta-T vs monopolar control"),
    dict(domain="energy_harvesting",
         device="implantable sensor",
         failure_mode="POWER_DEPLETION",
         failure="primary cell exhausts before device end of life",
         constraint="harvest within safe biologic limits",
         mechanism="piezoelectric stack harvests arterial pulsation energy through a compliant coupling",
         intervention="pulsation-coupled piezoelectric energy harvester",
         effect="net positive energy balance at physiologic pulse pressure",
         fals="pulsatile pressure rig; harvested energy per cycle vs load"),
    dict(domain="energy_harvesting",
         device="implantable sensor",
         failure_mode="POWER_DEPLETION",
         failure="sensor sleeps to save power and misses events",
         constraint="energy autonomy without duty-cycle gaps",
         mechanism="thermoelectric gradient across the implant capsule trickle-charges the reservoir",
         intervention="thin-film thermoelectric liner in the capsule wall",
         effect="continuous sensing without sleep windows",
         fals="implant-mimic thermal gradient rig; charge rate vs standby draw"),
    dict(domain="optical_photonic",
         device="CSF shunt system",
         failure_mode="OBSTRUCTION",
         failure="distal obstruction is invisible to imaging",
         constraint="no ionizing radiation exposure",
         mechanism="fiber-coupled near-infrared backscatter drops when the distal lumen fills with debris",
         intervention="optical reflectometry fiber along the distal catheter",
         effect="localized obstruction detection without imaging",
         fals="staged-obstruction optical bench; reflectance vs blockage position"),
    dict(domain="mechanical_structural",
         device="implantable valve",
         failure_mode="SETTING_DRIFT",
         failure="valve pressure setting drifts after MRI exposure",
         constraint="MR-conditional mechanical stability",
         mechanism="ferromagnetic-free actuator with mechanical detent resists magnetically induced repositioning",
         intervention="detented ceramic valve actuator",
         effect="setting retention across MR exposure cycles",
         fals="3T exposure rig; setting deviation vs exposure count"),
]


def build_benchmark_envelope(spec: Dict[str, Any], idx: int,
                             prefix: str = "coder2-bench") -> Candidate:
    """One survivor envelope per benchmark input (SYNTHETIC_BENCHMARK_INPUT).

    prefix separates the identity universes of the committed benchmark
    runs (coder2-bench) from the blind runs (coder2-blind) so the two
    sets' ids can never collide in cross-set contamination checks.
    """
    problem_id = f"{prefix}:{idx:02d}:{spec['domain']}"
    problem = {
        "problem_id": problem_id, "device": spec["device"],
        "failure_mode": spec["failure_mode"], "failure": spec["failure"],
        "constraint": spec["constraint"],
    }
    env = Candidate(problem=problem, problem_id=problem_id)
    # 5 evidence items per input = corpus floor density (gold min = 5,
    # real-run retrieval = 5-7). One-item fixtures would under-represent
    # what the real retrieval stage produces and make the EVIDENCE_DENSITY
    # dimension measure fixture poverty instead of pipeline behavior.
    ev_base = {
        "source_type": "scientific_paper", "source": "Coder2BenchmarkFixture",
        "publication_date": "2021-06-01",
        "content_hash": sha256_obj({"b": f"{prefix}-{idx:02d}"}),
    }
    ev = dict(ev_base, **{
        "id": f"{prefix}-evidence-{idx:02d}",
        "source_id": f"BENCH-{idx:02d}",
        "source_uri": f"https://{prefix}.invalid/{idx:02d}",
        "title": f"Benchmark fixture study {idx:02d} ({spec['domain']})",
        "abstract": (
            f"In a controlled model, the {spec['mechanism']} was "
            f"demonstrated with the {spec['intervention']}, producing "
            f"{spec['effect']}. Extended observation text follows so the "
            f"abstract carries realistic length for truncation and "
            f"contamination checks: repeated trials held the measured "
            f"behavior stable across varying load and posture conditions "
            f"throughout the full observation window."),
        "doi": f"10.0000/coder2-bench.{idx:02d}",
    })
    supp = []
    for s_i in range(2, 6):
        supp.append(dict(ev_base, **{
            "id": f"{prefix}-evidence-{idx:02d}-{s_i}",
            "source_id": f"BENCH-{idx:02d}-{s_i}",
            "source_uri": f"https://{prefix}.invalid/{idx:02d}/{s_i}",
            "title": f"Benchmark fixture supporting study "
                     f"{idx:02d}-{s_i} ({spec['domain']})",
            "abstract": (
                f"Supporting benchmark observation {s_i} for the "
                f"{spec['domain']} fixture: the reported behavior of the "
                f"{spec['device']} under {spec['failure_mode'].lower()} "
                f"conditions remained consistent with the primary fixture "
                f"study across repeated measurement series."),
            "doi": f"10.0000/coder2-bench.{idx:02d}.{s_i}",
            "content_hash": sha256_obj({"b": f"{prefix}-{idx:02d}-{s_i}"}),
        }))
    env.evidence = [ev] + supp
    env.evidence_ids = [e["id"] for e in env.evidence]
    freeze = {
        "run_id": f"coder2:{prefix}", "problem_id": problem_id,
        "frozen_at": "2026-01-01T00:00:00Z",
        "evidence_count": len(env.evidence),
        "custody_records": [{"record_id": e["id"],
                             "content_hash": e["content_hash"]}
                            for e in env.evidence],
        "hash_verification_all_pass": True,
        "_fixture_epistemic_class": "SYNTHETIC_BENCHMARK_INPUT"}
    freeze["snapshot_hash"] = sha256_obj(freeze)
    env.provenance = {"evidence_freeze": freeze}
    raw = {
        "candidate_id": f"cand:{prefix}-{idx:02d}",
        "falsification_test": spec["fals"],
        "mechanism_source_span": spec["mechanism"],
        "source_evidence": {"source_id": ev["id"],
                            "source_hash": ev["content_hash"],
                            "source_span": ev["abstract"][:500],
                            "source_title": ev["title"]},
        "mechanism": spec["mechanism"],
        "intervention": spec["intervention"],
        "expected_effect": spec["effect"],
        "_fixture_epistemic_class": "SYNTHETIC_BENCHMARK_INPUT",
    }
    env.mechanism_map = {
        "mechanism": raw["mechanism"], "intervention": raw["intervention"],
        "expected_effect": raw["expected_effect"],
        "falsification_test": raw["falsification_test"],
        "mechanism_source_span": raw["mechanism_source_span"],
        "raw_candidate": raw}
    env.attack_results = {
        "overall": "PASS", "killed_count": 0,
        "reason": "synthetic benchmark pass",
        "attacks": {d: "SURVIVED" for d in (
            "unsupported_mechanism", "weak_transfer", "obvious_combination",
            "prior_art", "contradiction", "boundary_failure",
            "engineering_infeasibility", "regulatory_incompatibility")},
        "invalid_dimensions": [], "v4_corrections_applied": [],
        "prior_art_state": "NO_MATCH_FOUND", "evidence_verified": True,
        "prompt_hash": "0" * 16, "output_hash": "0" * 16,
        "timestamp": "2026-01-01T00:00:00Z",
        "_fixture_epistemic_class": "SYNTHETIC_BENCHMARK_INPUT"}
    env.prior_art = {"prior_art_status": "NO_MATCH_FOUND",
                     "legacy_status": "NO_MATCHING_EVIDENCE_FOUND",
                     "state_vocabulary": "classify/v4_corrections"}
    env.collision_results = {
        "novelty_risk": "SEARCHED_NO_DIRECT_TITLE_MATCH",
        "patent": {"hits": [], "hit_count": 0, "source_errors": []}}
    for stage, adapter in CHAIN_PLAN:
        env.run_stage(stage, adapter.capability_id, adapter.module_path,
                      adapter.canonical_fn, adapter().execute, env, CTX)
    return env


def run_benchmark(out_root: Path, limit: int = 0,
                  keep_runs: bool = False) -> Dict[str, Any]:
    """Generate benchmark runs. limit=0 means all 15."""
    from .corpus_metrics import REQUIRED_PDFS  # noqa: F401
    runs_root = out_root / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)

    inputs = BENCHMARK_INPUTS[:limit] if limit else BENCHMARK_INPUTS
    run_dirs: List[Path] = []
    for idx, spec in enumerate(inputs, start=1):
        env = build_benchmark_envelope(spec, idx)
        run_dir = runs_root / f"BENCH_{idx:02d}"
        if run_dir.exists():
            shutil.rmtree(run_dir)
        run_id = f"coder2-benchmark:{idx:02d}"
        run = EngineRun(env.problem, str(run_dir), run_id=run_id,
                        package_number=f"8{idx:02d}")
        run.env = env
        run.rehearsal = True
        run._post_rank_pipeline({"run_id": run_id})
        # persist the harness's own input records in the standard run-dir
        # format (same records the full conductor writes): the audits anchor
        # provenance and replay verification on these
        (run_dir / "problem.json").write_text(
            json.dumps(env.problem, indent=1, ensure_ascii=False),
            encoding="utf-8")
        (run_dir / "candidate_envelope.json").write_text(
            json.dumps(env.to_dict(), indent=1, ensure_ascii=False,
                       default=str), encoding="utf-8")
        release = build_discovery_release(
            run_dir, run_id=run_id, problem_id=env.problem_id, env=env,
            spec=run._spec, eng=run._eng, package_report=run.package_report,
            failure_reason=run.package_failure)
        write_discovery_release(run_dir, release)
        run_dirs.append(run_dir)
        status = (release or {}).get("status", "?")
        print(f"[{idx:02d}/15] {spec['domain']:22s} release={status} "
              f"dir={run_dir.name}")

    return {"run_dirs": [str(rd) for rd in run_dirs],
            "runs_root": str(runs_root)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="artifacts/benchmark/generated")
    ap.add_argument("--contract",
                    default="artifacts/benchmark/"
                            "ENGINEERING_DEPTH_CONTRACT.json")
    ap.add_argument("--profile",
                    default="artifacts/benchmark/"
                            "BENCHMARK_DOSSIER_PROFILE.json")
    args = ap.parse_args()

    out_root = Path(args.out)
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))

    info = run_benchmark(out_root)
    benchmark = audit_runner.audit_batch(
        [Path(p) for p in info["run_dirs"]],
        contract=contract, profile=profile, expected_count=15,
        out_dir=out_root)

    summary_path = out_root / "BENCHMARK_RUN_SUMMARY.json"
    summary_path.write_text(json.dumps(info, indent=1), encoding="utf-8")

    print()
    print("=" * 70)
    print("CODER2 AUTOMATED DOSSIER BENCHMARK — 15 SURVIVOR INPUTS")
    print("=" * 70)
    print(f"runs input:         {benchmark['runs_input']}")
    print(f"released+audited:   {benchmark['runs_released_and_audited']}")
    print(f"engine-rejected:    {benchmark['engine_rejected_count']} "
          f"(engine's own E15-H gate refused release)")
    print(f"completeness:       {benchmark['completeness_ok']}")
    print(f"verdict counts:     {benchmark['verdict_counts']}")
    print(f"contamination:      {benchmark['contamination']['verdict']} "
          f"({benchmark['contamination']['violation_count']} violations)")
    print(f"V&V violations:     "
          f"{benchmark['vv_separation_audit']['total_violations']}")
    print(f"BATCH VERDICT:      {benchmark['batch_verdict']}")
    from collections import Counter
    dim_fails = Counter()
    for r in benchmark["runs"]:
        for d in r.get("failing_dimensions") or []:
            dim_fails[d] += 1
    if dim_fails:
        print("failing dimensions (across runs):")
        for d, c in dim_fails.most_common():
            print(f"  {d:32s} {c}/15")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

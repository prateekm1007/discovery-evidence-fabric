"""Medical Device Discovery Corpus V2 — Large-scale autonomous generation."""
from __future__ import annotations
import json, hashlib, re, ssl, time, os, sys
import urllib.request, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))
from discovery_fabric.a2.retrieve import search_europe_pmc
from discovery_fabric.a2.synthesize import llm_chat, SYNTHESIS_PROMPT, parse_candidate
from discovery_fabric.a2.verify import verify_evidence
from discovery_fabric.a2.prior_art import search_prior_art
from discovery_fabric.a2.adversarial import adversarial_challenge
from discovery_fabric.a2.classify import classify

FROZEN_MODEL = "deepseek/deepseek-v4-flash-0731"
OUTPUT = Path("corpus_v2")
for s in ["sources","problems","attempts","candidates","rejected","manifests","ledgers","reports","snapshots"]:
    (OUTPUT/s).mkdir(parents=True, exist_ok=True)

def _hash(s): return hashlib.sha256(s.encode()).hexdigest()[:16]
def _full(s): return hashlib.sha256(s.encode()).hexdigest()

# ============================================================
# LARGE PROBLEM UNIVERSE — device × failure_mode × query_type
# ============================================================

DEVICES = [
    # Implantables - Orthopedic
    "Hip Implant","Knee Implant","Spinal Fusion Device","Shoulder Implant","Dental Implant","Elbow Implant","Ankle Implant",
    # Implantables - Cardiovascular
    "Cardiac Pacemaker","Coronary Stent","Heart Valve","Implantable Defibrillator","Ventricular Assist Device",
    # Implantables - Neurostimulation
    "Deep Brain Stimulator","Vagus Nerve Stimulator","Cochlear Implant","Spinal Cord Stimulator","Sacral Nerve Stimulator",
    # Implantables - Ophthalmic
    "Intraocular Lens","Glau Drainage Device","Corneal Implant",
    # Diagnostics - Imaging
    "CT Scanner","MRI System","Ultrasound System","X-Ray System","PET Scanner",
    # Diagnostics - Biosensors
    "Continuous Glucose Monitor","Blood Glucose Monitor","Pulse Oximeter","ECG Monitor","Blood Pressure Monitor",
    # Diagnostics - Point of Care
    "Point-of-Care Test Device","Lateral Flow Device","Portable Ultrasound",
    # Surgical - Robotics
    "Robotic Surgical System","Surgical Robot Arm",
    # Surgical - Minimally Invasive
    "Laparoscope","Endoscope","Arthroscope","Surgical Stapler","Trocar",
    # Surgical - Energy-based
    "Electrosurgical Unit","Laser Surgical Device","Ultrasonic Surgical Device",
    # Surgical - Navigation
    "Surgical Navigation System","Robotic Navigation System",
    # Wearables
    "Cardiac Monitor Patch","EEG Headset","Smartwatch Sensor","Fitness Tracker","Wearable ECG",
    # Biomaterials
    "Antimicrobial Coating","Drug-Eluting Stent","Hydrogel Coating","Bioceramic Coating","Bone Cement","Wound Dressing",
    # Neurotechnology
    "Neural Interface","BCI Electrode","EEG Electrode","Neurofeedback Device","Retinal Prosthesis",
]

FAILURE_MODES = [
    "WEAR","FATIGUE","CORROSION","FRACTURE","INFECTION","THROMBOSIS","BATTERY_FAILURE",
    "THERMAL_DAMAGE","SENSOR_DRIFT","DELAMINATION","BIOCOMPATIBILITY","STERILIZATION",
    "SIGNAL_DEGRADATION","FALSE_POSITIVES","FALSE_NEGATIVES","MANUFACTURING_VARIABILITY",
    "MECHANICAL_FAILURE","DEGRADATION","LEAKAGE","MIGRATION",
]

QUERY_TYPES = [
    "{device} {failure} mechanism",
    "{failure} mechanism material science",
    "{device} {failure} prevention solution",
    "{failure} engineering mechanism measured effect",
    "{device} {failure} coating surface treatment",
    "{device} {failure} material design improvement",
]

def generate_problems():
    """Generate problems: device × failure_mode, with varied queries."""
    problems = []
    pid = 0
    for device in DEVICES:
        for fm in FAILURE_MODES:
            pid += 1
            # Select query type based on pid for variety
            qt = QUERY_TYPES[pid % len(QUERY_TYPES)]
            fm_lower = fm.lower().replace("_"," ")
            query = qt.format(device=device.lower(), failure=fm_lower)
            problems.append({
                "problem_id": f"v2_{pid:05d}",
                "device": device,
                "failure_mode": fm,
                "failure": f"{device} {fm_lower} causing device malfunction",
                "constraint": f"Must maintain {device.lower()} function within clinical specifications",
                "query": query,
            })
    print(f"Generated {len(problems)} problems ({len(DEVICES)} devices × {len(FAILURE_MODES)} failure modes)")
    return problems

# ============================================================
# RELEVANCE GATE
# ============================================================

def classify_relevance(paper, problem):
    title = paper.get("title","").lower()
    abstract = paper.get("abstract","")[:500].lower()
    text = title + " " + abstract
    device = problem["device"].lower()
    fm = problem["failure_mode"].lower().replace("_"," ")
    device_words = [w for w in device.split() if len(w) > 3]
    fm_words = [w for w in fm.split() if len(w) > 3]
    device_match = any(w in text for w in device_words)
    fm_match = any(w in text for w in fm_words)
    medical = any(t in text for t in ["implant","surgical","clinical","patient","medical","device","biomedical",
        "orthopedic","cardiac","neuro","sensor","scanner","stent","stapler","coating","electrode","monitor"])
    irrelevant = any(t in text for t in ["urban","road","collapse","soil","wetting","pavement","traffic",
        "electronic cigarette","tobacco","smoking","vaping","cigarette"])
    if irrelevant: return "IRRELEVANT"
    if device_match and (fm_match or medical): return "RELEVANT"
    if device_match or fm_match or medical: return "PARTIALLY_RELEVANT"
    return "IRRELEVANT"

# ============================================================
# A2 PIPELINE (with relevance gate)
# ============================================================

def run_a2(problem):
    pid = problem["problem_id"]
    evidence = search_europe_pmc(problem["query"], per_page=5)
    time.sleep(1.0)
    if not evidence:
        return {"problem_id":pid,"final_status":"REJECTED","reason":"no evidence",
                "device":problem["device"],"failure_mode":problem["failure_mode"],
                "domain":"unknown","relevance":"NO_EVIDENCE","epistemic_state":"OBSERVED"}
    
    # Relevance gate
    relevant = []
    for p in evidence:
        rel = classify_relevance(p, problem)
        p["relevance"] = rel
        if rel != "IRRELEVANT":
            relevant.append(p)
    
    if not relevant:
        return {"problem_id":pid,"final_status":"REJECTED","reason":"all sources irrelevant",
                "device":problem["device"],"failure_mode":problem["failure_mode"],
                "domain":"unknown","relevance":"ALL_IRRELEVANT","epistemic_state":"OBSERVED",
                "retrieval_count":len(evidence)}
    
    paper = relevant[0]
    
    # A2 synthesis
    prompt = SYNTHESIS_PROMPT.format(
        device=problem["device"], failure=problem["failure"], constraint=problem["constraint"],
        title=paper["title"], abstract=paper["abstract"][:1200])
    resp = llm_chat(prompt, system="You are a medical device engineer.")
    if not resp:
        return {"problem_id":pid,"final_status":"REJECTED","reason":"LLM failed",
                "device":problem["device"],"failure_mode":problem["failure_mode"],
                "relevance":paper["relevance"],"epistemic_state":"OBSERVED","retrieval_count":len(evidence)}
    
    parsed = parse_candidate(resp)
    if not parsed.get("intervention"):
        return {"problem_id":pid,"final_status":"REJECTED","reason":"no intervention",
                "device":problem["device"],"failure_mode":problem["failure_mode"],
                "relevance":paper["relevance"],"epistemic_state":"OBSERVED","retrieval_count":len(evidence)}
    
    candidate = {
        "candidate_id":f"cand:{pid}:{_hash(resp[:200])}","problem_id":pid,
        "device":problem["device"],"failure_mode":problem["failure_mode"],
        "failure":problem["failure"],"constraint":problem["constraint"],
        "mechanism":parsed.get("mechanism",""),"intervention":parsed.get("intervention",""),
        "expected_effect":parsed.get("expected_effect",""),
        "falsification_test":parsed.get("falsification_test",""),
        "mechanism_source_span":parsed.get("mechanism_source_span",""),
        "source_evidence":{"source_id":paper["id"],"source_hash":paper["content_hash"],
            "source_title":paper["title"],"source_span":paper["abstract"][:2000],
            "retrieval_timestamp":paper["retrieval_timestamp"],"relevance":paper["relevance"]},
        "model":FROZEN_MODEL,"prompt_hash":_hash(SYNTHESIS_PROMPT),
        "input_hash":_hash(prompt),"output_hash":_hash(resp),
        "synthesis_timestamp":datetime.now(timezone.utc).isoformat(),
        "retrieval_count":len(evidence),"relevance":paper["relevance"],
    }
    
    verification = verify_evidence(candidate, [{"abstract": paper["abstract"]}])
    prior_art = search_prior_art(candidate["intervention"], problem["device"])
    adversarial = adversarial_challenge(candidate)
    classification = classify(candidate, verification, prior_art, adversarial)
    
    return {**candidate,"verification":verification,"prior_art":prior_art,
            "adversarial":adversarial,"classification":classification,
            "final_status":classification["final_status"],
            "epistemic_state":classification["epistemic_state"]}

# ============================================================
# MAIN
# ============================================================

def main():
    print("="*60)
    print("MEDICAL DEVICE DISCOVERY CORPUS V2")
    print("="*60)
    print(f"Model: {FROZEN_MODEL}, temp=0.0, max_tokens=8000")
    print(f"Relevance gate: ACTIVE")
    print(f"A2 contract: FROZEN — no threshold tuning")
    
    problems = generate_problems()
    
    # Load progress
    progress_path = OUTPUT / "corpus_v2_progress.json"
    if progress_path.exists():
        results = json.loads(progress_path.read_text())
        print(f"Resumed from {len(results)} candidates")
    else:
        results = []
    
    # Run A2 for each problem
    for problem in problems:
        if any(r["problem_id"] == problem["problem_id"] for r in results):
            continue
        pid = problem["problem_id"]
        print(f"\n  [{pid}] {problem['device']} ({problem['failure_mode']})")
        try:
            result = run_a2(problem)
            results.append(result)
            progress_path.write_text(json.dumps(results, indent=2, default=str))
            
            status = result["final_status"]
            marker = " ★ INVENTION_CANDIDATE" if status == "INVENTION_CANDIDATE" else ""
            rel = result.get("relevance","?")
            print(f"    rel={rel} → {status}{marker}")
            
            # Save individual files
            if status == "INVENTION_CANDIDATE":
                (OUTPUT/"candidates"/f"{pid}.json").write_text(json.dumps(result, indent=2, default=str))
            else:
                (OUTPUT/"rejected"/f"{pid}.json").write_text(json.dumps(result, indent=2, default=str))
            
            # Check stop conditions
            survivors = sum(1 for r in results if r["final_status"] == "INVENTION_CANDIDATE")
            if survivors >= 100:
                print(f"\n  STOP: 100 invention candidates reached!")
                break
        except Exception as e:
            print(f"    ERROR: {e}")
            results.append({"problem_id":pid,"final_status":"ERROR","error":str(e)[:100],
                           "device":problem["device"],"failure_mode":problem["failure_mode"]})
            progress_path.write_text(json.dumps(results, indent=2, default=str))
    
    # Stats
    n = len(results)
    status_dist = Counter(r["final_status"] for r in results)
    relevance_dist = Counter(r.get("relevance","?") for r in results)
    device_dist = Counter(r.get("device","?") for r in results)
    fm_dist = Counter(r.get("failure_mode","?") for r in results)
    survivors = [r for r in results if r["final_status"] == "INVENTION_CANDIDATE"]
    rejected = [r for r in results if r["final_status"] == "REJECTED"]
    reject_reasons = Counter()
    for r in rejected:
        reason = r.get("reason", r.get("classification",{}).get("reason","unknown"))
        reject_reasons[reason[:60]] += 1
    
    print(f"\n{'='*60}")
    print("CORPUS V2 STATISTICS")
    print(f"{'='*60}")
    print(f"  Total candidates: {n}")
    print(f"  INVENTION_CANDIDATE: {len(survivors)}")
    print(f"  REJECTED: {len(rejected)}")
    print(f"  Survival rate: {len(survivors)/n:.1%}" if n else "N/A")
    print(f"  Status: {dict(status_dist)}")
    print(f"  Relevance: {dict(relevance_dist)}")
    print(f"  Rejection reasons: {dict(reject_reasons)}")
    
    # Write manifest
    all_hash = _full(json.dumps(results, sort_keys=True, default=str))
    commit = os.popen("git rev-parse HEAD 2>/dev/null").read().strip() or "unknown"
    manifest = {
        "corpus_version":"MEDICAL_DEVICE_CORPUS_V2","generated_at":datetime.now(timezone.utc).isoformat(),
        "model":FROZEN_MODEL,"temperature":0.0,"max_tokens":8000,"relevance_gate":"ACTIVE",
        "total_problems_target":len(problems),"total_candidates":n,
        "total_survivors":len(survivors),"total_rejected":len(rejected),
        "survival_rate":round(len(survivors)/n,4) if n else 0,
        "status_distribution":dict(status_dist),"relevance_distribution":dict(relevance_dist),
        "device_distribution":dict(device_dist),"failure_mode_distribution":dict(fm_dist),
        "rejection_reasons":dict(reject_reasons),"code_commit":commit,"corpus_root_hash":all_hash,
    }
    (OUTPUT/"CORPUS_MANIFEST.json").write_text(json.dumps(manifest, indent=2, default=str))
    (OUTPUT/"CORPUS_ROOT_HASH").write_text(all_hash)
    
    md = f"""# Medical Device Discovery Corpus V2

## TRUE NUMBERS

| Metric | Value |
|--------|-------|
| Total problems target | {len(problems)} |
| Total candidates | {n} |
| INVENTION_CANDIDATE | {len(survivors)} |
| REJECTED | {len(rejected)} |
| Survival rate | {len(survivors)/n:.1% if n else 'N/A'} |

## Status Distribution
{json.dumps(dict(status_dist), indent=2)}

## Relevance Distribution
{json.dumps(dict(relevance_dist), indent=2)}

## Rejection Reasons
{json.dumps(dict(reject_reasons), indent=2)}

## Model: {FROZEN_MODEL}
## Temperature: 0.0
## Max tokens: 8000
## Relevance gate: ACTIVE
## Corpus Root Hash: {all_hash}
## Code Commit: {commit}
"""
    (OUTPUT/"CORPUS_REPORT.md").write_text(md)
    
    auditor_md = f"""# Auditor Package — Corpus V2

## Corpus Root Hash
{all_hash}

## Source Universe
- Connector: Europe PMC (LIVE)
- Relevance gate: ACTIVE (IRRELEVANT sources blocked)

## Candidate Universe
- Total: {n}
- Survivors: {len(survivors)}
- Rejected: {len(rejected)}

## Generation Protocol
- A2: retrieve → relevance gate → freeze → synthesize → verify → prior-art → adversarial → classify
- Model: {FROZEN_MODEL}, temp=0.0, max_tokens=8000
- A2 contract FROZEN — no threshold tuning

## Sampling
- Survivors: corpus_v2/candidates/
- Rejected: corpus_v2/rejected/
- Progress: corpus_v2/corpus_v2_progress.json

## Code Commit: {commit}
"""
    (OUTPUT/"AUDITOR_PACKAGE.md").write_text(auditor_md)
    print(f"\nArtifacts: {OUTPUT}/")

if __name__ == "__main__":
    main()

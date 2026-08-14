"""Large-scale medical-device discovery corpus generator."""
from __future__ import annotations
import json, hashlib, re, ssl, time, os, sys
import urllib.request, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))
from discovery_fabric.a2.retrieve import search_europe_pmc
from discovery_fabric.a2.synthesize import synthesize, llm_chat, SYNTHESIS_PROMPT, parse_candidate
from discovery_fabric.a2.verify import verify_evidence
from discovery_fabric.a2.prior_art import search_prior_art
from discovery_fabric.a2.adversarial import adversarial_challenge
from discovery_fabric.a2.classify import classify

FROZEN_MODEL = "deepseek/deepseek-v4-flash-0731"
OUTPUT_DIR = Path("corpus")
OUTPUT_DIR.mkdir(exist_ok=True)
for s in ["sources","problems","candidates","rejected","manifests","ledgers","reports"]:
    (OUTPUT_DIR/s).mkdir(exist_ok=True)

def _hash(s): return hashlib.sha256(s.encode()).hexdigest()[:16]
def _full(s): return hashlib.sha256(s.encode()).hexdigest()

DOMAINS = {
    "implantables_orthopedic": {"devices":["Hip Implant","Knee Implant","Spinal Fusion Device","Shoulder Implant","Dental Implant"],
        "failure_modes":["WEAR","MECHANICAL_FAILURE","CORROSION","INFECTION","FATIGUE"]},
    "implantables_cardiovascular": {"devices":["Cardiac Pacemaker","Coronary Stent","Heart Valve","Implantable Defibrillator"],
        "failure_modes":["BATTERY_FAILURE","THROMBOSIS","MECHANICAL_FAILURE","INFECTION"]},
    "implantables_neurostimulation": {"devices":["Deep Brain Stimulator","Vagus Nerve Stimulator","Cochlear Implant","Spinal Cord Stimulator"],
        "failure_modes":["BATTERY_FAILURE","MECHANICAL_FAILURE","SENSOR_DRIFT","INFECTION"]},
    "diagnostics_imaging": {"devices":["CT Scanner","MRI System","Ultrasound System","X-Ray System"],
        "failure_modes":["THERMAL_DAMAGE","MECHANICAL_FAILURE","DEGRADATION"]},
    "diagnostics_biosensors": {"devices":["Continuous Glucose Monitor","Blood Glucose Monitor","Pulse Oximeter","ECG Monitor"],
        "failure_modes":["SENSOR_DRIFT","DEGRADATION","CORROSION"]},
    "surgical_robotics": {"devices":["Robotic Surgical System","Surgical Stapler","Electrosurgical Unit","Laparoscope"],
        "failure_modes":["MECHANICAL_FAILURE","THERMAL_DAMAGE","INFECTION"]},
    "wearables_sensing": {"devices":["Cardiac Monitor Patch","CGM Patch","EEG Headset","Smartwatch Sensor"],
        "failure_modes":["SENSOR_DRIFT","DEGRADATION","BATTERY_FAILURE"]},
    "biomaterials_coatings": {"devices":["Antimicrobial Coating","Drug-Eluting Stent","Hydrogel Coating","Bioceramic Coating"],
        "failure_modes":["DEGRADATION","INFECTION","CORROSION"]},
    "neurotechnology_interfaces": {"devices":["Neural Interface","BCI Electrode","EEG Electrode","Neurofeedback Device"],
        "failure_modes":["SENSOR_DRIFT","DEGRADATION","MECHANICAL_FAILURE"]},
}

def generate_problems():
    problems = []
    pid = 0
    for domain, config in DOMAINS.items():
        for device in config["devices"]:
            for fm in config["failure_modes"]:
                pid += 1
                problems.append({"problem_id":f"p{pid:04d}","domain":domain,"device":device,
                    "failure_mode":fm,"failure":f"{device} {fm.lower().replace('_',' ')} causing malfunction",
                    "constraint":f"Must maintain {device.lower()} function within clinical specifications"})
    print(f"Generated {len(problems)} problems across {len(DOMAINS)} domains")
    return problems

def run_a2_for_problem(problem):
    pid = problem["problem_id"]
    query = f"{problem['device']} {problem['failure_mode'].lower().replace('_',' ')} mechanism"
    evidence = search_europe_pmc(query, per_page=3)
    time.sleep(1.0)
    if not evidence:
        return {"problem_id":pid,"final_status":"REJECTED","reason":"no evidence retrieved",
                "epistemic_state":"OBSERVED","domain":problem["domain"],"device":problem["device"],"failure_mode":problem["failure_mode"]}
    snapshot_hash = _full(json.dumps(evidence, sort_keys=True))
    paper = evidence[0]
    prompt = SYNTHESIS_PROMPT.format(device=problem["device"],failure=problem["failure"],
        constraint=problem["constraint"],title=paper["title"],abstract=paper["abstract"][:1200])
    resp = llm_chat(prompt, system="You are a medical device engineer.")
    if not resp:
        return {"problem_id":pid,"final_status":"REJECTED","reason":"LLM synthesis failed",
                "epistemic_state":"OBSERVED","domain":problem["domain"],"device":problem["device"],"failure_mode":problem["failure_mode"]}
    parsed = parse_candidate(resp)
    if not parsed.get("intervention"):
        return {"problem_id":pid,"final_status":"REJECTED","reason":"no intervention",
                "epistemic_state":"OBSERVED","domain":problem["domain"],"device":problem["device"],"failure_mode":problem["failure_mode"]}
    candidate = {"candidate_id":f"cand:{pid}:{_hash(resp[:200])}","problem_id":pid,"domain":problem["domain"],
        "device":problem["device"],"failure_mode":problem["failure_mode"],"failure":problem["failure"],
        "constraint":problem["constraint"],"mechanism":parsed.get("mechanism",""),
        "intervention":parsed.get("intervention",""),"expected_effect":parsed.get("expected_effect",""),
        "falsification_test":parsed.get("falsification_test",""),"mechanism_source_span":parsed.get("mechanism_source_span",""),
        "source_evidence":{"source_id":paper["id"],"source_hash":paper["content_hash"],"source_title":paper["title"],
            "source_span":paper["abstract"][:500],"retrieval_timestamp":paper["retrieval_timestamp"]},
        "model":FROZEN_MODEL,"prompt_hash":_hash(SYNTHESIS_PROMPT),"input_hash":_hash(prompt),
        "output_hash":_hash(resp),"synthesis_timestamp":datetime.now(timezone.utc).isoformat(),"snapshot_hash":snapshot_hash}
    verification = verify_evidence(candidate, evidence)
    prior_art = search_prior_art(candidate["intervention"], problem["device"])
    adversarial = adversarial_challenge(candidate)
    classification = classify(candidate, verification, prior_art, adversarial)
    return {**candidate,"verification":verification,"prior_art":prior_art,"adversarial":adversarial,
            "classification":classification,"final_status":classification["final_status"],
            "epistemic_state":classification["epistemic_state"]}

def main():
    print("="*60)
    print("MEDICAL DEVICE DISCOVERY CORPUS GENERATION")
    print("="*60)
    print(f"Model: {FROZEN_MODEL}")
    problems = generate_problems()
    progress_path = OUTPUT_DIR / "corpus_progress.json"
    results = json.loads(progress_path.read_text()) if progress_path.exists() else []
    if results: print(f"Resumed from {len(results)} candidates")
    
    for problem in problems:
        if any(r["problem_id"]==problem["problem_id"] for r in results): continue
        pid = problem["problem_id"]
        print(f"\n  [{pid}] {problem['device']} ({problem['failure_mode']})")
        try:
            result = run_a2_for_problem(problem)
            results.append(result)
            progress_path.write_text(json.dumps(results, indent=2, default=str))
            status = result["final_status"]
            marker = " ★" if status=="INVENTION_CANDIDATE" else ""
            print(f"    → {status}{marker}")
            if status=="INVENTION_CANDIDATE":
                (OUTPUT_DIR/"candidates"/f"{pid}.json").write_text(json.dumps(result,indent=2,default=str))
            else:
                (OUTPUT_DIR/"rejected"/f"{pid}.json").write_text(json.dumps(result,indent=2,default=str))
        except Exception as e:
            print(f"    ERROR: {e}")
            results.append({"problem_id":pid,"final_status":"ERROR","error":str(e),
                           "domain":problem["domain"],"device":problem["device"],"failure_mode":problem["failure_mode"]})
            progress_path.write_text(json.dumps(results,indent=2,default=str))
    
    # Stats
    n = len(results)
    status_dist = Counter(r["final_status"] for r in results)
    domain_dist = Counter(r.get("domain","unknown") for r in results)
    survivors = [r for r in results if r["final_status"]=="INVENTION_CANDIDATE"]
    rejected = [r for r in results if r["final_status"]=="REJECTED"]
    reject_reasons = Counter()
    for r in rejected:
        reason = r.get("reason", r.get("classification",{}).get("reason","unknown"))
        reject_reasons[reason[:60]] += 1
    
    print(f"\n{'='*60}\nCORPUS STATISTICS\n{'='*60}")
    print(f"  Total: {n}, Survivors: {len(survivors)}, Rejected: {len(rejected)}")
    print(f"  Survival rate: {len(survivors)/n:.1%}" if n else "N/A")
    print(f"  Status: {dict(status_dist)}")
    print(f"  Domains: {dict(domain_dist)}")
    print(f"  Rejection reasons: {dict(reject_reasons)}")
    
    all_results_hash = _full(json.dumps(results, sort_keys=True, default=str))
    commit = os.popen("git rev-parse HEAD 2>/dev/null").read().strip() or "unknown"
    manifest = {"corpus_version":"MEDICAL_DEVICE_CORPUS_V1","generated_at":datetime.now(timezone.utc).isoformat(),
        "model":FROZEN_MODEL,"total_problems":len(problems),"total_candidates":n,
        "total_survivors":len(survivors),"total_rejected":len(rejected),
        "survival_rate":round(len(survivors)/n,4) if n else 0,
        "status_distribution":dict(status_dist),"domain_distribution":dict(domain_dist),
        "rejection_reasons":dict(reject_reasons),"code_commit":commit,"corpus_root_hash":all_results_hash}
    (OUTPUT_DIR/"CORPUS_MANIFEST.json").write_text(json.dumps(manifest,indent=2,default=str))
    (OUTPUT_DIR/"CORPUS_ROOT_HASH").write_text(all_results_hash)
    
    md = f"""# Medical Device Discovery Corpus V1

## Statistics
- Total problems: {len(problems)}
- Total candidates: {n}
- INVENTION_CANDIDATE: {len(survivors)}
- REJECTED: {len(rejected)}
- Survival rate: {len(survivors)/n:.1% if n else 'N/A'}

## Domain Distribution
{json.dumps(dict(domain_dist), indent=2)}

## Rejection Reasons
{json.dumps(dict(reject_reasons), indent=2)}

## Model: {FROZEN_MODEL}
## Corpus Root Hash: {all_results_hash}
## Code Commit: {commit}
"""
    (OUTPUT_DIR/"CORPUS_REPORT.md").write_text(md)
    
    auditor_md = f"""# Auditor Package

## Corpus Root Hash
{all_results_hash}

## Source Universe
- Connector: Europe PMC (LIVE)

## Candidate Universe
- Total: {n}, Survivors: {len(survivors)}, Rejected: {len(rejected)}

## Generation Protocol
- A2: retrieve → freeze → synthesize → verify → prior-art → adversarial → classify
- Model: {FROZEN_MODEL}, temp=0.3
- Prompt hash: {_hash(SYNTHESIS_PROMPT)}

## Sampling
- Survivors: corpus/candidates/
- Rejected: corpus/rejected/
- Sources: corpus/corpus_progress.json (source_evidence fields)

## Code Commit: {commit}
"""
    (OUTPUT_DIR/"AUDITOR_PACKAGE.md").write_text(auditor_md)
    print(f"\nArtifacts in {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()

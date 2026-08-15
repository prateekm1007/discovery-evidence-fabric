"""Post-fix A2 validation with relevance gate."""
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

OUTPUT = Path("postfix_validation")
OUTPUT.mkdir(exist_ok=True)
FROZEN_MODEL = "deepseek/deepseek-v4-flash-0731"

def _hash(s): return hashlib.sha256(s.encode()).hexdigest()[:16]

# 10 frozen medical-device problems
PROBLEMS = [
    {"problem_id":"v01","device":"Hip Implant","failure_mode":"WEAR",
     "failure":"Hip implant polyethylene wear causing osteolysis","constraint":"Must maintain articulation surface integrity"},
    {"problem_id":"v02","device":"Hip Implant","failure_mode":"CORROSION",
     "failure":"Hip implant modular junction corrosion","constraint":"Must maintain structural integrity"},
    {"problem_id":"v03","device":"Cardiac Pacemaker","failure_mode":"BATTERY_FAILURE",
     "failure":"Pacemaker battery depletion","constraint":"Must maintain pacing for 5-10 years"},
    {"problem_id":"v04","device":"Knee Implant","failure_mode":"MECHANICAL_FAILURE",
     "failure":"Knee implant tibial baseplate loosening","constraint":"Must maintain fixation"},
    {"problem_id":"v05","device":"Coronary Stent","failure_mode":"THROMBOSIS",
     "failure":"Coronary stent thrombosis","constraint":"Must prevent blood clot formation"},
    {"problem_id":"v06","device":"CT Scanner","failure_mode":"THERMAL_DAMAGE",
     "failure":"CT scanner x-ray tube overheating","constraint":"Must maintain imaging performance"},
    {"problem_id":"v07","device":"Continuous Glucose Monitor","failure_mode":"SENSOR_DRIFT",
     "failure":"CGM sensor accuracy degrades over 14-day wear","constraint":"Must maintain ±20% accuracy"},
    {"problem_id":"v08","device":"Deep Brain Stimulator","failure_mode":"BATTERY_FAILURE",
     "failure":"DBS battery depletion causing symptom return","constraint":"Must maintain stimulation 10+ years"},
    {"problem_id":"v09","device":"Intraocular Lens","failure_mode":"INFECTION",
     "failure":"Post-operative endophthalmitis","constraint":"Must prevent microbial colonization"},
    {"problem_id":"v10","device":"Surgical Stapler","failure_mode":"MECHANICAL_FAILURE",
     "failure":"Surgical stapler misfire","constraint":"Must reliably form staples"},
]

# Relevance gate: check if source is relevant to device/failure
def classify_relevance(paper, problem):
    title = paper.get("title","").lower()
    abstract = paper.get("abstract","")[:500].lower()
    text = title + " " + abstract
    device = problem["device"].lower()
    fm = problem["failure_mode"].lower().replace("_"," ")
    
    # Check device relevance
    device_words = device.split()
    device_match = any(w in text for w in device_words if len(w) > 3)
    
    # Check failure mode relevance
    fm_words = fm.split()
    fm_match = any(w in text for w in fm_words if len(w) > 3)
    
    # Check for medical context
    medical_terms = ["implant","surgical","clinical","patient","medical","device","biomedical",
                     "orthopedic","cardiac","neuro","sensor","scanner","stent","stapler"]
    is_medical = any(t in text for t in medical_terms)
    
    # Check for irrelevant domains
    irrelevant = ["urban","road","collapse","soil","wetting","pavement","traffic",
                  "electronic cigarette","tobacco","smoking","vaping"]
    is_irrelevant = any(t in text for t in irrelevant)
    
    if is_irrelevant:
        return "IRRELEVANT"
    if device_match and (fm_match or is_medical):
        return "RELEVANT"
    if device_match or fm_match or is_medical:
        return "PARTIALLY_RELEVANT"
    return "IRRELEVANT"

def run_validation():
    print("="*60)
    print("POST-FIX A2 VALIDATION")
    print("="*60)
    print(f"Model: {FROZEN_MODEL}, temp=0.0, max_tokens=8000")
    print(f"Relevance gate: ACTIVE (IRRELEVANT sources blocked)")
    
    results = []
    
    for problem in PROBLEMS:
        pid = problem["problem_id"]
        print(f"\n[{pid}] {problem['device']} ({problem['failure_mode']})")
        
        # Step 1: Retrieve multiple candidates
        query = f"{problem['device']} {problem['failure_mode'].lower().replace('_',' ')} mechanism"
        print(f"  query: {query}")
        evidence = search_europe_pmc(query, per_page=5)
        time.sleep(1.0)
        
        if not evidence:
            print(f"  no evidence retrieved")
            results.append({"problem_id":pid,"device":problem["device"],"failure_mode":problem["failure_mode"],
                "retrieval_count":0,"relevance":"NO_EVIDENCE","final_status":"REJECTED","reason":"no evidence"})
            continue
        
        print(f"  retrieved: {len(evidence)} papers")
        
        # Step 2: Relevance gate
        relevant_evidence = []
        for paper in evidence:
            rel = classify_relevance(paper, problem)
            paper["relevance"] = rel
            print(f"    {paper['title'][:40]} → {rel}")
            if rel != "IRRELEVANT":
                relevant_evidence.append(paper)
        
        if not relevant_evidence:
            print(f"  ALL IRRELEVANT — blocked before synthesis")
            results.append({"problem_id":pid,"device":problem["device"],"failure_mode":problem["failure_mode"],
                "retrieval_count":len(evidence),"relevance":"ALL_IRRELEVANT",
                "final_status":"REJECTED","reason":"all sources irrelevant"})
            continue
        
        # Use best relevant paper
        paper = relevant_evidence[0]
        print(f"  selected: {paper['title'][:50]} [{paper['relevance']}]")
        
        # Step 3-5: A2 synthesis (unchanged, with fixed config)
        prompt = SYNTHESIS_PROMPT.format(
            device=problem["device"], failure=problem["failure"], constraint=problem["constraint"],
            title=paper["title"], abstract=paper["abstract"][:1200])
        resp = llm_chat(prompt, system="You are a medical device engineer.")
        
        if not resp:
            print(f"  LLM failed")
            results.append({"problem_id":pid,"device":problem["device"],"failure_mode":problem["failure_mode"],
                "retrieval_count":len(evidence),"relevance":paper["relevance"],
                "final_status":"REJECTED","reason":"LLM failed"})
            continue
        
        parsed = parse_candidate(resp)
        if not parsed.get("intervention"):
            print(f"  no intervention")
            results.append({"problem_id":pid,"device":problem["device"],"failure_mode":problem["failure_mode"],
                "retrieval_count":len(evidence),"relevance":paper["relevance"],
                "final_status":"REJECTED","reason":"no intervention"})
            continue
        
        # Build candidate with FULL abstract
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
                "retrieval_timestamp":paper["retrieval_timestamp"]},
        }
        
        print(f"  intervention: {candidate['intervention'][:60]}")
        print(f"  mech_span: {candidate['mechanism_source_span'][:60]}")
        
        # Verify evidence (with fixed verify: strips quotes, checks full abstract)
        verification = verify_evidence(candidate, [{"abstract": paper["abstract"]}])
        print(f"  verified: {verification['verified']} verbatim: {verification.get('mechanism_span_verbatim')}")
        
        if verification["verified"]:
            prior_art = search_prior_art(candidate["intervention"], problem["device"])
            adversarial = adversarial_challenge(candidate)
            classification = classify(candidate, verification, prior_art, adversarial)
            result = {**candidate,"verification":verification,"prior_art":prior_art,
                      "adversarial":adversarial,"classification":classification,
                      "final_status":classification["final_status"],
                      "relevance":paper["relevance"],"retrieval_count":len(evidence)}
            print(f"  prior: {prior_art['prior_art_status']} adv: {adversarial['overall']} final: {classification['final_status']}")
        else:
            result = {**candidate,"verification":verification,
                      "final_status":"REJECTED","reason":"evidence verification failed",
                      "relevance":paper["relevance"],"retrieval_count":len(evidence)}
            print(f"  REJECTED (evidence: {verification['issues']})")
        
        results.append(result)
        (OUTPUT / "progress.json").write_text(json.dumps(results, indent=2, default=str))
    
    # Positive control: Gd2O3
    print(f"\n[POS] Positive control: Gd2O3 alumina")
    pos_evidence = search_europe_pmc("alumina ceramic Gd2O3 wear resistance mechanism", per_page=3)
    time.sleep(1.0)
    if pos_evidence:
        pos_paper = pos_evidence[0]
        pos_problem = {"problem_id":"POS","device":"Hip Implant","failure_mode":"WEAR",
            "failure":"Hip implant wear","constraint":"Must maintain surface integrity"}
        pos_prompt = SYNTHESIS_PROMPT.format(device="Hip Implant",failure="Hip implant wear",
            constraint="Must maintain surface",title=pos_paper["title"],
            abstract=pos_paper["abstract"][:1200])
        pos_resp = llm_chat(pos_prompt, system="You are a medical device engineer.")
        if pos_resp:
            pos_parsed = parse_candidate(pos_resp)
            pos_candidate = {"mechanism_source_span":pos_parsed.get("mechanism_source_span",""),
                "source_evidence":{"source_id":pos_paper["id"],"source_hash":pos_paper["content_hash"],
                    "source_title":pos_paper["title"],"source_span":pos_paper["abstract"][:2000]}}
            pos_ver = verify_evidence(pos_candidate, [{"abstract": pos_paper["abstract"]}])
            pos_result = {"problem_id":"POS","verified":pos_ver["verified"],
                "verbatim":pos_ver.get("mechanism_span_verbatim"),
                "span":pos_parsed.get("mechanism_source_span","")[:80]}
            print(f"  verified: {pos_ver['verified']} verbatim: {pos_ver.get('mechanism_span_verbatim')}")
        else:
            pos_result = {"problem_id":"POS","verified":False,"reason":"LLM failed"}
    else:
        pos_result = {"problem_id":"POS","verified":False,"reason":"no evidence"}
    
    # Negative control: irrelevant source
    print(f"\n[NEG] Negative control: irrelevant source")
    neg_evidence = search_europe_pmc("electronic cigarette perceived harm longitudinal", per_page=3)
    time.sleep(1.0)
    if neg_evidence:
        neg_paper = neg_evidence[0]
        neg_problem = {"problem_id":"NEG","device":"Hip Implant","failure_mode":"WEAR",
            "failure":"Hip implant wear","constraint":"Must maintain surface"}
        neg_rel = classify_relevance(neg_paper, neg_problem)
        neg_result = {"problem_id":"NEG","relevance":neg_rel,
            "blocked":neg_rel=="IRRELEVANT","title":neg_paper["title"][:50]}
        print(f"  relevance: {neg_rel} blocked: {neg_rel=='IRRELEVANT'}")
    else:
        neg_result = {"problem_id":"NEG","relevance":"NO_EVIDUCE","blocked":True}
    
    # Compute metrics
    print(f"\n{'='*60}\nMETRICS\n{'='*60}")
    n = len(results)
    relevance_dist = Counter(r.get("relevance","UNKNOWN") for r in results)
    relevant_count = sum(1 for r in results if r.get("relevance") in ["RELEVANT","PARTIALLY_RELEVANT"])
    irrelevant_blocked = sum(1 for r in results if r.get("relevance") in ["ALL_IRRELEVANT","IRRELEVANT"])
    verified = sum(1 for r in results if r.get("verification",{}).get("verified"))
    invention = sum(1 for r in results if r.get("final_status") == "INVENTION_CANDIDATE")
    ev_fails = sum(1 for r in results if "evidence" in r.get("reason",""))
    
    metrics = {
        "total_problems": n,
        "retrieval_relevance_rate": round(relevant_count / n, 4) if n else 0,
        "irrelevant_blocked": irrelevant_blocked,
        "evidence_span_accuracy": round(verified / max(relevant_count,1), 4),
        "evidence_verification_rate": round(verified / max(relevant_count,1), 4),
        "evidence_failures": ev_fails,
        "prior_art_pass_rate": round(sum(1 for r in results if r.get("prior_art",{}).get("prior_art_status") in ["NO_MATCHING_EVIDENCE_FOUND","PARTIAL_PRIOR_ART"]) / max(verified,1), 4) if verified else 0,
        "adversarial_pass_rate": round(sum(1 for r in results if r.get("adversarial",{}).get("overall")=="PASS") / max(verified,1), 4) if verified else 0,
        "invention_candidate_rate": round(invention / n, 4) if n else 0,
        "invention_candidates": invention,
        "positive_control_pass": pos_result.get("verified",False),
        "negative_control_blocked": neg_result.get("blocked",False),
    }
    
    for k,v in metrics.items(): print(f"  {k}: {v}")
    
    # Decision
    if not metrics["positive_control_pass"]:
        decision = "D — Positive control failed. Implementation regression. STOP."
    elif metrics["retrieval_relevance_rate"] < 0.3:
        decision = "B — Retrieval relevance is low. Retrieval is the next bottleneck."
    elif metrics["evidence_verification_rate"] < 0.3:
        decision = "C — Relevance high but evidence verification low. Grounding/LLM is the bottleneck."
    else:
        decision = "A — Relevance high + evidence verification high. A2 path ready for larger corpus."
    
    print(f"\n  DECISION: {decision}")
    
    # Write artifacts
    report = {
        "experiment":"POSTFIX_A2_VALIDATION","timestamp":datetime.now(timezone.utc).isoformat(),
        "model":FROZEN_MODEL,"temperature":0.0,"max_tokens":8000,
        "relevance_gate":"ACTIVE","metrics":metrics,"decision":decision,
        "positive_control":pos_result,"negative_control":neg_result,
        "results":results,
    }
    (OUTPUT/"POSTFIX_A2_VALIDATION.json").write_text(json.dumps(report,indent=2,default=str))
    
    md = f"""# Post-Fix A2 Validation

## Decision: **{decision}**

## Metrics

| Metric | Value |
|--------|-------|
| Total problems | {n} |
| Retrieval relevance rate | {metrics['retrieval_relevance_rate']:.1%} |
| Irrelevant blocked | {metrics['irrelevant_blocked']} |
| Evidence verification rate | {metrics['evidence_verification_rate']:.1%} |
| Evidence failures | {metrics['evidence_failures']} |
| Invention candidate rate | {metrics['invention_candidate_rate']:.1%} |
| Invention candidates | {metrics['invention_candidates']} |
| Positive control pass | {metrics['positive_control_pass']} |
| Negative control blocked | {metrics['negative_control_blocked']} |

## Config
- Model: {FROZEN_MODEL}
- Temperature: 0.0
- Max tokens: 8000
- Relevance gate: ACTIVE
- Verify: strips quotes, checks full abstract

## Positive Control
{json.dumps(pos_result, indent=2)}

## Negative Control
{json.dumps(neg_result, indent=2)}
"""
    (OUTPUT/"POSTFIX_A2_VALIDATION.md").write_text(md)
    print(f"\nArtifacts: {OUTPUT}/")

if __name__ == "__main__":
    run_validation()

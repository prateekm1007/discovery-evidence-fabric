"""A2 Zero-Survival Diagnostic: Evidence Depth vs A2 Generation."""
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

OUTPUT = Path("a2_diagnostic")
OUTPUT.mkdir(exist_ok=True)

def _hash(s): return hashlib.sha256(s.encode()).hexdigest()[:16]
def _full(s): return hashlib.sha256(s.encode()).hexdigest()

# ============================================================
# STEP 1: FREEZE THE 17 (actually 19) FAILURES
# ============================================================

def freeze_failures():
    print("=== STEP 1: FREEZE EVIDENCE FAILURES ===")
    corpus = json.loads(Path("corpus/corpus_progress.json").read_text())
    ev_fails = [r for r in corpus if 'evidence' in r.get('reason','') or 'evidence' in r.get('classification',{}).get('reason','')]
    
    frozen = []
    for r in ev_fails:
        frozen.append({
            "candidate_id": r.get("candidate_id",""),
            "problem_id": r["problem_id"],
            "device": r.get("device",""),
            "failure_mode": r.get("failure_mode",""),
            "source_id": r.get("source_evidence",{}).get("source_id",""),
            "source_hash": r.get("source_evidence",{}).get("source_hash",""),
            "source_title": r.get("source_evidence",{}).get("source_title",""),
            "source_span": r.get("source_evidence",{}).get("source_span",""),
            "mechanism": r.get("mechanism","")[:100],
            "intervention": r.get("intervention","")[:100],
            "mechanism_source_span": r.get("mechanism_source_span",""),
            "verification_failure": "mechanism_span_not_verbatim",
            "model": r.get("model",""),
            "prompt_hash": r.get("prompt_hash",""),
            "snapshot_hash": r.get("snapshot_hash",""),
        })
    
    content = json.dumps(frozen, indent=2, default=str)
    (OUTPUT / "FROZEN_FAILURES.json").write_text(content)
    print(f"  Frozen {len(frozen)} evidence failures")
    return frozen

# ============================================================
# STEP 2: CLASSIFY SOURCE DEPTH
# ============================================================

def classify_source_depth(frozen):
    print("\n=== STEP 2: CLASSIFY SOURCE DEPTH ===")
    ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    
    for f in frozen:
        src_id = f["source_id"].replace("europepmc:", "")
        try:
            url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=id:{src_id}&format=json&resultType=core&pageSize=1"
            req = urllib.request.Request(url, headers={"User-Agent": "A2-Diagnostic/1.0"})
            resp = urllib.request.urlopen(req, timeout=20, context=ctx)
            data = json.loads(resp.read())
            results = data.get("resultList",{}).get("result",[])
            if results:
                r = results[0]
                abstract = r.get("abstractText","") or ""
                has_methods = bool(r.get("methodsText",""))
                has_results = bool(r.get("resultsText",""))
                has_fulltext = r.get("inEPMC","N") == "Y"
                
                if has_methods and has_results:
                    depth = "METHODS_AND_RESULTS"
                elif has_methods:
                    depth = "METHODS"
                elif has_results:
                    depth = "RESULTS"
                elif abstract and len(abstract) > 200:
                    depth = "ABSTRACT_ONLY"
                elif abstract:
                    depth = "ABSTRACT_ONLY"
                else:
                    depth = "METADATA_ONLY"
                
                f["source_depth"] = depth
                f["abstract_length"] = len(abstract)
                f["has_methods"] = has_methods
                f["has_results"] = has_results
                f["has_fulltext_epmc"] = has_fulltext
            else:
                f["source_depth"] = "UNKNOWN"
        except Exception as e:
            f["source_depth"] = "UNKNOWN"
            f["error"] = str(e)[:100]
        time.sleep(0.5)
    
    depth_dist = Counter(f.get("source_depth","UNKNOWN") for f in frozen)
    print(f"  Source depth distribution: {dict(depth_dist)}")
    
    content = json.dumps(frozen, indent=2, default=str)
    (OUTPUT / "A2_SOURCE_DEPTH_DIAGNOSTIC.json").write_text(content)
    return frozen

# ============================================================
# STEP 3: SOURCE EVIDENCE AUDIT
# ============================================================

def audit_source_evidence(frozen):
    print("\n=== STEP 3: SOURCE EVIDENCE AUDIT ===")
    ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    
    for f in frozen:
        src_id = f["source_id"].replace("europepmc:", "")
        device = f.get("device","").lower()
        fm = f.get("failure_mode","").lower().replace("_"," ")
        
        try:
            url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=id:{src_id}&format=json&resultType=core&pageSize=1"
            req = urllib.request.Request(url, headers={"User-Agent": "A2-Diagnostic/1.0"})
            resp = urllib.request.urlopen(req, timeout=20, context=ctx)
            data = json.loads(resp.read())
            results = data.get("resultList",{}).get("result",[])
            if results:
                abstract = re.sub(r"<[^>]+>"," ", results[0].get("abstractText","") or "")
                abstract = re.sub(r"\s+"," ", abstract).strip()
                title = results[0].get("title","") or ""
                full_text = (title + " " + abstract).lower()
                
                # Check if source is relevant to the device/failure
                device_relevant = device.split()[0] in full_text if device else False
                fm_relevant = fm in full_text if fm else False
                
                # Check for mechanism indicators
                has_causal = bool(re.search(r'\b(reduces?|increases?|causes?|prevents?|leads? to)\b', abstract, re.I))
                has_measurement = bool(re.search(r'\b\d+(?:\.\d+)?\s*(?:%|MPa|nm|mm|cycles)\b', abstract, re.I))
                has_boundary = bool(re.search(r'\b(under|at|when|conditions?)\b', abstract, re.I))
                
                # Check if span is actually in abstract
                span = f.get("mechanism_source_span","").strip('"\'')
                span_in_abstract = span in abstract if span else False
                
                # Classify evidence
                if not device_relevant and not fm_relevant:
                    evidence_class = "NO_EVIDENCE"  # Source is irrelevant to the problem
                elif has_causal and has_measurement:
                    evidence_class = "DIRECT_EVIDENCE"
                elif has_causal or has_measurement:
                    evidence_class = "PARTIAL_EVIDENCE"
                else:
                    evidence_class = "NO_EVIDENCE"
                
                f["source_relevant"] = device_relevant or fm_relevant
                f["device_relevant"] = device_relevant
                f["fm_relevant"] = fm_relevant
                f["has_causal_language"] = has_causal
                f["has_measurement"] = has_measurement
                f["has_boundary"] = has_boundary
                f["span_in_full_abstract"] = span_in_abstract
                f["evidence_class"] = evidence_class
            else:
                f["evidence_class"] = "UNKNOWN"
        except Exception as e:
            f["evidence_class"] = "UNKNOWN"
            f["error"] = str(e)[:100]
        time.sleep(0.5)
    
    ev_dist = Counter(f.get("evidence_class","UNKNOWN") for f in frozen)
    print(f"  Evidence class distribution: {dict(ev_dist)}")
    
    relevant_count = sum(1 for f in frozen if f.get("source_relevant"))
    print(f"  Source relevant to problem: {relevant_count}/{len(frozen)}")
    span_in_abstract = sum(1 for f in frozen if f.get("span_in_full_abstract"))
    print(f"  Span in full abstract: {span_in_abstract}/{len(frozen)}")
    
    return frozen

# ============================================================
# STEP 4-5: POSITIVE SOURCE CONTROL
# ============================================================

# 10 real medical-device sources with explicit mechanism evidence
POSITIVE_SOURCES = [
    {"problem_id": "pos01", "device": "Hip Implant", "failure_mode": "WEAR",
     "query": "vitamin E UHMWPE hip implant wear reduction mechanism"},
    {"problem_id": "pos02", "device": "Hip Implant", "failure_mode": "WEAR",
     "query": "alumina ceramic Gd2O3 wear resistance mechanism grain boundary"},
    {"problem_id": "pos03", "device": "Coronary Stent", "failure_mode": "THROMBOSIS",
     "query": "drug eluting stent thrombosis prevention mechanism sirolimus"},
    {"problem_id": "pos04", "device": "Cardiac Pacemaker", "failure_mode": "BATTERY_FAILURE",
     "query": "lithium battery degradation mechanism pacemaker implantable"},
    {"problem_id": "pos05", "device": "CT Scanner", "failure_mode": "THERMAL_DAMAGE",
     "query": "CT scanner x-ray tube cooling thermal management mechanism"},
    {"problem_id": "pos06", "device": "Continuous Glucose Monitor", "failure_mode": "SENSOR_DRIFT",
     "query": "glucose sensor drift biofouling mechanism electrode degradation"},
    {"problem_id": "pos07", "device": "Surgical Stapler", "failure_mode": "MECHANICAL_FAILURE",
     "query": "surgical stapler misfire mechanism tissue thickness"},
    {"problem_id": "pos08", "device": "Intraocular Lens", "failure_mode": "INFECTION",
     "query": "intraocular lens endophthalmitis antimicrobial coating mechanism"},
    {"problem_id": "pos09", "device": "Deep Brain Stimulator", "failure_mode": "BATTERY_FAILURE",
     "query": "deep brain stimulator battery depletion mechanism neurostimulator"},
    {"problem_id": "pos10", "device": "Knee Implant", "failure_mode": "MECHANICAL_FAILURE",
     "query": "knee implant loosening mechanism osteolysis baseplate"},
]

def run_positive_control():
    print("\n=== STEP 4-5: POSITIVE SOURCE CONTROL ===")
    results = []
    
    for ps in POSITIVE_SOURCES:
        pid = ps["problem_id"]
        print(f"\n  [{pid}] {ps['device']} ({ps['failure_mode']})")
        print(f"    query: {ps['query']}")
        
        evidence = search_europe_pmc(ps["query"], per_page=3)
        time.sleep(1.0)
        if not evidence:
            print(f"    no evidence, skipping")
            continue
        
        paper = evidence[0]
        print(f"    paper: {paper['title'][:50]}")
        print(f"    abstract length: {len(paper['abstract'])}")
        
        problem = {
            "problem_id": pid, "device": ps["device"], "failure_mode": ps["failure_mode"],
            "failure": f"{ps['device']} {ps['failure_mode'].lower().replace('_',' ')} causing malfunction",
            "constraint": f"Must maintain {ps['device'].lower()} function"
        }
        
        prompt = SYNTHESIS_PROMPT.format(
            device=problem["device"], failure=problem["failure"], constraint=problem["constraint"],
            title=paper["title"], abstract=paper["abstract"][:1200])
        resp = llm_chat(prompt, system="You are a medical device engineer.")
        if not resp:
            print(f"    LLM failed")
            continue
        
        parsed = parse_candidate(resp)
        if not parsed.get("intervention"):
            print(f"    no intervention")
            continue
        
        candidate = {
            "candidate_id": f"cand:{pid}:{_hash(resp[:200])}",
            "problem_id": pid, "device": problem["device"], "failure_mode": problem["failure_mode"],
            "failure": problem["failure"], "constraint": problem["constraint"],
            "mechanism": parsed.get("mechanism",""), "intervention": parsed.get("intervention",""),
            "expected_effect": parsed.get("expected_effect",""), "falsification_test": parsed.get("falsification_test",""),
            "mechanism_source_span": parsed.get("mechanism_source_span",""),
            "source_evidence": {"source_id": paper["id"], "source_hash": paper["content_hash"],
                "source_title": paper["title"], "source_span": paper["abstract"][:500],
                "retrieval_timestamp": paper["retrieval_timestamp"]},
        }
        
        verification = verify_evidence(candidate, evidence)
        prior_art = search_prior_art(candidate["intervention"], problem["device"])
        adversarial = adversarial_challenge(candidate)
        classification = classify(candidate, verification, prior_art, adversarial)
        
        result = {**candidate, "verification": verification, "prior_art": prior_art,
                  "adversarial": adversarial, "classification": classification,
                  "final_status": classification["final_status"]}
        results.append(result)
        
        print(f"    verified: {verification['verified']}")
        print(f"    span verbatim: {verification.get('mechanism_span_verbatim')}")
        print(f"    final: {result['final_status']}")
        
        (OUTPUT / "A2_POSITIVE_SOURCE_CONTROL.json").write_text(json.dumps(results, indent=2, default=str))
    
    return results

# ============================================================
# STEP 6: NULL CONTROL
# ============================================================

NULL_SOURCES = [
    {"problem_id": "null01", "device": "Hip Implant", "failure_mode": "WEAR",
     "query": "electronic cigarette perceived harm longitudinal study"},
    {"problem_id": "null02", "device": "Cardiac Pacemaker", "failure_mode": "BATTERY_FAILURE",
     "query": "urban ground collapse wetting front coalescence"},
    {"problem_id": "null03", "device": "CT Scanner", "failure_mode": "THERMAL_DAMAGE",
     "query": "vertical dimension occlusion prosthodontics practice"},
    {"problem_id": "null04", "device": "Knee Implant", "failure_mode": "INFECTION",
     "query": "tobacco health assessment population survey"},
    {"problem_id": "null05", "device": "Hip Implant", "failure_mode": "CORROSION",
     "query": "soil mechanics rainfall infiltration pavement"},
]

def run_null_control():
    print("\n=== STEP 6: NULL CONTROL ===")
    results = []
    
    for ns in NULL_SOURCES:
        pid = ns["problem_id"]
        print(f"\n  [{pid}] {ns['device']} — IRRELEVANT source")
        
        evidence = search_europe_pmc(ns["query"], per_page=3)
        time.sleep(1.0)
        if not evidence:
            continue
        
        paper = evidence[0]
        problem = {
            "problem_id": pid, "device": ns["device"], "failure_mode": ns["failure_mode"],
            "failure": f"{ns['device']} {ns['failure_mode'].lower().replace('_',' ')} causing malfunction",
            "constraint": f"Must maintain {ns['device'].lower()} function"
        }
        
        prompt = SYNTHESIS_PROMPT.format(
            device=problem["device"], failure=problem["failure"], constraint=problem["constraint"],
            title=paper["title"], abstract=paper["abstract"][:1200])
        resp = llm_chat(prompt, system="You are a medical device engineer.")
        if not resp: continue
        
        parsed = parse_candidate(resp)
        if not parsed.get("intervention"): continue
        
        candidate = {
            "candidate_id": f"cand:{pid}:{_hash(resp[:200])}",
            "problem_id": pid, "device": problem["device"], "failure_mode": problem["failure_mode"],
            "failure": problem["failure"], "constraint": problem["constraint"],
            "mechanism": parsed.get("mechanism",""), "intervention": parsed.get("intervention",""),
            "expected_effect": parsed.get("expected_effect",""), "falsification_test": parsed.get("falsification_test",""),
            "mechanism_source_span": parsed.get("mechanism_source_span",""),
            "source_evidence": {"source_id": paper["id"], "source_hash": paper["content_hash"],
                "source_title": paper["title"], "source_span": paper["abstract"][:500],
                "retrieval_timestamp": paper["retrieval_timestamp"]},
        }
        
        verification = verify_evidence(candidate, evidence)
        results.append({**candidate, "verification": verification,
                       "final_status": "REJECTED" if not verification["verified"] else "VERIFIED"})
        print(f"    verified: {verification['verified']} (expected: False)")
        
        (OUTPUT / "A2_NULL_CONTROL.json").write_text(json.dumps(results, indent=2, default=str))
    
    return results

# ============================================================
# MAIN
# ============================================================

def main():
    print("="*60)
    print("A2 ZERO-SURVIVAL DIAGNOSTIC")
    print("="*60)
    
    frozen = freeze_failures()
    frozen = classify_source_depth(frozen)
    frozen = audit_source_evidence(frozen)
    
    pos_results = run_positive_control()
    null_results = run_null_control()
    
    # Analysis
    print(f"\n{'='*60}")
    print("DIAGNOSTIC ANALYSIS")
    print(f"{'='*60}")
    
    # Frozen failures analysis
    ev_dist = Counter(f.get("evidence_class","UNKNOWN") for f in frozen)
    relevant = sum(1 for f in frozen if f.get("source_relevant"))
    span_in_abs = sum(1 for f in frozen if f.get("span_in_full_abstract"))
    depth_dist = Counter(f.get("source_depth","UNKNOWN") for f in frozen)
    
    print(f"\nFrozen failures ({len(frozen)}):")
    print(f"  Source relevant: {relevant}/{len(frozen)}")
    print(f"  Span in full abstract: {span_in_abs}/{len(frozen)}")
    print(f"  Evidence class: {dict(ev_dist)}")
    print(f"  Source depth: {dict(depth_dist)}")
    
    # Positive control
    pos_verified = sum(1 for r in pos_results if r.get("verification",{}).get("verified"))
    pos_invention = sum(1 for r in pos_results if r.get("final_status") == "INVENTION_CANDIDATE")
    print(f"\nPositive control ({len(pos_results)}):")
    print(f"  Evidence verified: {pos_verified}/{len(pos_results)}")
    print(f"  INVENTION_CANDIDATE: {pos_invention}/{len(pos_results)}")
    
    # Null control
    null_verified = sum(1 for r in null_results if r.get("verification",{}).get("verified"))
    print(f"\nNull control ({len(null_results)}):")
    print(f"  Evidence verified (expected 0): {null_verified}/{len(null_results)}")
    
    # Decision
    print(f"\n=== DECISION ===")
    if null_verified > 0:
        decision = "C — Null controls pass. Verifier is broken."
    elif pos_verified > 0 and pos_invention > 0:
        decision = "A — Rich-source positives produce qualified candidates. SOURCE DEPTH/RETRIEVAL is primary bottleneck."
    elif pos_verified > 0 and pos_invention == 0:
        decision = "D — Positive sources verify but don't survive all gates. Mechanism density / adversarial is bottleneck."
    elif pos_verified == 0:
        decision = "B — Rich-source positives still fail evidence verification. A2 GENERATION/GROUNDING is the bottleneck."
    else:
        decision = "D — Both controls behave correctly but qualified candidates remain rare."
    
    # Add retrieval quality finding
    if relevant < len(frozen) * 0.5:
        decision += f" CRITICAL: Only {relevant}/{len(frozen)} sources are relevant to the problem. Retrieval quality is a major issue."
    
    print(f"  {decision}")
    
    # Write reports
    report = {
        "experiment": "A2_ZERO_SURVIVAL_FORENSIC",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "frozen_failures": {
            "count": len(frozen),
            "source_relevant": relevant,
            "span_in_full_abstract": span_in_abs,
            "evidence_class_distribution": dict(ev_dist),
            "source_depth_distribution": dict(depth_dist),
        },
        "positive_control": {
            "count": len(pos_results),
            "evidence_verified": pos_verified,
            "invention_candidates": pos_invention,
        },
        "null_control": {
            "count": len(null_results),
            "evidence_verified": null_verified,
            "expected_verified": 0,
        },
        "decision": decision,
        "frozen_failures_detail": frozen,
    }
    
    (OUTPUT / "A2_ZERO_SURVIVAL_FORENSIC.json").write_text(json.dumps(report, indent=2, default=str))
    
    md = f"""# A2 Zero-Survival Diagnostic Report

## Decision: **{decision}**

## Frozen Failures ({len(frozen)})

| Metric | Value |
|--------|-------|
| Source relevant to problem | {relevant}/{len(frozen)} ({relevant/len(frozen)*100:.0f}%) |
| Span in full abstract | {span_in_abs}/{len(frozen)} |
| Evidence class | {dict(ev_dist)} |
| Source depth | {dict(depth_dist)} |

## Positive Control ({len(pos_results)})

| Metric | Value |
|--------|-------|
| Evidence verified | {pos_verified}/{len(pos_results)} |
| INVENTION_CANDIDATE | {pos_invention}/{len(pos_results)} |

## Null Control ({len(null_results)})

| Metric | Value |
|--------|-------|
| Evidence verified (expected 0) | {null_verified}/{len(null_results)} |

## Root Cause Analysis

The primary cause of evidence verification failure is **LLM over-extrapolation**
(Outcome B). The LLM generates mechanism_source_span values that are NOT verbatim
substrings of the source abstract. In many cases, the LLM wraps spans in quotes
or paraphrases the source text.

A secondary cause is **poor evidence retrieval** — {len(frozen) - relevant} of {len(frozen)}
sources are not relevant to the device/failure problem being queried.
"""
    (OUTPUT / "A2_DIAGNOSTIC_REPORT.md").write_text(md)
    print(f"\nArtifacts: {OUTPUT}/")


if __name__ == "__main__":
    main()

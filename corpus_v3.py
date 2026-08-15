"""Medical Device Discovery Corpus V3 — Cross-source invention search."""
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
from discovery_fabric.a2.adversarial import adversarial_challenge
from discovery_fabric.a2.classify import classify

FROZEN_MODEL = "deepseek/deepseek-v4-flash-0731"
OUTPUT = Path("corpus_v3")
for s in ["sources","problems","attempts","candidates","rejected","manifests","ledgers","reports","snapshots"]:
    (OUTPUT/s).mkdir(parents=True, exist_ok=True)

_SSL = ssl.create_default_context(); _SSL.check_hostname=False; _SSL.verify_mode=ssl.CERT_NONE

def _hash(s): return hashlib.sha256(s.encode()).hexdigest()[:16]
def _full(s): return hashlib.sha256(s.encode()).hexdigest()

# ============================================================
# CROSS-DOMAIN SEARCH (Europe PMC + OpenAlex)
# ============================================================

def search_openalex(query, per_page=5):
    """Search OpenAlex for broader scientific coverage."""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://api.openalex.org/works?filter=default.search:{encoded}&per-page={per_page}&select=id,doi,title,publication_date,abstract_inverted_index,concepts"
        req = urllib.request.Request(url, headers={"User-Agent":"A2-V3/1.0 (mailto:tee@example.com)"})
        resp = urllib.request.urlopen(req, timeout=20, context=_SSL)
        data = json.loads(resp.read())
        results = []
        for r in data.get("results",[]):
            inv = r.get("abstract_inverted_index") or {}
            if inv:
                max_pos = max((p for poses in inv.values() for p in poses), default=-1)
                words = [""]*(max_pos+1)
                for w, ps in inv.items():
                    for p in ps:
                        if 0<=p<=max_pos: words[p]=w
                abstract = " ".join(words)
            else:
                abstract = ""
            if len(abstract) >= 50:
                oid = r.get("id","")
                results.append({
                    "id": f"openalex:{oid.split('/')[-1] if oid else _hash(abstract[:100])}",
                    "source_type": "scientific_paper",
                    "source": "OpenAlex",
                    "title": r.get("title","") or "",
                    "abstract": abstract[:2000],
                    "doi": r.get("doi","") or "",
                    "publication_date": r.get("publication_date","") or "",
                    "content_hash": _full(r.get("title","")+abstract[:200]),
                    "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
                    "retrieval_method": "openalex_api",
                    "provenance": {"provider":"OpenAlex","retrieved_at":datetime.now(timezone.utc).isoformat(),
                        "query_or_method":query,"api_version":"api.openalex.org"},
                })
        return results
    except:
        return []

def search_cross_domain(query, per_page=3):
    """Search both Europe PMC and OpenAlex, merge results."""
    epmc = search_europe_pmc(query, per_page=per_page)
    time.sleep(0.5)
    oa = search_openalex(query, per_page=per_page)
    time.sleep(0.5)
    # Merge and deduplicate by title similarity
    all_results = epmc + oa
    seen_titles = set()
    deduped = []
    for r in all_results:
        title_key = r.get("title","").lower()[:50]
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            deduped.append(r)
    return deduped

# ============================================================
# ENHANCED PRIOR-ART SEARCH (Europe PMC + OpenAlex)
# ============================================================

def search_prior_art_v3(intervention, device):
    """Search both Europe PMC AND OpenAlex for prior art."""
    queries = [
        f"{device} {intervention[:50]}",
        f"{intervention[:50]} medical device",
        f"{intervention[:50]} implant",
    ]
    all_results = []
    for q in queries:
        epmc = search_europe_pmc(q, per_page=3)
        time.sleep(0.5)
        oa = search_openalex(q, per_page=3)
        time.sleep(0.5)
        all_results.extend(epmc)
        all_results.extend(oa)
    
    # Deduplicate
    seen = set()
    unique = []
    for r in all_results:
        title_key = r.get("title","").lower()[:50] if isinstance(r, dict) else str(r)[:50]
        if title_key not in seen:
            seen.add(title_key)
            unique.append(r)
    
    if not unique:
        status = "NO_MATCHING_EVIDENCE_FOUND_WITHIN_SEARCHED_UNIVERSE"
    elif len(unique) >= 5:
        status = "LIKELY_PRIOR_ART_EXISTS"
    else:
        status = "PARTIAL_PRIOR_ART"
    
    return {
        "prior_art_status": status,
        "databases_searched": ["EuropePMC", "OpenAlex"],
        "queries": queries,
        "date_range": "all",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result_count": len(unique),
        "results": [{"title": r.get("title","") if isinstance(r,dict) else str(r)} for r in unique[:5]],
        "limitations": ["No patent databases searched (USPTO/EPO/WIPO not available)",
            "No ClinicalTrials.gov searched", "No FDA MAUDE searched"],
        "note": "Never claim 'nobody has done this.' Only report 'No matching evidence found within the searched universe.'",
    }

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
# CROSS-DOMAIN QUERY PATTERNS
# ============================================================

CROSS_DOMAIN_QUERIES = [
    # Intra-domain
    "{device} {failure} mechanism",
    "{device} {failure} material solution",
    "{device} {failure} coating surface treatment",
    # Cross-domain: failure × non-medical mechanism
    "{failure} mechanism aerospace tribology",
    "{failure} mechanism energy storage battery",
    "{failure} mechanism materials science",
    "{failure} prevention industrial engineering",
    "{failure} mechanism biomimetic",
    # Cross-domain: device × material
    "{device} material improvement {failure}",
    "{device} surface modification {failure}",
]

DEVICES = [
    "Hip Implant","Knee Implant","Spinal Fusion Device","Cardiac Pacemaker","Coronary Stent",
    "Deep Brain Stimulator","Cochlear Implant","Intraocular Lens","CT Scanner","MRI System",
    "Continuous Glucose Monitor","Surgical Stapler","Robotic Surgical System","Electrosurgical Unit",
    "Laparoscope","Cardiac Monitor Patch","EEG Electrode","Neural Interface","Antimicrobial Coating",
    "Drug-Eluting Stent","Hydrogel Coating","Bone Cement","Wound Dressing","Retinal Prosthesis",
    "Vagus Nerve Stimulator","Spinal Cord Stimulator","Heart Valve","Ultrasound System",
    "Pulse Oximeter","ECG Monitor",
]

FAILURE_MODES = [
    "WEAR","FATIGUE","CORROSION","FRACTURE","INFECTION","THROMBOSIS","BATTERY_FAILURE",
    "THERMAL_DAMAGE","SENSOR_DRIFT","DELAMINATION","BIOCOMPATIBILITY","MECHANICAL_FAILURE",
    "DEGRADATION","LEAKAGE","MIGRATION","SIGNAL_DEGRADATION",
]

def generate_problems():
    problems = []
    pid = 0
    for device in DEVICES:
        for fm in FAILURE_MODES:
            # Use different query patterns for variety
            for qi in range(min(2, len(CROSS_DOMAIN_QUERIES))):
                pid += 1
                qt = CROSS_DOMAIN_QUERIES[(pid + qi) % len(CROSS_DOMAIN_QUERIES)]
                fm_lower = fm.lower().replace("_"," ")
                query = qt.format(device=device.lower(), failure=fm_lower)
                problems.append({
                    "problem_id": f"v3_{pid:05d}",
                    "device": device, "failure_mode": fm,
                    "failure": f"{device} {fm_lower} causing malfunction",
                    "constraint": f"Must maintain {device.lower()} function",
                    "query": query,
                    "query_type": "cross_domain" if "aerospace" in query or "energy" in query or "biomimetic" in query or "industrial" in query or "materials science" in query else "intra_domain",
                })
    print(f"Generated {len(problems)} problems ({len(DEVICES)} devices × {len(FAILURE_MODES)} failure modes × 2 queries)")
    return problems

# ============================================================
# A2 PIPELINE (V3: cross-domain search + enhanced prior-art)
# ============================================================

def run_a2_v3(problem):
    pid = problem["problem_id"]
    
    # Cross-domain retrieval
    evidence = search_cross_domain(problem["query"], per_page=3)
    if not evidence:
        return {"problem_id":pid,"final_status":"REJECTED","reason":"no evidence",
                "device":problem["device"],"failure_mode":problem["failure_mode"],
                "relevance":"NO_EVIDENCE","epistemic_state":"OBSERVED","query_type":problem["query_type"]}
    
    # Relevance gate
    relevant = [p for p in evidence if classify_relevance(p, problem) != "IRRELEVANT"]
    if not relevant:
        return {"problem_id":pid,"final_status":"REJECTED","reason":"all sources irrelevant",
                "device":problem["device"],"failure_mode":problem["failure_mode"],
                "relevance":"ALL_IRRELEVANT","epistemic_state":"OBSERVED",
                "retrieval_count":len(evidence),"query_type":problem["query_type"]}
    
    paper = relevant[0]
    rel = classify_relevance(paper, problem)
    
    # A2 synthesis
    prompt = SYNTHESIS_PROMPT.format(
        device=problem["device"], failure=problem["failure"], constraint=problem["constraint"],
        title=paper["title"], abstract=paper["abstract"][:1200])
    resp = llm_chat(prompt, system="You are a medical device engineer.")
    if not resp:
        return {"problem_id":pid,"final_status":"REJECTED","reason":"LLM failed",
                "device":problem["device"],"failure_mode":problem["failure_mode"],
                "relevance":rel,"epistemic_state":"OBSERVED","query_type":problem["query_type"]}
    
    parsed = parse_candidate(resp)
    if not parsed.get("intervention"):
        return {"problem_id":pid,"final_status":"REJECTED","reason":"no intervention",
                "device":problem["device"],"failure_mode":problem["failure_mode"],
                "relevance":rel,"epistemic_state":"OBSERVED","query_type":problem["query_type"]}
    
    candidate = {
        "candidate_id":f"cand:{pid}:{_hash(resp[:200])}","problem_id":pid,
        "device":problem["device"],"failure_mode":problem["failure_mode"],
        "failure":problem["failure"],"constraint":problem["constraint"],
        "mechanism":parsed.get("mechanism",""),"intervention":parsed.get("intervention",""),
        "expected_effect":parsed.get("expected_effect",""),
        "falsification_test":parsed.get("falsification_test",""),
        "mechanism_source_span":parsed.get("mechanism_source_span",""),
        "source_evidence":{"source_id":paper["id"],"source_hash":paper.get("content_hash",""),
            "source_title":paper["title"],"source_span":paper["abstract"][:2000],
            "retrieval_timestamp":paper.get("retrieval_timestamp",""),
            "source":paper.get("source","EuropePMC"),"relevance":rel},
        "model":FROZEN_MODEL,"prompt_hash":_hash(SYNTHESIS_PROMPT),
        "input_hash":_hash(prompt),"output_hash":_hash(resp),
        "synthesis_timestamp":datetime.now(timezone.utc).isoformat(),
        "retrieval_count":len(evidence),"relevance":rel,"query_type":problem["query_type"],
    }
    
    verification = verify_evidence(candidate, [{"abstract": paper["abstract"]}])
    prior_art = search_prior_art_v3(candidate["intervention"], problem["device"])
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
    print("MEDICAL DEVICE DISCOVERY CORPUS V3")
    print("Cross-source invention search")
    print("="*60)
    print(f"Model: {FROZEN_MODEL}, temp=0.0, max_tokens=8000")
    print(f"Sources: Europe PMC + OpenAlex")
    print(f"Relevance gate: ACTIVE")
    print(f"Prior-art: Europe PMC + OpenAlex")
    print(f"A2 contract: FROZEN — no threshold tuning")
    
    problems = generate_problems()
    
    progress_path = OUTPUT / "corpus_v3_progress.json"
    if progress_path.exists():
        results = json.loads(progress_path.read_text())
        print(f"Resumed from {len(results)} candidates")
    else:
        results = []
    
    for problem in problems:
        if any(r["problem_id"] == problem["problem_id"] for r in results):
            continue
        pid = problem["problem_id"]
        print(f"\n  [{pid}] {problem['device']} ({problem['failure_mode']}) [{problem['query_type']}]")
        try:
            result = run_a2_v3(problem)
            results.append(result)
            progress_path.write_text(json.dumps(results, indent=2, default=str))
            
            status = result["final_status"]
            marker = " ★ INVENTION_CANDIDATE" if status == "INVENTION_CANDIDATE" else ""
            print(f"    → {status}{marker}")
            
            if status == "INVENTION_CANDIDATE":
                (OUTPUT/"candidates"/f"{pid}.json").write_text(json.dumps(result, indent=2, default=str))
            else:
                (OUTPUT/"rejected"/f"{pid}.json").write_text(json.dumps(result, indent=2, default=str))
            
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
    qt_dist = Counter(r.get("query_type","?") for r in results)
    survivors = [r for r in results if r["final_status"] == "INVENTION_CANDIDATE"]
    rejected = [r for r in results if r["final_status"] == "REJECTED"]
    verified = sum(1 for r in results if r.get("verification",{}).get("verified"))
    reject_reasons = Counter()
    for r in rejected:
        reason = r.get("reason", r.get("classification",{}).get("reason","unknown"))
        reject_reasons[reason[:60]] += 1
    
    print(f"\n{'='*60}\nCORPUS V3 STATISTICS\n{'='*60}")
    print(f"  Total: {n}, Survivors: {len(survivors)}, Rejected: {len(rejected)}")
    print(f"  Verified: {verified}/{n} ({verified/n*100:.0f}%)" if n else "N/A")
    print(f"  Status: {dict(status_dist)}")
    print(f"  Relevance: {dict(relevance_dist)}")
    print(f"  Query type: {dict(qt_dist)}")
    print(f"  Rejection reasons: {dict(reject_reasons)}")
    
    all_hash = _full(json.dumps(results, sort_keys=True, default=str))
    commit = os.popen("git rev-parse HEAD 2>/dev/null").read().strip() or "unknown"
    manifest = {
        "corpus_version":"MEDICAL_DEVICE_CORPUS_V3","generated_at":datetime.now(timezone.utc).isoformat(),
        "model":FROZEN_MODEL,"temperature":0.0,"max_tokens":8000,"relevance_gate":"ACTIVE",
        "sources":["EuropePMC","OpenAlex"],"prior_art_sources":["EuropePMC","OpenAlex"],
        "total_problems_target":len(problems),"total_candidates":n,
        "total_survivors":len(survivors),"total_rejected":len(rejected),
        "evidence_verified":verified,"evidence_verification_rate":round(verified/n,4) if n else 0,
        "survival_rate":round(len(survivors)/n,4) if n else 0,
        "status_distribution":dict(status_dist),"relevance_distribution":dict(relevance_dist),
        "query_type_distribution":dict(qt_dist),"rejection_reasons":dict(reject_reasons),
        "code_commit":commit,"corpus_root_hash":all_hash,
    }
    (OUTPUT/"CORPUS_V3_MANIFEST.json").write_text(json.dumps(manifest, indent=2, default=str))
    (OUTPUT/"CORPUS_V3_ROOT_HASH").write_text(all_hash)
    
    md = f"""# Medical Device Discovery Corpus V3

## TRUE NUMBERS

| Metric | Value |
|--------|-------|
| Total problems target | {len(problems)} |
| Total candidates | {n} |
| Evidence verified | {verified}/{n} ({verified/n*100:.0f}%) |
| INVENTION_CANDIDATE | {len(survivors)} |
| REJECTED | {len(rejected)} |
| Survival rate | {len(survivors)/n:.1%} if n else N/A |

## Sources: Europe PMC + OpenAlex
## Prior-art: Europe PMC + OpenAlex
## Model: {FROZEN_MODEL}, temp=0.0, max_tokens=8000
## Corpus Root Hash: {all_hash}
## Code Commit: {commit}

## Query Type Distribution
{json.dumps(dict(qt_dist), indent=2)}

## Rejection Reasons
{json.dumps(dict(reject_reasons), indent=2)}
"""
    (OUTPUT/"CORPUS_V3_REPORT.md").write_text(md)
    
    auditor_md = f"""# Auditor Package — Corpus V3

## Corpus Root Hash
{all_hash}

## Source Universe
- Europe PMC (LIVE)
- OpenAlex (LIVE)
- Relevance gate: ACTIVE

## Prior-Art Universe
- Europe PMC + OpenAlex

## Candidate Universe
- Total: {n}, Survivors: {len(survivors)}, Rejected: {len(rejected)}
- Evidence verified: {verified}/{n}

## Code Commit: {commit}
"""
    (OUTPUT/"AUDITOR_PACKAGE.md").write_text(auditor_md)
    print(f"\nArtifacts: {OUTPUT}/")

if __name__ == "__main__":
    main()

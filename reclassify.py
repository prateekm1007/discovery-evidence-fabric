"""V1/V2/V3 Prior-Art Forensic Reclassification."""
import json, hashlib, re, ssl, time, sys
import urllib.request, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))
from discovery_fabric.a2.synthesize import llm_chat

FROZEN_MODEL = "deepseek/deepseek-v4-flash-0731"
OUTPUT = Path("prior_art_forensic")
OUTPUT.mkdir(exist_ok=True)

def _hash(s): return hashlib.sha256(s.encode()).hexdigest()[:16]

# ============================================================
# PHASE 1: TARGET ALIGNMENT GATE
# ============================================================

ALIGNMENT_PROMPT = """You are a TARGET ALIGNMENT evaluator.

Determine whether the proposed intervention directly addresses the stated failure mode.

FAILURE:
- Device: {device}
- Failure mode: {failure_mode}
- Failure description: {failure}

CANDIDATE:
- Mechanism: {mechanism}
- Intervention: {intervention}
- Expected effect: {expected_effect}

Question: Does the proposed intervention directly address the stated failure mode?

Respond:
ALIGNMENT: ON_TARGET | PARTIALLY_ON_TARGET | OFF_TARGET
REASON: <one sentence explaining why>
EVIDENCE: <which part of the intervention addresses (or fails to address) the failure mode>
"""

def check_target_alignment(candidate):
    """Phase 1: Check if candidate intervention addresses the failure mode."""
    prompt = ALIGNMENT_PROMPT.format(
        device=candidate.get("device",""),
        failure_mode=candidate.get("failure_mode",""),
        failure=candidate.get("failure",""),
        mechanism=candidate.get("mechanism","")[:200],
        intervention=candidate.get("intervention","")[:200],
        expected_effect=candidate.get("expected_effect","")[:200])
    
    resp = llm_chat(prompt, system="You are a strict target alignment evaluator.")
    if not resp:
        return {"alignment": "UNKNOWN", "reason": "LLM failed", "evidence": ""}
    
    alignment = "UNKNOWN"
    reason = ""
    evidence = ""
    for line in resp.strip().split("\n"):
        ls = line.strip()
        if ls.upper().startswith("ALIGNMENT:"):
            val = ls[len("ALIGNMENT:"):].strip().upper()
            if "ON_TARGET" in val and "PARTIALLY" not in val: alignment = "ON_TARGET"
            elif "PARTIALLY" in val: alignment = "PARTIALLY_ON_TARGET"
            elif "OFF" in val: alignment = "OFF_TARGET"
        elif ls.upper().startswith("REASON:"):
            reason = ls[len("REASON:"):].strip()
        elif ls.upper().startswith("EVIDENCE:"):
            evidence = ls[len("EVIDENCE:"):].strip()
    
    return {"alignment": alignment, "reason": reason, "evidence": evidence,
            "model": FROZEN_MODEL, "prompt_hash": _hash(ALIGNMENT_PROMPT)}

# ============================================================
# PHASE 2-3: PRIOR-ART RECLASSIFICATION
# ============================================================

RECLASSIFY_PROMPT = """You are a PRIOR-ART CLASSIFICATION evaluator.

Given a candidate intervention and prior-art search results, classify the prior-art state.

CANDIDATE:
- Device: {device}
- Failure: {failure_mode}
- Intervention: {intervention}

PRIOR-ART SEARCH RESULTS (titles of papers found):
{prior_art_titles}

Classify the prior-art state:
- NO_MATCH_FOUND: No results relate to the specific intervention
- TOPICAL_RELATED: Results discuss the same topic/material but NOT the specific intervention
- POSSIBLE_RELEVANCE: Results may relate to the intervention but don't specifically disclose it
- SPECIFIC_DISCLOSURE: A result specifically discloses this intervention for this device/failure
- IDENTICAL_DISCLOSURE: A result is essentially identical to the proposed intervention

Respond:
PRIOR_ART_STATE: <value>
WHAT_EARLIER_SOURCE_SAYS: <what the closest result actually discloses>
WHAT_IS_MISSING: <what gap exists between the prior art and the candidate>
OVERLAP: <where the overlap occurs>
"""

def reclassify_prior_art(candidate):
    """Phase 2-3: Reclassify prior-art state."""
    pa = candidate.get("prior_art", {})
    pa_results = pa.get("results", [])
    pa_titles = "\n".join(f"- {r.get('title','')}" for r in pa_results[:5])
    
    prompt = RECLASSIFY_PROMPT.format(
        device=candidate.get("device",""),
        failure_mode=candidate.get("failure_mode",""),
        intervention=candidate.get("intervention","")[:200],
        prior_art_titles=pa_titles)
    
    resp = llm_chat(prompt, system="You are a strict prior-art classification evaluator.")
    if not resp:
        return {"prior_art_state": "UNKNOWN", "what_earlier_says": "", "what_missing": "", "overlap": ""}
    
    state = "UNKNOWN"
    what_says = ""
    what_missing = ""
    overlap = ""
    for line in resp.strip().split("\n"):
        ls = line.strip()
        if ls.upper().startswith("PRIOR_ART_STATE:"):
            state = ls[len("PRIOR_ART_STATE:"):].strip()
        elif ls.upper().startswith("WHAT_EARLIER_SOURCE_SAYS:"):
            what_says = ls[len("WHAT_EARLIER_SOURCE_SAYS:"):].strip()
        elif ls.upper().startswith("WHAT_IS_MISSING:"):
            what_missing = ls[len("WHAT_IS_MISSING:"):].strip()
        elif ls.upper().startswith("OVERLAP:"):
            overlap = ls[len("OVERLAP:"):].strip()
    
    return {"prior_art_state": state, "what_earlier_says": what_says,
            "what_missing": what_missing, "overlap": overlap}

# ============================================================
# PHASE 7: FORENSIC RECLASSIFICATION OF V1/V2/V3
# ============================================================

def reclassify_all():
    """Reclassify all V1/V2/V3 candidates."""
    print("="*60)
    print("V1/V2/V3 FORENSIC RECLASSIFICATION")
    print("="*60)
    
    # Load all candidates
    v1 = json.loads(Path("corpus/corpus_progress.json").read_text())
    v2 = json.loads(Path("corpus_v2/corpus_v2_progress.json").read_text())
    v3 = json.loads(Path("corpus_v3/corpus_v3_progress.json").read_text())
    
    all_candidates = []
    for corpus, version in [(v1,'V1'), (v2,'V2'), (v3,'V3')]:
        for r in corpus:
            r['_corpus_version'] = version
            all_candidates.append(r)
    
    print(f"Total candidates: {len(all_candidates)} (V1:{len(v1)}, V2:{len(v2)}, V3:{len(v3)})")
    
    # Load progress
    progress_path = OUTPUT / "reclassification_progress.json"
    if progress_path.exists():
        reclassified = json.loads(progress_path.read_text())
        print(f"Resumed from {len(reclassified)} candidates")
    else:
        reclassified = []
    
    for candidate in all_candidates[len(reclassified):]:
        pid = candidate.get("problem_id", "unknown")
        version = candidate.get("_corpus_version", "?")
        print(f"\n  [{len(reclassified)+1}/{len(all_candidates)}] {version} {pid}: {candidate.get('device','')} ({candidate.get('failure_mode','')})")
        
        # Phase 1: Target alignment
        print(f"    checking target alignment...")
        alignment = check_target_alignment(candidate)
        print(f"    alignment: {alignment['alignment']}")
        
        # Phase 2-3: Prior-art reclassification (only if not OFF_TARGET)
        if alignment["alignment"] == "OFF_TARGET":
            new_classification = "WRONG_TARGET"
            pa_reclass = {"prior_art_state": "NOT_EVALUATED", "reason": "OFF_TARGET - terminated before prior-art"}
            print(f"    → WRONG_TARGET (terminated before prior-art)")
        else:
            # Only reclassify if there was a prior-art rejection
            old_reason = candidate.get("reason", candidate.get("classification",{}).get("reason",""))
            if "prior art" in old_reason.lower():
                print(f"    reclassifying prior-art...")
                pa_reclass = reclassify_prior_art(candidate)
                print(f"    prior_art_state: {pa_reclass['prior_art_state']}")
                
                # Determine new classification
                state = pa_reclass["prior_art_state"]
                if state in ["SPECIFIC_DISCLOSURE", "IDENTICAL_DISCLOSURE"]:
                    new_classification = "TRUE_SPECIFIC_PRIOR_ART"
                elif state == "POSSIBLE_RELEVANCE":
                    new_classification = "POSSIBLE_PRIOR_ART"
                elif state == "TOPICAL_RELATED":
                    new_classification = "TOPICAL_ONLY"
                elif state == "NO_MATCH_FOUND":
                    new_classification = "FALSE_PRIOR_ART_KILL"
                else:
                    new_classification = "POSSIBLE_PRIOR_ART"
            elif "evidence" in old_reason.lower():
                new_classification = "EVIDENCE_FAILURE"
                pa_reclass = {"prior_art_state": "NOT_EVALUATED", "reason": "evidence verification failed"}
            elif "adversarial" in old_reason.lower():
                new_classification = "ADVERSARIAL_NON_PRIOR_ART"
                pa_reclass = {"prior_art_state": "NOT_EVALUATED", "reason": "adversarial challenge failed"}
            elif "irrelevant" in old_reason.lower() or "no evidence" in old_reason.lower():
                new_classification = "EVIDENCE_FAILURE"
                pa_reclass = {"prior_art_state": "NOT_EVALUATED", "reason": "no relevant evidence"}
            else:
                new_classification = "UNKNOWN"
                pa_reclass = {"prior_art_state": "NOT_EVALUATED", "reason": old_reason}
            
            print(f"    → {new_classification}")
        
        result = {
            "problem_id": pid,
            "corpus_version": version,
            "device": candidate.get("device",""),
            "failure_mode": candidate.get("failure_mode",""),
            "intervention": candidate.get("intervention","")[:100],
            "old_rejection_reason": candidate.get("reason", candidate.get("classification",{}).get("reason","")),
            "old_prior_art_status": candidate.get("prior_art",{}).get("prior_art_status",""),
            "target_alignment": alignment,
            "prior_art_reclassification": pa_reclass,
            "new_classification": new_classification,
        }
        reclassified.append(result)
        progress_path.write_text(json.dumps(reclassified, indent=2, default=str))
    
    # Stats
    print(f"\n{'='*60}")
    print("RECLASSIFICATION STATISTICS")
    print(f"{'='*60}")
    
    new_dist = Counter(r["new_classification"] for r in reclassified)
    align_dist = Counter(r["target_alignment"]["alignment"] for r in reclassified)
    pa_dist = Counter(r["prior_art_reclassification"].get("prior_art_state","?") for r in reclassified)
    
    print(f"  New classification: {dict(new_dist)}")
    print(f"  Target alignment: {dict(align_dist)}")
    print(f"  Prior-art state: {dict(pa_dist)}")
    
    # Key metrics
    wrong_target = new_dist.get("WRONG_TARGET", 0)
    true_pa = new_dist.get("TRUE_SPECIFIC_PRIOR_ART", 0)
    topical_only = new_dist.get("TOPICAL_ONLY", 0)
    false_kills = new_dist.get("FALSE_PRIOR_ART_KILL", 0)
    possible_pa = new_dist.get("POSSIBLE_PRIOR_ART", 0)
    
    total_pa_rejected = sum(1 for r in reclassified if "prior art" in r.get("old_rejection_reason","").lower())
    false_kill_rate = false_kills / total_pa_rejected if total_pa_rejected else 0
    topical_rate = topical_only / total_pa_rejected if total_pa_rejected else 0
    
    print(f"\n  Total prior-art rejected: {total_pa_rejected}")
    print(f"  TRUE_SPECIFIC_PRIOR_ART: {true_pa}")
    print(f"  TOPICAL_ONLY (false kill): {topical_only}")
    print(f"  FALSE_PRIOR_ART_KILL: {false_kills}")
    print(f"  POSSIBLE_PRIOR_ART: {possible_pa}")
    print(f"  WRONG_TARGET: {wrong_target}")
    print(f"  False kill rate: {false_kill_rate:.1%}")
    print(f"  Topical-only rate: {topical_rate:.1%}")
    
    # Write artifacts
    report = {
        "experiment": "V1_V2_V3_RECLASSIFICATION",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_candidates": len(reclassified),
        "new_classification_distribution": dict(new_dist),
        "target_alignment_distribution": dict(align_dist),
        "prior_art_state_distribution": dict(pa_dist),
        "total_prior_art_rejected": total_pa_rejected,
        "true_specific_prior_art": true_pa,
        "topical_only_false_kills": topical_only,
        "false_prior_art_kills": false_kills,
        "possible_prior_art": possible_pa,
        "wrong_target": wrong_target,
        "false_kill_rate": round(false_kill_rate, 4),
        "topical_only_rate": round(topical_rate, 4),
        "results": reclassified,
    }
    (OUTPUT / "V1_V2_V3_RECLASSIFICATION.json").write_text(json.dumps(report, indent=2, default=str))
    
    md = f"""# V1/V2/V3 Prior-Art Forensic Reclassification

## TRUE NUMBERS

| Metric | Value |
|--------|-------|
| Total candidates | {len(reclassified)} |
| WRONG_TARGET | {wrong_target} |
| TRUE_SPECIFIC_PRIOR_ART | {true_pa} |
| TOPICAL_ONLY (false kill) | {topical_only} |
| FALSE_PRIOR_ART_KILL | {false_kills} |
| POSSIBLE_PRIOR_ART | {possible_pa} |
| EVIDENCE_FAILURE | {new_dist.get('EVIDENCE_FAILURE',0)} |
| ADVERSARIAL_NON_PRIOR_ART | {new_dist.get('ADVERSARIAL_NON_PRIOR_ART',0)} |

## Key Finding

Of {total_pa_rejected} candidates previously rejected for "prior art likely exists":
- {true_pa} were TRUE_SPECIFIC_PRIOR_ART (correct kill)
- {topical_only} were TOPICAL_ONLY (false kill — papers discuss same topic but don't disclose the intervention)
- {false_kills} were FALSE_PRIOR_ART_KILL (no match found)
- {possible_pa} were POSSIBLE_PRIOR_ART (may relate but don't specifically disclose)

**False kill rate: {false_kill_rate:.1%}**
**Topical-only rate: {topical_rate:.1%}**

## Target Alignment

{dict(align_dist)}

## New Classification Distribution

{dict(new_dist)}

## Prior-Art State Distribution

{dict(pa_dist)}
"""
    (OUTPUT / "PRIOR_ART_FORENSIC_V1.md").write_text(md)
    (OUTPUT / "PRIOR_ART_FORENSIC_V1.json").write_text(json.dumps(report, indent=2, default=str))
    
    # Target alignment report
    ta_report = {
        "experiment": "TARGET_ALIGNMENT_REPORT",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_candidates": len(reclassified),
        "alignment_distribution": dict(align_dist),
        "wrong_target_count": wrong_target,
        "results": [{"problem_id": r["problem_id"], "corpus_version": r["corpus_version"],
                     "device": r["device"], "failure_mode": r["failure_mode"],
                     "intervention": r["intervention"],
                     "alignment": r["target_alignment"]["alignment"],
                     "alignment_reason": r["target_alignment"]["reason"]} for r in reclassified],
    }
    (OUTPUT / "TARGET_ALIGNMENT_REPORT.json").write_text(json.dumps(ta_report, indent=2, default=str))
    
    print(f"\nArtifacts: {OUTPUT}/")
    return report

if __name__ == "__main__":
    reclassify_all()

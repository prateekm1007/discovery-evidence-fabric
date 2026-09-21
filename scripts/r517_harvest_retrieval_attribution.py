#!/usr/bin/env python3
"""R517 harvest: pull durable RETRIEVE attribution from 5 completed runs + classify straggler."""
import json, os, sys, time, hashlib
from urllib.request import Request, urlopen
from urllib.error import HTTPError

HF_TOKEN = os.environ.get("HF_TOKEN")
SESSIONS_FILE = os.environ.get("R517_SESSIONS", "R517/BATTERY2_SESSIONS.json")
OUTPUT_FILE = "R517/RETRIEVE_ATTRIBUTION_HARVEST.json"
SPACE_URL = "https://prateekm1-toscanini-prod-validation.hf.space"

def fetch_result(session_id, owner_key):
    url = f"{SPACE_URL}/api/run/{session_id}/result"
    req = Request(url, headers={"Authorization": f"Bearer {HF_TOKEN}", "X-Tosca-Owner": owner_key})
    with urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b"{}")

def main():
    if not HF_TOKEN:
        print("ERROR: HF_TOKEN not set"); sys.exit(1)
    
    with open(SESSIONS_FILE) as f:
        sessions = json.load(f)
    
    harvest = {
        "battery": sessions["battery"],
        "manifest_sha256": sessions["manifest_sha256"],
        "harvested_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "straggler": {
            "session_id": "ts_6d3b0347c780",
            "classification": "INFRA_STUCK",
            "reason": "RUNNING with no stage progress for >10h; durable branch has only created+awaiting_clarification events; no terminal state; Art. LXXIV: session loss is observer fact, not execution failure",
            "durable_events": ["created:ts_6d3b0347c780", "awaiting_clarification:ts_6d3b0347c780"]
        },
        "runs": []
    }
    
    completed = [s for s in sessions["submissions"] if s["session_id"] != "ts_6d3b0347c780"]
    print(f"Harvesting {len(completed)} completed runs...")
    
    for s in completed:
        sid = s["session_id"]
        okey = s["owner_key"]
        print(f"  Fetching {sid} (problem {s['problem_index']}, {s['declared_family']})...")
        try:
            result = fetch_result(sid, okey)
            status = result.get("status", "UNKNOWN")
            
            # Extract envelope provenance
            run_state = result.get("run_state", {})
            envelope = run_state.get("envelope", {})
            provenance = envelope.get("provenance", {})
            retrieval_attr = provenance.get("retrieval_fabric", {}).get("retrieval_attribution", [])
            stage_timing = run_state.get("stage_timing", {})
            stage_log = run_state.get("stage_log", [])
            
            # Get RETRIEVE stage timing
            retrieve_timing = stage_timing.get("RETRIEVE", {})
            
            # Count stages completed
            stages_completed = [e.get("stage") for e in stage_log if e.get("stage")]
            
            run_record = {
                "session_id": sid,
                "problem_index": s["problem_index"],
                "source_id": s["source_id"],
                "declared_family": s["declared_family"],
                "api_status": status,
                "stages_completed": stages_completed,
                "stage_timing": retrieve_timing,
                "n_retrieval_operations": len(retrieval_attr),
                "retrieval_attribution": retrieval_attr,
                "has_envelope_provenance": bool(retrieval_attr),
                "envelope_hash": hashlib.sha256(json.dumps(envelope, sort_keys=True).encode()).hexdigest()[:16]
            }
            
            # If we have retrieval attribution, compute critical-path stats
            if retrieval_attr:
                walls = [op.get("wall_seconds", 0) for op in retrieval_attr if op.get("wall_seconds")]
                records = [op.get("records_returned", 0) for op in retrieval_attr if op.get("records_returned") is not None]
                outcomes = [op.get("outcome", "unknown") for op in retrieval_attr]
                run_record["critical_path_wall_s"] = max(walls) if walls else 0
                run_record["total_search_wall_s"] = sum(walls)
                run_record["total_records"] = sum(records)
                run_record["outcome_distribution"] = {o: outcomes.count(o) for o in set(outcomes)}
                run_record["fanout_jobs"] = len(retrieval_attr)
                
                # Per-source breakdown
                source_stats = {}
                for op in retrieval_attr:
                    src = op.get("source_id", "unknown")
                    if src not in source_stats:
                        source_stats[src] = {"count": 0, "total_wall": 0, "total_records": 0, "failures": []}
                    source_stats[src]["count"] += 1
                    source_stats[src]["total_wall"] += op.get("wall_seconds", 0)
                    source_stats[src]["total_records"] += op.get("records_returned", 0) or 0
                    if op.get("outcome") not in ("success", "UNKNOWN"):
                        source_stats[src]["failures"].append(op.get("outcome"))
                run_record["source_breakdown"] = source_stats
            
            harvest["runs"].append(run_record)
            print(f"    status={status}, attribution={'YES' if retrieval_attr else 'NO'}, stages={len(stages_completed)}")
            
        except HTTPError as e:
            print(f"    HTTPError {e.code}: {e.reason}")
            harvest["runs"].append({
                "session_id": sid, "problem_index": s["problem_index"],
                "api_status": f"HTTP_{e.code}", "error": str(e)
            })
        except Exception as e:
            print(f"    Error: {e}")
            harvest["runs"].append({
                "session_id": sid, "problem_index": s["problem_index"],
                "api_status": "ERROR", "error": str(e)
            })
    
    # Summary stats
    successful = [r for r in harvest["runs"] if r.get("has_envelope_provenance")]
    harvest["summary"] = {
        "total_runs": len(harvest["runs"]),
        "with_attribution": len(successful),
        "straggler_count": 1,
        "straggler_classification": "INFRA_STUCK"
    }
    
    if successful:
        walls = [r["critical_path_wall_s"] for r in successful]
        total_walls = [r["total_search_wall_s"] for r in successful]
        harvest["summary"]["critical_path_wall_median_s"] = sorted(walls)[len(walls)//2]
        harvest["summary"]["critical_path_wall_max_s"] = max(walls)
        harvest["summary"]["critical_path_wall_min_s"] = min(walls)
        harvest["summary"]["total_search_wall_median_s"] = sorted(total_walls)[len(total_walls)//2]
        
        # Aggregate source stats
        agg_sources = {}
        for r in successful:
            for src, stats in r.get("source_breakdown", {}).items():
                if src not in agg_sources:
                    agg_sources[src] = {"total_ops": 0, "total_wall": 0, "total_records": 0, "failures": 0}
                agg_sources[src]["total_ops"] += stats["count"]
                agg_sources[src]["total_wall"] += stats["total_wall"]
                agg_sources[src]["total_records"] += stats["total_records"]
                agg_sources[src]["failures"] += len(stats["failures"])
        harvest["summary"]["aggregate_source_stats"] = agg_sources
    
    with open(OUTPUT_FILE, "w") as f:
        json.dump(harvest, f, indent=2)
    
    print(f"\nHarvest written to {OUTPUT_FILE}")
    print(f"Summary: {json.dumps(harvest['summary'], indent=2)}")

if __name__ == "__main__":
    main()

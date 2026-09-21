#!/usr/bin/env python3
"""R517: Read retrieval attribution from durable envelope_RETRIEVE.json on the durable branch."""
import json, os, subprocess, sys, hashlib

# Battery 2 session-to-run-directory mapping (from snapshot_log + run names)
# These are the run directories that match the battery 2 problems
RUN_DIRS = [
    "runs/toscanini_ui_ui_engine_block_hole_formation_999969",       # ts_6d3b0347c780 (straggler, problem 1)
    "runs/toscanini_ui_ui_engine_block_rupture_from_coolant_leak_and_997779",  # ts_102894096a26 (problem 2, Camry)
    "runs/toscanini_ui_ui_propeller_shaft_fracture_999961",         # ts_dd733590d006 (problem 3)
    "runs/toscanini_ui_ui_vibration_and_shift_difficulty_during_acce_998312",  # ts_314d0a15feea (problem 4)
    "runs/toscanini_ui_ui_intermittent_shifter_buzzing_with_loss_of_998276",  # ts_5a14ec4438fb (problem 5, Nissan Rogue)
    "runs/toscanini_ui_ui_spontaneous_parked_vehicle_fire_998352",  # ts_9f1f1bba3936 (problem 6, Nissan Rogue fire)
]

def git_show(path):
    """Read a file from origin/runtime-state-hf using git show."""
    try:
        result = subprocess.run(
            ["git", "show", f"origin/runtime-state-hf:{path}"],
            capture_output=True, timeout=30
        )
        if result.returncode == 0:
            return result.stdout.decode("utf-8", errors="replace")
        return None
    except Exception as e:
        return None

def main():
    OUTPUT_FILE = "R517/RETRIEVE_ATTRIBUTION_DURABLE.json"
    
    harvest = {
        "battery": "R517-retrieval-attribution-2",
        "source": "durable branch (origin/runtime-state-hf)",
        "harvest_method": "git show envelope_RETRIEVE.json",
        "runs": []
    }
    
    for run_dir in RUN_DIRS:
        env_path = f"{run_dir}/envelope_RETRIEVE.json"
        content = git_show(env_path)
        if content is None:
            print(f"  SKIP {run_dir}: envelope_RETRIEVE.json not found")
            continue
        
        try:
            envelope = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"  SKIP {run_dir}: JSON decode error: {e}")
            continue
        
        prov = envelope.get("provenance", {})
        rf = prov.get("retrieval_fabric", {})
        ra = rf.get("retrieval_attribution", {})
        
        if not ra or not isinstance(ra, dict):
            print(f"  SKIP {run_dir}: no retrieval_attribution")
            continue
        
        run_name = run_dir.split("/")[-1]
        
        # Extract key metrics
        run_record = {
            "run_dir": run_dir,
            "run_name": run_name,
            "schema": ra.get("schema"),
            "mode": ra.get("mode"),
            "n_jobs": ra.get("n_jobs"),
            "fanout_wall_s": ra.get("fanout_wall_s"),
            "total_search_call_s": ra.get("total_search_call_s"),
            "max_job_wall_s": ra.get("max_job_wall_s"),
            "assemble_s": ra.get("assemble_s"),
            "worker_queue_wait_s": ra.get("worker_queue_wait_s"),
            "peak_concurrency_observed": ra.get("peak_concurrency_observed"),
            "max_workers_configured": ra.get("max_workers_configured"),
            "max_workers_effective": ra.get("max_workers_effective"),
            "records_returned": ra.get("records_returned"),
            "records_admitted": ra.get("records_admitted"),
            "canonical_merges": ra.get("canonical_merges"),
            "enrichment_s": ra.get("enrichment_s"),
            "jobs": ra.get("jobs", []),
        }
        
        # Source breakdown from jobs
        source_stats = {}
        for job in ra.get("jobs", []):
            src = job.get("source_id", "unknown")
            if src not in source_stats:
                source_stats[src] = {"count": 0, "total_wall": 0, "total_records": 0, "failures": [], "max_wall": 0}
            source_stats[src]["count"] += 1
            wall = job.get("job_wall_s", 0)
            source_stats[src]["total_wall"] += wall
            source_stats[src]["max_wall"] = max(source_stats[src]["max_wall"], wall)
            records = job.get("records_returned", 0) or 0
            source_stats[src]["total_records"] += records
            outcome = job.get("outcome", "unknown")
            if outcome not in ("successful",):
                source_stats[src]["failures"].append({"outcome": outcome, "wall_s": wall})
        run_record["source_breakdown"] = source_stats
        
        harvest["runs"].append(run_record)
        print(f"  OK {run_name}: n_jobs={ra.get('n_jobs')}, fanout_wall={ra.get('fanout_wall_s')}s, total_search={ra.get('total_search_call_s')}s, records={ra.get('records_returned')}")
    
    # Summary
    if harvest["runs"]:
        walls = [r["fanout_wall_s"] for r in harvest["runs"] if r.get("fanout_wall_s")]
        search_walls = [r["total_search_call_s"] for r in harvest["runs"] if r.get("total_search_call_s")]
        max_job_walls = [r["max_job_wall_s"] for r in harvest["runs"] if r.get("max_job_wall_s")]
        harvest["summary"] = {
            "n_runs": len(harvest["runs"]),
            "fanout_wall_median_s": sorted(walls)[len(walls)//2] if walls else None,
            "fanout_wall_max_s": max(walls) if walls else None,
            "fanout_wall_min_s": min(walls) if walls else None,
            "total_search_wall_median_s": sorted(search_walls)[len(search_walls)//2] if search_walls else None,
            "total_search_wall_max_s": max(search_walls) if search_walls else None,
            "max_job_wall_median_s": sorted(max_job_walls)[len(max_job_walls)//2] if max_job_walls else None,
            "max_job_wall_max_s": max(max_job_walls) if max_job_walls else None,
        }
        
        # Aggregate source stats across all runs
        agg = {}
        for r in harvest["runs"]:
            for src, stats in r.get("source_breakdown", {}).items():
                if src not in agg:
                    agg[src] = {"total_ops": 0, "total_wall": 0, "total_records": 0, "max_wall_seen": 0, "failures": 0}
                agg[src]["total_ops"] += stats["count"]
                agg[src]["total_wall"] += stats["total_wall"]
                agg[src]["total_records"] += stats["total_records"]
                agg[src]["max_wall_seen"] = max(agg[src]["max_wall_seen"], stats["max_wall"])
                agg[src]["failures"] += len(stats["failures"])
        harvest["summary"]["aggregate_source_stats"] = agg
        
        # Identify slowest source
        if agg:
            slowest = max(agg.items(), key=lambda x: x[1]["max_wall_seen"])
            harvest["summary"]["slowest_source"] = {"source": slowest[0], "max_wall_s": slowest[1]["max_wall_seen"]}
    
    with open(OUTPUT_FILE, "w") as f:
        json.dump(harvest, f, indent=2)
    
    print(f"\nHarvest written to {OUTPUT_FILE}")
    print(json.dumps(harvest.get("summary", {}), indent=2))

if __name__ == "__main__":
    main()

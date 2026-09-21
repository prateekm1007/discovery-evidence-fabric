#!/usr/bin/env python3
"""Deep analysis of the 2 runs with complete RETRIEVE attribution."""
import json, subprocess

def git_show(path):
    result = subprocess.run(
        ["git", "show", f"origin/runtime-state-hf:{path}"],
        capture_output=True, timeout=30
    )
    return json.loads(result.stdout.decode("utf-8", errors="replace"))

runs = [
    ("engine_block_hole_formation_999969", "ts_6d3b0347c780", "straggler"),
    ("propeller_shaft_fracture_999961", "ts_dd733590d006", "completed"),
]

for run_name, sid, label in runs:
    env = git_show(f"runs/toscanini_ui_ui_{run_name}/envelope_RETRIEVE.json")
    rf = env["provenance"]["retrieval_fabric"]
    ra = rf["retrieval_attribution"]
    
    print(f"\n{'='*70}")
    print(f"RUN: {run_name} ({sid}, {label})")
    print(f"{'='*70}")
    print(f"  schema: {ra['schema']}")
    print(f"  mode: {ra['mode']}")
    print(f"  n_jobs: {ra['n_jobs']}")
    print(f"  fanout_wall_s: {ra['fanout_wall_s']}")
    print(f"  total_search_call_s: {ra['total_search_call_s']}")
    print(f"  max_job_wall_s: {ra['max_job_wall_s']}")
    print(f"  assemble_s: {ra['assemble_s']}")
    print(f"  worker_queue_wait_s: {ra['worker_queue_wait_s']}")
    print(f"  peak_concurrency: {ra['peak_concurrency_observed']}")
    print(f"  records_returned: {ra['records_returned']}")
    print(f"  records_admitted: {ra['records_admitted']}")
    print(f"  canonical_merges: {ra['canonical_merges']}")
    print(f"  enrichment_s: {ra.get('enrichment_s', 'N/A')}")
    
    print(f"\n  Per-job breakdown (sorted by wall_s desc):")
    jobs = sorted(ra["jobs"], key=lambda j: j.get("job_wall_s", 0), reverse=True)
    for j in jobs:
        print(f"    [{j['index']:2d}] {j['source_id']:25s} wall={j['job_wall_s']:7.3f}s search_ms={str(j.get('search_call_ms','?')):>6} records={str(j.get('records_returned','?')):>4} outcome={j['outcome']}")
    
    print(f"\n  CRITICAL PATH ANALYSIS:")
    fanout = ra["fanout_wall_s"]
    max_job = ra["max_job_wall_s"]
    total = ra["total_search_call_s"]
    print(f"    fanout_wall = {fanout:.3f}s")
    print(f"    max_job_wall = {max_job:.3f}s (the bottleneck)")
    print(f"    total_search_call = {total:.3f}s (aggregate)")
    print(f"    residual (fanout - max_job) = {fanout - max_job:.3f}s")
    print(f"    aggregate parallelism = {total / fanout:.1f}x")
    
    # Source breakdown
    print(f"\n  Source breakdown:")
    source_stats = {}
    for j in ra["jobs"]:
        src = j["source_id"]
        if src not in source_stats:
            source_stats[src] = {"count": 0, "walls": [], "records": 0, "failures": 0}
        source_stats[src]["count"] += 1
        source_stats[src]["walls"].append(j.get("job_wall_s", 0))
        source_stats[src]["records"] += j.get("records_returned", 0) or 0
        if j["outcome"] != "successful":
            source_stats[src]["failures"] += 1
    
    for src, stats in sorted(source_stats.items(), key=lambda x: max(x[1]["walls"]), reverse=True):
        max_w = max(stats["walls"])
        avg_w = sum(stats["walls"]) / len(stats["walls"])
        print(f"    {src:25s} count={stats['count']:2d} max={max_w:7.3f}s avg={avg_w:7.3f}s records={stats['records']:3d} failures={stats['failures']}")

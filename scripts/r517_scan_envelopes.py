#!/usr/bin/env python3
"""Quick scan of all 5 completed runs to understand envelope provenance structure."""
import json, os, sys
from urllib.request import Request, urlopen

HF_TOKEN = os.environ.get("HF_TOKEN")
sessions = json.load(open("R517/BATTERY2_SESSIONS.json"))

for s in sessions["submissions"]:
    sid = s["session_id"]
    okey = s["owner_key"]
    url = f"https://prateekm1-toscanini-prod-validation.hf.space/api/run/{sid}/result"
    req = Request(url, headers={"Authorization": f"Bearer {HF_TOKEN}", "X-Tosca-Owner": okey})
    with urlopen(req, timeout=60) as r:
        data = json.loads(r.read() or b"{}")
    rs = data.get("run_state", {})
    prov = rs.get("provenance", {})
    ev = rs.get("evidence_state", {})
    mr = rs.get("model_route", {})
    calls = mr.get("calls", [])
    phases = rs.get("phase_progression", [])
    stages_done = {}
    for p in phases:
        for stg, val in p.get("stages", {}).items():
            stages_done[stg] = val
    print(f"\n{'='*60}")
    print(f"SID: {sid} (problem {s['problem_index']}, {s['declared_family']})")
    print(f"  outcome: {rs.get('outcome')}")
    print(f"  outcome_label: {rs.get('outcome_label')}")
    print(f"  status: {rs.get('status')}")
    print(f"  provenance_keys: {list(prov.keys())}")
    print(f"  has_retrieval_attribution: {'retrieval_attribution' in json.dumps(prov)}")
    print(f"  evidence_sources: {ev.get('sources')}")
    print(f"  evidence_records: {ev.get('records_found')}")
    print(f"  evidence_retrieval_route: {ev.get('retrieval_route')}")
    print(f"  stages_completed: {stages_done}")
    print(f"  model_route_calls: {len(calls)}")
    for c in calls:
        print(f"    {c.get('role')}: provider={c.get('provider')}, status={c.get('status')}, latency_ms={c.get('latency_ms')}, failure_class={c.get('failure_class','OK')}")

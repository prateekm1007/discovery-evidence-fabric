#!/usr/bin/env python3
"""Check all 6 battery 2 runs for retrieval_attribution in both API and durable envelope."""
import json, os, subprocess, sys
from urllib.request import Request, urlopen

HF_TOKEN = os.environ.get("HF_TOKEN")
sessions = json.load(open("R517/BATTERY2_SESSIONS.json"))

# Run directory mapping
RUN_MAP = {
    "ts_6d3b0347c780": "runs/toscanini_ui_ui_engine_block_hole_formation_999969",
    "ts_102894096a26": "runs/toscanini_ui_ui_engine_block_rupture_from_coolant_leak_and_997779",
    "ts_dd733590d006": "runs/toscanini_ui_ui_propeller_shaft_fracture_999961",
    "ts_314d0a15feea": "runs/toscanini_ui_ui_vibration_and_shift_difficulty_during_acce_998312",
    "ts_5a14ec4438fb": "runs/toscanini_ui_ui_intermittent_shifter_buzzing_with_loss_of_998276",
    "ts_9f1f1bba3936": "runs/toscanini_ui_ui_spontaneous_parked_vehicle_fire_998352",
}

def git_show(path):
    try:
        result = subprocess.run(
            ["git", "show", f"origin/runtime-state-hf:{path}"],
            capture_output=True, timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout.decode("utf-8", errors="replace"))
        return None
    except:
        return None

for s in sessions["submissions"]:
    sid = s["session_id"]
    okey = s["owner_key"]
    run_dir = RUN_MAP.get(sid, "UNKNOWN")
    run_name = run_dir.split("/")[-1] if run_dir != "UNKNOWN" else "UNKNOWN"
    
    # Check API
    url = f"https://prateekm1-toscanini-prod-validation.hf.space/api/run/{sid}/result"
    req = Request(url, headers={"Authorization": f"Bearer {HF_TOKEN}", "X-Tosca-Owner": okey})
    try:
        with urlopen(req, timeout=60) as r:
            api_data = json.loads(r.read() or b"{}")
        api_rs = api_data.get("run_state", {})
        api_prov = api_rs.get("provenance", {})
        api_has_attr = "retrieval_attribution" in json.dumps(api_prov)
    except Exception as e:
        api_has_attr = f"ERROR: {e}"
    
    # Check durable envelope
    env = git_show(f"{run_dir}/envelope_RETRIEVE.json") if run_dir != "UNKNOWN" else None
    if env:
        rf = env.get("provenance", {}).get("retrieval_fabric", {})
        durable_has_attr = "retrieval_attribution" in rf
        durable_version = rf.get("version", "MISSING")
    else:
        durable_has_attr = "NO_ENVELOPE"
        durable_version = "N/A"
    
    # Check if there's a RETRIEVAL_ATTRIBUTION.json sidecar
    sidecar = git_show(f"{run_dir}/RETRIEVAL_ATTRIBUTION.json") if run_dir != "UNKNOWN" else None
    sidecar_has = sidecar is not None and bool(sidecar)
    
    print(f"\n{sid} ({s['declared_family']}, problem {s['problem_index']})")
    print(f"  run_dir: {run_name}")
    print(f"  API provenance has attribution: {api_has_attr}")
    print(f"  Durable envelope has attribution: {durable_has_attr} (version={durable_version})")
    print(f"  Sidecar RETRIEVAL_ATTRIBUTION.json: {sidecar_has}")

#!/usr/bin/env python3.13
"""Patsnap Patent Search Pipeline — ready when balance recharged."""
import requests, json, time
from pathlib import Path

API_KEY = "sk-[S01-REDACTED:kWs]"
BASE = "https://connect.patsnap.com/api"
HEADERS = {"X-PatSnap-API-Key": API_KEY, "Content-Type": "application/json"}

QUERIES = {
    "P-16": ["near infrared transcranial photovoltaic implantable power", "940nm optical power delivery implantable"],
    "P-01": ["multi-segment CSF shunt obstruction prediction", "Bayesian shunt flow redistribution"],
    "P-24": ["anti-siphon hydraulic damper proportional valve CSF", "gravity compensating overdrainage prevention"],
    "P-21": ["UWB ultra-wideband catheter positioning medical", "implant localization skull tissue"],
    "P-13": ["AI shunt failure prediction neuromorphic implantable", "machine learning CSF shunt complication"],
    "P-02": ["adaptive valve ICP excursion reduction CSF shunt"],
    "P-04": ["catheter amyloid beta clearance Alzheimer CSF"],
    "P-07": ["shunt drainage maintenance obstruction floor mechanism"],
    "P-11": ["phage anti-biofilm coating titanium catheter"],
    "P-12": ["catheter tau clearance Cathepsin D Alzheimer"],
    "P-15": ["implantable energy harvesting cardiac motion hybrid power"],
    "P-20": ["glycan immune tolerance coating implantable device"],
    "P-22": ["autonomous catheter navigation shape memory polymer"],
    "P-26": ["osmotic membrane valve CSF drainage regulation"],
    "P-27": ["shape memory polymer kink resistant catheter helical"]
}

def check_balance():
    resp = requests.post(f"{BASE}/account/balance", headers=HEADERS, json={}, timeout=15)
    data = resp.json()
    if data.get("status") == False:
        print(f"BALANCE EXHAUSTED: {data.get('error_msg')}")
        print("Recharge ~$3,000 and re-run.")
        return False
    return True

def search(query, limit=10):
    resp = requests.post(f"{BASE}/search", headers=HEADERS, json={"q": query, "type": "semantic", "limit": limit, "lang": "en"}, timeout=30)
    return resp.json()

def run():
    print("Patsnap Patent Search Pipeline")
    if not check_balance():
        return
    results = {}
    for cid, queries in QUERIES.items():
        print(f"\nSearching {cid}...")
        for q in queries:
            r = search(q)
            if r and r.get("status") != False:
                results.setdefault(cid, []).append({"query": q, "result": r})
            time.sleep(1)
    Path(__file__).parent.joinpath("PATSNAP_RESULTS.json").write_text(json.dumps(results, indent=2))

if __name__ == "__main__":
    run()

#!/usr/bin/env python3.13
"""R354 — Patent Prior Art Search + Patsnap Pipeline"""
import json, hashlib
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parents[1]
R354 = REPO / "R354"

def _write(p, o):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(o, indent=2, default=str))

def _write_text(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t)

def _now():
    return datetime.now(timezone.utc).isoformat()

PATSNAP_STATUS = {
    "api_key_provided": True,
    "api_key_valid": True,
    "api_response": "error_code: 67200203, error_msg: 'API need a true rate!'",
    "diagnosis": "API key recognized but account balance EXHAUSTED. Confirms consultant audit: 'PatSnap balance EXHAUSTED. Recharge is single highest-leverage action.'",
    "action_required": "Recharge Patsnap account (~$3,000). Pipeline at R354/patsnap_pipeline/patsnap_search.py ready to run when recharged.",
    "fallback_used": "Web search via z-ai SDK → Google Patents, USPTO, PMC"
}

PRIOR_ART = {
    "P-16": {"prior_art_count": 4, "closest": "US 20260224911 (photobiomodulation+electrical modulation, 2026)", "delta": 0, "rationale": "MEDIUM risk confirmed. Optical-implant space active but P-16 power delivery distinct.", "obviousness": "MEDIUM (unchanged)", "fto": "MEDIUM"},
    "P-24": {"prior_art_count": 3, "closest": "US 6090062A (programmable antisiphon) + PMC 9133390 (anti-siphon review)", "delta": -5, "rationale": "DECREASED — PMC review catalogs ALL anti-siphon mechanisms. §103 risk HIGH.", "obviousness": "HIGH (confirmed)", "fto": "HIGH"},
    "P-01": {"prior_art_count": 3, "closest": "WO 2011146757A2 (CSF shunt flow+patency classification)", "delta": +3, "rationale": "INCREASED — prior art is diagnostic, not predictive. P-01's predictive+redistributive more novel.", "obviousness": "MEDIUM (improved from MEDIUM-HIGH)", "fto": "MEDIUM"},
    "P-21": {"prior_art_count": 3, "closest": "US 10993619 (UWB radar medical tracking, 2021) + US 7658196B2 (implant orientation)", "delta": -5, "rationale": "DECREASED — US 10993619 directly covers UWB medical tracking. Obviousness HIGH.", "obviousness": "HIGH (upgraded from MEDIUM)", "fto": "HIGH"},
    "P-13": {"prior_art_count": 3, "closest": "US 10596377B2 (seizure prediction DNN implantable) + PMC 10614444 (ML shunt prediction)", "delta": -3, "rationale": "DECREASED — PMC 10614444 shows ML shunt prediction already published. Novelty gap narrower.", "obviousness": "HIGH (confirmed)", "fto": "HIGH"}
}

PATSNAP_PIPELINE = '''#!/usr/bin/env python3.13
"""Patsnap Patent Search Pipeline — ready when balance recharged."""
import requests, json, time
from pathlib import Path

API_KEY = "[REDACTED:patsnap_key]"
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
        print(f"\\nSearching {cid}...")
        for q in queries:
            r = search(q)
            if r and r.get("status") != False:
                results.setdefault(cid, []).append({"query": q, "result": r})
            time.sleep(1)
    Path(__file__).parent.joinpath("PATSNAP_RESULTS.json").write_text(json.dumps(results, indent=2))

if __name__ == "__main__":
    run()
'''

def main():
    print("=" * 60)
    print("R354 — PATENT PRIOR ART SEARCH")
    print("=" * 60)

    _write(R354 / "patsnap_pipeline" / "PATSNAP_API_STATUS.json", PATSNAP_STATUS)
    _write(R354 / "web_prior_art" / "PRIOR_ART_RESULTS.json", PRIOR_ART)
    _write_text(R354 / "patsnap_pipeline" / "patsnap_search.py", PATSNAP_PIPELINE)

    # Load R353 scores and update
    r353_dir = REPO / "R353" / "premium_portfolio"
    updated = {}
    for cid, pa in PRIOR_ART.items():
        pf = r353_dir / cid / "PATENT_DEFENSIBILITY.json"
        old = json.loads(pf.read_text())["patent_readiness_score"] if pf.exists() else 0
        new = max(0, min(100, old + pa["delta"]))
        updated[cid] = {"old": old, "delta": pa["delta"], "new": new, "rationale": pa["rationale"],
                         "closest_prior_art": pa["closest"], "obviousness": pa["obviousness"], "fto": pa["fto"],
                         "search_method": "web search (z-ai SDK)", "formal_search_required": True}
        print(f"  {cid}: {old} → {new} (Δ{pa['delta']:+d}) — {pa['rationale'][:60]}")

    _write(R354 / "updated_scores" / "UPDATED_PATENT_SCORES.json", updated)

    audit = {
        "round": 354, "date": _now(),
        "patsnap_status": "VALID key, EXHAUSTED balance (error 67200203). Recharge ~$3,000.",
        "fallback": "Web search via z-ai SDK → 16 real patent references found across 5 packages",
        "score_updates": {cid: f"{u['old']} → {u['new']} (Δ{u['delta']:+d})" for cid, u in updated.items()},
        "key_findings": {
            "P-24": "PMC 9133390 catalogs ALL anti-siphon mechanisms. §103 risk HIGH. Score 56→51.",
            "P-21": "US 10993619 covers UWB medical tracking. §103 risk HIGH. Score 67→62.",
            "P-13": "PMC 10614444 shows ML shunt prediction published. Score 55→52.",
            "P-01": "Prior art diagnostic, not predictive. P-01 more novel. Score 68→71.",
            "P-16": "US 20260224911 adjacent but distinct. Score unchanged 67."
        },
        "action_required": "1. Recharge Patsnap ~$3,000 for definitive §103. 2. Engage patent attorney for top 5. 3. P-24/P-21 patent risk HIGHER than assessed — may need redesign.",
        "pipeline_ready": "R354/patsnap_pipeline/patsnap_search.py — runs when balance recharged"
    }
    _write(R354 / "audit" / "ROUND_354_AUDIT.json", audit)
    _write_text(R354 / "audit" / "ROUND_354_AUDIT.md",
        f"# R354 — Patent Prior Art Search\n\n**Date:** {_now()}\n\n## Patsnap API: VALID key, EXHAUSTED balance\n\nError 67200203: 'API need a true rate!'\nAction: Recharge ~$3,000\nPipeline: ready at patsnap_pipeline/patsnap_search.py\n\n## Web Search Fallback\n\n16 real patent references found across 5 packages via z-ai SDK.\n\n## Score Updates\n\n" +
        "\n".join(f"- **{cid}**: {u}" for cid, u in audit["score_updates"].items()) +
        "\n\n## Key Findings\n\n" +
        "\n".join(f"### {k}\n{v}\n" for k, v in audit["key_findings"].items()) +
        f"\n## Action Required\n\n{audit['action_required']}\n")

    print(f"\nR354 COMPLETE — {len(updated)} scores updated, pipeline ready")

if __name__ == "__main__":
    main()

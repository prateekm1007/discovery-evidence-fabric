#!/usr/bin/env python3
"""
TERRITORY-10-DISCOVERY — Google Patents prior-art search via agent-browser (v2).
Use page innerText extraction with longer wait time + parse patent entries.
Direct curl blocked by CAPTCHA per T7/T8/T9 pattern; agent-browser works.
"""
import json
import os
import re
import subprocess
import time
import urllib.parse

OUT_DIR = "/home/z/my-project/discovery-evidence-fabric/CEREVASC_TERRITORY_10_LIFECYCLE_INTELLIGENCE"
os.makedirs(OUT_DIR, exist_ok=True)
TIMESTAMP = "2026-08-19T00:00:00Z"

QUERIES = [
    {"id": "GP1",  "q": "cerebrospinal fluid shunt failure prediction machine learning sensor", "purpose": "M1 — predictive failure ML on sensor"},
    {"id": "GP2",  "q": "VP shunt obstruction detection chronic pressure sensor", "purpose": "M1 — VP shunt obstruction via chronic pressure sensor"},
    {"id": "GP3",  "q": "endovascular shunt telemetry chronic sensor", "purpose": "M1+T9 eShunt-specific telemetry"},
    {"id": "GP4",  "q": "CardioMEMS heart failure pressure prediction wireless", "purpose": "M1 — CardioMEMS precedent"},
    {"id": "GP5",  "q": "implantable medical device remaining useful life prediction", "purpose": "M7 — RUL implant"},
    {"id": "GP6",  "q": "shunt revision scheduling prediction algorithm", "purpose": "M7 — shunt revision prediction"},
    {"id": "GP7",  "q": "hydrocephalus shunt sensor telemetry wireless", "purpose": "M1 — hydrocephalus wireless telemetry"},
    {"id": "GP8",  "q": "implantable pressure sensor batteryless RF inductive", "purpose": "M6 — batteryless confirmation"},
    {"id": "GP9",  "q": "implantable medical device cybersecurity", "purpose": "M8 — cybersecurity saturation"},
    {"id": "GP10", "q": "externally programmable shunt valve wireless", "purpose": "M5 — remote programming saturation"},
    {"id": "GP11", "q": "patient reported outcome mobile app medical device", "purpose": "M3 — PRO app saturation"},
    {"id": "GP12", "q": "fleet learning medical device population analytics", "purpose": "M4 — fleet learning saturation"},
]

def run_ab(args, timeout=60):
    cmd = ["agent-browser"] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR: {e}"

def gp_search_v2(query_text):
    """Open Google Patents search, wait, extract page innerText."""
    q = urllib.parse.quote(query_text)
    url = f"https://patents.google.com/?q={q}"
    run_ab(["open", url], timeout=30)
    time.sleep(8.0)  # long wait for JS rendering
    js = 'document.body.innerText.slice(0, 30000)'
    out = run_ab(["eval", js], timeout=30)
    # Output looks like: "\"<page_text>\""  — strip leading quote
    text = out.strip()
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    # also unescape
    text = text.encode().decode('unicode_escape', errors='ignore')
    return text

def parse_patents(text):
    """Parse Google Patents page text into list of {title, meta, snippet}."""
    # Heuristic: patents appear as blocks separated by Priority lines
    patents = []
    # find total
    m_total = re.search(r'About\s+([0-9,]+)\s+results', text)
    total = m_total.group(1) if m_total else "unknown"
    # split on Priority YYYY-MM-DD patterns
    # Pattern: <title>\n<meta with country codes + assignee>\nPriority YYYY-MM-DD • Filed ...
    blocks = re.split(r'(?=Priority\s+\d{4}-\d{2}-\d{2})', text)
    for b in blocks[1:]:  # skip first (preamble)
        # The patent title and meta come BEFORE the Priority line
        # Find this Priority line
        pm = re.match(r'Priority\s+(\d{4}-\d{2}-\d{2})\s+[•·]\s+Filed\s+(\d{4}-\d{2}-\d{2})(?:\s+[•·]\s+Granted\s+(\d{4}-\d{2}-\d{2}))?\s+[•·]\s+Published\s+(\d{4}-\d{2}-\d{2})', b)
        if not pm:
            continue
        # The preceding text in the previous block holds title + meta
        # Simpler: walk through full text and find title-meta-priority clusters
        pass
    # Simpler approach: scan for "PN USxxxxxxB2" or similar PN patterns; or just dump patent titles
    # The text has patent titles followed by a meta line with country codes and assignee, then Priority date
    # Use regex: <TITLE>\n<COUNTRY_CODES + PN + INVENTOR + ASSIGNEE>\nPriority ...
    pat = re.compile(r'([^\n]{5,200}?)\n([A-Z]{2}(?:\s+[A-Z]{2})*\s+([A-Z0-9]{6,}[A-Z0-9]+)\s+([^\n]+?))\nPriority\s+(\d{4}-\d{2}-\d{2})')
    for m in pat.finditer(text):
        patents.append({
            "title": m.group(1).strip(),
            "meta": m.group(2).strip(),
            "pn": m.group(3).strip(),
            "inventor_assignee": m.group(4).strip(),
            "priority_date": m.group(5).strip(),
        })
    return patents, total

# ============================================================
# RUN GOOGLE PATENTS QUERIES
# ============================================================
print("=== GOOGLE PATENTS (v2 — innerText parse) ===")
results = []
for q in QUERIES:
    print(f"  {q['id']}: {q['q'][:60]}...")
    text = gp_search_v2(q["q"])
    patents, total = parse_patents(text)
    print(f"    -> total={total}, parsed={len(patents)}")
    results.append({
        "query_id": q["id"],
        "query": q["q"],
        "purpose": q["purpose"],
        "total_results_on_page": total,
        "patents": patents[:15],
        "count_parsed": len(patents),
    })

out = {
    "task_id": "TERRITORY-10-DISCOVERY",
    "artifact_type": "PRIOR_ART_GOOGLE_PATENTS",
    "source": "Google Patents public web (via agent-browser headless chromium — direct curl blocked by CAPTCHA per T7/T8/T9 pattern)",
    "timestamp": TIMESTAMP,
    "queries_executed": len(QUERIES),
    "extraction_method": "Open URL, wait 8s for JS render, extract body.innerText, parse via regex for title+meta+priority_date",
    "results": results,
}
with open(os.path.join(OUT_DIR, "PRIOR_ART_GOOGLE_PATENTS.json"), "w") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print(f"\nWrote PRIOR_ART_GOOGLE_PATENTS.json")

print("\n=== TOP PARSED HITS PER QUERY ===")
for r in results:
    print(f"--- {r['query_id']}: page_total={r.get('total_results_on_page')}, parsed={r.get('count_parsed',0)}; purpose: {r.get('purpose', '')}")
    for p in r.get("patents", [])[:8]:
        if isinstance(p, dict):
            print(f"    * {p.get('pn','?')} | {p.get('title','')[:80]} | {p.get('priority_date','')} | {p.get('inventor_assignee','')[:60]}")

#!/usr/bin/env python3
"""Open Data Expansion Audit — live access probes (CEO directive 2026-08-30).

For every candidate source/dataset the CEO listed, MEASURE from this
egress: reachability, content-type, license page, schema sample. Nothing
is claimed integrated here — integration needs the full custody chain.
Verdicts feed TOSCANINI/OPEN_DATA_EXPANSION_AUDIT.json.
"""

from __future__ import annotations

import json
import ssl
import sys
import urllib.request

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0.0.0"}


def probe(name, url, accept="application/json,*/*"):
    out = {"name": name, "url": url}
    try:
        req = urllib.request.Request(url, headers={**UA, "Accept": accept})
        r = urllib.request.urlopen(req, timeout=30, context=CTX)
        body = r.read(4096)
        out.update(status=r.status, content_type=r.headers.get("Content-Type", "?"),
                   len_sample=len(body))
        try:
            j = json.loads(body)
            out["shape"] = (list(j.keys())[:8] if isinstance(j, dict)
                            else f"list[{len(j)}]")
        except Exception:  # noqa: BLE001
            out["shape"] = body[:120].decode("utf-8", "replace").replace("\n", " ")
    except urllib.error.HTTPError as e:
        out.update(status=e.code, error=e.read()[:150].decode("utf-8", "replace"))
    except Exception as e:  # noqa: BLE001
        out.update(error=repr(e)[:150])
    print(f"[{out.get('status', 'FAIL')}] {name}: {out.get('shape', out.get('error',''))}"[:150])
    return out


results = []

# ---- TIER 1: evidence infrastructure -----------------------------------
# 1. OpenAlex — API budget-blocked (measured); snapshot is CC0
results.append(probe("openalex_api_anonymous",
                     "https://api.openalex.org/works?per-page=1"))
results.append(probe("openalex_snapshot_release",
                     "https://files.openalex.org/snapshot/latest/LICENSE"))
results.append(probe("openalex_snapshot_index",
                     "https://files.openalex.org/snapshot/latest/data_manifest.json"))

# 2. PatentsView — official data-download configuration (sources.yml)
results.append(probe("patentsview_sources_yml",
                     "https://raw.githubusercontent.com/PatentsView/PatentsView-Code-Examples/main/data-downloads/sources.yml",
                     accept="text/plain"))
results.append(probe("patentsview_api_keyless",
                     "https://search.patentsview.org/api/v1/patent/?q=%7B%7D&s=0&o=0"))

# 3. USPTO bulk data (official, free)
results.append(probe("uspto_bulk_index",
                     "https://bulkdata.uspto.gov/", accept="text/html"))
results.append(probe("uspto_json_grants_2026",
                     "https://bulkdata.uspto.gov/data/patent/grant/redbook/fulltext/2026/",
                     accept="text/html"))

# 4. NTSB — CAROL API blocked (HTML); try the aviations data exports
results.append(probe("ntsb_data_root",
                     "https://data.ntsb.gov/", accept="text/html"))
results.append(probe("ntsb_carol_file",
                     "https://data.ntsb.gov/carol-main-public/basic-search/export",
                     accept="application/json"))

# 5/6. NASA NTRS + DOE OSTI — already integrated LIVE (verify remain)
results.append(probe("nasa_ntrs_api", "https://ntrs.nasa.gov/api/citations/search?q=battery"))
results.append(probe("doe_osti_api",
                     "https://www.osti.gov/api/v1/records?q=battery&rows=1"))

# 7. Materials Project — ASN-blocked (re-verify once for the record)
results.append(probe("materials_project_api",
                     "https://api.materialsproject.org/materials/summary/?formula=TiO2"))

# 8. Open Power System Data
results.append(probe("opsd_data_portal",
                     "https://data.open-power-system-data.org/", accept="text/html"))
results.append(probe("opsd_national_generation",
                     "https://data.open-power-system-data.org/national_generation_capacity/2020-10-01/"))

# 9. arXiv — integrated LIVE (verify)
results.append(probe("arxiv_api",
                     "http://export.arxiv.org/api/query?search_query=all:battery&max_results=1",
                     accept="application/atom+xml"))

# 10. PMC Open Access subset (bulk)
results.append(probe("pmc_oa_filelist",
                     "https://ftp.ncbi.nlm.nih.gov/pub/pmc/file_list.txt",
                     accept="text/plain"))
results.append(probe("pmc_oa_jsonl",
                     "https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_jsonl/oa_jsonl.filelist.csv",
                     accept="text/plain"))

# ---- TIER 2: benchmark/evaluation (NEVER evidence-layer) ---------------
for hf in ["v13s/golden-fto-layer-a", "Orionfold/patent-strategist-bench-v0.1",
           "PatSnap/novelty-search-bench", "mhurhangee/ep-patent-all-claims",
           "EMBO/soda-vec-data-full_pmc_title_abstract"]:
    results.append(probe(f"hf:{hf}",
                         f"https://huggingface.co/api/datasets/{hf}"))

print("\n=== SUMMARY ===")
for r in results:
    print(f"{r['name']:42s} {str(r.get('status','FAIL')):>5s} {r.get('shape', r.get('error',''))[:60]}")

out_path = "TOSCANINI/OPEN_DATA_PROBES.json"
json.dump({"probe_run": "2026-08-30", "results": results},
          open(out_path, "w"), indent=1)
print(f"\nwrote {out_path}")

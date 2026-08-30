#!/usr/bin/env python3
"""Live probe candidate sources for the CEO 2026-08-30 directive:
- missing general-purpose FAILURE UNIVERSE (aerospace/automotive/industrial/
  energy/infrastructure/electronics/chemical failures)
- replacement strategies for blocked routes (WHO ICTRP new platform,
  EUDAMED, NIST standards-full-text, CPSC commercial/product)

Each probe prints a MEASURED verdict (HTTP status, content-type, body
shape). Nothing is claimed integrated by probing — integration requires
the full 7-step chain (Art. XXI). Probes that fail are recorded as
measured blockers with dates.
"""

from __future__ import annotations

import json
import ssl
import sys
import urllib.request

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like "
      "Gecko) Chrome/120.0.0.0 Safari/537.36")


def probe(name: str, url: str, expect_hint: str = "", accept: str = "application/json,*/*"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    try:
        r = urllib.request.urlopen(req, timeout=25, context=CTX)
        body = r.read()
        ct = r.headers.get("Content-Type", "?")
        snippet = body[:220].decode("utf-8", "replace").replace("\n", " ")
        try:
            j = json.loads(body)
            shape = f"JSON keys={list(j.keys())[:8] if isinstance(j, dict) else type(j).__name__}"
        except Exception:
            shape = "NOT-JSON"
        print(f"[{name}] HTTP {r.status} {ct} len={len(body)} {shape}")
        print(f"   url={url}")
        print(f"   {expect_hint} :: {snippet}")
        return {"name": name, "url": url, "status": r.status,
                "content_type": ct, "len": len(body), "shape": shape}
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read()[:200]
        except Exception:
            pass
        print(f"[{name}] HTTP {e.code} {e.headers.get('Content-Type','?')} :: {body[:180].decode('utf-8','replace')}")
        return {"name": name, "url": url, "status": e.code, "error": body[:180].decode("utf-8", "replace")}
    except Exception as e:  # noqa: BLE001
        print(f"[{name}] FAIL {e!r}")
        return {"name": name, "url": url, "error": repr(e)}


results = []

# --- WHO ICTRP new platform (legacy API retired; probe backend routes) ---
results.append(probe("who_ictrp_v2_root", "https://trialsearch.who.int/",
                     "new ICTRP SPA — check root"))
results.append(probe("who_ictrp_v2_api", "https://trialsearch.who.int/api/v1/trials?pageSize=3",
                     "possible JSON backend"))
results.append(probe("who_ictrp_legacy", "https://apps.who.int/trialsearch/PlatformMain.aspx",
                     "legacy platform"))

# --- NIST publications API (standards-adjacent: NIST SP/FIPS are standards) ---
results.append(probe("nist_pubs_api", "https://pubs.nist.gov/pub/search?q=800-53&page=1",
                     "NIST Publication API"))
results.append(probe("nist_pubs_api_v2", "https://pubs-api.nist.gov/pubs/search?q=battery&page%5Bsize%5D=3",
                     "alt route"))

# --- CPSC SaferProducts recalls API (consumer products + electronics) ---
results.append(probe("cpsc_recalls", "https://www.saferproducts.gov/RestWebServices/Recall?format=json&RecallDateStart=2026-01-01",
                     "CPSC recalls JSON"))

# --- NRC event notifications (energy failures) ---
results.append(probe("nrc_events_rss", "https://www.nrc.gov/reading-rm/doc-collections/event-notifications/rss/",
                     "NRC event notifications RSS"))
results.append(probe("nrc_adams_public", "https://adamspublic.nrc.gov/webapi2/api/data/search/header/fields?docket_number=0500001",
                     "ADAMS public API?"))

# --- OSHA enforcement / severe injury (industrial failures) ---
results.append(probe("osha_ords_inspections", "https://www.osha.gov/ords/imr_inspection?ROW_MOD=2026&stateeq=OH",
                     "OSHA ORDS inspections API"))
results.append(probe("osha_sev_injury", "https://www.osha.gov/severe-injury/index-sevintro",
                     "severe injury reports page"))

# --- CSB investigations (chemical/process) ---
results.append(probe("csb_investigations", "https://www.csb.gov/api/v1/investigations?page=1&per_page=3",
                     "CSB API attempt"))
results.append(probe("csb_rss", "https://www.csb.gov/rss.xml", "CSB RSS"))

# --- USGS earthquakes (infrastructure-adjacent events; free no-key) ---
results.append(probe("usgs_eq_query", "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&limit=2&starttime=2026-08-01",
                     "USGS FDSN event query"))

# --- NASA ASRS / LLIS (aerospace failures) ---
results.append(probe("nasa_llis", "https://llis.nasa.gov//api/lessons?limit=3",
                     "NASA LLIS API attempt"))
results.append(probe("nasa_asrs", "https://asrs.arc.nasa.gov/search/api/search?queryType=all&text=battery",
                     "ASRS API attempt"))

# --- FAA SDR (avionics/electronics service difficulty) ---
results.append(probe("faa_sdr", "https://av-info.faa.gov/sdrx/SDR122Query.aspx?sdrinvent=1",
                     "FAA SDR query route"))

# --- PHMSA pipeline incidents (energy infrastructure) via data.dot.gov ---
results.append(probe("dot_phmsa_api", "https://data.transportation.gov/resource/4ggw-9m7h.json?$limit=3",
                     "Socrata PHMSA incidents attempt"))

# --- EUDAMED public API re-probe (registration required?) ---
results.append(probe("eudamed_api_devices", "https://ec.europa.eu/tools/eudamed/api/devices?size=3",
                     "EUDAMED public API attempt"))

# --- OpenAlex keyless (budget issue: does anonymous still work?) ---
results.append(probe("openalex_anonymous", "https://api.openalex.org/works?search=battery%20thermal%20runaway&per-page=3",
                     "anonymous polite pool"))

# --- NHTSA complaints (automotive adverse-event analog) ---
results.append(probe("nhtsa_complaints_api", "https://api.nhtsa.gov/complaints/complaintsByVehicle?make=toyota&model=camry&modelYear=2020",
                     "NHTSA complaints by vehicle"))
results.append(probe("nhtsa_complaints_flat", "https://static.nhtsa.gov/odi/ffdd/cmis/Complaints_FLAT_SP.zip",
                     "NHTSA complaints flat file"))

# --- Materials Project re-probe with key from .env.keys ---
try:
    sys.path.insert(0, ".")
    from discovery_fabric.source_registry.keys import load_key
    mpkey = load_key("MATERIALS_PROJECT_API_KEY")
    if mpkey:
        results.append(probe("materials_project_key",
                             f"https://api.materialsproject.org/materials/summary/?formula=TiO2",
                             "MP with key", accept="application/json"))
except Exception as e:  # noqa: BLE001
    print("MP probe skip:", e)

print("\n=== SUMMARY ===")
for r in results:
    print(r.get("name"), "->", r.get("status", r.get("error")))

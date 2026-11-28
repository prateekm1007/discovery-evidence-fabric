#!/usr/bin/env python3
"""r11_novelty_live.py — LIVE prior-art packet resolution for the
novelty search (R11 Q7, 2026-11-14).

The frozen run-tree envelopes (eval/runs/<commit>/<run_id>/<pid>/
pipeline/envelope_FREEZE.json) live in the GITIGNORED ENGINE_RUNS
scratch and were recycled between sessions — the committed novelty
artifact (3ad63e8c8) resolved them in the session where they existed;
today search_one types every problem NOT_MEASURED
('the frozen evidence packet is unresolvable').

This repair keeps the packet HONEST without fabricating anything: the
pair records carry evidence_ids (DOIs) — the packet records are
re-fetched LIVE from Crossref (title + abstract per DOI), cached under
ENGINE_RUNS/novelty_live_cache/ (scratch, gitignored), and the novelty
search runs on the re-resolved packets. The cached JSON carries the
fetch timestamp and the exact DOI — provenance is never manufactured
(Art. VI); a DOI that no longer resolves is typed
UNRESOLVED_DOI and excluded from the pool (never silently replaced).
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / "ENGINE_RUNS" / "novelty_live_cache"
UA = {"User-Agent": "discovery-evidence-fabric/1.0 (mailto:audit@local)"}


def fetch_doi(doi: str) -> dict:
    """Live metadata for one evidence id. Crossref for doi:10.* (title +
    abstract); the arXiv API for doi:10.48550/arxiv.* (Crossref does not
    serve arXiv DOIs — measured 2026-11-14: every 10.48550 id returned
    UNRESOLVED on Crossref while the arXiv API serves them); zenodo and
    anything else unresolved stays typed UNRESOLVED (never silently
    replaced). Cached under ENGINE_RUNS/novelty_live_cache/."""
    key = doi.replace("/", "_").replace(":", "-")
    cf = CACHE / f"{key}.json"
    if cf.exists():
        try:
            return json.loads(cf.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — corrupt cache refetches
            pass
    rec = None
    if doi.startswith("10.48550/arxiv."):
        ax = doi.split("arxiv.", 1)[1]
        rec = _fetch_arxiv(ax, doi)
    if rec is None:
        rec = _fetch_crossref(doi)
    CACHE.mkdir(parents=True, exist_ok=True)
    cf.write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    return rec


def _fetch_crossref(doi: str) -> dict:
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=20) as r:
            m = (json.loads(r.read().decode("utf-8", "replace"))
                 .get("message") or {})
        return {
            "id": f"doi:{m.get('DOI', doi)}",
            "title": (m.get("title") or [""])[0],
            "abstract": m.get("abstract") or "",
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
            "resolved": True, "source": "crossref",
        }
    except Exception as e:  # noqa: BLE001 — typed unresolved, never silent
        return {"id": f"doi:{doi}", "title": "", "abstract": "",
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                            time.gmtime()),
                "resolved": False, "source": "crossref",
                "error": str(e)[:120]}


def _fetch_arxiv(ax_id: str, doi: str) -> dict:
    import re
    url = ("http://export.arxiv.org/api/query?id_list="
           + urllib.parse.quote(ax_id) + "&max_results=1")
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=20) as r:
            xml = r.read().decode("utf-8", "replace")
        titles = re.findall(r"<title>(.*?)</title>", xml, re.S)
        summaries = re.findall(r"<summary>(.*?)</summary>", xml, re.S)
        # entry 0 is the query echo; entry 1 is the paper
        title = (titles[1].strip() if len(titles) > 1 else "")
        abstract = (summaries[0].strip() if summaries else "")
        if not title:
            return {"id": f"doi:{doi}", "title": "", "abstract": "",
                    "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                time.gmtime()),
                    "resolved": False, "source": "arxiv",
                    "error": "no entry in arxiv api response"}
        return {"id": f"doi:{doi}", "title": title,
                "abstract": abstract,
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                            time.gmtime()),
                "resolved": True, "source": "arxiv"}
    except Exception as e:  # noqa: BLE001
        return {"id": f"doi:{doi}", "title": "", "abstract": "",
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                            time.gmtime()),
                "resolved": False, "source": "arxiv",
                "error": str(e)[:120]}


def main() -> int:
    pair_dir = sys.argv[1] if len(sys.argv) > 1 else "eval/pairs/dev12_r7"
    out = {}
    n_ok = n_bad = 0
    for f in sorted(Path(pair_dir).glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        pid = d.get("problem_id") or f.stem
        recs = []
        for ev in d.get("evidence_ids") or []:
            if str(ev).startswith("doi:"):
                r = fetch_doi(str(ev)[4:])
                recs.append(r)
                if r["resolved"]:
                    n_ok += 1
                else:
                    n_bad += 1
            elif str(ev).startswith("title:"):
                recs.append({"id": ev, "title": ev, "abstract": "",
                             "resolved": False,
                             "typed": "TITLE_ONLY_ID_NO_FETCH"})
            time.sleep(0.4)  # polite Crossref pacing
        out[pid] = recs
        print(f"[novelty-live] {pid[:40]:<42} {len(recs)} ids "
              f"({sum(1 for r in recs if r.get('resolved'))} resolved)")
    (CACHE / "packets_by_pid.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[novelty-live] done: {n_ok} resolved / {n_bad} unresolved "
          f"-> {CACHE/'packets_by_pid.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""r412_v3_benchmark_corpus.py — directive item 7: the frozen
retrieval benchmark built from REAL records containing known
quantitative evidence.

CONSTRUCTION DISCIPLINE (Art. VIII — certification must attack
itself; the corpus is authored BEFORE the benchmark evaluator runs
and its labels are NOT derived from the FEAL instrument):

  Stage 1 (acquire, this script --acquire):
    NEUTRAL ground-truth acquisition — direct connector calls
    (europepmc / arxiv / core), query form "{capability} experimental
    comparison" — deliberately DISTINCT from every lane form:
      Lane A: "{rung} performance trend improvement measured benchmark"
      Lane B: "{rung} {measurement-terms} measured improvement"
      Lane C: "{frontier-domain} {bridge} measured performance ..."
    Candidate selection by a SIMPLE independent scan (digit + unit
    regex) — not FEAL.
  Stage 2 (label, human-in-loop):
    the coder READS each dumped record and authors the labels
    (numeric_bearing, measurement_bearing, baseline_terms, year,
    source_identity, domain) — labels authored by READING, never by
    running FEAL; authorship independence DISCLOSED on the frozen
    corpus (AI_REVIEW per Art. LXVII).
  Stage 3 (freeze, this script --freeze):
    labels validated to cover every candidate; corpus frozen with
    sha256; negative cases (scan false-positives labeled false on
    reading) are RETAINED as adversarial recall controls.

The benchmark evaluator (a separate script) runs ONLY after the
corpus is frozen and the lane pools are committed; it computes
deterministic recall/diversity/recovery metrics over the persisted
lane pool bytes. No LLM participates anywhere in this benchmark.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.r412.frontier_evidence import (  # noqa: E402
    extract_year,
)

STAGING = REPO / "R412" / "GRADIENT_V3" / \
    "RETRIEVAL_BENCHMARK" / "corpus_staging.json"
LABELS = REPO / "R412" / "GRADIENT_V3" / "RETRIEVAL_BENCHMARK" / \
    "corpus_labels.json"
FROZEN = REPO / "R412" / "GRADIENT_V3" / "RETRIEVAL_BENCHMARK" / \
    "RETRIEVAL_BENCHMARK_CORPUS.json"

#: the benchmark's capability areas — a bounded, mixed sample of the
#: 13 sealed rungs (6 allocation-relevant + 2 non-allocation), chosen
#: for domain spread (power electronics, wind, chemical process,
#: batteries, thermal, machining, carbon capture, semiconductor fab)
BENCHMARK_AREAS = [
    "device switching energy",
    "active alignment actuation control bandwidth",
    "control oriented dynamic modeling",
    "differential measurement instrumentation",
    "turbulent regime porous insert tradeoff",
    "material-property-consistent effectiveness prediction",
    "amine substitution novelty margin",
    "primary evidence quantified prediction",
]

#: NEUTRAL query form (distinct from all three lanes)
NEUTRAL_SUFFIX = "experimental comparison"

#: simple independent candidate scan (NOT the FEAL extractor):
#: a digit followed within 3 chars by a unit-ish token
_SIMPLE_SCAN = re.compile(
    r"\d+(?:\.\d+)?\s?(?:%|Hz|kHz|MHz|GHz|W|kW|mW|MW|V|mV|kV|A|mA|"
    r"J|mJ|kJ|Wh|kWh|Pa|kPa|MPa|GPa|bar|K|ms|s|min|h|kg|g|mg|mm|cm|"
    r"um|nm|m|km|N|dB|rpm|fold|x\b)", re.I)


def _connector(sid: str):
    from discovery_fabric.retrieval_fabric.adapters import \
        _connector_for
    return _connector_for(sid)


def acquire() -> int:
    """Stage 1: neutral acquisition + simple-scan candidate dump."""
    out: List[Dict[str, Any]] = []
    for area in BENCHMARK_AREAS:
        q = f"{area} {NEUTRAL_SUFFIX}"
        got: List[Dict[str, Any]] = []
        for sid in ("europepmc", "arxiv", "core"):
            conn = _connector(sid)
            if conn is None:
                continue
            try:
                try:
                    r = conn.search(q, retrieval_role="DISCOVERY")
                except TypeError:
                    r = conn.search(q)
            except Exception as e:  # recorded, never silent
                print(f"  [{sid}] EXC {str(e)[:60]}")
                continue
            if r.status not in ("OK",):
                print(f"  [{sid}] {r.status}")
                continue
            for rec in (r.records or [])[:6]:
                n = rec.normalized or {}
                title = str(n.get("title") or rec.title or "")
                abstract = str(n.get("abstract") or
                               n.get("snippet") or "")[:900]
                rid = str(rec.record_id or n.get("record_id") or "")
                doi = n.get("doi")
                year = extract_year(
                    n.get("publication_year"), n.get("year"),
                    n.get("issued_year"), n.get("publication_date"),
                    n.get("published"), n.get("firstPublicationDate"))
                text = f"{title} {abstract}"
                got.append({
                    "area": area,
                    "source": sid,
                    "record_id": rid,
                    "doi": (str(doi).lower() if doi else None),
                    "title": title[:220],
                    "abstract": abstract,
                    "year": year,
                    "scan_numeric": bool(_SIMPLE_SCAN.search(text)),
                    "raw_payload_sha256": rec.raw_payload_sha256,
                })
            time.sleep(1.5)
        # candidate preference: scan-positive first (then a few
        # scan-negative as adversarial controls), capped per area
        pos = [g for g in got if g["scan_numeric"]]
        neg = [g for g in got if not g["scan_numeric"]]
        chosen = pos[:6] + neg[:2]
        # dedup within area by doi/title
        seen = set()
        for g in chosen:
            key = g["doi"] or g["title"][:80].lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(g)
        print(f"{area}: {len(got)} retrieved, "
              f"{len(pos)} scan-positive, {len(chosen)} staged")
    STAGING.parent.mkdir(parents=True, exist_ok=True)
    STAGING.write_text(json.dumps({
        "staging_note": "neutral acquisition; labels authored next "
                        "by READING (Art. VIII); not yet frozen",
        "acquired_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime()),
        "candidates": out,
    }, indent=1) + "\n")
    print(f"\nstaged {len(out)} candidates -> {STAGING}")
    print("NEXT: author labels by reading the dump "
          "(scripts prints --read), then --freeze")
    return 0


def read_dump() -> int:
    """Print the staged candidates compactly for label authoring."""
    d = json.loads(STAGING.read_text())
    for i, g in enumerate(d["candidates"]):
        print(f"--- [{i}] {g['area']} | {g['source']} | "
              f"scan={g['scan_numeric']} | year={g['year']} | "
              f"doi={g['doi']}")
        print(f"    T: {g['title']}")
        a = g["abstract"].replace("\n", " ")
        print(f"    A: {a[:420]}")
    return 0


def freeze() -> int:
    """Stage 3: validate labels cover every candidate; freeze."""
    staging = json.loads(STAGING.read_text())
    labels_doc = json.loads(LABELS.read_text())
    labels = labels_doc.get("labels") or labels_doc
    by_key = {}
    for i, g in enumerate(staging["candidates"]):
        key = g["doi"] or g["title"][:80].lower()
        by_key[str(i)] = (key, g)
    missing = []
    records = []
    for i, (key, g) in by_key.items():
        lab = labels.get(str(i))
        if lab is None:
            missing.append(i)
            continue
        for req in ("relevant", "numeric_bearing",
                    "measurement_bearing", "baseline_terms",
                    "year", "domain"):
            if req not in lab:
                missing.append(f"{i}:{req}")
        records.append({
            "benchmark_id": f"BENCH-{int(i):03d}",
            "area": g["area"],
            "source": g["source"],
            "record_id": g["record_id"],
            "doi": g["doi"],
            "title": g["title"],
            "abstract": g["abstract"],
            "scan_numeric": g["scan_numeric"],
            "raw_payload_sha256": g["raw_payload_sha256"],
            "labels": {
                "relevant": bool(lab["relevant"]),
                "numeric_bearing": bool(lab["numeric_bearing"]),
                "measurement_bearing":
                    bool(lab["measurement_bearing"]),
                "baseline_terms": list(lab["baseline_terms"]),
                "year": lab["year"],
                "source_identity": g["source"],
                "domain": str(lab["domain"]),
                "label_authorship":
                    "AUTHORED_BY_CODER_BY_READING (pre-freeze; labels "
                    "never derived from the FEAL instrument; the "
                    "simple scan is selection only, a disclosed "
                    "imperfection)",
            },
        })
    if missing:
        print("REFUSED: missing labels:", missing[:20])
        return 1
    n_num = sum(1 for r in records
                if r["labels"]["numeric_bearing"])
    n_meas = sum(1 for r in records
                 if r["labels"]["measurement_bearing"])
    n_neg = sum(1 for r in records
                if r["scan_numeric"] and
                not r["labels"]["numeric_bearing"])
    n_rel = sum(1 for r in records if r["labels"]["relevant"])
    n_rel_num = sum(1 for r in records if r["labels"]["relevant"]
                    and r["labels"]["numeric_bearing"])
    n_rel_meas = sum(1 for r in records
                     if r["labels"]["relevant"]
                     and r["labels"]["measurement_bearing"])
    corpus = {
        "artifact_type": "R412_GRADIENT_V3_RETRIEVAL_BENCHMARK_CORPUS",
        "directive_item": 7,
        "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                   time.gmtime()),
        "n_records": len(records),
        "n_numeric_bearing": n_num,
        "n_measurement_bearing": n_meas,
        "n_scan_positive_labeled_negative (adversarial)": n_neg,
        "n_relevant": n_rel,
        "n_relevant_and_numeric (recall_numeric denominator)":
            n_rel_num,
        "n_relevant_and_measurement "
        "(recall_measurement denominator)": n_rel_meas,
        "acquisition_neutrality": (
            "direct connector calls, query form "
            f'\"{{capability}} {NEUTRAL_SUFFIX}\" — distinct from '
            "every lane form (A/B/C); candidate selection by a "
            "simple digit+unit scan, NOT the FEAL extractor"),
        "label_independence": (
            "labels authored by reading each record before the "
            "benchmark evaluator existed; FEAL was not run on these "
            "records during labeling (Art. VIII)"),
        "benchmark_metrics_contract": [
            "recall_numeric_bearing (reference-set recall, DOI/"
            "title identity match into the lane union pool)",
            "recall_measurement_bearing",
            "numeric_bearing_rate (pool property)",
            "measurement_bearing_rate (pool property)",
            "abstract_bearing_rate (pool property)",
            "year_recovery_rate (pool property)",
            "source_identity_recovery_rate (pool property)",
            "baseline_recovery_rate (pool property)",
            "domain_diversity (pool property)",
        ],
        "records": records,
        "reviewer_provenance": "AI_REVIEW",
    }
    payload = json.dumps(corpus, indent=1, sort_keys=True)
    FROZEN.write_text(payload + "\n")
    sha = hashlib.sha256(payload.encode()).hexdigest()
    print(f"frozen: {FROZEN}")
    print(f"  records={len(records)} numeric={n_num} "
          f"measurement={n_meas} adversarial-neg={n_neg}")
    print(f"  sha256={sha}")
    return 0


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "--acquire":
        raise SystemExit(acquire())
    if mode == "--read":
        raise SystemExit(read_dump())
    if mode == "--freeze":
        raise SystemExit(freeze())
    print("usage: --acquire | --read | --freeze")
    raise SystemExit(2)

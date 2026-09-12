#!/usr/bin/env python3
"""R447 Evidence-Fabric reconnaissance (scoping-only; NO ingestion).

Operator analysis (this round's message): Hugging Face Pro provides hub
infrastructure (private datasets, Dataset Viewer, storage, compute, APIs)
plus access to the public/gated dataset ecosystem — NOT a proprietary
patent-database subscription. The recommended next high-information move
is a reconnaissance: inventory the highest-value patent/scientific/
engineering/materials/chemistry datasets, inspect schema/license/
provenance, select the first ~10 sources, then (future round) prove one
complete retrieval -> normalization -> provenance -> mechanism-evidence
flow on a fresh problem.

This script does the VERIFIABLE part now: for each operator-named
dataset, probe the live HF API and record existence, license, size,
gated status, downloads, and last modification — the machine-checkable
foundation of the inventory. NOTHING is downloaded; no evidence enters
any pipeline; per the operator's own epistemic rule, 'available' is
never 'correct' (schema validation and cross-source corroboration are
FUTURE steps, recorded as such).

Output: R447/EVIDENCE_FABRIC_RECONNAISSANCE.json
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

HF_TOKEN = os.environ.get("HF_TOKEN", "")
AUTH = {"Authorization": f"Bearer {HF_TOKEN}"}

# the operator's table, as named in the analysis (family -> dataset ids)
INVENTORY = [
    ("E1_patent_intelligence", "common-pile/uspto",
     "USPTO patent text corpus (patent sections preserved, equations as "
     "LaTeX); use as historical technological knowledge + prior-art "
     "discovery + mechanism neighborhoods, NEVER as a patentability "
     "authority"),
    ("E1_patent_intelligence", "baber/WOPTO",
     "worldwide patent applications outside the US (bibliographic + "
     "titles/abstracts, many languages) — the global landscape "
     "complement"),
    ("E1_patent_intelligence", "istat-ai/ai-patents",
     "AI-focused patent corpus (~105k US/EU) — specialized index, not a "
     "replacement for the giant corpora"),
    ("E2_scientific_intelligence", "Mearman/OpenAlex",
     "OpenAlex snapshot mirror (works/authors/institutions/citations/"
     "concepts) — research-frontier discovery"),
    ("E2_scientific_intelligence", "sentence-transformers/s2orc",
     "S2ORC embedding-oriented release (titles/abstracts/citations)"),
    ("E2_scientific_intelligence", "scientifi-papers/scientific-papers",
     "large multi-corpus scientific collection (S2ORC + PeS2o + CORE "
     "full-text)"),
    ("E3_engineering_intelligence", "HuggingAI4Engineering/cadgenbench-data",
     "CADGenBench — 81 mechanical-part fixtures (drawings, 3D parts, "
     "STEP generation/editing, mating interfaces); ground truth kept "
     "private by design (cannot be gamed) — external engineering-geometry "
     "benchmark"),
    ("E3_engineering_intelligence", "arungovindneelan/openfoam-Agent-Dataset",
     "validated OpenFOAM cases paired with natural-language prompts — "
     "fluid-mechanism falsification-experiment analogues"),
    ("E4_materials_intelligence", "materials-toolkits/materials-project",
     "Materials Project structures + formation energies"),
    ("E4_materials_intelligence", "CrystalReasoner/CrystalReasoner-MP",
     "~200k structures with formation energy, stability, band gap, "
     "moduli, thermal expansion"),
    ("E4_materials_intelligence", "colabfit/Materials_Project",
     "ColabFit MP — 6.34M rows of energies/forces/stresses/structures"),
    ("E4_materials_intelligence", "LeMaterial/LeMat-Rho",
     "~69k inorganic crystals from AFLOW/OQMD/MP with charge densities, "
     "Bader charges, forces, stresses"),
    ("E4_materials_intelligence", "foundry-ml/dataset_debyet_aflow",
     "AFLOW-derived Debye-temperature property dataset"),
    ("E5_chemical_intelligence", "liuganghuggingface/QM9",
     "QM9 molecular structures + computed properties (HOMO/LUMO/gap/"
     "dipole/polarizability/energies)"),
    ("E5_chemical_intelligence", "ChemRAG/uspto",
     "USPTO-derived reaction datasets (reactants/reagents/products/"
     "yield)"),
]

SEARCHES = [
    ("E5_chemical_intelligence", "pubchem", "PubChem-derived molecular "
     "collections (multiple mirrors exist; a specific mirror gets "
     "selected in the selection round)"),
    ("E6_domain_intelligence", "nasa", "NASA-tagged datasets "
     "(publications, Earth observation, space weather, engineering "
     "benchmarks)"),
]


def api(path, timeout=45):
    req = urllib.request.Request(
        f"https://huggingface.co/api/{path}", headers=AUTH)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def probe_dataset(ds_id):
    """Live metadata probe: existence, license, gating, size, activity."""
    try:
        d = api(f"datasets/{ds_id}")
        card = d.get("cardData") or {}
        return {
            "exists": True,
            "id": d.get("id"),
            "private": d.get("private"),
            "gated": d.get("gated"),
            "downloads": d.get("downloads"),
            "likes": d.get("likes"),
            "last_modified": d.get("lastModified"),
            "created_at": d.get("createdAt"),
            "license": (card.get("license") if isinstance(
                card.get("license"), str)
                else (card.get("license") or {}).get("name")
                if isinstance(card.get("license"), dict) else None),
            "tags_sample": [t for t in (d.get("tags") or [])
                            if t.startswith(("task_categories", "size_",
                                             "language", "modality",
                                             "format", "benchmark"))][:8],
            "provenance_note": "card metadata as served by the HF API at "
                               "probe time — availability is not "
                               "correctness (the operator's epistemic "
                               "rule); schema + license text + "
                               "cross-source corroboration are future "
                               "selection-round steps",
        }
    except urllib.error.HTTPError as e:
        return {"exists": False, "probe": f"HTTP {e.code}"}
    except Exception as e:  # noqa: BLE001
        return {"exists": False, "probe": f"{type(e).__name__}: {e}"}


def search_datasets(query, limit=8):
    try:
        res = api(f"datasets?search={query}&limit={limit}&sort=downloads")
        return [{"id": s.get("id"), "downloads": s.get("downloads"),
                 "last_modified": s.get("lastModified")}
                for s in res[:limit]]
    except Exception as e:  # noqa: BLE001
        return [{"_error": f"{type(e).__name__}: {e}"}]


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    families = {}
    entries = []
    for family, ds_id, note in INVENTORY:
        probe = probe_dataset(ds_id)
        entries.append({"family": family, "dataset_id": ds_id,
                        "operator_note": note, "live_probe": probe})
        families.setdefault(family, []).append(
            (ds_id, probe.get("exists")))
        print(f"{'OK ' if probe.get('exists') else 'MISS'} {ds_id}")
        time.sleep(0.4)

    search_entries = []
    for family, query, note in SEARCHES:
        hits = search_datasets(query)
        search_entries.append({"family": family, "query": query,
                               "operator_note": note,
                               "top_hits_by_downloads": hits})
        print(f"SRCH {query}: {len(hits)} hits")

    exist_count = sum(1 for e in entries if e["live_probe"].get("exists"))

    record = {
        "artifact_type": "R447 Evidence-Fabric reconnaissance "
                         "(scoping inventory — NO ingestion)",
        "created_at_utc": now,
        "reviewer_provenance": "AI_REVIEW",
        "operator_analysis_source": "the R447 operator message (the "
                                    "six-family Toscanini Evidence Fabric "
                                    "recommendation: E1 patents, E2 "
                                    "papers, E3 engineering, E4 materials, "
                                    "E5 chemistry, E6 domain)",
        "scope_rule": "reconnaissance only: existence/license/gating/"
                      "activity verified LIVE via the HF API; nothing "
                      "downloaded, nothing ingested, no evidence enters "
                      "any pipeline, no retrieval->normalization flow "
                      "claimed — that flow is the operator's stated "
                      "NEXT high-information move, to be proven on a "
                      "fresh problem in a future round",
        "epistemic_rule": "a dataset hosted on HF is AVAILABLE, never "
                          "automatically CORRECT: provenance, license "
                          "text, schema validation, quality assessment, "
                          "and cross-source corroboration are explicit "
                          "future steps per record (the operator's rule; "
                          "Art. XXI/XXV apply at ingestion time)",
        "inventory": entries,
        "searches": search_entries,
        "summary": {
            "operator_named_datasets": len(entries),
            "verified_existing": exist_count,
            "verified_missing": len(entries) - exist_count,
            "families": {f: {"probed": len(v),
                             "existing": sum(1 for _, ok in v if ok)}
                         for f, v in families.items()},
        },
        "next_decisive_test": [
            "selection round: pick the first ~10 sources by the "
            "operator's priority table (USPTO/WOPTO/OpenAlex/S2ORC/"
            "CADGenBench/OpenFOAM/Materials Project first), reading each "
            "license TEXT and schema in full",
            "one complete flow on a fresh Toscanini problem: retrieval "
            "-> EvidenceRecord normalization (source/source_type/source_id/"
            "domain/technical_entities/mechanisms/claims/measurements/"
            "license/provenance/retrieval_timestamp/content_hash/"
            "confidence) -> provenance custody -> mechanism-evidence "
            "binding, with relevance adjudicated per record (Art. XXI.4) "
            "and provider failures distinct from absence (Art. XXI.3)",
            "federated retrieval layer first (retrieve only what the "
            "problem needs); NO bulk warehouse (the operator's explicit "
            "constraint); HF Buckets for large indexes, private HF "
            "datasets for Toscanini-proprietary evidence caches",
        ],
    }

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "R447", "EVIDENCE_FABRIC_RECONNAISSANCE.json")
    with open(out, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    print(f"\nWROTE {os.path.abspath(out)}")
    print(f"existing {exist_count}/{len(entries)} operator-named datasets "
          f"(live-verified)")


if __name__ == "__main__":
    main()

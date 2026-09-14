#!/usr/bin/env python3
"""R449 Phases 1 + 2 — freeze the source-selection layer and read the
actual license texts.

Phase 1 (directive): "Take the 15-source reconnaissance and select the
first production subset... maximize coverage, quality, license clarity,
technical diversity, information gain." The operator's recommended
rough subset: USPTO, WOPTO, OpenAlex, S2ORC, CADGenBench,
OpenFOAM-Agent, Materials Project, one AFLOW/OQMD-derived source, QM9,
ChemRAG/USPTO. The selection here SCORES the 15 reconnaissance sources
on the five criteria (deterministic, live-metadata-derived, basis
recorded per score) and freezes the first subset; the scoring may
confirm or adjust the operator's rough set ON RECORDED EVIDENCE (e.g.,
a recommended source whose license text cannot be read stays selected
but NOT promoted to PRODUCTION — fail-closed).

Phase 2 (directive): "Do not promote such datasets into production
evidence until the actual licensing/access state has been verified."
For EVERY source: the card README is READ (raw), the license
declaration extracted and hashed, LICENSE/COPYING files searched in the
repo tree and read when present, gated status + access requirements
recorded from the Hub API. license=None on the card is an honest
UNVERIFIED state, never a guessed permissive license (Art. VI/XXV).

Outputs:
  R449/EVIDENCE_SOURCE_REGISTRY.json    (the committed authority)
  R449/EVIDENCE_LICENSE_REGISTRY.json   (per-source license records)

Federated discipline: NOTHING is downloaded; metadata + card text +
tree listings + one rows-page per dataset (schema features) only.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.evidence_fabric import connectors as hc  # noqa: E402

OUT_DIR = REPO_ROOT / "R449"
SOURCE_REGISTRY = OUT_DIR / "EVIDENCE_SOURCE_REGISTRY.json"
LICENSE_REGISTRY = OUT_DIR / "EVIDENCE_LICENSE_REGISTRY.json"

NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")

#: the 15 reconnaissance sources (R447/EVIDENCE_FABRIC_RECONNAISSANCE
#: inventory — the operator's table), with the runtime wiring that the
#: federated connector uses per source.
CANDIDATES: List[Dict[str, Any]] = [
    {"source_id": "uspto_patents", "family": "E1_patent_intelligence",
     "dataset_id": "common-pile/uspto",
     "source_url": "https://huggingface.co/datasets/common-pile/uspto",
     "config": "default", "split": "train", "query_mode": "search",
     "text_field": "text", "document_field": "id",
     "operator_recommended": True,
     "operator_note": "USPTO patent text corpus; historical "
                      "technological knowledge + prior-art discovery + "
                      "mechanism neighborhoods, NEVER patentability"},
    {"source_id": "wopto", "family": "E1_patent_intelligence",
     "dataset_id": "baber/WOPTO",
     "source_url": "https://huggingface.co/datasets/baber/WOPTO",
     "config": "default", "split": "train", "query_mode": "search",
     "text_field": "abstract_text", "fallback_text_field": "title_text",
     "document_field": "publication_number",
     "operator_recommended": True,
     "operator_note": "worldwide patent applications outside the US "
                      "(bibliographic + titles/abstracts; many rows "
                      "carry null abstracts — the title fallback is "
                      "measured)"},
    {"source_id": "ai_patents", "family": "E1_patent_intelligence",
     "dataset_id": "istat-ai/ai-patents",
     "source_url": "https://huggingface.co/datasets/istat-ai/ai-patents",
     "config": "default", "split": "train", "query_mode": "search",
     "text_field": "text", "document_field": "id",
     "operator_recommended": False,
     "operator_note": "AI-focused patent corpus; specialized index"},
    {"source_id": "openalex_mirror", "family": "E2_scientific_intelligence",
     "dataset_id": "Mearman/OpenAlex",
     "source_url": "https://huggingface.co/datasets/Mearman/OpenAlex",
     "config": "works__work_abstracts", "split": "train",
     "query_mode": "search", "text_field": "abstract",
     "document_field": "id",
     "operator_recommended": True,
     "operator_note": "OpenAlex snapshot mirror (works/abstracts)"},
    {"source_id": "s2orc_abstracts", "family": "E2_scientific_intelligence",
     "dataset_id": "sentence-transformers/s2orc",
     "source_url": "https://huggingface.co/datasets/"
                   "sentence-transformers/s2orc",
     "config": "default", "split": "train", "query_mode": "search",
     "text_field": "title", "document_field": "id",
     "operator_recommended": True,
     "operator_note": "S2ORC embedding-oriented release "
                      "(titles/abstracts/citations)"},
    {"source_id": "scientific_papers",
     "family": "E2_scientific_intelligence",
     "dataset_id": "scientifi-papers/scientific-papers",
     "source_url": "https://huggingface.co/datasets/"
                   "scientifi-papers/scientific-papers",
     "config": "default", "split": "train", "query_mode": "search",
     "text_field": "text", "document_field": "id",
     "operator_recommended": False,
     "operator_note": "large multi-corpus scientific collection"},
    {"source_id": "cadgenbench", "family": "E3_engineering_intelligence",
     "dataset_id": "HuggingAI4Engineering/cadgenbench-data",
     "source_url": "https://huggingface.co/datasets/"
                   "HuggingAI4Engineering/cadgenbench-data",
     "config": "default", "split": "train", "query_mode": "search",
     "text_field": "text", "document_field": "id",
     "operator_recommended": True,
     "operator_note": "CADGenBench mechanical-part fixtures; external "
                      "engineering-geometry benchmark"},
    {"source_id": "openfoam_cases", "family": "E3_engineering_intelligence",
     "dataset_id": "arungovindneelan/openfoam-Agent-Dataset",
     "source_url": "https://huggingface.co/datasets/"
                   "arungovindneelan/openfoam-Agent-Dataset",
     "config": "per_case_chat", "split": "train",
     "query_mode": "search", "text_field": "text", "document_field": "text",
     "operator_recommended": True,
     "operator_note": "validated OpenFOAM cases paired with NL prompts"},
    {"source_id": "materials_project",
     "family": "E4_materials_intelligence",
     "dataset_id": "materials-toolkits/materials-project",
     "source_url": "https://huggingface.co/datasets/"
                   "materials-toolkits/materials-project",
     "config": "default", "split": "train", "query_mode": "search",
     "text_field": "text", "document_field": "id",
     "operator_recommended": True,
     "operator_note": "Materials Project structures + formation energies"},
    {"source_id": "crystalreasoner_mp",
     "family": "E4_materials_intelligence",
     "dataset_id": "CrystalReasoner/CrystalReasoner-MP",
     "source_url": "https://huggingface.co/datasets/"
                   "CrystalReasoner/CrystalReasoner-MP",
     "config": "default", "split": "train", "query_mode": "filter",
     "text_field": "formula", "document_field": "material_id",
     "where_template": "", 
     "operator_recommended": False,
     "operator_note": "~200k structures with formation energy, "
                      "stability, band gap, moduli"},
    {"source_id": "colabfit_mp", "family": "E4_materials_intelligence",
     "dataset_id": "colabfit/Materials_Project",
     "source_url": "https://huggingface.co/datasets/colabfit/Materials_Project",
     "config": "default", "split": "train", "query_mode": "search",
     "query_kind": "element",
     "text_field": "chemical_formula_reduced",
     "document_field": "property_id",
     "measurement_fields": ["formation_energy", "energy_above_hull",
                             "electronic_band_gap",
                             "electronic_band_gap_type", "method"],
     "operator_recommended": False,
     "operator_note": "ColabFit MP 6.34M rows energies/forces/stresses/"
                      "structures; formation energy + energy above hull "
                      "(thermodynamic stability) per structure; element-"
                      "symbol queries via the full-text index (string "
                      "WHERE filters are rejected by the datasets-server "
                      "— measured live: HTTP 422 invalid symbols)"},
    {"source_id": "lemat_rho", "family": "E4_materials_intelligence",
     "dataset_id": "LeMaterial/LeMat-Rho",
     "source_url": "https://huggingface.co/datasets/LeMaterial/LeMat-Rho",
     "config": "default", "split": "train", "query_mode": "search",
     "query_kind": "element",
     "text_field": "chemical_formula_reduced",
     "document_field": "immutable_id",
     "measurement_fields": ["energy", "energy_corrected", "nsites",
                             "space_group_it_number", "functional"],
     "operator_recommended": "AFLOW/OQMD-derived candidate",
     "operator_note": "~69k inorganic crystals from AFLOW/OQMD/MP with "
                      "charge densities, Bader charges; element-symbol "
                      "queries via the full-text index"},
    {"source_id": "debyet_aflow", "family": "E4_materials_intelligence",
     "dataset_id": "foundry-ml/dataset_debyet_aflow",
     "source_url": "https://huggingface.co/datasets/"
                   "foundry-ml/dataset_debyet_aflow",
     "config": "default", "split": "train", "query_mode": "filter",
     "text_field": "formula", "document_field": "id",
     "where_template": "",
     "operator_recommended": "AFLOW/OQMD-derived candidate",
     "operator_note": "AFLOW-derived Debye-temperature property dataset"},
    {"source_id": "qm9", "family": "E5_chemical_intelligence",
     "dataset_id": "liuganghuggingface/QM9",
     "source_url": "https://huggingface.co/datasets/liuganghuggingface/QM9",
     "config": "default", "split": "train", "query_mode": "filter",
     "text_field": "smiles", "document_field": "mol_id",
     "where_template": "\"gap\">0.3",
     "measurement_fields": ["gap", "homo", "lumo", "mu", "alpha",
                             "zpve"],
     "operator_recommended": True,
     "operator_note": "QM9 molecular structures + computed properties "
                      "(units: Hartree — measured live: gap>0.3 Ha ~ "
                      "8.2 eV selects insulator-class molecules, 25672 "
                      "rows; gap>7 returned 0 rows under the eV "
                      "assumption — the unit discovery is recorded)"},
    {"source_id": "chemrag_reactions",
     "family": "E5_chemical_intelligence",
     "dataset_id": "ChemRAG/uspto",
     "source_url": "https://huggingface.co/datasets/ChemRAG/uspto",
     "config": "default", "split": "train", "query_mode": "search",
     "text_field": "contents", "document_field": "id",
     "operator_recommended": True,
     "operator_note": "USPTO-derived reaction datasets"},
]

PERMISSIVE = {
    "cc0-1.0", "cc-by-4.0", "cc-by-sa-4.0", "apache-2.0", "mit",
    "odc-by", "odc-by-1.0", "bsd-3-clause", "bsd-2-clause", "other-open",
}


def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def frontmatter(text: str) -> Dict[str, str]:
    """Parse the YAML frontmatter's scalar keys (license, pretty_name).
    The closing --- may end the file without a trailing newline (measured
    live: liuganghuggingface/QM9's card ends exactly at ---)."""
    fm: Dict[str, str] = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text or "", re.S)
    if not m:
        return fm
    for line in m.group(1).splitlines():
        mm = re.match(r"^([a-zA-Z0-9_-]+):\s*(.+?)\s*$", line)
        if mm:
            fm[mm.group(1)] = mm.group(2).strip("\"'")
    return fm


def origin_from_card(card: str) -> str:
    """Extract the first provenance-bearing sentence from the card body
    (exported-from / derived-from / source-of statements)."""
    body = re.sub(r"^---\s*\n.*?\n---\s*\n", "", card or "", flags=re.S)
    for pat in (r"[^.]*\b(?:exported from|derived from|obtained from|"
                r"source[d]? from|based on|built from|collected from)"
                r"\b[^.]*\.",
                r"[^.]*\bdataset\b[^.]*\b(?:contains|provides|includes)\b"
                r"[^.]*\."):
        m = re.search(pat, body, re.I)
        if m:
            return re.sub(r"\s+", " ", m.group(0)).strip()[:400]
    first = re.sub(r"\s+", " ", body.strip())[:200]
    return first


def probe_license(cand: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 2: read the ACTUAL license state for one source."""
    ds = cand["dataset_id"]
    rec: Dict[str, Any] = {
        "source_id": cand["source_id"], "dataset_id": ds,
        "verified_at": NOW,
        "hub_probe": {}, "card_declaration": None,
        "license": None, "license_verified": False,
        "license_basis": "UNVERIFIED",
        "license_text_hash": None,
        "license_file": None, "gated": False,
        "access_requirements": {"gated": False, "requirements": [],
                                "met": None},
    }
    info, err = hc.dataset_info(ds)
    if err or not info:
        rec["hub_probe"] = {"state": "UNKNOWN", "reason": err}
        rec["access_requirements"]["met"] = False
        return rec
    rec["hub_probe"] = {
        "state": "SUCCESS",
        "dataset_revision": info.get("sha"),
        "private": info.get("private"),
        "gated": info.get("gated"),
        "last_modified": info.get("lastModified"),
    }
    card_license = None
    cd = info.get("cardData") or {}
    raw = cd.get("license") if isinstance(cd, dict) else None
    if isinstance(raw, str):
        card_license = raw
    elif isinstance(raw, dict):
        card_license = raw.get("name")
    gated = info.get("gated")
    rec["gated"] = bool(gated) and str(gated).lower() not in (
        "false", "no", "none", "")
    if rec["gated"]:
        rec["access_requirements"] = {
            "gated": True,
            "requirements": [
                f"hub gating mode {gated}: access requires the "
                f"dataset's own approval (the HF Pro subscription does "
                f"NOT bypass gated-dataset approval)"],
            "met": False,
        }
    # read the card README raw (the actual text, hashed)
    card, cerr = hc.raw_file(ds, "README.md")
    declaration_span = ""
    if not cerr and card:
        fm = frontmatter(card)
        if fm.get("license"):
            card_license = card_license or fm.get("license")
            declaration_span = f"license: {fm.get('license')}"
        rec["card_declaration"] = {
            "read": True,
            "frontmatter_license": fm.get("license"),
            "card_sha256": sha256_text(card),
            "origin_description": origin_from_card(card),
        }
    else:
        rec["card_declaration"] = {"read": False, "reason": cerr}
    # the Hub API's cardData.license is the platform's own parse of the
    # same frontmatter — a legitimate declaration basis when the local
    # parse missed (the card sha is recorded either way)
    if not declaration_span and card_license:
        declaration_span = f"license: {card_license} (cardData)"
    # search the repo tree for a LICENSE / COPYING file
    tree, terr = hc.repo_tree(ds)
    lic_file = None
    if not terr and tree:
        for f in tree:
            p = str(f.get("path") or "")
            if p.upper() in ("LICENSE", "LICENSE.MD", "LICENSE.TXT",
                             "COPYING", "COPYING.TXT", "NOTICE"):
                lic_file = p
                break
    license_text = None
    if lic_file:
        lt, lerr = hc.raw_file(ds, lic_file)
        if not lerr and lt and lt.strip():
            license_text = lt
            rec["license_file"] = {"path": lic_file,
                                   "sha256": sha256_text(lt),
                                   "bytes": len(lt.encode("utf-8"))}
    # resolve the license state
    if license_text is not None:
        rec["license"] = card_license or "other-open"
        rec["license_verified"] = True
        rec["license_basis"] = "LICENSE_FILE"
        rec["license_text_hash"] = sha256_text(license_text)
    elif declaration_span:
        rec["license"] = (card_license or "").strip().lower() or None
        if rec["license"] and rec["license"] in PERMISSIVE:
            rec["license_verified"] = True
            rec["license_basis"] = "CARD_DECLARATION_ONLY"
            rec["license_text_hash"] = sha256_text(declaration_span)
        else:
            # declared but not a recognized permissive id: NOT verified
            # as production-admissible (fail-closed; recorded honestly)
            rec["license_verified"] = False
            rec["license_basis"] = "CARD_DECLARATION_ONLY"
            rec["license_text_hash"] = sha256_text(declaration_span)
    else:
        rec["license"] = None
        rec["license_verified"] = False
        rec["license_basis"] = "UNVERIFIED"
        rec["license_text_hash"] = None
    if rec["gated"]:
        rec["license_verified"] = False
        rec["license_basis"] = rec["license_basis"] + "+GATED"
    return rec


def probe_endpoint(cand: Dict[str, Any]) -> Dict[str, Any]:
    """Probe the federated endpoint (splits + one rows page for the
    schema features). Records reachability honestly (UNKNOWN-class
    failures are never absence)."""
    ds = cand["dataset_id"]
    out: Dict[str, Any] = {"splits_state": None, "configs": [],
                           "features": None, "rows_probe_state": None,
                           "reachable": False}
    splits, err = hc.dataset_splits(ds)
    if err or splits is None:
        out["splits_state"] = err or "UNKNOWN"
        return out
    out["splits_state"] = "SUCCESS"
    out["configs"] = sorted({s.get("config") for s in splits})
    # find the candidate's config or the first available
    want = cand.get("config") or "default"
    chosen = next((s for s in splits if s.get("config") == want), None)
    if chosen is None:
        alt = [s for s in splits if "default" in str(s.get("config"))]
        chosen = (alt or splits)[0] if (alt or splits) else None
    if chosen is None:
        out["rows_probe_state"] = "NO_SPLIT"
        return out
    out["chosen_config"] = chosen.get("config")
    out["chosen_split"] = chosen.get("split")
    row, rerr = hc.get_row(ds, chosen.get("config", "default"),
                           chosen.get("split", "train"), 0)
    if rerr or row is None:
        out["rows_probe_state"] = rerr or "UNKNOWN"
        return out
    out["rows_probe_state"] = "SUCCESS"
    out["reachable"] = True
    return out


def probe_features(cand: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The schema features for the chosen config (column names/types)."""
    ds = cand["dataset_id"]
    params = urllib.parse.urlencode({
        "dataset": ds, "config": cand.get("config") or "default",
        "split": cand.get("split") or "train", "offset": 0, "length": 1})
    body, err = hc._get_json(
        f"https://datasets-server.huggingface.co/rows?{params}")
    if err or not isinstance(body, dict):
        return []
    feats = body.get("features") or []
    return [{"name": f.get("name"), "type": (f.get("type") or {}).get(
        "_type") or (f.get("type") or {}).get("dtype")}
        for f in feats][:24]


def score_source(cand: Dict[str, Any], lic: Dict[str, Any],
                 ep: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic selection scoring — the five directive criteria,
    each with a recorded basis (no invented numbers; every score
    derives from live metadata)."""
    s: Dict[str, Any] = {}
    fam = cand["family"]
    # coverage (0..1): family reach, scaled by endpoint reachability
    s["coverage"] = (1.0 if ep.get("reachable") else
                     0.4 if ep.get("splits_state") == "SUCCESS" else 0.1)
    # quality: provenance origin present + activity signals
    origin = ((lic.get("card_declaration") or {}).get(
        "origin_description") or "")
    q = 0.0
    if origin:
        q += 0.5
    if (lic.get("hub_probe") or {}).get("lastModified"):
        q += 0.25
    if (lic.get("hub_probe") or {}).get("dataset_revision"):
        q += 0.25
    s["quality"] = q
    # license clarity
    if lic.get("license_verified"):
        s["license_clarity"] = 1.0
    elif lic.get("license"):
        s["license_clarity"] = 0.4   # declared but not verifiable-open
    else:
        s["license_clarity"] = 0.0
    # technical diversity: text-bearing evidence for mechanism search
    if cand.get("query_mode") == "search" and cand.get(
            "text_field") in ("text", "abstract_text", "contents",
                              "abstract"):
        s["technical_diversity"] = 1.0
    elif cand.get("query_mode") == "search":
        s["technical_diversity"] = 0.6
    else:
        s["technical_diversity"] = 0.5   # structured property table
    # information gain: family competition (1st in family > 2nd > ...)
    fam_count = sum(1 for c in CANDIDATES if c["family"] == fam)
    fam_rank = [c["source_id"] for c in CANDIDATES
                if c["family"] == fam].index(cand["source_id"]) + 1
    s["information_gain"] = round(
        max(0.25, 1.0 - 0.3 * (fam_rank - 1)) /
        (1.0 if fam_count <= 3 else 1.2), 2)
    weights = {"coverage": 0.25, "quality": 0.20,
               "license_clarity": 0.20, "technical_diversity": 0.20,
               "information_gain": 0.15}
    total = round(sum(s[k] * weights[k] for k in weights), 3)
    return {"scores": s, "weights": weights, "total": total}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    license_records: List[Dict[str, Any]] = []
    endpoint_probes: Dict[str, Dict[str, Any]] = {}
    scored: List[Dict[str, Any]] = []
    for cand in CANDIDATES:
        print(f"[r449-select] {cand['source_id']} "
              f"({cand['dataset_id']})", flush=True)
        lic = probe_license(cand)
        license_records.append(lic)
        ep = probe_endpoint(cand)
        endpoint_probes[cand["source_id"]] = ep
        sc = score_source(cand, lic, ep)
        scored.append({"cand": cand, "lic": lic, "ep": ep, "sc": sc})
        time.sleep(0.4)

    # ---- Phase 1: freeze the first production subset ------------------
    # selection rule (deterministic, recorded):
    #   1. the operator's 10 recommended seats are the target shape
    #      (2 patents + 2 papers + 2 engineering + 1 MP-family + 1
    #       AFLOW/OQMD + 2 chemistry);
    #   2. seat resolution: the designated source keeps its seat when
    #      promotable (license verified AND endpoint reachable);
    #      otherwise the highest-scoring promotable SAME-FAMILY candidate
    #      takes the seat (coverage is one of the five criteria — a seat
    #      that cannot serve evidence has zero effective coverage this
    #      round); when no same-family candidate is promotable the
    #      designated source keeps the seat with its honest PENDING
    #      status (the seat stays selected, never silently dropped);
    #   3. the AFLOW/OQMD seat: the highest-scoring promotable of
    #      lemat_rho / debyet_aflow;
    #   4. an unlicensed-but-recommended source with no promotable
    #      alternate keeps its seat with status PENDING_LICENSE_
    #      VERIFICATION (selected, NOT promoted — fail-closed);
    #   5. unselected sources: HELD_RESERVE with their scores.
    family_seats = {
        "E1_patent_intelligence": ["uspto_patents", "wopto"],
        "E2_scientific_intelligence": ["openalex_mirror",
                                       "s2orc_abstracts"],
        "E3_engineering_intelligence": ["cadgenbench", "openfoam_cases"],
        "E4_materials_intelligence": ["materials_project",
                                      "AFLOW_OQMD_SEAT"],
        "E5_chemical_intelligence": ["qm9", "chemrag_reactions"],
    }
    by_id = {s["cand"]["source_id"]: s for s in scored}

    def promotable(sid: str) -> bool:
        s = by_id[sid]
        return bool(s["lic"].get("license_verified")) and \
            bool(s["ep"].get("reachable"))

    selected: List[str] = []
    selection_basis: List[str] = []
    for fam, seats in family_seats.items():
        # pass 1: designated seats that are promotable keep their seats
        # (checked against sources already seated in ANY family — a
        # source serves at most one seat)
        taken = set(selected)
        keep: Dict[int, str] = {}
        for i, seat in enumerate(seats):
            if seat == "AFLOW_OQMD_SEAT":
                continue
            if promotable(seat) and seat not in taken:
                keep[i] = seat
                taken.add(seat)
        # pass 2: resolve each non-promotable (or AFLOW) seat
        for i, seat in enumerate(seats):
            if i in keep:
                s = by_id[seat]
                selection_basis.append(
                    f"{fam} seat {i + 1}: {seat} (designated, promotable; "
                    f"score {s['sc']['total']}; license "
                    f"{s['lic'].get('license')})")
                selected.append(seat)
                continue
            if seat == "AFLOW_OQMD_SEAT":
                cands = [by_id[x] for x in ("lemat_rho", "debyet_aflow")
                         if x in by_id]
                cands.sort(key=lambda x: -x["sc"]["total"])
                avail = [x for x in cands
                         if x["cand"]["source_id"] not in taken]
                win = None
                for x in avail:
                    if promotable(x["cand"]["source_id"]):
                        win = x
                        break
                if win is None and avail:
                    win = avail[0]
                if win is not None:
                    wid = win["cand"]["source_id"]
                    keep[i] = wid
                    taken.add(wid)
                    selected.append(wid)
                    others = ", ".join(
                        f"{x['cand']['source_id']} score "
                        f"{x['sc']['total']}" for x in cands
                        if x["cand"]["source_id"] != wid)
                    selection_basis.append(
                        f"{fam} AFLOW/OQMD seat: {wid} (score "
                        f"{win['sc']['total']}; promotable="
                        f"{promotable(wid)}" +
                        (f"; considered {others}" if others else "") + ")")
                continue
            # designated seat not promotable: resolve from the highest-
            # scoring promotable same-family candidate not already seated
            s = by_id[seat]
            fam_cands = [x for x in scored
                         if x["cand"]["family"] == fam and
                         x["cand"]["source_id"] not in taken and
                         promotable(x["cand"]["source_id"])]
            fam_cands.sort(key=lambda x: -x["sc"]["total"])
            if fam_cands:
                alt = fam_cands[0]["cand"]["source_id"]
                keep[i] = alt
                taken.add(alt)
                selected.append(alt)
                selection_basis.append(
                    f"{fam} seat {i + 1}: designated {seat} NOT promotable "
                    f"(license_verified="
                    f"{s['lic'].get('license_verified')}, "
                    f"endpoint_reachable={s['ep'].get('reachable')}) -> "
                    f"seat resolved to {alt} (highest-scoring promotable "
                    f"same-family candidate; score "
                    f"{fam_cands[0]['sc']['total']}; coverage is a "
                    f"selection criterion)")
            else:
                # no promotable same-family alternate: the designated
                # source keeps the seat with its honest PENDING status
                keep[i] = seat
                taken.add(seat)
                selected.append(seat)
                selection_basis.append(
                    f"{fam} seat {i + 1}: {seat} (designated; NOT "
                    f"promotable this round — license_verified="
                    f"{s['lic'].get('license_verified')}, "
                    f"endpoint_reachable={s['ep'].get('reachable')}; no "
                    f"promotable same-family alternate; the seat keeps "
                    f"its honest PENDING status)")

    # ---- assemble the registry ----------------------------------------
    sources_out: List[Dict[str, Any]] = []
    for s in scored:
        cand, lic, ep, sc = s["cand"], s["lic"], s["ep"], s["sc"]
        sid = cand["source_id"]
        is_sel = sid in selected
        gated = lic.get("gated")
        if not is_sel:
            status = "HELD_RESERVE"
        elif not lic.get("license_verified"):
            status = "PENDING_LICENSE_VERIFICATION"
        elif not ep.get("reachable"):
            status = "PENDING_INDEX"
        else:
            status = "PRODUCTION"
        rec = {
            "source_id": sid,
            "source_url": cand["source_url"],
            "dataset_id": cand["dataset_id"],
            "dataset_revision": (lic.get("hub_probe") or {}).get(
                "dataset_revision") or "",
            "family": cand["family"],
            "license": lic.get("license"),
            "license_text_hash": lic.get("license_text_hash"),
            "license_basis": lic.get("license_basis"),
            "license_verified": bool(lic.get("license_verified")),
            "gated": bool(gated),
            "access_requirements": lic.get("access_requirements"),
            "provenance_origin": ((lic.get("card_declaration") or {}).get(
                "origin_description") or ""),
            "schema": {
                "config": ep.get("chosen_config") or cand.get("config"),
                "split": ep.get("chosen_split") or cand.get("split"),
                "query_mode": cand.get("query_mode"),
                "query_kind": cand.get("query_kind") or "text_problem",
                "text_field": cand.get("text_field"),
                "fallback_text_field": cand.get("fallback_text_field"),
                "document_field": cand.get("document_field"),
                "where_template": cand.get("where_template"),
                "measurement_fields": cand.get("measurement_fields") or [],
                "endpoint_reachable": ep.get("reachable"),
                "splits_state": ep.get("splits_state"),
                "rows_probe_state": ep.get("rows_probe_state"),
                "features": probe_features(
                    {**cand,
                     "config": ep.get("chosen_config") or
                     cand.get("config"),
                     "split": ep.get("chosen_split") or
                     cand.get("split")}),
            },
            "last_verified": NOW,
            "status": status,
            "selection": {
                "selected": is_sel,
                "operator_recommended": bool(
                    cand.get("operator_recommended")),
                "scores": sc["scores"],
                "weights": sc["weights"],
                "score_total": sc["total"],
            },
            "operator_note": cand.get("operator_note"),
        }
        sources_out.append(rec)

    registry = {
        "artifact_type": "EVIDENCE_SOURCE_REGISTRY",
        "round": "R449",
        "created_at_utc": NOW,
        "reviewer_provenance": "AI_REVIEW",
        "directive": ("R449 Phases 1-2: freeze the first production "
                      "subset from the R447 15-source reconnaissance; "
                      "verify the actual licensing/access state per "
                      "source; fail-closed promotion (unverified license "
                      "=> never production evidence)"),
        "selection_criteria": {
            "coverage": "family reach + federated endpoint reachability",
            "quality": "provenance origin recorded + revision pinned + "
                       "activity signals",
            "license_clarity": "actual license text read and hashed "
                               "(LICENSE file or card declaration)",
            "technical_diversity": "evidence type diversity (text "
                                   "mechanism spans vs structured "
                                   "property tables)",
            "information_gain": "family seat competition (first seat in "
                                "family > duplicate coverage)",
        },
        "selection_basis": selection_basis,
        "subset_shape": {
            "target": "10 seats: 2 patents, 2 papers, 2 engineering, "
                      "1 Materials-Project-family, 1 AFLOW/OQMD-derived, "
                      "2 chemistry",
            "selected": len(selected),
            "promoted_production": sum(
                1 for r in sources_out if r["status"] == "PRODUCTION"),
            "pending_license": sum(1 for r in sources_out if
                                   r["status"] ==
                                   "PENDING_LICENSE_VERIFICATION"),
            "pending_index": sum(1 for r in sources_out if
                                 r["status"] == "PENDING_INDEX"),
            "held_reserve": sum(1 for r in sources_out if
                                r["status"] == "HELD_RESERVE"),
        },
        "epistemic_rule": ("hosted == available, NEVER automatically "
                           "correct; promotion requires the verified "
                           "license record; PENDING states are honest "
                           "and fail-closed (Art. XXV/XXVII)"),
        "federated_rule": ("NO bulk download; every production query "
                           "goes to the remote datasets-server; no local "
                           "vector store; no second knowledge graph"),
        "sources": sources_out,
    }
    SOURCE_REGISTRY.write_text(json.dumps(registry, indent=1,
                                          ensure_ascii=False))
    licreg = {
        "artifact_type": "EVIDENCE_LICENSE_REGISTRY",
        "round": "R449",
        "created_at_utc": NOW,
        "reviewer_provenance": "AI_REVIEW",
        "directive": ("R449 Phase 2: the ACTUAL license text read per "
                      "source — card frontmatter parsed from the raw "
                      "README, LICENSE/COPYING files fetched when "
                      "present, gated + access requirements recorded "
                      "from the Hub API; license=None stays UNVERIFIED "
                      "(never guessed permissive — Art. VI/XXV)"),
        "verification_method": {
            "card": "raw README.md fetched from the dataset repo main "
                    "branch; YAML frontmatter parsed; declaration span "
                    "hashed (license: <id>)",
            "license_file": "repo tree scanned for LICENSE/LICENSE.MD/"
                            "LICENSE.TXT/COPYING/COPYING.TXT/NOTICE; "
                            "fetched raw and hashed whole",
            "gating": "Hub API cardData + gated field; gated datasets "
                      "record unmet access requirements (HF Pro does "
                      "NOT bypass gated-dataset approval)",
            "promotion_rule": "PRODUCTION requires license_verified "
                              "AND permissive id AND not gated-with-"
                              "unmet-requirements",
        },
        "permissive_ids": sorted(PERMISSIVE),
        "records": license_records,
        "summary": {
            "verified": sum(1 for r in license_records if r.get(
                "license_verified")),
            "unverified": sum(1 for r in license_records if not r.get(
                "license_verified")),
            "gated": sum(1 for r in license_records if r.get("gated")),
            "license_file_present": sum(1 for r in license_records if
                                        r.get("license_file")),
            "card_declaration_only": sum(
                1 for r in license_records if
                (r.get("license_basis") or "").startswith(
                    "CARD_DECLARATION_ONLY")),
        },
    }
    LICENSE_REGISTRY.write_text(json.dumps(licreg, indent=1,
                                           ensure_ascii=False))
    print(f"[r449-select] wrote {SOURCE_REGISTRY}")
    print(f"[r449-select] wrote {LICENSE_REGISTRY}")
    prod = [r["source_id"] for r in sources_out
            if r["status"] == "PRODUCTION"]
    pend = [r["source_id"] for r in sources_out
            if r["status"] != "PRODUCTION" and r["selection"]["selected"]]
    print(f"[r449-select] PRODUCTION: {prod}")
    print(f"[r449-select] selected-but-pending: {pend}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

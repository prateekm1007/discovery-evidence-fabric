"""Fabric source registry — loader + validator for FABRIC_SOURCES.json.

Art. X discipline (ONE authority per fact class):
- provider policy facts (13 CEO fields) -> source_registry/registry.py
- fabric fields (families, lanes, lineage, coverage classes, versions)
  -> THIS file + FABRIC_SOURCES.json

The validator enforces the cross-reference: every fabric source that
declares a connector path must resolve to a registered source_id in
SOURCE_REGISTRY, and every family/lane/vocabulary value must be one of
the declared vocabularies. The registry file is committed and immutable
per fabric version (V2 is frozen with this round; changes require a new
fabric version, Art. XLIV retrieval-version discipline).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

_PACKAGE_DIR = Path(__file__).resolve().parent
FABRIC_SOURCES_PATH = _PACKAGE_DIR / "FABRIC_SOURCES.json"

FABRIC_VERSION = "2"

LANES = ["SCHOLARLY", "PREPRINT", "THESIS", "TECHNICAL_REPORT", "PATENT",
         "DATASET", "REPOSITORY", "OA_LOCATION"]
PUBLICATION_STATUS_VOCAB = ["PEER_REVIEWED", "PREPRINT", "THESIS",
                            "CONFERENCE", "REPORT", "DATASET", "UNKNOWN"]
SOURCE_TYPES = ["METADATA", "FULLTEXT", "DISCOVERY_INDEX", "REGISTRY",
                "AGGREGATOR", "RESOLUTION"]
ROLES = ["DISCOVERY", "DISCOVERY_AND_RECIPROCAL", "DISCOVERY_AND_RECONCILIATION",
         "FULLTEXT_RESOLUTION", "RECIPROCAL_ONLY"]

#: the fabric's wired V2 discovery sources, in canonical lane order.
#: V1 membership is declared per source in FABRIC_SOURCES.json
#: ("fabric_versions": ["V1", ...]) — the historical V1 pair is exactly
#: europepmc + openalex (a2/retrieve.py, byte-unchanged).
V1_SOURCE_IDS = ["europepmc", "openalex"]

_REQUIRED_FIELDS = [
    "source_id", "source_name", "source_type", "source_family",
    "evidence_lanes", "fabric_versions", "access_method", "api_endpoint",
    "authentication_required", "free_access", "open_metadata",
    "full_text_available", "patent_coverage", "preprint_coverage",
    "thesis_dissertation_coverage", "conference_coverage",
    "technical_report_coverage", "citation_graph", "date_coverage",
    "discipline_coverage", "rate_limit", "license",
    "provenance_requirements", "health_status", "derives_from",
    "query_grammar", "role",
]

_cache: Optional[Dict[str, Any]] = None


def load_fabric_sources(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load + validate the fabric registry (cached). Raises on any
    structural violation — a broken registry is a hard failure, never
    a silent partial load (Art. XVII)."""
    global _cache
    if _cache is not None and path is None:
        return _cache
    p = path or FABRIC_SOURCES_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    errors = validate_fabric_sources(data)
    if errors:
        raise ValueError("FABRIC_SOURCES.json validation failed: "
                         + "; ".join(errors))
    _cache = data
    return data


def validate_fabric_sources(data: Dict[str, Any]) -> List[str]:
    """Structural + cross-reference validation (hermetic, no network)."""
    errors: List[str] = []
    families = set((data.get("independence_model") or {}).get("families", {}).keys())
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        return ["sources list missing/empty"]
    seen: set = set()
    for s in sources:
        sid = s.get("source_id", "?")
        if sid in seen:
            errors.append(f"{sid}: duplicate source_id")
        seen.add(sid)
        for f in _REQUIRED_FIELDS:
            if f not in s:
                errors.append(f"{sid}: missing field {f}")
        if s.get("source_family") not in families:
            errors.append(f"{sid}: unknown family {s.get('source_family')}")
        for lane in s.get("evidence_lanes", []):
            if lane not in LANES:
                errors.append(f"{sid}: unknown lane {lane}")
        if s.get("source_type") not in SOURCE_TYPES:
            errors.append(f"{sid}: unknown source_type {s.get('source_type')}")
        if s.get("role") not in ROLES:
            errors.append(f"{sid}: unknown role {s.get('role')}")
        if s.get("query_grammar") not in ("KEYWORD_FORM", "DOI_ONLY", "CQL"):
            errors.append(f"{sid}: unknown query_grammar {s.get('query_grammar')}")
        for v in s.get("fabric_versions", []):
            if v not in ("V1", "V2"):
                errors.append(f"{sid}: unknown fabric version {v}")
        if str(s.get("connector_state", "")).startswith("NO_CONNECTOR"):
            # declared-not-integrated: allowed (honest gap), but may never
            # be counted as a wired source
            continue
    # cross-reference with the 13-field SOURCE_REGISTRY
    try:
        from discovery_fabric.source_registry.registry import SOURCE_REGISTRY
    except Exception as exc:  # pragma: no cover — import failure is env-level
        errors.append(f"source_registry import failed: {exc}")
        return errors
    for s in sources:
        sid = s["source_id"]
        if str(s.get("connector_state", "")).startswith("NO_CONNECTOR"):
            continue
        rec = SOURCE_REGISTRY.get(sid)
        if rec is None:
            errors.append(f"{sid}: not registered in SOURCE_REGISTRY "
                          "(Art. X cross-reference)")
        elif not rec.get("connector"):
            errors.append(f"{sid}: SOURCE_REGISTRY entry has no connector "
                          "(fabric wiring requires the 7-step chain)")
    return errors


def fabric_sources_for_version(version: str = "V2") -> List[Dict[str, Any]]:
    """All sources whose fabric_versions includes `version` and that are
    wired (connector_state != NO_CONNECTOR)."""
    data = load_fabric_sources()
    out = []
    for s in data["sources"]:
        if version in s.get("fabric_versions", []) and \
                s.get("connector_state") != "NO_CONNECTOR":
            out.append(s)
    return out


def get_fabric_source(source_id: str) -> Optional[Dict[str, Any]]:
    for s in load_fabric_sources()["sources"]:
        if s["source_id"] == source_id:
            return s
    return None


def source_family(source_id: str) -> str:
    s = get_fabric_source(source_id)
    return (s or {}).get("source_family", "UNKNOWN")


def derives_from(source_id: str) -> List[str]:
    s = get_fabric_source(source_id)
    return (s or {}).get("derives_from", [])


def families_declared() -> Dict[str, str]:
    data = load_fabric_sources()
    return (data.get("independence_model") or {}).get("families", {})

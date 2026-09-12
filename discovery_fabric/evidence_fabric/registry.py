"""Evidence-fabric source registry — loader + selection criteria.

Phase 1 (freeze the source-selection layer): the FIRST production
subset selected from the R447 15-source reconnaissance, maximizing
coverage / quality / license clarity / technical diversity /
information gain.

Phase 2 (read the actual license text): every promoted source carries
a LIVE-VERIFIED license record — the card declaration text read and
hashed, the LICENSE file fetched when the repo has one, gated/access
requirements recorded. A source whose licensing/access state cannot be
verified is NOT promoted to production evidence (it stays
status=PENDING_LICENSE_VERIFICATION in the registry and every record
from it is BLOCKED_LICENSE_UNVERIFIED — fail-closed, Art. XXVII).

Authority (Art. X): the COMMITTED registry JSON is the single
authority for what is production evidence; this module only loads and
validates it. The generator script (scripts/r449_source_selection.py)
is the regeneration path.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "R449" / "EVIDENCE_SOURCE_REGISTRY.json"
LICENSE_REGISTRY_PATH = REPO_ROOT / "R449" / "EVIDENCE_LICENSE_REGISTRY.json"

#: registry status vocabulary (closed)
STATUS_VOCAB = [
    "PRODUCTION",                    # verified + promoted: evidence flows
    "PENDING_LICENSE_VERIFICATION",  # license/access state unreadable ->
                                     # blocked from evidence flow
    "PENDING_INDEX",                 # federated endpoint not yet reachable
    "HELD_RESERVE",                  # reconnaissance-only for this subset
                                     # (not selected in the first production
                                     # set; a future subset decision)
]

#: the selection criteria (directive Phase 1) with their frozen weights
SELECTION_CRITERIA = {
    "coverage": 0.25,        # breadth of the source's domain reach
    "quality": 0.20,         # provenance origin + curation signals
    "license_clarity": 0.20, # verified declaration / standard license
    "technical_diversity": 0.20,  # distinct family / distinct evidence type
    "information_gain": 0.15,     # expected mechanism-search value
}

#: permissive licenses verified as production-admissible (OSI/SPDX
#: open licenses; the license TEXT is what was read — the id maps to
#: the declaration recorded in the license registry)
_PERMISSIVE = {
    "cc0-1.0", "cc-by-4.0", "cc-by-sa-4.0", "apache-2.0", "mit",
    "odc-by", "odc-by-1.0", "bsd-3-clause", "bsd-2-clause",
    "other-open",
}

_cache: Optional[Dict[str, Any]] = None


def load_registry(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load + structurally validate the committed source registry."""
    global _cache
    if _cache is not None and path is None:
        return _cache
    p = path or REGISTRY_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    errors = validate_registry(data)
    if errors:
        raise ValueError("EVIDENCE_SOURCE_REGISTRY.json invalid: "
                         + "; ".join(errors))
    _cache = data
    return data


def validate_registry(data: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        return ["sources list missing/empty"]
    seen: set = set()
    prod = 0
    for s in sources:
        sid = s.get("source_id")
        if not sid:
            errors.append("source without source_id")
            continue
        if sid in seen:
            errors.append(f"duplicate source_id {sid}")
        seen.add(sid)
        for k in ("source_url", "dataset_id", "family", "license",
                  "gated", "access_requirements", "provenance_origin",
                  "schema", "last_verified", "status"):
            if k not in s:
                errors.append(f"{sid}: missing {k}")
        if s.get("status") not in STATUS_VOCAB:
            errors.append(f"{sid}: status not in vocabulary")
        if s.get("family") not in (
                "E1_patent_intelligence", "E2_scientific_intelligence",
                "E3_engineering_intelligence", "E4_materials_intelligence",
                "E5_chemical_intelligence", "E6_domain_intelligence"):
            errors.append(f"{sid}: family not in vocabulary")
        if s.get("status") == "PRODUCTION":
            prod += 1
            if not s.get("dataset_revision"):
                errors.append(f"{sid}: PRODUCTION without dataset_revision")
            if not s.get("license_text_hash"):
                errors.append(f"{sid}: PRODUCTION without license_text_hash")
            if not s.get("license_verified"):
                errors.append(f"{sid}: PRODUCTION without license_verified "
                              "(fail-closed promotion rule)")
    if prod == 0:
        errors.append("no PRODUCTION source — the registry must freeze at "
                      "least one verified source or declare the whole "
                      "fabric blocked")
    return errors


def production_sources(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """The sources licensed + verified for production evidence flow.

    The registry's per-source wiring (config/split/query_mode/text_field/
    document_field/where_template/measurement_fields/fallback_text_field)
    is stored under `schema` in the committed JSON; this loader FLATTENS
    it to the top level so the retrieval channel reads one record shape
    (the committed JSON remains the authority — Art. X).
    """
    reg = load_registry(path)
    out: List[Dict[str, Any]] = []
    for s in reg["sources"]:
        if s.get("status") != "PRODUCTION":
            continue
        flat = dict(s)
        schema = s.get("schema") or {}
        for k in ("config", "split", "query_mode", "text_field",
                  "document_field", "where_template",
                  "measurement_fields", "fallback_text_field",
                  "query_kind"):
            if k in schema:
                flat[k] = schema.get(k)
        out.append(flat)
    return out


def source_by_id(source_id: str,
                 path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    reg = load_registry(path)
    for s in reg["sources"]:
        if s.get("source_id") == source_id:
            return s
    return None


def license_ok(source: Dict[str, Any]) -> bool:
    """The promotion rule: license verified AND permissive AND not
    gated-with-unmet-requirements. A source with license=None stays
    NOT ok (Art. XXVII: no threshold invention, no silent promotion)."""
    if not source.get("license_verified"):
        return False
    lic = str(source.get("license") or "").strip().lower()
    if lic and lic not in _PERMISSIVE:
        return False
    gated = source.get("gated")
    if gated and str(gated).lower() not in ("false", "no", "none", ""):
        ac = source.get("access_requirements")
        if not (isinstance(ac, dict) and ac.get("met")):
            return False
    return True


def load_license_registry(path: Optional[Path] = None) -> Dict[str, Any]:
    p = path or LICENSE_REGISTRY_PATH
    return json.loads(p.read_text(encoding="utf-8"))

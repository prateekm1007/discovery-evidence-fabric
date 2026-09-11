#!/usr/bin/env python3
"""scripts/r446_cio_extraction.py — R446-C1 Task 1: the canonical CIO
field extractor (the driver-side verifier/extractor for the Canonical
Invention Object HTTP response).

THE DEFECT THIS CLOSES (recorded in R444/R445 PRODUCTION_RUNS.json):
the production drivers recorded `cio_http: 200` while their extractors
read a PHANTOM schema — keys that have never existed in the CIO body:

  r444 driver:  architecture.mechanism / engineering.technology_class /
                artifact_state.components / experiment_contract
  r445 driver:  summary / top-level mechanism / technology_class /
                n_components

The real body (toscanini/cio.py::build_cio, server adds present=true
and strips provenance.run_dir) carries:

  identity.mechanism          (dict after _unwrap: mechanism /
                                intervention / expected_effect — or str)
  identity.domain             {domain, label, basis, ...}
  geometry.domain_family      the R445-A canonical family id
  geometry.components         the bridge report's named components
  experiment.decisive_experiment  the Art. LII record (dict)

CONTRACT (the directive's acceptance):
  1. The extractor CONSUMES the canonical shape — it never demands the
     engine emit new fields (no engine semantics altered to fit the
     driver; the canonical shape is the authority, Art. X).
  2. HTTP 200 + canonical field extraction == CIO_FIELDS_VERIFIED.
  3. HTTP 200 with missing/malformed fields can NEVER be interpreted
     as semantic success: the typed state stays explicitly incomplete
     with the missing canonical paths named (Art. XXV / Art. V —
     absence of a field is evidence of nothing).
  4. present=false (the honest no-artifacts 200) is an HONEST state,
     distinct from malformed (typed separately, never an error).

Typed verdicts:
  CIO_FIELDS_VERIFIED         HTTP-body present=true AND every required
                              canonical field extracted
  CIO_PRESENT_FALSE_HONEST    200 + present=false (run has no
                              invention-side artifacts — honest absence)
  CIO_BODY_NOT_JSON           body is not a JSON object
  CIO_BODY_NOT_CIO            JSON object but kind != CANONICAL_INVENTION_
                              OBJECT (wrong endpoint shape)
  CIO_MISSING_CANONICAL_FIELDS  present=true but required canonical
                              paths absent/null — INCLUDING the old
                              phantom-schema bodies (they land here)

Usage (drivers import; tests import):
  from r446_cio_extraction import extract_cio_fields
  summary = extract_cio_fields(http_status, body)
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# The authoritative CIO response shape — READ from toscanini/cio.py's
# build_cio return (the ONE authority; this module documents the HTTP
# projection of it: server adds `present`, strips `provenance.run_dir`).
# ---------------------------------------------------------------------------
CIO_KIND = "CANONICAL_INVENTION_OBJECT"

# required canonical paths: (path tuple, human name, extractor)
REQUIRED_CANONICAL_FIELDS: List[tuple] = [
    (("identity", "mechanism"), "identity.mechanism"),
    (("geometry", "domain_family"), "geometry.domain_family"),
    (("geometry", "components"), "geometry.components"),
    (("experiment", "decisive_experiment"),
     "experiment.decisive_experiment"),
]

VERIFIED = "CIO_FIELDS_VERIFIED"
PRESENT_FALSE = "CIO_PRESENT_FALSE_HONEST"
NOT_JSON = "CIO_BODY_NOT_JSON"
NOT_CIO = "CIO_BODY_NOT_CIO"
MISSING = "CIO_MISSING_CANONICAL_FIELDS"


def _norm_mechanism(m: Any) -> Dict[str, Any]:
    """identity.mechanism arrives as a dict (mechanism / intervention /
    expected_effect) or a bare string — normalize WITHOUT inventing
    content: absent sub-fields stay explicitly None."""
    if isinstance(m, dict):
        return {
            "mechanism": (m.get("mechanism") or None),
            "intervention": (m.get("intervention") or None),
            "expected_effect": (m.get("expected_effect") or None),
        }
    return {"mechanism": m if isinstance(m, str) else None,
            "intervention": None, "expected_effect": None}


def _get(body: Dict[str, Any], path: tuple) -> Any:
    cur: Any = body
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _is_present(v: Any) -> bool:
    """A canonical field is PRESENT when it carries actual content:
    non-empty string, non-null, or a (possibly empty, but typed) list —
    geometry.components may honestly be [] (no bridge ran); the FIELD is
    present when the key exists with list type. Absent key -> None ->
    NOT present."""
    if v is None:
        return False
    if isinstance(v, str):
        return len(v.strip()) > 0
    if isinstance(v, (list, dict)):
        return True
    return True


def extract_cio_fields(http_status: Optional[int],
                       body: Any) -> Dict[str, Any]:
    """The canonical-shape extractor + typed verdict. `body` is the
    parsed HTTP body (or None when the request failed / was not JSON).

    The verdict NEVER converts HTTP 200 + missing fields into success:
    only the simultaneous presence of every required canonical field
    yields CIO_FIELDS_VERIFIED."""
    out: Dict[str, Any] = {
        "http_status": http_status,
        "extraction_version": "r446-cio-extraction/1.0.0",
        "canonical_fields_consumed": [n for _, n in
                                      REQUIRED_CANONICAL_FIELDS],
        "extraction_state": None,
        "missing_canonical_fields": [],
        "fields": {},
    }
    if not isinstance(body, dict):
        out["extraction_state"] = NOT_JSON
        out["note"] = ("HTTP body is not a JSON object — nothing may be "
                       "inferred from it (Art. XXV); this is never "
                       "semantic success")
        return out
    kind = body.get("kind")
    if body.get("present") is False:
        # the honest no-artifacts response (server's explicit 200 shape)
        out["extraction_state"] = PRESENT_FALSE
        out["note"] = ("HTTP 200 with present=false: the run has no "
                       "invention-side artifacts yet — honest absence, "
                       "explicitly incomplete, never semantic success")
        return out
    if kind != CIO_KIND:
        out["extraction_state"] = NOT_CIO
        out["note"] = (f"body kind={kind!r} is not {CIO_KIND!r} — wrong "
                       "endpoint shape; explicitly incomplete")
        return out

    mech = _norm_mechanism(_get(body, ("identity", "mechanism")))
    domain_family = _get(body, ("geometry", "domain_family"))
    components = _get(body, ("geometry", "components"))
    dex = _get(body, ("experiment", "decisive_experiment"))

    out["fields"] = {
        "mechanism": mech,
        "technology_class_note": (
            "technology_class is a bridge-layer field (BRIDGE_REPORT "
            "geometry.key_dimensions), deliberately NOT projected into "
            "the CIO; the canonical domain-class field the CIO carries "
            "is geometry.domain_family (R445-A vocabulary)"),
        "domain_family": domain_family if isinstance(domain_family, str)
        else None,
        "n_components": len(components) if isinstance(components, list)
        else None,
        "components_present_typed": isinstance(components, list),
        "decisive_experiment_present": dex is not None,
        "identity_final_status": _get(body, ("identity",
                                             "final_status")),
        "identity_domain": _get(body, ("identity", "domain"))
        if isinstance(_get(body, ("identity", "domain")), dict) else None,
    }

    missing: List[str] = []
    if not _is_present(mech.get("mechanism")):
        missing.append("identity.mechanism")
    if not _is_present(domain_family):
        missing.append("geometry.domain_family")
    if not isinstance(components, list):
        missing.append("geometry.components")
    if dex is None:
        missing.append("experiment.decisive_experiment")
    out["missing_canonical_fields"] = missing

    if missing:
        out["extraction_state"] = MISSING
        out["note"] = ("HTTP 200 with present=true but canonical fields "
                       "missing: " + ", ".join(missing) +
                       " — explicitly incomplete; HTTP 200 is transport "
                       "success, never semantic success")
    else:
        out["extraction_state"] = VERIFIED
        out["note"] = ("HTTP 200 + canonical field extraction: mechanism, "
                       "domain_family, components (typed list), and "
                       "decisive_experiment all extracted from the "
                       "canonical CIO shape")
    return out


def summarize_for_record(http_status: Optional[int],
                         body: Any) -> Dict[str, Any]:
    """The compact projection the production drivers record per run —
    the FULL extraction (typed state + missing fields) travels in the
    record; nothing is collapsed to a bare HTTP code."""
    full = extract_cio_fields(http_status, body)
    return {
        "cio_http": http_status,
        "cio_extraction_state": full["extraction_state"],
        "cio_missing_fields": full["missing_canonical_fields"],
        "mechanism": (full["fields"].get("mechanism") or {}).get(
            "mechanism") or "",
        "domain_family": full["fields"].get("domain_family"),
        "n_components": full["fields"].get("n_components"),
        "decisive_experiment_present": full["fields"].get(
            "decisive_experiment_present"),
    }


if __name__ == "__main__":  # pragma: no cover — operator probe
    import json
    src = sys.argv[1] if len(sys.argv) > 1 else "/tmp/cio_probe.json"
    body = json.loads(Path(src).read_text())
    print(json.dumps(summarize_for_record(200, body), indent=1))

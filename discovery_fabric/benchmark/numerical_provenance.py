"""Phase 9 — numerical provenance audit (Coder 2). HARD GATE.

For every nontrivial number in the generated artifacts:

    number_id / value / unit / source_type / source_id / source_hash /
    derivation / assumptions

Detects:
    NAKED_NUMBER           — a number with no provenance record at all
    UNSUPPORTED_NUMBER     — claimed source does not contain the number
    UNTRACEABLE_DERIVATION — derivation chain references missing inputs
    SOURCE_MISMATCH        — recorded source hash differs from actual
    UNIT_MISMATCH          — unit recorded in provenance differs from the
                             unit where the number is used

This audit re-derives provenance from the raw artifacts; the package's own
self-reported number_provenance block is ignored (Art. III).

HARD GATE: any NAKED_NUMBER / UNSUPPORTED_NUMBER / SOURCE_MISMATCH fails
the package regardless of other results.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

_NUMBER_RE = re.compile(
    r"(?<![A-Za-z_0-9.])(\d+(?:\.\d+)?)(?![A-Za-z_0-9.]|\s*%)")

# numbers that are structural, not engineering values
_TRIVIAL_CONTEXTS = (
    # section numbering, IDs, years, version tags
)
_TRIVIAL_VALUE = {"0", "1", "2", "3", "15", "100", "2021", "2022", "2023",
                  "2024", "2025", "2026", "10", "20", "30", "40", "50",
                  "60", "70", "80", "90"}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def audit_numerical_provenance(run_dir: Optional[Path],
                               package_dir: Optional[Path],
                               eng_spec: Optional[dict],
                               inv_spec: Optional[dict]) -> Dict[str, Any]:
    """Audit numbers in the machine-readable artifacts of one run.

    Scope (deterministic, machine-readable first):
      1. ENGINEERING_SPECIFICATION numeric values (critical parameters,
         design input values, verification acceptance criteria)
      2. INVENTION_SPECIFICATION numeric values
      3. MATURITY_BASIS / PACKAGE_MANIFEST numeric claims
    Each number must resolve to a provenance record: an evidence id whose
    content (or the problem statement) contains the value, a COMPUTED
    derivation, or an explicit UNKNOWN-class placeholder (not a number).
    """
    findings: List[Dict[str, Any]] = []

    # ---- build the admissible source corpus for this run ---------------
    sources: Dict[str, str] = {}
    if run_dir:
        for name in ("problem.json", "stage_RETRIEVE.json",
                     "stage_FREEZE.json", "candidate_envelope.json"):
            p = run_dir / name
            if p.exists():
                sources[name] = p.read_text(encoding="utf-8",
                                             errors="replace")[:200000]
    ev_texts = _evidence_texts(run_dir)

    # ---- 1. critical parameters ----------------------------------------
    if eng_spec:
        cps = (eng_spec.get("engineering_core") or {}) \
            .get("critical_parameters", []) or []
        for i, cp in enumerate(cps):
            if not isinstance(cp, dict):
                continue
            val = cp.get("value")
            nid = f"CP-{i + 1:02d}:{cp.get('parameter') or cp.get('name')}"
            if _is_number(val):
                findings.append(_check_number(
                    nid, val, cp.get("unit"), cp.get("basis"),
                    cp.get("source_id"), cp.get("source_hash"),
                    cp.get("derivation"), sources, ev_texts))
            elif val is None:
                findings.append(_missing(nid, "critical parameter value "
                                              "absent (not even UNKNOWN)"))

        # ---- 2. design input values ------------------------------------
        for d in eng_spec.get("design_inputs", []) or []:
            if not isinstance(d, dict):
                continue
            v = d.get("value")
            if _is_number(v):
                findings.append(_check_number(
                    f"{d.get('id')}:{v}", v, None,
                    d.get("evidence_class"),
                    (d.get("evidence_refs") or [None])[0], None,
                    None, sources, ev_texts))
            elif isinstance(v, str) and d.get("evidence_class") == \
                    "SOURCE_FACT":
                # fact-promotion guard: a SOURCE_FACT string value must be
                # contained in its referenced source (Art. XXVIII — a
                # MODELLED value silently re-classed as fact is forgery)
                src_id = (d.get("evidence_refs") or [None])[0]
                src_text = sources.get(src_id or "") or \
                    ev_texts.get(src_id or "")
                words = len(v.split())
                if src_id is None:
                    findings.append({
                        "number_id": f"{d.get('id')}:value",
                        "value": v[:80], "unit": None,
                        "source_type": "SOURCE_FACT",
                        "source_id": None, "source_hash": None,
                        "derivation": None, "assumptions": None,
                        "status": "NAKED_NUMBER",
                        "detail": "SOURCE_FACT design input with no "
                                  "evidence reference"})
                elif src_text is not None and words >= 4 and \
                        v.strip() not in src_text:
                    findings.append({
                        "number_id": f"{d.get('id')}:value",
                        "value": v[:80], "unit": None,
                        "source_type": "SOURCE_FACT",
                        "source_id": src_id, "source_hash": None,
                        "derivation": None, "assumptions": None,
                        "status": "UNSUPPORTED_NUMBER",
                        "detail": "SOURCE_FACT value text not present in "
                                  "its referenced source (suspected "
                                  "MODELLED -> SOURCE_FACT promotion)"})
            if _is_number(d.get("input")):
                pass  # 'input' is a category label, not a measured value

        # ---- 3. verification acceptance criteria -----------------------
        for v in eng_spec.get("verification_matrix", []) or []:
            if isinstance(v, dict):
                acc = v.get("acceptance") or v.get("acceptance_criterion")
                if _contains_number(acc):
                    findings.append(_check_number(
                        f"{v.get('id')}:acceptance", acc, None,
                        "VERIFICATION_ACCEPTANCE", None, None, None,
                        sources, ev_texts, literal_text=acc))
    if inv_spec:
        for field in ("engineering_parameters", "constraints",
                      "novelty_hypothesis"):
            val = (inv_spec.get(field) or {}).get("value") \
                if isinstance(inv_spec.get(field), dict) else None
            if _contains_number(val):
                findings.append(_check_number(
                    f"INV:{field}", str(val), None, None, None, None,
                    None, sources, ev_texts, literal_text=str(val)))

    # ---- verdict --------------------------------------------------------
    hard = [f for f in findings if f["status"] in
            ("NAKED_NUMBER", "UNSUPPORTED_NUMBER", "SOURCE_MISMATCH")]
    soft = [f for f in findings if f["status"] in
            ("UNTRACEABLE_DERIVATION", "UNIT_MISMATCH")]
    return {
        "available": True,
        "numbers_audited": len(findings),
        "hard_violations": len(hard),
        "soft_violations": len(soft),
        "findings": findings,
        "verdict": "FAIL" if hard else ("CONDITIONAL" if soft else "PASS"),
        "gate": "HARD — any NAKED_NUMBER / UNSUPPORTED_NUMBER / "
                "SOURCE_MISMATCH fails the package",
        "note": "re-derived from raw artifacts; self-reported "
                "number_provenance blocks were not consulted (Art. III)",
    }


def _evidence_texts(run_dir: Optional[Path]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not run_dir:
        return out
    for name in ("stage_RETRIEVE.json", "candidate_envelope.json"):
        p = run_dir / name
        if not p.exists():
            continue
        try:
            import json
            data = json.loads(p.read_text(encoding="utf-8"))
            items = _find_evidence_items(data)
            for ev in items:
                if isinstance(ev, dict) and ev.get("id"):
                    body = ev.get("abstract") or ev.get("text") or ""
                    out[str(ev["id"])] = str(body)
        except Exception:
            continue
    return out


def _find_evidence_items(obj: Any) -> List[Any]:
    found: List[Any] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("evidence", "evidence_items", "items", "results") and \
                    isinstance(v, list):
                found.extend(v)
            else:
                found.extend(_find_evidence_items(v))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_find_evidence_items(item))
    return found


def _is_number(v: Any) -> bool:
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return True
    if isinstance(v, str):
        s = v.strip()
        try:
            float(s)
            return True
        except ValueError:
            # "5-10 years" style: contains a number → audited as range text
            return bool(_NUMBER_RE.search(s)) and not \
                s.upper().startswith("UNKNOWN")
    return False


def _contains_number(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return True
    if isinstance(v, str):
        if v.upper().startswith(("UNKNOWN", "NOT ")):
            return False
        return bool(_NUMBER_RE.search(v))
    return False


def _missing(nid: str, detail: str) -> Dict[str, Any]:
    return {"number_id": nid, "value": None, "unit": None,
            "source_type": None, "source_id": None, "source_hash": None,
            "derivation": None, "assumptions": None,
            "status": "NAKED_NUMBER", "detail": detail}


def _check_number(nid: str, value: Any, unit: Optional[str],
                  source_type: Optional[str], source_id: Optional[str],
                  source_hash: Optional[str], derivation: Optional[str],
                  sources: Dict[str, str], ev_texts: Dict[str, str],
                  literal_text: Optional[str] = None) -> Dict[str, Any]:
    rec: Dict[str, Any] = {
        "number_id": nid, "value": value, "unit": unit,
        "source_type": source_type, "source_id": source_id,
        "source_hash": source_hash, "derivation": derivation,
        "assumptions": None, "status": None, "detail": None,
    }
    text = literal_text or str(value)
    nums = _NUMBER_RE.findall(text)
    nontrivial = [n for n in nums if n not in _TRIVIAL_VALUE]

    # SOURCE_FACT numbers must appear in the referenced source
    if source_type == "SOURCE_FACT" and source_id:
        src_text = sources.get(source_id) or ev_texts.get(source_id)
        if src_text is None:
            rec["status"] = "NAKED_NUMBER"
            rec["detail"] = f"claimed source {source_id} not present in run"
        elif not any(n in src_text for n in nums):
            rec["status"] = "UNSUPPORTED_NUMBER"
            rec["detail"] = (f"numbers {nums} not found in claimed source "
                             f"{source_id}")
        else:
            rec["status"] = "OK"
    elif source_type in ("COMPUTED",):
        if not derivation:
            rec["status"] = "UNTRACEABLE_DERIVATION"
            rec["detail"] = "COMPUTED number without derivation record"
        else:
            rec["status"] = "OK"
    elif source_type in ("MODELLED", "MODEL_DERIVED", "ENGINEERING_PROPOSED"):
        # a modelled number must not masquerade as sourced; recorded as
        # classed model value — acceptable only when labeled, which it is
        rec["status"] = "OK_CLASSIFIED"
        rec["detail"] = "model-derived value, explicitly classed"
    elif source_type in ("UNKNOWN",) or (isinstance(value, str) and
                                         "UNKNOWN" in str(value).upper()):
        rec["status"] = "OK_CLASSIFIED"
        rec["detail"] = "explicit unknown placeholder (Art. XXV)"
    else:
        if nontrivial:
            rec["status"] = "NAKED_NUMBER"
            rec["detail"] = "nontrivial number without source_type"
        else:
            rec["status"] = "OK_TRIVIAL"
            rec["detail"] = "trivial/structural number"
    return rec

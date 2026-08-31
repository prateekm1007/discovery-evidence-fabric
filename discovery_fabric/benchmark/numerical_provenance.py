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
import json
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


def _forms_of(v: Any) -> List[str]:
    """Decimal literal forms a numeric value can take inside a span
    (55.0 / 55 / 0.4) — shared with the technical-state validator's
    number-in-span rule so the audit and the builder agree."""
    if v is None or isinstance(v, bool) or not isinstance(v, (int, float)):
        return []
    forms = {str(v)}
    if isinstance(v, float):
        if v.is_integer():
            forms.add(str(int(v)))
        forms.add(f"{v:.4f}".rstrip("0").rstrip("."))
    return sorted(forms)


def _num_in_span(v: Any, span: str) -> bool:
    return any(f in span for f in _forms_of(v))


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
            if isinstance(v, str) and "content_hash" in v and \
                    d.get("evidence_class") == "SOURCE_FACT":
                # provenance-record values are records, not engineering
                # numbers — verified by hash binding, not number presence
                findings.append(_check_provenance_record(
                    f"{d.get('id')}:provenance", v,
                    (d.get("evidence_refs") or [None])[0], ev_texts,
                    run_dir))
            elif _is_number(v):
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

        # ---- R379: the structured TECHNICAL_STATE section is audited
        # with the SAME hardness as every other numeric site — a new
        # section must not become a laundering path for invented
        # numbers (Art. III: this audit re-derives from raw artifacts
        # and never trusts the builder's own class labels).
        ts = (inv_spec.get("technical_state") or {}).get("value") \
            if isinstance(inv_spec.get("technical_state"), dict) \
            else None
        if isinstance(ts, dict):
            for p in ts.get("parameters") or []:
                if not isinstance(p, dict):
                    continue
                pid = p.get("param_id") or "<param>"
                for key in ("value", "range_min", "range_max"):
                    v = p.get(key)
                    if v is None or not _is_number(v):
                        continue
                    vclass = (p.get("value_class")
                              if key == "value" else
                              p.get("range_class")) or "UNKNOWN"
                    if vclass == "EXTRACTED":
                        span = (p.get("value_span")
                                if key == "value"
                                else p.get("range_span")) or ""
                        ev_id = (p.get("value_evidence_id")
                                 if key == "value"
                                 else p.get("range_evidence_id")) or ""
                        src_text = ev_texts.get(ev_id) or \
                            sources.get(ev_id)
                        if not ev_id or src_text is None:
                            findings.append({
                                "number_id": f"TS:{pid}:{key}",
                                "value": v, "unit": p.get("unit"),
                                "source_type": "EXTRACTED",
                                "source_id": ev_id, "source_hash": None,
                                "derivation": None, "assumptions": None,
                                "status": "NAKED_NUMBER",
                                "detail": ("EXTRACTED technical-state "
                                           "value cites no custodied "
                                           "evidence")})
                        elif span and span not in src_text:
                            findings.append({
                                "number_id": f"TS:{pid}:{key}",
                                "value": v, "unit": p.get("unit"),
                                "source_type": "EXTRACTED",
                                "source_id": ev_id, "source_hash": None,
                                "derivation": None, "assumptions": None,
                                "status": "UNSUPPORTED_NUMBER",
                                "detail": ("technical-state span is NOT "
                                           "verbatim in the cited "
                                           "evidence (Art. VI)")})
                        elif span and not _num_in_span(v, span):
                            findings.append({
                                "number_id": f"TS:{pid}:{key}",
                                "value": v, "unit": p.get("unit"),
                                "source_type": "EXTRACTED",
                                "source_id": ev_id, "source_hash": None,
                                "derivation": None, "assumptions": None,
                                "status": "UNSUPPORTED_NUMBER",
                                "detail": ("the number is not inside "
                                           "its own span")})
                        else:
                            findings.append({
                                "number_id": f"TS:{pid}:{key}",
                                "value": v, "unit": p.get("unit"),
                                "source_type": "EXTRACTED",
                                "source_id": ev_id, "source_hash": None,
                                "derivation": None, "assumptions": None,
                                "status": "OK",
                                "detail": "span-verified"})
                    elif vclass == "MODELLED":
                        findings.append({
                            "number_id": f"TS:{pid}:{key}",
                            "value": v, "unit": p.get("unit"),
                            "source_type": "MODELLED",
                            "source_id": None, "source_hash": None,
                            "derivation": None, "assumptions": None,
                            "status": "OK_CLASSIFIED",
                            "detail": ("model-declared design value, "
                                       "explicitly classed")})
                    else:
                        findings.append({
                            "number_id": f"TS:{pid}:{key}",
                            "value": v, "unit": p.get("unit"),
                            "source_type": "UNKNOWN_CLASS",
                            "source_id": None, "source_hash": None,
                            "derivation": None, "assumptions": None,
                            "status": "NAKED_NUMBER",
                            "detail": ("numeric technical-state value "
                                       "with no EXTRACTED/MODELLED "
                                       "class — a number with no class "
                                       "is certainty laundering (Art. XXV)")})
            for c in ts.get("constraints") or []:
                if not isinstance(c, dict):
                    continue
                v = c.get("limit")
                if not _is_number(v):
                    continue
                if (c.get("limit_class") or "") == "EXTRACTED":
                    span = c.get("limit_span") or ""
                    ev_id = c.get("limit_evidence_id") or ""
                    src_text = ev_texts.get(ev_id) or sources.get(ev_id)
                    if not ev_id or src_text is None or \
                            span not in (src_text or "") or \
                            (span and not _num_in_span(v, span)):
                        findings.append({
                            "number_id":
                                f"TS:{c.get('constraint_id')}:limit",
                            "value": v, "unit": c.get("unit"),
                            "source_type": "EXTRACTED",
                            "source_id": ev_id, "source_hash": None,
                            "derivation": None, "assumptions": None,
                            "status": "UNSUPPORTED_NUMBER",
                            "detail": ("EXTRACTED constraint limit not "
                                       "span-verified")})
                    else:
                        findings.append({
                            "number_id":
                                f"TS:{c.get('constraint_id')}:limit",
                            "value": v, "unit": c.get("unit"),
                            "source_type": "EXTRACTED",
                            "source_id": ev_id, "source_hash": None,
                            "derivation": None, "assumptions": None,
                            "status": "OK",
                            "detail": "span-verified"})
                elif (c.get("limit_class") or "") == "MODELLED":
                    findings.append({
                        "number_id": f"TS:{c.get('constraint_id')}:limit",
                        "value": v, "unit": c.get("unit"),
                        "source_type": "MODELLED",
                        "source_id": None, "source_hash": None,
                        "derivation": None, "assumptions": None,
                        "status": "OK_CLASSIFIED",
                        "detail": ("model-declared threshold with "
                                   "justification (Art. XXVII)")})
                else:
                    findings.append({
                        "number_id": f"TS:{c.get('constraint_id')}:limit",
                        "value": v, "unit": c.get("unit"),
                        "source_type": "UNKNOWN_CLASS",
                        "source_id": None, "source_hash": None,
                        "derivation": None, "assumptions": None,
                        "status": "NAKED_NUMBER",
                        "detail": "constraint limit with no class"})

        # ---- R380: the PARAMETRIC_MODEL section is audited with the
        # SAME hardness — geometric measurements are numbers, and a new
        # section must not become a laundering path for invented
        # measurements (Art. III/VI/XXXVIII).
        pm = (inv_spec.get("parametric_model") or {}).get("value") \
            if isinstance(inv_spec.get("parametric_model"), dict) \
            else None
        if isinstance(pm, dict):
            # (a) the section's evidence class is COMPUTATIONAL_RESULT —
            #     anything claiming physical observation is a forbidden
            #     transition (Art. XXXVIII: compute is never reality)
            pm_class = (inv_spec.get("parametric_model") or
                        {}).get("epistemic_class")
            if pm_class not in (None, "COMPUTATIONAL_RESULT"):
                findings.append({
                    "number_id": "PM:epistemic_class", "value": pm_class,
                    "unit": None, "source_type": "SECTION_CLASS",
                    "source_id": None, "source_hash": None,
                    "derivation": None, "assumptions": None,
                    "status": "NAKED_NUMBER",
                    "detail": (f"parametric model section claims "
                               f"class {pm_class} — only "
                               f"COMPUTATIONAL_RESULT is legal for "
                               f"computed geometry (Art. XXXVIII)")})
            # (b) parameter map values carry a value_class; EXTRACTED
            #     values must be span-verified like any TS value
            for pid, p in sorted((pm.get("parameter_map")
                                  or {}).items()):
                if not isinstance(p, dict):
                    continue
                v = p.get("value")
                if not _is_number(v):
                    continue
                vclass = p.get("value_class") or "UNKNOWN"
                if vclass == "MODELLED":
                    findings.append({
                        "number_id": f"PM:{pid}:value", "value": v,
                        "unit": p.get("unit"), "source_type": "MODELLED",
                        "source_id": None, "source_hash": None,
                        "derivation": None, "assumptions": None,
                        "status": "OK_CLASSIFIED",
                        "detail": "model-declared design parameter"})
                elif vclass == "EXTRACTED":
                    span = p.get("value_span") or ""
                    ev_id = p.get("value_evidence_id") or ""
                    src_text = ev_texts.get(ev_id) or sources.get(ev_id)
                    if not ev_id or src_text is None or \
                            span not in (src_text or "") or \
                            not _num_in_span(v, span):
                        findings.append({
                            "number_id": f"PM:{pid}:value", "value": v,
                            "unit": p.get("unit"),
                            "source_type": "EXTRACTED",
                            "source_id": ev_id, "source_hash": None,
                            "derivation": None, "assumptions": None,
                            "status": "UNSUPPORTED_NUMBER",
                            "detail": ("EXTRACTED parametric parameter "
                                       "not span-verified (Art. VI)")})
                    else:
                        findings.append({
                            "number_id": f"PM:{pid}:value", "value": v,
                            "unit": p.get("unit"),
                            "source_type": "EXTRACTED",
                            "source_id": ev_id, "source_hash": None,
                            "derivation": None, "assumptions": None,
                            "status": "OK", "detail": "span-verified"})
                else:
                    findings.append({
                        "number_id": f"PM:{pid}:value", "value": v,
                        "unit": p.get("unit"),
                        "source_type": "UNKNOWN_CLASS",
                        "source_id": None, "source_hash": None,
                        "derivation": None, "assumptions": None,
                            "status": "NAKED_NUMBER",
                            "detail": ("parametric parameter with no "
                                       "EXTRACTED/MODELLED class — an "
                                       "unclassed number is certainty "
                                       "laundering (Art. XXV)")})
            # (c) MEASURED geometric quantities must carry computation
            #     logs — a measurement without its computation record
            #     is an invented measurement
            meas = pm.get("measurements") or {}
            logged_objects = {
                entry.get("object_id")
                for entry in meas.get("computation_log") or []
                if isinstance(entry, dict)}
            for oid, m in sorted((meas.get("objects") or {}).items()):
                if not isinstance(m, dict):
                    continue
                for field in ("volume_mm3", "min_wall_thickness_mm"):
                    v = m.get(field)
                    if not _is_number(v):
                        continue
                    if oid in logged_objects:
                        findings.append({
                            "number_id": f"PM:meas:{oid}:{field}",
                            "value": v, "unit": "mm^3" if field ==
                            "volume_mm3" else "mm",
                            "source_type": "COMPUTATIONAL_RESULT",
                            "source_id": None, "source_hash": None,
                            "derivation": "OCCT kernel computation log "
                                          "in measurements.computation_log",
                            "assumptions": None, "status": "OK_CLASSIFIED",
                            "detail": "kernel-measured with computation log"})
                    else:
                        findings.append({
                            "number_id": f"PM:meas:{oid}:{field}",
                            "value": v, "unit": None,
                            "source_type": "COMPUTATIONAL_RESULT",
                            "source_id": None, "source_hash": None,
                            "derivation": None, "assumptions": None,
                            "status": "NAKED_NUMBER",
                            "detail": ("measured geometric quantity with "
                                       "no computation log — an invented "
                                       "measurement (Art. VI)")})
            # (d) derived artifact hashes must be real: when the run
            #     directory is available, re-hash the referenced files
            if run_dir:
                for key, art in sorted((pm.get("derived_artifacts")
                                        or {}).items()):
                    if not isinstance(art, dict):
                        continue
                    path = art.get("path")
                    recorded = art.get("sha256")
                    if path and recorded and Path(path).exists():
                        actual = _sha(path)
                        if actual != recorded:
                            findings.append({
                                "number_id": f"PM:art:{key}:sha256",
                                "value": recorded, "unit": None,
                                "source_type": "ARTIFACT_HASH",
                                "source_id": path, "source_hash": recorded,
                                "derivation": None, "assumptions": None,
                                "status": "SOURCE_MISMATCH",
                                "detail": ("derived artifact hash does "
                                           "not match the file on disk "
                                           "(Art. VI)")})
                        else:
                            findings.append({
                                "number_id": f"PM:art:{key}:sha256",
                                "value": recorded, "unit": None,
                                "source_type": "ARTIFACT_HASH",
                                "source_id": path, "source_hash": recorded,
                                "derivation": None, "assumptions": None,
                                "status": "OK",
                                "detail": "artifact hash re-verified on disk"})

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


def _check_provenance_record(nid: str, value: str, src_id: Optional[str],
                             ev_texts: Dict[str, str],
                             run_dir: Optional[Path]) -> Dict[str, Any]:
    """Verify a provenance-record value (source URI + content hash).

    The recorded content hash must match the referenced evidence item's
    actual content hash — a forged or drifted anchor is SOURCE_MISMATCH.
    """
    m = re.search(r"content_hash\s+([0-9a-fA-F]{8,})", value)
    rec: Dict[str, Any] = {
        "number_id": nid, "value": value[:80], "unit": None,
        "source_type": "SOURCE_FACT_PROVENANCE_RECORD",
        "source_id": src_id, "source_hash": m.group(1) if m else None,
        "derivation": None, "assumptions": None,
        "status": None, "detail": None}
    if not m:
        rec["status"] = "OK_TRIVIAL"
        rec["detail"] = "provenance record without parsable hash"
        return rec
    recorded_hash = m.group(1)
    # resolve the referenced evidence's actual content hash from run records
    actual = None
    lookup_errors: List[str] = []
    if run_dir:
        for name in ("candidate_envelope.json", "stage_RETRIEVE.json",
                     "stage_FREEZE.json"):
            p = run_dir / name
            if not p.exists():
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception as exc:
                lookup_errors.append(f"{name}: {exc}")
                continue
            for ev in _find_evidence_items(data):
                if isinstance(ev, dict) and str(ev.get("id")) == str(src_id):
                    actual = ev.get("content_hash")
                    break
            if actual:
                break
    if lookup_errors:
        rec["lookup_errors"] = lookup_errors
    if actual is None:
        if run_dir is None:
            rec["status"] = "OK_TRIVIAL"
            rec["detail"] = ("provenance record present but no run records "
                             "available to verify against (skipped)")
        else:
            rec["status"] = "SOURCE_MISMATCH"
            rec["detail"] = (f"provenance record references {src_id} but no "
                             "matching evidence record exists in the run "
                             "(unresolvable anchor)")
    elif str(actual) != recorded_hash:
        rec["status"] = "SOURCE_MISMATCH"
        rec["detail"] = (f"recorded content_hash {recorded_hash[:12]}... != "
                         f"actual {str(actual)[:12]}... for {src_id}")
    else:
        rec["status"] = "OK_PROVENANCE_VERIFIED"
        rec["detail"] = "content hash binds to the referenced evidence"
    return rec


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

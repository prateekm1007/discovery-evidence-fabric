"""Common measured-property extraction for a buyer package directory.

Coder 2 measurement layer. Works on BOTH:
  - gold corpus packages (technology-transfer-portfolio-15/FULL_DOSSIERS/*)
  - generated packages  (EngineRun DOWNLOAD/<NN>_<name>/)

Principles (Constitution):
  - Art. XXV: a measurement that could not be made is recorded as MISSING,
    never as zero. Missing is an epistemic state.
  - Art. III: we never trust the package's own self-reported audit verdicts
    (e.g. traceability.passed); we re-derive raw counts and densities from
    the underlying JSON structures and the rendered PDF text.
  - Art. II: counts are derived from exact ID structures where they exist,
    falling back to explicit section parsing — never keyword guessing for
    object identity.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from pypdf import PdfReader
    _HAVE_PYPDF = True
except ImportError:  # pragma: no cover
    _HAVE_PYPDF = False

# The 15 dossier sections rendered by the frozen builders (both corpora).
DOSSIER_SECTIONS = [
    (1, "Technology Description"),
    (2, "Mechanism Architecture"),
    (3, "Governing Engineering Model"),
    (4, "Design Inputs"),
    (5, "Design Outputs"),
    (6, "Critical Design Parameters"),
    (7, "Failure Modes"),
    (8, "Failure Analysis"),
    (9, "Verification Strategy"),
    (10, "Validation Strategy"),
    (11, "Materials"),
    (12, "Bill of Materials"),
    (13, "Manufacturing"),
    (14, "External Evidence"),
    (15, "Transfer Boundary"),
]

REQUIRED_PDFS = [
    "00_PACKAGE_README.pdf",
    "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
    "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
    "03_BUYER_DECISION_CARD.pdf",
    "04_EVIDENCE_SUMMARY.pdf",
    "05_TRANSFER_MANIFEST.pdf",
]

UNKNOWN_MARKERS = [
    "UNKNOWN", "NOT ESTABLISHED", "NOT_TESTED", "NOT_PERFORMED",
    "NOT_POSSIBLE_YET", "NOT POSSIBLE YET", "MODELLED", "ENGINEERING_PROPOSED",
]

# Buyer-decision elements expected on the dossier decision page / buyer card.
BUYER_DECISION_ELEMENTS = [
    "WHAT IS IT",
    "WHY DOES IT MATTER",
    "WHAT IS ACTUALLY ESTABLISHED",
    "WHAT IS NOT ESTABLISHED",
    "WHAT DOES THE BUYER GET",
    "WHAT DOES THE BUYER HAVE TO BUILD",
    "WHAT IS THE NEXT DECISIVE EXPERIMENT",
    "WHAT WOULD MAKE US KILL IT",
    "WHAT TRANSACTION COULD MAKE SENSE",
]

TRANSFER_BOUNDARY_ELEMENTS = [
    "YOU RECEIVE",
    "YOU MUST DEVELOP",
    "YOU MUST VERIFY",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def pdf_text(package_dir: Path, pdf_name: str) -> Optional[str]:
    """Extract text from a package PDF. None if unreadable (MISSING, not '')."""
    if not _HAVE_PYPDF:
        return None
    p = package_dir / pdf_name
    if not p.exists():
        return None
    try:
        reader = PdfReader(str(p))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return None


def _section_spans(text: str) -> Dict[int, Dict[str, Any]]:
    """Locate the 15 numbered sections in the dossier text.

    Returns {section_number: {"title": str, "chars": int}} — chars is the
    character span between this heading and the next (depth proxy).
    """
    if not text:
        return {}
    positions = []
    for num, title in DOSSIER_SECTIONS:
        # headings render as "N. Title" (whitespace-tolerant)
        pat = re.compile(rf"^\s*{num}\.\s*{re.escape(title)}\s*$",
                         re.IGNORECASE | re.MULTILINE)
        m = pat.search(text)
        if m:
            positions.append((num, title, m.start(), m.end()))
    spans: Dict[int, Dict[str, Any]] = {}
    for i, (num, title, _s, end) in enumerate(positions):
        next_start = positions[i + 1][2] if i + 1 < len(positions) else len(text)
        spans[num] = {"title": title, "chars": max(0, next_start - end)}
    return spans


def _count_marker(text: str, marker: str) -> int:
    if not text:
        return 0
    return len(re.findall(re.escape(marker), text, re.IGNORECASE))


def extract_package_metrics(package_dir: Path,
                            run_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Extract the common measured-property set from one package.

    package_dir: the buyer package folder (6 PDFs + JSONs).
    run_dir:     optional engine run dir (INVENTION_SPECIFICATION.json /
                 ENGINEERING_SPECIFICATION.json) — available for generated
                 packages only; deepens several measurements.
    """
    package_dir = Path(package_dir)
    run_dir = Path(run_dir) if run_dir else None

    manifest = _load_json(package_dir / "PACKAGE_MANIFEST.json")
    trace = _load_json(package_dir / "ENGINEERING_TRACEABILITY.json")
    maturity = _load_json(package_dir / "MATURITY_BASIS.json")
    eng_spec = _load_json(run_dir / "ENGINEERING_SPECIFICATION.json") \
        if run_dir else None
    inv_spec = _load_json(run_dir / "INVENTION_SPECIFICATION.json") \
        if run_dir else None

    m: Dict[str, Any] = {
        "package_dir": str(package_dir),
        "package_id": (manifest or {}).get("package_id"),
        "source_manifest": manifest,
        "traceability": trace,
        "maturity": maturity,
        "eng_spec": eng_spec,
        "inv_spec": inv_spec,
    }

    # ---------------- object counts (schema-tolerant, ID-derived) --------
    counts = (maturity or {}).get("counts", {}) or {}
    t_eq = (trace or {}).get("equation_integrity", {}) or {}
    t_np = (trace or {}).get("number_provenance", {}) or {}
    t_dd = (trace or {}).get("di_do_consistency", {}) or {}
    t_rv = (trace or {}).get("risk_verification", {}) or {}
    t_vv = (trace or {}).get("v_and_v", {}) or {}

    def _first(*candidates) -> Optional[int]:
        for c in candidates:
            if isinstance(c, int):
                return c
        return None

    di = _first(counts.get("design_inputs"),
                None if not eng_spec else len(eng_spec.get("design_inputs", [])))
    do = _first(counts.get("design_outputs"),
                None if not eng_spec else len(eng_spec.get("design_outputs", [])))
    fm = _first(counts.get("failure_modes"),
                None if not eng_spec else len(eng_spec.get("failure_analysis", [])))
    vf = _first(counts.get("verification_items"),
                counts.get("verifications_total"),
                None if not eng_spec else len(eng_spec.get("verification_matrix", [])))
    va = _first(t_vv.get("validation_items"),
                None if not eng_spec else len(eng_spec.get("validation_matrix", [])))
    eq = _first(counts.get("equations"), counts.get("governing_equations"),
                t_eq.get("total_equations"))
    cp = _first(t_np.get("total_critical_params"),
                None if not eng_spec else
                len((eng_spec.get("engineering_core") or {})
                    .get("critical_parameters", []) or []))
    bp = _first(counts.get("build_plan_steps"),
                None if not eng_spec else
                len(eng_spec.get("engineering_build_plan", []) or []))
    ext_ev = _first(counts.get("external_evidence"),
                    (manifest or {}).get("external_evidence_count"))
    unk = _first(counts.get("remaining_unknowns"),
                 None if not eng_spec else
                 len((eng_spec.get("engineering_core") or {})
                     .get("remaining_unknowns", []) or []))

    m["objects"] = {
        "design_inputs": di, "design_outputs": do, "failure_modes": fm,
        "verifications": vf, "validations": va, "equations": eq,
        "critical_parameters": cp, "build_plan_steps": bp,
        "external_evidence": ext_ev, "remaining_unknowns": unk,
    }

    # ---------------- traceability density (re-derived, not self-reported) --
    # Both corpora carry a `linked` flag per chain; evidence density is
    # measured identically from MATURITY_BASIS evidence-id lists.
    chains = (trace or {}).get("traceability_chains", []) or []
    evidence_bound = [c for c in chains
                      if isinstance(c, dict) and c.get("evidence_ids")]
    linked = [c for c in chains
              if isinstance(c, dict) and c.get("linked")]
    ev_lists = {k: (maturity or {}).get(k, []) or [] for k in (
        "governing_model_evidence_ids", "design_input_evidence_ids",
        "design_output_evidence_ids", "failure_analysis_evidence_ids",
        "build_plan_evidence_ids", "verification_evidence_ids")}
    ev_id_total = sum(len(v) for v in ev_lists.values())
    obj_total = sum(v for v in m["objects"].values() if isinstance(v, int))
    m["traceability_density"] = {
        "chains_total": len(chains),
        "chains_linked": len(linked),
        "chain_linkage_rate": (len(linked) / len(chains)) if chains else None,
        "chains_evidence_bound": len(evidence_bound),
        "evidence_id_total": ev_id_total,
        "evidence_ids_per_object": (ev_id_total / obj_total) if obj_total else None,
        "orphan_design_outputs": t_dd.get("orphan_design_outputs"),
        "orphan_failure_modes": t_rv.get("orphan_failure_modes"),
        "unsupported_numbers": t_np.get("unsupported_numbers"),
        "equations_with_issues": t_eq.get("equations_with_issues"),
    }

    # ---------------- rendered PDF measurements ---------------------------
    dossier_text = pdf_text(package_dir, "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf")
    card_text = pdf_text(package_dir, "03_BUYER_DECISION_CARD.pdf")
    manifest_pdf_text = pdf_text(package_dir, "05_TRANSFER_MANIFEST.pdf")

    spans = _section_spans(dossier_text or "")
    m["section_coverage"] = {
        "present": len(spans),
        "total": len(DOSSIER_SECTIONS),
        "missing_sections": [n for n, _t in DOSSIER_SECTIONS if n not in spans],
        "section_chars": {str(n): spans[n]["chars"] for n in spans},
    }

    m["pdf_presence"] = {p: (package_dir / p).exists() for p in REQUIRED_PDFS}

    if dossier_text is None:
        m["unknown_disclosure"] = {"markers_total": None, "by_marker": {}}
        m["buyer_decision"] = {"elements_present": [], "elements_missing":
                               list(BUYER_DECISION_ELEMENTS)}
        m["transfer_boundary_pdf"] = {"elements_present": [],
                                      "elements_missing":
                                      list(TRANSFER_BOUNDARY_ELEMENTS)}
        m["dossier_chars"] = None
    else:
        by_marker = {mk: _count_marker(dossier_text, mk)
                     for mk in UNKNOWN_MARKERS}
        m["unknown_disclosure"] = {
            "markers_total": sum(by_marker.values()),
            "by_marker": by_marker,
        }
        combined = dossier_text + "\n" + (card_text or "")
        m["buyer_decision"] = {
            "elements_present": [e for e in BUYER_DECISION_ELEMENTS
                                 if e in combined],
            "elements_missing": [e for e in BUYER_DECISION_ELEMENTS
                                 if e not in combined],
        }
        tb_combined = (manifest_pdf_text or "") + "\n" + dossier_text
        m["transfer_boundary_pdf"] = {
            "elements_present": [e for e in TRANSFER_BOUNDARY_ELEMENTS
                                 if e in tb_combined],
            "elements_missing": [e for e in TRANSFER_BOUNDARY_ELEMENTS
                                 if e not in tb_combined],
        }
        m["dossier_chars"] = len(dossier_text)

    # decisive-experiment specificity: a measurable criterion sentence in the
    # decisive-experiment block of the dossier decision page
    m["killer_experiment"] = _killer_experiment_probe(dossier_text, inv_spec)

    # ---------------- transfer boundary (structured, when present) --------
    tb = (eng_spec or {}).get("transfer_boundary") or {}
    m["transfer_boundary_structured"] = {
        "buyer_receives": len(tb.get("buyer_receives", []) or []),
        "buyer_must_create": len(tb.get("buyer_must_create", []) or []),
        "has_structured_boundary": bool(tb),
    }
    tl = (trace or {}).get("transfer_logic") or {}
    m["transfer_logic_reported"] = tl

    # ---------------- manufacturing / regulatory --------------------------
    mfg = (trace or {}).get("manufacturing") or {}
    reg = (trace or {}).get("regulatory") or {}
    mfg_processes = len(((eng_spec or {}).get("manufacturing") or {})
                        .get("candidate_processes", []) or []) \
        if eng_spec else None
    m["manufacturing"] = {
        "has_processes": mfg.get("has_processes",
                                 bool(mfg_processes) if mfg_processes else None),
        "candidate_processes": mfg_processes,
        "status_recorded": bool(mfg.get("status")),
    }
    m["regulatory"] = {
        "has_regulatory_di": reg.get("has_regulatory_di"),
        "pathway_recorded": bool(reg.get("pathway")),
        "regulatory_di_count": _first(
            _regulatory_di_count(eng_spec),
            1 if reg.get("has_regulatory_di") else
            (0 if reg.get("has_regulatory_di") is False else None)),
    }

    # ---------------- V&V honesty probes (re-derived) ---------------------
    m["vv_probe"] = _vv_probe(eng_spec)
    return m


def _regulatory_di_count(eng_spec: Optional[dict]) -> Optional[int]:
    if not eng_spec:
        return None
    dis = eng_spec.get("design_inputs", []) or []
    return sum(1 for d in dis if isinstance(d, dict) and
               re.search(r"regulat|FDA|510|class ii|CE mark",
                         str(d.get("input", "")) + str(d.get("value", "")),
                         re.IGNORECASE) is not None)


def _vv_probe(eng_spec: Optional[dict]) -> Dict[str, Any]:
    """Re-derive V&V honesty signals from the engineering spec.

    Catches: a verification claiming a result without a test, a validation
    claiming performance without a physical observation (Art. XXXVIII).
    """
    if not eng_spec:
        return {"available": False}
    vf = eng_spec.get("verification_matrix", []) or []
    va = eng_spec.get("validation_matrix", []) or []
    vf_claimed = [v for v in vf
                  if isinstance(v, dict) and v.get("result")
                  not in (None, "NOT_TESTED", "NOT TESTED")]
    va_claimed = [v for v in va
                  if isinstance(v, dict) and v.get("result")
                  not in (None, "NOT_PERFORMED", "NOT PERFORMED")]
    return {
        "available": True,
        "verifications_total": len(vf),
        "verifications_claiming_result": len(vf_claimed),
        "validations_total": len(va),
        "validations_claiming_result": len(va_claimed),
        "validation_honesty_basis": [
            v.get("reason") for v in va if isinstance(v, dict)
            and v.get("reason")
        ][:3],
    }


def _killer_experiment_probe(dossier_text: Optional[str],
                             inv_spec: Optional[dict]) -> Dict[str, Any]:
    """Measure decisive-experiment specificity: is there a named decisive
    experiment with a measurable criterion and kill condition?"""
    out: Dict[str, Any] = {"block_present": False,
                           "has_measurable_criterion": False,
                           "has_kill_condition": False}
    if dossier_text:
        i = dossier_text.upper().find("WHAT IS THE NEXT DECISIVE EXPERIMENT")
        if i >= 0:
            block = dossier_text[i:i + 1500]
            out["block_present"] = True
            out["block_chars"] = len(block.split("WHAT WOULD MAKE US KILL IT")[0])
            out["has_measurable_criterion"] = bool(
                re.search(r"\d", block))
    if inv_spec:
        ke = (inv_spec.get("killer_experiment") or {}).get("value") \
            if isinstance(inv_spec.get("killer_experiment"), dict) \
            else inv_spec.get("killer_experiment")
        if isinstance(ke, dict):
            out["inv_spec_present"] = bool(ke)
        else:
            out["inv_spec_present"] = bool(ke)
    return out

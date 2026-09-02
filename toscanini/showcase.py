"""Portfolio showcase — the investor-demo surface (R389 Phases 4/5/8).

Serves the REAL portfolio packages through the same product API the UI
uses for fresh runs. The buyer-distribution repository is the authority
(Art. XXXIX): files are served from the portfolio tree, never re-rendered
or edited. The interactive evaluator rebuilds REAL geometry through the
canonical cad_pipeline (deterministic sandbox, full mutation provenance,
independent re-measure) — the CEO's Phase 5 loop:

    USER CHANGES PARAMETER (inside its declared envelope)
    -> parametric build program re-executes in the sandbox
    -> new geometry, re-measured deterministically
    -> viewer + measurements update
    -> everything labeled COMPUTATIONAL_RESULT / MODELLED

Honesty rules (constitution):
- Art. XXVII: parameter values keep their declared value_class; the
  rebuild is a MODELLED preview, never an evidence claim.
- Art. XXXVIII: geometry output is COMPUTATIONAL_RESULT; nothing here
  can produce PHYSICAL_VALIDATION.
- Art. IX: canonical portfolio bytes are READ-ONLY here; previews are
  written to a separate TOSCANINI_UI/previews scratch area.
- Art. VI: every preview records its real model_id, mutation provenance
  and artifact hashes from the real build.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from toscanini.sessions import _read_json  # noqa: E402  (same store util)

PORTFOLIO_ROOT = REPO_ROOT.parent / "portfolio"
DOWNLOAD_ROOT = PORTFOLIO_ROOT / "DOWNLOAD"
PREVIEW_ROOT = REPO_ROOT / "TOSCANINI_UI" / "previews"

# The three CEO-picked investor demos (R389 Phase 8) + every other slot
# with a real 3D model, all served from the same code path.
DEMO_FOCUS = ("04", "08", "09")

SLOT_TITLES = {
    "01": ("Multisegment flow control", "A multi-segment catheter that "
            "resists total occlusion of any single segment"),
    "02": ("Adaptive valve", "Pressure-adaptive valve maintaining flow "
            "within a physiologic envelope"),
    "03": ("Catalytic clearance", "Surface catalysis clears accumulated "
            "protein deposits at the interface"),
    "04": ("Drainage floor protection", "A parallel low-conductance "
            "floor lumen keeps minimum drainage when the primary path "
            "obstructs — the CEO investor demo #1"),
    "05": ("Phage antibiofilm", " bacteriophage-coated surface prevents "
            "bacterial biofilm establishment"),
    "07": ("Self-powered sensing", "Energy-harvesting sensor without a "
            "battery or lead"),
    "08": ("NIR photovoltaic conversion", "Near-infrared photovoltaic "
            "layer converts wasted deep-tissue light — CEO investor "
            "demo #2"),
    "09": ("UWB localization", "Ultra-wideband pulse positioning of "
            "instruments without line-of-sight — CEO investor demo #3 "
            "(non-medical domain)"),
    "10": ("Catheter navigation", "Shape-memory steering of catheter "
            "tips under magnetic guidance"),
    "11": ("Gravity damper", "Passive gravity-compensating damper "
            "counteracts motion artifacts"),
    "12": ("Osmotic valve", "Osmotically driven valve actuation with no "
            "electronics"),
    "13": ("Pressure sensor", "Intracranial pressure sensing through a "
            "hermetic transducer"),
    "14": ("Acoustic detection", "Acoustic signature detection of "
            "impending mechanical failure"),
    "15": ("MR flow sensor", "MRI-compatible flow measurement without "
            "ferromagnetic materials"),
}


def _slot_dir(slot: str) -> Optional[Path]:
    for d in DOWNLOAD_ROOT.glob(f"{slot}_*"):
        if d.is_dir():
            return d
    return None


def _slots_with_models() -> List[str]:
    out = []
    for d in sorted(DOWNLOAD_ROOT.iterdir()) if DOWNLOAD_ROOT.exists() \
            else []:
        if d.is_dir() and (d / "MODEL").exists() \
                and list((d / "MODEL").glob("*.glb")):
            out.append(d.name[:2])
    return out


def list_showcase() -> List[Dict[str, Any]]:
    out = []
    for slot in _slots_with_models():
        d = _slot_dir(slot)
        if not d:
            continue
        model = d / "MODEL"
        params = (_read_json(model / "PARAMETERS.json") or {})
        plist = params.get("parameters") or []
        pkg = (_read_json(model / "MODEL_MANIFEST.json") or {}) \
            .get("package_id") or (d.name)
        title, blurb = SLOT_TITLES.get(slot, (d.name.replace("_", " "), ""))
        out.append({
            "slot": slot,
            "package_id": pkg,
            "title": title,
            "blurb": blurb,
            "domain": ("non-medical" if slot == "09" else "medical"),
            "demo_focus": slot in DEMO_FOCUS,
            "parameter_count": len(plist),
            "glb": f"/api/showcase/{slot}/model",
        })
    return out


def showcase_detail(slot: str) -> Optional[Dict[str, Any]]:
    d = _slot_dir(slot)
    if not d or not (d / "MODEL").exists():
        return None
    model = d / "MODEL"
    params = (_read_json(model / "PARAMETERS.json") or {})
    eq_reg = _read_json(d / "EQUATION_REGISTRY.json") or {}
    key_dims = _read_json(model / "KEY_DIMENSIONS.json") or {}
    manifest = _read_json(model / "MODEL_MANIFEST.json") or {}
    loop_state = _read_json(d / "LOOP_STATE.json") or {}
    status_3d = _read_json(model / "3D_DESIGN_STATUS.json") or {}
    glbs = sorted(model.glob("*.glb"))
    title, blurb = SLOT_TITLES.get(slot, (d.name.replace("_", " "), ""))
    zip_path = None
    zips = list(DOWNLOAD_ROOT.glob(f"{d.name}.zip"))
    if zips:
        zip_path = str(zips[0])
    return {
        "kind": "SHOWCASE",
        "slot": slot,
        "package_id": manifest.get("package_id") or d.name,
        "title": title,
        "blurb": blurb,
        "demo_focus": slot in DEMO_FOCUS,
        "created_from": "portfolio buyer-distribution repository "
                        "(Art. XXXIX authority)",
        "mechanism_summary": eq_reg.get("model_summary"),
        "equations": [
            {"id": e.get("equation_id"),
             "expression": e.get("math_expression"),
             "caption": e.get("caption")}
            for e in (eq_reg.get("equations") or [])[:6]],
        "parameters": [
            {"param_id": p.get("param_id"),
             "value": p.get("value"),
             "unit": p.get("unit"),
             "envelope": p.get("envelope"),
             "value_class": p.get("value_class"),
             "category": p.get("category"),
             "design_basis": p.get("design_basis")}
            for p in (params.get("parameters") or [])],
        "key_dimensions": key_dims.get("objects") or {},
        "model_manifest": {
            "model_id": manifest.get("model_id"),
            "program_sha256": manifest.get("program_source_sha256"),
        },
        "loop_verification_state": loop_state.get("loop_verification_state"),
        "design_status_3d": status_3d.get("status") or status_3d,
        "model": {
            "glb": f"/api/showcase/{slot}/model",
            "glb_path": str(glbs[0]) if glbs else None,
            "step": sorted(model.glob("*.step")),
            "stl": sorted(model.glob("*.stl")),
            "svg_views": sorted(model.glob("*.svg")),
        },
        "dossier": {
            "pdfs": [p.name for p in sorted(d.glob("*.pdf"))],
            "download": f"/api/showcase/{slot}/package",
            "download_path": zip_path,
        },
        "provenance_note":
            "All geometry is COMPUTATIONAL_RESULT with computation logs; "
            "no file claims a physical observation (Art. XXXVIII). "
            "Parameter values are ENGINE-DECLARED MODELLED design "
            "proposals inside declared envelopes (Art. XXVII).",
    }


def glb_path(slot: str) -> Optional[Path]:
    d = _slot_dir(slot)
    if not d:
        return None
    glbs = sorted((d / "MODEL").glob("*.glb"))
    return glbs[0] if glbs else None


def package_zip(slot: str) -> Optional[Path]:
    d = _slot_dir(slot)
    if not d:
        return None
    zips = list(DOWNLOAD_ROOT.glob(f"{d.name}.zip"))
    return zips[0] if zips else None


# ---------------------------------------------------------------------------
# The interactive evaluator — REAL geometry rebuild (CEO Phase 5)
# ---------------------------------------------------------------------------

def evaluate_parameter(slot: str, param_id: str, new_value: float,
                       reason: str = "interactive product preview"
                       ) -> Tuple[Optional[Dict[str, Any]],
                                  Dict[str, Any]]:
    """USER CHANGES PARAMETER -> CAD model changes -> measurements update.

    Only parameters bound to the package's own parametric model are
    mutable, only inside their DECLARED envelope (out-of-envelope or
    unbound -> explicit refusal, never a silent substitution).

    The rebuild runs the package's own PARAMETRIC_MODEL_SOURCE.py in the
    engine's deterministic sandbox via cad_pipeline.rebuild_with_mutation
    — full mutation provenance, real model_id, real artifact hashes.
    Output is a MODELLED preview (COMPUTATIONAL_RESULT); the canonical
    portfolio files are untouched (Art. IX).
    """
    d = _slot_dir(slot)
    if not d:
        return None, {"status": "NOT_FOUND", "reason": f"slot {slot}"}
    model_dir = d / "MODEL"
    params = (_read_json(model_dir / "PARAMETERS.json") or {})
    plist = params.get("parameters") or []
    src_path = model_dir / "PARAMETRIC_MODEL_SOURCE.py"
    if not src_path.exists():
        return None, {"status": "NO_PARAMETRIC_SOURCE",
                      "reason": "package carries no build program"}
    source = src_path.read_text()

    pmap: Dict[str, Dict[str, Any]] = {}
    target = None
    for p in plist:
        pid = p.get("param_id")
        if not pid:
            continue
        env = p.get("envelope") or [None, None]
        pmap[pid] = {
            "value": p.get("value"),
            "value_class": p.get("value_class"),
            "unit": p.get("unit"),
            "range_min": env[0] if len(env) > 0 else None,
            "range_max": env[1] if len(env) > 1 else None,
        }
        if pid == param_id:
            target = pmap[pid]

    if target is None:
        return None, {
            "status": "UNBOUND_PARAMETER",
            "reason": (f"parameter {param_id!r} is not bound to the "
                       "parametric model — nothing was rebuilt (Art. VI: "
                       "no silent substitution)")}
    lo, hi = target.get("range_min"), target.get("range_max")
    if lo is not None and new_value < lo or hi is not None and new_value > hi:
        return None, {
            "status": "OUTSIDE_DECLARED_ENVELOPE",
            "reason": (f"{param_id} envelope is [{lo}, {hi}] "
                       f"({target.get('unit')}); requested {new_value}. "
                       "The envelope is the safe-and-meaningful exposure "
                       "bound (R389 Phase 5) — refusing, not clamping "
                       "silently.")}

    model = {
        "model_id": "showcase:" + slot,
        "template_id": f"portfolio_slot_{slot}",
        "model_version": "showcase_preview_r389",
        "candidate_id": f"showcase_{slot}",
        "build_program": source,
        "parameter_map": pmap,
    }
    from discovery_fabric.engine import cad_pipeline
    mutation_id = f"ui_preview_{int(time.time())}"
    out_dir = PREVIEW_ROOT / slot / f"{param_id}_{new_value}"
    try:
        built, rec = cad_pipeline.rebuild_with_mutation(
            model, param_id, new_value, mutation_id,
            reason, out_dir=str(out_dir))
    except Exception as exc:  # noqa: BLE001
        return None, {"status": "BUILD_ERROR",
                      "reason": f"{type(exc).__name__}: {exc}"[:400]}

    result: Dict[str, Any] = {
        "status": rec.get("status"),
        "slot": slot, "param_id": param_id,
        "new_value": new_value, "unit": target.get("unit"),
        "value_class": target.get("value_class"),
        "evidence_class": "COMPUTATIONAL_RESULT",
        "mutation_id": mutation_id,
        "preview_dir": str(out_dir),
        "record": {k: v for k, v in rec.items()
                   if k in ("status", "build_errors", "model_id",
                            "validation_summary",
                            "rebuild_for_mutation")},
        "honesty": "MODELLED preview inside the declared envelope — "
                   "the canonical portfolio package is untouched; this "
                   "rebuild is a hypothesis exploration, not a state "
                   "change (Art. IX/XXVII/XXXVIII).",
    }
    if built:
        result["measurements"] = built.get("measurements")
        gv = built.get("geometry_validation") or {}
        result["geometry_validation"] = {
            "valid": gv.get("valid"),
            "status": gv.get("status"),
            "checks": {g: c.get("status")
                       for g, c in (gv.get("checks") or {}).items()},
        }
        result["model_id"] = built.get("model_id")
        glb_arts = {k: v for k, v in (built.get("derived_artifacts")
                                      or {}).items()
                    if k.startswith("GLB")}
        if glb_arts:
            first = next(iter(glb_arts.values()))
            # serve path uses the preview registry (see server.py)
            result["preview_glb"] = {
                "path": first.get("path"),
                "sha256": first.get("sha256"),
                "bytes": first.get("bytes"),
                "serve": f"/api/showcase/{slot}/preview/"
                         f"{Path(first.get('path')).name}",
            }
    return result, {"status": "OK"}


def preview_glb_path(slot: str, name: str) -> Optional[Path]:
    """Resolve a preview GLB by filename inside this slot's previews."""
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", name)
    root = PREVIEW_ROOT / slot
    if not root.exists():
        return None
    hits = [p for p in root.rglob(safe) if p.is_file()
            and p.parent == p.parent]  # any depth within the slot
    if not hits:
        return None
    return sorted(hits, key=lambda p: p.stat().st_mtime)[-1]


# ---------------------------------------------------------------------------
# R390: the REALITY LOOP surface (CEO directive #6 — the proof that an
# observation changes a technical decision, shown in the product)
# ---------------------------------------------------------------------------

def reality_loop_record(slot: str) -> Optional[Dict[str, Any]]:
    """Product view of the R390 reality-loop closure for a slot.

    Reads the LIVE closure record (TOSCANINI/R390_REALITY_LOOP/**) for
    this slot's package and returns the investor-facing summary: the
    CEO's nine loop steps, the observation, the discrepancy, the causal
    hypothesis, the decision change, and the re-evaluated technical
    result. Honest labels only — MEASURED is shown with its acquisition
    attestation; nothing claims PHYSICAL_VALIDATION (Art. XXXVIII).
    """
    root = REPO_ROOT / "TOSCANINI" / "R390_REALITY_LOOP"
    if not root.exists():
        return None
    candidates = []
    for p in root.rglob("LOOP_CLOSURE_RECORD.json"):
        try:
            rec = json.loads(p.read_text())
        except (json.JSONDecodeError, ValueError):
            continue
        if rec.get("package_slot") == slot:
            candidates.append(rec)
    if not candidates:
        return None
    # prefer a real-event LOOP_CLOSED record; else the newest
    candidates.sort(key=lambda r: (
        bool(r.get("real_event")), r.get("status") == "LOOP_CLOSED"))
    rec = candidates[-1]
    comp = rec.get("comparison") or {}
    hyp = rec.get("causal_hypothesis") or {}
    mut = rec.get("mutation") or {}
    reev = rec.get("re_evaluation") or {}
    proof = (reev.get("decision_change_proof") or {})
    chain = rec.get("causal_chain") or {}
    return {
        "kind": "REALITY_LOOP",
        "slot": slot,
        "status": rec.get("status"),
        "loop_verification_state": rec.get("loop_verification_state"),
        "real_event": rec.get("real_event"),
        "observation": {
            "event_id": rec.get("observation_event_id"),
            "origin": rec.get("observation_origin"),
            "origin_caveat": rec.get("observation_origin_caveat"),
            "quantity": comp.get("name"),
            "design_value": comp.get("design_value"),
            "measured_value": comp.get("reality_value"),
            "relative_delta": comp.get("relative_delta"),
            "declared_uncertainty": comp.get("declared_uncertainty"),
            "status": comp.get("status"),
            "design_declared_basis": comp.get("design_declared_basis"),
        },
        "causal_hypothesis": {
            "statement": hyp.get("statement"),
            "equation_basis": hyp.get("equation_basis"),
            "residual_unknown": hyp.get("residual_unknown"),
            "deterministic": hyp.get("deterministic"),
            "llm_used": hyp.get("llm_used"),
        },
        "decision_change": {
            "question": proof.get("question"),
            "answer": proof.get("answer"),
            "before": proof.get("decision_before"),
            "after": proof.get("decision_after"),
            "technical_result": proof.get("technical_result"),
            "mutation": {
                "parameter": mut.get("target_parameter"),
                "from": mut.get("from_value"),
                "to": mut.get("to_value"),
                "envelope": mut.get("envelope"),
                "applied_to_canonical_package":
                    mut.get("applied_to_canonical_package")},
        },
        "re_evaluation": {
            "evaluator": reev.get("evaluator"),
            "before": reev.get("before"),
            "as_built": reev.get("as_built_at_design_geometry"),
            "after": reev.get("after"),
            "restored_ratio": reev.get("conductance_restored_ratio"),
        },
        "causal_chain": {
            "stages": [s.get("stage") for s in
                       (chain.get("stages") or [])],
            "recorded_in_canonical_ledger":
                chain.get("recorded_in_canonical_ledger"),
        },
        "preview_glb": ((rec.get("new_design") or {}).get("preview_glb")
                        or {}).get("path"),
        "honesty": rec.get("honesty") or (
            "MEASURED data entered through the R370G one door; the "
            "canonical buyer package is untouched; PHYSICAL_VALIDATION "
            "is never claimed (Art. XXXVIII)"),
    }

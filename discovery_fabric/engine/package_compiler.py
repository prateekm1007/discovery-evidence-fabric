"""discovery_fabric/engine/package_compiler.py — R440.1 THE canonical
package compiler.

    FINAL_CANONICAL_INVENTION            (post-evolution final state — R440.2)
            ↓
    FINAL_ENGINEERING_STATE
            ↓
    FINAL_DECISIVE_EXPERIMENT
            ↓
    CANONICAL_PACKAGE_COMPILER           (this module — the ONE entry)
            ↓  TECHNOLOGY_PACKAGE_MODEL.json   (R440.4 object model)
            ↓  PACKAGE_SECTION_PROVENANCE.json (R440.5 structural binding)
            ↓  humanized rendering              (R440.6 buyer language)
            ↓  compiler validators              (R440.7–.12)
            ↓  INDEPENDENT_PACKAGE_QUALITY_GATE (R440.14 — verdict from
            ↓                                      the built tree, never
            ↓                                      from compiler objects)
    ATOMIC_PACKAGE_PROMOTION             (R440.13 — ZIP only on PASS;
                                           quarantine + PACKAGE_BUILD_BLOCKED
                                           on FAIL)

Production call graph contract (R440.1):
  * Exactly ONE runtime call site creates the customer package:
    invention_bridge/bridge.py step 3 calls compile_package().
  * The old discovery_fabric.engine.package_factory is RETIRED from
    production (archived; Art. LXIV disposition recorded).
  * package.assemble() is this compiler's rendering/derivation library,
    not an authority.

The compiler never certifies itself: the quality gate (package_quality_gate)
parses the built tree independently. A BLOCK is a first-class product
outcome — the buyer never receives an incoherent package.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .invention_bridge import package as _render
from .invention_bridge import epistemics as _ep
from .domains import (canonical_family_of_engine_domain,  # R445
                      resolve_run_canonical_family)

COMPILER_VERSION = "R440_CANONICAL_PACKAGE_COMPILER/1.1"  # R445: canonical domain family


class PackageCompileError(RuntimeError):
    """Raised when the canonical state cannot produce a coherent package.

    A compile error is an honest BLOCKED build (never a silent partial
    package) — the caller records PACKAGE_BUILD_BLOCKED with this reason.
    """


# ---------------------------------------------------------------------------
# 1. FINAL canonical state resolution (R440.2 — after evolution)
# ---------------------------------------------------------------------------
_FINAL_STATE_FILES = (
    ("final_state", "final_state.json"),
    ("invention_specification", "INVENTION_SPECIFICATION.json"),
    ("engineering_specification", "ENGINEERING_SPECIFICATION.json"),
    ("decisive_experiment", "DECISIVE_EXPERIMENT.json"),
)


def _read_json(path: Path) -> Optional[dict]:
    try:
        if path.is_file():
            return json.loads(path.read_text())
    except Exception:  # noqa: BLE001 — malformed record -> honest absent
        return None
    return None


def resolve_final_state(run_result: Dict[str, Any],
                        work_dir: Optional[str]) -> Dict[str, Any]:
    """The FINAL canonical state (post-evolution). Run-dir persisted
    artifacts are the authority (Art. X); run_result fields are the
    fallback. final_state.json + INVENTION_SPECIFICATION.json as
    persisted by the evolution pipeline are exactly the FINAL state
    (R440.2: the package compiles from the final generation, never a
    pre-evolution snapshot)."""
    final: Dict[str, Any] = {}
    rd = Path(work_dir) if work_dir else None
    for field, fname in _FINAL_STATE_FILES:
        obj = _read_json(rd / fname) if rd else None
        if obj is None:
            obj = run_result.get(field)
        if obj is not None:
            final[field] = obj
    return final


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      default=str, separators=(",", ":"))


def final_invention_hash(final_state: Dict[str, Any]) -> Optional[str]:
    """R440.2 — the exact hash of the FINAL invention specification.

    The package records this hash; the quality gate reconciles it
    against the canonical state. A GEN-2 mutation after compilation
    fails reconciliation (the adversarial mutation test)."""
    spec = final_state.get("invention_specification")
    if not isinstance(spec, dict):
        return None
    # the spec's own recorded hash, when present, is the canonical one
    for key in ("_spec_hash", "spec_hash"):
        h = spec.get(key)
        if isinstance(h, str) and len(h) >= 16:
            return h
    return hashlib.sha256(_canonical_json(spec).encode()).hexdigest()


# ---------------------------------------------------------------------------
# 2. The TECHNOLOGY_PACKAGE_MODEL (R440.4 — one internal representation)
# ---------------------------------------------------------------------------
def _u(field: Any) -> Any:
    """Unwrap a {value, epistemic_class, ...} field to its value."""
    if isinstance(field, dict) and "value" in field and set(
            field.keys()) <= {"value", "epistemic_class", "origin_stage",
                              "evidence_ids", "note", "source_span",
                              "provenance"}:
        return field.get("value")
    return field


def build_technology_package_model(
        run_result: Dict[str, Any], cio: Dict[str, Any],
        geometry_out: Dict[str, Any],
        final_state: Dict[str, Any],
        visualizability: Optional[Dict[str, Any]],
        engine_identity: Optional[Tuple[Optional[str], str]]) -> Dict:
    """R440.4 — the canonical intermediate object. Every PDF and every
    machine-readable layer derives from this model; nothing else may
    invent package content."""
    cio = cio or {}
    inv = final_state.get("invention_specification") \
        or run_result.get("invention_specification") or {}
    eng = final_state.get("engineering_specification") \
        or run_result.get("engineering_specification") or {}
    fs = final_state.get("final_state") \
        or run_result.get("final_state") or {}
    ke = final_state.get("decisive_experiment") \
        or run_result.get("decisive_experiment") or {}
    run_id = str(run_result.get("session_id")
                 or run_result.get("run_id") or "run")

    # unwrapped canonical field views (tagged {value, epistemic_class} -> value)
    inv_mech = _u(inv.get("mechanism")) or {}
    if not isinstance(inv_mech, dict):
        inv_mech = {"mechanism": str(inv_mech)}
    inv_chain = _u(inv.get("causal_chain")) or {}
    if not isinstance(inv_chain, dict):
        inv_chain = {}
    inv_problem = _u(inv.get("problem")) or {}
    if not isinstance(inv_problem, dict):
        inv_problem = {"failure": str(inv_problem)}
    inv_ke = _u(inv.get("killer_experiment")) or {}
    if not isinstance(inv_ke, dict):
        inv_ke = {}

    # ---- identity (R440.2/A): the CANONICAL invention id string is
    # preserved EXACTLY (inv:...:hash); the flattened label is only a
    # filename form. This closes the R439 identity divergence defect.
    canonical_invention_id = ""
    inv_id_field = inv.get("invention_id")
    if isinstance(inv_id_field, dict):
        canonical_invention_id = str(inv_id_field.get("value") or "")
    elif inv_id_field is not None:
        canonical_invention_id = str(inv_id_field)
    if not canonical_invention_id:
        cid = (cio.get("identity") or {}).get("invention_id")
        canonical_invention_id = str(
            (cid.get("value") if isinstance(cid, dict) else cid) or "")
    pid_field = inv.get("problem_id")
    if isinstance(pid_field, dict):
        pid_val = pid_field.get("value")
    else:
        pid_val = pid_field
    problem_id = str(run_result.get("problem_id") or pid_val or "")
    # R445: the package identity's domain_family is THE canonical family
    # — consumed via the ONE shared consumer ladder (domains.py::
    # resolve_run_canonical_family: the upstream engineering-spec
    # canonical_family first, then the registry over the run's own
    # problem words, then the engine-domain mapping). The same function
    # the bridge's domain spec uses — cross-layer agreement by
    # construction; never a compiler-side mapping of two vocabularies
    # (the F1 fix is upstream, not here).
    domain_family = resolve_run_canonical_family(
        run_result, eng)["canonical_family"]
    technology_name = str(
        run_result.get("title")
        or _u(inv.get("invention_id"))
        or canonical_invention_id
        or f"toscanini-{run_id[:12]}")
    fi_hash = final_invention_hash(final_state)
    # the PROBLEM's own domain family — ONLY from the run's explicit
    # problem classification (domain_hint); NEVER from the engineering
    # routing domain (a CSF-shunt problem routed to fluidics engineering
    # has problem domain 'medical', not 'fluidics_hydraulic' — conflating
    # the two would make the problem's own vocabulary look like
    # contamination). When the hint is absent the independent gate
    # re-derives the problem family from the canonical problem text
    # (Art. III: the user's own words are source, not claimant content).
    problem_domain = str(run_result.get("domain_hint") or "") or None

    model: Dict[str, Any] = {
        "schema": "TECHNOLOGY_PACKAGE_MODEL/1.0",
        "compiler_version": COMPILER_VERSION,
        "identity": {
            "run_id": run_id,
            "package_id": _flatten(canonical_invention_id
                                   or f"toscanini-{run_id[:12]}"),
            "invention_id": canonical_invention_id,
            "problem_id": problem_id,
            "technology_name": technology_name,
            "domain_family": domain_family,
            "problem_domain_family": problem_domain,
            "final_invention_hash": fi_hash,
        },
        "problem": {
            "user_problem": run_result.get("user_text")
            or run_result.get("title"),
            "failure_mode": (inv_problem.get("failure_mode")
                              or inv_problem.get("failure")
                              or inv_problem.get("device")),
            "unmet_need": _u(inv.get("user_need")),
            "source_refs": ["invention_specification.problem",
                            "invention_specification.user_need",
                            "run_record.user_text"],
        },
        "buyer": {
            "receives": (eng.get("transfer_boundary") or {}).get(
                "buyer_receives") or [],
            "must_create": (eng.get("transfer_boundary") or {}).get(
                "buyer_must_create") or [],
            "source_refs": ["engineering_specification.transfer_boundary"],
        },
        "invention": {
            "mechanism": inv_mech,
            "novelty_hypothesis": _u(inv.get("novelty_hypothesis")),
            "distinguishing_features": _u(inv.get(
                "distinguishing_features")),
            "intervention_site": inv_chain.get("intervention_site")
            or inv_mech.get("intervention"),
            "source_refs": ["invention_specification.mechanism",
                            "invention_specification.novelty_hypothesis"],
        },
        "causal_mechanism": {
            "chain": inv_chain,
            "expected_effect": inv_chain.get("expected_effect")
            or inv_mech.get("expected_effect"),
            "falsification_test": inv_chain.get("falsification_test"),
            "source_refs": ["invention_specification.causal_chain",
                            "invention_specification.mechanism"],
        },
        "causal_delta": {
            "why_genuinely_different": _u(inv.get("novelty_hypothesis")),
            "new_interaction": inv_chain.get("new_interaction"),
            "source_refs": ["invention_specification.novelty_hypothesis",
                            "invention_specification.causal_chain"],
        },
        "evidence": {
            "classification_counts": fs.get(
                "evidence_classification_counts") or {},
            "prior_art_status": fs.get("prior_art_status"),
            "retrieval_count": len((run_result.get("evidence_pack")
                                    or {}).get("retrieval") or []),
            "source_refs": ["final_state.evidence_classification_counts",
                            "evidence_pack.retrieval"],
        },
        "engineering": {
            "subsystems": (eng.get("system_architecture") or {}).get(
                "subsystems") or [],
            "design_inputs": eng.get("design_inputs") or [],
            "design_outputs": eng.get("design_outputs") or [],
            "constraints": eng.get("constraints") or [],
            "failure_modes": (eng.get("engineering_core") or {}).get(
                "failure_modes") or eng.get("failure_analysis") or [],
            "verification_matrix": eng.get("verification_matrix") or [],
            "build_plan": eng.get("engineering_build_plan") or [],
            "materials": eng.get("materials") or [],
            "manufacturing": (eng.get("manufacturing") or {}).get(
                "candidate_processes") or [],
            "source_refs": ["engineering_specification.*"],
        },
        # R443: the requirements dimension — buyer / manufacturing /
        # regulatory / market requirements derived from the CANONICAL
        # applicability state (engineering_specification.applicability,
        # the one context authority). The independent gate re-verifies
        # that every requirement statement in the built package traces
        # HERE (contamination check); a reusable medical template can
        # never again supply requirements to an industrial problem.
        "requirements": {
            "context_class": (eng.get("applicability") or {}).get(
                "context_class") or "UNKNOWN",
            "buyer_type": ((eng.get("applicability") or {}).get(
                "requirements") or {}).get("buyer_type") or {},
            "engineering_capability": ((eng.get("applicability") or {})
                                       .get("requirements") or {}).get(
                "engineering_capability") or [],
            "manufacturing_capability": ((eng.get("applicability") or {})
                                         .get("requirements") or {}).get(
                "manufacturing_capability") or [],
            "regulatory": ((eng.get("applicability") or {}).get(
                "requirements") or {}).get("regulatory") or {},
            "market_channels": ((eng.get("applicability") or {}).get(
                "requirements") or {}).get("market_channels") or [],
            "domain_content_exclusions": (eng.get("applicability") or
                                         {}).get(
                "domain_content_exclusions") or [],
            # the decision's OWN recorded basis (score table + matched
            # signals) rides the model so the independent gate can
            # verify the context claim is internally coherent (Art. III
            # — a fabricated context claim has zero signal support)
            "score_table": (eng.get("applicability") or {}).get(
                "score_table") or [],
            "matched_signals": (eng.get("applicability") or {}).get(
                "matched_signals") or [],
            "source_refs": [
                "engineering_specification.applicability (the canonical "
                "problem-context decision + requirements projection)"],
            # the gate's binding key (view.BINDING_KEYS): this section
            # IS a canonical projection — the vocabulary it carries
            # (including an honest NOT_APPLICABLE medical statement) is
            # bound to the applicability record, never free-floating
            "canonical_source_refs": [
                "engineering_specification.applicability"],
        },
        "equations": {
            "registry_source": "EQUATION_REGISTRY.json",
            "governing_models": ((eng.get("engineering_core") or {}).get(
                "governing_model") or {}),
            "source_refs": [
                "engineering_specification.engineering_core."
                "governing_model"],
        },
        "parameters": {
            "critical": (eng.get("engineering_core") or {}).get(
                "critical_parameters") or [],
            "source_refs": [
                "engineering_specification.engineering_core."
                "critical_parameters"],
        },
        "verification": {
            "matrix": eng.get("verification_matrix") or [],
            "validation": eng.get("validation_matrix") or [],
            "source_refs": ["engineering_specification.verification_matrix",
                            "engineering_specification.validation_matrix"],
        },
        "decisive_experiment": {
            "selected": (ke.get("selected") if isinstance(ke.get("selected"),
                        dict) else None) or _selected_shortlist(ke)
            or (run_result.get("decisive_experiment") or {}).get(
                "selected"),
            "invention_killer_experiment": inv_ke,
            "source_refs": ["DECISIVE_EXPERIMENT.json.selected",
                            "invention_specification.killer_experiment"],
        },
        "unknowns": {
            "recorded": (run_result.get("invention_specification")
                         or inv or {}).get("uncertainties"),
            "source_refs": ["invention_specification.uncertainties"],
        },
        "artifact_state": {
            "visualizability_class": geometry_out.get(
                "visualizability_class")
            or (visualizability or {}).get("visualizability_class"),
            "components": geometry_out.get("components") or [],
            "glb_sha256": geometry_out.get("glb_sha256"),
            "domain_family": geometry_out.get("domain_family"),
            "source_refs": ["bridge.geometry_out"],
        },
        "transfer_boundary": {
            "record": eng.get("transfer_boundary") or {},
            "source_refs": ["engineering_specification.transfer_boundary"],
        },
        "commercial_evidence": {
            "layer": "COMMERCIAL_EVIDENCE.json",
            "source_refs": ["COMMERCIAL_EVIDENCE.json (derived)"],
        },
        "maturity": {
            "basis_source": "MATURITY_BASIS.json",
            "final_status": fs.get("final_status"),
            "source_refs": ["final_state.final_status",
                            "MATURITY_BASIS.json (derived)"],
        },
        "provenance": {
            "engine_commit": engine_identity[0] if engine_identity else None,
            "engine_commit_source": (engine_identity[1]
                                     if engine_identity else None),
            "final_envelope_hash": fs.get("final_envelope_hash"),
            "invention_spec_hash": inv.get("_spec_hash"),
            "generated_at_utc": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        # R440.4 canonical inputs — the frozen source objects every layer
        # derives from (with hashes; the section provenance points here)
        "canonical_inputs": {
            "invention_specification": inv,
            "engineering_specification": eng,
            "final_state": fs,
            "decisive_experiment": ke,
            "source_hashes": {
                "invention_specification": fi_hash,
                "final_state": fs.get("final_envelope_hash"),
            },
            # binding key: this section is the FROZEN SOURCE copy — its
            # vocabulary is the sources' own, bound by hash
            "canonical_source_refs": [
                "INVENTION_SPECIFICATION.json",
                "ENGINEERING_SPECIFICATION.json",
                "final_state.json", "DECISIVE_EXPERIMENT.json"],
        },
    }
    return model


def _flatten(label: str) -> str:
    return "".join(c for c in str(label)
                   if c.isalnum() or c in "-_") or "package"


def _selected_shortlist(ke: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The selected experiment from the DECISIVE_EXPERIMENT shortlist
    (the real schema: items carry 'experiment'/'hypotheses'/'is_selected'
    _killer' — not 'hypothesis'/'comparison_arm' keys)."""
    for key in ("selected", "shortlist", "ranked"):
        items = ke.get(key)
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict) and (
                        it.get("is_selected_killer")
                        or it.get("is_selected")):
                    return it
    return None


def model_run_view(model: Dict[str, Any],
                   run_result: Dict[str, Any]) -> Dict[str, Any]:
    """The run_result-shaped VIEW of the model — the ONLY input the
    document renderers see (R440.4: PDFs derive from the object model;
    nothing else invents package content)."""
    ci = model["canonical_inputs"]
    view = dict(run_result)
    view["invention_specification"] = ci["invention_specification"]
    view["engineering_specification"] = ci["engineering_specification"]
    view["final_state"] = ci["final_state"]
    view["decisive_experiment"] = ci["decisive_experiment"]
    if model["identity"].get("problem_id"):
        view["problem_id"] = model["identity"]["problem_id"]
    if model["identity"].get("technology_name"):
        view["title"] = model["identity"]["technology_name"]
    if model["identity"].get("run_id"):
        view["run_id"] = model["identity"]["run_id"]
        view["session_id"] = model["identity"]["run_id"]
    return view


# ---------------------------------------------------------------------------
# 3. Compiler validators (R440.7–.12) — fail closed BEFORE rendering
# ---------------------------------------------------------------------------
def validate_model(model: Dict[str, Any]) -> List[Dict[str, str]]:
    """Compile-time contract checks over the object model. Returns the
    list of violations ([] = valid). A violation BLOCKS the build with
    its reason recorded (an honest BLOCK, never a weakened package)."""
    v: List[Dict[str, str]] = []
    ident = model["identity"]
    inv = model["canonical_inputs"]["invention_specification"]
    eng = model["canonical_inputs"]["engineering_specification"]
    fs = model["canonical_inputs"]["final_state"]

    # R440.2 — the package MUST bind the final invention hash
    if not ident.get("final_invention_hash"):
        v.append({"code": "M-NO-FINAL-HASH",
                  "reason": "final invention hash could not be computed — "
                            "the package cannot bind the final generation"})
    # identity coherence (R440.1/A)
    if not ident.get("invention_id"):
        v.append({"code": "M-NO-INVENTION-ID",
                  "reason": "canonical invention_id absent from the final "
                            "state — the package cannot prove ownership"})
    if not ident.get("run_id"):
        v.append({"code": "M-NO-RUN-ID",
                  "reason": "run identity absent — reconstruction "
                            "(Art. LXII) impossible"})

    # R440.9 — package-level causal coherence: PROBLEM → MECHANISM →
    # INTERVENTION → EFFECT → TEST must connect (machine-checkable;
    # the real schema: problem.failure, mechanism.mechanism,
    # causal_chain.intervention_site, causal_chain.expected_effect,
    # killer experiment presence)
    mechanism_text = (model["invention"].get("mechanism") or {}).get(
        "mechanism") if isinstance(
        model["invention"].get("mechanism"), dict) else None
    chain = [
        ("PROBLEM", model["problem"].get("failure_mode")
         or model["problem"].get("user_problem")),
        ("MECHANISM", mechanism_text
         or (model["invention"].get("mechanism") or {}).get(
             "intervention") if isinstance(
             model["invention"].get("mechanism"), dict) else None
         or model["invention"].get("mechanism")),
        ("INTERVENTION", model["invention"].get("intervention_site")
         or (model["invention"].get("mechanism") or {}).get(
             "intervention") if isinstance(
             model["invention"].get("mechanism"), dict) else None),
        ("EFFECT", model["causal_mechanism"].get("expected_effect")),
        ("TEST", _experiment_present(model)),
    ]
    missing_links = [name for name, val in chain
                     if val in (None, "", [], {})]
    if missing_links:
        v.append({"code": "M-CAUSAL-CHAIN-BROKEN",
                  "reason": f"causal chain links absent and not declared "
                            f"UNKNOWN: {missing_links} (R440.9: PROBLEM → "
                            f"MECHANISM → INTERVENTION → EFFECT → TEST "
                            f"must connect)"})

    # R440.7 — semantic section contracts (each section must answer its
    # questions FROM canonical state; a template answer is a violation)
    if mechanism_text in (None, "", []):
        v.append({"code": "M-MECHANISM-EMPTY",
                  "reason": "MECHANISM section cannot answer 'what "
                            "physically/algorithmically changes' — no "
                            "canonical mechanism recorded"})
    expected_effect = model["causal_mechanism"].get("expected_effect")
    if expected_effect in (None, "", []):
        v.append({"code": "M-EFFECT-UNKNOWN",
                  "reason": "MECHANISM cannot answer 'expected measurable "
                            "effect' and no explicit UNKNOWN declaration "
                            "with blockers is present (R440.7/.11)"})
    subsystems = model["engineering"].get("subsystems")
    if subsystems in (None, "", []):
        v.append({"code": "M-ENGINEERING-EMPTY",
                  "reason": "ENGINEERING cannot answer 'what is being "
                            "built' — no subsystem architecture recorded"})

    # R440.10 — useful depth (five flags per critical section)
    for section, items in (
            ("SYSTEM_ARCHITECTURE", subsystems),
            ("CRITICAL_PARAMETERS",
             model["parameters"].get("critical")),
            ("FAILURE_MODES", model["engineering"].get("failure_modes")),
            ("DESIGN_INPUTS", model["engineering"].get("design_inputs")),
    ):
        if items in (None, [], {}):
            v.append({"code": "M-DEPTH-SECTION-ABSENT",
                      "reason": f"{section}: not present — depth means "
                                f"useful depth, 20 sections PRESENT but "
                                f"empty is the #160 failure mode"})

    # R440.11 — experiment contract: hypothesis/comparison/apparatus/
    # measured/sampling/acceptance/falsification/uncertainty or an
    # explicit UNKNOWN triple (why / what to measure / what is blocked).
    # The REAL canonical shapes: DECISIVE_EXPERIMENT shortlist items
    # (experiment/hypotheses/kill_probability basis) and the invention
    # spec's killer_experiment (selected/definition/hypotheses/
    # options_ranked). The independent gate's K contract (calibrated on
    # the golden references) remains the final arbiter; this validator
    # blocks only a state with NO usable experiment content at all.
    if not _experiment_present(model):
        v.append({"code": "M-EXPERIMENT-CONTRACT-ABSENT",
                  "reason": "EXPERIMENT section has no usable contract "
                            "(no decisive-experiment selection, no killer "
                            "experiment record with hypotheses/options, "
                            "no falsification test) and no explicit "
                            "UNKNOWN-with-blockers declaration "
                            "(R440.11)"})

    # R440.12 — 3D traceability for physical inventions: the geometry
    # components must exist and map to the invention architecture
    art = model["artifact_state"]
    vis_class = art.get("visualizability_class") or ""
    comps = art.get("components") or []
    if vis_class and vis_class not in (
            _ep.NOT_VISUALIZABLE, "NOT_VISUALIZABLE") and not comps:
        v.append({"code": "M-3D-COMPONENTS-ABSENT",
                  "reason": f"visualizable invention ({vis_class}) with "
                            f"no geometry components — canonical "
                            f"components = geometry components cannot "
                            f"be verified (R440.12)"})

    # R440.8 — domain coherence (model-side): declared domain must not
    # be contradicted by the model's own engineering domain detection.
    # R445: the comparison happens in the ONE canonical vocabulary —
    # the declared family (canonical, application axis) is checked
    # against the upstream canonical decision when present, else
    # against the canonical mapping of the engine's physics-domain
    # detection (the two axes are orthogonal: a catheter is biomedical
    # as a family and fluidics as physics; neither contradicts the
    # other — what this check catches is the compiler diverging from
    # the engineering spec's own recorded family decision).
    declared = ident.get("domain_family")
    wd = eng.get("why_this_domain") or {}
    upstream_cf = wd.get("canonical_family") if isinstance(
        wd.get("canonical_family"), str) else ""
    detected = str(eng.get("technology_domain") or wd.get("domain") or "")
    detected_family = canonical_family_of_engine_domain(detected) \
        if detected else ""
    if declared and upstream_cf and str(declared).strip() \
            != str(upstream_cf).strip():
        v.append({"code": "M-DOMAIN-CONTRADICTION",
                  "reason": f"declared domain_family {declared!r} "
                            f"contradicts the engineering spec's own "
                            f"canonical family decision {upstream_cf!r} "
                            f"(R440.8/R445: the compiler must consume the "
                            f"upstream authority unchanged)"})
    elif declared and not upstream_cf and detected_family \
            and str(declared).strip() != detected_family:
        v.append({"code": "M-DOMAIN-CONTRADICTION",
                  "reason": f"declared domain_family {declared!r} "
                            f"contradicts engineering domain detection "
                            f"{detected!r} -> canonical family "
                            f"{detected_family!r} (R440.8/R445)"})
    return v


def _experiment_present(model: Dict[str, Any]) -> bool:
    """Is there ANY usable decisive-experiment content in the model?
    (the real schema: selected shortlist item, killer-experiment record
    with definition/hypotheses/options, or a falsification test)."""
    de = model.get("decisive_experiment") or {}
    sel = de.get("selected")
    if isinstance(sel, dict) and (sel.get("experiment")
                                  or sel.get("definition")
                                  or sel.get("hypotheses")):
        return True
    inv_ke = de.get("invention_killer_experiment") or {}
    if (inv_ke.get("definition") or inv_ke.get("hypotheses")
            or inv_ke.get("options_ranked")
            or (inv_ke.get("selected") not in (None, "", "UNKNOWN"))):
        return True
    if model.get("causal_mechanism", {}).get("falsification_test"):
        return True
    return False


# ---------------------------------------------------------------------------
# 4. Section provenance (R440.5) — structural, never lexical
# ---------------------------------------------------------------------------
_DOC_SOURCES = {
    "00_PACKAGE_README.pdf": [
        "invention_specification.problem",
        "invention_specification.user_need",
        "invention_specification.mechanism",
        "final_state.final_status",
        "DECISIVE_EXPERIMENT.json",
    ],
    "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf": [
        "invention_specification.problem",
        "invention_specification.mechanism",
        "invention_specification.novelty_hypothesis",
        "invention_specification.causal_chain.expected_effect",
        "final_state.evidence_classification_counts",
        "engineering_specification.design_inputs",
        "engineering_specification.engineering_core.failure_modes",
    ],
    "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf": [
        "invention_specification.problem",
        "engineering_specification.system_architecture.subsystems",
        "engineering_specification.engineering_core.governing_model",
        "engineering_specification.engineering_core.critical_parameters",
        "engineering_specification.design_inputs",
        "engineering_specification.design_outputs",
        "engineering_specification.engineering_core.failure_modes",
        "engineering_specification.verification_matrix",
        "engineering_specification.engineering_build_plan",
        "DECISIVE_EXPERIMENT.json",
    ],
    "03_BUYER_DECISION_CARD.pdf": [
        "invention_specification.problem",
        "invention_specification.mechanism",
        "invention_specification.novelty_hypothesis",
        "invention_specification.user_need",
        "invention_specification.uncertainties",
        "final_state.evidence_classification_counts",
        "final_state.final_status",
        "engineering_specification.engineering_build_plan",
        "DECISIVE_EXPERIMENT.json.selected",
    ],
    "04_EVIDENCE_SUMMARY.pdf": [
        "final_state.evidence_classification_counts",
        "evidence_pack.retrieval",
    ],
    "05_TRANSFER_MANIFEST.pdf": [
        "engineering_specification.transfer_boundary",
        "bridge.geometry_out",
        "final_state.final_status",
    ],
}


def build_section_provenance(model: Dict[str, Any]) -> Dict[str, Any]:
    """R440.5 — every buyer-facing section carries machine-readable
    provenance: source pointers, source hashes, derivation method,
    canonical identity. The verifier rejects a section without
    canonical provenance even when the prose sounds reasonable."""
    ident = model["identity"]
    ci = model["canonical_inputs"]
    source_hashes = ci.get("source_hashes") or {}
    sections: List[Dict[str, Any]] = []
    for doc, refs in _DOC_SOURCES.items():
        eq_ids = _equation_ids(model)
        param_ids = _parameter_ids(model)
        sections.append({
            "section_id": f"{Path(doc).stem}",
            "document": doc,
            "invention_id": ident.get("invention_id"),
            "run_id": ident.get("run_id"),
            "domain_family": ident.get("domain_family"),
            "canonical_source_refs": refs,
            "source_hashes": {
                "invention_specification": source_hashes.get(
                    "invention_specification"),
                "final_state": source_hashes.get("final_state"),
            },
            "derivation_method": "ENGINE_DERIVED",
            "equation_ids": eq_ids if "02" in doc or "01" in doc else [],
            "parameter_ids": param_ids if "02" in doc else [],
            "final_invention_hash": ident.get("final_invention_hash"),
        })
    return {
        "artifact": "PACKAGE_SECTION_PROVENANCE",
        "schema": "R440_SECTION_PROVENANCE/1.0",
        "rule": ("every buyer-facing section derives from these canonical "
                 "references; the independent verifier checks that the "
                 "references resolve — token coincidence is never "
                 "invention linkage (R440.3/.5)"),
        "sections": sections,
    }


def _equation_ids(model: Dict[str, Any]) -> List[str]:
    gm = (model["canonical_inputs"].get("engineering_specification")
          or {}).get("engineering_core") or {}
    eqs = ((gm.get("governing_model") or {}).get("equations")) or []
    out = []
    for e in eqs:
        if isinstance(e, dict):
            eid = e.get("equation_id") or e.get("id")
            if eid:
                out.append(str(eid))
    return out


def _parameter_ids(model: Dict[str, Any]) -> List[str]:
    params = model["parameters"].get("critical") or []
    out = []
    for p in params:
        if isinstance(p, dict):
            pid = p.get("parameter_id") or p.get("id") or p.get("param_id")
            if pid:
                out.append(str(pid))
    return out


# ---------------------------------------------------------------------------
# 5. Transactional compile (R440.13) — the ONE production entry
# ---------------------------------------------------------------------------
def compile_package(
    run_result: Dict[str, Any],
    cio: Optional[Dict[str, Any]],
    geometry_out: Dict[str, Any],
    work_dir: str,
    visualizability: Optional[Dict[str, Any]] = None,
    zip_name: Optional[str] = None,
    engine_identity: Optional[Tuple[Optional[str], str]] = None,
    run_gate: bool = True,
    rehearsal: bool = False,
    package_registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """The ONE canonical package compilation (R440.1). Returns the
    package_out contract (zip_path/manifest/maturity/...) on success, or
    a blocked record (state=PACKAGE_BUILD_BLOCKED, no zip) when any
    compiler validator or the independent quality gate fails.

    Transactional contract (R440.13):
      * build in a fresh empty temp dir (no stale artifact survives)
      * gate verifies the BUILT TREE (independent parse)
      * PASS -> ZIP appears at the public download path (atomic replace)
      * FAIL -> quarantine + PACKAGE_BUILD_BLOCKED.json; no ZIP, ever

    rehearsal=True stamps SYNTHETIC_REHEARSAL on every artifact class
    (Art. XXXVII: a rehearsal package is machinery proof, never a
    buyer deliverable — the label must ride in the manifest).
    package_registry_path: optional explicit registry for the terminal
    allocation marking (falls back to the run manifest's recorded
    path — production runs always persist it)."""
    work = Path(work_dir)
    final_state = resolve_final_state(run_result, str(work))
    model = build_technology_package_model(
        run_result, cio or {}, geometry_out, final_state,
        visualizability, engine_identity)
    ident = model["identity"]
    label = ident["package_id"]

    tmp = Path(tempfile.mkdtemp(prefix=f"pkgc_{label}_"))
    result: Dict[str, Any] = {
        "schema": COMPILER_VERSION,
        "compiler": "package_compiler.compile_package",
        "run_id": ident.get("run_id"),
        "package_id": label,
        "invention_id": ident.get("invention_id"),
        "final_invention_hash": ident.get("final_invention_hash"),
        "clean_build": True,
    }
    try:
        # ---- compiler validators FIRST (fail closed before rendering)
        violations = validate_model(model)
        if violations:
            return _blocked(result, work, tmp, model,
                            "MODEL_VALIDATION_FAILED",
                            violations, keep_quarantine=False)

        # ---- render the package tree from the MODEL view (R440.4)
        view = model_run_view(model, run_result)
        view_cio = dict(cio or {})
        view_cio["identity"] = dict(view_cio.get("identity") or {})
        view_cio["identity"]["invention_id"] = ident.get("invention_id")
        pkg_dir = tmp / "TECHNOLOGY_PACKAGE"
        render_out = _render.assemble(
            view, view_cio, geometry_out, str(pkg_dir),
            visualizability=visualizability,
            zip_name=None, engine_identity=engine_identity,
            build_zip=False)
        result["render_report"] = {
            k: render_out.get(k) for k in (
                "package_maturity", "visualizability_class",
                "glb_sha256", "render_artifacts", "render_status",
                "zip_bytes")}

        # ---- post-pass: model + provenance + identity stamps (R440.4/5)
        _post_pass(pkg_dir, model, render_out)

        # ---- A2 transparency (R440): the depth-contract evaluation of
        # the FINAL state rides in the package (the buyer/auditor sees
        # the per-section depth + structural tie evidence; the compiler
        # already FAILS CLOSED on a violated contract — this records it)
        try:
            from .depth_contract import evaluate_depth_contract
            ci = model["canonical_inputs"]
            depth_eval = evaluate_depth_contract(
                ci["invention_specification"],
                ci["engineering_specification"])
            (pkg_dir / "DEPTH_CONTRACT_EVALUATION.json").write_text(
                json.dumps(depth_eval, indent=2, default=str))
        except Exception:  # noqa: BLE001 — evaluation is transparency,
            # never a second authority (the validators + gate own the
            # verdict); a failure here must not block an otherwise
            # verified package
            pass

        # ---- rebuild the manifest over the final tree (R440.13)
        manifest = _rebuild_manifest(pkg_dir, label, render_out,
                                      model=model, rehearsal=rehearsal)

        # ---- independent quality gate over the BUILT TREE (R440.14)
        if run_gate:
            from .package_quality_gate import run_quality_gate
            canonical_for_gate = _canonical_for_gate(model)
            verdict = run_quality_gate(str(pkg_dir), canonical_for_gate)
            result["quality_gate"] = {
                k: verdict[k] for k in (
                    "package_quality", "failed_gates", "warned_gates",
                    "dimensions")}
            result["quality_gate_full"] = verdict
            # the verdict is PERSISTED in the run dir (Art. XXVI: the
            # release decision's evidence is auditable from the record,
            # never only from the compiler's return value)
            try:
                (work / "PACKAGE_QUALITY_GATE_VERDICT.json").write_text(
                    json.dumps(verdict, indent=2, default=str))
            except Exception:  # noqa: BLE001 — record best-effort
                pass
            if verdict["package_quality"] != "PASS":
                return _blocked(result, work, tmp, model,
                                "QUALITY_GATE_BLOCKED",
                                verdict.get("blocked_record")
                                or {"failed_gates": verdict["failed_gates"]})

        # ---- ATOMIC PROMOTION (R440.13): only now do the package dir
        # and the ZIP appear at the public path; stale zips removed
        zip_final = work / (zip_name
                            or f"TECHNOLOGY_TRANSFER_PACKAGE_{label}.zip")
        staged_zip = tmp / zip_final.name
        _zip_tree(pkg_dir, staged_zip)
        dest_dir = work / "TECHNOLOGY_PACKAGE"
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        shutil.move(str(pkg_dir), str(dest_dir))
        tmp_zip = work / (zip_final.name + ".partial")
        shutil.copy2(staged_zip, tmp_zip)
        os.replace(tmp_zip, zip_final)
        # stale package ZIPs from prior builds never survive (R440.13)
        for old in work.glob("TECHNOLOGY_PACKAGE_*.zip"):
            if old != zip_final:
                old.unlink()
        for old in work.glob("TECHNOLOGY_TRANSFER_PACKAGE_*.zip"):
            if old != zip_final:
                old.unlink()
        shutil.rmtree(tmp, ignore_errors=True)
        # Directive 2 binding (R440): the DISCOVERY_RELEASE record now
        # binds to the promoted transfer artifact by hash — written
        # only AFTER the compiler + independent gate passed, never
        # before (the release may never describe a package that does
        # not exist yet).
        result["release_binding"] = _bind_release(work, result, manifest)
        # registry terminal state: the allocated portfolio number
        # reaches HELD_FOR_HUMAN_REVIEW when the compiled package is
        # promoted (portfolio RELEASE to the buyer repo stays a
        # human-gated authority — Art. XXXIX; the registry path comes
        # from the run manifest the way resume does)
        result["registry_marked"] = _mark_registry(
            work, ident, package_registry_path)
        result.update({
            "state": "ZIP_READY",
            "zip_emitted": True,
            "buyer_release": True,
            "zip_path": str(zip_final),
            "zip_sha256": _sha256_file(zip_final),
            "zip_bytes": zip_final.stat().st_size,
            "package_dir": str(dest_dir),
            "manifest": manifest,
            "package_maturity": render_out.get("package_maturity"),
            "visualizability_class": render_out.get(
                "visualizability_class"),
            "essay": render_out.get("essay"),
            "glb_sha256": render_out.get("glb_sha256"),
            "render_artifacts": render_out.get("render_artifacts"),
            "render_status": render_out.get("render_status"),
            "invention_label": label,
            "engine_commit": render_out.get("engine_commit"),
            "package_version": render_out.get("package_version"),
            "promoted_at_utc": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
        return result
    except Exception as exc:  # noqa: BLE001 — a crash is a BLOCK, never partial
        return _blocked(result, work, tmp, model, "COMPILE_ERROR",
                        [{"code": type(exc).__name__,
                          "reason": str(exc)[:400]}],
                        keep_quarantine=False)


def _mark_registry(work: Path, ident: Dict[str, Any],
                  explicit_path: Optional[str] = None) -> Optional[str]:
    """Mark the allocated portfolio number HELD_FOR_HUMAN_REVIEW when
    the package is promoted (the registry is append-only — Art. XI).
    The registry path comes from the explicit argument or the run
    manifest (the way EngineRun resume does); a compile without a
    registry (pure workflows, tests) skips honestly."""
    inv_id = ident.get("invention_id")
    if not inv_id:
        return None
    registry_path = explicit_path
    if not registry_path:
        rm = _read_json(work / "run_manifest.json")
        if isinstance(rm, dict):
            registry_path = rm.get("package_registry_path")
    if not registry_path:
        return None
    try:
        from .package_registry import mark_released
        mark_released(inv_id, registry_path=registry_path,
                      status="HELD_FOR_HUMAN_REVIEW")
        return "HELD_FOR_HUMAN_REVIEW"
    except Exception:  # noqa: BLE001 — registry marking is best-effort;
        # the compile result (the package + the blocked/PASS record)
        # stands on its own; the registry retry is an operator concern
        return None


def _bind_release(work: Path, result: Dict[str, Any],
                  manifest: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update DISCOVERY_RELEASE.json with the compiled-package hashes
    (Directive 2: the release binds discovery to the transfer artifact
    by hash). The status becomes HELD_FOR_HUMAN_REVIEW: portfolio
    distribution to the buyer repository remains a human-gated
    authority (Art. XXXIX) — the compiler never auto-RELEASES a
    portfolio slot. Returns the binding written (None if no release
    record exists — e.g. pure compile workflows)."""
    rel = work / "DISCOVERY_RELEASE.json"
    try:
        data = json.loads(rel.read_text())
        if not isinstance(data, dict):
            return None
    except Exception:  # noqa: BLE001 — no release record: nothing to bind
        return None
    pm = work / "TECHNOLOGY_PACKAGE" / "PACKAGE_MANIFEST.json"
    binding = {
        "bound_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "compiler": COMPILER_VERSION,
        "package_folder": str(work / "TECHNOLOGY_PACKAGE"),
        "package_zip": result.get("zip_path"),
        "dossier_manifest_hash": _sha256_file(pm) if pm.is_file() else None,
        "buyer_package_hash": result.get("zip_sha256"),
        "final_invention_hash": result.get("final_invention_hash"),
        "quality_gate": (result.get("quality_gate") or {}).get(
            "package_quality"),
    }
    for key in ("package_folder", "package_zip", "dossier_manifest_hash",
                "buyer_package_hash"):
        if binding[key] is not None:
            data[key] = binding[key]
    data["status"] = "HELD_FOR_HUMAN_REVIEW"
    data["r440_package_compiled"] = binding
    rel.write_text(json.dumps(data, indent=2, default=str))
    return binding


def _post_pass(pkg_dir: Path, model: Dict[str, Any],
               render_out: Dict[str, Any]) -> None:
    """Stamp the object model + section provenance + canonical identity
    into the built tree (R440.2/.4/.5). Identity divergence (the R439
    specimen defect) is structurally closed: every machine layer carries
    the SAME canonical invention_id / run_id / problem_id / domain_family
    / technology_name / final_invention_hash."""
    ident = model["identity"]
    stamp = {
        "invention_id": ident.get("invention_id"),
        "run_id": ident.get("run_id"),
        "problem_id": ident.get("problem_id"),
        "domain_family": ident.get("domain_family"),
        "technology_name": ident.get("technology_name"),
        "final_invention_hash": ident.get("final_invention_hash"),
    }
    # 1. the object model + section provenance enter the tree
    (pkg_dir / "TECHNOLOGY_PACKAGE_MODEL.json").write_text(
        json.dumps(model, indent=2, ensure_ascii=False, default=str))
    (pkg_dir / "PACKAGE_SECTION_PROVENANCE.json").write_text(
        json.dumps(build_section_provenance(model), indent=2,
                   ensure_ascii=False, default=str))
    # 2. every machine JSON layer is identity-stamped
    for p in sorted(pkg_dir.glob("*.json")):
        if p.name in ("PACKAGE_MANIFEST.json",):
            continue
        try:
            data = json.loads(p.read_text())
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(data, dict):
            continue
        changed = False
        for key in ("invention_id", "run_id", "problem_id",
                    "domain_family", "technology_name",
                    "final_invention_hash"):
            if stamp[key] and not data.get(key):
                data[key] = stamp[key]
                changed = True
        if p.name == "PROVENANCE.json":
            # canonical_invention_state_identity.invention_id must be
            # the CANONICAL string (the R439 A-CANON-DIVERGENT defect)
            csi = data.get("canonical_invention_state_identity")
            if not isinstance(csi, dict):
                csi = {}
                data["canonical_invention_state_identity"] = csi
            csi["invention_id"] = ident.get("invention_id")
            csi["final_invention_hash"] = ident.get("final_invention_hash")
            data["final_invention_hash"] = ident.get("final_invention_hash")
            data["compiler"] = COMPILER_VERSION
            data["compile_transaction"] = (
                "temp-dir build -> compiler validators -> independent "
                "package quality gate -> atomic promotion (R440.13)")
            changed = True
        if changed:
            p.write_text(json.dumps(data, indent=2, ensure_ascii=False,
                                    default=str))
    # 3. MODEL/MODEL_MANIFEST.json gets model_id (the R439
    # S-RUN-IDENTITY-MISSING defect — Art. LXII reconstruction)
    mman = pkg_dir / "MODEL" / "MODEL_MANIFEST.json"
    if mman.is_file():
        try:
            data = json.loads(mman.read_text())
            if isinstance(data, dict) and not data.get("model_id"):
                data["model_id"] = f"model-{ident.get('package_id')}"
                data["invention_id"] = ident.get("invention_id")
                data["run_id"] = ident.get("run_id")
                mman.write_text(json.dumps(data, indent=2,
                                           ensure_ascii=False,
                                           default=str))
        except Exception:  # noqa: BLE001 — stamping stays honest
            pass


def _rebuild_manifest(pkg_dir: Path, label: str,
                      render_out: Dict[str, Any],
                      model: Optional[Dict[str, Any]] = None,
                      rehearsal: bool = False) -> Dict[str, Any]:
    """Re-hash the COMPLETE final tree (incl. the new model/provenance
    files) into PACKAGE_MANIFEST.json — the manifest always matches the
    promoted bytes exactly (R440.13). The Art. XXXVII honesty labels
    (loop_verification_state / real_loop_verified / transfer_ready,
    read from the built LOOP_STATE.json) and the SYNTHETIC_REHEARSAL
    stamp ride in the manifest: every package declares its own loop
    state (Art. XXXVII machine-enforcement point 1)."""
    files = []
    for p in sorted(pkg_dir.rglob("*")):
        if not p.is_file() or p.name == "PACKAGE_MANIFEST.json":
            continue
        files.append({
            "path": str(p.relative_to(pkg_dir)),
            "sha256": _sha256_file(p),
            "bytes": p.stat().st_size,
        })
    ident = (model or {}).get("identity") or {}
    loop_state = _read_json(pkg_dir / "LOOP_STATE.json") or {}
    maturity_basis = _read_json(pkg_dir / "MATURITY_BASIS.json") or {}
    manifest = {
        "artifact": "PACKAGE_MANIFEST",
        "package_id": label,
        "invention_id": ident.get("invention_id")
        or render_out.get("invention_label"),
        "technology_name": ident.get("technology_name"),
        "run_id": ident.get("run_id"),
        "file_count": len(files),
        "files": files,
        "package_maturity": render_out.get("package_maturity"),
        "visualizability_class": render_out.get("visualizability_class"),
        # ---- Art. XXXVII honesty labels (declared by EVERY package) --
        "loop_verification_state": loop_state.get(
            "loop_verification_state", "NONE"),
        "real_loop_verified": bool(loop_state.get("real_loop_verified")),
        "transfer_ready": bool(maturity_basis.get("transfer_ready")),
        "synthetic_rehearsal": bool(rehearsal),
        "integrity_rule": ("every file is sha256-hashed; verify after "
                           "transfer (R440.13: manifest rebuilt over the "
                           "final promoted tree)"),
    }
    (pkg_dir / "PACKAGE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2))
    return manifest


def _canonical_for_gate(model: Dict[str, Any]) -> Dict[str, Any]:
    """The canonical state handed to the INDEPENDENT gate — identity +
    problem + final hash + components. The gate re-derives everything
    else from the package itself (Art. III: the claimant cannot define
    what the evidence says)."""
    ident = model["identity"]
    inv = model["canonical_inputs"]["invention_specification"]
    arch = (model["canonical_inputs"].get("engineering_specification")
            or {}).get("system_architecture") or {}
    comps = [c.get("name") if isinstance(c, dict) else c
             for c in (arch.get("subsystems") or [])]
    comps = [str(c) for c in comps if c]
    return {
        "package_id": ident.get("package_id"),
        "invention_id": ident.get("invention_id"),
        "problem_id": ident.get("problem_id"),
        "run_id": ident.get("run_id"),
        "technology_name": ident.get("technology_name"),
        "domain_family": ident.get("domain_family"),
        "problem_domain_family": ident.get("problem_domain_family"),
        # R443: the canonical problem-context applicability (ONE
        # authority — the engineering specification's decision; the
        # gate CONSUMES it as source so a medical-context package
        # routed to a non-medical ENGINEERING domain is not misread as
        # foreign-domain contamination)
        "applicability_context": (model.get("requirements") or {}).get(
            "context_class"),
        "final_invention_hash": ident.get("final_invention_hash"),
        "problem": (model["problem"].get("user_problem")
                    or model["problem"].get("failure_mode")),
        # the verifier's invention vocabulary source (Gate E/U): the
        # canonical mechanism + architecture, never package text
        "invention": (model["invention"].get("intervention_site")
                      or (model["invention"].get("mechanism") or {}).get(
                          "mechanism") if isinstance(
                          model["invention"].get("mechanism"), dict)
                      else model["invention"].get("mechanism")),
        "mechanism": (model["invention"].get("mechanism") or {}).get(
            "mechanism") if isinstance(
            model["invention"].get("mechanism"), dict) else None,
        "essential_components": comps or None,
    }


def _blocked(result: Dict[str, Any], work: Path, tmp: Path,
             model: Dict[str, Any], stage: str,
             detail: Any, keep_quarantine: bool = True) -> Dict[str, Any]:
    """A blocked build is a first-class outcome: no ZIP at the public
    path, an honest PACKAGE_BUILD_BLOCKED.json in the run dir, and the
    failed tree quarantined for engineering inspection (R440.13)."""
    rec = {
        "state": "PACKAGE_BUILD_BLOCKED",
        "stage": stage,
        "at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run_id": result.get("run_id"),
        "package_id": result.get("package_id"),
        "invention_id": result.get("invention_id"),
        "final_invention_hash": result.get("final_invention_hash"),
        "detail": detail,
    }
    result.update({
        "state": "PACKAGE_BUILD_BLOCKED",
        "zip_emitted": False,
        "buyer_release": False,
        "blocked": True,
        "blocked_record": rec,
        "package_maturity": None,
        "manifest": None,
    })
    try:
        (work / "PACKAGE_BUILD_BLOCKED.json").write_text(
            json.dumps(rec, indent=2, default=str))
    except Exception:  # noqa: BLE001 — record best-effort, block stands
        pass
    if keep_quarantine and tmp.exists():
        try:
            q = work / "PACKAGE_QUARANTINE"
            q.mkdir(exist_ok=True)
            shutil.move(str(tmp), str(q / time.strftime(
                "%Y%m%dT%H%M%SZ", time.gmtime())))
        except Exception:  # noqa: BLE001
            shutil.rmtree(tmp, ignore_errors=True)
    else:
        shutil.rmtree(tmp, ignore_errors=True)
    return result


def _zip_tree(root: Path, dest: Path) -> None:
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(root.rglob("*")):
            if p.is_file():
                zf.write(p, str(Path("TECHNOLOGY_PACKAGE")
                                / p.relative_to(root)))


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

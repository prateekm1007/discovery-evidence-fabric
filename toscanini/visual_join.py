"""visual_join.py — THE machine-verifiable geometry-to-visual join
evaluator (R451-C2.2 §5/§6, hardened by R451-C2.3).

The directive's join contract:

    ENGINEERING GEOMETRY READY
        ↓
    VISUAL INVOCATION RECORD
        ↓
    RENDER
        ↓
    VISUAL GATE
        ↓
    HERO / PRESENTATION SET

Every arrow must be provable from persisted records — a missing arrow
is an explicit, typed state, never silence ("No silent gap"):

  * the engineering geometry is ready but the canonical GLB contract
    is not satisfied (a valid STEP alone never proves the Visual
    Compiler has a canonical GLB to consume)   ->  VISUAL_INPUT_NOT_READY
  * GLB verified, no VISUAL_COMPILER_INVOCATION.json, no render job
    pending                                     ->  INVOCATION_MISSING
    (an explicit join FAILURE)
  * the invocation record exists but the render has not produced its
    record yet                                  ->  INVOCATION_PENDING
  * the invocation occurred and the renderer typed a skip/failure
                                                ->  RENDER_BLOCKED
  * the renderer produced pixels and the gate did not pass
                                                ->  STOPPED_GATE
  * the gate passed but the RELEASE CHAIN fails closed (identity
    mismatch anywhere in the chain, missing required presentation
    artifacts, hero absent, hero source not the canonical GLB)
                                                ->  RELEASE_UNVERIFIED
  * the FULL release chain verifies             ->  VISUAL_READY
  * the invocation claims pixels but no render record exists
                                                ->  RENDER_RECORD_MISSING

R451-C2.3 identity chain (enforced HERE, inside the evaluator — a
mismatch is a fail-closed state, never a later report):

    geometry_spec_sha256   ==  receipt.geometry_spec_sha256
    canonical_glb_sha256   ==  receipt.glb_sha256
                           ==  render_record.source_glb_sha256
    hero source identity   ==  canonical GLB bytes

R451-C2.3 geometry artifact contract (the seven authoritative
conditions for geometry_available authority): a canonical geometry
artifact exists AND is non-zero AND carries a valid artifact identity
AND the generation identities match AND every recorded SHA matches the
bytes on disk AND the engineering authority is explicit AND no
contradicting terminal failure is recorded. A route string such as
"/api/run/x/model" NEVER establishes geometry; a missing engineering
class stays UNKNOWN; legacy boolean-only projections remain readable
but never inherit current ENGINEERING_DEFINED authority.

THE one evaluator (R451-C2.3 §8): the dossier projection AND the
r451_c2_watchdog consume THIS module's state semantics. The watchdog
attacks it with independently authored adversarial fixtures — it does
not implement a second state machine.

PRESENTATION-ONLY (Coder 2 boundary): this module derives state from
canonical records and changes no engineering truth. It WRITES nothing
(Art. IX — certification is observational; the invocation record is
written by the Visual Compiler itself, the job record by the artifact
worker). It never invents a hash, status, or reason (Art. VI): every
field is read from the run's own files or the CIO projection.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# The closed join-state vocabulary. THE one place it is defined; the
# strip, the design tab, and the watchdog all speak it.
VISUAL_JOIN_STATES = (
    "NOT_APPLICABLE",         # engineering visualization does not apply
    "NOT_REACHED",            # no engineering geometry was produced
    "VISUAL_INPUT_NOT_READY",  # engineering geometry ready; the canonical
                              # GLB the visual boundary consumes is not
                              # verifiable (STEP alone never proves it)
    "INVOCATION_PENDING",     # geometry ready; the invocation is in flight
    "INVOCATION_MISSING",     # geometry ready; the invocation never ran —
                              # an EXPLICIT FAILURE (no silent gap)
    "RENDER_BLOCKED",         # invoked; the renderer typed a skip/failure
    "RENDER_RECORD_MISSING",  # invoked as rendered; no record on disk —
                              # record integrity failure
    "STOPPED_GATE",           # rendered; the integrity gate did not pass
    "RELEASE_UNVERIFIED",     # gate passed; the release chain fails closed
                              # (identity mismatch / missing release
                              # artifacts / hero not the canonical GLB)
    "VISUAL_READY",           # the FULL release chain verified
)

RECEIPT_REL = "MODEL/3D/VISUAL_COMPILER_INVOCATION.json"
RENDER_RECORD_REL = "MODEL/3D/render_record.json"
GATE_REL = "MODEL/3D/visual_gate.json"
RENDER_JOB_REL = "MODEL/3D/RENDER_JOB.json"
ARTIFACT_IDENTITY_REL = "MODEL/ARTIFACT_IDENTITY.json"
GEOMETRY_SPEC_REL = "MODEL/GEOMETRY_SPEC.json"
DESIGN_LINEAGE_REL = "MODEL/DESIGN_LINEAGE.json"
HERO_GLB_REL = "MODEL/3D/hero.glb"
HERO_PNG_REL = "MODEL/3D/hero.png"

# render-record statuses that mean the renderer produced pixels
# (ONE vocabulary — the dossier and the watchdog import this tuple)
RENDERER_RAN_STATUSES = ("OK", "SUCCEEDED", "COMPLETE", "PARTIAL")

# receipt statuses that mean the invocation occurred but the renderer
# did not produce pixels (typed skips and typed failures)
_RENDERER_DID_NOT_RUN_PREFIXES = ("RENDER_SKIPPED",)
_RENDERER_DID_NOT_RUN_STATUSES = ("RENDER_FAILED", "RENDER_TIMEOUT",
                                  "INTERRUPTED")

# the run statuses whose stop is infrastructure (Art. LXI) — the same
# class user_state/dossier treat as infrastructure
_INFRA_STATUSES = ("INTERRUPTED", "ERROR_TRANSPORT", "ERROR_BUILD",
                   "ERROR_RUN", "ERROR_STUCK", "RUN_BLOCKED_TRANSPORT")

# gate verdicts that mean the presentation is approved (legacy PASS
# only while no completeness block is declared — the R443 contract)
GATE_PASS_VERDICTS = ("COMPLETE_PASS", "PASS")

# the recorded conceptual classes (never engineering authority)
_CONCEPTUAL_CLASSES = ("SYSTEM_3D", "CONCEPTUAL_3D", "PROCESS_3D")
_ENGINEERING_CLASS = "ENGINEERING_3D"

# the bridge outcomes under which an engineering realization was
# recorded as built (the bridge report DESCRIBES it — the realization
# itself is the verified artifact, R451-C2.3 §3)
BRIDGE_BUILT_OUTCOMES = ("COMPLETED", "ALREADY_COMPLETE",
                         "PACKAGE_ADDED_TO_EXISTING_GEOMETRY",
                         "CONCEPTUAL_FALLBACK")
BRIDGE_GEOMETRY_FAILED = "GEOMETRY_FAILED"
BRIDGE_NOT_APPLICABLE = "NOT_VISUALIZABLE"
CAD_LEDGER_FAILED = ("MODEL_REJECTED_BY_GEOMETRY_GATES",)
CAD_LEDGER_NOT_APPLICABLE = ("NOT_APPLICABLE_NO_GEOMETRY",)
CAD_LEDGER_INFRA = ("BLOCKED_TRANSPORT", "NO_MODEL_NO_LLM")

# the STEP file magic (ISO 10303-21) — a real validity byte check, never
# an extension-only acceptance
_STEP_MAGIC = b"ISO-10303-21"


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if path.is_file():
            data = json.loads(path.read_text())
            return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        pass
    return None


def _sha256_file(path: Path) -> Optional[str]:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


# ---------------------------------------------------------------------------
# THE geometry artifact contract (R451-C2.3 §1) — one implementation,
# two consumers (the dossier projection and the watchdog).
# ---------------------------------------------------------------------------
def resolve_canonical_glb(run_dir: Optional[Path]) -> Optional[Path]:
    """The CURRENT generation's canonical GLB — the same resolution
    order the Visual Compiler itself uses (one authority, all
    consumers). A path string in a projection NEVER establishes the
    artifact; only a real file on disk resolves here."""
    if run_dir is None:
        return None
    model_dir = run_dir / "MODEL"
    lineage = _read_json(run_dir / DESIGN_LINEAGE_REL) or \
        _read_json(model_dir / "DESIGN_LINEAGE.json")
    if lineage:
        for gen in lineage.get("generation_models") or []:
            if gen.get("current") and gen.get("glb"):
                p = run_dir / str(gen["glb"])
                if p.is_file():
                    return p
    identity = _read_json(run_dir / ARTIFACT_IDENTITY_REL) or {}
    id_path = identity.get("glb_path")
    if id_path:
        p = run_dir / str(id_path)
        if p.is_file():
            return p
    if model_dir.is_dir():
        p = model_dir / "engineering_model.glb"
        if p.is_file():
            return p
        glbs = sorted(model_dir.glob("model-*.glb"))
        if glbs:
            return glbs[-1]
    roots = sorted(run_dir.glob("*.glb"))
    return roots[0] if roots else None


def resolve_step_artifacts(run_dir: Optional[Path]) -> List[Path]:
    """The run's STEP artifacts (real files, never route strings)."""
    if run_dir is None:
        return []
    out: List[Path] = []
    model_dir = run_dir / "MODEL"
    for root in (model_dir, run_dir):
        if root.is_dir():
            out.extend(sorted(root.glob("*.step")))
    seen, uniq = set(), []
    for p in out:
        if str(p) not in seen:
            seen.add(str(p))
            uniq.append(p)
    return uniq


def evaluate_geometry_contract(session: Dict[str, Any],
                               run_dir: Optional[Path],
                               geom: Dict[str, Any]) -> Dict[str, Any]:
    """R451-C2.3 §1 — THE artifact contract. The geometry state is
    decided by the recorded engineering CHAIN, verified against the
    bytes on disk:

      geometry_available          a canonical geometry artifact exists,
                                  is non-zero, carries a valid artifact
                                  identity whose generation matches,
                                  every recorded SHA matches the bytes,
                                  and no contradicting terminal failure
                                  is recorded. The ENGINEERING authority
                                  is reported separately — it is
                                  explicit, conceptual, or UNKNOWN.
      geometry_generation_failed  the chain RECORDS a generation failure
                                  (or concluded COMPLETE with only a
                                  parametric DEFINITION and no artifact)
      geometry_not_applicable     the chain RECORDS that geometry does
                                  not apply
      upstream_not_reached        everything else, including every
                                  infrastructure-class block (Art. LXI)

    Route strings ("/api/run/x/model") never establish geometry: the
    artifact must resolve to real bytes under the run directory. A
    missing engineering class is UNKNOWN — never silently engineering.
    A legacy boolean-only projection stays readable as
    geometry_available (that era's recorded fact, Art. XI) but its
    engineering authority is UNKNOWN — it never inherits the current
    ENGINEERING_DEFINED authority (R451-C2.3 §1).
    """
    run_dir = Path(run_dir) if run_dir else None
    if run_dir is not None and not run_dir.exists():
        run_dir = None
    session = session or {}

    glb_route = bool(geom.get("glb"))
    step_route = bool(geom.get("step"))
    # legacy CIO projections (pre-R451-C2.2) carried only the boolean
    # `present` — readable (Art. XI), authority UNKNOWN (R451-C2.3 §1)
    legacy_projection = ("glb" not in geom and "step" not in geom
                         and "parametric_model_present" not in geom)
    legacy_present = legacy_projection and bool(geom.get("present"))

    # ---- resolve the actual artifacts from the run directory ---------
    glb_path = resolve_canonical_glb(run_dir)
    glb_size = glb_path.stat().st_size if glb_path is not None else 0
    glb_bytes_ok = glb_path is not None and glb_size > 0
    glb_sha = _sha256_file(glb_path) if glb_bytes_ok else None
    step_paths = resolve_step_artifacts(run_dir)
    step_ok: List[Path] = []
    for p in step_paths:
        try:
            if p.stat().st_size > 0:
                with p.open("rb") as fh:
                    if fh.read(64).lstrip().startswith(_STEP_MAGIC):
                        step_ok.append(p)
        except OSError:
            continue

    # ---- the recorded identity chain --------------------------------
    identity = _read_json(run_dir / ARTIFACT_IDENTITY_REL) if run_dir \
        else None
    br_identity = (geom.get("artifact_identity") or {}) if isinstance(
        geom.get("artifact_identity"), dict) else {}
    generation_id = geom.get("generation_id") or \
        br_identity.get("generation_id")

    # ---- SHA verification: every RECORDED sha must match the bytes ---
    sha_checks: List[Dict[str, Any]] = []
    recorded_shas = {
        "artifact_identity.geometry_hash":
            (identity or {}).get("geometry_hash"),
        "artifact_identity.glb_disk_sha256":
            (identity or {}).get("glb_disk_sha256"),
        "cio.geometry.glb_sha256": geom.get("glb_sha256"),
        "bridge.artifact_identity.geometry_hash":
            br_identity.get("geometry_hash"),
    }
    any_sha_recorded = False
    sha_mismatch = False
    for source, recorded in recorded_shas.items():
        if not recorded:
            continue
        any_sha_recorded = True
        ok = (glb_sha is not None and str(recorded) == glb_sha)
        sha_checks.append({"source": source, "recorded": str(recorded),
                           "matches_bytes": ok})
        if not ok:
            sha_mismatch = True

    # ---- the engineering authority (explicit / conceptual / UNKNOWN) -
    # R451-C2.3: the authority reads RECORDED identity documents only
    # (MODEL/ARTIFACT_IDENTITY.json, the bridge report's own class
    # fields, the CAD ledger's completion). The CIO's DERIVED class
    # field is never an authority source — for a bare GLB it is a
    # filename-derived inference (exactly what this round removes).
    class_sources: List[str] = []
    for src, val in (
            ("artifact_identity.visualizability_class",
             (identity or {}).get("visualizability_class")),
            ("bridge.artifact_identity.visualizability_class",
             br_identity.get("visualizability_class"))):
        if val:
            class_sources.append(f"{src}={val}")
    bridge_report = _read_json(run_dir / "BRIDGE_REPORT.json") \
        if run_dir else None
    for src, val in (
            ("bridge_report.visualizability_class",
             (bridge_report or {}).get("visualizability_class")),
            ("bridge_report.geometry.visualizability_class",
             ((bridge_report or {}).get("geometry") or {})
             .get("visualizability_class"))):
        if val:
            class_sources.append(f"{src}={val}")
    bridge_outcome = (bridge_report or {}).get("outcome") or \
        geom.get("bridge_outcome")
    cad_outcome = None
    if run_dir is not None:
        ledger = _read_json(run_dir / "CAD_PIPELINE_LEDGER.json")
        cad_outcome = (ledger or {}).get("outcome") \
            or (ledger or {}).get("status")
    if not cad_outcome:
        cad_outcome = geom.get("cad_pipeline_status") or None
    eng_spec_present = bool(run_dir and
                            (run_dir / "ENGINEERING_SPECIFICATION.json")
                            .is_file())

    up_classes = [c for c in class_sources
                  if _ENGINEERING_CLASS in c.upper()]
    concept_classes = [c for c in class_sources
                       if any(k in c.upper()
                              for k in _CONCEPTUAL_CLASSES)]
    if sha_mismatch:
        # the recorded identity contradicts the bytes on disk — the
        # artifact fails closed and no authority survives it
        engineering_authority = "UNKNOWN"
        artifact_verified = False
        verify_detail = ("a recorded geometry SHA does not match the "
                         "artifact bytes on disk — identity chain "
                         "broken (fail closed)")
    elif glb_bytes_ok or step_ok:
        artifact_verified = True
        if up_classes and not concept_classes:
            engineering_authority = "ENGINEERING"
        elif concept_classes:
            engineering_authority = "CONCEPTUAL"
        elif cad_outcome == "COMPLETED":
            # the CAD pipeline's own recorded completion — the recorded
            # engineering authority for STEP-era realizations
            engineering_authority = "ENGINEERING"
        else:
            engineering_authority = "UNKNOWN"
        verify_detail = None
    else:
        artifact_verified = False
        engineering_authority = "UNKNOWN"
        if legacy_present:
            verify_detail = ("the recorded projection carries only a "
                             "boolean presence flag — no verifiable "
                             "geometry artifact (presence alone never "
                             "establishes geometry)")
        elif glb_route or step_route:
            verify_detail = ("the projection records a geometry route "
                             "but no verifiable artifact resolves under "
                             "the run directory — a route string is "
                             "never the artifact")
        else:
            verify_detail = ("no verifiable geometry artifact resolves "
                             "under the run directory")

    # ---- generation identity must match when both sides record it ----
    identity_generation = (identity or {}).get("generation_id") or \
        br_identity.get("generation_id")
    generation_mismatch = bool(
        identity_generation and generation_id
        and str(identity_generation) != str(generation_id))
    if generation_mismatch:
        artifact_verified = False
        engineering_authority = "UNKNOWN"
        verify_detail = ("the recorded generation identity does not "
                         "match the artifact identity (fail closed)")

    # ---- contradicting terminal failure ------------------------------
    chain_failure = (bridge_outcome == BRIDGE_GEOMETRY_FAILED
                     or cad_outcome in CAD_LEDGER_FAILED)
    chain_not_applicable = (bridge_outcome == BRIDGE_NOT_APPLICABLE
                            or cad_outcome in CAD_LEDGER_NOT_APPLICABLE)
    chain_infra = cad_outcome in CAD_LEDGER_INFRA
    pm_only = bool(geom.get("parametric_model_present")) and \
        not glb_bytes_ok and not step_ok and not legacy_present

    # ---- the geometry-side state (the six-value vocabulary) ----------
    if artifact_verified and not chain_failure:
        state = "geometry_available"
    elif chain_failure:
        state = "geometry_generation_failed"
    elif chain_not_applicable:
        state = "geometry_not_applicable"
    elif chain_infra:
        # Art. LXI: an infrastructure block is never a failure
        state = "upstream_not_reached"
    elif pm_only:
        # the engineering DEFINITION exists, the geometry ARTIFACT does
        # not — the honest classification depends on the run's own
        # terminal state (a COMPLETE run concluded without producing
        # geometry; a live or infra-stopped run simply has not)
        status = str(session.get("status") or "")
        state = "geometry_generation_failed" if status == "COMPLETE" \
            else "upstream_not_reached"
    else:
        state = "upstream_not_reached"

    # ---- the two boundary states (R451-C2.3 §2) ----------------------
    # ENGINEERING_GEOMETRY_READY: the verified artifact + explicit
    # engineering authority + no contradicting failure. A valid STEP
    # may establish this.
    engineering_geometry_ready = bool(
        artifact_verified and not chain_failure
        and engineering_authority == "ENGINEERING")
    # VISUAL_INPUT_READY: the canonical GLB contract — what the Visual
    # Compiler actually consumes. A STEP never satisfies it by itself.
    visual_input_ready = bool(glb_bytes_ok and glb_sha and not sha_mismatch
                              and not generation_mismatch
                              and not chain_failure)
    if visual_input_ready:
        visual_input_basis = (f"canonical GLB {glb_path.name} verified "
                              f"({glb_size} bytes, sha256 on record)")
    elif engineering_geometry_ready:
        visual_input_basis = ("the engineering geometry is verified but "
                              "no canonical GLB resolves under the run "
                              "directory — the visual boundary contract "
                              "is not satisfied by a STEP alone")
    elif glb_route or legacy_present:
        visual_input_basis = ("the projection records geometry presence "
                              "but no verifiable canonical GLB resolves "
                              "under the run directory")
    else:
        visual_input_basis = None

    return {
        "geometry_state": state,
        "geometry_state_detail": verify_detail,
        "engineering_authority": engineering_authority,
        "artifact_verified": artifact_verified,
        "verification": {
            "glb_resolved": str(glb_path) if glb_path else None,
            "glb_bytes": glb_size,
            "glb_sha256_measured": glb_sha,
            "step_files_verified": [str(p) for p in step_ok],
            "sha_checks": sha_checks,
            "any_sha_recorded": any_sha_recorded,
            "sha_mismatch": sha_mismatch,
            "generation_mismatch": generation_mismatch,
            "identity_present": identity is not None or bool(br_identity),
            "class_sources": class_sources,
        },
        "engineering_geometry_ready": engineering_geometry_ready,
        "visual_input_ready": visual_input_ready,
        "visual_input_basis": visual_input_basis,
        "geometry_spec_sha256": _sha256_file(
            run_dir / GEOMETRY_SPEC_REL)
        if run_dir and (run_dir / GEOMETRY_SPEC_REL).is_file() else None,
        "canonical_glb": str(glb_path) if glb_path else None,
        "canonical_glb_sha256": glb_sha,
        # recorded-chain facts (the dossier's detail strings build on
        # these; the watchdog consumes them directly)
        "has_artifact": artifact_verified or legacy_present,
        "legacy_projection": legacy_projection,
        "legacy_present": legacy_present,
        "glb_route": glb_route,
        "step_route": step_route,
        "pm_only": pm_only,
        "glb": glb_bytes_ok,
        "step": bool(step_ok),
        "bridge_outcome": bridge_outcome,
        "cad_outcome": cad_outcome,
        "eng_spec_present": eng_spec_present,
        "chain_failure": chain_failure,
        "chain_not_applicable": chain_not_applicable,
        "chain_infra": chain_infra,
    }


def read_invocation_receipt(run_dir: Optional[Path]) -> Optional[Dict]:
    """The invocation receipt in EITHER field era (Art. XI: historical
    1.0.0 records on existing runs stay readable; the writer emits
    1.1.0 only). Normalizes to the 1.1.0 names:
    invocation_status / glb_sha256 / visual_compiler_version."""
    receipt = _read_json(Path(run_dir) / RECEIPT_REL) if run_dir else None
    if not receipt:
        return None
    norm = dict(receipt)
    norm.setdefault("invocation_status",
                    receipt.get("status") or receipt.get("invocation_status"))
    norm.setdefault("glb_sha256",
                    receipt.get("glb_sha256")
                    or receipt.get("canonical_glb_sha256"))
    norm.setdefault("visual_compiler_version",
                    receipt.get("visual_compiler_version")
                    or receipt.get("compiler_version"))
    return norm


def _job_pending(run_dir: Optional[Path]) -> Tuple[bool, Optional[str]]:
    """The async render job's own record — the invocation was REQUESTED
    and has not spoken yet (RUNNING), or was interrupted and is owed a
    recovery re-enqueue (INTERRUPTED). Both are explicit pending
    states, never silence."""
    job = _read_json(Path(run_dir) / RENDER_JOB_REL) if run_dir else None
    status = str((job or {}).get("status") or "")
    if status in ("RUNNING", "INTERRUPTED"):
        return True, status
    return False, status or None


# ---------------------------------------------------------------------------
# THE release chain (R451-C2.3 §5/§6) — VISUAL_READY requires every rung
# ---------------------------------------------------------------------------
def verify_release_chain(run_dir: Optional[Path],
                         glb_path: Optional[Path] = None,
                         contract: Optional[Dict[str, Any]] = None,
                         ) -> Dict[str, Any]:
    """The Article LXXII release chain, verified from the run's own
    records and bytes. VISUAL_READY requires AT MINIMUM:

      canonical GLB identity verified
        -> invocation receipt identity verified
        -> render record identity verified
        -> gate PASS
        -> required presentation artifact set exists
        -> hero exists
        -> hero source identity == the canonical GLB

    Anything missing or mismatching: not VISUAL_READY (fail closed).
    Missing evidence is recorded per rung (Art. XXV — unknown stays
    unknown); it never becomes a pass. Observational: reads only."""
    run_dir = Path(run_dir) if run_dir else None
    rungs: List[Dict[str, Any]] = []
    contract = contract or {}

    # ---- rung 1: canonical GLB identity ------------------------------
    glb = glb_path if glb_path is not None \
        else resolve_canonical_glb(run_dir)
    glb_sha = _sha256_file(glb) if glb is not None and \
        glb.stat().st_size > 0 else None
    rungs.append({
        "rung": "canonical_glb_identity",
        "pass": bool(glb is not None and glb_sha),
        "detail": (f"{glb.name} ({glb.stat().st_size} bytes)"
                   if glb is not None and glb_sha else
                   "no non-empty canonical GLB resolves under the run "
                   "directory"),
    })

    receipt = read_invocation_receipt(run_dir)
    # ---- rung 2: invocation receipt identity ------------------------
    receipt_ok = False
    detail = "no invocation receipt on disk"
    if receipt:
        rec_glb = receipt.get("glb_sha256")
        rec_run = receipt.get("run_id")
        problems = []
        if not rec_glb:
            problems.append("receipt carries no glb_sha256")
        elif rec_glb != glb_sha:
            problems.append("receipt glb_sha256 != canonical GLB bytes")
        if rec_run and run_dir is not None and rec_run != run_dir.name:
            problems.append("receipt run_id != the run it sits in")
        spec_path = run_dir / GEOMETRY_SPEC_REL if run_dir else None
        spec_sha = _sha256_file(spec_path) if spec_path and \
            spec_path.is_file() else None
        rec_spec = receipt.get("geometry_spec_sha256")
        if spec_sha and rec_spec and rec_spec != spec_sha:
            problems.append("receipt geometry_spec_sha256 != the "
                            "GEOMETRY_SPEC.json bytes (identity chain "
                            "broken)")
        elif spec_sha and not rec_spec:
            problems.append("GEOMETRY_SPEC.json exists but the receipt "
                            "carries no geometry_spec_sha256")
        elif rec_spec and not spec_sha:
            problems.append("receipt names a geometry spec sha but no "
                            "GEOMETRY_SPEC.json exists on disk")
        receipt_ok = not problems
        detail = "; ".join(problems) if problems else \
            "receipt identity == canonical GLB identity"
    rungs.append({"rung": "invocation_receipt_identity",
                  "pass": receipt_ok, "detail": detail})

    # ---- rung 3: render record identity ------------------------------
    record = _read_json(run_dir / RENDER_RECORD_REL) if run_dir else None
    record_ok = False
    detail = "no persisted render record on disk"
    if record:
        src = record.get("source_glb_sha256")
        if not src:
            detail = ("the render record predates the source_glb_sha256 "
                      "field — the render-source link is UNPROVEN")
        elif src != glb_sha:
            detail = ("render_record.source_glb_sha256 != the canonical "
                      "GLB bytes — source substitution fail closed")
        else:
            record_ok = True
            detail = "render record source == canonical GLB bytes"
    rungs.append({"rung": "render_record_identity",
                  "pass": record_ok, "detail": detail})

    # ---- rung 4: gate PASS -------------------------------------------
    gate = _read_json(run_dir / GATE_REL) if run_dir else None
    verdict = (gate or {}).get("verdict")
    gate_ok = verdict in GATE_PASS_VERDICTS
    rungs.append({"rung": "gate_pass",
                  "pass": gate_ok,
                  "detail": f"gate verdict {verdict or 'absent'}"})

    # ---- rung 5: the required presentation artifact set --------------
    set_ok = False
    detail = "no render record — the required set cannot be derived"
    if record:
        node_count = int(((record.get("scene_spec") or {}).get("model")
                          or {}).get("node_count") or 0)
        try:
            from discovery_fabric.engine.visual_compiler import \
                visual_set  # noqa: E402 — read-only ladder definition
            required = visual_set.required_artifacts(
                node_count, visual_set.DEFAULT_TURNTABLE_FRAMES)
        except Exception:  # noqa: BLE001 — typed degradation below
            required = None
        if required is None:
            detail = "the visual-set ladder definition is unavailable"
        else:
            three_d = run_dir / "MODEL" / "3D" if run_dir else None
            missing = []
            if three_d is None or not three_d.is_dir():
                missing = list(required["required"])
            else:
                for name in required["required"]:
                    p = three_d / name
                    if not p.is_file() or p.stat().st_size == 0:
                        missing.append(name)
            set_ok = not missing
            detail = ("the required presentation set is on disk"
                      if set_ok else
                      f"missing required presentation artifacts: "
                      f"{missing[:8]}")
    rungs.append({"rung": "presentation_artifact_set",
                  "pass": set_ok, "detail": detail})

    # ---- rung 6: hero exists ------------------------------------------
    hero = run_dir / HERO_PNG_REL if run_dir else None
    hero_ok = bool(hero and hero.is_file() and hero.stat().st_size > 0)
    rungs.append({"rung": "hero_exists", "pass": hero_ok,
                  "detail": "hero.png on disk" if hero_ok else
                  "hero.png missing or empty"})

    # ---- rung 7: hero source identity == canonical GLB ---------------
    # The hero's SOURCE is what the renderer consumed: proven by the
    # render record's source link (rung 3). An exported hero.glb is a
    # scene artifact whose integrity is proven against the render
    # record's OWN recorded view hash (never against an assumption
    # that the export is byte-identical to the canonical GLB).
    hero_src_ok = False
    detail = "no canonical GLB to compare against"
    if glb is not None and glb_sha:
        record = _read_json(run_dir / RENDER_RECORD_REL) if run_dir \
            else None
        src = (record or {}).get("source_glb_sha256")
        hero_glb = run_dir / HERO_GLB_REL if run_dir else None
        if src == glb_sha:
            hero_src_ok = True
            detail = ("the hero's rendered source == the canonical GLB "
                      "bytes (render record source identity)")
            if hero_glb is not None and hero_glb.is_file() and \
                    hero_glb.stat().st_size > 0:
                recorded_view = ((record or {}).get("views") or {}).get(
                    "hero.glb") or {}
                recorded_sha = (recorded_view or {}).get("sha256") \
                    if isinstance(recorded_view, dict) else None
                if recorded_sha:
                    disk_sha = _sha256_file(hero_glb)
                    if disk_sha != recorded_sha:
                        hero_src_ok = False
                        detail = ("the exported hero.glb bytes do not "
                                  "match the render record's own view "
                                  "hash — hero provenance fails closed")
                else:
                    hero_src_ok = False
                    detail = ("hero.glb is exported but the render "
                              "record carries no hash for it — the "
                              "hero provenance is UNPROVEN")
        else:
            detail = ("the render record's source identity is not the "
                      "canonical GLB — hero source identity fails "
                      "closed")
    rungs.append({"rung": "hero_source_identity",
                  "pass": hero_src_ok, "detail": detail})

    verified = all(r["pass"] for r in rungs)
    first_failure = next((r["rung"] for r in rungs if not r["pass"]),
                         None)
    return {"verified": verified, "rungs": rungs,
            "first_failure": first_failure,
            "canonical_glb": str(glb) if glb else None,
            "canonical_glb_sha256": glb_sha}


def evaluate_visual_join(session: Dict[str, Any],
                         geom: Dict[str, Any],
                         renders: Dict[str, Any],
                         running: bool,
                         engineering_geometry_ready: bool,
                         geometry_state: str,
                         contract: Optional[Dict[str, Any]] = None,
                         ) -> Dict[str, Any]:
    """Derive the join state from canonical records — THE one evaluator
    (R451-C2.3 §8: the dossier and the watchdog consume THIS; the
    watchdog attacks it with adversarial fixtures instead of deriving
    its own second state).

    session / geom / renders  — the same inputs the dossier's design
                                tab already holds (the session record,
                                the CIO geometry block, the CIO renders
                                block).
    engineering_geometry_ready — the artifact contract's engineering
                                verdict (verified artifact + explicit
                                ENGINEERING authority).
    geometry_state            — the geometry-side state the contract
                                produced (the join is defined only when
                                geometry is available).
    contract                  — the full contract dict when the caller
                                holds it (visual_input_ready /
                                canonical GLB path ride in).

    `visual_join_state` None means UNDECIDED — no records were
    readable; the caller renders from the CIO renders block (the
    pre-receipt fallback) rather than inventing a state (Art. XXV).
    """
    run_dir = Path(session["run_dir"]) if session.get("run_dir") else None
    if run_dir is not None and not run_dir.exists():
        run_dir = None
    # THE evaluator self-serves its contract when the caller did not
    # hand one (the watchdog and direct calls get the SAME byte-verified
    # inputs the dossier consumes — one evaluator, R451-C2.3 §8)
    if contract is None:
        contract = evaluate_geometry_contract(session, run_dir, geom)
    # fail closed against a stale optimistic caller: BOTH the caller's
    # engineering verdict and the contract's must say ready
    engineering_geometry_ready = bool(engineering_geometry_ready) and \
        bool(contract.get("engineering_geometry_ready"))
    receipt = read_invocation_receipt(run_dir)
    render_record = _read_json(Path(run_dir) / RENDER_RECORD_REL) \
        if run_dir else None
    gate = _read_json(Path(run_dir) / GATE_REL) if run_dir else None
    visual_input_ready = bool(contract.get("visual_input_ready"))
    glb_path = Path(contract["canonical_glb"]) \
        if contract.get("canonical_glb") else None

    result: Dict[str, Any] = {
        "visual_join_state": None,
        "visual_join_detail": None,
        "visual_join_cause": None,
        "invocation_present": receipt is not None,
        "invocation_status": (receipt or {}).get("invocation_status"),
        "render_record_present": render_record is not None,
        "gate_verdict": (gate or {}).get("verdict")
        or ((renders.get("visual_gate") or {}).get("verdict")
            if isinstance(renders.get("visual_gate"), dict) else None),
        "pending_render_job": None,
        "release_chain": None,
    }

    # ---- the join is defined only downstream of geometry --------------
    if geometry_state in ("geometry_not_applicable",):
        result["visual_join_state"] = "NOT_APPLICABLE"
        result["visual_join_detail"] = \
            "engineering visualization is not applicable to this invention"
        return result
    if geometry_state != "geometry_available":
        # upstream_not_reached / geometry_generation_failed: the join
        # has no geometry to invoke. (Legacy render-side states are
        # passed through undecided — the caller's renders-block
        # fallback owns them for pre-receipt payloads.)
        result["visual_join_state"] = ("NOT_REACHED"
                                       if geometry_state != "" else None)
        return result
    if not engineering_geometry_ready:
        # R451-C2.3: geometry presence without the explicit ENGINEERING
        # authority never drives the join — the artifact contract's
        # authority verdict is recorded, nothing is claimed
        result["visual_join_state"] = None
        result["visual_join_detail"] = contract.get(
            "geometry_state_detail") or None
        return result

    if run_dir is None and receipt is None:
        # no run directory to read (session-only projection): the join
        # cannot verify the invocation from records — undecided; the
        # caller falls back to the CIO renders block (pre-receipt era)
        result["visual_join_state"] = None
        return result

    # ---- the visual input boundary (R451-C2.3 §2) ---------------------
    if not visual_input_ready:
        # engineering geometry ready, the canonical GLB contract is
        # not satisfied — a valid STEP alone never proves the Visual
        # Compiler has a canonical GLB to consume
        result["visual_join_state"] = "VISUAL_INPUT_NOT_READY"
        result["visual_join_detail"] = contract.get("visual_input_basis") \
            or ("the canonical GLB the visual boundary consumes is not "
                "verifiable under the run directory")
        return result

    # geometry + visual input are ready: the invocation side decides ----
    if receipt is not None:
        status = str(result["invocation_status"] or "")
        if status in RENDERER_RAN_STATUSES:
            if render_record is None:
                # the invocation claims pixels; the record is absent —
                # a record-integrity failure, never read as success
                # (Art. XXIV: the record, not the claim, is the proof)
                result["visual_join_state"] = "RENDER_RECORD_MISSING"
                result["visual_join_detail"] = (
                    "the invocation record says the renderer produced "
                    "pixels but no render record exists on disk — "
                    "recorded as a join integrity failure")
                return result
            verdict = result["gate_verdict"]
            if verdict in GATE_PASS_VERDICTS:
                # R451-C2.3 §5: the gate pass alone is NOT visual
                # readiness — the FULL release chain must verify
                chain = verify_release_chain(run_dir, glb_path, contract)
                result["release_chain"] = chain
                if chain["verified"]:
                    result["visual_join_state"] = "VISUAL_READY"
                    result["visual_join_detail"] = None
                else:
                    result["visual_join_state"] = "RELEASE_UNVERIFIED"
                    result["visual_join_detail"] = (
                        "the gate passed but the release chain fails "
                        f"closed at '{chain['first_failure']}' — not "
                        f"visual ready")
                return result
            if verdict is not None:
                result["visual_join_state"] = "STOPPED_GATE"
                result["visual_join_detail"] = (
                    f"the render completed but the presentation "
                    f"integrity gate returned {verdict}")
                return result
            # a rendered record without any gate verdict: the gate
            # contract requires one — fail closed to STOPPED_GATE with
            # the honest detail (the gate never spoke)
            result["visual_join_state"] = "STOPPED_GATE"
            result["visual_join_detail"] = (
                "the render record exists but no presentation "
                "integrity gate verdict is recorded — fail closed")
            return result
        if status.startswith(_RENDERER_DID_NOT_RUN_PREFIXES) or \
                status in _RENDERER_DID_NOT_RUN_STATUSES:
            cause_detail = (receipt.get("skip_reason")
                            or f"the renderer recorded {status or 'UNKNOWN'}")
            result["visual_join_state"] = "RENDER_BLOCKED"
            result["visual_join_detail"] = cause_detail
            # the typed cause from the receipt's OWN status vocabulary
            # (never text-matched from the reason): no renderer/deps in
            # the environment -> renderer_unavailable; capacity/infra
            # skips and transport-class failures -> infrastructure;
            # a renderer that tried and failed -> renderer_unavailable
            if status in ("RENDER_SKIPPED_NO_RENDERER",
                          "RENDER_SKIPPED_NO_RENDER_NODE",
                          "RENDER_SKIPPED_NO_CHROME",
                          "RENDER_SKIPPED_THREE",
                          "RENDER_FAILED", "RENDER_TIMEOUT") or \
                    "DEPS" in status:
                result["visual_join_cause"] = "renderer_unavailable"
            else:
                result["visual_join_cause"] = "infrastructure"
            return result
        # an invocation record whose status is unknown/pending — the
        # boundary was reached; the renderer has not spoken
        result["visual_join_state"] = "INVOCATION_PENDING"
        result["visual_join_detail"] = (
            f"the visual compiler invocation is recorded "
            f"({status or 'status not recorded'}) and the render has "
            f"not produced its verdict yet")
        return result

    # no receipt: was the invocation requested (async job) or missed? ----
    pending, job_status = _job_pending(run_dir)
    result["pending_render_job"] = job_status
    if pending:
        result["visual_join_state"] = "INVOCATION_PENDING"
        result["visual_join_detail"] = (
            f"the presentation render job is {job_status} — the "
            f"geometry-to-visual invocation is in flight (explicit "
            f"pending, never a silent gap)")
        return result
    if running:
        # the run is still executing — the join legitimately has not
        # been reached yet (the bridge invokes the renderer in the
        # worker / requests the async job at the end of the run)
        result["visual_join_state"] = "INVOCATION_PENDING"
        result["visual_join_detail"] = (
            "the investigation is still executing — the "
            "geometry-to-visual invocation follows the engineering "
            "geometry")
        return result
    # terminal run, geometry ready, no invocation record, no pending
    # job: THE no-silent-gap failure (R451-C2.2 §5) — recorded as the
    # explicit failure it is, never read as "render not needed"
    result["visual_join_state"] = "INVOCATION_MISSING"
    result["visual_join_detail"] = (
        "the engineering geometry is ready but no visual invocation "
        "record exists and no render job is pending — the "
        "geometry-to-visual join did not run (explicit join failure)")
    return result


def join_cause(join_state: Optional[str],
               cause: Optional[str]) -> Tuple[str, str]:
    """The join state -> (geometry_state, presentation_cause) for the
    render-related join states — the design tab consumes THIS pair for
    the States C/D/E decision (the cause is the receipt's own typed
    vocabulary, never text-matched). Callers keep their own
    geometry-side states for the non-render joins.
    """
    if join_state == "VISUAL_READY":
        return "visual_complete", ""
    if join_state == "STOPPED_GATE":
        return "visual_render_failed", "gate_not_passed"
    if join_state == "RELEASE_UNVERIFIED":
        return "visual_render_failed", "release_unverified"
    if join_state == "RENDER_RECORD_MISSING":
        return "visual_render_failed", cause or "renderer_unavailable"
    if join_state == "RENDER_BLOCKED":
        return "visual_render_failed", cause or "renderer_unavailable"
    if join_state == "VISUAL_INPUT_NOT_READY":
        return "geometry_available", "visual_input_missing"
    if join_state == "INVOCATION_MISSING":
        return "geometry_available", "not_attempted"
    if join_state == "INVOCATION_PENDING":
        return "geometry_available", "rendering_in_progress"
    return "", ""

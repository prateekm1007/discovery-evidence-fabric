"""visual_join.py — THE machine-verifiable geometry-to-visual join
evaluator (R451-C2.2 §5/§6, hardened by R451-C2.3, certified by
R451-C2.4, sovereignty-hardened by R451-C2.5, authority-closed by
R451-C2.6).

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

R451-C2.4 certification contract: ARTIFACT IDENTITY IS MANDATORY.
geometry_available requires ALL NINE conditions — the canonical
artifact exists AND is non-zero AND a valid artifact identity exists
AND the identity carries the required SHA AND the SHA equals the
actual bytes AND a generation ID exists AND the generation matches
AND the engineering authority is EXPLICIT (a recorded verdict from
the identity documents — UNKNOWN is not explicit) AND no
contradicting terminal failure is recorded. Missing ANY mandatory
proof: not success. A GLB whose bytes merely hash correctly is NOT
certified: the format itself is validated (glTF magic, version 2,
declared length == file size), and the artifact must be NAMED by a
recorded identity document — a filename that merely looks right
("engineering_model.glb", "model-001.glb") is a DIAGNOSTIC candidate,
never a certification (artifact DISCOVERY and artifact CERTIFICATION
are separate: resolve_canonical_glb locates, certified_canonical_glb
certifies). The receipt lineage is mandatory for VISUAL_READY:
receipt.geometry_spec_sha256 must EXIST and equal the spec file
bytes, and the generation identity must hold three ways (artifact
generation == receipt generation == current generation).

THE one evaluator (R451-C2.3 §8): the dossier projection AND the
r451_c2_watchdog consume THIS module's state semantics. The watchdog
attacks it with independently authored adversarial fixtures — it does
not implement a second state machine.

R451-C2.5 PERSISTED IDENTITY SOVEREIGNTY (§3): certification traces
to PERSISTED identity documents only — DESIGN_LINEAGE.json's
current-generation entry or ARTIFACT_IDENTITY.json (the explicit
canonical persisted equivalents). The projection's carried
geom.artifact_identity object and generation field are DIAGNOSTICS:
they may contradict the persisted chain (fail closed) and they are
reported as diagnostics, but they can never name the artifact,
certify a SHA, state the authority class, or anchor the current
generation. A forged geom object carrying a complete artifact
identity certifies nothing when the persisted document is absent.

R451-C2.5 STRUCTURAL GLB VALIDITY (§4): glb_format_check proves the
container's own structure — the header (magic, version 2, declared
length == file size), the chunk framing (each chunk's declared length
fits the container; the first chunk is the JSON chunk), and the JSON
structure (the JSON chunk parses; asset.version is "2.0"). A valid
header over malformed internal structure never certifies. Honest
scope: this is container-level structural validity — the semantic
render verification remains the Visual Quality Gate's job downstream
(Article LXXII); this check never claims mesh/buffer semantics.

R451-C2.6 — THE AUTHORITY CLOSURE (the last hardening round):

  §2 THE INDEPENDENT PERSISTED CURRENT-GENERATION ANCHOR: the ONE
  canonical persisted current-generation source is DESIGN_LINEAGE
  .json's current-generation entry (its own generation_id when the
  entry records one, else the entry's recorded generation number
  normalized through the pipeline's own gen-<n> convention). The
  artifact generation is NEVER its own current-generation anchor:
  current_generation = artifact_generation is never inferred. The
  triple identity is mandatory — artifact generation == receipt
  generation == the independent persisted current generation — and a
  missing anchor fails closed at every boundary: the certification
  never completes (the artifact stays geometry_unverified with an
  UNKNOWN authority), and the release chain's generation rung fails
  (RELEASE_UNVERIFIED).

  §3 verify_release_chain IS SOVEREIGN: the chain independently
  obtains the CERTIFIED canonical artifact through the persisted
  identity chain (certified_canonical_glb). A caller-provided glb_path
  is a DIAGNOSTIC cross-check only — it may agree (recorded) or
  contradict (fails closed), and it can never weaken the persisted-
  identity requirement. The diagnostic locator's filename fallbacks
  never satisfy a rung (discovery and certification remain separate).

  §4 THE RENDERER-SUCCESS RECORDS CROSS-CHECK: the invocation
  receipt's status, the render record's own status, and the gate must
  agree on what happened. The production writer copies the record's
  status into the receipt verbatim, so a disagreement between the two
  success records is tampering or forgery — the rung fails closed and
  neither contradiction (receipt OK / record FAILED, or the reverse)
  can produce VISUAL_READY.

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
import struct
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

# the glTF binary container magic — the deterministic GLB format check
# (R451-C2.4 §3, upgraded to STRUCTURAL validation R451-C2.5 §4): a
# file whose bytes hash correctly is still not a GLB unless the
# container's structure itself is valid
_GLB_MAGIC = b"glTF"
_GLB_JSON_CHUNK = b"JSON"
_GLB_BIN_CHUNK = b"BIN\x00"


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


def glb_format_check(path: Path) -> Dict[str, Any]:
    """R451-C2.4 §3, upgraded R451-C2.5 §4 — THE deterministic
    STRUCTURAL GLB validity check (no loaders, no interpretation — the
    container's own bytes):
      * the file is at least the 12-byte glTF header
      * bytes 0..4 are the magic b"glTF"
      * the version field (uint32 LE at offset 4) is 2
      * the declared length (uint32 LE at offset 8) equals the file
        size on disk (a truncated or padded container fails)
      * CHUNK FRAMING: walking chunks from offset 12, every chunk's
        8-byte sub-header (uint32 LE length + 4-byte type) fits inside
        the container; the FIRST chunk is the JSON chunk (0x4E4F534A);
        chunk lengths do not overrun the declared container length
      * JSON STRUCTURE: the JSON chunk decodes as UTF-8 and parses as
        a JSON object carrying asset.version == "2.0" (the glTF 2.0
        spec-mandatory asset block)
      * a BIN chunk (0x004E4942), when present, is 4-byte aligned (the
        spec's padding requirement) and never precedes the JSON chunk
    A correct hash over INVALID bytes must never certify: the header
    alone is not a proof — a valid header over a malformed internal
    structure (a BIN first chunk, corrupt JSON, a chunk that overruns
    the container) FAILS here.
    Honest scope: this establishes container-level structural
    validity — header + chunk framing + JSON structure. It does NOT
    validate mesh/buffer/accessor semantics (the presentation's
    semantic verification remains the Visual Quality Gate's rendered
    measurement, Article LXXII)."""
    result = {"valid": False, "detail": "file missing"}
    try:
        size = path.stat().st_size
    except OSError:
        return result
    if size < 12:
        result["detail"] = f"file is {size} bytes — smaller than the " \
                           "12-byte glTF header"
        return result
    try:
        data = path.read_bytes()
    except OSError:
        result["detail"] = "container unreadable"
        return result
    if data[0:4] != _GLB_MAGIC:
        result["detail"] = ("bytes do not begin with the glTF magic — "
                            "this is not a GLB container")
        return result
    version, declared = struct.unpack("<II", data[4:12])
    if version != 2:
        result["detail"] = f"glTF version {version} is not 2"
        return result
    if declared != size:
        result["detail"] = (f"declared container length {declared} != "
                            f"{size} bytes on disk — truncated or "
                            "padded container")
        return result
    # ---- chunk framing (R451-C2.5 §4) -------------------------------
    offset = 12
    first_chunk = True
    seen_json = False
    json_bytes: Optional[bytes] = None
    while offset < declared:
        if offset + 8 > declared:
            result["detail"] = (f"chunk header at offset {offset} "
                                "overruns the container — malformed "
                                "chunk framing")
            return result
        chunk_len, chunk_type = struct.unpack("<I4s",
                                              data[offset:offset + 8])
        offset += 8
        if offset + chunk_len > declared:
            result["detail"] = (f"chunk of {chunk_len} bytes at offset "
                                f"{offset} overruns the declared "
                                "container length — malformed chunk "
                                "framing")
            return result
        if first_chunk:
            if chunk_type != _GLB_JSON_CHUNK:
                result["detail"] = ("the first chunk is not the JSON "
                                    "chunk — malformed GLB structure")
                return result
            first_chunk = False
            seen_json = True
            json_bytes = data[offset:offset + chunk_len]
        elif chunk_type == _GLB_BIN_CHUNK:
            if chunk_len % 4 != 0:
                result["detail"] = ("the BIN chunk length is not "
                                    "4-byte aligned — malformed GLB "
                                    "structure")
                return result
        offset += chunk_len
    if not seen_json:
        result["detail"] = ("the container carries no JSON chunk — "
                            "malformed GLB structure")
        return result
    # ---- JSON structure (R451-C2.5 §4) -------------------------------
    try:
        doc = json.loads(json_bytes.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        result["detail"] = ("the JSON chunk does not parse as JSON — "
                            "malformed GLB structure")
        return result
    if not isinstance(doc, dict):
        result["detail"] = ("the JSON chunk is not a JSON object — "
                            "malformed GLB structure")
        return result
    asset = doc.get("asset")
    if not isinstance(asset, dict) or str(asset.get("version")) != "2.0":
        result["detail"] = ("the glTF JSON carries no asset.version "
                            "\"2.0\" — not a valid glTF 2.0 "
                            "structure")
        return result
    return {"valid": True, "detail": f"structurally valid glTF 2.0 "
                                     f"binary ({size} bytes, chunk "
                                     "framing + JSON structure "
                                     "verified)"}


# ---------------------------------------------------------------------------
# THE geometry artifact contract (R451-C2.3 §1) — one implementation,
# two consumers (the dossier projection and the watchdog).
# ---------------------------------------------------------------------------
def resolve_canonical_glb(run_dir: Optional[Path]) -> Optional[Path]:
    """R451-C2.4 §4 — the DIAGNOSTIC locator only. Locates candidate
    GLB files under the run directory (the same resolution order the
    Visual Compiler itself uses) so diagnostics and record invariants
    can name a candidate. It NEVER certifies canonicality: a filename
    that looks right ("engineering_model.glb", "model-001.glb", a
    root-level glob) is a candidate, not the certified canonical
    artifact. Certification is certified_canonical_glb's verdict —
    the recorded identity chain -> exact artifact -> measured SHA ->
    current generation. A path string in a projection NEVER
    establishes the artifact; only a real file on disk resolves
    here."""
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


def certified_canonical_glb(run_dir: Optional[Path],
                            geom: Optional[Dict[str, Any]] = None,
                            ) -> Dict[str, Any]:
    """R451-C2.4 §2/§4 — THE certification path. PERSISTED IDENTITY
    SOVEREIGNTY (R451-C2.5 §3): the authoritative resolution is a
    PERSISTED identity document on the run's own disk —
    DESIGN_LINEAGE.json's current-generation entry or
    ARTIFACT_IDENTITY.json — naming the exact artifact -> the
    artifact's SHA measured from its own bytes -> the generation
    identity held against a PERSISTED current-generation anchor.

      1. exact artifact   named by DESIGN_LINEAGE.json's current-
                          generation entry, else by ARTIFACT_IDENTITY
                          .glb_path (the persisted identity chain —
                          never a filename that merely looks right,
                          and NEVER the projection's carried
                          geom.artifact_identity object)
      2. measured SHA     sha256 over the named file's own bytes,
                          equal to the SHA the PERSISTED identity
                          records (geometry_hash / glb_disk_sha256)
      3. current          the INDEPENDENT persisted current-generation
         generation       anchor (DESIGN_LINEAGE.json's current-
                          generation entry, R451-C2.6 §2) exists and
                          matches the persisted identity's generation
                          — the artifact generation is never its own
                          anchor and the anchor is never inferred from
                          it; a missing anchor never certifies

    R451-C2.5 §3: a projection-side geom.artifact_identity object —
    however complete — is DIAGNOSTIC ONLY. It can never name the
    artifact, never supply a certifying SHA, and never anchor the
    current generation. Attack proven by the battery: a forged geom
    object carrying a complete artifact identity does NOT certify an
    artifact when no persisted identity document exists.

    Plus the container proofs: the file exists, is non-zero, and is a
    STRUCTURALLY VALID glTF 2.0 binary (R451-C2.5 §4: header + chunk
    framing + JSON structure — glb_format_check).

    A file found only by the DIAGNOSTIC locator's filename fallbacks
    is reported as `diagnostic_candidate` — readable, never certified
    (artifact discovery and artifact certification are separate).
    Returns {certified, glb, sha256, size, generation_id,
    current_generation_id, basis, failures, diagnostic_candidate,
    diagnostic_basis, format}. Observational: reads only."""
    run_dir = Path(run_dir) if run_dir else None
    geom = geom or {}
    br_identity = (geom.get("artifact_identity") or {}) \
        if isinstance(geom.get("artifact_identity"), dict) else {}
    out: Dict[str, Any] = {
        "certified": False, "glb": None, "sha256": None, "size": 0,
        "generation_id": None, "current_generation_id": None,
        "basis": None, "failures": [],
        "diagnostic_candidate": None, "diagnostic_basis": None,
        "format": None,
        # R451-C2.5 §3 — a projection-carried identity object is
        # reported AS a diagnostic; its presence never certifies
        "projection_identity_diagnostic": bool(br_identity),
    }
    if run_dir is None or not run_dir.exists():
        out["failures"] = ["no run directory is readable"]
        return out

    # ---- the PERSISTED identity documents (R451-C2.5 §3) -------------
    # ONLY documents persisted under the run directory can certify. The
    # projection's carried geom.artifact_identity object is diagnostic
    # only — it never names the artifact, never certifies a SHA, and
    # never anchors the current generation.
    lineage = _read_json(run_dir / DESIGN_LINEAGE_REL) or \
        _read_json(run_dir / "MODEL" / DESIGN_LINEAGE_REL)
    identity = _read_json(run_dir / ARTIFACT_IDENTITY_REL) or {}
    model_identity = _read_json(
        run_dir / "MODEL" / ARTIFACT_IDENTITY_REL) or {}
    if not identity and model_identity:
        identity = model_identity

    # ---- 1. the exact artifact, named by the PERSISTED chain ---------
    named: Optional[Path] = None
    basis: Optional[str] = None
    if lineage:
        for gen in lineage.get("generation_models") or []:
            if gen.get("current") and gen.get("glb"):
                named = run_dir / str(gen["glb"])
                basis = "DESIGN_LINEAGE.json current generation entry"
                break
    if named is None and identity:
        id_path = identity.get("glb_path")
        if id_path:
            named = run_dir / str(id_path)
            basis = "ARTIFACT_IDENTITY.json glb_path"
    if named is None:
        out["failures"].append(
            "no PERSISTED identity document names the canonical GLB "
            "(DESIGN_LINEAGE.json current generation / "
            "ARTIFACT_IDENTITY.json glb_path) — a filename that "
            "merely looks right is a diagnostic candidate, and a "
            "projection-carried artifact identity is diagnostic only "
            "(R451-C2.5 §3): neither certifies")

    # ---- the diagnostic candidate (readable, never certified) --------
    diag = resolve_canonical_glb(run_dir)
    if diag is not None:
        out["diagnostic_candidate"] = str(diag)
        out["diagnostic_basis"] = \
            "the diagnostic locator's resolution order" if named is None \
            or diag != named else basis

    if named is None:
        return out

    # ---- the container proofs ----------------------------------------
    if not named.is_file():
        out["failures"].append(
            f"the recorded identity names {named.name} but the file "
            "does not exist on disk")
        return out
    size = named.stat().st_size
    out["size"] = size
    if size == 0:
        out["failures"].append("the named artifact is a zero-byte file")
        return out
    fmt = glb_format_check(named)
    out["format"] = fmt
    if not fmt["valid"]:
        out["failures"].append(
            f"the named artifact is not a valid GLB container "
            f"({fmt['detail']})")
        return out

    # ---- 2. the measured SHA vs the PERSISTED identity's SHA --------
    # R451-C2.5 §3: only the persisted identity's recorded SHAs can
    # certify. The projection's carried SHA fields are contradiction
    # diagnostics in evaluate_geometry_contract — never authority here.
    glb_sha = _sha256_file(named)
    out["sha256"] = glb_sha
    recorded_shas = [
        ("ARTIFACT_IDENTITY.geometry_hash", identity.get("geometry_hash")),
        ("ARTIFACT_IDENTITY.glb_disk_sha256",
         identity.get("glb_disk_sha256")),
    ]
    identity_shas = [(s, v) for s, v in recorded_shas if v]
    if not identity_shas:
        out["failures"].append(
            "the PERSISTED identity records no SHA for the canonical "
            "GLB — identity without the required SHA is not a "
            "certification, and a projection-carried SHA can never "
            "certify (R451-C2.5 §3)")
        return out
    mismatches = [s for s, v in identity_shas if str(v) != glb_sha]
    if mismatches:
        out["failures"].append(
            "the recorded artifact SHA does not match the bytes on "
            f"disk (source: {', '.join(mismatches)}) — identity chain "
            "broken (fail closed)")
        return out

    # ---- 3. the generation identity (INDEPENDENT anchor, R451-C2.6 §2)-
    # The triple identity is mandatory: the persisted identity's
    # generation == the INDEPENDENT persisted current-generation anchor
    # (DESIGN_LINEAGE.json's current-generation entry) == the receipt's
    # generation (checked on the release chain). R451-C2.6 §2: the
    # artifact generation is NEVER its own anchor — the C2.5-era
    # fallback that anchored the current generation with the identity's
    # own generation_id when the lineage recorded none is SUPERSEDED
    # (Art. LXIV: a missing anchor now fails closed at every boundary).
    # The projection's carried generation fields are contradiction
    # diagnostics (evaluate_geometry_contract) — they can fail this
    # certification closed but can never anchor it.
    id_generation = identity.get("generation_id")
    current_anchor = lineage_anchor_generation(run_dir)
    out["generation_id"] = str(id_generation) if id_generation else None
    out["current_generation_id"] = str(current_anchor) \
        if current_anchor else None
    if not id_generation:
        out["failures"].append(
            "the PERSISTED identity records no generation ID — the "
            "generation identity is mandatory and cannot be anchored "
            "by a projection field (R451-C2.5 §3)")
        return out
    if not current_anchor:
        out["failures"].append(
            "no independent persisted current-generation anchor exists "
            "(DESIGN_LINEAGE.json's current-generation entry records no "
            "generation identity) — the artifact generation is never "
            "its own anchor and the current generation is never "
            "inferred from it (R451-C2.6 §2)")
        return out
    if str(id_generation) != str(current_anchor):
        out["failures"].append(
            f"the artifact generation ({id_generation}) does not "
            f"match the independent persisted current generation "
            f"({current_anchor}) — a stale artifact never certifies")
        return out
    # R451-C2.5 §3 — a projection-carried generation CONTRADICTING the
    # persisted identity fails the certification closed (the projection
    # never anchors the current generation; a contradiction is never
    # resolved by trusting either side's promotion path)
    proj_gen = None
    if isinstance(geom.get("artifact_identity"), dict):
        proj_gen = geom["artifact_identity"].get("generation_id")
    proj_gen = proj_gen or geom.get("generation_id")
    if proj_gen and str(id_generation) != str(proj_gen):
        out["failures"].append(
            f"the projection's carried generation ({proj_gen}) "
            f"contradicts the persisted identity generation "
            f"({id_generation}) — the projection never anchors the "
            "current generation and its contradiction fails the "
            "certification closed (R451-C2.5 §3)")
        return out

    out["certified"] = True
    out["glb"] = str(named)
    out["basis"] = basis
    return out


def _load_lineage(run_dir: Optional[Path]) -> Dict[str, Any]:
    """The PERSISTED DESIGN_LINEAGE.json (either location), read-only.
    R451-C2.5 §3: the lineage is one of the two persisted identity
    documents — the projection never substitutes for it."""
    if run_dir is None:
        return {}
    return _read_json(Path(run_dir) / DESIGN_LINEAGE_REL) or \
        _read_json(Path(run_dir) / "MODEL" / DESIGN_LINEAGE_REL) or {}


def lineage_anchor_generation(run_dir: Optional[Path]) -> Optional[str]:
    """R451-C2.6 §2 — THE INDEPENDENT PERSISTED CURRENT-GENERATION
    ANCHOR: DESIGN_LINEAGE.json's current-generation entry. The entry
    carries the current generation's OWN identity — its generation_id
    when the entry records one, else the entry's recorded generation
    number normalized through the pipeline's own convention (gen-<n>,
    the same normalization the bridge's projection writer applies).
    This persisted document — not the artifact's own identity, and
    never the projection — is the ONE canonical current-generation
    source. R451-C2.6 §2: the artifact generation is never its own
    anchor; when the entry records no generation identity this returns
    None and every consumer fails closed (the anchor is not invented
    from the artifact — Art. VI/XXV)."""
    lineage = _load_lineage(run_dir)
    for gen in lineage.get("generation_models") or []:
        if not gen.get("current"):
            continue
        gid = gen.get("generation_id")
        if gid:
            return str(gid)
        n = gen.get("generation")
        if n is not None:
            return f"gen-{n}"
    return None


def resolve_step_artifacts(run_dir: Optional[Path]) -> List[Path]:
    """The run's STEP artifacts (real files, never route strings).

    Returns [] when there is no run directory."""
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
                                  is non-zero, is a valid container,
                                  carries a valid artifact identity
                                  that names it and records the SHA,
                                  the SHA matches the bytes, the
                                  generation identity holds, the
                                  authority verdict is EXPLICIT, and
                                  no contradicting terminal failure
                                  is recorded (R451-C2.4 §2: the
                                  NINE mandatory proofs — missing
                                  any: not success)
      geometry_unverified         a geometry artifact candidate exists
                                  under the run directory but its
                                  mandatory certification is
                                  incomplete — an explicit, typed
                                  unverified state (Art. XXV: never
                                  a failure, never a silent pass)
      geometry_generation_failed  the chain RECORDS a generation failure
                                  (or concluded COMPLETE with only a
                                  parametric DEFINITION and no artifact)
      geometry_not_applicable     the chain RECORDS that geometry does
                                  not apply
      upstream_not_reached        everything else, including every
                                  infrastructure-class block (Art. LXI)

    Route strings ("/api/run/x/model") never establish geometry: the
    artifact must resolve to real bytes under the run directory. A
    missing engineering class is UNKNOWN — never silently engineering,
    and (R451-C2.4 §2) UNKNOWN is not an EXPLICIT authority, so an
    unclassed artifact is geometry_unverified, never geometry_available.
    A legacy boolean-only projection stays readable (that era's
    recorded fact, Art. XI) but establishes nothing — its engineering
    authority is UNKNOWN and it never inherits the current
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

    # ---- resolve + CERTIFY the canonical artifact (R451-C2.4 §2/§4) --
    # discovery (the diagnostic locator) and certification are separate:
    # only the recorded identity chain's named artifact can certify.
    cert = certified_canonical_glb(run_dir, geom)
    diag_path = resolve_canonical_glb(run_dir)
    diag_size = diag_path.stat().st_size if diag_path is not None else 0
    diag_sha = _sha256_file(diag_path) \
        if diag_path is not None and diag_size > 0 else None
    glb_certified = bool(cert["certified"])
    glb_path = Path(cert["glb"]) if glb_certified else None
    glb_size = cert["size"] if glb_certified else 0
    glb_bytes_ok = glb_certified
    glb_sha = cert["sha256"] if glb_certified else None
    glb_format = cert.get("format") or {}
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
    # R451-C2.5 §3 — PERSISTED IDENTITY SOVEREIGNTY: `identity` below is
    # the PERSISTED ARTIFACT_IDENTITY.json (the only certification
    # authority). `br_identity` (the projection's carried
    # geom.artifact_identity) and the projection's own generation_id
    # are DIAGNOSTICS: they may CONTRADICT the persisted chain (fail
    # closed) but can never name an artifact, certify a SHA, state an
    # authority class, or anchor the current generation.
    identity = _read_json(run_dir / ARTIFACT_IDENTITY_REL) if run_dir \
        else None
    br_identity = (geom.get("artifact_identity") or {}) if isinstance(
        geom.get("artifact_identity"), dict) else {}
    projection_generation_id = geom.get("generation_id") or \
        br_identity.get("generation_id")

    # ---- the independent persisted current-generation anchor ----------
    # R451-C2.6 §2 — surfaced verbatim: the ONE canonical persisted
    # current-generation source, read before the contradiction checks
    # (the anchor decides the current side of the triple identity; it
    # is never inferred from the artifact generation).
    lineage_anchor = lineage_anchor_generation(run_dir)

    # ---- SHA verification: every RECORDED sha must match the bytes ---
    # (R451-C2.5 §3: the persisted identity's SHAs are the certification
    # authority; the projection-carried SHAs are CONTRADICTION
    # diagnostics — a projection SHA that disagrees with the bytes
    # fails the artifact closed, never certifies it)
    sha_checks: List[Dict[str, Any]] = []
    recorded_shas = {
        "artifact_identity.geometry_hash":
            (identity or {}).get("geometry_hash"),
        "artifact_identity.glb_disk_sha256":
            (identity or {}).get("glb_disk_sha256"),
        "cio.geometry.glb_sha256 (projection diagnostic)":
            geom.get("glb_sha256"),
        "bridge.artifact_identity.geometry_hash (projection diagnostic)":
            br_identity.get("geometry_hash"),
    }
    any_sha_recorded = False
    sha_mismatch = False
    # the SHA the recorded sources are checked against: the CERTIFIED
    # artifact's measured SHA when certification held, else the
    # diagnostic candidate's measured SHA (contradiction detection)
    check_sha = glb_sha or diag_sha
    for source, recorded in recorded_shas.items():
        if not recorded:
            continue
        any_sha_recorded = True
        ok = (check_sha is not None and str(recorded) == check_sha)
        sha_checks.append({"source": source, "recorded": str(recorded),
                           "matches_bytes": ok})
        if not ok:
            sha_mismatch = True

    # ---- the engineering authority (explicit / conceptual / UNKNOWN) -
    # R451-C2.3: the authority reads RECORDED identity documents only
    # (the PERSISTED MODEL/ARTIFACT_IDENTITY.json, the PERSISTED bridge
    # report's own class fields, the CAD ledger's completion).
    # R451-C2.5 §3: the projection's carried
    # geom.artifact_identity.visualizability_class is a DIAGNOSTIC — it
    # never creates authority (a forged projection claiming
    # ENGINEERING_3D certifies nothing). The CIO's DERIVED class field
    # is never an authority source either — for a bare GLB it is a
    # filename-derived inference.
    class_sources: List[str] = []
    for src, val in (
            ("artifact_identity.visualizability_class",
             (identity or {}).get("visualizability_class")),):
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
    # R451-C2.4 §2 (the NINTH mandatory proof): the authority verdict
    # must be EXPLICIT — a recorded class from the identity documents
    # (ENGINEERING or CONCEPTUAL) or the CAD ledger's own recorded
    # completion. UNKNOWN (no recorded verdict) is not explicit.
    authority_explicit = bool(
        up_classes or concept_classes or cad_outcome == "COMPLETED")
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

    # ---- generation identity (INDEPENDENT anchor, R451-C2.6 §2) -------
    # The persisted identity's generation_id is the artifact side of the
    # triple identity; the INDEPENDENT persisted current-generation
    # anchor (DESIGN_LINEAGE.json's current-generation entry) is the
    # current side. The projection's carried generation is a
    # CONTRADICTION diagnostic: when it disagrees with the persisted
    # identity OR with the independent anchor, the artifact fails closed
    # (the projection never anchors, never certifies, never promotes).
    identity_generation = (identity or {}).get("generation_id") or \
        lineage_anchor_generation(run_dir)
    generation_mismatch = bool(
        identity_generation and projection_generation_id
        and str(identity_generation) != str(projection_generation_id))
    anchor_mismatch = bool(
        lineage_anchor and projection_generation_id
        and str(lineage_anchor) != str(projection_generation_id))
    if generation_mismatch or anchor_mismatch:
        artifact_verified = False
        engineering_authority = "UNKNOWN"
        mismatched = (f"persisted identity generation "
                      f"({identity_generation})" if generation_mismatch
                      else f"independent persisted current-generation "
                      f"anchor ({lineage_anchor})")
        verify_detail = ("the projection's carried generation "
                         f"({projection_generation_id}) contradicts the "
                         f"{mismatched} — a projection never "
                         "anchors the current generation (fail closed, "
                         "R451-C2.5 §3 / R451-C2.6 §2)")

    # ---- R451-C2.4 §2: the NINE mandatory proofs gate -----------------
    # A verified-LOOKING artifact whose certification is incomplete is
    # never geometry_available — the missing proofs are named (Art. XV):
    #   * the GLB path: certified_canonical_glb must have certified
    #   * the STEP path keeps its R451-C2.3 semantics (a byte-valid
    #     STEP establishes ENGINEERING_GEOMETRY_READY and NEVER the
    #     visual input boundary — the GLB certification is what gates
    #     the visual boundary)
    #   * the authority must be EXPLICIT (UNKNOWN is not a verdict)
    if artifact_verified and not step_ok and not glb_certified:
        artifact_verified = False
        engineering_authority = "UNKNOWN"
        verify_detail = verify_detail or (
            "the geometry artifact is present but its certification "
            "is incomplete: " + "; ".join(cert["failures"]))
    elif artifact_verified and not authority_explicit and not step_ok:
        artifact_verified = False
        engineering_authority = "UNKNOWN"
        verify_detail = verify_detail or (
            "the artifact bytes verified but no recorded identity "
            "document states an explicit authority class — UNKNOWN "
            "is not an explicit authority (R451-C2.4 §2)")

    # ---- contradicting terminal failure ------------------------------
    chain_failure = (bridge_outcome == BRIDGE_GEOMETRY_FAILED
                     or cad_outcome in CAD_LEDGER_FAILED)
    chain_not_applicable = (bridge_outcome == BRIDGE_NOT_APPLICABLE
                            or cad_outcome in CAD_LEDGER_NOT_APPLICABLE)
    chain_infra = cad_outcome in CAD_LEDGER_INFRA
    pm_only = bool(geom.get("parametric_model_present")) and \
        not glb_bytes_ok and not step_ok and not legacy_present

    # ---- the geometry-side state (the seven-value vocabulary) --------
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
    elif diag_path is not None or step_paths:
        # R451-C2.4 §2: an artifact candidate EXISTS under the run
        # directory but its mandatory certification is incomplete —
        # the explicit typed unverified state (never a failure, never
        # a silent pass; Art. XXV). A route string alone is NOT a
        # candidate — only real files make this state.
        state = "geometry_unverified"
        verify_detail = verify_detail or (
            "a geometry artifact candidate exists but its mandatory "
            "certification is incomplete: "
            + "; ".join(cert["failures"]))
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
    # R451-C2.4 §2: the GLB must be CERTIFIED (identity-named, SHA-
    # verified, generation-matched, format-valid) — measured bytes
    # alone never satisfy the boundary (the C2.3 byte-satisfiable
    # shortcut is superseded).
    visual_input_ready = bool(glb_certified and not sha_mismatch
                              and not generation_mismatch
                              and not chain_failure)
    if visual_input_ready:
        visual_input_basis = (
            f"canonical GLB {glb_path.name} certified ({glb_size} "
            f"bytes, valid glTF 2.0 container, sha256 verified against "
            f"the recorded identity, generation "
            f"{cert.get('generation_id')})")
    elif engineering_geometry_ready:
        visual_input_basis = ("the engineering geometry is verified but "
                              "no certified canonical GLB resolves under "
                              "the run directory — the visual boundary "
                              "contract is not satisfied by a STEP alone")
    elif glb_route or legacy_present:
        visual_input_basis = ("the projection records geometry presence "
                              "but no certified canonical GLB resolves "
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
            "glb_certified": glb_certified,
            "glb_format": glb_format,
            "certification_basis": cert.get("basis"),
            "certification_failures": cert.get("failures") or [],
            "diagnostic_candidate": cert.get("diagnostic_candidate"),
            "step_files_verified": [str(p) for p in step_ok],
            "sha_checks": sha_checks,
            "any_sha_recorded": any_sha_recorded,
            "sha_mismatch": sha_mismatch,
            "generation_mismatch": generation_mismatch,
            "current_generation_anchor": lineage_anchor,
            "independent_current_generation_anchor_present":
                bool(lineage_anchor),
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
        # R451-C2.4 §5: the generation identity the release chain
        # triple-checks (artifact == receipt == current)
        "artifact_generation_id": cert.get("generation_id"),
        "current_generation_id": cert.get("current_generation_id"),
        # recorded-chain facts (the dossier's detail strings build on
        # these; the watchdog consumes them directly)
        "has_artifact": artifact_verified or legacy_present
        or diag_path is not None,
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
    records and bytes. R451-C2.6 §3 — THE CHAIN IS SOVEREIGN: rung 1
    independently obtains the CERTIFIED canonical artifact through the
    persisted identity chain (certified_canonical_glb). A caller-
    provided glb_path is a DIAGNOSTIC cross-check only — it may agree
    with the certified artifact (recorded) or contradict it (fails
    closed), and it can NEVER weaken the persisted-identity requirement;
    the diagnostic locator's filename fallbacks never satisfy a rung.
    VISUAL_READY requires AT MINIMUM:

      certified canonical GLB identity (persisted identity names it,
        the SHA matches the bytes, the generation matches the
        INDEPENDENT persisted current-generation anchor, and the
        container is STRUCTURALLY valid — R451-C2.5 §4, R451-C2.6 §2)
        -> invocation receipt identity verified (glb_sha256 == bytes;
           run_id == run; geometry_spec_sha256 EXISTS and equals the
           GEOMETRY_SPEC.json bytes — the spec lineage is MANDATORY,
           R451-C2.4 §5)
        -> generation identity verified (artifact generation == receipt
           generation == independent persisted current generation —
           R451-C2.4 §5, R451-C2.6 §2)
        -> render record identity AND renderer-success records that
           AGREE (receipt status == record status — R451-C2.6 §4)
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

    # ---- rung 1: the CERTIFIED canonical artifact (R451-C2.6 §3) -----
    # SOVEREIGN: the chain certifies through the persisted identity
    # chain itself — never through a caller's path, never through the
    # diagnostic locator's filename fallbacks (discovery locates;
    # certification decides).
    cert = certified_canonical_glb(run_dir)
    glb = Path(cert["glb"]) if cert.get("certified") and cert.get("glb") \
        else None
    glb_sha = cert.get("sha256") if cert.get("certified") else None
    fmt = cert.get("format") or {}
    if glb is None or not glb_sha or not fmt.get("valid"):
        rung1_detail = ("the persisted identity chain does not certify a "
                        "canonical GLB"
                        + (": " + "; ".join(cert["failures"])
                           if cert.get("failures") else ""))
        rung1_pass = False
    else:
        rung1_detail = (f"{glb.name} ({cert.get('size')} bytes, certified "
                        f"via {cert.get('basis')}, structurally valid "
                        "glTF 2.0)")
        rung1_pass = True
    # the caller-provided path is a DIAGNOSTIC cross-check: agreement is
    # harmless, disagreement FAILS CLOSED — a caller path never weakens
    # the persisted-identity requirement (R451-C2.6 §3)
    if glb_path is not None:
        try:
            same = glb is not None and \
                Path(glb_path).resolve() == glb.resolve()
        except OSError:
            same = False
        if not same:
            rung1_pass = False
            rung1_detail = (
                rung1_detail + "; the caller-provided glb_path ("
                f"{Path(glb_path).name}) does not name the certified "
                "canonical artifact — a caller path is a diagnostic and "
                "never weakens the persisted-identity requirement "
                "(R451-C2.6 §3)")
    rungs.append({"rung": "canonical_glb_identity",
                  "pass": rung1_pass, "detail": rung1_detail})

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
        # R451-C2.4 §5: the geometry-spec lineage is MANDATORY for
        # VISUAL_READY — the receipt must NAME the spec sha AND the
        # name must equal the spec file's bytes. The C2.3-era lenient
        # both-absent pass is superseded (disclosed in the battery):
        # an unprovable lineage is a failed rung, never a pass.
        if not rec_spec:
            problems.append("the receipt carries no geometry_spec_sha256 "
                            "— the geometry-spec lineage is mandatory "
                            "(R451-C2.4 §5)")
        elif spec_sha and rec_spec != spec_sha:
            problems.append("receipt geometry_spec_sha256 != the "
                            "GEOMETRY_SPEC.json bytes (identity chain "
                            "broken)")
        elif rec_spec and not spec_sha:
            problems.append("receipt names a geometry spec sha but no "
                            "GEOMETRY_SPEC.json exists on disk")
        receipt_ok = not problems
        detail = "; ".join(problems) if problems else \
            "receipt identity == canonical GLB identity"
    rungs.append({"rung": "invocation_receipt_identity",
                  "pass": receipt_ok, "detail": detail})

    # ---- rung 3: the generation identity (R451-C2.4 §5, R451-C2.6 §2)-
    # artifact generation == receipt generation == the INDEPENDENT
    # persisted current generation (the anchor; the artifact generation
    # is never its own anchor)
    gen_ok = False
    detail = "the invocation receipt is absent — no generation lineage"
    if receipt:
        rec_gen = receipt.get("generation_id")
        art_gen = contract.get("artifact_generation_id")
        cur_gen = contract.get("current_generation_id")
        if (art_gen is None or cur_gen is None) and run_dir is not None:
            # the rung-1 certification already holds the generation
            # verdict — reuse it (one certification pass, one authority)
            art_gen = art_gen or cert.get("generation_id")
            cur_gen = cur_gen or cert.get("current_generation_id")
        problems = []
        if not rec_gen:
            problems.append("the receipt records no generation_id — the "
                            "generation lineage is mandatory "
                            "(R451-C2.4 §5)")
        if not art_gen:
            problems.append("the artifact identity records no "
                            "generation_id")
        if not cur_gen:
            problems.append("no independent persisted current-generation "
                            "anchor exists (DESIGN_LINEAGE.json's "
                            "current-generation entry records no "
                            "generation identity) — the generation "
                            "identity cannot hold three ways "
                            "(R451-C2.6 §2)")
        if rec_gen and art_gen and str(rec_gen) != str(art_gen):
            problems.append(f"receipt generation ({rec_gen}) != the "
                            f"artifact generation ({art_gen})")
        if art_gen and cur_gen and str(art_gen) != str(cur_gen):
            problems.append(f"the artifact generation ({art_gen}) is "
                            f"not the independent persisted current "
                            f"generation ({cur_gen})")
        gen_ok = not problems
        detail = "; ".join(problems) if problems else \
            (f"generation identity holds three ways "
             f"({art_gen})")
    rungs.append({"rung": "generation_identity",
                  "pass": gen_ok, "detail": detail})

    # ---- rung 4: render record identity + the success-records
    #      cross-check (R451-C2.6 §4) -----------------------------------
    # The record's source link must name the certified canonical bytes,
    # AND the renderer-success records must AGREE: the production
    # receipt writer copies the render record's status verbatim, so a
    # disagreement between receipt.invocation_status and
    # render_record.status is tampering or forgery — the rung fails
    # closed and neither contradiction can produce VISUAL_READY.
    record = _read_json(run_dir / RENDER_RECORD_REL) if run_dir else None
    record_ok = False
    detail = "no persisted render record on disk"
    if record:
        src = record.get("source_glb_sha256")
        rec_status = str(record.get("status") or "")
        receipt_status = str((receipt or {}).get("invocation_status") or "")
        if receipt_status and rec_status and \
                receipt_status != rec_status:
            detail = (f"the renderer-success records contradict: "
                      f"receipt.invocation_status ({receipt_status}) != "
                      f"render_record.status ({rec_status}) — the "
                      "production writer copies the record's status "
                      "verbatim, so a disagreement is tampering or "
                      "forgery (fail closed, R451-C2.6 §4)")
        elif not src:
            detail = ("the render record predates the source_glb_sha256 "
                      "field — the render-source link is UNPROVEN")
        elif src != glb_sha:
            detail = ("render_record.source_glb_sha256 != the canonical "
                      "GLB bytes — source substitution fail closed")
        else:
            record_ok = True
            detail = ("render record source == canonical GLB bytes; "
                      "renderer-success records agree "
                      f"({rec_status or 'unrecorded'})")
    rungs.append({"rung": "render_record_identity",
                  "pass": record_ok, "detail": detail})

    # ---- rung 5: gate PASS -------------------------------------------
    gate = _read_json(run_dir / GATE_REL) if run_dir else None
    verdict = (gate or {}).get("verdict")
    gate_ok = verdict in GATE_PASS_VERDICTS
    rungs.append({"rung": "gate_pass",
                  "pass": gate_ok,
                  "detail": f"gate verdict {verdict or 'absent'}"})

    # ---- rung 6: the required presentation artifact set --------------
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

    # ---- rung 7: hero exists ------------------------------------------
    hero = run_dir / HERO_PNG_REL if run_dir else None
    hero_ok = bool(hero and hero.is_file() and hero.stat().st_size > 0)
    rungs.append({"rung": "hero_exists", "pass": hero_ok,
                  "detail": "hero.png on disk" if hero_ok else
                  "hero.png missing or empty"})

    # ---- rung 8: hero source identity == canonical GLB ---------------
    # The hero's SOURCE is what the renderer consumed: proven by the
    # render record's source link (rung 4). An exported hero.glb is a
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
    if geometry_state == "geometry_unverified":
        # R451-C2.4 §2: an artifact candidate exists but the mandatory
        # certification is incomplete — the join has NO certified
        # geometry to invoke. UNDECIDED (never a state promotion, Art.
        # XXV); the caller's explicitly-unverified historical treatment
        # owns the render side.
        result["visual_join_state"] = None
        result["visual_join_detail"] = contract.get(
            "geometry_state_detail") or None
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
        # (R451-C2.4: a CONCEPTUAL or UNKNOWN authority can NEVER
        # reach VISUAL_READY through a render — the fallback this
        # round removed was the only path that let it happen)
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

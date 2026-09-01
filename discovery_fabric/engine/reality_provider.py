"""discovery_fabric/engine/reality_provider.py — R389 PHASE 2: the
provider-neutral REALITY layer.

CEO directive (R389, Phase 2 — BUILD THE REALITY LOOP):

> "Build a provider-neutral REALITY_PROVIDER with World Labs as the first
>  integration candidate. World Labs/Marble is a spatial reconstruction
>  provider, NOT ground truth. Use outputs as RECONSTRUCTED / COMPUTATIONAL
>  unless independently measured."

Architecture:

    REALITY_PROVIDER  (provider-neutral contract; World Labs first)
         |
         v  assets tagged evidence_origin=RECONSTRUCTED (never MEASURED)
    REALITY_MODEL     (geometry, dimensions, materials, interfaces,
         |             operating_conditions, observations, measurements,
         |             uncertainties, failure_modes, provenance)
         v
    REALITY_WORLD  <-->  REALITY_COMPARISON  <-->  DESIGN_WORLD
                              |
                              v
    discrepancy -> hypothesis -> technical-state update
                 -> mutation proposal -> new design (PROPOSAL ONLY)

Constitutional enforcement (the module IS the boundary):
- Art. XXXVIII (Reality Boundary): a provider is an AI system. It can
  produce RECONSTRUCTED or COMPUTATIONAL evidence ONLY. There is NO code
  path by which a provider asset becomes MEASURED / PHYSICAL_OBSERVATION:
  `MEASURED` evidence_origin is rejected by the provider constructor, and
  measured values enter REALITY_MODEL exclusively through R370G-validated
  REALITY_EVENT ids (external attestation). A generated reconstruction can
  NEVER automatically become PHYSICAL_VALIDATION — the comparison layer
  emits hypotheses and proposals, never validations.
- Art. XXI.3 (provider failure is not absence): statuses AUTH_FAILED /
  TIMEOUT / PROVIDER_ERROR are distinct from NO_DATA; each carries the
  failure reason verbatim.
- Art. VI (never manufacture provenance): the provider call ledger records
  what actually happened (operation ids, request/response hashes from the
  real wire). Absent ledger entries stay PROVENANCE_INCOMPLETE.
- Art. IV (no fallback epistemology): no silent weaker path — a failed
  provider call BLOCKS that reality source, it does not substitute a guess.
- Art. XXV (unknown stays unknown): comparisons on unresolved fields emit
  UNRESOLVED records, never zero-deltas.

This module NEVER calls an LLM (Art. XVIII) and never mutates canonical
state (Art. IX): comparison outputs are proposals consumed downstream by
the SAME validators as every other proposal (technical_state /
improvement_engine), never auto-applied.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field as dc_field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# The evidence-origin vocabulary (Art. XXXVIII structural boundary)
# ---------------------------------------------------------------------------


class EvidenceOrigin(str, Enum):
    """WHO produced a reality datum. Ranks follow Art. XXXVIII layers."""

    RECONSTRUCTED = "RECONSTRUCTED"   # rank 3/4 — provider/AI reconstruction
    COMPUTATIONAL = "COMPUTATIONAL"   # rank 4 — deterministic computation
    MEASURED = "MEASURED"             # rank 5 — external instrument only

    @property
    def rank(self) -> int:
        return {"RECONSTRUCTED": 3, "COMPUTATIONAL": 4, "MEASURED": 5}[self.value]


# Providers are AI systems: they may NEVER hold these origins.
FORBIDDEN_PROVIDER_ORIGINS = (EvidenceOrigin.MEASURED,)

REALITY_MODEL_FIELDS = (
    "geometry", "dimensions", "materials", "interfaces",
    "operating_conditions", "observations", "measurements",
    "uncertainties", "failure_modes", "provenance",
)


# ---------------------------------------------------------------------------
# Provider call ledger (provenance custody — Art. VI/XXI.9)
# ---------------------------------------------------------------------------

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class ProviderCallLedger:
    """Append-only record of real provider wire calls.

    Records operation ids + request/response hashes + statuses. Entries are
    written only from actual HTTP exchanges (or explicit RECORDED_LOCAL
    markers for tests — visibly labeled). Nothing is inferred, nothing
    back-filled: absent = PROVENANCE_INCOMPLETE (Art. VI).
    """

    def __init__(self, path: Optional[Path] = None):
        self.path = path
        self.entries: List[Dict[str, Any]] = []
        if path and path.exists():
            try:
                self.entries = json.loads(path.read_text()).get("entries", [])
            except (json.JSONDecodeError, ValueError):
                self.entries = []  # honest absent, not fabricated

    def record(self, entry: Dict[str, Any]) -> None:
        entry = dict(entry)
        entry.setdefault("recorded_at", _now())
        self.entries.append(entry)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps({"entries": self.entries}, indent=1))

    def for_operation(self, operation_id: str) -> List[Dict[str, Any]]:
        return [e for e in self.entries
                if e.get("operation_id") == operation_id]

    def summary(self) -> Dict[str, Any]:
        return {"total_calls": len(self.entries),
                "providers": sorted({e.get("provider") for e in self.entries
                                     if e.get("provider")})}


# ---------------------------------------------------------------------------
# The provider-neutral contract
# ---------------------------------------------------------------------------

PROVIDER_STATUSES = (
    "PENDING", "IN_PROGRESS", "SUCCEEDED", "AUTH_FAILED", "TIMEOUT",
    "PROVIDER_ERROR", "CANCELED",
)
# Failure statuses that must NEVER be read as absence (Art. XXI.3)
FAILURE_STATUSES = ("AUTH_FAILED", "TIMEOUT", "PROVIDER_ERROR", "CANCELED")


@dataclass
class RealityRequest:
    """A request for a spatial/physical reconstruction of a described scene."""
    prompt: str                                   # what to reconstruct
    display_name: str = "Toscanini reality probe"
    reference_design: Optional[Dict[str, Any]] = None  # DESIGN_WORLD context
    request_id: str = ""


@dataclass
class RealityAsset:
    """One artifact returned by a provider. ALWAYS origin-tagged."""
    asset_id: str
    kind: str                       # e.g. WORLD_MESH, WORLD_METADATA
    origin: EvidenceOrigin          # structurally RECONSTRUCTED/COMPUTATIONAL
    provider: str
    operation_id: str
    payload: Dict[str, Any] = dc_field(default_factory=dict)
    fetched_at: str = ""
    # R370G event binding — set ONLY for externally measured data; a
    # provider asset can never carry one (there is no code path that sets
    # this for provider assets; the constructor forbids MEASURED).
    reality_event_id: Optional[str] = None


class RealityProvider:
    """Provider-neutral contract. Subclasses implement ONE transport.

    Structural guarantees enforced here (not by convention):
      * evidence_origin is locked to RECONSTRUCTED/COMPUTATIONAL at
        construction — MEASURED raises (providers are AI systems; Art. XXXVIII).
      * every asset passes through _asset() which stamps the origin.
      * failure statuses are explicit, never converted to "empty".
    """

    KIND = "GENERIC"

    def __init__(self, evidence_origin: EvidenceOrigin
                 = EvidenceOrigin.RECONSTRUCTED,
                 ledger: Optional[ProviderCallLedger] = None):
        if evidence_origin in FORBIDDEN_PROVIDER_ORIGINS:
            raise ValueError(
                "REALITY BOUNDARY VIOLATION: a provider may not declare "
                f"evidence_origin={evidence_origin.value}. Only external "
                "R370G-attested events may carry MEASURED (Art. XXXVIII).")
        self.evidence_origin = evidence_origin
        self.ledger = ledger or ProviderCallLedger()

    # ---- contract surface -------------------------------------------------
    def submit(self, request: RealityRequest) -> Dict[str, Any]:
        """Start generation. Returns {operation_id, status, ...}."""
        raise NotImplementedError

    def poll(self, operation_id: str) -> Dict[str, Any]:
        """Poll operation status. Status ∈ PROVIDER_STATUSES."""
        raise NotImplementedError

    def fetch(self, operation_id: str) -> List[RealityAsset]:
        """Fetch available assets for a SUCCEEDED operation."""
        raise NotImplementedError

    # ---- shared helpers ---------------------------------------------------
    def _asset(self, kind: str, operation_id: str,
               payload: Dict[str, Any]) -> RealityAsset:
        return RealityAsset(
            asset_id=f"{self.name()}:{operation_id}:{kind}",
            kind=kind, origin=self.evidence_origin, provider=self.name(),
            operation_id=operation_id, payload=payload, fetched_at=_now())

    @classmethod
    def name(cls) -> str:
        return cls.__name__


# ---------------------------------------------------------------------------
# World Labs (Marble) adapter — the first integration candidate
# ---------------------------------------------------------------------------

class WorldLabsProvider(RealityProvider):
    """World Labs / Marble text-to-world client.

    Transport (verified live 2026-09-01):
      POST https://api.worldlabs.ai/marble/v1/worlds:generate
      GET  https://api.worldlabs.ai/marble/v1/operations/{operation_id}
    Auth: WLT-Api-Key header. Key comes from env WORLD_LABS_API_KEY or the
    gitignored .env.keys — NEVER committed.

    The provider returns generated 3D worlds: spatial RECONSTRUCTIONS.
    They are hypotheses about scene structure, not measurements; the
    evidence_origin stays RECONSTRUCTED for the asset lifetime.
    """

    KIND = "SPATIAL_RECONSTRUCTION"
    BASE = "https://api.worldlabs.ai/marble/v1"
    MODEL = "marble-1.1"

    def __init__(self, api_key: Optional[str] = None,
                 ledger: Optional[ProviderCallLedger] = None,
                 timeout_s: int = 60):
        super().__init__(evidence_origin=EvidenceOrigin.RECONSTRUCTED,
                         ledger=ledger)
        self.api_key = api_key or os.environ.get("WORLD_LABS_API_KEY") or \
            self._key_from_env_file()
        self.timeout_s = timeout_s

    @staticmethod
    def _key_from_env_file() -> Optional[str]:
        kf = Path(__file__).resolve().parents[2] / ".env.keys"
        if not kf.exists():
            return None
        for line in kf.read_text().splitlines():
            if line.strip().startswith("WORLD_LABS_API_KEY="):
                return line.strip().split("=", 1)[1].strip() or None
        return None

    # ---- wire ------------------------------------------------------------
    def _request(self, method: str, path: str,
                 body: Optional[Dict[str, Any]] = None) -> Tuple[int, Any]:
        url = f"{self.BASE}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if self.api_key:
            req.add_header("WLT-Api-Key", self.api_key)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as r:
                raw = r.read()
                code = r.status
        except urllib.error.HTTPError as e:
            raw = e.read()
            code = e.code
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", e)
            return 0, {"transport_error": str(reason)}
        except TimeoutError:
            return 0, {"transport_error": "timeout"}
        try:
            return code, json.loads(raw) if raw else {}
        except (json.JSONDecodeError, ValueError):
            return code, {"raw_text": raw.decode(errors="replace")[:2000]}

    @classmethod
    def _wire_error(cls, code: int, payload: Dict[str, Any]) -> str:
        if code == 401 or code == 403:
            return "AUTH_FAILED"
        if code == 0:
            return "TIMEOUT" if "timeout" in str(payload) else "PROVIDER_ERROR"
        return "PROVIDER_ERROR"

    # ---- contract --------------------------------------------------------
    def submit(self, request: RealityRequest) -> Dict[str, Any]:
        if not self.api_key:
            # honest unavailability — NOT an empty result (Art. XXI.3)
            return {"status": "AUTH_FAILED",
                    "reason": "no WORLD_LABS_API_KEY configured",
                    "provider": self.name()}
        body = {
            "display_name": request.display_name[:80],
            "model": self.MODEL,
            "world_prompt": {"type": "text",
                             "text_prompt": request.prompt[:2000]},
        }
        code, payload = self._request("POST", "/worlds:generate", body)
        if code != 200:
            status = self._wire_error(code, payload)
            self.ledger.record({
                "provider": self.name(), "call": "worlds:generate",
                "http_status": code, "status": status,
                "request_sha256": _sha256(json.dumps(body).encode()),
                "error": str(payload)[:400]})
            return {"status": status, "provider": self.name(),
                    "http_status": code, "reason": str(payload)[:400]}
        op_id = payload.get("operation_id")
        self.ledger.record({
            "provider": self.name(), "call": "worlds:generate",
            "http_status": 200, "status": payload.get("done") and
            "SUCCEEDED" or "IN_PROGRESS",
            "operation_id": op_id,
            "request_sha256": _sha256(json.dumps(body).encode()),
            "world_id": (payload.get("metadata") or {}).get("world_id"),
            "expires_at": payload.get("expires_at")})
        return {"status": "SUCCEEDED" if payload.get("done") else
                "IN_PROGRESS", "operation_id": op_id,
                "provider": self.name(),
                "expires_at": payload.get("expires_at")}

    def poll(self, operation_id: str) -> Dict[str, Any]:
        if not self.api_key or not operation_id:
            return {"status": "AUTH_FAILED" if not self.api_key
                    else "PROVIDER_ERROR",
                    "reason": "missing key or operation_id"}
        code, payload = self._request(
            "GET", f"/operations/{operation_id}")
        if code != 200:
            return {"status": self._wire_error(code, payload),
                    "http_status": code, "reason": str(payload)[:400]}
        if payload.get("error"):
            return {"status": "PROVIDER_ERROR", "operation_id": operation_id,
                    "reason": str(payload["error"])[:400],
                    "provider": self.name()}
        if payload.get("done"):
            return {"status": "SUCCEEDED", "operation_id": operation_id,
                    "provider": self.name(), "response": payload.get("response"),
                    "world_id": (payload.get("metadata") or {}).get("world_id"),
                    "cost": payload.get("cost")}
        prog = (payload.get("metadata") or {}).get("progress") or {}
        st = "IN_PROGRESS" if str(prog.get("status", "")).upper() in (
            "IN_PROGRESS", "QUEUED", "PENDING") else "IN_PROGRESS"
        return {"status": st, "operation_id": operation_id,
                "provider": self.name(),
                "world_id": (payload.get("metadata") or {}).get("world_id"),
                "description": prog.get("description")}

    def fetch(self, operation_id: str) -> List[RealityAsset]:
        # Poll first: only SUCCEEDED operations yield assets; failures
        # yield [] with the failure recorded in the ledger (honest absence
        # vs provider failure stays distinguishable via the ledger).
        status = self.poll(operation_id)
        if status.get("status") != "SUCCEEDED":
            self.ledger.record({
                "provider": self.name(), "call": "fetch",
                "operation_id": operation_id,
                "status": status.get("status"),
                "reason": status.get("reason", "not done")})
            return []
        resp = status.get("response") or {}
        assets_meta = (resp.get("assets") or {}) if isinstance(
            resp, dict) else {}
        mesh = (assets_meta.get("mesh") or {})
        splats = (assets_meta.get("splats") or {})
        semantics = (splats.get("semantics_metadata") or {})
        assets: List[RealityAsset] = []
        if mesh.get("collider_mesh_url"):
            assets.append(self._asset("WORLD_MESH", operation_id, {
                "world_id": resp.get("world_id"),
                "asset_kind": "GENERATED_WORLD_GLB",
                "mesh_url": mesh["collider_mesh_url"],
                "provider_model": self.MODEL,
                "semantics": semantics,
                "caption": (resp.get("caption") or "")[:2000],
                "note": "generated spatial reconstruction — hypothesis "
                        "about scene structure, not a measurement",
            }))
        if assets_meta.get("imagery", {}).get("pano_url"):
            assets.append(self._asset("WORLD_IMAGERY", operation_id, {
                "world_id": resp.get("world_id"),
                "pano_url": assets_meta["imagery"]["pano_url"],
                "note": "rendered panorama of the reconstructed world",
            }))
        if splats.get("spz_urls"):
            assets.append(self._asset("WORLD_SPLATS", operation_id, {
                "world_id": resp.get("world_id"),
                "spz_urls": splats["spz_urls"],
                "semantics": semantics,
            }))
        for a in assets:
            self.ledger.record({
                "provider": self.name(), "call": "fetch",
                "operation_id": operation_id, "status": "SUCCEEDED",
                "asset_id": a.asset_id, "asset_kind": a.kind,
                "asset_sha256": _sha256(
                    json.dumps(a.payload, sort_keys=True).encode())})
        if not assets:
            # succeeded but no assets — honest empty, still ledgered
            self.ledger.record({
                "provider": self.name(), "call": "fetch",
                "operation_id": operation_id, "status": "SUCCEEDED",
                "asset_id": None, "reason": "response carried no assets"})
        return assets


# ---------------------------------------------------------------------------
# REALITY_MODEL — the ten-field container, every field origin-tagged
# ---------------------------------------------------------------------------

def _r370g_validator():
    """Late import (engine learning_loop uses the same loader)."""
    import importlib.util
    import sys
    p = Path(__file__).resolve().parents[2] / "premium_package_factory" \
        / "gates" / "r370g_reality_event_schema.py"
    spec = importlib.util.spec_from_file_location("r389_r370g_schema", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("r389_r370g_schema", mod)
    spec.loader.exec_module(mod)
    return mod


def validate_measured_event(reality_event_id: str,
                            ledger_path: Optional[Path] = None) \
        -> Dict[str, Any]:
    """A MEASURED datum must bind to an R370G-validated REALITY_EVENT.

    Returns {valid: bool, errors: [...]}. Unknown/missing event ids are
    INVALID — never silently accepted (Art. IV: no fallback path).
    ledger_path redirects the frozen ledger for tests/rehearsals ONLY
    (None = canonical ledger — same discipline as learning_loop).
    """
    try:
        r370g = _r370g_validator()
        original = None
        if ledger_path is not None:
            original = r370g.REALITY_EVENT_LEDGER_PATH
            r370g.REALITY_EVENT_LEDGER_PATH = str(ledger_path)
        try:
            event = r370g.get_reality_event(reality_event_id)
        finally:
            if original is not None:
                r370g.REALITY_EVENT_LEDGER_PATH = original
    except Exception as exc:  # noqa: BLE001
        return {"valid": False,
                "errors": [f"R370G loader failure: {type(exc).__name__}: "
                           f"{exc}"]}
    if not event:
        return {"valid": False,
                "errors": ["REALITY_EVENT not found: "
                           f"{reality_event_id} — MEASURED data requires an "
                           "existing, attested event (Art. XXXVIII)."]}
    ok, errs = r370g.validate_reality_event(event)
    errors = [str(e) for e in (errs or [])] if ok else \
        [str(e) for e in (errs or [])]
    if event.get("source_type") == "CONTROLLED_REHEARSAL":
        errors.append("CONTROLLED_REHEARSAL events are SYNTHETIC — they may "
                      "not supply MEASURED reality-world data.")
    return {"valid": (ok and not errors), "errors": errors}


@dataclass
class RealityDatum:
    """One value in a REALITY_MODEL field, with its origin and uncertainty."""
    name: str
    value: Any
    origin: EvidenceOrigin
    uncertainty: Optional[str] = None        # declared, e.g. "±10% (provider)"
    source: Optional[str] = None             # provider:op / event id
    note: str = ""


class RealityModel:
    """REALITY_MODEL — where available, the ten CEO-mandated fields.

    Every datum carries origin + uncertainty. MEASURED data is admitted
    only through add_measured() with an R370G-validated event id — the one
    door to rank 5, and it is NOT callable by providers.
    """

    def __init__(self, package_id: str = ""):
        self.package_id = package_id
        self.fields: Dict[str, List[RealityDatum]] = {
            f: [] for f in REALITY_MODEL_FIELDS}

    # ---- construction -----------------------------------------------------
    def add(self, field_name: str, datum: RealityDatum) -> None:
        if field_name not in self.fields:
            raise KeyError(f"REALITY_MODEL has no field {field_name!r}")
        if datum.origin in FORBIDDEN_PROVIDER_ORIGINS:
            # ADVERSARIAL HOLE (found by self-attack, Art. XVII): direct
            # add() could smuggle MEASURED data without R370G attestation.
            # MEASURED has exactly ONE door: add_measured().
            raise ValueError(
                "REALITY BOUNDARY VIOLATION: RealityDatum with origin="
                f"{datum.origin.value} cannot be added directly — use "
                "add_measured() with an R370G-validated event id "
                "(Art. XXXVIII; external attestation required).")
        self.fields[field_name].append(datum)

    def add_measured(self, field_name: str, name: str, value: Any,
                     reality_event_id: str,
                     ledger_path: Optional[Path] = None) -> Dict[str, Any]:
        """The ONLY path for MEASURED data — requires R370G validation."""
        check = validate_measured_event(reality_event_id,
                                        ledger_path=ledger_path)
        if not check["valid"]:
            # BLOCK — no fallback origin (Art. IV). The datum is refused.
            return {"admitted": False, "errors": check["errors"]}
        # _append is unchecked BY DESIGN and used ONLY here, immediately
        # after R370G attestation. Every other caller goes through add().
        self._append(field_name, RealityDatum(
            name=name, value=value, origin=EvidenceOrigin.MEASURED,
            source=reality_event_id,
            note="externally attested via R370G REALITY_EVENT"))
        return {"admitted": True, "errors": []}

    def _append(self, field_name: str, datum: RealityDatum) -> None:
        """Raw append — private; no origin guard (guard lives in add())."""
        self.fields[field_name].append(datum)

    def add_from_asset(self, asset: RealityAsset) -> Dict[str, Any]:
        """Ingest a provider asset into observations/geometry.

        The asset origin is PRESERVED (RECONSTRUCTED/COMPUTATIONAL). There
        is deliberately no branch that could store it as MEASURED.
        """
        if asset.origin in FORBIDDEN_PROVIDER_ORIGINS:
            return {"admitted": False, "errors": [
                "provider asset origin may not be MEASURED"]}
        datum = RealityDatum(
            name=f"{asset.kind}:{asset.asset_id.rsplit(':', 1)[-1]}",
            value=asset.payload, origin=asset.origin,
            uncertainty="provider reconstruction — no measured accuracy",
            source=f"{asset.provider}:{asset.operation_id}",
            note="spatial reconstruction; hypothesis about scene structure "
                 "only (Art. XXXVIII rank 3/4)")
        self.add("observations", datum)
        self.add("geometry", RealityDatum(
            name=f"world:{asset.operation_id}", value=asset.payload,
            origin=asset.origin,
            uncertainty="generated mesh — not dimensional ground truth",
            source=f"{asset.provider}:{asset.operation_id}"))
        return {"admitted": True, "errors": []}

    # ---- serialization ----------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact": "REALITY_MODEL",
            "package_id": self.package_id,
            "fields": {
                f: [{"name": d.name, "value": d.value,
                     "origin": d.origin.value,
                     "uncertainty": d.uncertainty, "source": d.source,
                     "note": d.note} for d in data]
                for f, data in self.fields.items()},
            "origin_counts": self.origin_counts(),
            "loop_verification_note":
                "provider data is RECONSTRUCTED/COMPUTATIONAL and cannot "
                "move loop_verification_state (Art. XXXVII/XXXVIII)",
        }

    def origin_counts(self) -> Dict[str, int]:
        counts = {o.value: 0 for o in EvidenceOrigin}
        for data in self.fields.values():
            for d in data:
                counts[d.origin.value] += 1
        return counts


# ---------------------------------------------------------------------------
# DESIGN_WORLD / REALITY_WORLD
# ---------------------------------------------------------------------------

def build_design_world(spec: Dict[str, Any]) -> Dict[str, Any]:
    """DESIGN_WORLD from the canonical engineering spec.

    The engineering/CAD representation is AUTHORITATIVE here by definition
    (CEO: keep CAD/engineering geometry authoritative). Values keep their
    existing epistemic classes from the spec — nothing is promoted.
    """
    eng = spec.get("engineering_specification") or spec
    dims = []
    for p in (eng.get("parameters") or []):
        if isinstance(p, dict) and p.get("name"):
            dims.append({"name": p["name"], "value": p.get("value"),
                         "unit": p.get("unit", ""),
                         "epistemic_class": p.get("epistemic_class",
                                                   "MODEL_DERIVED")})
    return {
        "artifact": "DESIGN_WORLD",
        "source": "canonical engineering specification (authoritative)",
        "problem_id": spec.get("problem_id", ""),
        "dimensions": dims,
        "geometry_refs": eng.get("geometry_refs") or [],
        "materials": [
            {"name": m.get("name", ""), "value": m.get("spec", ""),
             "epistemic_class": m.get("epistemic_class", "MODEL_DERIVED")}
            for m in (eng.get("materials") or [])
            if isinstance(m, dict)],
        "operating_conditions": eng.get("operating_conditions") or {},
        "interfaces": eng.get("interfaces") or [],
        "authoritative": True,
    }


def build_reality_world(model: RealityModel) -> Dict[str, Any]:
    """REALITY_WORLD from the REALITY_MODEL, origin-separated."""
    d = model.to_dict()
    measured = [x for f in ("dimensions", "measurements")
                for x in d["fields"][f] if x["origin"] == "MEASURED"]
    reconstructed = [x for f in ("observations", "geometry")
                     for x in d["fields"][f]
                     if x["origin"] == "RECONSTRUCTED"]
    return {
        "artifact": "REALITY_WORLD",
        "package_id": model.package_id,
        "fields": d["fields"],
        "measured_count": len(measured),
        "reconstructed_count": len(reconstructed),
        "authoritative": False,
        "note": "reality world aggregates RECONSTRUCTED (provider) and "
                "MEASURED (R370G-attested) data; reconstructed data is a "
                "hypothesis, measured data is evidence",
    }


# ---------------------------------------------------------------------------
# REALITY_COMPARISON — deterministic, hypothesis-generating, never validating
# ---------------------------------------------------------------------------

HYPOTHESIS_TEMPLATE = {
    "dimension": (
        "Design value {design} vs reality-world datum {reality} "
        "({origin}) for '{name}' — delta {delta}. Hypothesis: the design "
        "assumption for '{name}' is {verdict} the externally available "
        "reality signal. Next step: an independent MEASURED observation "
        "(R370G event) to resolve the discrepancy."),
}


def compare_design_to_reality(design_world: Dict[str, Any],
                              reality_world: Dict[str, Any],
                              tolerance: float = 0.20) -> Dict[str, Any]:
    """DESIGN_WORLD ↔ REALITY_COMPARISON ↔ REALITY_WORLD.

    Deterministic field-wise comparison. Each dimension present in BOTH
    worlds yields a discrepancy record with:
      discrepancy -> hypothesis -> technical_state_update (proposal)
                  -> mutation proposal -> new-design direction
    Everything is a PROPOSAL: this function writes nothing, validates
    nothing, and can never emit PHYSICAL_VALIDATION (structural absence —
    the word does not appear in any emitted state).

    RECONSTRUCTED origins count only as hypothesis-grade comparisons; they
    are labeled as such and can NEVER mark a design 'confirmed'.
    """
    design_dims = {d["name"]: d for d in design_world.get("dimensions", [])
                   if isinstance(d, dict) and d.get("name")}
    reality_dims: Dict[str, List[Dict[str, Any]]] = {}
    for f in ("dimensions", "measurements", "observations"):
        for x in (reality_world.get("fields") or {}).get(f, []):
            nm = x.get("name", "")
            if nm in design_dims:
                reality_dims.setdefault(nm, []).append(x)

    records: List[Dict[str, Any]] = []
    for name, dd in design_dims.items():
        matches = reality_dims.get(name)
        if not matches:
            records.append({
                "field": "dimensions", "name": name,
                "design_value": dd.get("value"),
                "reality_value": None, "delta": None,
                "within_uncertainty": None,
                "status": "UNRESOLVED",
                "origin": None,
                "hypothesis": f"No reality-world datum for '{name}'. "
                              "Unknown stays unknown (Art. XXV) — this is "
                              "NOT evidence the design value is correct.",
            })
            continue
        for r in matches:
            origin = r.get("origin")
            try:
                dv = float(dd.get("value"))
                rv = float(r.get("value"))
                delta = rv - dv
                rel = abs(delta) / (abs(dv) or 1.0)
                within = rel <= tolerance
            except (TypeError, ValueError):
                delta, rel, within = None, None, None
            verdict = ("consistent with" if within else
                       "potentially inconsistent with")
            rec = {
                "field": "dimensions", "name": name,
                "design_value": dd.get("value"),
                "reality_value": r.get("value"),
                "delta": delta, "relative_delta": rel,
                "within_uncertainty": within,
                "status": "COMPARED",
                "origin": origin,
            }
            if origin == "MEASURED":
                rec["hypothesis"] = HYPOTHESIS_TEMPLATE["dimension"].format(
                    design=dd.get("value"), reality=r.get("value"),
                    origin=origin, name=name, delta=delta, verdict=verdict)
                rec["grade"] = "EVIDENCE_GRADE"
                rec["technical_state_update"] = {
                    "proposal": (
                        f"parameter '{name}' observed {r.get('value')} vs "
                        f"design {dd.get('value')} (MEASURED) — update the "
                        "technical-state parameter from the measured datum "
                        "after passing the standard validator"),
                    "auto_applied": False,
                }
            else:
                rec["hypothesis"] = HYPOTHESIS_TEMPLATE["dimension"].format(
                    design=dd.get("value"), reality=r.get("value"),
                    origin=origin, name=name, delta=delta, verdict=verdict)
                rec["grade"] = "HYPOTHESIS_GRADE"
                rec["technical_state_update"] = {
                    "proposal": (
                        f"reconstruction suggests '{name}' ≈ "
                        f"{r.get('value')} (RECONSTRUCTED, hypothesis only) — "
                        "consider a decisive experiment to measure it"),
                    "auto_applied": False,
                }
            rec["mutation"] = {
                "direction": (
                    "increase" if (delta or 0) > 0 else "decrease"
                    if (delta or 0) < 0 else "hold"),
                "parameter": name,
                "rationale": "reality-world comparison proposal (not applied)",
                "auto_applied": False,
            }
            records.append(rec)

    unresolved = [r for r in records if r["status"] == "UNRESOLVED"]
    compared = [r for r in records if r["status"] == "COMPARED"]
    return {
        "artifact": "REALITY_COMPARISON",
        "design_world_source": design_world.get("source"),
        "reality_world_package": reality_world.get("package_id"),
        "records": records,
        "summary": {
            "dimensions_compared": len(compared),
            "dimensions_unresolved": len(unresolved),
            "measured_comparisons": len(
                [r for r in compared if r.get("origin") == "MEASURED"]),
            "reconstructed_comparisons": len(
                [r for r in compared
                 if r.get("origin") == "RECONSTRUCTED"]),
        },
        "emits": "hypotheses and proposals ONLY — a generated "
                 "reconstruction NEVER becomes PHYSICAL_VALIDATION "
                 "(Art. XXXVIII); measured comparisons still route through "
                 "the standard validators before any state change",
        "loop_verification_state": "UNTOUCHED",
    }


# ---------------------------------------------------------------------------
# Product-facing convenience: one call from problem text to comparison input
# ---------------------------------------------------------------------------

def request_reality_reconstruction(
        prompt: str, provider: Optional[RealityProvider] = None,
        display_name: str = "Toscanini reality probe") -> Dict[str, Any]:
    """Submit a reconstruction request; returns operation handle + honest
    status. Long-running: the caller polls and fetches later."""
    provider = provider or WorldLabsProvider()
    return provider.submit(RealityRequest(
        prompt=prompt, display_name=display_name))


def harvest_reality_model(provider: RealityProvider, operation_id: str,
                          package_id: str = "") -> Tuple[RealityModel,
                                                         Dict[str, Any]]:
    """Fetch assets for an operation into a REALITY_MODEL (RECONSTRUCTED).

    Ingestion is the provenance-custody point: EVERY ingested asset is
    recorded in the provider call ledger with its content hash — provider
    neutral, so fake/real/alternate providers get identical custody
    (Art. VI/XXI.9).
    """
    model = RealityModel(package_id=package_id)
    assets = provider.fetch(operation_id)
    for a in assets:
        provider.ledger.record({
            "provider": provider.name(), "call": "ingest",
            "operation_id": operation_id, "asset_id": a.asset_id,
            "origin": a.origin.value,
            "asset_sha256": _sha256(
                json.dumps(a.payload, sort_keys=True).encode())})
    ingest = [model.add_from_asset(a) for a in assets]
    status = {"assets": len(assets), "ingested": ingest,
              "provider": provider.name(),
              "origin": provider.evidence_origin.value,
              "ledger_entries": len(provider.ledger.entries)}
    return model, status

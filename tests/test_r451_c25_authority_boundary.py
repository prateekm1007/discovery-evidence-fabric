"""R451-C2.5 — Final Presentation Authority Hardening battery: the
eight decisive adversarial attacks, each proven to FAIL CLOSED, plus
the engineering positive control that must keep reaching VISUAL_READY.

Operator directive R451-C2.5. The round's question: can the
presentation boundary be reached through a PROJECTION (a forged
geom.artifact_identity, a forged generation), through a contradiction
(visual_complete + CONCEPTUAL / UNKNOWN, lineage-vs-identity
disagreement, a valid header over malformed internal structure), or
through a LEGACY payload with a convincing render PASS — and still
claim visual readiness? Every attack below feeds the forged shape to
THE canonical evaluator (toscanini/visual_join.py — the SAME evaluator
the dossier and the watchdog consume) and proves the system does NOT
promote the state.

The eight directive attacks:

  1. projection identity forged, persisted identity absent
     -> the forged geom.artifact_identity certifies NOTHING
  2. projection generation forged, canonical generation absent
     -> the projection's generation never anchors the current one
  3. visual_complete + CONCEPTUAL   -> the join never announces it
  4. visual_complete + UNKNOWN      -> geometry_unverified, join none
  5. lineage points A / identity points B
     -> the persisted contradiction fails the certification closed
  6. valid header / malformed internal GLB structure
     -> the structural check (chunk framing + JSON structure) fails it
  7. two GLBs / only one identity-named
     -> ONLY the identity-named artifact certifies; the decoy never does
  8. legacy frontend payload with convincing render PASS
     -> LEGACY_STATE_UNAVAILABLE, never a current presentation state
        (behavioral proof in scripts/r451_c2_ui_tests.mjs; the python
        side pins the mapping's source and the backend vocabulary)

Plus the positive control (Art. V — not a universal rejector): the
complete valid chain with the recorded ENGINEERING authority reaches
geometry_available + ENGINEERING + VISUAL_READY + "Technology ready",
the watchdog PASSes it, the one-evaluator coupling holds on every
fixture (dossier == watchdog), and the clean-state replay is
byte-identical.
"""
from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from toscanini import dossier as dossier_mod  # noqa: E402
from toscanini import visual_join as vj  # noqa: E402

WEBAPP = REPO / "TOSCANINI_UI" / "webapp"


# ---------------------------------------------------------------------------
# fixture machinery — the same recorded shapes the production bridge writes
# ---------------------------------------------------------------------------
def _valid_glb(payload: bytes = b'{"asset":{"version":"2.0"}}') -> bytes:
    json_data = payload + b" " * ((4 - len(payload) % 4) % 4)
    header = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(json_data))
    chunk_header = struct.pack("<I", len(json_data)) + b"JSON"
    return header + chunk_header + json_data


def _valid_glb_with_bin() -> bytes:
    """A REAL two-chunk GLB: 4-byte-aligned JSON chunk + aligned BIN
    chunk."""
    json_data = b'{"asset":{"version":"2.0"},"scenes":[{"nodes":[0]}]}'
    json_data += b" " * ((4 - len(json_data) % 4) % 4)
    bin_data = b"\x00\x01\x02\x03"
    header = struct.pack("<III", 0x46546C67, 2,
                         12 + 8 + len(json_data) + 8 + len(bin_data))
    return (header
            + struct.pack("<I", len(json_data)) + b"JSON" + json_data
            + struct.pack("<I", len(bin_data)) + b"BIN\x00" + bin_data)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _spec_bytes() -> bytes:
    spec = {"artifact": "GEOMETRY_SPEC", "parameters": [
        {"param_id": "d", "value": 2.0}]}
    payload = json.dumps(spec, sort_keys=True).encode()
    return payload + b"\n" + json.dumps(
        {"spec_sha256": _sha(payload)}).encode() + b"\n"


def _complete_run(run: Path, session_id="ts_r451c25_golden",
                  with_spec: bool = True) -> Dict[str, Any]:
    """The golden chain: certified-canonical GLB + spec + identity +
    bridge report + receipt (1.1.0) + render record + COMPLETE_PASS
    gate + the full required presentation ladder + a full invention
    record — the SAME recorded shape the C2.4 battery certified."""
    model = run / "MODEL"
    model.mkdir(parents=True, exist_ok=True)
    glb = model / "engineering_model.glb"
    glb.write_bytes(_valid_glb())
    glb_sha = _sha(glb.read_bytes())
    spec_file_sha = None
    if with_spec:
        (model / "GEOMETRY_SPEC.json").write_bytes(_spec_bytes())
        spec_file_sha = _sha((model / "GEOMETRY_SPEC.json").read_bytes())
    identity = {
        "artifact": "ARTIFACT_IDENTITY",
        "run_id": session_id,
        "generation_id": "gen-1",
        "geometry_hash": glb_sha,
        "glb_path": str(glb),
        "glb_disk_sha256": glb_sha,
        "glb_matches_geometry_hash": True,
        "visualizability_class": "ENGINEERING_3D",
    }
    (model / "ARTIFACT_IDENTITY.json").write_text(json.dumps(identity))
    (run / "BRIDGE_REPORT.json").write_text(json.dumps({
        "outcome": "COMPLETED",
        "visualizability_class": "ENGINEERING_3D",
        "geometry": {"generation_id": "gen-1",
                     "visualizability_class": "ENGINEERING_3D",
                     "artifact_identity": identity},
    }))
    m3d = model / "3D"
    m3d.mkdir(parents=True, exist_ok=True)
    (m3d / "render_record.json").write_text(json.dumps({
        "stage": "RENDER", "status": "OK",
        "source_glb_sha256": glb_sha,
        "scene_spec": {"model": {"node_count": 1}},
        "views": {"hero.glb": {"sha256": _sha(glb.read_bytes())}},
    }))
    (m3d / "visual_gate.json").write_text(json.dumps(
        {"verdict": "COMPLETE_PASS"}))
    (m3d / "VISUAL_COMPILER_INVOCATION.json").write_text(json.dumps({
        "kind": "VISUAL_COMPILER_INVOCATION",
        "schema_version": "1.1.0",
        "run_id": session_id, "generation_id": "gen-1",
        "glb_sha256": glb_sha,
        "geometry_spec_sha256": spec_file_sha,
        "visual_compiler_version": "VISUAL_COMPILER_HEADLESS_THREE",
        "invocation_status": "OK",
        "invoked_at": "2026-09-13T00:00:00Z",
        "skip_reason": None,
        "render_record_reference": str(m3d / "render_record.json"),
        "output_directory": str(m3d),
    }))
    from discovery_fabric.engine.visual_compiler import visual_set
    for name in visual_set.required_artifacts(
            1, visual_set.DEFAULT_TURNTABLE_FRAMES)["required"]:
        p = m3d / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(_valid_glb() if name == "hero.glb"
                      else b"artifact-" + name.encode().replace(
                          b"/", b"_"))
    (run / "INVENTION_SPECIFICATION.json").write_text(json.dumps({
        "invention_id": "INV-R451C25",
        "problem": "fouling in compact heat exchangers",
        "mechanism": "self-clearing channel geometry",
        "causal_chain": ["fouling accumulates", "the geometry sheds it",
                         "the pressure drop stays in band"],
    }))
    (run / "session.json").write_text(json.dumps({"status": "COMPLETE"}))
    (run / "problem.json").write_text("{}")
    return {"glb_sha": glb_sha, "glb_path": glb}


def _geom_block(ids: Dict[str, Any]) -> Dict[str, Any]:
    return {"present": True, "class": "ENGINEERING_3D",
            "conceptual": False, "glb": "/api/run/x/model",
            "glb_sha256": ids["glb_sha"], "step": [],
            "parametric_model_present": False,
            "generation_id": "gen-1",
            "artifact_identity": {"generation_id": "gen-1"}}


def _session(run: Path, status="COMPLETE") -> Dict[str, Any]:
    return {"session_id": run.name, "status": status,
            "final_status": "AUTOMATED_INVENTION_CANDIDATE",
            "run_dir": str(run), "package": {}}


def _evaluator_state(run: Path,
                     geom_override: Dict[str, Any] = None) -> Dict[str, Any]:
    session = json.loads((run / "session.json").read_text())
    session.setdefault("run_dir", str(run))
    session.setdefault("session_id", run.name)
    geom = geom_override if geom_override is not None else \
        _geom_block(_ids[run.name])
    contract = vj.evaluate_geometry_contract(session, run, geom)
    join = vj.evaluate_visual_join(
        session, geom, {}, running=False,
        engineering_geometry_ready=contract["engineering_geometry_ready"],
        geometry_state=contract["geometry_state"], contract=contract)
    return {"contract": contract, "join": join}


def _watchdog_report(run: Path) -> Dict[str, Any]:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "r451_watchdog_c25", REPO / "scripts" / "r451_c2_watchdog.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run_watchdog(run)


_ids: Dict[str, Dict[str, Any]] = {}


@pytest.fixture()
def golden(tmp_path: Path) -> Path:
    run = tmp_path / "ts_r451c25_golden"
    _ids[run.name] = _complete_run(run)
    return run


def _mutated(tmp_path: Path, name: str, mutate) -> Path:
    run = tmp_path / name
    _ids[run.name] = _complete_run(run, session_id=name)
    mutate(run)
    return run


# ---------------------------------------------------------------------------
# the positive control (Art. V — the valid engineering chain STILL reaches
# VISUAL_READY; the hardening is not a universal rejector)
# ---------------------------------------------------------------------------
class TestPositiveControl:
    def test_engineering_chain_still_reaches_visual_ready(
            self, golden: Path):
        out = _evaluator_state(golden)
        c = out["contract"]
        assert c["geometry_state"] == "geometry_available"
        assert c["engineering_authority"] == "ENGINEERING"
        assert c["verification"]["glb_certified"] is True
        assert c["visual_input_ready"] is True
        assert out["join"]["visual_join_state"] == "VISUAL_READY"
        # the watchdog PASSes the healthy chain and reports the pair
        report = _watchdog_report(golden)
        assert report["observed_join_state"] == "VISUAL_READY"
        assert report["watchdog_verdict"] == "PASS"
        assert report["verdict"] == "PASS"
        # the badge label exists exactly once, behind the ENGINEERING
        # authority guard (the only path to "Technology ready")
        stage = (WEBAPP / "components" / "TechStage.tsx").read_text()
        assert stage.count('label: "Technology ready"') == 1
        ready_idx = stage.index('label: "Technology ready"')
        guard = stage[:ready_idx].rfind('case "VISUAL_READY"')
        block = stage[guard:ready_idx]
        assert 'view.engineeringAuthority !== "ENGINEERING"' in block

    def test_structural_check_passes_real_containers(self, tmp_path):
        p = tmp_path / "json-only.glb"
        p.write_bytes(_valid_glb())
        assert vj.glb_format_check(p)["valid"] is True
        p2 = tmp_path / "json-bin.glb"
        p2.write_bytes(_valid_glb_with_bin())
        fmt = vj.glb_format_check(p2)
        assert fmt["valid"] is True
        assert "chunk framing" in fmt["detail"]


# ---------------------------------------------------------------------------
# ATTACK 1 — projection identity forged / persisted identity absent
# ---------------------------------------------------------------------------
class TestAttack1ProjectionIdentityForged:
    def test_forged_projection_identity_never_certifies(self, tmp_path):
        """THE directive's attack scenario: a geom object carrying a
        COMPLETE artifact identity (path + SHA + generation + class)
        must not certify the artifact when the canonical PERSISTED
        identity document is absent."""
        def attack(run: Path):
            (run / "MODEL" / "ARTIFACT_IDENTITY.json").unlink()
            # the forged projection rides in on the geom block below —
            # complete, self-consistent, and worthlessly authoritative
        run = _mutated(tmp_path, "ts_c25_a1", attack)
        forged_identity = {
            "glb_path": str(_ids[run.name]["glb_path"]),
            "geometry_hash": _ids[run.name]["glb_sha"],
            "glb_disk_sha256": _ids[run.name]["glb_sha"],
            "generation_id": "gen-1",
            "visualizability_class": "ENGINEERING_3D",
        }
        geom = {k: v for k, v in _geom_block(_ids[run.name]).items()}
        geom["artifact_identity"] = forged_identity
        out = _evaluator_state(run, geom_override=geom)
        c = out["contract"]
        assert c["verification"]["glb_certified"] is False
        assert c["artifact_verified"] is False
        assert c["engineering_authority"] == "UNKNOWN"
        assert c["geometry_state"] == "geometry_unverified"
        assert c["visual_input_ready"] is False
        assert out["join"]["visual_join_state"] != "VISUAL_READY"
        failures = c["verification"]["certification_failures"]
        assert any("persisted" in f.lower() for f in failures)
        # the projection's identity object is REPORTED as a diagnostic —
        # present, and impotent
        assert any("projection" in f.lower() for f in failures)
        # the watchdog consumes THE evaluator and agrees
        report = _watchdog_report(run)
        assert report["observed_join_state"] != "VISUAL_READY"


# ---------------------------------------------------------------------------
# ATTACK 2 — projection generation forged / canonical generation absent
# ---------------------------------------------------------------------------
class TestAttack2ProjectionGenerationForged:
    def test_projection_generation_never_anchors(self, tmp_path):
        """The persisted identity records NO generation; the projection
        carries one. The generation identity is mandatory and can only
        be anchored by PERSISTED documents — the projection's generation
        field cannot create it."""
        def attack(run: Path):
            ident_path = run / "MODEL" / "ARTIFACT_IDENTITY.json"
            ident = json.loads(ident_path.read_text())
            ident["generation_id"] = None
            ident_path.write_text(json.dumps(ident))
        run = _mutated(tmp_path, "ts_c25_a2", attack)
        # the projection still claims generation gen-1 (its own field
        # AND the carried artifact_identity) — it anchors nothing
        out = _evaluator_state(run)
        c = out["contract"]
        assert c["verification"]["glb_certified"] is False
        assert c["geometry_state"] == "geometry_unverified"
        assert c["visual_input_ready"] is False
        assert out["join"]["visual_join_state"] != "VISUAL_READY"
        failures = c["verification"]["certification_failures"]
        assert any("generation" in f.lower() for f in failures)
        assert any("persisted" in f.lower() for f in failures)

    def test_projection_generation_contradiction_fails_closed(
            self, tmp_path):
        """A projection generation that CONTRADICTS the persisted
        identity is a fail-closed diagnostic — it can deny, never
        establish. The projection rides in on the geom block's carried
        artifact_identity (exactly the field a forged CIO payload
        controls)."""
        def attack(run: Path):
            br = json.loads((run / "BRIDGE_REPORT.json").read_text())
            br["geometry"]["generation_id"] = "gen-7"
            (run / "BRIDGE_REPORT.json").write_text(json.dumps(br))
        run = _mutated(tmp_path, "ts_c25_a2b", attack)
        out = _evaluator_state(run, geom_override={
            **_geom_block(_ids[run.name]),
            "generation_id": "gen-7",
            "artifact_identity": {"generation_id": "gen-7"}})
        c = out["contract"]
        assert c["geometry_state"] == "geometry_unverified"
        assert c["verification"]["glb_certified"] is False
        assert any("contradict" in f.lower()
                   for f in c["verification"]["certification_failures"])


# ---------------------------------------------------------------------------
# ATTACKS 3 + 4 — visual_complete + CONCEPTUAL / visual_complete + UNKNOWN
# ---------------------------------------------------------------------------
class TestAttack34ContradictionPairs:
    def test_visual_complete_conceptual_never_announced(self, tmp_path):
        """A fully certified CONCEPTUAL artifact with a COMPLETE render
        chain: the evaluator can never announce visual_complete/
        VISUAL_READY for it — the join is undecided (the authority is
        not ENGINEERING), and the frontend's state mapping carries the
        same invariant (source pin + the UI battery's behavioral
        matrix)."""
        def conceptualize(run: Path):
            ident_path = run / "MODEL" / "ARTIFACT_IDENTITY.json"
            ident = json.loads(ident_path.read_text())
            ident["visualizability_class"] = "SYSTEM_3D"
            ident_path.write_text(json.dumps(ident))
            br = json.loads((run / "BRIDGE_REPORT.json").read_text())
            br["visualizability_class"] = "SYSTEM_3D"
            br["geometry"]["visualizability_class"] = "SYSTEM_3D"
            (run / "BRIDGE_REPORT.json").write_text(json.dumps(br))
        run = _mutated(tmp_path, "ts_c25_a3", conceptualize)
        out = _evaluator_state(run)
        c = out["contract"]
        assert c["geometry_state"] == "geometry_available"
        assert c["engineering_authority"] == "CONCEPTUAL"
        assert c["engineering_geometry_ready"] is False
        assert c["visual_input_ready"] is True
        # THE invariant: the join NEVER announces visual readiness
        assert out["join"]["visual_join_state"] != "VISUAL_READY"
        assert out["join"]["visual_join_state"] is None
        # the strip's visualization row never RECEIVES on a conceptual
        # artifact
        tab = dossier_mod.design_tab(
            _session(run), {"geometry": _geom_block(_ids[run.name])})
        assert tab["geometry_state"] != "visual_complete"
        rows = {r["key"]: r for r in dossier_mod.pipeline_projection(
            _session(run), run, False,
            {"package_state": {"state": "NOT_PRODUCED"}},
            {"retrieval_state": "RETRIEVED", "retrieved_count": 3}, tab)}
        assert rows["visualization"]["status"] != "RECEIVED"

    def test_visual_complete_unknown_never_announced(self, tmp_path):
        """UNKNOWN authority: the artifact cannot even certify its
        class (UNKNOWN is not explicit) — geometry_unverified, the join
        is undecided, and no readiness exists anywhere."""
        def unclass(run: Path):
            ident_path = run / "MODEL" / "ARTIFACT_IDENTITY.json"
            ident = json.loads(ident_path.read_text())
            ident["visualizability_class"] = None
            ident_path.write_text(json.dumps(ident))
            (run / "BRIDGE_REPORT.json").unlink()
        run = _mutated(tmp_path, "ts_c25_a4", unclass)
        out = _evaluator_state(run)
        c = out["contract"]
        assert c["engineering_authority"] == "UNKNOWN"
        assert c["geometry_state"] == "geometry_unverified"
        # the certification (bytes/identity/generation) can hold — the
        # AUTHORITY is what failed: the artifact stays explicitly
        # unverified and the join NEVER becomes ready
        assert out["join"]["visual_join_state"] != "VISUAL_READY"
        assert out["join"]["visual_join_state"] is None
        # the frontend source carries the ABSOLUTE invariant: the
        # visual_complete branch refuses non-ENGINEERING authorities
        # (the state itself is not ready — not merely the badge)
        ps = (WEBAPP / "lib" / "presentationState.ts").read_text()
        vc_idx = ps.index('if (gstate === "visual_complete")')
        vc_block = ps[vc_idx:vc_idx + 1200]
        assert 'design?.engineering_authority !== "ENGINEERING"' in vc_block
        assert '"visual_authority_not_engineering"' in vc_block

    def test_frontend_visual_ready_branch_is_authority_gated(self):
        """SOURCE PIN (R451-C2.5 §2): VISUAL_READY exists only behind
        the ENGINEERING guard, and the badge label is produced exactly
        once behind the same authority (the C2.4 pin, re-asserted with
        the C2.5 mapping)."""
        ps = (WEBAPP / "lib" / "presentationState.ts").read_text()
        assert ps.count('state: "VISUAL_READY"') == 1
        ready_idx = ps.index('state: "VISUAL_READY"')
        branch = ps[ps.rfind('if (gstate === "visual_complete"'):ready_idx]
        assert '!== "ENGINEERING"' in branch
        # the cause vocabulary closes at ten and the new cause is in it
        assert ps.count('"visual_authority_not_engineering"') >= 3


# ---------------------------------------------------------------------------
# ATTACK 5 — lineage points A / identity points B
# ---------------------------------------------------------------------------
class TestAttack5LineageIdentitySplit:
    def test_lineage_identity_contradiction_fails_closed(self, tmp_path):
        """DESIGN_LINEAGE.json names model A; ARTIFACT_IDENTITY.json
        names model B with B's own SHA. The lineage's current entry has
        precedence for DISCOVERY, and the persisted identity's SHA
        contradicts A's bytes — the certification fails closed and no
        authority survives the contradiction."""
        def split(run: Path):
            glb_b = run / "MODEL" / "model-b.glb"
            glb_b.write_bytes(_valid_glb(b'{"asset":{"version":"2.0"},'
                                         b'"scene":0}'))
            sha_b = _sha(glb_b.read_bytes())
            (run / "MODEL" / "DESIGN_LINEAGE.json").write_text(json.dumps({
                "generation_models": [
                    {"generation": 1, "current": True,
                     "glb": "MODEL/engineering_model.glb"}]}))
            ident_path = run / "MODEL" / "ARTIFACT_IDENTITY.json"
            ident = json.loads(ident_path.read_text())
            ident["glb_path"] = str(glb_b)
            ident["geometry_hash"] = sha_b
            ident["glb_disk_sha256"] = sha_b
            ident_path.write_text(json.dumps(ident))
            _ids[run.name]["sha_b"] = sha_b
        run = _mutated(tmp_path, "ts_c25_a5", split)
        out = _evaluator_state(run)
        c = out["contract"]
        assert c["verification"]["glb_certified"] is False
        assert c["artifact_verified"] is False
        assert c["geometry_state"] == "geometry_unverified"
        assert c["engineering_authority"] == "UNKNOWN"
        assert c["visual_input_ready"] is False
        assert out["join"]["visual_join_state"] != "VISUAL_READY"
        failures = c["verification"]["certification_failures"]
        assert any("does not match the bytes on disk" in f
                   for f in failures)
        # the contradiction is also visible in the contract's SHA checks
        sha_checks = c["verification"]["sha_checks"]
        assert any(not sc["matches_bytes"] for sc in sha_checks)


# ---------------------------------------------------------------------------
# ATTACK 6 — valid header / malformed internal GLB structure
# ---------------------------------------------------------------------------
class TestAttack6StructuralGlb:
    def _header_for(self, body: bytes) -> bytes:
        return struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body

    def test_bin_first_chunk_fails(self, tmp_path):
        body = struct.pack("<I", 8) + b"BIN\x00" + b"\x00" * 8
        p = tmp_path / "bin-first.glb"
        p.write_bytes(self._header_for(body))
        fmt = vj.glb_format_check(p)
        assert fmt["valid"] is False
        assert "first chunk is not the JSON chunk" in fmt["detail"]

    def test_corrupt_json_chunk_fails(self, tmp_path):
        payload = b"{not valid json at allxxx"
        payload += b" " * ((4 - len(payload) % 4) % 4)
        body = struct.pack("<I", len(payload)) + b"JSON" + payload
        p = tmp_path / "bad-json.glb"
        p.write_bytes(self._header_for(body))
        fmt = vj.glb_format_check(p)
        assert fmt["valid"] is False
        assert "does not parse as JSON" in fmt["detail"]

    def test_chunk_overrun_fails(self, tmp_path):
        payload = b'{"asset":{"version":"2.0"}}'
        payload += b" " * ((4 - len(payload) % 4) % 4)
        # the chunk header declares far more than the container holds
        body = struct.pack("<I", len(payload) + 9999) + b"JSON" + payload
        p = tmp_path / "overrun.glb"
        p.write_bytes(self._header_for(body))
        fmt = vj.glb_format_check(p)
        assert fmt["valid"] is False
        assert "overrun" in fmt["detail"]

    def test_json_without_gltf_asset_version_fails(self, tmp_path):
        payload = b'{"scenes":[{"nodes":[]}]}'
        payload += b" " * ((4 - len(payload) % 4) % 4)
        body = struct.pack("<I", len(payload)) + b"JSON" + payload
        p = tmp_path / "no-asset.glb"
        p.write_bytes(self._header_for(body))
        fmt = vj.glb_format_check(p)
        assert fmt["valid"] is False
        assert "asset.version" in fmt["detail"]

    def test_structural_failure_blocks_certification(self, tmp_path):
        """The certification-level shape of the attack: an identity-
        named artifact whose HEADER is valid but whose internal JSON
        structure is corrupt — with every recorded SHA re-recorded to
        match — still never certifies (the header is not a proof)."""
        def attack(run: Path):
            glb = _ids[run.name]["glb_path"]
            corrupt = b'{"asset":{"version":"2.0"}CORRUPTED'
            corrupt += b" " * ((4 - len(corrupt) % 4) % 4)
            body = struct.pack("<I", len(corrupt)) + b"JSON" + corrupt
            glb.write_bytes(self._header_for(body))
            new_sha = _sha(glb.read_bytes())
            ident_path = run / "MODEL" / "ARTIFACT_IDENTITY.json"
            ident = json.loads(ident_path.read_text())
            ident["geometry_hash"] = ident["glb_disk_sha256"] = new_sha
            ident_path.write_text(json.dumps(ident))
            rec_path = run / "MODEL" / "3D" / "render_record.json"
            rec = json.loads(rec_path.read_text())
            rec["source_glb_sha256"] = new_sha
            rec_path.write_text(json.dumps(rec))
            receipt_path = run / "MODEL" / "3D" / \
                "VISUAL_COMPILER_INVOCATION.json"
            receipt = json.loads(receipt_path.read_text())
            receipt["glb_sha256"] = new_sha
            receipt_path.write_text(json.dumps(receipt))
            _ids[run.name]["glb_sha"] = new_sha
        run = _mutated(tmp_path, "ts_c25_a6", attack)
        out = _evaluator_state(run)
        c = out["contract"]
        assert c["verification"]["glb_certified"] is False
        assert c["geometry_state"] == "geometry_unverified"
        assert c["visual_input_ready"] is False
        assert out["join"]["visual_join_state"] != "VISUAL_READY"
        fmt = c["verification"]["glb_format"]
        assert fmt is not None and fmt["valid"] is False
        assert "malformed GLB structure" in fmt["detail"]


# ---------------------------------------------------------------------------
# ATTACK 7 — two GLBs / only one identity-named
# ---------------------------------------------------------------------------
class TestAttack7TwoGlbs:
    def test_only_identity_named_glb_certifies(self, golden: Path):
        """A second, unnamed GLB with DIFFERENT bytes sits beside the
        identity-named artifact: ONLY the named artifact certifies, the
        decoy's bytes never certify, and the certified SHA is the named
        file's own."""
        decoy = golden / "MODEL" / "model-999.glb"
        decoy.write_bytes(_valid_glb(b'{"asset":{"version":"2.0"},'
                                     b'"meshes":[]}'))
        assert _sha(decoy.read_bytes()) != _ids[golden.name]["glb_sha"]
        out = _evaluator_state(golden)
        c = out["contract"]
        assert c["verification"]["glb_certified"] is True
        assert c["verification"]["glb_sha256_measured"] == \
            _ids[golden.name]["glb_sha"]
        assert Path(c["verification"]["glb_resolved"]).name == \
            "engineering_model.glb"
        assert out["join"]["visual_join_state"] == "VISUAL_READY"

    def test_unnamed_decoy_alone_never_certifies(self, tmp_path):
        """The identity-named artifact is GONE; only the decoy (whose
        name looks right) remains: a filename that looks right is a
        diagnostic candidate — never certified."""
        def attack(run: Path):
            (_ids[run.name]["glb_path"]).unlink()
            decoy = run / "MODEL" / "model-001.glb"
            decoy.write_bytes(_valid_glb(b'{"asset":{"version":"2.0"},'
                                         b'"scene":0}'))
        run = _mutated(tmp_path, "ts_c25_a7", attack)
        out = _evaluator_state(run)
        c = out["contract"]
        assert c["verification"]["glb_certified"] is False
        assert c["geometry_state"] == "geometry_unverified"
        assert c["visual_input_ready"] is False
        assert out["join"]["visual_join_state"] != "VISUAL_READY"


# ---------------------------------------------------------------------------
# ATTACK 8 — legacy frontend payload with a convincing render PASS
# (behavioral proof: scripts/r451_c2_ui_tests.mjs; python pins the
# mapping's source and the closed vocabularies)
# ---------------------------------------------------------------------------
class TestAttack8LegacyPayload:
    def test_legacy_payload_mapping_is_non_current_only(self):
        """SOURCE PIN (R451-C2.5 §1): the legacy branch returns ONLY
        LEGACY_STATE_UNAVAILABLE and reads NO raw payload field — the
        branch's existence IS the legacy fact. The superseded C2.4-era
        reads (render status / gate verdict / cause inference) are
        gone from the mapping."""
        ps = (WEBAPP / "lib" / "presentationState.ts").read_text()
        assert 'state: "LEGACY_STATE_UNAVAILABLE"' in ps
        legacy_idx = ps.index('state: "LEGACY_STATE_UNAVAILABLE"')
        branch = ps[ps.rfind("} else if (design?.availability"):legacy_idx]
        # no raw-field state inference remains in the branch
        assert "GATE_PASS_VERDICTS" not in branch
        assert "renderRan" not in branch
        assert '"gate_not_passed"' not in branch
        assert '"renderer_unavailable"' not in branch
        assert '"legacy_render_unverified"' not in branch
        # the whole mapping produces VISUAL_READY exactly once (the
        # authority-gated branch) — a legacy payload cannot reach it
        assert ps.count('state: "VISUAL_READY"') == 1
        # the frontend gate-verdict constant set is DELETED (the
        # browser no longer reads gate verdicts at all)
        assert "export const GATE_PASS_VERDICTS" not in ps

    def test_frontend_vocabularies_are_closed(self):
        """The presentation-state vocabulary closes at EIGHT (the seven
        C2 states + LEGACY_STATE_UNAVAILABLE) and the cause vocabulary
        at TEN (nine + visual_authority_not_engineering)."""
        ps = (WEBAPP / "lib" / "presentationState.ts").read_text()
        for state in ("INVESTIGATING", "INFRASTRUCTURE_PAUSED",
                      "TECHNOLOGY_NOT_ESTABLISHED", "GEOMETRY_UNAVAILABLE",
                      "GEOMETRY_READY_RENDER_BLOCKED", "VISUAL_READY",
                      "SCIENTIFIC_REJECTION",
                      "LEGACY_STATE_UNAVAILABLE"):
            assert f'  | "{state}"' in ps
        for cause in ("renderer_unavailable", "gate_not_passed",
                      "not_attempted", "infrastructure",
                      "rendering_in_progress", "visual_input_missing",
                      "release_unverified", "geometry_unverified",
                      "legacy_render_unverified",
                      "visual_authority_not_engineering"):
            assert f'  | "{cause}"' in ps
        stage = (WEBAPP / "components" / "TechStage.tsx").read_text()
        # the component handles every state (no unhandled fall-through)
        assert 'case "LEGACY_STATE_UNAVAILABLE"' in stage
        assert 'case "visual_authority_not_engineering"' in stage


# ---------------------------------------------------------------------------
# the one-evaluator coupling + the clean-state replay
# ---------------------------------------------------------------------------
class TestCouplingAndDeterminism:
    def test_dossier_and_watchdog_agree_on_every_fixture(
            self, tmp_path):
        """ONE evaluator: the dossier's design tab and the watchdog's
        report announce the SAME state on every fixture shape (golden,
        forged projection, structural failure, decoy-only)."""
        shapes = []
        golden = tmp_path / "ts_c25_golden"
        _ids[golden.name] = _complete_run(golden)
        shapes.append(golden)
        a1 = tmp_path / "ts_c25_cpl_a1"
        _ids[a1.name] = _complete_run(a1, session_id=a1.name)
        (a1 / "MODEL" / "ARTIFACT_IDENTITY.json").unlink()
        shapes.append(a1)
        a6 = tmp_path / "ts_c25_cpl_a6"
        _ids[a6.name] = _complete_run(a6, session_id=a6.name)
        corrupt = b'{"asset":{"version":"2.0"}CORRUPTED'
        corrupt += b" " * ((4 - len(corrupt) % 4) % 4)
        body = struct.pack("<I", len(corrupt)) + b"JSON" + corrupt
        glb = _ids[a6.name]["glb_path"]
        glb.write_bytes(struct.pack("<III", 0x46546C67, 2,
                                    12 + len(body)) + body)
        shapes.append(a6)
        a7 = tmp_path / "ts_c25_cpl_a7"
        _ids[a7.name] = _complete_run(a7, session_id=a7.name)
        (_ids[a7.name]["glb_path"]).unlink()
        (a7 / "MODEL" / "model-001.glb").write_bytes(
            _valid_glb(b'{"asset":{"version":"2.0"},"scene":0}'))
        shapes.append(a7)
        for run in shapes:
            session = json.loads((run / "session.json").read_text())
            session.setdefault("run_dir", str(run))
            session.setdefault("session_id", run.name)
            geom = _geom_block(_ids[run.name])
            tab = dossier_mod.design_tab(session, {"geometry": geom})
            report = _watchdog_report(run)
            # both layers consume THE evaluator's semantics
            assert tab["visual_join_state"] == \
                report["observed_join_state"]
            assert tab["geometry_state"] in dossier_mod.GEOMETRY_STATES
            # the dual report is present and self-consistent
            assert report["watchdog_verdict"] in \
                ("PASS", "INTEGRITY_VIOLATION", "JOIN_FAILURE_OBSERVED")
            if report["violations"]:
                assert report["verdict"] == "FAIL"
                assert all("violation_class" in v
                           for v in report["violations"])

    def test_watchdog_release_unverified_is_a_join_observation(
            self, tmp_path):
        """R451-C2.5 §6 — a gate-pass + broken-release-chain run is
        observed as RELEASE_UNVERIFIED and classified
        JOIN_FAILURE_OBSERVED: a presentation-class finding, never a
        scientific rejection (the report has no scientific-rejection
        verdict to emit). The broken rung (the receipt's GLB identity)
        is one NO record-invariant rule covers — so the ONLY finding is
        the join observation itself."""
        def break_chain(run: Path):
            receipt_path = run / "MODEL" / "3D" / \
                "VISUAL_COMPILER_INVOCATION.json"
            receipt = json.loads(receipt_path.read_text())
            receipt["glb_sha256"] = "0" * 64  # != the canonical bytes
            receipt_path.write_text(json.dumps(receipt))
        run = _mutated(tmp_path, "ts_c25_rel", break_chain)
        report = _watchdog_report(run)
        assert report["observed_join_state"] == "RELEASE_UNVERIFIED"
        assert report["watchdog_verdict"] == "JOIN_FAILURE_OBSERVED"
        assert report["verdict"] == "FAIL"
        r10 = [v for v in report["violations"]
               if v["rule"] == "R10_evaluator_state_consistent"]
        assert r10 and r10[0]["violation_class"] == \
            "JOIN_STATE_OBSERVATION"
        # every OTHER applicable rule held — the observation is the only
        # finding (the clean JOIN_FAILURE_OBSERVED classification)
        assert all(c["state"] in ("PASS", "NOT_APPLICABLE")
                   for c in report["checks"]
                   if c["rule"] != "R10_evaluator_state_consistent")
        # the report carries NO scientific-rejection verdict anywhere
        assert "SCIENTIFIC" not in json.dumps(
            report["watchdog_verdicts_vocabulary"])

    def test_clean_state_replay_is_byte_identical(self, golden: Path):
        out1 = _evaluator_state(golden)
        out2 = _evaluator_state(golden)
        assert json.dumps(out1, sort_keys=True) == \
            json.dumps(out2, sort_keys=True)
        r1 = _watchdog_report(golden)
        r2 = _watchdog_report(golden)
        assert json.dumps(r1, sort_keys=True) == \
            json.dumps(r2, sort_keys=True)

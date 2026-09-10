"""R443 — the audit-fix regression suite.

Replicates the independent auditor's attacks (uploaded evidence:
toscanini-technology-audit.zip — fresh-package-audit.json,
independent-gate-tests.json, production-observations.json) as permanent
adversarial tests, so every fix is pinned by the exact defect class it
closes:

  A. Visual Quality Gate bypasses (independent-gate-tests.json):
     A1 geometry_attack — the exported hero GLB substituted with
        differently-shaped bytes while the renderer RECORD stayed
        unchanged: the OLD gate passed ("identical": true, "source":
        "untrusted renderer assertion"). The R443 gate re-measures both
        GLBs itself and MUST FAIL.
     A2 stripped_node_names — node names stripped from the raw GLB: the
        OLD naming check passed (trimesh synthesizes fallback names).
        The R443 check parses the raw glTF JSON chunk and MUST FAIL.
     A3 missing_required_views — only hero+poster produced (turntable/
        exploded/section/orthographic/dimension absent): the OLD gate
        passed. The R443 required-views check MUST FAIL and block the
        release.
     A4 source substitution — the canonical source GLB changed on disk
        after the scene was solved: the R443 source-hash re-verification
        MUST FAIL.
     A5 the honest full set still passes (the fix is not an
        over-rejector: paired positive control, Art. XVII).
  B. Geometry family archetypes (fresh-package-audit.json):
     B1 the audit's thermal case (fluidics subsystems, no thermal
        keywords) now carries heat_source/heat_sink/coolant_loop —
        family_feature + domain_architecture PASS.
     B2 every family satisfies its DOMAIN_ACCEPTANCE contract from the
        structural archetype alone (no mapping luck).
     B3 four unmapped modules: distinct placements — no_duplicate_model
        PASS, component_interference PASS (the audit's
        module_01==module_02 defect).
     B4 the stacked-duplicate attack (two parts at one cell) FAILS the
        interference witness (the R442 FEEDBACK DEFECT 2 class).
  C. model_route provenance (fresh-package-audit.json: 16 stage roles
     attributed to provider "unpaywall"):
     C1 evidence-source providers (unpaywall/EuropePMC) embedded in
        envelopes are never reported as stage model execution.
     C2 genuine LLM transport records (including a CALL_FAILED
        synthesize attempt) ARE reported with their roles.
  D. Retrieval routing (production-observations.json:
     fra_rail_accidents GRAMMAR_MISMATCH):
     D1 a free-text query planned for a date-grammar source becomes
        NOT_QUERIED_GRAMMAR — the engine never sends the mismatched
        question (the connector grammar gate stays as defense in
        depth).

Constitutional anchors: Art. III (verifier never trusts the claimant),
Art. V (fail closed), Art. XVII (every control has an attempted
bypass), Art. XXV (unknown stays unknown), Art. XXVIII (no silent
semantic promotion), Art. LXXII (visual gate verdict blocks release).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine.visual_compiler import visual_gate  # noqa: E402
from discovery_fabric.engine.visual_compiler import visual_set  # noqa: E402
from discovery_fabric.engine.invention_bridge.domain_spec import (  # noqa: E402
    derive_geometry_spec)
from discovery_fabric.engine.invention_bridge.domain_geometry import (  # noqa: E402
    build_domain_model)
from discovery_fabric.engine.invention_bridge import (  # noqa: E402
    geometry_quality_gate as gqg)


# ---------------------------------------------------------------------------
# shared fixtures
# ---------------------------------------------------------------------------
def _named_glb(path: Path, parts: Dict[str, Any]) -> Path:
    """A multi-part GLB with named nodes (trimesh scene export)."""
    import trimesh
    scene = trimesh.Scene()
    for name, box in parts.items():
        mesh = trimesh.creation.box(extents=box)
        mesh.apply_translation([box[0], 0.0, 0.0] if False else
                               [0.0, 0.0, 0.0])
        scene.add_geometry(mesh, node_name=name, geom_name=name)
    path.write_bytes(scene.export(file_type="glb"))
    return path


def _hero_png(path: Path, w: int = 100, h: int = 150) -> Path:
    """A gate-valid hero: solid model occupying the 0.70-0.85 band,
    grounded base, contact-shadow band below it."""
    arr = np.zeros((h, w, 4), np.uint8)
    top, base = int(h * 0.15), int(h * 0.847)
    left, right = int(w * 0.2), int(w * 0.8)
    arr[top:base, left:right] = [90, 90, 95, 255]
    shadow = base + 2
    arr[shadow:min(shadow + h // 12, h), left:right] = [30, 30, 34, 120]
    Image.fromarray(arr).save(path)
    return path


def _record_for(out: Path, source: Path, views: List[str]) -> Dict[str, Any]:
    """A render record whose view entries carry REAL sha256 hashes."""
    import hashlib
    rec: Dict[str, Any] = {
        "source_glb": str(source),
        "source_glb_sha256": hashlib.sha256(
            source.read_bytes()).hexdigest(),
        "views": {},
        "topology_comparison": {"identical": True},
    }
    for v in views:
        p = out / v
        if p.is_file():
            rec["views"][v] = {
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    return rec


def _strip_node_names(glb: Path) -> Path:
    """A TRUE raw-level name strip: rewrite the glTF JSON chunk with
    every node 'name' removed (the auditor's unnamed.glb — trimesh's
    own export always synthesizes names, so the strip must happen at
    the byte level, exactly like the attack)."""
    import struct
    raw = glb.read_bytes()
    json_len = int.from_bytes(raw[12:16], "little")
    doc = json.loads(raw[20:20 + json_len].decode("utf-8"))
    for node in doc.get("nodes") or []:
        node.pop("name", None)
    new_json = json.dumps(doc, separators=(",", ":")).encode("utf-8")
    # pad to 4-byte alignment with spaces (glTF JSON chunk padding)
    pad = (4 - len(new_json) % 4) % 4
    new_json += b" " * pad
    bin_header = raw[20 + json_len:28 + json_len]
    bin_data = raw[28 + json_len:]
    total = 12 + 8 + len(new_json) + len(bin_header) + len(bin_data)
    out = (raw[:8] + struct.pack("<I", total)
           + struct.pack("<I", len(new_json)) + b"JSON" + new_json
           + bin_header + bin_data)
    glb.write_bytes(out)
    return glb


def _spec_for(parts: Dict[str, Any]) -> Dict[str, Any]:
    names = list(parts.keys())
    return {
        "model": {
            "node_count": len(names),
            "nodes": [{"name": n} for n in names],
            "raw_size": [1.0, 1.0, 1.0],
            "center": [0.0, 0.5, 0.0],
            "min_y": 0.0,
            "min": [-0.5, 0.0, -0.5],
            "max": [0.5, 1.0, 0.5],
        },
        "grounding": {"scale": 0.5, "translate": [0.0, 0.0, 0.0]},
        "materials": {
            "mapping": {n: {"class": "metal"} for n in names}},
    }


@pytest.fixture()
def honest_render(tmp_path: Path) -> Dict[str, Any]:
    """The paired POSITIVE control: a complete, honest visual set
    (the full R443-C2 ladder: hero + poster + dimension + section +
    exploded pair + orthographic x4 + turntable x12 + hero.glb)."""
    out = tmp_path / "3D"
    out.mkdir()
    source = _named_glb(tmp_path / "model-001.glb", {
        "assembly_base": (2.0, 2.0, 0.4),
        "heat_source": (0.6, 0.6, 0.6),
    })
    exported = out / "hero.glb"
    exported.write_bytes(source.read_bytes())  # identical bytes
    _hero_png(out / "hero.png")
    (out / "poster.png").write_bytes((out / "hero.png").read_bytes())
    ladder = list(visual_set.UNCONDITIONAL) + [
        visual_set.TURNTABLE_PATTERN.format(n=i)
        for i in range(1, visual_set.DEFAULT_TURNTABLE_FRAMES + 1)] \
        + list(visual_set.CONDITIONAL)
    for v in ladder:
        if v.endswith(".glb"):
            continue
        p = out / v
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((out / "hero.png").read_bytes())
    (out / "exploded.glb").write_bytes(source.read_bytes())
    record = _record_for(out, source, ladder)
    spec = _spec_for({"assembly_base": None, "heat_source": None})
    spec["model"]["node_count"] = 2
    return {"out": out, "source": source, "record": record,
            "spec": spec, "ladder": ladder}


# ---------------------------------------------------------------------------
# A. the Visual Quality Gate bypasses (the auditor's attacks)
# ---------------------------------------------------------------------------
class TestGeometrySubstitutionAttack:
    """A1 — the exported hero GLB is substituted; the renderer record is
    unchanged (the exact geometry_attack from the audit)."""

    def test_substituted_exported_glb_fails(self, tmp_path: Path):
        out = tmp_path / "3D"
        out.mkdir()
        source = _named_glb(tmp_path / "model-001.glb", {
            "part_a": (1.0, 1.0, 1.0), "part_b": (0.5, 0.5, 0.5)})
        exported = out / "hero.glb"
        # the attacker's substitution: 1,1,1 -> 100,1,1 (audit extents)
        _named_glb(exported, {
            "part_a": (100.0, 1.0, 1.0), "part_b": (0.5, 0.5, 0.5)})
        record = {"source_glb": str(source),
                  "source_glb_sha256": "0" * 64,
                  "topology_comparison": {"identical": True}}
        res = visual_gate.independent_geometry_identity(
            str(source), exported)
        assert res["pass"] is False
        assert res.get("shape_changed_parts") == ["part_a"]

    def test_identical_bytes_pass(self, tmp_path: Path):
        out = tmp_path / "3D"
        out.mkdir()
        source = _named_glb(tmp_path / "model-001.glb", {
            "part_a": (1.0, 1.0, 1.0), "part_b": (0.5, 0.5, 0.5)})
        exported = out / "hero.glb"
        exported.write_bytes(source.read_bytes())
        res = visual_gate.independent_geometry_identity(
            str(source), exported)
        assert res["pass"] is True
        assert res["source"].startswith("independent re-measure")

    def test_full_gate_blocks_substitution(self, honest_render,
                                           tmp_path: Path):
        # the renderer record stays UNCHANGED (the audit's
        # renderer_record_unchanged: true) while the exported file is
        # swapped — the full gate must FAIL and block release
        _named_glb(honest_render["out"] / "hero.glb", {
            "assembly_base": (9.0, 1.0, 1.0), "heat_source": (0.6, 0.6, 0.6)})
        gate = visual_gate.evaluate(
            str(honest_render["out"]), honest_render["spec"],
            honest_render["record"], "OK")
        assert gate["checks"]["geometry_identity"]["pass"] is False
        assert gate["verdict"] == "FAIL"
        assert gate["release_blocked"] is True
        # the renderer's own assertion is recorded but NEVER the basis
        gi = gate["checks"]["geometry_identity"]
        assert gi["renderer_assertion"]["identical"] is True
        assert "corroboration" in gi["renderer_assertion_role"]

    def test_source_substitution_after_solve_fails(self,
                                                   honest_render):
        # A4 — the canonical source GLB changes on disk after the scene
        # was solved: the recorded source hash no longer matches
        _named_glb(honest_render["source"], {
            "assembly_base": (5.0, 5.0, 5.0), "heat_source": (1.0, 1.0, 1.0)})
        gate = visual_gate.evaluate(
            str(honest_render["out"]), honest_render["spec"],
            honest_render["record"], "OK")
        gi = gate["checks"]["geometry_identity"]
        assert gi.get("source_glb_sha256_match") is False
        assert gate["verdict"] == "FAIL"


class TestStrippedNodeNamesAttack:
    """A2 — node names stripped from the raw GLB (the audit's
    stripped_node_names: removed=1, raw_named_nodes=0, gate passed).
    R443-MERGED: the naming authority is check_canonical_node_identity
    (the R443-C2 raw glTF document walk); the merged gate carries it.
    """

    def test_stripped_names_fail_raw_document(self, tmp_path: Path):
        import trimesh
        scene = trimesh.Scene()
        mesh = trimesh.creation.box(extents=(1.0, 1.0, 1.0))
        scene.add_geometry(mesh, node_name="part_a", geom_name="part_a")
        glb = tmp_path / "stripped.glb"
        glb.write_bytes(scene.export(file_type="glb"))
        # the attack: names removed at the BYTE level (the auditor's
        # unnamed.glb) — loader fallback names must NOT rescue it
        _strip_node_names(glb)
        spec = _spec_for({"part_a": None})
        res = visual_gate.check_canonical_node_identity(glb, spec)
        assert res["pass"] is False
        assert any("ABSENT" in r for r in res.get("reasons", []))

    def test_named_glbs_pass_with_spec_parity(self, tmp_path: Path):
        glb = _named_glb(tmp_path / "named.glb", {"part_a": (1.0, 1.0, 1.0)})
        spec = _spec_for({"part_a": None})
        res = visual_gate.check_canonical_node_identity(glb, spec)
        assert res["pass"] is True


class TestMissingRequiredViews:
    """A3 — hero+poster only: the audit's files_present (hero.glb,
    hero.png, poster.png, unnamed.glb) with turntable/exploded/section/
    orthographic/dimension missing. R443-MERGED: the ladder authority
    is visual_set (the R443-C2 ladder — 23 artifacts, one definition);
    the merged gate adds view-hash integrity (swapped bytes FAIL)."""

    def test_missing_views_are_partial_and_blocked(self, honest_render):
        out = honest_render["out"]
        for v in honest_render["ladder"]:
            if v not in ("hero.png", "poster.png", "hero.glb"):
                p = out / v
                if p.is_file():
                    p.unlink()
        record = dict(honest_render["record"])
        record["views"] = {k: v for k, v in record["views"].items()
                           if k in ("hero.png", "poster.png",
                                    "hero.glb")}
        gate = visual_gate.evaluate(str(out), honest_render["spec"],
                                    record, "OK")
        rv = gate["checks"]["visual_set_completeness"]
        assert rv["pass"] is False
        assert set(rv["missing"]) >= {
            "dimension.png", "section.png",
            "orthographic/front.png", "turntable/frame-01.png"}
        # incomplete ladder alone = PARTIAL (never COMPLETE_PASS) —
        # release still blocked
        assert gate["verdict"] in ("PARTIAL", "FAIL")
        assert gate["release_blocked"] is True

    def test_typed_skip_of_required_view_is_not_a_pass(
            self, honest_render):
        # a "skipped" record entry does NOT complete the ladder: the
        # artifact is absent, the set is NOT complete, release blocked
        record = dict(honest_render["record"])
        record["views"] = dict(record["views"])
        (honest_render["out"] / "section.png").unlink()
        record["views"]["section.png"] = {
            "skipped": "renderer low-memory mid-render"}
        gate = visual_gate.evaluate(
            str(honest_render["out"]), honest_render["spec"],
            record, "OK")
        rv = gate["checks"]["visual_set_completeness"]
        assert "section.png" in rv["missing"]
        assert gate["verdict"] in ("PARTIAL", "FAIL")
        assert gate["release_blocked"] is True

    def test_single_part_exploded_is_a_typed_waiver(self):
        # the ONE architecture-legitimate waiver: a single-part model
        # has nothing to separate (disclosed, never faked)
        spec = visual_set.required_artifacts(node_count=1)
        assert "exploded.png" not in spec["required"]
        assert any(w["artifact"] == "exploded.png"
                   for w in spec["waived"])

    def test_view_bytes_swapped_after_render_fails(self,
                                                   honest_render):
        # a view file whose bytes no longer hash to the record: the
        # artifact was substituted post-render — a QUALITY failure
        # (FAIL), not merely an incomplete ladder (PARTIAL)
        out = honest_render["out"]
        (out / "dimension.png").write_bytes(b"attacker-bytes")
        gate = visual_gate.evaluate(
            str(out), honest_render["spec"], honest_render["record"],
            "OK")
        vh = gate["checks"]["view_hash_integrity"]
        assert vh["pass"] is False
        assert "dimension.png" in vh["sha256_mismatched"]
        assert gate["verdict"] == "FAIL"
        assert gate["release_blocked"] is True


class TestHonestFullSetPasses:
    """A5 — the paired positive controls: the honest complete set
    passes its integrity measures (the fix is not an over-rejector —
    Art. XVII). The full evaluate() COMPLETE_PASS path is covered by
    the R443-C2 suite (test_r443_visual_integrity.py); here the MERGED
    measures are positively controlled piecewise."""

    def test_identical_geometry_passes(self, honest_render):
        res = visual_gate.independent_geometry_identity(
            str(honest_render["source"]),
            honest_render["out"] / "hero.glb")
        assert res["pass"] is True

    def test_full_ladder_classifies_complete(self, honest_render):
        completeness = visual_set.classify(
            str(honest_render["out"]), node_count=2,
            turntable_frames=visual_set.DEFAULT_TURNTABLE_FRAMES)
        assert completeness["complete"] is True
        assert completeness["missing"] == []

    def test_full_ladder_view_hashes_verify(self, honest_render):
        completeness = visual_set.classify(
            str(honest_render["out"]), node_count=2,
            turntable_frames=visual_set.DEFAULT_TURNTABLE_FRAMES)
        mism = visual_gate._verify_view_hashes(
            honest_render["out"], honest_render["record"], completeness)
        assert mism == []

    def test_gate_not_run_fails_closed_with_completeness(
            self, tmp_path: Path):
        gate = visual_gate.evaluate(str(tmp_path / "nope"), {}, {},
                                    "RENDER_SKIPPED_LOW_MEMORY")
        assert gate["verdict"] == "NOT_RUN"
        assert gate["release_blocked"] is True
        assert gate["visual_set"]["complete"] is False


# ---------------------------------------------------------------------------
# B. the geometry family archetypes (the fresh-package-audit defects)
# ---------------------------------------------------------------------------
AUDIT_THERMAL_SUBSYSTEMS = [
    "flow path / lumen architecture",
    "pressure regulation element",
    "sensing / feedback element (if closed-loop)",
    "termination interfaces (application-context-specific: "
    "source and sink boundaries)",
]

FAMILIES = {
    # VEHICLE keeps the R433 mapping-derived contract on purpose: the
    # acceptance set is the SOLAR-EV case, and a battery-EV must NOT
    # get an invented solar roof (the R442 boundary: geometry is
    # causally derived — the semantic gate surfaces unmapped acceptance
    # components as not_visualized instead of inventing them). Its
    # fixture here maps the solar case explicitly.
    "VEHICLE": ["roof solar array", "battery pack", "traction motor",
                "power electronics", "thermal management loop"],
    "MEDICAL_DEVICE": ["flow lumen", "therapy lumen", "sensor band"],
    "FLUID_DEVICE": ["inlet port", "outlet port", "valve stage",
                     "chamber"],
    "THERMAL_SYSTEM": AUDIT_THERMAL_SUBSYSTEMS,
    "MECHANICAL_COMPONENT": ["shaft", "bearing", "spring", "housing",
                             "load path"],
    "ELECTRONIC_SYSTEM": ["power stage", "connectors", "thermal path"],
    "ENERGY_STORAGE": ["cell stack", "bus bars", "thermal barrier"],
}

# families whose acceptance contract is DEFINITIONAL of the family
# label (guaranteed structurally by the archetype; recorded subsystems
# map onto the slots as provenance aliases — never invented content)
DEFINITIONAL_FAMILIES = {k: v for k, v in FAMILIES.items()
                         if k != "VEHICLE"}


class TestFamilyArchetypes:
    def test_audit_thermal_case_passes_every_gate(self):
        # THE audit case: heat-exchanger problem, fluidics-style
        # subsystems — previously family_feature + domain_architecture
        # FAILED (heat_source/heat_sink never in the spec); now the
        # family archetype guarantees them with honest provenance.
        spec = derive_geometry_spec(
            "THERMAL_SYSTEM", AUDIT_THERMAL_SUBSYSTEMS, "hx")
        ids = {c["component_id"] for c in spec["components"]}
        assert {"heat_source", "heat_sink", "coolant_loop"} <= ids
        out = build_domain_model(spec)
        res = gqg.run_all_gates(out["glb_bytes"], spec, "THERMAL_SYSTEM")
        assert res["passed"] is True, res["failures"]
        sem = gqg.semantic_identity_gate(
            spec, out["glb_bytes"], "THERMAL_SYSTEM")
        assert sem["passed"] is True, sem["failures"]
        scores = gqg.score_technology_model(
            spec, out["glb_bytes"], "THERMAL_SYSTEM")
        for k in ("semantic_identity", "engineering_coherence",
                  "presentation_quality"):
            assert scores[k]["passed"] is True, (k, scores[k])

    def test_every_family_satisfies_domain_acceptance(self):
        # the acceptance contract no longer depends on mapping luck for
        # the DEFINITIONAL families: the archetype carries it; recorded
        # subsystems map as aliases. VEHICLE is the honest exception —
        # its solar-EV acceptance is mapping-derived and surfaced
        # honestly by the semantic gate (never invented geometry).
        for family, subs in DEFINITIONAL_FAMILIES.items():
            spec = derive_geometry_spec(family, subs, "site")
            ids = {c["component_id"] for c in spec["components"]}
            for required in gqg.DOMAIN_ACCEPTANCE[family]:
                assert required in ids, (family, required)
        spec = derive_geometry_spec(
            "VEHICLE", FAMILIES["VEHICLE"], "site")
        ids = {c["component_id"] for c in spec["components"]}
        for required in gqg.DOMAIN_ACCEPTANCE["VEHICLE"]:
            assert required in ids, ("VEHICLE", required)

    def test_four_modules_no_duplicates_no_interference(self):
        # the audit's module_01==module_02 defect: four unmapped
        # subsystems get four DISTINCT cells
        for family in FAMILIES:
            spec = derive_geometry_spec(family, [
                "recorded subsystem alpha", "recorded subsystem beta",
                "recorded subsystem gamma", "recorded subsystem delta"],
                "site")
            out = build_domain_model(spec)
            geo = gqg.geometry_quality_gate(
                out["glb_bytes"], spec, family)
            assert geo["passed"] is True, (family, geo["failures"])

    def test_stacked_duplicate_attack_fails(self):
        # the R442 FEEDBACK DEFECT 2 class: distinct named parts at one
        # cell = engineering-realization failure (unless mated)
        import trimesh
        spec = derive_geometry_spec(
            "THERMAL_SYSTEM", AUDIT_THERMAL_SUBSYSTEMS, "hx")
        scene = trimesh.Scene()
        box = trimesh.creation.box(extents=(1.1, 0.9, 0.8))
        scene.add_geometry(box, node_name="module_01")
        scene.add_geometry(box.copy(), node_name="module_02")
        ok, measured = gqg.component_interference_witness(scene, spec)
        assert ok is False
        assert measured["same_cell_unmated"] == [{
            "pair": "module_01==module_02",
            "overlap_fraction_min_part": 1.0,
            "overlap_fraction_max_part": 1.0,
            "mating_declared": False,
        }]

    def test_mated_co_location_is_disclosed_not_failed(self):
        # the R442 FEEDBACK DEFECT 3 discipline: an INTENTIONAL mating
        # recorded in the canonical spec (interfaces[]) is disclosed,
        # never a silent pass-through and never a false failure
        import trimesh
        spec = derive_geometry_spec(
            "THERMAL_SYSTEM", AUDIT_THERMAL_SUBSYSTEMS, "hx")
        scene = trimesh.Scene()
        box = trimesh.creation.box(extents=(1.1, 0.9, 0.8))
        scene.add_geometry(box, node_name="coolant_loop")
        scene.add_geometry(box.copy(), node_name="heat_source")
        ok, measured = gqg.component_interference_witness(scene, spec)
        assert ok is True
        rel = measured["nested_disclosed"]
        assert any(d["pair"] == "coolant_loop==heat_source"
                   and d["mating_declared"] for d in rel)


# ---------------------------------------------------------------------------
# C. model_route provenance (the 16-roles-attributed-to-unpaywall defect)
# ---------------------------------------------------------------------------
class TestModelRouteProvenance:
    @staticmethod
    def _fake_run(tmp_path: Path) -> Path:
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        # the audit replica: every envelope embeds evidence records whose
        # provenance.provider is a retrieval source (unpaywall)
        evidence = [{"title": "record", "provenance": {
            "provider": "unpaywall", "retrieved_at": "2026-09-10",
            "api_version": "v2", "query_or_method": "search"}}]
        for stage in ("RETRIEVE", "FREEZE", "PREMISE_GATE", "SYNTHESIZE",
                      "VERIFY", "MULTI_SOURCE_DISCOVERY", "COLLISION",
                      "PHYSICS", "ATTACK", "CONTRADICTION",
                      "KILLER_EXPERIMENT", "ADJUDICATION", "CLASSIFY",
                      "NEXT_BEST_ACTION", "RANK", "MECHANISM_SPACE"):
            (run_dir / f"envelope_{stage}.json").write_text(json.dumps({
                "stage": stage,
                "status": "SKIPPED_UPSTREAM_FAILURE",
                "evidence": evidence,
            }))
        # the ONE genuine model-call record: the failed synthesize
        # transport (typed CALL_FAILED — honest execution provenance)
        (run_dir / "envelope_SYNTHESIZE.json").write_text(json.dumps({
            "stage": "SYNTHESIZE", "status": "FAILED_EXPLICIT",
            "evidence": evidence,
            "transport": {"provider": "nvidia", "model": "glm-4.7",
                          "status": "CALL_FAILED",
                          "failure_type": "CALL_FAILED",
                          "latency_ms": 812},
        }))
        return run_dir

    def test_no_evidence_source_attributed_as_model_execution(
            self, tmp_path: Path):
        import toscanini.run_state as rs
        run_dir = self._fake_run(tmp_path)
        session = {"evidence_pack": {
            "llm": {"provider": "openrouter", "status": "OK"}}}
        route = rs._model_route(session, run_dir)
        providers = [c.get("provider") for c in route["calls"]]
        # the measured defect: unpaywall attributed to 16 roles
        assert "unpaywall" not in providers
        roles = [c.get("role") for c in route["calls"]]
        # skipped stages contribute NO model execution
        for stage in ("ADJUDICATION", "RANK", "FREEZE",
                      "NEXT_BEST_ACTION"):
            assert stage not in roles
        # the honest route: the extraction LLM + the typed synthesize
        # failure (execution attempted, transport failed)
        assert "evidence_extraction" in roles
        assert "SYNTHESIZE" in roles
        syn = next(c for c in route["calls"]
                   if c.get("role") == "SYNTHESIZE")
        assert syn["provider"] == "nvidia"
        assert syn["status"] == "CALL_FAILED"

    def test_llm_transport_records_still_reported(self, tmp_path: Path):
        import toscanini.run_state as rs
        run_dir = tmp_path / "run2"
        run_dir.mkdir()
        (run_dir / "envelope_ATTACK.json").write_text(json.dumps({
            "attack_results": {"transport": {
                "provider": "zai", "model": "glm-4.7",
                "status": "OK", "latency_ms": 3200}}})),
        route = rs._model_route({}, run_dir)
        roles = [c.get("role") for c in route["calls"]]
        assert roles == ["ATTACK"]
        assert route["calls"][0]["provider"] == "zai"


# ---------------------------------------------------------------------------
# D. retrieval routing (the fra_rail_accidents GRAMMAR_MISMATCH defect)
# ---------------------------------------------------------------------------
class TestDateGrammarRouting:
    def test_free_text_never_sent_to_date_grammar_source(self,
                                                         tmp_path: Path,
                                                         monkeypatch):
        import toscanini.problem_builder as pb
        sent: List[Dict[str, Any]] = []

        def fake_search(name, role, cls, query, timeout=40):
            sent.append({"source": name, "role": role, "query": query})
            return {"source": name, "role": role, "status": "OK",
                    "count": 0, "records": [], "relevant": 0,
                    "error": None}

        monkeypatch.setattr(pb, "_search_one", fake_search)
        monkeypatch.setattr(
            pb, "extract_problem_fields",
            lambda text: {
                "domain": "industrial",
                "device": "countercurrent heat exchanger",
                "failure_mode": "FOULING-DRIVEN HEAT TRANSFER DECAY",
                "failure_query": "heat exchanger fouling decay",
                "science_query": "heat exchanger fouling",
                "_llm": {"status": "SKIP", "provider": None,
                         "latency_ms": 0},
            })
        result = pb.build_problem(
            "Independent audit case: a passive countercurrent heat "
            "exchanger recovering heat from 40C industrial wastewater "
            "while managing fouling-prone suspended solids.")
        rows = {r["source"]: r for r in result["evidence_pack"]["retrieval"]}
        # the audit's defect: fra_rail_accidents queried with free text
        # -> GRAMMAR_MISMATCH (engine routing error). Now: the router
        # refuses BEFORE the request — a typed routing decision.
        assert rows["fra_rail_accidents"]["status"] == \
            "NOT_QUERIED_GRAMMAR"
        assert not any(s["source"] == "fra_rail_accidents" for s in sent)
        # the honest family state: doe_osti carries its R399 W3
        # SUSPENDED_RELEVANCE routing decision (typed, disclosed — the
        # audit observed exactly this row); NO free-text query was sent
        # to any date-grammar source and no routing error was burned
        assert rows["doe_osti"]["status"] == \
            "NOT_QUERIED_SUSPENDED_RELEVANCE"
        # the problem statement carries the honest routing note
        assert any("fra_rail_accidents" in n
                   for n in result["problem"]["failure"].split("ROUTING:"))

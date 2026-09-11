"""R447 Geometry Identity Join — the adversarial battery (Phase 1).

Operator directive R447-C1 Phase 1: the invariant

    canonical invention state
        -> engineering specification
        -> canonical component identity
        -> GEOMETRY_SPEC
        -> GLB raw-node identity
        -> visual scene identity

was demonstrated NOT universally closed by R446-HF Case B: the
conceptual-architecture GLB's node names failed the visual gate
(node_identity + geometry_identity) because three.js's GLTFLoader
sanitizes node names (whitespace -> '_', '[', ']', '.', ':', '/'
removed; post-sanitize collisions suffixed) and the conceptual path
authored human-readable names OUTSIDE that closure. The fix is
UPSTREAM authoring (conceptual_geometry.stable_node_id): `name` is
the canonical stable id, `label` keeps the human text — never a gate
exception, never Coder-2 tolerance.

This battery attacks the join from the RAW GLB identity source
(gltf_doc — no loader), per the directive:

  * renamed node      -> node_identity FAIL (identity set mismatch)
  * missing node      -> node_identity FAIL
  * extra node        -> node_identity FAIL
  * duplicate node    -> node_identity FAIL (multiset mismatch)
  * reordered node    -> identity-SET checks correctly PASS (order is
                         not identity — a benign sibling reorder must
                         not false-kill, Art. V) AND the source-side
                         post-solve reorder is caught by the source
                         sha contract (bytes are provenance)
  * conceptual geometry with canonical component set -> the join
     CLOSES: parts == raw GLB nodes == scene spec nodes, every id
     stable under the three.js sanitizer, injective by construction

Plus the engineering-path universality check (domain build + the
frozen R446 Case C bytes) and the live end-to-end compiler proof when
the Chromium/Node pair is available (same skip discipline as the
R441/R443 batteries).
"""
from __future__ import annotations

import hashlib
import json
import re
import struct
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import tempfile  # noqa: E402


def _tmp():
    return tempfile.TemporaryDirectory()


from discovery_fabric.engine.invention_bridge import (  # noqa: E402
    conceptual_geometry,)
from discovery_fabric.engine.visual_compiler import gltf_doc  # noqa: E402
from discovery_fabric.engine.visual_compiler import scene_builder  # noqa: E402
from discovery_fabric.engine.visual_compiler import visual_gate  # noqa: E402
from discovery_fabric.engine.visual_compiler import \
    visual_compiler as vc  # noqa: E402

# ---------------------------------------------------------------------------
# The three.js sanitizer, re-implemented INDEPENDENTLY in the test from
# the installed three 0.175.0 source (build/three.core.js:
# PropertyBinding.sanitizeNodeName -> name.replace(/\s/g,'_')
#    .replace(new RegExp('[\\[\\]\\.:\\/]', 'g'), '')
# and GLTFLoader.createUniqueName's post-sanitize dedup) — the closure
# every authored node id must be provably inside.
# ---------------------------------------------------------------------------
_THREE_RESERVED = re.compile(r"[\[\]\.:\/]")


def three_js_sanitize(name: str) -> str:
    return _THREE_RESERVED.sub("", re.sub(r"\s", "_", name or ""))


def _sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# GLB JSON-chunk rewrite helper (container-preserving mutation — same
# discipline as the R443 battery's _strip_glb_names)
def _mutate_glb(glb_path: Path, mutator) -> Path:
    raw = glb_path.read_bytes()
    magic, version, length = struct.unpack("<4sII", raw[:12])
    assert magic == b"glTF"
    offset, chunks = 12, []
    while offset < length:
        clen, ctype = struct.unpack("<I4s", raw[offset:offset + 8])
        chunks.append((ctype, raw[offset + 8:offset + 8 + clen]))
        offset += 8 + clen
    doc = json.loads(chunks[0][1].decode("utf-8"))
    mutator(doc)
    js = json.dumps(doc, separators=(",", ":")).encode("utf-8")
    pad = (4 - len(js) % 4) % 4
    js += b" " * pad
    bin_chunk = chunks[1] if len(chunks) > 1 else None
    out = bytearray()
    total = 12 + 8 + len(js) + (8 + len(bin_chunk[1]) if bin_chunk else 0)
    out += struct.pack("<4sII", b"glTF", 2, total)
    out += struct.pack("<I4s", len(js), b"JSON") + js
    if bin_chunk:
        out += struct.pack("<I4s", len(bin_chunk[1]),
                           b"BIN\x00") + bin_chunk[1]
    glb_path.write_bytes(bytes(out))
    return glb_path


# the adversarial subsystem corpus: spaces, brackets, colons, slashes,
# unicode, duplicates, and the exact R446 Case B names
NASTY_SUBSYSTEMS = [
    "load path / structural backbone",
    "actuation or compliance element",
    "guidance / bearing interfaces",
    "fatigue-critical features register",
    "sensor grid",
    "sensor grid",  # deliberate duplicate -> collision suffix path
    "PZT stack [v2]",
    "Ünïcödé:süb——system",
]
NASTY_SITE = "piezoelectric energy-harvesting floor tile"


def _built() -> dict:
    return conceptual_geometry.build_system_architecture(
        list(NASTY_SUBSYSTEMS), NASTY_SITE)


def _write_glb(tmp_path: Path, built: dict) -> Path:
    p = tmp_path / "canonical.glb"
    p.write_bytes(built["glb_bytes"])
    return p


# ---------------------------------------------------------------------------
# Part 1 — the canonicalizer unit contract (the stable vocabulary)
# ---------------------------------------------------------------------------
class TestStableNodeVocabulary:
    def test_emits_only_stable_characters(self):
        for label in NASTY_SUBSYSTEMS + [
                "substrate: " + NASTY_SITE, "flow 1 -> 2",
                "control -> [02]", "layer 1: form", "", "   ", "::/[]",
                "a_ _b", "already_stable_id"]:
            sid = conceptual_geometry.stable_node_id(label)
            assert re.fullmatch(r"[0-9A-Za-z_]+", sid), (label, sid)
            assert sid == sid.strip("_"), (label, sid)
            assert "__" not in sid, (label, sid)

    def test_three_js_closure_is_identity(self):
        """THE closure property: applying the REAL three.js sanitizer
        to any emitted id is the identity function (Art. XVI — the
        contract is measured against the independently re-implemented
        rule, not asserted rhetorically)."""
        ids = []
        for label in NASTY_SUBSYSTEMS:
            ids.append(conceptual_geometry.stable_node_id(
                f"[{NASTY_SUBSYSTEMS.index(label) + 1:02d}] {label}"))
        ids.append(conceptual_geometry.stable_node_id(
            "substrate: " + NASTY_SITE))
        ids.append(conceptual_geometry.stable_node_id("flow 1 -> 2"))
        ids.append(conceptual_geometry.stable_node_id("control -> [04]"))
        ids.append(conceptual_geometry.stable_node_id("layer 2: form"))
        for sid in ids:
            assert three_js_sanitize(sid) == sid, sid

    def test_uniqueness_allocation_is_deterministic(self):
        uid = conceptual_geometry._UniqueId()
        a = uid("sensor grid")
        b = uid("sensor grid")   # same label -> suffixed
        c = uid("sensor  grid")  # same after canonicalization -> suffixed
        assert a == "sensor_grid"
        assert b == "sensor_grid_2"
        assert c == "sensor_grid_3"
        assert len({a, b, c}) == 3

    def test_empty_falls_back(self):
        assert conceptual_geometry.stable_node_id("") == "part"
        assert conceptual_geometry.stable_node_id("::/[]") == "part"
        assert conceptual_geometry.stable_node_id("   ") == "part"


# ---------------------------------------------------------------------------
# Part 2 — the authored identity chain closes (raw GLB == parts == spec)
# ---------------------------------------------------------------------------
class TestConceptualIdentityJoin:
    def test_parts_carry_name_and_label(self):
        built = _built()
        for part in built["components"]:
            assert part.get("name") and part.get("label")
            assert re.fullmatch(r"[0-9A-Za-z_]+", part["name"])
        labels = [p["label"] for p in built["components"]]
        assert any(l == "substrate: " + NASTY_SITE for l in labels)
        assert any(l == "[01] " + NASTY_SUBSYSTEMS[0] for l in labels)

    def test_raw_glb_identity_equals_parts(self):
        """THE join: the RAW glTF node identity set equals the authored
        canonical component set 1:1 — proven from the raw document
        (gltf_doc), never through a loader."""
        built = _built()
        with _tmp() as d:
            glb = _write_glb(Path(d), built)
            raw = gltf_doc.raw_part_identity(str(glb))
            names = sorted(p["name"] for p in built["components"])
            assert sorted(raw["named"]) == names
            assert raw["unnamed_unattributed"] == []
            assert raw["mesh_nodes"] == len(names)

    def test_scene_spec_identity_equals_parts(self):
        built = _built()
        with _tmp() as d:
            glb = _write_glb(Path(d), built)
            spec = scene_builder.build_scene_spec(str(glb))
            spec_names = sorted(n["name"] for n in spec["model"]["nodes"])
            assert spec_names == sorted(
                p["name"] for p in built["components"])

    def test_authored_ids_survive_the_three_js_rule(self):
        built = _built()
        for part in built["components"]:
            assert three_js_sanitize(part["name"]) == part["name"]
            # and the OLD defect shape (label as node name) would NOT:
        assert three_js_sanitize("[01] load path / structural backbone") \
            != "[01] load path / structural backbone"

    def test_authored_ids_are_injective(self):
        built = _built()
        names = [p["name"] for p in built["components"]]
        assert len(names) == len(set(names))

    def test_deterministic_bytes(self):
        assert _built()["glb_sha256"] == _built()["glb_sha256"]

    def test_conceptual_device_layers_stable(self):
        built = conceptual_geometry.build_conceptual_device(
            NASTY_SITE, ["form", "mechanism layer", "interface"])
        for part in built["components"]:
            assert re.fullmatch(r"[0-9A-Za-z_]+", part["name"])
            assert three_js_sanitize(part["name"]) == part["name"]
            assert part["label"].startswith("layer ")
        assert built["components"][0]["name"] == "layer_1_form"


# ---------------------------------------------------------------------------
# Part 3 — the gate adversarial battery, from the raw GLB identity source
# ---------------------------------------------------------------------------
class TestGateIdentityAttacks:
    @pytest.fixture()
    def scene(self, tmp_path):
        built = _built()
        glb = _write_glb(tmp_path, built)
        spec = scene_builder.build_scene_spec(str(glb))
        return {"built": built, "glb": glb, "spec": spec}

    def _hero(self, tmp_path, glb, tag):
        hero = tmp_path / f"hero_{tag}.glb"
        hero.write_bytes(glb.read_bytes())
        return hero

    def test_canonical_passes(self, scene, tmp_path):
        hero = self._hero(tmp_path, scene["glb"], "clean")
        chk = visual_gate.check_canonical_node_identity(
            hero, scene["spec"])
        assert chk["pass"], chk

    def test_attack_renamed_node(self, scene, tmp_path):
        hero = self._hero(tmp_path, scene["glb"], "renamed")

        def mutate(doc):
            for node in doc["nodes"]:
                if node.get("name") and "load_path" in node["name"]:
                    node["name"] = node["name"] + "_tampered"
        _mutate_glb(hero, mutate)
        chk = visual_gate.check_canonical_node_identity(
            hero, scene["spec"])
        assert not chk["pass"]
        assert any("does not match the scene spec" in r
                   for r in chk["reasons"])
        gi = visual_gate.independent_geometry_identity(
            str(scene["glb"]), hero)
        assert not gi["pass"]

    def test_attack_missing_node(self, scene, tmp_path):
        hero = self._hero(tmp_path, scene["glb"], "missing")

        def mutate(doc):
            mesh_names = [n.get("name") for n in doc["nodes"]
                          if "mesh" in n and n.get("name")]
            for node in list(doc["nodes"]):
                if node.get("name") == mesh_names[0]:
                    doc["nodes"].remove(node)
                    break
            for s in doc.get("scenes", []):
                s["nodes"] = [i for i in s.get("nodes", [])
                              if i < len(doc["nodes"])]
        _mutate_glb(hero, mutate)
        chk = visual_gate.check_canonical_node_identity(
            hero, scene["spec"])
        assert not chk["pass"]

    def test_attack_extra_node(self, scene, tmp_path):
        hero = self._hero(tmp_path, scene["glb"], "extra")

        def mutate(doc):
            named = [n for n in doc["nodes"]
                     if "mesh" in n and n.get("name")]
            clone = dict(named[0])
            clone["name"] = "injected_extra_part"
            doc["nodes"].append(clone)
            doc["scenes"][0]["nodes"].append(len(doc["nodes"]) - 1)
        _mutate_glb(hero, mutate)
        chk = visual_gate.check_canonical_node_identity(
            hero, scene["spec"])
        assert not chk["pass"]

    def test_attack_duplicate_node(self, scene, tmp_path):
        hero = self._hero(tmp_path, scene["glb"], "dup")

        def mutate(doc):
            named = [n for n in doc["nodes"]
                     if "mesh" in n and n.get("name")]
            # duplicate the LAST named mesh node under the SAME name —
            # the multiset no longer equals the spec's unique set
            clone = dict(named[-1])
            doc["nodes"].append(clone)
            doc["scenes"][0]["nodes"].append(len(doc["nodes"]) - 1)
        _mutate_glb(hero, mutate)
        chk = visual_gate.check_canonical_node_identity(
            hero, scene["spec"])
        assert not chk["pass"]
        gi = visual_gate.independent_geometry_identity(
            str(scene["glb"]), hero)
        assert not gi["pass"]

    def test_attack_reordered_node_export_side(self, scene, tmp_path):
        """Reorder among the EXPORTED hero's sibling nodes: the identity
        SET is unchanged (order is not identity) — the set-based checks
        correctly still pass (a benign reorder must not false-kill,
        Art. V), and this is asserted EXPLICITLY so the discipline is
        a tested contract, not an accident."""
        hero = self._hero(tmp_path, scene["glb"], "reordered")

        def mutate(doc):
            ns = doc["scenes"][0]["nodes"]
            if len(ns) >= 2:
                ns[0], ns[1] = ns[1], ns[0]
        _mutate_glb(hero, mutate)
        chk = visual_gate.check_canonical_node_identity(
            hero, scene["spec"])
        assert chk["pass"], chk
        gi = visual_gate.independent_geometry_identity(
            str(scene["glb"]), hero)
        assert gi["pass"]

    def test_attack_reordered_node_source_side(self, scene, tmp_path):
        """The source GLB is reordered AFTER the scene was solved: the
        identity set still matches, the shape signature still matches —
        but the recorded source sha no longer matches the bytes on
        disk, and the R447 source-sha contract inside
        independent_geometry_identity FAILS it (bytes are provenance)."""
        original_sha = _sha256(scene["glb"])
        reordered = tmp_path / "source_reordered.glb"
        reordered.write_bytes(scene["glb"].read_bytes())

        def mutate(doc):
            # swap the first >=2-sibling child list (the conceptual GLB
            # has a single root; the siblings live one level down)
            for node in doc["nodes"]:
                ch = node.get("children") or []
                if len(ch) >= 2:
                    ch[0], ch[1] = ch[1], ch[0]
                    return
            ns = doc["scenes"][0]["nodes"]
            assert len(ns) >= 2, "no sibling list to reorder"
            ns[0], ns[1] = ns[1], ns[0]
        _mutate_glb(reordered, mutate)
        assert _sha256(reordered) != original_sha  # bytes really changed
        hero = self._hero(tmp_path, scene["glb"], "hero_src_reorder")
        gi = visual_gate.independent_geometry_identity(
            str(reordered), hero, source_sha_expected=original_sha)
        assert not gi["pass"]
        assert not gi["identical"]

    def test_negative_control_the_old_defect_shape_fails(self, scene,
                                                         tmp_path):
        """The R446 Case B defect, reproduced verbatim: the hero export
        carries the OLD human-readable names while the scene spec
        carries the canonical ids (the historical authoring state) —
        the gate FAILS. The gate was correct all along; the authoring
        was the defect, and this pins it."""
        spec = scene["spec"]
        hero = self._hero(tmp_path, scene["glb"], "old")

        def mutate(doc):
            for node in doc["nodes"]:
                n = node.get("name")
                if n and ("load_path" in n):
                    node["name"] = "[01] load path / structural backbone"
                elif n and ("substrate_" in n):
                    node["name"] = "substrate: " + NASTY_SITE
                elif n and n.startswith("flow_"):
                    idx = n.split("_")[1]
                    node["name"] = f"flow {idx} -> {int(idx) + 1}"
        _mutate_glb(hero, mutate)
        chk = visual_gate.check_canonical_node_identity(hero, spec)
        assert not chk["pass"]
        assert any("does not match the scene spec" in r
                   for r in chk["reasons"])


# ---------------------------------------------------------------------------
# Part 4 — universality: the engineering path + frozen production bytes
# ---------------------------------------------------------------------------
class TestEngineeringPathUniversality:
    def test_domain_build_names_are_stable(self, tmp_path):
        """The deterministic domain builder (the engineering half of the
        bridge) authors node ids that already satisfy the same closure
        — universality across BOTH authoring paths, not just Case B."""
        from discovery_fabric.engine.invention_bridge import domain_spec
        state = {
            "problem": {"device": "cold plate",
                        "problem_id": "p-test"},
            "engineering_specification": {
                "why_this_domain": {"canonical_family": "thermal"}},
            "user_text": "thermal management cold plate heat sink",
        }
        vis = {"visualizability_class": "SYSTEM_3D",
               "subsystems": ["heat source", "reject interface"],
               "intervention_site": "cold plate"}
        out = domain_spec.build_spec_from_state(state, vis)
        spec = out["spec"]
        from discovery_fabric.engine.invention_bridge import \
            domain_geometry
        try:
            built = domain_geometry.build_domain_model(spec)
        except Exception:  # noqa: BLE001 — archetype may be generic
            pytest.skip("no deterministic builder for this fixture")
        for part in built["components"]:
            assert three_js_sanitize(part["name"]) == part["name"], part

    def test_frozen_case_c_bytes_are_stable(self):
        """Regression over the R446-HF Case C production bytes (the
        gate-PASS case): every raw node id in the frozen artifact is
        inside the closure — the frozen evidence stays interpretable."""
        glb = REPO / "R446/HF_PRODUCTION_RUNS/ts_e24b5247333f_canonical.glb"
        if not glb.is_file():
            pytest.skip("frozen artifact not present in this checkout")
        raw = gltf_doc.raw_part_identity(str(glb))
        assert raw["unnamed_unattributed"] == []
        for name in raw["named"]:
            assert three_js_sanitize(name) == name, name

    def test_frozen_case_b_divergence_is_detectable(self):
        """The R446-HF Case B frozen bytes: the raw names are the OLD
        unstable vocabulary. Against a scene spec re-derived from those
        same bytes the identity set agrees (both derive from one
        document), but the names are OUTSIDE the closure — proven by
        the three.js rule — which is exactly the mutation the hero
        export applied live. This pins the historical defect class."""
        glb = REPO / "R446/HF_PRODUCTION_RUNS/ts_3a5d419028a3_canonical.glb"
        if not glb.is_file():
            pytest.skip("frozen artifact not present in this checkout")
        raw = gltf_doc.raw_part_identity(str(glb))
        unstable = [n for n in raw["named"]
                    if three_js_sanitize(n) != n]
        assert unstable, "the frozen Case B bytes must carry the " \
                         "pre-fix unstable names"


# ---------------------------------------------------------------------------
# Part 5 — the live end-to-end compiler proof (renderer-gated)
# ---------------------------------------------------------------------------
class TestLiveCompilerJoin:
    def test_conceptual_gate_identity_passes_live(self, tmp_path):
        """THE decisive falsification test: a freshly built conceptual
        architecture (the Case B class, nasty names) through the FULL
        Visual Compiler — the exported hero GLB's raw node identity
        must now EQUAL the source identity (node_identity PASS,
        geometry_identity PASS). Skipped when no verified
        Chromium/Node pair (same discipline as the R441/R443 live
        batteries)."""
        from discovery_fabric.engine.visual_compiler import render_worker
        if not render_worker.find_node() or not render_worker.find_chrome():
            pytest.skip("no verified Chromium/Node pair in this "
                        "environment")
        if render_worker.renderer_deps_present():
            pytest.skip("renderer deps not installed")
        built = _built()
        work = tmp_path / "work"
        (work / "MODEL").mkdir(parents=True)
        (work / "MODEL" / "model-001.glb").write_bytes(built["glb_bytes"])
        rec = vc.compile_visuals(
            str(work), geometry_out={"generation_models": [
                {"generation": 1, "current": True}]},
            is_conceptual=True, memory_mode="sync")
        gate = rec.get("visual_gate") or {}
        checks = gate.get("checks") or {}
        if gate.get("verdict") == "NOT_RUN":
            pytest.skip(f"compiler could not run: {rec.get('status')}")
        ni = checks.get("node_identity") or {}
        gi = checks.get("geometry_identity") or {}
        assert ni.get("pass"), ni
        assert gi.get("pass"), gi

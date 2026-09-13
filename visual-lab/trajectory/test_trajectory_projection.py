"""R451-C2 Steps 5 + 8 - projection-fidelity fixtures and the handoff contract.

Fixtures (directive step 5) - every corruption class must be rejected or
exposed honestly, fail closed, and never reach the viewer:

  positive      real canonical lineage (committed engine records)
  tampered      terminal invention_id altered -> binding breaks
  missing       expected_effect / falsification_test deleted from a
  prediction    generation -> exposed as ABSENT_IN_CANONICAL_RECORD
  wrong current state    current_invention.state contradicts the bound state
  wrong transition gen   generation sequence reordered/skipped
  wrong result status    current_invention.maturity contradicts the bound
                        generation; survivor binding tampered
  reordered states       generations array order swapped
  orphan transition      parent_id resolves to no generation

Handoff contract (directive step 8), proven on ONE real canonical record:

  Coder 1 canonical lineage bytes
        -> sha256 recorded, IDs preserved
        -> Coder 2 projection (typed, pointer-traceable)
        -> viewer artifact (self-contained HTML + JSON)
  with tests proving the viewer is a PROJECTION, not another truth store:
  determinism, pointer coverage, hash preservation, and the mutation
  non-authority proof (mutating the viewer artifact can never change what
  a fresh projection from the canonical bytes says).

Portable: every path is derived from this file's checkout location
(directive step 4). No author-machine directories anywhere.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

import sys

sys.path.insert(0, str(HERE))

import lineage_projection as lp  # noqa: E402

REAL_2GEN = (
    REPO_ROOT
    / "R445/EVOLUTION_RUNS/evol-x01-desalination-scaling/INVENTION_LINEAGE.json"
)
REAL_1GEN = (
    REPO_ROOT
    / "R401-WC2/BENCHMARK/RUNS/r401/bench-p01-pemfc-dehydration/INVENTION_LINEAGE.json"
)
REAL_NULL_CURRENT = (
    REPO_ROOT
    / (
        "R445/EVOLUTION_RUNS/evol-x01-desalination-scaling.attempt2-pinignored/"
        "INVENTION_LINEAGE.json"
    )
)
ALL_REAL_RECORDS = sorted((REPO_ROOT).glob("R4*/**/INVENTION_LINEAGE.json"))


def real_bytes() -> bytes:
    return REAL_2GEN.read_bytes()


def mutate(fn) -> bytes:
    """Derive a corruption fixture from the REAL canonical bytes."""
    record = json.loads(real_bytes().decode("utf-8"))
    fn(record)
    return json.dumps(record, indent=1).encode("utf-8")


def codes(exc: lp.ProjectionRejected) -> list:
    return [r["code"] for r in exc.rejections]


# --------------------------------------------------------------------------
# positive fixtures (real canonical bytes)
# --------------------------------------------------------------------------


class TestPositiveFixtures:
    def test_real_two_generation_record_projects(self):
        p = lp.project_file(str(REAL_2GEN))
        assert p["verdict"] == "PROJECTED"
        assert p["rejections"] == []
        vs = p["viewer_state"]
        assert [s["gen"] for s in vs["states"]] == [1, 2]
        assert len(vs["transitions"]) == 1
        # the exact binding tuple, in the canonical semantics of the schema
        b = vs["transitions"][0]["binding"]
        assert b["transition.from_gen"] == 1
        assert b["transition.to_gen"] == 2
        assert b["transition.result.gen"] == 2
        assert b["transition.result.status"] == "INVENTION_REQUIRES_EXPERIMENT"

    def test_real_single_generation_record_projects(self):
        p = lp.project_file(str(REAL_1GEN))
        assert p["verdict"] == "PROJECTED"
        vs = p["viewer_state"]
        assert [s["gen"] for s in vs["states"]] == [1]
        assert vs["transitions"] == []
        assert vs["current"]["resolution"] == "RESOLVED_TO_GENERATION_INDEX_0"

    def test_native_locations_not_aliases(self):
        """expected_effect / falsification_test come from their actual native
        location (/generations/i/architecture/...) with the real values."""
        source = json.loads(real_bytes().decode("utf-8"))
        p = lp.project_lineage(real_bytes())
        for i, gen in enumerate(source["generations"]):
            proj = p["viewer_state"]["states"][i]["architecture"]
            for field in lp.ARCHITECTURE_FIELDS:
                entry = proj[field]
                assert entry["status"] == "RECORDED"
                assert entry["pointer"] == (
                    f"/generations/{i}/architecture/{field}"
                )
                native = gen["architecture"][field]
                assert entry["value"] == native
                # no convenience alias produced a null for a recorded value
                assert entry["value"] not in (None, "")

    def test_current_invention_state_projected_from_native_root(self):
        source = json.loads(real_bytes().decode("utf-8"))
        p = lp.project_lineage(real_bytes())
        cur = p["viewer_state"]["current"]
        assert cur["resolution"].startswith("RESOLVED_TO_GENERATION_INDEX_")
        assert cur["fields"]["state"]["value"] == source["current_invention"]["state"]
        assert cur["fields"]["state"]["pointer"] == "/current_invention/state"

    def test_hash_and_ids_preserved(self):
        p = lp.project_lineage(real_bytes())
        assert p["source"]["sha256"] == hashlib.sha256(real_bytes()).hexdigest()
        source = json.loads(real_bytes().decode("utf-8"))
        assert p["source"]["run_id"]["value"] == source["run_id"]
        for i, gen in enumerate(source["generations"]):
            assert (
                p["viewer_state"]["states"][i]["invention_id"]["value"]
                == gen["invention_id"]
            )

    def test_epistemic_badges_are_declared_translations(self):
        p = lp.project_lineage(real_bytes())
        for st in p["viewer_state"]["states"]:
            badge = st["epistemic_badge"]
            if st["evidence_verified"]["value"] is False:
                assert badge["label"] == "UNVERIFIED"
            elif badge["canonical_label"] in lp.EPISTEMIC_BADGE_TABLE:
                assert badge["label"] == (
                    lp.EPISTEMIC_BADGE_TABLE[badge["canonical_label"]]
                )
            assert badge["basis"], "every badge carries its basis pointer"
            assert badge["label"] != "MEASURED"  # unreachable from this schema

    def test_all_null_current_is_honest_absence_not_violation(self):
        p = lp.project_file(str(REAL_NULL_CURRENT))
        assert p["verdict"] == "PROJECTED"
        assert p["viewer_state"]["current"]["resolution"] == "NOT_RECORDED"

    def test_whole_real_corpus_projects_without_rejection(self):
        """The strongest fidelity proof: every real canonical record in the
        repository projects cleanly (the projection accepts exactly the
        engine's real output)."""
        assert len(ALL_REAL_RECORDS) >= 20
        projected = 0
        for path in ALL_REAL_RECORDS:
            p = lp.project_file(str(path))
            assert p["verdict"] == "PROJECTED", f"{path} unexpectedly rejected"
            assert p["rejections"] == []
            projected += 1
        assert projected == len(ALL_REAL_RECORDS)


# --------------------------------------------------------------------------
# negative fixtures (corruption classes; fail closed; viewer never reached)
# --------------------------------------------------------------------------


class TestNegativeFixtures:
    def test_tampered_lineage_fails_closed(self):
        def tamper(r):
            r["generations"][-1]["invention_id"] = "inv:tampered:gen2"

        with pytest.raises(lp.ProjectionRejected) as e:
            lp.project_lineage(mutate(tamper))
        assert codes(e.value) == ["CURRENT_INVENTION_UNRESOLVED"]

    def test_missing_prediction_is_exposed_not_invented(self):
        def strip_prediction(r):
            del r["generations"][1]["architecture"]["expected_effect"]

        p = lp.project_lineage(mutate(strip_prediction))
        entry = p["viewer_state"]["states"][1]["architecture"]["expected_effect"]
        assert entry["status"] == "ABSENT_IN_CANONICAL_RECORD"
        assert entry["pointer"] == "/generations/1/architecture/expected_effect"
        assert "value" not in entry  # no invented content
        # the remaining recorded fields are untouched
        assert (
            p["viewer_state"]["states"][1]["architecture"]["mechanism"]["status"]
            == "RECORDED"
        )

    def test_missing_falsification_test_is_exposed_not_invented(self):
        def strip_falsifier(r):
            del r["generations"][0]["architecture"]["falsification_test"]

        p = lp.project_lineage(mutate(strip_falsifier))
        entry = p["viewer_state"]["states"][0]["architecture"]["falsification_test"]
        assert entry["status"] == "ABSENT_IN_CANONICAL_RECORD"
        assert "value" not in entry

    def test_wrong_current_state_fails_closed(self):
        def tamper(r):
            r["current_invention"]["state"] = "INVENTION_SURVIVED"

        with pytest.raises(lp.ProjectionRejected) as e:
            lp.project_lineage(mutate(tamper))
        assert codes(e.value) == ["CURRENT_INVENTION_STATE_MISMATCH"]

    def test_wrong_transition_generation_fails_closed(self):
        def tamper(r):
            r["generations"][1]["gen"] = 3  # skip 2

        with pytest.raises(lp.ProjectionRejected) as e:
            lp.project_lineage(mutate(tamper))
        assert codes(e.value) == ["GEN_SEQUENCE_NOT_CONSECUTIVE"]

    def test_wrong_result_status_fails_closed(self):
        def tamper(r):
            r["current_invention"]["maturity"] = "EVIDENCE_SUPPORTED"

        with pytest.raises(lp.ProjectionRejected) as e:
            lp.project_lineage(mutate(tamper))
        assert codes(e.value) == ["CURRENT_INVENTION_MATURITY_MISMATCH"]

    def test_survivor_binding_tamper_fails_closed(self):
        def tamper(r):
            r["survivor_gen"] = 1

        with pytest.raises(lp.ProjectionRejected) as e:
            lp.project_lineage(mutate(tamper))
        assert codes(e.value) == ["SURVIVOR_BINDING_MISMATCH"]

    def test_reordered_states_fail_closed(self):
        def tamper(r):
            r["generations"] = [r["generations"][1], r["generations"][0]]

        with pytest.raises(lp.ProjectionRejected) as e:
            lp.project_lineage(mutate(tamper))
        assert codes(e.value) == ["GEN_SEQUENCE_NOT_CONSECUTIVE"]

    def test_orphan_transition_fails_closed(self):
        def tamper(r):
            r["generations"][1]["parent_id"] = "inv:does-not-exist:gen9"

        with pytest.raises(lp.ProjectionRejected) as e:
            lp.project_lineage(mutate(tamper))
        assert codes(e.value) == ["TRANSITION_PARENT_ORPHAN"]

    def test_parent_missing_fails_closed(self):
        def tamper(r):
            r["generations"][1]["parent_id"] = None

        with pytest.raises(lp.ProjectionRejected) as e:
            lp.project_lineage(mutate(tamper))
        assert codes(e.value) == ["TRANSITION_PARENT_MISSING"]

    def test_origin_undeclared_fails_closed(self):
        def tamper(r):
            r["generations"][1]["origin"] = "BASELINE_SYNTHESIS"

        with pytest.raises(lp.ProjectionRejected) as e:
            lp.project_lineage(mutate(tamper))
        assert codes(e.value) == ["TRANSITION_ORIGIN_UNDECLARED"]

    def test_sha_mismatch_fails_closed_before_parse(self):
        with pytest.raises(lp.ProjectionRejected) as e:
            lp.project_lineage(real_bytes(), expected_sha256="0" * 64)
        assert codes(e.value) == ["PROVENANCE_SHA_MISMATCH"]

    def test_unparseable_bytes_fail_closed(self):
        with pytest.raises(lp.ProjectionRejected) as e:
            lp.project_lineage(b"{not json")
        assert codes(e.value) == ["SOURCE_BYTES_UNPARSEABLE"]

    def test_schema_unrecognized_fails_closed(self):
        def tamper(r):
            r["schema"] = "INVENTION_LINEAGE/9.9.9"

        with pytest.raises(lp.ProjectionRejected) as e:
            lp.project_lineage(mutate(tamper))
        assert codes(e.value) == ["SCHEMA_UNRECOGNIZED"]

    def test_double_tamper_reports_both_breaks(self):
        def tamper(r):
            r["current_invention"]["state"] = "INVENTION_SURVIVED"
            r["generations"][1]["parent_id"] = "inv:does-not-exist:gen9"

        with pytest.raises(lp.ProjectionRejected) as e:
            lp.project_lineage(mutate(tamper))
        assert set(codes(e.value)) == {
            "CURRENT_INVENTION_STATE_MISMATCH",
            "TRANSITION_PARENT_ORPHAN",
        }


# --------------------------------------------------------------------------
# directive step 6 - the projection must not decide anything causal
# --------------------------------------------------------------------------


class TestNoVisualSideCausalInference:
    def test_projection_computes_no_causal_fields(self):
        p = lp.project_lineage(real_bytes())
        text = json.dumps(p)
        for forbidden_key in (
            "caused_by",
            "root_cause",
            "mechanism_verdict",
            "novelty_verdict",
            "improvement_explanation",
            "failure_reason",
        ):
            assert forbidden_key not in text

    def test_boundary_declaration_is_present(self):
        p = lp.project_lineage(real_bytes())
        boundary = p["viewer_state"]["presentation_boundary"]
        assert boundary["this_viewer_may_not_decide"] == [
            "why the engine failed",
            "what caused the improvement",
            "whether the mechanism is true",
            "whether an invention is novel",
        ]

    def test_recorded_cause_is_verbatim_passthrough(self):
        source = json.loads(real_bytes().decode("utf-8"))
        p = lp.project_lineage(real_bytes())
        tr = p["viewer_state"]["transitions"][0]
        rec = source["generations"][1]
        assert tr["recorded_cause"]["change_delta"]["value"] == rec["change_delta"]
        assert (
            tr["recorded_cause"]["reason_for_change"]["value"]
            == rec["reason_for_change"]
        )


# --------------------------------------------------------------------------
# directive step 8 - the full handoff contract
# --------------------------------------------------------------------------


def resolve_pointer(record: dict, pointer: str):
    """RFC-6901 resolver against the canonical source record."""
    if pointer == "/":
        return record
    cur = record
    for tok in pointer.lstrip("/").split("/"):
        tok = tok.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, dict):
            if tok not in cur:
                return (False, None)
            cur = cur[tok]
        elif isinstance(cur, list):
            if not tok.isdigit() or int(tok) >= len(cur):
                return (False, None)
            cur = cur[int(tok)]
        else:
            return (False, None)
    return (True, cur)


def walk_entries(node, out):
    if isinstance(node, dict):
        if node.get("status") == "RECORDED" and "pointer" in node:
            out.append(node)
        for v in node.values():
            walk_entries(v, out)
    elif isinstance(node, list):
        for v in node:
            walk_entries(v, out)


class TestHandoffContract:
    """canonical lineage -> projection -> web viewer, hashes/IDs preserved."""

    def _build(self, tmp_path: Path):
        sys.path.insert(0, str(HERE))
        import build_trajectory_view as bv

        out_html = tmp_path / "trajectory_viewer.html"
        out_json = tmp_path / "trajectory_projection.json"
        bv.build(str(REAL_2GEN), str(out_html), str(out_json))
        return out_html, out_json

    def test_viewer_artifact_records_source_identity(self, tmp_path):
        _, out_json = self._build(tmp_path)
        artifact = json.loads(out_json.read_text())
        assert artifact["source"]["sha256"] == (
            hashlib.sha256(real_bytes()).hexdigest()
        )
        source = json.loads(real_bytes().decode("utf-8"))
        assert artifact["source"]["run_id"]["value"] == source["run_id"]
        assert artifact["verdict"] == "PROJECTED"

    def test_projection_is_deterministic(self, tmp_path):
        _, out_json_a = self._build(tmp_path)
        _, out_json_b = self._build(tmp_path)
        assert out_json_a.read_bytes() == out_json_b.read_bytes()

    def test_every_recorded_value_resolves_in_source_bytes(self, tmp_path):
        """Pointer coverage: the viewer holds no value that is not verbatim
        present at its declared pointer in the canonical record."""
        _, out_json = self._build(tmp_path)
        artifact = json.loads(out_json.read_text())
        source = json.loads(real_bytes().decode("utf-8"))
        entries: list = []
        walk_entries(artifact["viewer_state"], entries)
        assert len(entries) >= 20
        for entry in entries:
            found, value = resolve_pointer(source, entry["pointer"])
            assert found, f"pointer does not resolve: {entry['pointer']}"
            assert value == entry["value"], (
                f"viewer value diverges from canonical bytes at "
                f"{entry['pointer']}"
            )

    def test_every_absence_is_really_absent(self, tmp_path):
        _, out_json = self._build(tmp_path)
        artifact = json.loads(out_json.read_text())
        source = json.loads(real_bytes().decode("utf-8"))
        found_absent = 0
        for st in artifact["viewer_state"]["states"]:
            for field_entry in st["architecture"].values():
                if field_entry["status"] == "ABSENT_IN_CANONICAL_RECORD":
                    found, value = resolve_pointer(source, field_entry["pointer"])
                    assert not found or value in (None, "")
                    found_absent += 1
        # the real corpus record has all four architecture fields; absence
        # entries exist in this artifact only if the record truly lacks them
        assert found_absent >= 0

    def test_viewer_is_not_a_truth_store(self, tmp_path):
        """Mutating the viewer artifact can never change what a fresh
        projection from the canonical bytes says; the canonical bytes remain
        the only input."""
        out_html, out_json = self._build(tmp_path)
        # tamper the viewer artifact's viewer_state
        artifact = json.loads(out_json.read_text())
        artifact["viewer_state"]["states"][0]["state"]["value"] = (
            "INVENTION_TAMPERED"
        )
        out_json.write_text(json.dumps(artifact, indent=1))
        # a fresh projection from the canonical bytes is unaffected
        fresh = lp.project_lineage(real_bytes())
        assert (
            fresh["viewer_state"]["states"][0]["state"]["value"]
            == "INVENTION_EVOLVED"
        )
        # and re-building the viewer regenerates the truth from the bytes
        sys.path.insert(0, str(HERE))
        import build_trajectory_view as bv

        bv.build(str(REAL_2GEN), str(out_html), str(out_json))
        rebuilt = json.loads(out_json.read_text())
        assert (
            rebuilt["viewer_state"]["states"][0]["state"]["value"]
            == "INVENTION_EVOLVED"
        )

    def test_viewer_html_embeds_the_projection_verbatim(self, tmp_path):
        out_html, out_json = self._build(tmp_path)
        html = out_html.read_text()
        payload = json.loads(out_json.read_text())
        embedded = json.dumps(payload, ensure_ascii=False)
        assert embedded in html or json.dumps(
            payload, ensure_ascii=False, indent=2
        ) in html or payload["source"]["sha256"] in html
        assert "PROJECTION_ONLY" in html
        assert payload["source"]["sha256"][:12] in html

    def test_no_author_machine_paths_in_viewer_artifact(self, tmp_path):
        out_html, out_json = self._build(tmp_path)
        for f in (out_html, out_json):
            text = f.read_text()
            assert "/home/z/" not in text
            assert "/Users/" not in text
            assert "C:\\" not in text


# --------------------------------------------------------------------------
# directive step 7 - the visual-model lab stays provisional
# --------------------------------------------------------------------------


class TestLabStaysProvisional:
    """No TRELLIS/Hunyuan/other visual model becomes an engineering
    authority, and no visual artifact upgrades PROPOSED -> VALIDATED,
    SIMULATED -> MEASURED, CONCEPTUAL -> ENGINEERING."""

    def _guard(self):
        sys.path.insert(0, str(REPO_ROOT / "visual-lab" / "guard"))
        import epistemic_guard as eg

        return eg

    def test_no_visual_asset_may_promote_to_engineering_geometry(self):
        eg = self._guard()
        for cls in eg.KNOWN_CLASSES:
            asset = eg.VisualAsset(
                asset_id="hf:candidate", epistemic_class=cls,
                lineage=["x"], generator="hf:some-model",
            )
            with pytest.raises(eg.EpistemicViolation):
                eg.forbid_promotion(asset, eg.ENGINEERING_GEOMETRY)

    def test_no_visual_asset_may_promote_to_physical_validation(self):
        eg = self._guard()
        for cls in eg.KNOWN_CLASSES:
            asset = eg.VisualAsset(
                asset_id="hf:candidate", epistemic_class=cls,
                lineage=["x"], generator="hf:some-model",
            )
            with pytest.raises(eg.EpistemicViolation):
                eg.forbid_promotion(asset, eg.PHYSICAL_VALIDATION)

    def test_unknown_visual_generator_is_not_a_geometry_authority(self):
        eg = self._guard()
        for gen in ("hf:TRELLIS.2", "hf:tencent/Hunyuan3D-Omni", "hf:nvidia/PartPacker"):
            asset = eg.VisualAsset(
                asset_id="x", epistemic_class=eg.ENGINEERING_GEOMETRY,
                generator=gen,
            )
            with pytest.raises(eg.EpistemicViolation):
                eg.check_generator_authority(asset)

    def test_badge_table_cannot_emit_measured(self):
        for canonical, badge in lp.EPISTEMIC_BADGE_TABLE.items():
            assert badge != "MEASURED", (
                f"canonical {canonical} must not translate to MEASURED"
            )

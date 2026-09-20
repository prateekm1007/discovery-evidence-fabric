"""R511 measurement-only attribution (NO semantic change).

Proves the post-rank runtime-attribution sidecar
(`POST_RANK_ATTRIBUTION.json`) is emitted by the real
`EngineRun._post_rank_pipeline` path with phase wall times,
pool counts, and per-candidate gauntlet rows — and that the
call-context phase labels resolve through the existing
R451-C1.3-3 provenance mechanism.

Nothing here changes discovery semantics: the sidecar is
additive, every persist is guarded (Art. IX), and the
POST_RANK_* ledger namespace never collides with STAGE_ORDER.
"""
import json
import tempfile
from pathlib import Path

from tests.test_f_series_integration import _survivor_env
from discovery_fabric.engine.run import EngineRun
from discovery_fabric.engine import call_context as cctx

OUTCOMES = {
    "RESUMED_KILL", "CHEAP_SCREEN_KILL", "PHYSICS_KILL",
    "ENGINEERING_ATTACK_KILL", "INDEPENDENT_ATTACK_KILL",
    "SURVIVED_GAUNTLET",
}


def _run_post_rank(domain="fluidics_hydraulic"):
    env = _survivor_env(domain)
    td = tempfile.mkdtemp()
    run = EngineRun(env.problem, td, run_id="testrun:r511-attrib",
                    package_number="99")
    run.env = env
    run.rehearsal = True
    run._post_rank_pipeline({"run_id": "testrun:r511-attrib"})
    return Path(td), run


def test_post_rank_attribution_sidecar_emitted():
    td, run = _run_post_rank()
    sidecar = td / "POST_RANK_ATTRIBUTION.json"
    assert sidecar.is_file(), \
        "the pipeline must emit the attribution sidecar"
    rec = json.loads(sidecar.read_text())
    assert rec["schema"] == "POST_RANK_ATTRIBUTION/1.0"
    assert rec["run_id"] == "testrun:r511-attrib"
    assert isinstance(rec["phases"], dict)
    assert isinstance(rec["pool"], dict)
    assert isinstance(rec["candidates"], list)
    assert isinstance(rec["mutations"], dict)
    # the gauntlet + selection phases ran on this path
    assert "GAUNTLET" in rec["phases"], \
        "gauntlet wall time must be recorded, got %s" % sorted(
            rec["phases"])
    assert "SELECTION" in rec["phases"]
    assert rec["pool"]["n_total"] >= 1
    assert sum(rec["pool"]["origins"].values()) == rec["pool"]["n_total"]
    for row in rec["candidates"]:
        assert row["key"]
        assert row["candidate_id"]
        assert row["outcome"] in OUTCOMES, row["outcome"]
        assert row["wall_s"] >= 0.0
        assert isinstance(row["phase_s"], dict)
    # semantics preserved: the pipeline still did its real work
    assert (td / "SURVIVOR_SELECTION.json").is_file()
    assert (td / "PACKAGE_DEFERRED.json").is_file()


def test_post_rank_phase_labels_resolve_via_call_context():
    tok = cctx.bind_run("testrun:r511-labels", session_id="ts_label")
    try:
        cctx.set_stage("POST_RANK_ENSEMBLE")
        prov = cctx.effective()
        assert prov["run_id"] == "testrun:r511-labels"
        assert prov["engine_stage"] == "POST_RANK_ENSEMBLE"
        assert prov["call_class"] == "RUN_OWNED"
        assert prov["engine_stage"] not in (
            "RETRIEVE", "FREEZE", "PREMISE_GATE", "SYNTHESIZE",
            "VERIFY", "MECHANISM_SPACE", "MULTI_SOURCE_DISCOVERY",
            "COLLISION", "PHYSICS", "ATTACK", "CONTRADICTION",
            "KILLER_EXPERIMENT", "IMPROVE", "ADJUDICATION",
            "CLASSIFY", "NEXT_BEST_ACTION", "RANK"), \
            "post-rank labels must never collide with STAGE_ORDER names"
    finally:
        cctx.unbind(tok)
    assert cctx.current() is None

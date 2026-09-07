"""R420 render-path autonomy tests — the operator directive's decisive
joins, proven adversarially (Art. XVI/XVII: code is a hypothesis about
enforcement; these tests are evidence).

Operator directive R420 (2026-09-08), sections 1-7:

  §1  AUTO-ENQUEUE: a typed in-worker render skip (e.g.
      RENDER_SKIPPED_LOW_MEMORY / RENDER_TIMEOUT) automatically hands
      off to the async artifact-render job from the production worker —
      no operator intervention, no copied JSON, no user-side
      regeneration.
  §2  EPISTEMIC BOUNDARY: render availability is never scientific
      maturity; a completed render changes no CIO maturity/class field;
      conceptual geometry is never promoted.
  §3  RESTART CONTRACT: a job left RUNNING across a container restart
      has a deterministic, OBSERVABLE recovery path (IMPLEMENTED, not
      documented — the pre-R420 docstring claimed recovery the runtime
      never performed; that claim is now code under test).
  §4  BLENDER PROVENANCE FAIL-CLOSED: only the pinned build (exact
      version string) may render; an arbitrary system blender or a
      version-mismatched binary is REFUSED with a typed skip and a
      recorded refusal trail. No silent shutil.which fallback.
  §5  THRESHOLD PROVENANCE: the 269 MB baseline and every operational
      threshold carry their Article XXVII record (environment, date,
      baseline, margin rationale, threshold, context, uncertainty).
  §6  DOCKERFILE HYGIENE: no external diagnostic callbacks in the
      production image.
  §7  STAGE JOINS: invention -> GLB -> render decision -> async job ->
      persisted render record -> CIO -> website surface -> package.

Hermetic tests run everywhere (Blender pinned to absent). The full-join
class runs the REAL pinned build when BLENDER_PATH is set — the same
discipline as tests/test_r419_render_pipeline.py.
"""

import inspect
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from discovery_fabric.engine.invention_bridge import render as render_mod  # noqa: E402
from toscanini import artifact_worker  # noqa: E402
from toscanini import cio as cio_mod  # noqa: E402
from toscanini import durable as durable_mod  # noqa: E402
from toscanini import server as srv  # noqa: E402
from toscanini import worker as worker_mod  # noqa: E402

BLENDER = os.environ.get("BLENDER_PATH", "")

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# helpers: patched store + a session fixture shaped like a real run dir
# ---------------------------------------------------------------------------

def _session_fixture(td: str, with_glb: bool = True,
                     bridge_render_status: str = "RENDER_TIMEOUT"):
    """A run dir + session dict shaped like a COMPLETED fresh run whose
    in-worker render ended with a typed skip (the observed production
    state of ts_c0f41af92195, R419f)."""
    run_dir = Path(td)
    model = run_dir / "MODEL"
    model.mkdir(parents=True, exist_ok=True)
    if with_glb:
        (model / "model-001.glb").write_bytes(b"glb-bytes-authoritative")
    (run_dir / "INVENTION_SPECIFICATION.json").write_text(json.dumps({
        "mechanism": {"value": "adaptive thermal regulation"},
    }))
    (run_dir / "BRIDGE_REPORT.json").write_text(json.dumps({
        "outcome": "COMPLETED",
        "case": "B",
        "visualizability_class": "SYSTEM_3D",
        "renders": {"stage": "RENDER", "status": bridge_render_status,
                    "note": "typed infrastructure outcome"},
    }))
    return {"session_id": "ts_r420", "run_dir": str(run_dir),
            "status": "COMPLETE",
            "final_status": "EVOLVED_INVENTION_CANDIDATE"}


class _PatchedStore:
    """Patch sessions.get_session/list_sessions for hermetic job tests
    (the artifact worker reads the store; the tests never touch the
    real session store)."""

    def __init__(self, sessions):
        from toscanini import sessions as store
        self.store = store
        self.sessions = {s["session_id"]: s for s in sessions}
        self._orig_get = store.get_session
        self._orig_list = store.list_sessions

    def __enter__(self):
        self.store.get_session = lambda sid: self.sessions.get(sid)
        self.store.list_sessions = lambda: list(self.sessions.values())
        return self

    def __exit__(self, *exc):
        self.store.get_session = self._orig_get
        self.store.list_sessions = self._orig_list


class _NoSpawn:
    """Patch artifact_worker._spawn_job: record the spawn, return a fake
    Popen (a pid that is verifiably dead — liveness resolves False, so
    later re-enqueue paths are exercised honestly)."""

    def __init__(self):
        self.spawned: list = []
        self._orig = artifact_worker._spawn_job

    def __enter__(self):
        artifact_worker._spawn_job = self._fake_spawn
        return self

    def _fake_spawn(self, session_id):
        self.spawned.append(session_id)
        return SimpleNamespace(pid=999999)  # verifiably dead pid

    def __exit__(self, *exc):
        artifact_worker._spawn_job = self._orig


# ---------------------------------------------------------------------------
# §6 Dockerfile hygiene
# ---------------------------------------------------------------------------

class TestDockerfileHygiene(unittest.TestCase):

    def test_no_external_diagnostic_callbacks(self):
        """R420 §6: the production Dockerfile carries no outbound
        webhook/diagnostic posts (the R419d sink was temporary; its
        purpose — locating the failing step — is documented in the
        comment chain and commit trail instead)."""
        src = (REPO_ROOT / "Dockerfile").read_text()
        self.assertNotIn("urlopen", src)
        self.assertNotIn("fetch(", src)
        # the diagnostic UUID must not appear in any build instruction
        for line in src.splitlines():
            if line.strip().startswith("#"):
                continue
            self.assertNotIn("webhook.site", line)


# ---------------------------------------------------------------------------
# §5 threshold provenance (Art. XXVII)
# ---------------------------------------------------------------------------

class TestThresholdProvenance(unittest.TestCase):

    RECORD = REPO_ROOT / "discovery_fabric" / "engine" / \
        "invention_bridge" / "render_threshold_provenance.json"

    def test_record_exists_and_is_complete(self):
        self.assertTrue(self.RECORD.is_file())
        d = json.loads(self.RECORD.read_text())
        # the 269 MB baseline measurement carries all seven required
        # provenance elements (operator §5)
        m = d["measurements"][0]
        self.assertEqual(m["observed_value"], "269 MB")
        self.assertTrue(m["measurement_date"])
        self.assertIn("measurement_environment", m)
        self.assertIn("Render", json.dumps(m["measurement_environment"]))
        self.assertIn("uncertainty", m)
        self.assertIn("269", json.dumps(m))
        # every threshold: class, value, context, margin rationale
        names = {t["name"] for t in d["thresholds"]}
        self.assertIn("in_worker memory guard", names)
        self.assertIn("async memory guard", names)
        for t in d["thresholds"]:
            self.assertEqual(t["class"], "ENGINEERING")
            self.assertTrue(t["safety_margin_rationale"])
            self.assertTrue(t["intended_execution_context"])
            self.assertTrue(t.get("justification_for_not_another_number")
                            or t.get("value"))
        self.assertIn("limitations", d["cross_cutting"])
        self.assertIn("intended_execution_contexts", d["cross_cutting"])

    def test_thresholds_match_the_code(self):
        """The record's thresholds are the ones the guard actually
        applies — provenance and implementation agree (no silent
        drift, Art. XXVII)."""
        d = json.loads(self.RECORD.read_text())
        vals = {t["name"]: t for t in d["thresholds"]}
        self.assertEqual(
            vals["in_worker memory guard"]["value_mb"], 650)
        self.assertEqual(vals["async memory guard"]["value_mb"], 400)
        self.assertEqual(
            vals["in_worker render budget"]["value_seconds"],
            render_mod._in_worker_budget_s())
        # the async ladder in the job matches the record
        record_ladder = vals["async quality ladder attempts 2-3"]
        self.assertIn("6 samples", record_ladder["value"])
        self.assertIn(
            (6, [768, 512], 240), artifact_worker.QUALITY_LADDER)
        self.assertIn(
            (48, [1152, 768], 900), artifact_worker.QUALITY_LADDER)

    def test_memory_guard_record_carries_provenance(self):
        """A typed low-memory skip points at the Article XXVII record
        (never an unexplained magic number)."""
        orig = render_mod._mem_available_mb
        render_mod._mem_available_mb = lambda: 120  # force the skip
        try:
            guard = render_mod._memory_guard("test", mode="in_worker")
        finally:
            render_mod._mem_available_mb = orig
        self.assertIsNotNone(guard)
        self.assertEqual(guard["status"], "RENDER_SKIPPED_LOW_MEMORY")
        self.assertEqual(guard["required_mb"], 650)
        self.assertEqual(guard["mem_available_mb"], 120)
        self.assertEqual(guard["threshold_class"], "ENGINEERING")
        self.assertIn("render_threshold_provenance.json",
                      guard["threshold_provenance"])
        self.assertTrue(Path(guard["threshold_provenance"]).exists()
                        or (REPO_ROOT / "discovery_fabric" / "engine" /
                            "invention_bridge" /
                            "render_threshold_provenance.json").exists())


# ---------------------------------------------------------------------------
# §4 Blender provenance fail-closed
# ---------------------------------------------------------------------------

class TestBlenderFailClosed(unittest.TestCase):
    """Adversarial (Art. XVII): how would an adversary sneak an
    arbitrary binary into the render path? A system blender on PATH, a
    version-mismatched BLENDER_PATH, a binary that cannot answer — each
    must be REFUSED with a typed skip and a recorded trail."""

    def _fake_blender(self, td: str, version_line: str) -> str:
        """An executable that answers `--version` with the given line."""
        path = Path(td) / f"blender_{abs(hash(version_line)) % 10000}"
        path.write_text("#!/bin/sh\n"
                        f"echo '{version_line}'\nexit 0\n")
        path.chmod(0o755)
        return str(path)

    def test_version_mismatch_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            fake = self._fake_blender(td, "Blender 4.1.1")
            env = {"BLENDER_PATH": fake}
            orig = os.environ.get("BLENDER_PATH")
            os.environ["BLENDER_PATH"] = fake
            try:
                found = render_mod.find_blender()
            finally:
                if orig is None:
                    os.environ.pop("BLENDER_PATH", None)
                else:
                    os.environ["BLENDER_PATH"] = orig
            self.assertIsNone(found)  # REFUSED
            trail = render_mod.last_blender_resolution()
            entry = trail["candidates"][0]
            self.assertEqual(entry["result"], "REFUSED_VERSION_MISMATCH")
            self.assertEqual(entry["version_reported"], "Blender 4.1.1")
            self.assertEqual(env and entry["path"], fake)

    def test_unresponsive_binary_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            # an executable that exists but cannot answer --version
            path = Path(td) / "blender_silent"
            path.write_text("#!/bin/sh\nexit 1\n")
            path.chmod(0o755)
            orig = os.environ.get("BLENDER_PATH")
            os.environ["BLENDER_PATH"] = str(path)
            try:
                found = render_mod.find_blender()
            finally:
                if orig is None:
                    os.environ.pop("BLENDER_PATH", None)
                else:
                    os.environ["BLENDER_PATH"] = orig
            self.assertIsNone(found)
            trail = render_mod.last_blender_resolution()
            self.assertEqual(trail["candidates"][0]["result"],
                             "REFUSED_BINARY_UNRESPONSIVE")

    def test_no_path_fallback(self):
        """The removed shutil.which fallback: a blender on PATH is never
        silently used (operator §4). Skipped on machines where the
        Docker install exists (the deployed image IS the authority)."""
        if Path("/opt/blender/blender").exists():
            self.skipTest("/opt/blender present (Docker image context)")
        with tempfile.TemporaryDirectory() as td:
            fake = self._fake_blender(td, "Blender 5.2.1 LTS")
            # poison PATH with a binary that would be ACCEPTED if the
            # fallback existed — it must not even be consulted
            os.environ["PATH"] = f"{os.path.dirname(fake)}:" \
                                 f"{os.environ.get('PATH', '')}"
            orig = os.environ.pop("BLENDER_PATH", None)
            try:
                found = render_mod.find_blender()
            finally:
                if orig is not None:
                    os.environ["BLENDER_PATH"] = orig
            self.assertIsNone(found)
            # the trail shows only the two sanctioned candidate sources
            sources = [c["source"]
                       for c in render_mod.last_blender_resolution()
                       ["candidates"]]
            self.assertNotIn("PATH", sources)

    def test_skip_record_carries_resolution_trail(self):
        """The typed no-blender skip EVIDENCES its resolution trail
        (which candidates, why refused — never a bare 'not found')."""
        with tempfile.TemporaryDirectory() as td:
            orig = os.environ.pop("BLENDER_PATH", None)
            try:
                rec = render_mod.render_invention(td, {},
                                                  is_conceptual=True)
            finally:
                if orig is not None:
                    os.environ["BLENDER_PATH"] = orig
            self.assertEqual(rec["status"], "RENDER_SKIPPED_NO_BLENDER")
            self.assertIn("blender_resolution", rec)
            self.assertIn("pinned_tarball_sha256",
                          rec["blender_resolution"])

    def test_pinned_local_build_is_accepted_and_recorded(self):
        if not (BLENDER and Path(BLENDER).is_file()):
            self.skipTest("pinned local build not available (BLENDER_PATH)")
        found = render_mod.find_blender()
        self.assertEqual(found, BLENDER)
        trail = render_mod.last_blender_resolution()
        self.assertEqual(trail["accepted"], BLENDER)
        self.assertEqual(trail["verified_version"],
                         f"Blender {render_mod.PINNED_BLENDER_VERSION}")

    def test_render_record_carries_verified_binary_identity(self):
        if not (BLENDER and Path(BLENDER).is_file()):
            self.skipTest("pinned local build not available (BLENDER_PATH)")
        with tempfile.TemporaryDirectory() as td:
            # a source GLB so the record reaches the identity fields
            model = Path(td) / "MODEL"
            model.mkdir()
            (model / "model-001.glb").write_bytes(b"glb")
            rec = render_mod.render_invention(
                td, {}, is_conceptual=True, timeout_s=60)
            # even if the render itself fails/times out, the record has
            # the verified binary provenance (it ran under the pinned
            # build — that fact is independent of render success)
            if rec.get("status") != "RENDER_SKIPPED_NO_SOURCE_GLB":
                self.assertEqual(rec.get("blender_path"), BLENDER)
                self.assertEqual(
                    rec.get("blender_version_verified"),
                    f"Blender {render_mod.PINNED_BLENDER_VERSION}")

    def test_in_worker_budget_is_short_and_recorded(self):
        """The in-worker render hands off quickly (observed defect:
        ts_c0f41af92195 held the run 900 s in a doomed render). The
        budget is recorded in the typed record."""
        with tempfile.TemporaryDirectory() as td:
            orig = os.environ.pop("BLENDER_PATH", None)
            try:
                rec = render_mod.render_invention(td, {},
                                                  is_conceptual=True)
            finally:
                if orig is not None:
                    os.environ["BLENDER_PATH"] = orig
            self.assertEqual(rec["memory_mode"], "in_worker")
            self.assertEqual(rec["budget_seconds"], 300)
            self.assertEqual(render_mod._in_worker_budget_s(), 300)
        # env override is honored (verification runs)
        os.environ["ENGINE_RENDER_INWORKER_TIMEOUT_S"] = "600"
        try:
            self.assertEqual(render_mod._in_worker_budget_s(), 600)
        finally:
            os.environ.pop("ENGINE_RENDER_INWORKER_TIMEOUT_S", None)


# ---------------------------------------------------------------------------
# §1 auto-enqueue + §3 restart contract (the job lifecycle)
# ---------------------------------------------------------------------------

class TestAutoEnqueue(unittest.TestCase):

    def test_typed_skip_needs_followup(self):
        with tempfile.TemporaryDirectory() as td:
            s = _session_fixture(td, bridge_render_status="RENDER_TIMEOUT")
            why = artifact_worker.needs_render_followup(s)
            self.assertIsNotNone(why)
            self.assertIn("RENDER_TIMEOUT", why)

    def test_low_memory_skip_needs_followup(self):
        with tempfile.TemporaryDirectory() as td:
            s = _session_fixture(
                td, bridge_render_status="RENDER_SKIPPED_LOW_MEMORY")
            self.assertIsNotNone(artifact_worker.needs_render_followup(s))

    def test_no_glb_no_followup(self):
        with tempfile.TemporaryDirectory() as td:
            s = _session_fixture(td, with_glb=False)
            self.assertIsNone(artifact_worker.needs_render_followup(s))

    def test_complete_renders_no_followup(self):
        with tempfile.TemporaryDirectory() as td:
            s = _session_fixture(td)
            d3 = Path(td) / "MODEL" / "3D"
            d3.mkdir(parents=True)
            for n in ("hero.png", "section.png", "exploded.png"):
                # intact PNGs: magic + IEND trailer
                body = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
                        + b"\x00\x00\x00\x00IEND\xaeB`\x82")
                (d3 / n).write_bytes(body)
            self.assertIsNone(artifact_worker.needs_render_followup(s))

    def test_terminal_job_verdict_stands(self):
        """A terminal job record ends the automatic followup — no retry
        loop (re-attempting is explicit, never automatic)."""
        with tempfile.TemporaryDirectory() as td:
            s = _session_fixture(td)
            d3 = Path(td) / "MODEL" / "3D"
            d3.mkdir(parents=True)
            (d3 / "RENDER_JOB.json").write_text(json.dumps({
                "artifact": "RENDER_JOB", "session_id": "ts_r420",
                "status": "RENDER_SKIPPED_LOW_MEMORY", "at": "now",
            }))
            with _PatchedStore([s]):
                self.assertIsNone(
                    artifact_worker.needs_render_followup(s))

    def test_auto_enqueue_creates_job_record(self):
        """The production handoff: typed skip -> job record with
        identity (pid/starttime), enqueued_by=production_worker."""
        with tempfile.TemporaryDirectory() as td:
            s = _session_fixture(td)
            with _PatchedStore([s]), _NoSpawn() as spawn:
                record = artifact_worker.auto_enqueue(
                    "ts_r420", enqueued_by="production_worker")
                self.assertEqual(spawned_count(spawn), 1)
            self.assertIsNotNone(record)
            self.assertEqual(record["status"], "RUNNING")
            self.assertEqual(record["enqueued_by"], "production_worker")
            self.assertIn("worker_pid", record)
            self.assertIn("RENDER_TIMEOUT", record["followup_reason"])
            # the record is PERSISTED (the file is the authority, Art. X)
            on_disk = json.loads(
                (Path(td) / "MODEL" / "3D" / "RENDER_JOB.json").read_text())
            self.assertEqual(on_disk["status"], "RUNNING")
            self.assertEqual(on_disk["enqueued_by"], "production_worker")

    def test_auto_enqueue_is_a_noop_when_satisfied(self):
        with tempfile.TemporaryDirectory() as td:
            s = _session_fixture(td, with_glb=False)
            with _PatchedStore([s]), _NoSpawn() as spawn:
                record = artifact_worker.auto_enqueue("ts_r420")
            self.assertIsNone(record)
            self.assertEqual(spawned_count(spawn), 0)

    def test_worker_wires_the_handoff(self):
        """The production path actually calls it: worker.run contains
        the auto-enqueue phase (source-inspection precedent — the
        wiring is the contract under test)."""
        src = inspect.getsource(worker_mod.run)
        self.assertIn("artifact_worker.auto_enqueue", src)
        self.assertIn("render_followup", src)


def spawned_count(spawn) -> int:
    return len(spawn.spawned)


class TestRestartContract(unittest.TestCase):

    def test_dead_running_job_is_interrupted_and_re_enqueued(self):
        """§3: a job left RUNNING across a restart (dead pid) gets the
        deterministic recovery: INTERRUPTED trail + re-enqueue."""
        with tempfile.TemporaryDirectory() as td:
            s = _session_fixture(td)
            d3 = Path(td) / "MODEL" / "3D"
            d3.mkdir(parents=True)
            (d3 / "RENDER_JOB.json").write_text(json.dumps({
                "artifact": "RENDER_JOB", "session_id": "ts_r420",
                "status": "RUNNING", "enqueued_at": "before-restart",
                "worker_pid": 999999,  # dead
                "worker_starttime": "12",
            }))
            with _PatchedStore([s]), _NoSpawn() as spawn:
                record = artifact_worker.enqueue(
                    "ts_r420", enqueued_by="test")
                self.assertEqual(spawned_count(spawn), 1)
            self.assertEqual(record["status"], "RUNNING")
            self.assertIn("interruption_reason", record)
            self.assertIn("999999", record["interruption_reason"])
            self.assertIn("restart", record["interruption_reason"])
            # the observable trail: enqueued_by lineage + interruption
            self.assertEqual(record["enqueued_by"], "test")
            self.assertTrue(record.get("interrupted_at"))

    def test_live_running_job_is_returned_as_is(self):
        with tempfile.TemporaryDirectory() as td:
            s = _session_fixture(td)
            d3 = Path(td) / "MODEL" / "3D"
            d3.mkdir(parents=True)
            from toscanini import sessions as store
            starttime = store._proc_stat_starttime(os.getpid())
            live = {
                "artifact": "RENDER_JOB", "session_id": "ts_r420",
                "status": "RUNNING",
                "worker_pid": os.getpid(),
                "worker_starttime": starttime,
            }
            (d3 / "RENDER_JOB.json").write_text(json.dumps(live))
            with _PatchedStore([s]), _NoSpawn() as spawn:
                record = artifact_worker.enqueue("ts_r420")
                self.assertEqual(spawned_count(spawn), 0)  # no second job
            self.assertEqual(record["worker_pid"], os.getpid())
            self.assertEqual(record["status"], "RUNNING")

    def test_boot_recovery_sweep(self):
        """recover_interrupted_jobs(): dead-RUNNING -> INTERRUPTED +
        re-enqueue; terminal -> untouched."""
        with tempfile.TemporaryDirectory() as td_a:
            with tempfile.TemporaryDirectory() as td_b:
                dead = _session_fixture(td_a)
                (Path(td_a) / "MODEL" / "3D").mkdir(parents=True)
                (Path(td_a) / "MODEL" / "3D" / "RENDER_JOB.json") \
                    .write_text(json.dumps({
                        "artifact": "RENDER_JOB",
                        "session_id": dead["session_id"],
                        "status": "RUNNING",
                        "worker_pid": 999999,
                        "worker_starttime": "5"}))
                terminal = _session_fixture(td_b)
                terminal["session_id"] = "ts_terminal"
                (Path(td_b) / "MODEL" / "3D").mkdir(parents=True)
                (Path(td_b) / "MODEL" / "3D" / "RENDER_JOB.json") \
                    .write_text(json.dumps({
                        "artifact": "RENDER_JOB",
                        "session_id": "ts_terminal",
                        "status": "RENDER_SKIPPED_LOW_MEMORY",
                        "at": "t"}))
                with _PatchedStore([dead, terminal]) as patched, \
                        _NoSpawn() as spawn:
                    # give the terminal fixture a dead pid too — its
                    # TERMINAL status must still protect it
                    recovered = artifact_worker \
                        .recover_interrupted_jobs()
                    self.assertEqual(spawned_count(spawn), 1)
                self.assertEqual(len(recovered), 1)
                self.assertEqual(recovered[0]["session_id"],
                                 dead["session_id"])
                self.assertTrue(recovered[0]["re_enqueued"])
                job = json.loads(
                    (Path(td_a) / "MODEL" / "3D" / "RENDER_JOB.json")
                    .read_text())
                self.assertEqual(job["status"], "RUNNING")
                self.assertEqual(job["enqueued_by"],
                                 "boot_restart_recovery")

    def test_boot_render_recovery_is_one_shot(self):
        """§1/§7: completed runs with missing renders get their job at
        boot — ONCE (the record stops the next sweep: bounded, no
        storm). This is the sweep that healed pre-R420 runs."""
        with tempfile.TemporaryDirectory() as td:
            s = _session_fixture(td)
            with _PatchedStore([s]) as patched, _NoSpawn() as spawn:
                first = artifact_worker.boot_render_recovery()
                self.assertEqual(len(first), 1)
                self.assertEqual(spawned_count(spawn), 1)
                # the job wrote its record (the no-spawn fake still
                # wrote it via enqueue) — second sweep: nothing
                patched.store.get_session = lambda sid: s
                second = artifact_worker.boot_render_recovery()
                self.assertEqual(len(second), 0)
                self.assertEqual(spawned_count(spawn), 1)

    def test_server_boot_performs_the_contract(self):
        src = inspect.getsource(srv.main)
        self.assertIn("recover_interrupted_jobs", src)
        self.assertIn("boot_render_recovery", src)

    def test_artifact_log_route_wired(self):
        """The recovery path is OBSERVABLE: the async job's own log is
        operator-served (enumeration-safe, key-scoped)."""
        src = inspect.getsource(srv.Handler.do_GET)
        self.assertIn("/api/ops/artifact-log", src)

    def test_job_docstring_states_implemented_contract(self):
        """§3 (the documentation-correction clause): the module claims
        ONLY what the runtime performs. The claim 'a restart finds it'
        must be backed by the code that does it."""
        src = inspect.getsource(artifact_worker)
        self.assertIn("def recover_interrupted_jobs", src)
        doc = artifact_worker.__doc__ or ""
        self.assertIn("RESTART CONTRACT", doc)
        self.assertIn("recover_interrupted_jobs()", doc)


class TestIdempotentIntegrity(unittest.TestCase):
    """Adversarial (Art. XVII): a killed Blender leaves truncated PNGs —
    size>0 must not count as complete (the corpse-render attack)."""

    @staticmethod
    def _intact_png() -> bytes:
        return (b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
                + b"\x00\x00\x00\x00IEND\xaeB`\x82")

    def test_truncated_png_is_not_complete(self):
        with tempfile.TemporaryDirectory() as td:
            s = _session_fixture(td)
            d3 = Path(td) / "MODEL" / "3D"
            d3.mkdir(parents=True)
            (d3 / "hero.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 512)
            (d3 / "section.png").write_bytes(self._intact_png())
            (d3 / "exploded.png").write_bytes(self._intact_png())
            self.assertFalse(artifact_worker.render_artifacts_complete(s))

    def test_intact_pngs_are_complete(self):
        with tempfile.TemporaryDirectory() as td:
            s = _session_fixture(td)
            d3 = Path(td) / "MODEL" / "3D"
            d3.mkdir(parents=True)
            for n in ("hero.png", "section.png", "exploded.png"):
                (d3 / n).write_bytes(self._intact_png())
            self.assertTrue(artifact_worker.render_artifacts_complete(s))

    def test_record_sha_verification(self):
        with tempfile.TemporaryDirectory() as td:
            s = _session_fixture(td)
            d3 = Path(td) / "MODEL" / "3D"
            d3.mkdir(parents=True)
            import hashlib
            png = self._intact_png()
            for n in ("hero.png", "section.png", "exploded.png"):
                (d3 / n).write_bytes(png)
            (d3 / "render_record.json").write_text(json.dumps({
                "renders": {n: {"sha256": hashlib.sha256(png).hexdigest()}
                            for n in ("hero.png", "section.png",
                                      "exploded.png")}}))
            self.assertTrue(artifact_worker.render_artifacts_complete(s))
            # corrupt one byte — sha mismatch -> NOT complete
            data = bytearray((d3 / "hero.png").read_bytes())
            data[20] ^= 0xFF
            (d3 / "hero.png").write_bytes(bytes(data))
            self.assertFalse(artifact_worker.render_artifacts_complete(s))


class TestLadderAndTypedTerminal(unittest.TestCase):

    def test_run_ladder_records_attempts_and_stops_at_no_blender(self):
        """The bounded ladder: with no pinned build the first attempt
        records the typed skip and the ladder STOPS (the same
        environment would repeat it — honest terminal, no wasted
        rungs)."""
        with tempfile.TemporaryDirectory() as td:
            s = _session_fixture(td)
            orig_find = render_mod.find_blender
            render_mod.find_blender = lambda: None
            try:
                with _PatchedStore([s]):
                    out = artifact_worker.run("ts_r420")
            finally:
                render_mod.find_blender = orig_find
            self.assertEqual(out["status"], "RENDER_SKIPPED_NO_BLENDER")
            self.assertEqual(len(out["attempts"]), 1)
            self.assertEqual(out["attempts"][0]["samples"], 48)
            self.assertTrue(out["quality_ladder"])
            job = json.loads(
                (Path(td) / "MODEL" / "3D" / "RENDER_JOB.json").read_text())
            self.assertEqual(job["status"], "RENDER_SKIPPED_NO_BLENDER")
            self.assertIn("RENDER_SKIPPED_NO_BLENDER",
                          job["render_record"]["status"])

    def test_ladder_is_bounded(self):
        """Three rungs, descending quality, bounded budgets (provenance:
        render_threshold_provenance.json)."""
        ladder = artifact_worker.QUALITY_LADDER
        self.assertEqual(len(ladder), 3)
        samples = [r[0] for r in ladder]
        self.assertEqual(samples, sorted(samples, reverse=True))
        for _, _, budget in ladder:
            self.assertLessEqual(budget, 900)
            self.assertGreaterEqual(budget, 60)


# ---------------------------------------------------------------------------
# §2 epistemic boundary + CIO projection
# ---------------------------------------------------------------------------

class TestCioRenderStateProjection(unittest.TestCase):

    @staticmethod
    def _cio_for(td: str) -> dict:
        s = _session_fixture(td)
        return cio_mod.build_cio(s) or {}

    def test_inflight_job_surfaces_as_rendering(self):
        with tempfile.TemporaryDirectory() as td:
            d3 = Path(td) / "MODEL" / "3D"
            d3.mkdir(parents=True)
            (d3 / "RENDER_JOB.json").write_text(json.dumps({
                "artifact": "RENDER_JOB", "status": "RUNNING",
                "pipeline": "BLENDER_HEADLESS",
                "enqueued_by": "production_worker"}))
            cio = self._cio_for(td)
            renders = (cio.get("visualization") or {}).get("renders") or {}
            self.assertEqual(renders.get("status"), "RENDERING")
            self.assertIn("prepared", renders.get("note", ""))
            self.assertEqual(renders.get("enqueued_by"),
                             "production_worker")
            # never a fabricated URL while pending
            self.assertFalse(renders.get("hero_png"))

    def test_terminal_skip_status_surfaced(self):
        with tempfile.TemporaryDirectory() as td:
            d3 = Path(td) / "MODEL" / "3D"
            d3.mkdir(parents=True)
            (d3 / "RENDER_JOB.json").write_text(json.dumps({
                "artifact": "RENDER_JOB",
                "status": "RENDER_SKIPPED_LOW_MEMORY"}))
            cio = self._cio_for(td)
            renders = (cio.get("visualization") or {}).get("renders") or {}
            self.assertEqual(renders.get("status"),
                             "RENDER_SKIPPED_LOW_MEMORY")
            self.assertFalse(renders.get("hero_png"))

    def test_epistemic_boundary_render_changes_no_maturity(self):
        """§2 — THE boundary test: renders present vs absent vs
        RENDERING — the CIO's epistemic fields are IDENTICAL (maturity,
        geometry class, reality loop, ladder). A render is presentation
        only; it can never promote conceptual geometry."""
        with tempfile.TemporaryDirectory() as td_a:
            with tempfile.TemporaryDirectory() as td_b:
                with tempfile.TemporaryDirectory() as td_c:
                    # A: no renders at all
                    cio_a = self._cio_for(td_a)
                    # B: renders on disk
                    d3 = Path(td_b) / "MODEL" / "3D"
                    d3.mkdir(parents=True)
                    for n in ("hero.png", "hero.glb", "section.png",
                              "section.glb", "exploded.png",
                              "exploded.glb"):
                        (d3 / n).write_bytes(b"x" * 2048)
                    (d3 / "render_record.json").write_text(json.dumps({
                        "render_pipeline": "BLENDER_HEADLESS",
                        "blender_version": "5.2.1 LTS",
                        "status": "OK", "samples": 16,
                        "resolution": [960, 640]}))
                    cio_b = self._cio_for(td_b)
                    # C: render job in flight
                    d3c = Path(td_c) / "MODEL" / "3D"
                    d3c.mkdir(parents=True)
                    (d3c / "RENDER_JOB.json").write_text(json.dumps({
                        "artifact": "RENDER_JOB", "status": "RUNNING"}))
                    cio_c = self._cio_for(td_c)

                    for cio in (cio_a, cio_b, cio_c):
                        self.assertEqual(
                            (cio.get("geometry") or {}).get("class"),
                            "SYSTEM_3D")
                        self.assertTrue(
                            (cio.get("geometry") or {}).get("conceptual"))
                    mat_a = cio_a.get("maturity")
                    mat_b = cio_b.get("maturity")
                    mat_c = cio_c.get("maturity")
                    self.assertEqual(mat_a, mat_b)
                    self.assertEqual(mat_a, mat_c)
                    # the conceptual disclaimer survives renders: the
                    # engine-side CIO carries it as geometry.authority
                    # ("NOT engineering geometry" — Art. XXVIII: a
                    # render never promotes conceptual geometry)
                    authority_b = (cio_b.get("geometry") or {}).get(
                        "authority") or ""
                    self.assertIn("NOT engineering geometry", authority_b)
                    self.assertEqual(
                        (cio_b.get("geometry") or {}).get("authority"),
                        (cio_a.get("geometry") or {}).get("authority"))
                    # quality disclosure from the ladder attempt
                    renders_b = (cio_b.get("visualization") or {}).get(
                        "renders") or {}
                    self.assertEqual(renders_b.get("samples"), 16)
                    self.assertEqual(renders_b.get("resolution"),
                                     [960, 640])


# ---------------------------------------------------------------------------
# durable persistence (renders + package survive restarts)
# ---------------------------------------------------------------------------

class TestDurableRenderPersistence(unittest.TestCase):

    def test_run_dir_files_collect_renders_and_package_zip(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            model = run_dir / "MODEL"
            d3 = model / "3D"
            d3.mkdir(parents=True)
            (model / "model-001.glb").write_bytes(b"glb")
            for n in ("hero.png", "hero.glb", "section.png",
                      "render_record.json", "RENDER_JOB.json",
                      "render_spec.json"):
                (d3 / n).write_bytes(b"x" * 128)
            (run_dir / "BRIDGE_REPORT.json").write_text("{}")
            (run_dir / "TECHNOLOGY_PACKAGE_solar.zip").write_bytes(
                b"z" * 256)
            files = durable_mod._run_dir_files(run_dir)
            names = {f.name for f in files}
            for n in ("hero.png", "hero.glb", "section.png",
                      "render_record.json", "RENDER_JOB.json"):
                self.assertIn(n, names)
            self.assertIn("TECHNOLOGY_PACKAGE_solar.zip", names)
            self.assertIn("model-001.glb", names)
            self.assertIn("BRIDGE_REPORT.json", names)

    def test_worker_module_wires_durable_snapshot_on_completion(self):
        src = inspect.getsource(artifact_worker.run)
        self.assertIn("render_complete", src)


# ---------------------------------------------------------------------------
# §7 the hermetic stage-join chain (the decisive test, minus Blender)
# ---------------------------------------------------------------------------

class TestStageJoinHermetic(unittest.TestCase):
    """invention(GLB on disk) -> render decision (typed skip recorded
    in BRIDGE_REPORT) -> AUTO enqueue -> job record persisted -> typed
    terminal state surfaced in the CIO. Every join is proven with the
    real modules; only the Blender binary is absent (the full-join
    class below covers it when the pinned build exists)."""

    def test_the_chain(self):
        with tempfile.TemporaryDirectory() as td:
            s = _session_fixture(
                td, bridge_render_status="RENDER_SKIPPED_LOW_MEMORY")
            # 1. the render decision: typed skip, evidence recorded
            self.assertIsNotNone(
                artifact_worker.needs_render_followup(s))
            # 2. the automatic handoff (production worker's own call)
            with _PatchedStore([s]), _NoSpawn() as spawn:
                record = artifact_worker.auto_enqueue(
                    "ts_r420", enqueued_by="production_worker")
                self.assertEqual(spawned_count(spawn), 1)
            self.assertEqual(record["status"], "RUNNING")
            # 3. the job record persisted (RENDER_JOB.json authority)
            job_path = Path(td) / "MODEL" / "3D" / "RENDER_JOB.json"
            self.assertTrue(job_path.is_file())
            # 4. the CIO surfaces the in-flight state (calm, honest)
            cio = cio_mod.build_cio(s) or {}
            renders = (cio.get("visualization") or {}).get("renders") or {}
            self.assertEqual(renders.get("status"), "RENDERING")
            # 5. simulate the job's typed terminal outcome (this host
            #    has no pinned build in this hermetic context)
            job = json.loads(job_path.read_text())
            job["status"] = "RENDER_SKIPPED_NO_BLENDER"
            job_path.write_text(json.dumps(job))
            # 6. the CIO surfaces the typed terminal state — never a
            #    fabricated render, never a changed maturity
            cio2 = cio_mod.build_cio(s) or {}
            renders2 = (cio2.get("visualization") or {}).get("renders") or {}
            self.assertEqual(renders2.get("status"),
                             "RENDER_SKIPPED_NO_BLENDER")
            self.assertEqual(cio2.get("maturity"), cio.get("maturity"))
            # 7. the terminal verdict stands: no further auto enqueue
            s2 = dict(s)
            with _PatchedStore([s2]):
                self.assertIsNone(
                    artifact_worker.needs_render_followup(s2))


# ---------------------------------------------------------------------------
# §7 the full join with the REAL pinned build (BLENDER_PATH)
# ---------------------------------------------------------------------------

@unittest.skipUnless(
    BLENDER and Path(BLENDER).is_file(),
    "the pinned Blender build is not available (set BLENDER_PATH)")
class TestFullJoinWithPinnedBuild(unittest.TestCase):
    """The decisive stage-join WITH rendering: GLB -> async job ->
    pinned Blender -> six artifacts -> terminal job record -> CIO
    gallery pointers -> epistemic fields untouched. Same discipline as
    tests/test_r419_render_pipeline.py (the full battery also runs the
    bridge render there)."""

    @classmethod
    def setUpClass(cls):
        from discovery_fabric.engine.invention_bridge import \
            conceptual_geometry
        cls.td = tempfile.mkdtemp(prefix="r420_join_")
        cls.s = _session_fixture(cls.td)
        built = conceptual_geometry.build_system_architecture(
            ["sensing layer", "compute core", "power substrate",
             "interface boundary"], "thermal regulation canopy")
        (Path(cls.td) / "MODEL" / "model-001.glb").write_bytes(
            built["glb_bytes"])
        with _PatchedStore([cls.s]):
            cls.out = artifact_worker.run("ts_r420")

    def test_job_completed_with_artifacts(self):
        self.assertIn(self.out.get("status"), ("OK", "PARTIAL"))
        d3 = Path(self.td) / "MODEL" / "3D"
        for n in ("hero.png", "section.png", "exploded.png"):
            p = d3 / n
            self.assertTrue(p.is_file() and p.stat().st_size > 100,
                            f"missing {n}")
        self.assertTrue(artifact_worker.render_artifacts_complete(self.s))

    def test_job_record_carries_identity_and_ladder(self):
        job = json.loads(
            (Path(self.td) / "MODEL" / "3D" / "RENDER_JOB.json").read_text())
        self.assertIn(job["status"], ("OK", "PARTIAL"))
        self.assertTrue(job["attempts"])
        self.assertTrue(job["attempts"][0].get("budget_seconds"))
        self.assertIn("quality_ladder", job)

    def test_cio_shows_the_renders(self):
        cio = cio_mod.build_cio(self.s) or {}
        renders = (cio.get("visualization") or {}).get("renders") or {}
        self.assertEqual(renders.get("status"), "OK")
        self.assertTrue((renders.get("hero_png") or "").endswith("hero.png"))
        self.assertTrue((renders.get("exploded_png") or "")
                        .endswith("exploded.png"))
        self.assertIn("samples", renders)  # quality disclosed

    def test_render_route_serves_the_artifact(self):
        """The website surface: the render route resolves the file the
        job produced (route logic exercised through the handler's own
        resolution contract)."""
        # the handler serves run_dir/MODEL/3D/<name> for whitelisted
        # names — the job wrote exactly those files
        d3 = Path(self.s["run_dir"]) / "MODEL" / "3D"
        src = inspect.getsource(srv.Handler.do_GET)
        self.assertIn('"hero.png", "hero.glb", "section.png", '
                      '"section.glb",', src)
        self.assertTrue((d3 / "hero.png").is_file())

    def test_epistemic_boundary_on_the_real_render(self):
        """§2 on the REAL rendered run: a completed render never
        promotes the conceptual class or changes maturity — compare
        against the same fixture WITHOUT renders."""
        with tempfile.TemporaryDirectory() as td_bare:
            bare = _session_fixture(td_bare)
            (Path(td_bare) / "MODEL" / "model-001.glb").write_bytes(
                (Path(self.td) / "MODEL" / "model-001.glb").read_bytes())
            cio_bare = cio_mod.build_cio(bare) or {}
            cio_rendered = cio_mod.build_cio(self.s) or {}
            self.assertEqual(
                (cio_rendered.get("geometry") or {}).get("class"),
                (cio_bare.get("geometry") or {}).get("class"))
            self.assertEqual(cio_rendered.get("maturity"),
                             cio_bare.get("maturity"))
            self.assertEqual(
                cio_rendered.get("reality_loop"),
                cio_bare.get("reality_loop"))
            # and the conceptual disclaimer survives a real render
            # (engine-side field: geometry.authority)
            self.assertIn(
                "NOT engineering geometry",
                (cio_rendered.get("geometry") or {}).get("authority")
                or "")


if __name__ == "__main__":
    unittest.main()

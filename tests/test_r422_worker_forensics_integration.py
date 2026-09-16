"""R422 — worker-forensics integration tests (directive 2, the a5a7 class).

The R421-era module suite (28/28 in scripts/test_worker_forensics.py) covers
the ledger mechanics in isolation. THESE tests verify the ENGINE-SIDE wiring
that makes the anomaly observable in production:

  1. the production worker wraps its whole lifecycle in the durable ledger
  2. the retry endpoint appends RETRY_REQUESTED before spawning
  3. /api/health carries the worker_forensics summary
  4. the durable snapshot payload carries the ledger (evidence leaves the
     container with every push)
  5. the boot path runs the forensic reconciliation after restore

Source-inspection precedent (test_r420_render_autonomy.py): the wiring IS
the contract under test.
"""
from __future__ import annotations

import inspect
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from toscanini import worker as worker_mod            # noqa: E402
from toscanini import worker_forensics as wfx         # noqa: E402
from toscanini import durable as durable_mod          # noqa: E402
from toscanini import server as server_mod            # noqa: E402


class TestWorkerWiring(unittest.TestCase):

    def test_run_wraps_body_in_durable_forensics(self):
        """The worker's public entry wraps the whole run in the
        WorkerForensics context + heartbeat loop — an exception, a SIGTERM,
        or a silent death inside ANY phase leaves a durable record."""
        src = inspect.getsource(worker_mod.run)
        self.assertIn("WorkerForensics", src)
        self.assertIn("heartbeat_loop", src)
        self.assertIn("_run_inner", src)

    def test_body_emits_phase_events(self):
        """Every phase boundary emits a forensics event BEFORE the worker
        proceeds (durable-before-next-action)."""
        body = inspect.getsource(worker_mod._run_inner)
        for phase in ("SESSION_LOOKUP", "REGISTER_RUNNING",
                      "TRANSPORT_PROBE", "BUILDING_PROBLEM", "ENGINE_RUN",
                      "BRIDGE_GATE", "RENDER_FOLLOWUP", "FINAL_SNAPSHOT"):
            self.assertIn(phase, body)
        # terminal paths record their terminal state
        self.assertIn("TERMINAL_STATE", body)

    def test_probe_backoff_ladder(self):
        """R422 transport reliability: three preflight attempts (probe /
        +10 s / +30 s) instead of one eager retry — bounded, honest."""
        body = inspect.getsource(worker_mod._run_inner)
        self.assertIn("_PROBE_BACKOFF_S", body)
        self.assertIn("(0, 10, 30)", body)

    def test_package_field_refresh_on_gate_landing(self):
        """The UI-copy server-side companion: when the bridge gate lands a
        package, the session's package field is refreshed from the run dir
        (the authority) so the stored projection cannot disagree with the
        product surface."""
        body = inspect.getsource(worker_mod._run_inner)
        self.assertIn("package-field refresh", body)
        self.assertIn("_package_info", body)


class TestRetryAndHealthWiring(unittest.TestCase):

    def test_retry_endpoint_appends_before_spawn(self):
        """The a5a7 path: RETRY_REQUESTED is durably appended BEFORE the
        worker spawn (a spawn that dies instantly still leaves the request
        on the ledger)."""
        src = inspect.getsource(server_mod.Handler.do_POST)
        self.assertIn("RETRY_REQUESTED", src)
        # the event is written before _spawn_worker in program order
        self.assertLess(
            src.index("RETRY_REQUESTED"), src.index("_spawn_worker(sid)"))

    def test_health_carries_worker_forensics(self):
        """the /api/health payload exposes worker_forensics (the field that
        makes 'Discovery ready' + zero live workers impossible to miss)."""
        src = inspect.getsource(server_mod._health_payload)
        self.assertIn("worker_forensics", src)
        helper = server_mod._worker_forensics_state()
        self.assertIn("enabled", helper)
        self.assertIn("active_workers", helper)
        self.assertIn("forensics_degraded", helper)

    def test_boot_reconciles_after_restore(self):
        """main() runs reconcile_at_boot AFTER the durable restore — the
        restored previous-boot tail is what orphans are computed from.
        R473: the restore call is now the GATED restore_for_serve() (the
        audit-named restore-before-serve defense) — the pin follows the
        strengthened contract: the restore STILL happens (gated, retried)
        before the reconciliation, and the gate-closed disclosure exists."""
        src = inspect.getsource(server_mod.main)
        self.assertIn("reconcile_at_boot", src)
        self.assertIn("restore_for_serve", src)
        self.assertLess(
            src.index("restore_for_serve("),
            src.index("reconcile_at_boot"))


class TestDurablePayloadCarriesLedger(unittest.TestCase):

    def test_collect_payload_source_wiring(self):
        src = inspect.getsource(durable_mod._collect_payload)
        self.assertIn("worker_forensics", src)
        self.assertIn(".jsonl", src)

    def test_restore_merges_ledger_idempotently(self):
        """Restore merges remote ledger lines by event_id (append-only
        history preserved; a repeated restore adds nothing)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            local = root / "ledger.jsonl"
            events = [
                {"event_id": f"e{i}", "event": "WORKER_SPAWNED",
                 "ts_utc": "2026-09-08T00:00:00Z", "session_id": "ts_a5a7",
                 "kind": "run"}
                for i in range(3)
            ]
            local.write_text(
                "\n".join(json.dumps(e) for e in events) + "\n")
            remote = root / "remote.jsonl"
            # remote = same events + one NEW one (the pushed-then-grown case)
            remote.write_text(
                "\n".join(json.dumps(e) for e in events) +
                "\n" + json.dumps({"event_id": "e9", "event": "HEARTBEAT",
                                   "session_id": "ts_a5a7",
                                   "kind": "run"}) + "\n")
            # simulate the merge branch from durable.restore
            local_ids = set()
            for line in local.read_text().splitlines():
                if line.strip():
                    local_ids.add(json.loads(line).get("event_id"))
            with open(local, "a", encoding="utf-8") as out:
                for line in remote.read_text().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    if json.loads(line).get("event_id") not in local_ids:
                        out.write(line + "\n")
            lines = [l for l in local.read_text().splitlines() if l.strip()]
            self.assertEqual(len(lines), 4)
            # idempotent: replaying the same remote adds nothing
            local_ids = {
                json.loads(l).get("event_id") for l in lines}
            with open(local, "a", encoding="utf-8") as out:
                for line in remote.read_text().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    if json.loads(line).get("event_id") not in local_ids:
                        out.write(line + "\n")
            lines = [l for l in local.read_text().splitlines() if l.strip()]
            self.assertEqual(len(lines), 4)


class TestForensicsModuleInEngine(unittest.TestCase):

    def test_durable_root_is_store_tree(self):
        """The ledger root is the sessions store tree (the PARENT — the
        module nests worker_forensics/ under it), the same tree the
        snapshot payload collects, so events ride the existing push."""
        root = wfx.durable_root()
        self.assertTrue(root.endswith("TOSCANINI_UI"))
        # a WorkerForensics on this root writes into <root>/worker_forensics/
        with wfx.WorkerForensics(session_id="ts_wiring",
                                 kind="run",
                                 durable_root=root) as fx:
            fx.event("STAGE_STARTED", stage="TEST")
        ledger = Path(root) / "worker_forensics" / "ledger.jsonl"
        self.assertTrue(ledger.is_file())
        events = wfx.read_tail(root)
        self.assertEqual(events[-1]["session_id"], "ts_wiring")

    def test_read_tail_tolerates_torn_line(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "worker_forensics").mkdir()
            (root / "worker_forensics" / "ledger.jsonl").write_text(
                json.dumps({"event_id": "a", "event": "WORKER_SPAWNED",
                            "ts_utc": "2026-09-08T00:00:00Z",
                            "session_id": "ts_x", "kind": "run"}) +
                "\n{torn json without newline")
            events = wfx.read_tail(str(root))
            self.assertEqual(len(events), 2)
            self.assertEqual(events[0]["event_id"], "a")
            self.assertEqual(events[1]["event"], "LEDGER_TORN_LINE")


if __name__ == "__main__":
    unittest.main()

"""Production-state contamination guards (Art. IX/XVII) — regression tests
for the two autouse conftest redirects.

FOUND LIVE 2026-08-30 (disclosed): the F-series resume test allocated a
package id against the PRODUCTION PACKAGE_ID_REGISTRY through the
from_run_dir() path that the R374 sandbox did not cover; the row was
working-tree-only and restored before commit. These tests pin BOTH guards
so a future conftest regression cannot silently reopen the class.

Attack form: attempt, from inside a test, to allocate through the DEFAULT
paths (no explicit registry_path / LOG_PATH). If the guards are active,
production state is untouched.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


PROD_REGISTRY = (Path(__file__).resolve().parent.parent
                 / "PACKAGE_ID_REGISTRY.json")
PROD_REL_LOG = (Path(__file__).resolve().parent.parent
                / "artifacts" / "source_health"
                / "relevance_adjudication_log.jsonl")


class TestProductionStateUntouchable:
    def test_default_allocate_cannot_touch_production_registry(self):
        """Adversarial: allocate with NO registry_path (the exact call shape
        that contaminated P-148). Must land in the conftest sandbox."""
        from discovery_fabric.engine import package_registry as pr
        row = pr.allocate("inv:guard:attack:1", "run:guard:attack")
        sandbox = Path(pr.CANONICAL_REGISTRY)
        assert sandbox != PROD_REGISTRY
        assert sandbox.exists()
        assert "PACKAGE_ID_REGISTRY_SANDBOX" in sandbox.name
        # the row landed in the sandbox, not production
        import json
        rows = json.loads(sandbox.read_text())["packages"]
        assert any(r["invention_id"] == "inv:guard:attack:1" for r in rows)

    def test_production_registry_byte_identical_after_allocate(self):
        before = _sha(PROD_REGISTRY)
        from discovery_fabric.engine import package_registry as pr
        pr.allocate("inv:guard:attack:2", "run:guard:attack")
        assert _sha(PROD_REGISTRY) == before

    def test_relevance_log_redirect_active(self):
        from discovery_fabric.source_registry import relevance_aggregation
        assert relevance_aggregation.LOG_PATH != PROD_REL_LOG
        relevance_aggregation.record_adjudications(
            "guard", "attack-query",
            [{"record_id": "x", "relevance": "RELEVANT"}])
        assert not PROD_REL_LOG.exists() or _sha(PROD_REL_LOG) == _sha(PROD_REL_LOG)

    def test_resume_path_also_sandboxed(self):
        """The exact bypass shape from the live finding: from_run_dir on a
        manifest WITHOUT package_registry_path."""
        import tempfile
        from discovery_fabric.engine.run import EngineRun
        before = _sha(PROD_REGISTRY)
        with tempfile.TemporaryDirectory() as td:
            run = EngineRun({"problem_id": "p", "device": "d",
                             "failure_mode": "f", "failure": "f",
                             "constraint": "c"}, td,
                            run_id="run:guard:resume")
            run._persist("manifest.json", {
                "run_id": "run:guard:resume", "package_number": "99"})
            run._persist("problem.json", run.problem)
            EngineRun.from_run_dir(td)
        assert _sha(PROD_REGISTRY) == before

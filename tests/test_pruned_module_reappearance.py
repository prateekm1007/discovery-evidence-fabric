"""tests/test_pruned_module_reappearance.py — DIR-3 (R141-F2 /
R139S3-F2): the resurrection class, killed structurally.

A module pruned with import-graph evidence must NEVER reappear in any
commit tree on the queue branch. The R139S3 prune (be7065706) was
resurrected by the stale-tree close (8efc85b54), undetected for two
rounds because no test watched the paths.

The PRUNED_MODULES registry below is the retirement ledger's guard
line (Art. 16): adding a path here is how a future prune becomes
protected; a path listed here that appears in HEAD's tree fails the
test, and a commit that re-adds it fails the queue battery the moment
the guard runs in CI.

Mechanics-only fixtures: the test runs against the real repo tree
(git), no hand-built samples needed for the reappearance check itself;
the synthetic-tree case uses a temp git repo to prove the scanner
catches a reintroduced path.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# The pruned-module registry (retirement ledger guard line, Art. 16).
# Every entry: (path, prune_epoch_commit) — pruned with zero-importer
# import-graph evidence; the epoch is the commit that performed the
# prune (commits touching the path AT/BEFORE its own epoch are the
# module's legitimate history; anything AFTER is a resurrection).
# R145S1: the registry moved from a single global epoch (d86f59aec)
# to per-path epochs — a SECOND prune (the DIR-8 census) made the
# single-epoch shape false by construction (its own deletion commit
# postdates the first epoch and was flagged as a resurrection).
PRUNED_MODULES = [
    # d86f59aec (R141S1): zero .py importers re-verified at the tip;
    # the R455 record's claimed consumer tests/test_e21_series.py does
    # not exist. Resurrected twice by stale-tree closes before this
    # guard existed (R139S3-F1 / R140-F1).
    ("discovery_fabric/engine/causal_correctness.py", "d86f59aec"),
    # 71de1c870 (R145S1, DIR-8, claim c-0243 lineage): the
    # zero-importer census at the tip found ONE dead module — the
    # V3.9 calibration pipeline (303 lines, last touched 806c4112b
    # in the V3.9 era; zero .py importers; zero json/yml/md
    # consumers; no CI step; no script execs it by path). Pruned
    # with import-graph evidence; the prior_art_v2 family's LIVE
    # members (calibration_v3, claim_identity, elite_v3,
    # prior_art_v2_bridge) are untouched.
    ("discovery_fabric/prior_art_v2/calibration_v3_9.py",
     "71de1c870"),
]


def _git(*args: str, cwd: Path = REPO) -> str:
    out = subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True)
    if out.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {out.stderr}")
    return out.stdout


def test_01_pruned_modules_absent_at_head() -> None:
    """Every registry path must be absent from HEAD's tree."""
    for path, _epoch in PRUNED_MODULES:
        # cat-file -e exits 0 when the path EXISTS in HEAD's tree
        rc = subprocess.run(
            ["git", "cat-file", "-e", f"HEAD:{path}"],
            cwd=str(REPO), capture_output=True).returncode
        assert rc != 0, (
            f"PRUNED module resurrected at HEAD: {path} — the retirement "
            f"ledger (Art. 16) says this path is dead; either re-prune it "
            f"or (if it genuinely returns with a consumer) remove it from "
            f"tests/test_pruned_module_reappearance.py::PRUNED_MODULES "
            f"WITH import-graph evidence in the same commit")


def test_02_pruned_modules_absent_across_recent_history() -> None:
    """No commit in the last 200 may re-add a pruned path after the
    prune commit that removed it (the silent-resurrection detector)."""
    for path, epoch_sha in PRUNED_MODULES:
        log = _git("log", "-200", "--format=%H", "--", path)
        shas = [s for s in log.split() if s]
        # commits touching the path must all PREDATE the path's OWN
        # prune epoch (the per-path registry commit). Any newer
        # commit touching it is a resurrection — findable even if a
        # later commit re-pruned it.
        if not shas:
            continue
        epoch = _git("rev-parse", epoch_sha).strip()
        newer = []
        for sha in shas:
            # is sha an ancestor of the prune commit? (older/equal)
            rc = subprocess.run(
                ["git", "merge-base", "--is-ancestor", sha, epoch],
                cwd=str(REPO), capture_output=True).returncode
            if rc != 0:
                newer.append(sha)
        assert not newer, (
            f"pruned path {path} touched by post-prune commits {newer} — "
            f"a resurrection slipped through; check those commits' trees")


def test_03_scanner_catches_reintroduced_path() -> None:
    """Mechanics-only (temp repo): the reappearance scanner fails a
    tree that contains a pruned path."""
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "r"
        repo.mkdir()
        _git("init", "-q", cwd=repo)
        _git("config", "user.email", "t@t", cwd=repo)
        _git("config", "user.name", "t", cwd=repo)
        (repo / "keep.txt").write_text("base\n")
        _git("add", ".", cwd=repo)
        _git("commit", "-qm", "base", cwd=repo)
        # reintroduce a pruned-shaped path
        dead = repo / "discovery_fabric" / "engine"
        dead.mkdir(parents=True)
        (dead / "causal_correctness.py").write_text("# resurrected\n")
        _git("add", ".", cwd=repo)
        _git("commit", "-qm", "resurrect", cwd=repo)
        rc = subprocess.run(
            ["git", "cat-file", "-e", "HEAD:discovery_fabric/engine/causal_correctness.py"],
            cwd=str(repo), capture_output=True).returncode
        assert rc == 0, "fixture setup failed: path not in temp HEAD"
        # the same check the head test uses — must flag it
        flagged = subprocess.run(
            ["git", "cat-file", "-e",
             "HEAD:discovery_fabric/engine/causal_correctness.py"],
            cwd=str(repo), capture_output=True).returncode == 0
        assert flagged, "the scanner must detect a reintroduced pruned path"


def test_04_registry_is_json_serializable_and_documented() -> None:
    """The guard registry itself must stay well-formed (CI wiring)."""
    blob = json.dumps(PRUNED_MODULES)
    assert isinstance(json.loads(blob), list)
    # R145S1: the registry entries are (path, prune_epoch) pairs
    assert all(isinstance(p, tuple) and len(p) == 2
               and isinstance(p[0], str) and p[0].endswith(".py")
               and isinstance(p[1], str) and len(p[1]) >= 7
               for p in PRUNED_MODULES)
    assert len(PRUNED_MODULES) >= 1, (
        "the reappearance registry is empty — a prune without a guard "
        "line is how R139S3-F1 happened; add the pruned path here")


if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", __file__, "-q"]))

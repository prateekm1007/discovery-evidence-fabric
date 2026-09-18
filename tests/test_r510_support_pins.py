"""R510 support-script pins (auditor follow-up 1) — harness-only, scored set untouched.

Pins the five new R510 guard scripts against drift: tick placement + git
resolution, watchdog thresholds, replay determinism (watchdog signature and
failover policy), frozen-instrument reuse, honest block records, warm-path
schema, zero engine delta, English-only authorship. No model calls, no metered
spend, no secrets (BS-021): all assertions are local and hermetic except the
watchdog replay, which reads local git history only.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
R510 = REPO / "R510"
sys.path.insert(0, str(REPO / "scripts"))

import shutil

if not shutil.which("git"):  # Windows stock PATH gap (measured R510-C1)
    for _d in (r"C:\Program Files\Git\cmd", r"C:\Program Files\Git\bin",
               "/usr/bin", "/usr/local/bin"):
        _cand = os.path.join(_d, "git.exe" if os.name == "nt" else "git")
        if os.path.isfile(_cand):
            os.environ["PATH"] = _d + os.pathsep + os.environ.get("PATH", "")
            break

GIT = ["C:\\Program Files\\Git\\cmd\\git.exe", "git"]
GIT = next((g for g in GIT if g == "git" or os.path.isfile(g)), "git")


def test_tick_paths_under_r510():
    import r510_observe_tick as t
    assert Path(t.TICK_LOG).parent.name == "R510"
    assert Path(t.ALERT_LOG).parent.name == "R510"


def test_tick_git_resolver_finds_git():
    import r510_observe_tick as t
    assert t.ensure_git_on_path(), "git unresolvable even with install-dir fix"


def test_watchdog_thresholds_pinned():
    import r509_battery_watchdog as w
    assert w.STALLED_MIN == 82, "2 x p90=41 measured (n=98)"
    assert w.TIP_STALE_MIN == 30, "3 x 10.0-min checkpoint cadence"


def test_watchdog_signature_replay_deterministic():
    ref = json.loads((R510 / "REPLAY_R510_DRYRUN.json").read_text())
    out = Path(os.environ.get("TEMP", "/tmp")) / "r510_pin_replay.json"
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "r509_battery_watchdog.py"),
         "--replay", "2026-09-18T00:00Z", "2026-09-18T02:00Z",
         "--out", str(out)],
        cwd=str(REPO), capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-500:]
    got = json.loads(out.read_text())
    assert [(a["alert"], a["at"]) for a in got["alerts"]] == \
        [(a["alert"], a["at"]) for a in ref["alerts"]]
    assert got["polls"] == ref["polls"] == 25


def test_failover_replay_deterministic_and_green():
    p = R510 / "FAILOVER_REPLAY.json"
    before = hashlib.sha256(p.read_bytes()).hexdigest()
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "r510_failover_replay.py")],
        cwd=str(REPO), capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-500:]
    after = hashlib.sha256(p.read_bytes()).hexdigest()
    assert before == after, "policy replay must be byte-deterministic"
    assert json.loads(p.read_text())["acceptance"] is True


def test_wrapper_reuses_frozen_instrument_unedited():
    blob = subprocess.run(
        [GIT, "show", "HEAD:scripts/r505_a2_strong_ring.py"],
        cwd=str(REPO), capture_output=True, timeout=60).stdout
    assert hashlib.sha256(blob).hexdigest() == hashlib.sha256(
        (REPO / "scripts" / "r505_a2_strong_ring.py").read_bytes()).hexdigest()
    import r505_a2_strong_ring as frozen
    import r510_a2_dev_rerun as wrapper_mod  # noqa: F401 (import = reuse proof)
    assert "R505" in str(frozen.OUT_DIR), "frozen default output parent moved"


def test_diversity_block_record_honest():
    d = json.loads((R510 / "DIVERSITY_DRYRUN.json").read_text())
    assert [r["problem"] for r in d["problems"]] == ["B1", "E1", "F1"]
    assert all(r["grid_status"] == "PROVIDER_UNAVAILABLE" for r in d["problems"])
    assert d["acceptance_median_ge_3"] is False
    assert "never the scored" in json.dumps(d) or "breadth" in json.dumps(d)


def test_keyless_warm_schema_zero_spend():
    d = json.loads((R510 / "KEYLESS_WARM.json").read_text())
    assert d["metered_debits"] == 0
    assert len(d["probes"]) == 2
    blob = (R510 / "KEYLESS_WARM.json").read_text()
    assert not re.search(r"ghp_[A-Za-z0-9]{30,}|hf_[A-Za-z0-9]{30,}", blob)


def test_no_engine_delta():
    r = subprocess.run([GIT, "status", "--porcelain"], cwd=str(REPO),
                       capture_output=True, text=True, timeout=60)
    engine_roots = ("discovery_fabric/", "toscanini/", "orchestrator/",
                    "TOSCANINI_UI/", "Dockerfile", "requirements.txt")
    touched = [l[3:] for l in r.stdout.splitlines() if l.strip()]
    assert not [p for p in touched if p.startswith(engine_roots)], touched


def test_english_only_new_files():
    new = ["R510/OBSERVATION_PLAYBOOK.md", "R510/A2_V43_DEV_TRACK.md",
           "R510/RING_FAILOVER_DESIGN.md", "R510/DIVERSITY_ADAPTER_DESIGN.md",
           "R510/COLLISION_READINESS.md", "scripts/r510_observe_tick.py",
           "scripts/r510_a2_dev_rerun.py", "scripts/r510_failover_replay.py",
           "scripts/r510_diversity_dryrun.py", "scripts/r510_keyless_warm.py",
           "tests/test_r510_support_pins.py"]
    bad = []
    for rel in new:
        for ch in (REPO / rel).read_text(encoding="utf-8"):
            o = ord(ch)
            if (0x300 <= o <= 0x36F) or (0x400 <= o <= 0x4FF) or \
               (0x4E00 <= o <= 0x9FFF) or (0x600 <= o <= 0x6FF):
                bad.append((rel, hex(o)))
                break
    assert not bad, bad


def test_emission_lf_only():
    import subprocess
    out = subprocess.run(
        ["git", "ls-files", "R510/", "scripts/r510_a2_dev_rerun.py",
         "scripts/r510_observe_tick.py", "scripts/r510_failover_replay.py",
         "scripts/r510_diversity_dryrun.py", "scripts/r510_keyless_warm.py",
         "scripts/r510_space_deploy.py", "tests/test_r510_support_pins.py",
         "worklog.md"],
        capture_output=True, text=True, cwd=str(REPO)).stdout.splitlines()
    bad = [f for f in out if b"\r\n" in (REPO / f).read_bytes()]
    assert not bad, bad


def test_writers_force_lf():
    writers = ["scripts/r510_a2_dev_rerun.py", "scripts/r510_observe_tick.py",
               "scripts/r510_failover_replay.py",
               "scripts/r510_diversity_dryrun.py",
               "scripts/r510_keyless_warm.py", "scripts/r510_space_deploy.py"]
    missing = [w for w in writers
               if "newline=" not in (REPO / w).read_text(encoding="utf-8")]
    assert not missing, missing


def test_gitattributes_covers_text_types():
    attrs = (REPO / ".gitattributes").read_text(encoding="utf-8")
    for ext in ("*.json", "*.py", "*.md", "*.jsonl", "*.txt"):
        assert ext in attrs and "eol=lf" in attrs, ext

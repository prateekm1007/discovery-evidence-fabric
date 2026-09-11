"""render_worker.py — R441 the renderer process boundary.

Replaces the Blender subprocess boundary (render.py) as the PRIMARY
render path. Blender is demoted to format conversion only (operator
directive R441: "Never use it for normal hero renders").

Contract inherited from the R419/R420/R423 render path (unchanged
guarantees, new engine):

  * PINNED, fail-closed binary resolution — a Chrome that exists but
    cannot report a version is refused; the resolution trail is
    recorded (Art. VI: the binary identity is part of every record).
  * EXPLICIT environment allowlist — the renderer subprocess NEVER
    sees GITHUB_TOKEN / provider keys / operator keys / any unrelated
    secret (the R423A absent-by-construction contract, now applied to
    the Chromium boundary; adversarial regression in
    tests/test_r441_visual_compiler.py).
  * CGROUP-AWARE memory guard — measured against the container's REAL
    limit (the R420d lesson: /proc/meminfo reports the host). The
    Chrome baseline is measured and recorded in
    visual_compiler_thresholds.json (Art. XXVII provenance).
  * Bounded budget — one timeout for the whole visual set; a timeout
    is a typed failure, never a silent gap.

This module resolves binaries and runs them. It never decides WHAT the
scene looks like (scene_builder/camera_solver/material_mapper do) and
never decides whether the result is GOOD ENOUGH to ship
(visual_gate.py does) — generator/verifier separation (Art. XLV).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

RENDERER_DIR = Path(__file__).resolve().parent / "renderer"
THRESHOLD_PROVENANCE_PATH = Path(__file__).resolve().parent / \
    "visual_compiler_thresholds.json"

# pinned renderer stack (parity with TOSCANINI_UI/webapp/package.json)
PINNED_THREE_VERSION = "0.175.0"
PINNED_PUPPETEER_CORE_VERSION = "25.9.0"

# R423A boundary, re-expressed for Chromium: the renderer is UNTRUSTED
# compute; anything not listed is absent by construction.
RENDER_ENV_ALLOWLIST = (
    "PATH",
    "HOME",
    "TMPDIR",
    "LANG", "LC_ALL",
    "OMP_NUM_THREADS",
    "PYTHONIOENCODING",
    "NODE_PATH",
    "CHROME_PATH",
    "ENGINE_VC_TIMEOUT_S",
)

RENDER_SCRIPT = RENDERER_DIR / "render.js"


def _render_subprocess_env() -> Dict[str, str]:
    return {k: v for k, v in os.environ.items()
            if k in RENDER_ENV_ALLOWLIST}


# ---------------------------------------------------------------------------
# binary resolution (fail-closed, provenance trail — the render.py pattern)
# ---------------------------------------------------------------------------
_LAST_RESOLUTION: Dict[str, Any] = {"chrome_candidates": [],
                                    "node_candidates": []}


def _version_string(path: str, args: List[str]) -> Optional[str]:
    try:
        proc = subprocess.run([path, *args], capture_output=True,
                              text=True, timeout=30)
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    first = (proc.stdout or "").strip().splitlines()
    return first[0].strip() if first else None


def _puppeteer_cache_candidates() -> List[str]:
    """Chrome binaries installed by the puppeteer cache (~/.cache/
    puppeteer/chrome*/linux-*/...). Explicit operator override
    (CHROME_PATH) always wins; this scan is the documented discovery
    path, never a silent guess (every candidate is recorded)."""
    out: List[str] = []
    home = os.environ.get("HOME") or str(Path.home())
    cache = Path(home) / ".cache" / "puppeteer"
    if not cache.is_dir():
        return out
    for build in sorted(cache.glob("chrome*/linux-*"), reverse=True):
        for rel in ("chrome-linux64/chrome", "chrome-linux/chrome",
                    "chrome-headless-shell-linux64/chrome-headless-shell",
                    "chrome-headless-shell-linux/chrome-headless-shell"):
            p = build / rel
            if p.is_file() and os.access(p, os.X_OK):
                out.append(str(p))
    return out


# the fixed system locations probed by _system_chrome_candidates (a
# module constant so tests can patch the environment boundary)
_SYSTEM_CHROME_FIXED_PATHS = (
    "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
    "/snap/bin/chromium", "/opt/google/chrome/chrome",
)


def _system_chrome_candidates() -> List[str]:
    """Well-known system Chromium/Chrome locations (the Debian/Ubuntu
    packaging names plus the standard bin dirs). The detached artifact
    worker's R425 §7 env allowlist legitimately strips CHROME_PATH (a
    secret-hygiene boundary on the WORKER side), which left hosts whose
    only Chromium is the system package unable to resolve the renderer:
    observed live on the R446-HF-PRO Space (16 GB, chromium installed
    at /usr/bin/chromium) as typed RENDER_SKIPPED_NO_RENDERER while the
    binary was present and healthy. This probe ADDS candidates to the
    documented discovery scan — the operator override still wins, the
    puppeteer cache still precedes it, and the verification contract
    (the binary must answer --version) is UNCHANGED and fail-closed
    (every candidate is recorded; nothing is guessed silently)."""
    names = ("chromium", "chromium-browser", "google-chrome",
             "google-chrome-stable", "chrome")
    out: List[str] = []
    seen = set()
    for name in names:
        p = shutil.which(name)
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    for p in _SYSTEM_CHROME_FIXED_PATHS:
        if p not in seen and os.path.isfile(p) and os.access(p, os.X_OK):
            seen.add(p)
            out.append(p)
    return out


def find_chrome() -> Optional[str]:
    """Resolve + VERIFY the Chromium binary (fail-closed)."""
    trail: List[Dict[str, Any]] = []
    _LAST_RESOLUTION["chrome_candidates"] = trail
    cache_hits = _puppeteer_cache_candidates()
    system_hits = _system_chrome_candidates()
    candidates = ([("CHROME_PATH", os.environ.get("CHROME_PATH") or "")]
                  + [("PUPPETEER_CACHE", c) for c in cache_hits]
                  + [("SYSTEM_PATH", c) for c in system_hits])
    seen = set()
    for source, c in candidates:
        if not c or c in seen:
            continue
        seen.add(c)
        entry: Dict[str, Any] = {"source": source, "path": c}
        if not (os.path.isfile(c) and os.access(c, os.X_OK)):
            entry["result"] = "ABSENT"
            trail.append(entry)
            continue
        ver = _version_string(c, ["--version", "--no-sandbox"])
        entry["version_reported"] = ver
        if ver is None:
            entry["result"] = "REFUSED_BINARY_UNRESPONSIVE"
        else:
            entry["result"] = "ACCEPTED"
            _LAST_RESOLUTION["accepted_chrome"] = c
            _LAST_RESOLUTION["chrome_version"] = ver
            trail.append(entry)   # the accepted candidate IS evidence too
            return c
        trail.append(entry)
    _LAST_RESOLUTION["accepted_chrome"] = None
    return None


def find_node() -> Optional[str]:
    node = shutil.which("node")
    trail: List[Dict[str, Any]] = []
    _LAST_RESOLUTION["node_candidates"] = trail
    if node:
        ver = _version_string(node, ["--version"])
        trail.append({"source": "PATH", "path": node,
                      "version_reported": ver,
                      "result": "ACCEPTED" if ver else "REFUSED"})
        if ver:
            _LAST_RESOLUTION["node_version"] = ver
            return node
    _LAST_RESOLUTION["accepted_node"] = None
    return None


def last_resolution() -> Dict[str, Any]:
    out = dict(_LAST_RESOLUTION)
    out["pinned_three"] = PINNED_THREE_VERSION
    out["pinned_puppeteer_core"] = PINNED_PUPPETEER_CORE_VERSION
    return out


def renderer_deps_present() -> Optional[str]:
    """The renderer's node_modules must carry the pinned three version —
    anything else is a typed skip, never a silent downgrade."""
    pkg = RENDERER_DIR / "node_modules" / "three" / "package.json"
    if not RENDER_SCRIPT.is_file():
        return "RENDER_SCRIPT_MISSING"
    if not pkg.is_file():
        return "RENDER_SKIPPED_NO_RENDERER_DEPS"
    try:
        version = json.loads(pkg.read_text()).get("version")
    except Exception:  # noqa: BLE001
        return "RENDER_SKIPPED_NO_RENDERER_DEPS"
    if version != PINNED_THREE_VERSION:
        return f"RENDER_SKIPPED_THREE_VERSION_MISMATCH({version})"
    return None


# ---------------------------------------------------------------------------
# cgroup-aware memory guard (the R420d lesson, carried to Chromium)
# ---------------------------------------------------------------------------
def _cgroup_avail_mb(root: str = "/sys/fs/cgroup") -> Optional[int]:
    try:
        limit_raw = open(f"{root}/memory.max").read().strip()
        if limit_raw and limit_raw != "max":
            limit = int(limit_raw)
            current = int(open(f"{root}/memory.current").read().strip())
            if limit > 0:
                return max(0, limit - current) // (1024 * 1024)
    except (OSError, ValueError):
        pass
    try:
        limit = int(open(
            f"{root}/memory/memory.limit_in_bytes").read().strip())
        if 0 < limit < (1 << 40):
            current = int(open(
                f"{root}/memory/memory.usage_in_bytes").read().strip())
            return max(0, limit - current) // (1024 * 1024)
    except (OSError, ValueError):
        pass
    return None


def _host_avail_mb() -> Optional[int]:
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except OSError:
        pass
    return None


def _mem_available_mb() -> Optional[int]:
    cgroup = _cgroup_avail_mb()
    host = _host_avail_mb()
    if cgroup is not None and host is not None:
        return min(cgroup, host)
    return cgroup if cgroup is not None else host


def _thresholds() -> Dict[str, Any]:
    try:
        return json.loads(THRESHOLD_PROVENANCE_PATH.read_text())
    except Exception:  # noqa: BLE001
        return {}


def memory_guard(context: str, mode: str = "async") -> Optional[Dict[str, Any]]:
    """Typed skip when headless Chromium cannot fit (Art. LXI:
    infrastructure capacity is never a scientific verdict). Threshold
    provenance: visual_compiler_thresholds.json (measured, dated)."""
    th = _thresholds()
    need_mb = int(th.get("memory_guard_mb", {}).get(mode) or
                  {"in_worker": 800, "async": 650}.get(mode, 800))
    avail = _mem_available_mb()
    if avail is None or avail >= need_mb:
        return None
    basis = "CGROUP_AND_HOST" if (_cgroup_avail_mb() is not None
                                  and _host_avail_mb() is not None) \
        else ("CGROUP" if _cgroup_avail_mb() is not None else "HOST")
    return {
        "stage": "RENDER",
        "render_pipeline": "VISUAL_COMPILER_HEADLESS_THREE",
        "status": "RENDER_SKIPPED_LOW_MEMORY",
        "context": context,
        "mem_available_mb": avail,
        "mem_available_basis": basis,
        "required_mb": need_mb,
        "threshold_class": "ENGINEERING",
        "threshold_provenance": str(
            THRESHOLD_PROVENANCE_PATH.relative_to(
                RENDERER_DIR.parent.parent.parent.parent.parent))
        if THRESHOLD_PROVENANCE_PATH.is_file() else
        "visual_compiler_thresholds.json",
        "note": ("headless Chromium does not fit in available memory — "
                 "typed skip; the interactive GLB is served unchanged"),
    }


# ---------------------------------------------------------------------------
# the subprocess
# ---------------------------------------------------------------------------
def run_renderer(spec_path: str, timeout_s: int,
                 context: str = "visual_compiler") -> Dict[str, Any]:
    """Run the headless renderer over one spec. Returns the typed
    record fragments (status/artifacts/...) — never raises into the
    caller of the visual compiler."""
    t0 = time.time()
    record: Dict[str, Any] = {
        "stage": "RENDER",
        "render_pipeline": "VISUAL_COMPILER_HEADLESS_THREE",
        "renderer_stack": {
            "three": PINNED_THREE_VERSION,
            "puppeteer_core": PINNED_PUPPETEER_CORE_VERSION,
            "node": _LAST_RESOLUTION.get("node_version"),
            "chrome": _LAST_RESOLUTION.get("chrome_version"),
            "chrome_path": _LAST_RESOLUTION.get("accepted_chrome"),
        },
        "context": context,
        "budget_seconds": timeout_s,
    }
    node = find_node()
    chrome = find_chrome()
    record["binary_resolution"] = last_resolution()
    if not node or not chrome:
        record["status"] = "RENDER_SKIPPED_NO_RENDERER"
        record["note"] = ("no verified Chromium/Node pair for the "
                          "headless Three.js renderer — typed skip, "
                          "the interactive GLB is served unchanged")
        return record
    deps = renderer_deps_present()
    if deps:
        record["status"] = deps
        record["note"] = ("the renderer dependency contract is not met "
                          f"({deps}) — typed skip")
        return record

    env = _render_subprocess_env()
    env.setdefault("CHROME_PATH", chrome)
    try:
        proc = subprocess.run(
            [node, str(RENDER_SCRIPT), spec_path],
            capture_output=True, text=True, timeout=timeout_s,
            cwd=str(RENDERER_DIR), env=env)
    except subprocess.TimeoutExpired:
        record["status"] = "RENDER_TIMEOUT"
        record["timeout_seconds"] = timeout_s
        record["note"] = ("the visual set exceeded its budget — typed "
                          "failure; the GLB contract is unaffected")
        return record
    except Exception as exc:  # noqa: BLE001 — typed, never silent
        record["status"] = "RENDER_FAILED"
        record["error"] = f"{type(exc).__name__}: {exc}"
        return record

    record["exit_code"] = proc.returncode
    if (proc.stderr or "").strip():
        record["stderr_tail"] = (proc.stderr or "")[-2000:]
    out_dir = Path(spec_path).parent
    side = out_dir / "render_record.json"
    if side.is_file():
        try:
            side_rec = json.loads(side.read_text())
            record.update({k: v for k, v in side_rec.items()
                           if k not in ("stage", "render_pipeline")})
        except Exception:  # noqa: BLE001
            record["renderer_record_unreadable"] = True
    if proc.returncode != 0 and record.get("status") in (None, "OK"):
        record["status"] = "RENDER_FAILED"
    record["seconds"] = round(time.time() - t0, 2)
    return record

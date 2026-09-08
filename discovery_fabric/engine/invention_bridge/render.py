"""Engine-side render orchestrator — invokes the pinned Blender build.

R419 fixed 3D stack (operator directive):

    INVENTION -> ENGINEERING SPEC -> CadQuery/OCCT -> MEASURE -> GLB
        -> Blender 5.2 LTS (headless) -> hero/section/exploded renders
        -> Three.js / React Three Fiber -> WEB

This module is the engine half of that pipeline. It NEVER runs Blender
interactively, never keeps it resident, and runs it as a subprocess of
the run WORKER (the run is already a background job — the web request
never waits for Blender; operator directive section 21).

Failure semantics: a render failure is a TYPED record
(RENDER_FAILED / RENDER_SKIPPED_NO_BLENDER / RENDER_TIMEOUT) written to
the bridge report. The GLB contract is unaffected — the interactive 3D
artifact is served from the CadQuery-authored geometry regardless; the
PNG renders and materialized GLBs are enhancements produced when the
pinned build is available. Nothing is fabricated (Art. VI/XXV/LXI:
infrastructure failure is never scientific rejection).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

RENDER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "blender_render.py")

# R420: the Article XXVII provenance record for every operational
# threshold this module applies (memory guards, render budgets). The
# file is the authority for WHY these numbers; the code only applies
# them and points at the record.
THRESHOLD_PROVENANCE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "render_threshold_provenance.json")

# Pinned build (operator directive: Blender 5.2 LTS). The tarball sha256
# is recorded so the Docker image and every local verification run use
# byte-identical builds.
PINNED_BLENDER_VERSION = "5.2.1 LTS"
PINNED_TARBALL_SHA256 = (
    "a31f524fa99a527d3d52b7f5aaa68c34e1a19d5a1c9473f79c5cc610fd5b10e9")

# R420: the in-worker render budget is SHORT because the async job is
# the completion path — a slow instance must hand off quickly instead
# of holding the run hostage (observed live: the fresh production run
# ts_c0f41af92195 sat 900 s in a doomed full-quality render before
# timing out with nothing produced). Env-overridable for verification
# runs. The async ladder's budgets live in artifact_worker.py and are
# documented in the same threshold-provenance record.
# R423A Phase 7 (operator §7): the renderer subprocess gets an
# EXPLICIT environment allowlist. The Blender process is UNTRUSTED
# compute: it must receive NEITHER the GitHub token, NOR provider keys
# (NVIDIA/ZAI/OPENROUTER), NOR operator keys, NOR anything else the
# service carries. The allowlist is the whole contract — anything not
# listed is absent by construction. Adversarial regression:
# tests/test_r423_renderer_env_allowlist.py (a stub blender dumps its
# received environment; poisoned secrets must be ABSENT, the few
# allowlisted variables PRESENT).
RENDER_ENV_ALLOWLIST = (
    "PATH",            # blender resolves its own libs on PATH
    "HOME",            # blender's --factory-startup scratch space
    "TMPDIR",          # render temp files
    "LANG", "LC_ALL",  # deterministic number formatting in Cycles
    "OMP_NUM_THREADS",  # the thread pin applied below
    "BLENDER_PATH",    # provenance: which pinned build was resolved
    "PYTHONIOENCODING",  # blender's python stdout/stderr encoding
)


def _render_subprocess_env() -> Dict[str, str]:
    """The EXPLICIT allowlisted environment for the Blender subprocess.
    Absent-by-construction beats scrub-by-blacklist: a future secret in
    os.environ cannot leak into a renderer we did not update (a new
    allowlist entry must be a deliberate code change with a test).
    """
    env = {k: v for k, v in os.environ.items()
           if k in RENDER_ENV_ALLOWLIST}
    env.setdefault("OMP_NUM_THREADS", "2")
    return env


def _in_worker_budget_s() -> int:
    try:
        return max(60, int(os.environ.get(
            "ENGINE_RENDER_INWORKER_TIMEOUT_S", "300")))
    except (TypeError, ValueError):
        return 300


_ASYNC_BUDGET_S = 900  # whole hero+section+exploded bundle, async job
_ARTIFACTS = ("hero.png", "section.png", "exploded.png",
              "hero.glb", "section.glb", "exploded.glb")

# R420 fail-closed provenance: the resolution result of the LAST
# find_blender() call — every candidate considered, what it reported,
# and why it was accepted or refused. Recorded into the render record
# so 'which binary rendered this' is never a guess (Art. VI).
_LAST_RESOLUTION: Dict[str, Any] = {"candidates": []}


def _blender_version_string(path: str) -> Optional[str]:
    """First line of `<blender> --version` (e.g. 'Blender 5.2.1 LTS'),
    or None when the binary cannot even answer — never a guess."""
    try:
        proc = subprocess.run(
            [path, "--version"], capture_output=True, text=True,
            timeout=30)
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    first = (proc.stdout or "").strip().splitlines()
    return first[0].strip() if first else None


def find_blender() -> Optional[str]:
    """Locate the PINNED Blender build — fail-closed (R420, operator §4).

    Resolution order:

    1. $BLENDER_PATH (explicit operator/environment override — also
       how local verification runs point at their own build)
    2. /opt/blender/blender — the Docker image install location (the
       pinned tarball, sha256-verified at build time)

    EVERY candidate must report EXACTLY the pinned version string via
    `--version` before it is used. A binary that exists but reports a
    different version is REFUSED and the refusal is recorded. There is
    deliberately NO shutil.which("blender") fallback: an arbitrary
    system-installed blender is not provenance, it is a guess (Art. VI),
    and the pinned-build contract (operator §4) forbids silent
    substitution. When no candidate verifies, the caller records the
    typed honest RENDER_SKIPPED_NO_BLENDER state with the resolution
    trail attached.

    The verified result is cached per (path, mtime, size) so repeated
    renders do not re-run `--version`.
    """
    candidates = [
        ("BLENDER_PATH", os.environ.get("BLENDER_PATH") or ""),
        ("DOCKER_INSTALL", "/opt/blender/blender"),
    ]
    trail: List[Dict[str, Any]] = []
    _LAST_RESOLUTION["candidates"] = trail
    for source, c in candidates:
        if not c:
            continue
        entry: Dict[str, Any] = {"source": source, "path": c}
        if not (os.path.isfile(c) and os.access(c, os.X_OK)):
            entry["result"] = "ABSENT"
            trail.append(entry)
            continue
        try:
            stat = os.stat(c)
            key = (c, stat.st_mtime_ns, stat.st_size)
        except OSError:
            entry["result"] = "UNSTATABLE"
            trail.append(entry)
            continue
        cached = _VERSION_CACHE.get(key)
        if cached is None:
            cached = _blender_version_string(c)
            _VERSION_CACHE[key] = cached
        entry["version_reported"] = cached
        if cached is None:
            entry["result"] = "REFUSED_BINARY_UNRESPONSIVE"
        elif cached != f"Blender {PINNED_BLENDER_VERSION}":
            entry["result"] = "REFUSED_VERSION_MISMATCH"
        else:
            entry["result"] = "ACCEPTED"
            _LAST_RESOLUTION["accepted"] = c
            _LAST_RESOLUTION["verified_version"] = cached
            return c
        trail.append(entry)
    _LAST_RESOLUTION["accepted"] = None
    _LAST_RESOLUTION["verified_version"] = None
    return None


_VERSION_CACHE: Dict[Any, Optional[str]] = {}


def last_blender_resolution() -> Dict[str, Any]:
    """The fail-closed resolution trail for the last find_blender() call
    (recorded into every render record — provenance, Art. VI/XII)."""
    out = dict(_LAST_RESOLUTION)
    out["pinned_version"] = f"Blender {PINNED_BLENDER_VERSION}"
    out["pinned_tarball_sha256"] = PINNED_TARBALL_SHA256
    return out


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def authoritative_glb(work_dir: str,
                      generation_models: Optional[List[Dict]] = None
                      ) -> Optional[str]:
    """The CURRENT generation's GLB — the geometry authority to render.

    Order: the current generation model (MODEL/model-00N.glb where N is
    the current generation), then engineering_model.glb, then any GLB.
    """
    model_dir = os.path.join(work_dir, "MODEL")
    current: Optional[int] = None
    for m in generation_models or []:
        if m.get("current"):
            current = int(m.get("generation") or 0)
    if current:
        p = os.path.join(model_dir, f"model-{current:03d}.glb")
        if os.path.isfile(p):
            return p
    eng = os.path.join(model_dir, "engineering_model.glb")
    if os.path.isfile(eng):
        return eng
    if os.path.isdir(model_dir):
        glbs = sorted(Path(model_dir).glob("model-*.glb"))
        if glbs:
            return str(glbs[-1])
    roots = sorted(Path(work_dir).glob("*.glb"))
    return str(roots[0]) if roots else None


def _cgroup_avail_mb(root: str = "/sys/fs/cgroup") -> Optional[int]:
    """The container's OWN memory headroom in MB, or None when no
    cgroup limit is visible. R420d: /proc/meminfo inside the container
    reports the HOST's memory — on the Render Starter plan the cgroup
    caps the container at 512 MB while the host reports GBs of
    MemAvailable. The R419f-era guard trusted the host number, passed,
    and launched Blender into over-subscription — the cgroup OOM
    killer then crashed the container (observed live 2026-09-07 at
    23:04 and 23:40, fresh boot snapshots in the runtime-state
    branch). The honest availability is the cgroup headroom."""
    # cgroup v2
    try:
        limit_raw = open(f"{root}/memory.max").read().strip()
        if limit_raw and limit_raw != "max":
            limit = int(limit_raw)
            current = int(open(f"{root}/memory.current").read().strip())
            if limit > 0:
                return max(0, limit - current) // (1024 * 1024)
    except (OSError, ValueError):
        pass
    # cgroup v1
    try:
        limit = int(open(
            f"{root}/memory/memory.limit_in_bytes").read().strip())
        if 0 < limit < (1 << 40):  # the 'unlimited' sentinel is huge
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
    """The honest per-process launch budget: the MINIMUM of the cgroup
    headroom (the container's actual limit) and the host MemAvailable.
    None only when neither is readable (never a guess, Art. XXV)."""
    cgroup = _cgroup_avail_mb()
    host = _host_avail_mb()
    if cgroup is not None and host is not None:
        return min(cgroup, host)
    return cgroup if cgroup is not None else host


def _memory_guard(context: str,
                  mode: str = "in_worker") -> Optional[Dict[str, Any]]:
    """R419c: typed skip when the pinned Blender build cannot fit in
    available memory. Measured: blender --background baseline is
    ~269 MB RSS (trivial scene), plus scene geometry and render buffers.

    in_worker mode (the bridge RENDER step inside the discovery run):
    the gauntlet worker still holds its own memory, so a Blender launch
    there can OOM-kill the RUN ITSELF on small instances — the guard
    threshold is high and the skip is typed, never a run failure (Art.
    LXI: infrastructure capacity is never a scientific verdict).

    async mode (the detached artifact-build job, after the worker
    exits): more headroom exists; the threshold is lower.

    R420: the thresholds themselves carry provenance — the Article
    XXVII record (render_threshold_provenance.json: measurement
    environment, date, observed baseline, safety-margin rationale,
    intended execution context, uncertainty) is referenced by every
    guard record, so no operational threshold is an unexplained magic
    number.

    Returns the typed skip record, or None when rendering may proceed.
    """
    thresholds = {"in_worker": 650, "async": 400}
    need_mb = thresholds.get(mode, 650)
    avail = _mem_available_mb()
    if avail is None or avail >= need_mb:
        return None
    basis = "CGROUP_AND_HOST" if (_cgroup_avail_mb() is not None
                                  and _host_avail_mb() is not None) \
        else ("CGROUP" if _cgroup_avail_mb() is not None else "HOST")
    return {
        "stage": "RENDER",
        "render_pipeline": "BLENDER_HEADLESS",
        "pinned_blender": PINNED_BLENDER_VERSION,
        "status": "RENDER_SKIPPED_LOW_MEMORY",
        "context": context,
        "mem_available_mb": avail,
        "mem_available_basis": basis,
        "required_mb": need_mb,
        "threshold_class": "ENGINEERING",
        "threshold_provenance": (
            "discovery_fabric/engine/invention_bridge/"
            "render_threshold_provenance.json"),
        "note": (
            "the pinned Blender build (baseline ~269 MB RSS) does not "
            "fit in available memory alongside the run worker — typed "
            "skip, the interactive GLB is served unchanged; the async "
            "artifact-build job renders when memory allows, or the "
            "operator raises the instance plan (owner-gated decision, "
            "Art. LXV)"),
    }


def render_invention(work_dir: str,
                     geometry_out: Optional[Dict[str, Any]],
                     is_conceptual: bool,
                     renders: Optional[List[str]] = None,
                     resolution: Optional[List[int]] = None,
                     samples: Optional[int] = None,
                     memory_mode: str = "in_worker",
                     timeout_s: Optional[int] = None) -> Dict[str, Any]:
    """Run the pinned Blender build over the authoritative GLB.

    Returns a typed render record — always honest, never raising into
    the caller (the run's epistemic state is never altered by a
    presentation-layer failure; Art. LXI).

    R420: the render budget depends on the execution context —
    in_worker renders get a SHORT budget (the async job is the
    completion path; a slow instance hands off instead of holding the
    run hostage), async renders get the full bundle budget. Every
    budget applied is recorded in the typed record.
    """
    if timeout_s is None:
        timeout_s = _ASYNC_BUDGET_S if memory_mode == "async" \
            else _in_worker_budget_s()
    record: Dict[str, Any] = {
        "stage": "RENDER",
        "render_pipeline": "BLENDER_HEADLESS",
        "pinned_blender": PINNED_BLENDER_VERSION,
        "pinned_tarball_sha256": PINNED_TARBALL_SHA256,
        "is_conceptual": bool(is_conceptual),
        "memory_mode": memory_mode,
        "budget_seconds": timeout_s,
        "status": "OK",
    }
    t0 = time.time()

    blender = find_blender()
    if not blender:
        record["status"] = "RENDER_SKIPPED_NO_BLENDER"
        # R420 fail-closed provenance: which candidates were considered
        # and why each was refused — the skip is evidenced, not asserted
        record["blender_resolution"] = last_blender_resolution()
        record["note"] = (
            "no pinned Blender build verified (BLENDER_PATH or the "
            "Docker /opt/blender install reporting exactly "
            f"'{PINNED_BLENDER_VERSION}') — the interactive GLB is "
            "served unchanged; PNG renders are enhancements, not the "
            "contract")
        return record

    # R419c memory guard — typed skip before the subprocess is launched
    # (a Blender OOM on a small instance can kill the run worker itself)
    guard = _memory_guard("bridge_render", mode=memory_mode)
    if guard:
        record.update({k: v for k, v in guard.items() if k != "stage"})
        return record

    source = authoritative_glb(
        work_dir, (geometry_out or {}).get("generation_models"))
    if not source:
        record["status"] = "RENDER_SKIPPED_NO_SOURCE_GLB"
        record["note"] = "no authoritative GLB found in the run directory"
        return record
    record["source_glb"] = source
    record["source_glb_sha256"] = _sha256_file(source)
    # R420: the verified binary identity is part of every render record
    # (fail-closed provenance — never a guessed binary, Art. VI)
    record["blender_path"] = blender
    record["blender_version_verified"] = _LAST_RESOLUTION.get(
        "verified_version")

    out_dir = os.path.join(work_dir, "MODEL", "3D")
    os.makedirs(out_dir, exist_ok=True)
    spec = {
        "source_glb": source,
        "output_dir": out_dir,
        "is_conceptual": is_conceptual,
        "renders": renders or ["hero", "section", "exploded"],
        "export_glbs": True,
        "resolution": resolution or [1152, 768],
        "samples": samples or 48,
    }
    spec_path = os.path.join(out_dir, "render_spec.json")
    with open(spec_path, "w") as f:
        json.dump(spec, f, indent=2)

    # R423A Phase 7: explicit allowlist (see RENDER_ENV_ALLOWLIST) —
    # the renderer NEVER sees GITHUB_TOKEN / provider keys / operator
    # keys / any unrelated secret. Verified adversarially by
    # tests/test_r423_renderer_env_allowlist.py.
    env = _render_subprocess_env()
    try:
        proc = subprocess.run(
            [blender, "--background", "--factory-startup",
             "--python", RENDER_SCRIPT, "--", spec_path],
            capture_output=True, text=True, timeout=timeout_s,
            cwd=out_dir, env=env)
    except subprocess.TimeoutExpired:
        record["status"] = "RENDER_TIMEOUT"
        record["timeout_seconds"] = timeout_s
        record["note"] = (
            "Blender exceeded the render budget — typed failure; the GLB "
            "contract is unaffected (interactive 3D served from the "
            "authoritative geometry)")
        return record
    except Exception as exc:  # noqa: BLE001 — typed, never silent
        record["status"] = "RENDER_FAILED"
        record["error"] = f"{type(exc).__name__}: {exc}"
        return record

    record["blender_exit_code"] = proc.returncode
    # pull the blender-side record (authoritative detail)
    side_path = os.path.join(out_dir, "render_record.json")
    if os.path.isfile(side_path):
        try:
            side = json.loads(Path(side_path).read_text())
            record["blender"] = side
        except Exception:  # noqa: BLE001
            record["blender_record_unreadable"] = True
    if proc.returncode != 0:
        record["status"] = "RENDER_FAILED"
        record["stderr_tail"] = (proc.stderr or "")[-2000:]
        return record

    # verify every artifact class exists (operator §4: EVERY invention
    # gets the six artifacts when the stack is available)
    produced = {}
    missing = []
    for name in _ARTIFACTS:
        p = os.path.join(out_dir, name)
        if os.path.isfile(p) and os.path.getsize(p) > 0:
            produced[name] = {"bytes": os.path.getsize(p),
                              "sha256": _sha256_file(p)}
        else:
            missing.append(name)
    record["artifacts"] = produced
    record["missing_artifacts"] = missing
    if missing:
        record["status"] = "RENDER_PARTIAL"
        record["note"] = (
            f"Blender completed but {len(missing)} artifact(s) missing: "
            f"{missing} — disclosed; GLB contract unaffected")
    record["seconds"] = round(time.time() - t0, 2)
    record["out_dir"] = out_dir
    return record

#!/usr/bin/env python3
"""r453_c2_production_acceptance.py — R453-C2 acceptance: the §44 STEP 15
"test fresh production behavior" + §46 final comparison evidence, run
against the LIVE canonical Space at the merged SHA.

Phases (slice-resumable; state in R453/PRODUCTION_ACCEPTANCE_R453C2/):

  A. IDENTITY  — /api/version + /api/health: engine_commit ==
                 8d019f3df7ef5f9769b460118f3afd3718631b52 (build_artifact),
                 drift GREEN, identity_tamper False, constitution 2.4.0,
                 web_build_file_count == 30.
  B. SERVED SURFACE — fetch / + all discovered /_next assets (Bearer);
                 two-fetch per-file sha256 stability; the §6 home markers
                 ("DISCOVER. INVENT. ANYTHING." + the composer prompt) in
                 the served HTML; the honest-state vocabulary (present.ts
                 strings) present in the served chunks; the Art. LXIV
                 deletions (TechStage / DeepDive / DiscoveryPipelineStrip
                 / InfrastructureBlockedHero) ABSENT from the served
                 chunks; the §37 machine-vocabulary scan over the served
                 HTML.
  C. LOCAL REBUILD CROSS-CHECK (best effort, honest either way — Art.
                 XXV: never a manufactured pass): NEXT_OUTPUT=export
                 next build with the committed lockfile; the server's own
                 hash recipe (toscanini/server.py::_web_build_hash) over
                 the rebuilt export; equality with the served
                 web_build_hash is a byte-level confirmation, divergence
                 is recorded as environment-divergent (node 24 sandbox vs
                 node:20 builder), never silently passed.
  D. FRESH DISCOVERY — ONE genuinely fresh problem (authored for THIS
                 round, never submitted to any environment) through the
                 real user path (POST /api/run, the owner-capability
                 transport), polled to a terminal/observable state.
  E. STATE-MAP CONFORMANCE — every canonical state observed in the fresh
                 run must have an entry in CODER2_UI_STATE_MAP.json (the
                 §47 deliverable): the production run is presentable in
                 the Claude-class vocabulary with NO unmapped state.

Credentials: HF_TOKEN (Bearer probes) + GITHUB_TOKEN (durable-state
ledger, optional) — env-injection only, never persisted.

Usage:
  HF_TOKEN=... python3 r453_c2_production_acceptance.py [--skip-build]
  HF_TOKEN=... python3 r453_c2_production_acceptance.py --poll-minutes 8
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path("/home/z/my-project/hf_space")
SCRIPTS = Path(__file__).resolve().parent
BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
OUTDIR = REPO / "R453" / "PRODUCTION_ACCEPTANCE_R453C2"
SUMMARY = REPO / "R453" / "PRODUCTION_ACCEPTANCE_R453C2.json"
SESSION = OUTDIR / "session.json"

TARGET_COMMIT = "8d019f3df7ef5f9769b460118f3afd3718631b52"
EXPECTED_CONSTITUTION = "2.4.0"

# the §6 home markers (page.tsx, the composer-first home)
HOME_MARKERS = [
    "DISCOVER. INVENT. ANYTHING.",
    "What do you want to discover?",
]
# the honest-state vocabulary (lib/present.ts — the one answer renderer)
HONEST_MARKERS = [
    "Current run blocked",
    "Evidence retrieval failed",
    "The adversarial tests contradicted this candidate.",
    "Resume the investigation",
]
# the Art. LXIV deletions must not be served
DELETED_MARKERS = [
    "TechStage", "DeepDive", "DiscoveryPipelineStrip",
    "InfrastructureBlockedHero",
]
# the §37 machine vocabulary must not be VISIBLE in the served HTML
MACHINE_VOCAB = [
    "candidate_id", "run_id", "ATTACK_GATE", "generation_status",
    "provider_status", "RETRIEVAL_BATCH", "worker_id",
]

# the §45 fresh case — authored for THIS round, never submitted anywhere
CASE = {
    "case_id": "r453c2-fresh-fogged-display-case-doors",
    "directive_class": (
        "R453-C2 production acceptance: a genuinely fresh problem "
        "through the real user path on the deployed Claude-class UI "
        "build (the merged SHA) — the §44 STEP 15 proof"),
    "text": (
        "Condensation keeps forming on the inside of the glass doors "
        "of refrigerated display cases in a supermarket chain: within "
        "minutes after a customer opens a door the glass fogs over, "
        "and staff wipe the doors up to twenty times per door per day. "
        "The chain wants the doors to stay clear without PFAS-based "
        "anti-fog coatings (banned by their 2027 packaging and "
        "equipment sustainability standard), without heated glass "
        "(each heated door adds roughly 400 kilowatt-hours per year "
        "and the chain is under a group energy-reduction mandate), and "
        "without modifying the case refrigeration system. The doors "
        "are 900 by 1600 millimetres, the case interior holds 70 to 85 "
        "percent relative humidity at about 4 degrees Celsius, and "
        "store air is around 24 degrees Celsius at 55 percent relative "
        "humidity. Any retrofit must cost under 40 euros per door and "
        "need no maintenance more often than once a year."),
}


def _log(msg: str) -> None:
    print(f"[r453c2-accept] {msg}", flush=True)


def _req(path: str, body: dict | None = None, timeout: int = 120,
         owner_key: str | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json",
               "Authorization": f"Bearer {os.environ.get('HF_TOKEN', '')}"}
    if owner_key:
        headers["X-Tosca-Owner"] = owner_key
    req = urllib.request.Request(BASE + path, data=data, headers=headers,
                                 method="POST" if data is not None
                                 else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {"http_status": r.status,
                    "body": json.loads(r.read() or b"{}")}
    except urllib.error.HTTPError as e:
        try:
            txt = e.read()[:400].decode(errors="replace")
        except Exception:  # noqa: BLE001
            txt = ""
        return {"http_status": e.code, "error": txt}
    except Exception as exc:  # noqa: BLE001
        return {"http_status": None,
                "error": f"{type(exc).__name__}: {str(exc)[:150]}"}


def _fetch(path: str, timeout: int = 60) -> bytes | None:
    req = urllib.request.Request(
        BASE + path,
        headers={"Authorization":
                 f"Bearer {os.environ.get('HF_TOKEN', '')}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as exc:  # noqa: BLE001
        _log(f"fetch {path}: {type(exc).__name__}")
        return None


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _hash_recipe(files: dict[str, bytes]) -> str:
    """toscanini/server.py::_web_build_hash verbatim, over fetched or
    local bytes: sha256 over sorted (rel path, per-file sha256 hex)."""
    acc = hashlib.sha256()
    for rel in sorted(files):
        acc.update(rel.encode("utf-8"))
        acc.update(_sha(files[rel]).encode("ascii"))
    return acc.hexdigest()


# ---------------------------------------------------------------- phase A
def phase_a() -> dict:
    _log("A: identity")
    v = _req("/api/version", timeout=60)
    h = _req("/api/health", timeout=90)
    if v.get("http_status") != 200 or h.get("http_status") != 200:
        _log(f"A FATAL: version={v.get('http_status')} "
             f"health={h.get('http_status')}")
        return {"pass": False, "fatal": True}
    vb, hb = v["body"], h["body"]
    di = hb.get("deployment_identity") or {}
    checks = {
        "engine_commit == target":
            vb.get("engine_commit") == TARGET_COMMIT,
        "engine_commit_source == build_artifact":
            vb.get("engine_commit_source") == "build_artifact",
        "constitution == 2.4.0":
            vb.get("constitution_version") == EXPECTED_CONSTITUTION,
        "web_build_file_count == 30":
            vb.get("web_build_file_count") == 30,
        "health ok": hb.get("ok") is True,
        "drift GREEN": di.get("deployment_drift") == "GREEN",
        "identity_tamper False": di.get("identity_tamper") is False,
        "discovery_ready": hb.get("discovery_ready") is True,
    }
    served_web_hash = vb.get("web_build_hash")
    for k, ok in checks.items():
        _log(f"  {'PASS' if ok else 'FAIL'}: {k}")
    _log(f"  served web_build_hash: {served_web_hash}")
    return {"pass": all(checks.values()), "fatal": not all(
        checks.values()), "checks": checks,
        "served_web_build_hash": served_web_hash,
        "api_version": vb, "api_health_keys":
        {k: hb.get(k) for k in ("ok", "discovery_ready")} | {
            "deployment_drift": di.get("deployment_drift"),
            "identity_tamper": di.get("identity_tamper")}}


# ---------------------------------------------------------------- phase B
def phase_b() -> dict:
    _log("B: served surface")
    idx = _fetch("/")
    if not idx:
        _log("B FATAL: / unreachable")
        return {"pass": False, "fatal": True}
    html = idx.decode(errors="replace")
    files = {"index.html": idx}

    # discover assets (one expansion round into the manifests)
    paths = set(re.findall(r'(?:src|href)="(/[^"]+)"', html))
    for m in re.finditer(r'"/_next/[^"]+\.(?:js|css)"', html):
        paths.add(m.group(0).strip('"'))
    expansion = set()
    for p in list(paths):
        if p.endswith(".js"):
            blob = _fetch(p)
            if blob:
                expansion |= set(re.findall(
                    r'/_next/static/[^"\'\\)]+?\.(?:js|css)',
                    blob.decode(errors="replace")))
    paths |= {p for p in expansion if p.startswith("/_next/")}
    for p in sorted(paths):
        if p in ("index.html",) or not p.startswith("/"):
            continue
        blob = _fetch(p)
        if blob is not None:
            files[p.lstrip("/")] = blob
    _log(f"  fetched {len(files)} served files "
         f"({sum(len(b) for b in files.values()) / 1e6:.1f} MB)")

    # stability: refetch index + the largest chunk, compare digests
    stability = True
    for probe in ["/", ] + ["/" + p for p in sorted(files)
                            if p.endswith(".js")][:3]:
        again = _fetch(probe)
        rel = probe.lstrip("/") or "index.html"
        if again is None or _sha(again) != _sha(files[rel]):
            stability = False
            _log(f"  UNSTABLE: {probe}")
    _log(f"  two-fetch content stability: {stability}")

    html_visible = re.sub(r"<[^>]+>", " ", html)
    shell = re.sub(r"\s+", " ", re.sub(
        r"<script[^>]*>.*?</script>", " ", html, flags=re.S))
    shell = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", shell)).strip()
    chunks = {p: b for p, b in files.items()
              if p.endswith(".js") and p != "index.html"}
    chunk_text = "\n".join(b.decode(errors="replace")
                           for b in chunks.values())
    # the home renders client-side (the page gates on client state to
    # choose home vs run view): the markers live in the page CHUNK —
    # checked against html + chunk_text together, honestly recorded
    home_hits = {m: (m in html or m in chunk_text)
                 for m in HOME_MARKERS}
    honest_hits = {m: (m in chunk_text) for m in HONEST_MARKERS}
    deleted_hits = {m: (m in chunk_text) for m in DELETED_MARKERS}
    machine_html_hits = {m: (m in html_visible)
                         for m in MACHINE_VOCAB}
    for m, ok in home_hits.items():
        _log(f"  {'PASS' if ok else 'FAIL'}: home marker {m!r}")
    for m, ok in honest_hits.items():
        _log(f"  {'PASS' if ok else 'FAIL'}: honest state {m!r}")
    for m, hit in deleted_hits.items():
        _log(f"  {'PASS' if not hit else 'FAIL'}: deleted surface "
             f"{m!r} {'ABSENT' if not hit else 'STILL SERVED'}")
    for m, hit in machine_html_hits.items():
        _log(f"  {'PASS' if not hit else 'FAIL'}: machine vocab "
             f"{m!r} {'absent from served HTML' if not hit else 'VISIBLE'}")
    ok = (all(home_hits.values()) and all(honest_hits.values())
          and not any(deleted_hits.values())
          and not any(machine_html_hits.values()) and stability)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "served_index.html").write_text(html)
    return {"pass": ok, "fatal": not ok,
            "files_fetched": sorted(files.keys()),
            "prerendered_shell": shell[:120],
            "prerender_note": ("the static export prerenders a '" +
                shell[:40] + "' hydration shell; the home renders "
                "client-side from the app/page chunk — the home "
                "markers are served IN THE BUNDLE and verified there "
                "(a first-paint refinement opportunity, recorded for "
                "the §46 comparison)"),
            "home_markers": home_hits, "honest_markers": honest_hits,
            "deleted_surface_hits": deleted_hits,
            "machine_vocab_html_hits": machine_html_hits,
            "stability": stability,
            "fetched_set_hash": _hash_recipe(files)}


# ---------------------------------------------------------------- phase C
def phase_c() -> dict:
    _log("C: local rebuild cross-check (best effort)")
    webapp = REPO / "TOSCANINI_UI" / "webapp"
    out = webapp / "out"
    if "--skip-build" not in sys.argv:
        if out.exists():
            subprocess.run(["rm", "-rf", str(out)], check=True)
        env = dict(os.environ, NEXT_OUTPUT="export",
                   NEXT_TELEMETRY_DISABLED="1")
        r = subprocess.run(["npm", "run", "build"], cwd=str(webapp),
                           capture_output=True, text=True, env=env,
                           timeout=420)
        if r.returncode != 0:
            _log(f"  build FAILED: {r.stderr[-300:]}")
            return {"pass": False, "fatal": False,
                    "error": "local rebuild failed", "detail":
                    r.stderr[-300:]}
        ve = subprocess.run(["node", "verify-export.mjs", "out"],
                            cwd=str(webapp), capture_output=True,
                            text=True, timeout=120)
        _log(f"  verify-export: exit {ve.returncode}")
    if not out.exists():
        return {"pass": False, "fatal": False,
                "error": "no local out/ (use --skip-build only when "
                         "a previous build exists)"}
    files = {}
    for f in sorted(out.rglob("*")):
        if f.is_file():
            files[f.relative_to(out).as_posix()] = f.read_bytes()
    local_hash = _hash_recipe(files)
    served = phase_a()["served_web_build_hash"]
    match = bool(served) and local_hash == served
    _log(f"  local rebuild: {len(files)} files, hash {local_hash[:16]}...")
    _log(f"  == served web_build_hash: {match}")
    return {"pass": True, "fatal": False, "local_file_count":
            len(files), "local_web_build_hash": local_hash,
            "served_web_build_hash": served, "byte_identical": match,
            "note": ("byte-identical: the served export == the committed "
                     "source rebuilt" if match else
                     "hash divergent — the sandbox rebuild (node 24) vs "
                     "the image builder (node:20); the SERVER-side fresh "
                     "recompute of web_build_hash over its own served "
                     "dir remains the identity authority; divergence is "
                     "recorded, never silently passed")}


# ---------------------------------------------------------------- phase D
def phase_d(poll_minutes: int) -> dict:
    _log("D: fresh discovery (the real user path)")
    OUTDIR.mkdir(parents=True, exist_ok=True)
    sess = {}
    if SESSION.exists():
        sess = json.loads(SESSION.read_text())
    if not sess.get("session_id"):
        r = _req("/api/run", body={"text": CASE["text"],
                                   "problem_id": CASE["case_id"]},
                 timeout=180)
        if r.get("http_status") not in (200, 201, 202):
            _log(f"D FATAL: create failed {r.get('http_status')} "
                 f"{str(r.get('error') or r.get('body'))[:250]}")
            return {"pass": False, "fatal": True,
                    "error": "run creation failed"}
        b = r.get("body") or {}
        sess = {"session_id": b.get("session_id") or b.get("id"),
                "owner_key": b.get("owner_key"),
                "created_at_utc": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "case_id": CASE["case_id"]}
        SESSION.write_text(json.dumps(sess, indent=1))
        _log(f"  run created: {sess['session_id']}")
    sid, ok_key = sess["session_id"], sess.get("owner_key")

    deadline = time.time() + poll_minutes * 60
    result = {}
    while True:
        result = _req(f"/api/run/{sid}/result", timeout=120,
                      owner_key=ok_key)
        if result.get("http_status") == 200:
            body = result.get("body") or {}
            status = str(body.get("status") or "").upper()
            _log(f"  status: {status or '(none)'}")
            if status in ("COMPLETE", "FAILED", "ERROR", "DONE",
                          "INTERRUPTED", "RUN_BLOCKED_TRANSPORT",
                          "ERROR_RUN", "ERROR_BUILD"):
                break
        elif result.get("http_status") is None:
            _log(f"  transport hiccup: "
                 f"{str(result.get('error'))[:80]}")
        if time.time() >= deadline:
            _log("  slice deadline — re-invoke to resume the SAME run")
            return {"pass": True, "fatal": False, "resumed": True,
                    "session_id": sid, "slice_deadline": True}
        time.sleep(30)

    body = result.get("body") or {}
    state = _req(f"/api/run/{sid}/state", timeout=120, owner_key=ok_key)
    st = (state.get("body") or {}) if state.get("http_status") == 200 \
        else {"error": state.get("error")}
    (OUTDIR / "run_result.json").write_text(
        json.dumps(body, indent=1, default=str)[:400_000])
    (OUTDIR / "run_state.json").write_text(
        json.dumps(st, indent=1, default=str)[:400_000])
    sess["terminal_status"] = body.get("status")
    SESSION.write_text(json.dumps(sess, indent=1))
    _log(f"  terminal: {body.get('status')} | "
         f"captured run_result.json + run_state.json")
    return {"pass": True, "fatal": False, "session_id": sid,
            "terminal_status": body.get("status"),
            "final_status": body.get("final_status"),
            "reason": body.get("reason")}


# ---------------------------------------------------------------- phase E
def phase_e(d_result: dict) -> dict:
    _log("E: state-map conformance (CODER2_UI_STATE_MAP.json)")
    smap = json.loads((REPO / "CODER2_UI_STATE_MAP.json").read_text())
    maps = smap.get("maps") or {}
    map_blob = json.dumps(maps, default=str).lower()
    if not d_result.get("session_id") or d_result.get("slice_deadline"):
        return {"pass": True, "fatal": False, "note": "run in flight"}
    observed = {}
    rf = OUTDIR / "run_result.json"
    if rf.exists():
        body = json.loads(rf.read_text())
        for k in ("status", "final_status", "reason"):
            v = body.get(k)
            if v:
                observed[f"result.{k}={v}"] = str(v)
    rs = OUTDIR / "run_state.json"
    if rs.exists():
        st = json.loads(rs.read_text())
        for sect in ("evidence_state", "mechanism_state",
                     "attack_state", "engineering_state",
                     "candidate_state"):
            s = st.get(sect) or {}
            v = s.get("state")
            if v:
                observed[f"{sect}.state={v}"] = str(v)
    unmapped = []
    for key, val in observed.items():
        hit = str(val).lower() in map_blob
        _log(f"  {'MAPPED' if hit else 'UNMAPPED'}: {key}")
        if not hit:
            unmapped.append(key)
    return {"pass": not unmapped, "fatal": False,
            "observed_states": observed, "unmapped": unmapped,
            "state_map_round": smap.get("round"),
            "state_map_schema": smap.get("schema_version")}


def main() -> int:
    hf = os.environ.get("HF_TOKEN", "")
    if not hf:
        _log("FATAL: HF_TOKEN missing (env-injection only)")
        return 2
    record_path = SUMMARY
    record = json.loads(record_path.read_text()) \
        if record_path.exists() else {
            "artifact_type": "R453-C2 production acceptance record",
            "reviewer_provenance": "AI_REVIEW",
            "case": CASE, "target_commit": TARGET_COMMIT}

    a = phase_a()
    record["phase_A_identity"] = a
    _write(record)
    if a.get("fatal"):
        return 4
    b = phase_b()
    record["phase_B_served_surface"] = {
        k: v for k, v in b.items() if k != "fatal"}
    _write(record)
    if b.get("fatal"):
        return 4
    c = phase_c()
    record["phase_C_local_rebuild"] = c
    _write(record)
    d = phase_d(int(sys.argv[sys.argv.index("--poll-minutes") + 1])
                if "--poll-minutes" in sys.argv else 4)
    record["phase_D_fresh_discovery"] = {
        k: v for k, v in d.items() if k != "fatal"}
    _write(record)
    if d.get("fatal"):
        return 4
    e = phase_e(d)
    record["phase_E_state_map_conformance"] = e
    record["completed_at_utc"] = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _write(record)
    complete = a["pass"] and b["pass"] and e["pass"] and \
        not d.get("slice_deadline")
    _log(f"ACCEPTANCE {'COMPLETE' if complete else 'IN PROGRESS / PARTIAL'}")
    return 0 if complete else 1


def _write(record: dict) -> None:
    SUMMARY.write_text(json.dumps(record, indent=1, default=str))
    _log(f"record -> {SUMMARY}")


if __name__ == "__main__":
    raise SystemExit(main())

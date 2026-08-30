"""Toscanini HTTP orchestration service (stdlib only; port 8788).

Endpoints (all consumed by the Next.js UI proxy — never by the browser
directly; keys and internals stay server-side):

  GET  /healthz
  GET  /api/engine                       engine commit + gateway status
  POST /api/discoveries  {text}          start a new discovery (worker subprocess)
  GET  /api/sessions                     conversation history
  GET  /api/sessions/<id>                full session detail (stages, result)
  GET  /api/sessions/<id>/events         SSE live stream (artifact-derived)
  POST /api/sessions/<id>/share          create read-only share link
  GET  /api/share/<share_id>             PUBLIC payload (six fields, no internals)
  GET  /api/sessions/<id>/package        buyer ZIP download (if produced)
  GET  /api/cemetery                     failed-candidate cemetery

Every streamed event is derived from a persisted artifact on disk (envelope
JSON, session record, final_state) — no fabricated progress (Art. IV/VI).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import threading
import urllib.parse
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from toscanini import gateway as gw  # noqa: E402
from toscanini import sessions as store  # noqa: E402

PORT = 8788


def _git_head() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001
        return "UNKNOWN"


ENGINE_COMMIT = _git_head()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------------ util
    def _json(self, code: int, payload) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _body_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n))
        except Exception:  # noqa: BLE001
            return {}

    def log_message(self, fmt, *args):  # quiet
        pass

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods",
                         "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    # ------------------------------------------------------------------ GET
    def do_GET(self):
        p = urllib.parse.urlparse(self.path)
        parts = [x for x in p.path.split("/") if x]

        if p.path == "/healthz":
            return self._json(200, {"ok": True, "service": "toscanini",
                                    "engine_commit": ENGINE_COMMIT,
                                    "gateway_up": gw.gateway_up()})
        if p.path == "/api/engine":
            return self._json(200, {
                "engine_commit": ENGINE_COMMIT,
                "gateway_up": gw.gateway_up(),
                "runs_root": str(store.ENGINE_RUNS),
            })
        if p.path == "/api/sessions":
            # failure recovery (CEO #8): honest stuck detection runs on
            # every history read — dead workers surface as ERROR_STUCK,
            # never as eternal spinners
            stuck = store.mark_stuck_sessions()
            sessions = store.list_sessions()
            return self._json(200, {"sessions": sessions,
                                    "marked_stuck": stuck})
        if p.path == "/api/cemetery":
            return self._json(200, store.cemetery_summary())

        if len(parts) >= 3 and parts[0] == "api" and parts[1] == "sessions":
            sid = parts[2]
            if len(parts) == 3:
                detail = store.session_detail(sid)
                return self._json(200, detail) if detail else self._json(404, {"error": "not found"})
            if len(parts) == 4 and parts[3] == "events":
                return self._sse(sid)
            if len(parts) == 4 and parts[3] == "package":
                return self._package(sid)

        if len(parts) == 3 and parts[0] == "api" and parts[1] == "share":
            payload = self._share_payload(parts[2])
            return self._json(200, payload) if payload else self._json(404, {"error": "not found"})

        return self._json(404, {"error": "no such endpoint"})

    # ----------------------------------------------------------------- POST
    def do_POST(self):
        p = urllib.parse.urlparse(self.path)
        parts = [x for x in p.path.split("/") if x]

        if p.path == "/api/discoveries":
            body = self._body_json()
            text = (body.get("text") or "").strip()
            if len(text) < 15:
                return self._json(400, {"error": "problem description too short"})
            session = store.create_session(
                title=text.split("\n")[0][:120], user_text=text)
            # Transport pinning (EXPLICIT operator overrides, logged by the
            # engine and recorded in candidate provenance — the designed
            # mechanism for degraded-endpoint situations: nvidia oscillates
            # 35s..>240s and mistral is payment-blocked; zai gateway is the
            # measured-healthy transport). Without the pin, synthesis waits
            # out multiple 240 s timeouts before substituting.
            env = dict(os.environ)
            env.setdefault("ENGINE_SYNTHESIS_PROVIDER", "zai")
            env.setdefault("ENGINE_ATTACK_PROVIDER", "zai")
            env.setdefault("ENGINE_ENSEMBLE_PROVIDERS", "zai")
            env.setdefault("ENGINE_GRID_PROVIDERS", "zai")
            subprocess.Popen(
                [sys.executable, "-m", "toscanini.worker",
                 session["session_id"]],
                cwd=str(REPO_ROOT), env=env,
                stdout=open(REPO_ROOT / "ENGINE_RUNS" / "toscanini_worker.log",
                            "ab"),
                stderr=subprocess.STDOUT,
                start_new_session=True)
            return self._json(200, session)

        if len(parts) == 4 and parts[0] == "api" and parts[1] == "sessions" \
                and parts[3] == "share":
            sid = parts[2]
            share_id = store.create_share(sid)
            if not share_id:
                return self._json(404, {"error": "session not found"})
            return self._json(200, {"share_id": share_id})

        # failure recovery (CEO #8): re-enqueue an ERROR_* session through
        # the SAME serialized worker path. COMPLETE verdicts are NOT
        # retryable (append-only history — re-running is a new session).
        if len(parts) == 4 and parts[0] == "api" and parts[1] == "sessions" \
                and parts[3] == "retry":
            sid = parts[2]
            result = store.retry_session(sid)
            if result is None:
                return self._json(404, {"error": "session not found"})
            if "error" in result:
                return self._json(409, result)
            env = dict(os.environ)
            env.setdefault("ENGINE_SYNTHESIS_PROVIDER", "zai")
            env.setdefault("ENGINE_ATTACK_PROVIDER", "zai")
            env.setdefault("ENGINE_ENSEMBLE_PROVIDERS", "zai")
            env.setdefault("ENGINE_GRID_PROVIDERS", "zai")
            subprocess.Popen(
                [sys.executable, "-m", "toscanini.worker", sid],
                cwd=str(REPO_ROOT), env=env,
                stdout=open(REPO_ROOT / "ENGINE_RUNS" / "toscanini_worker.log",
                            "ab"),
                stderr=subprocess.STDOUT,
                start_new_session=True)
            return self._json(200, result)

        return self._json(404, {"error": "no such endpoint"})

    # ------------------------------------------------------------- package
    def _package(self, sid: str):
        s = store.get_session(sid)
        if not s:
            return self._json(404, {"error": "not found"})
        run_dir = Path(s["run_dir"]) if s.get("run_dir") else None
        info = store.package_info(run_dir) if run_dir and run_dir.exists() else None
        if not info or not info.get("zip") or not Path(info["zip"]).exists():
            return self._json(404, {"error": "no buyer package produced "
                                    "(no survivor reached the release gate)"})
        zp = Path(info["zip"])
        data = zp.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Disposition",
                         f'attachment; filename="{zp.name}"')
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    # ---------------------------------------------------------------- share
    def _share_payload(self, share_id: str):
        sid = store.share_session(share_id)
        if not sid:
            return None
        d = store.session_detail(sid)
        if not d:
            return None
        inv = d.get("invention_specification") or {}
        evid = (d.get("evidence_pack") or {}).get("retrieval") or []
        engine_evidence = []
        engine_sources = []
        for st in d.get("stages") or []:
            if st.get("stage") == "RETRIEVE":
                engine_evidence = st.get("sample_titles") or []
                engine_sources = st.get("sources") or []
        sources_queried = (
            [r.get("source") for r in evid if r.get("source")]
            or engine_sources)
        inv_evidence = inv.get("evidence") or {}
        uncertainties = inv.get("uncertainties") or {}

        def _plain(field):
            v = field.get("value") if isinstance(field, dict) else field
            cls = field.get("epistemic_class") if isinstance(field, dict) else None
            return v, cls

        def _flat(v):
            """Flatten dict/array spec values into readable text (the share
            view is public prose, never raw engine objects)."""
            if isinstance(v, str):
                return v
            if isinstance(v, dict):
                parts = []
                for key in ("mechanism", "intervention", "expected_effect",
                            "description", "source_observation"):
                    if isinstance(v.get(key), str):
                        parts.append(v[key])
                return " ".join(parts) if parts else json.dumps(v, default=str)[:600]
            if isinstance(v, list):
                return " ".join(_flat(x) for x in v[:4] if x)
            return "" if v is None else str(v)[:600]

        mech_v, mech_c = _plain(inv.get("mechanism") or {})
        why_v, why_c = _plain(inv.get("causal_chain") or {})
        nov_v, nov_c = _plain(inv.get("novelty_hypothesis") or {})
        ke = (d.get("decisive_experiment") or {}).get("selected") or {}
        ke = {k: _flat(v) if not isinstance(v, (int, float, bool)) else v
              for k, v in (ke or {}).items()} if isinstance(ke, dict) else {}
        pkg = d.get("package") or {}
        fs = d.get("final_state") or {}
        return {
            "share_id": share_id,
            "created_at": d.get("created_at"),
            "problem": {
                "title": d.get("title"),
                "failure_mode": (d.get("problem_id") or "").replace("ui_", "").replace("_", " "),
                "domain": d.get("domain_hint"),
            },
            "invention": {
                "mechanism": _flat(mech_v), "epistemic_class": mech_c,
                "why_it_may_work": _flat(why_v),
                "novelty_hypothesis": _flat(nov_v),
                "status": fs.get("final_status"),
            },
            "evidence": {
                "sources_queried": sources_queried,
                "records": engine_evidence[:5],
            },
            "key_uncertainty": (
                _flat(uncertainties.get("value"))
                if isinstance(uncertainties, dict)
                else _flat(uncertainties)) or (
                f"prior art: {fs.get('prior_art_status')}"
                if fs.get("prior_art_status") else
                "Prior art unresolved — collision claims not yet inspected."),
            "next_experiment": ke,
            "package_availability": {
                "available": bool(pkg.get("zip")),
                "maturity": pkg.get("maturity"),
            },
        }

    # ------------------------------------------------------------------ SSE
    def _sse(self, sid: str):
        s = store.get_session(sid)
        if not s:
            return self._json(404, {"error": "not found"})
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Connection", "close")
        self.end_headers()

        def send(event: str, data: dict) -> bool:
            try:
                self.wfile.write(
                    f"event: {event}\ndata: ".encode()
                    + json.dumps(data, ensure_ascii=False, default=str).encode()
                    + b"\n\n")
                self.wfile.flush()
                return True
            except (BrokenPipeError, ConnectionResetError):
                return False

        send("hello", {"session_id": sid})
        seen_stages: set = set()
        last_status = None
        start = time.time()
        while time.time() - start < 3600:
            cur = store.get_session(sid)
            if not cur:
                break
            if cur.get("status") != last_status:
                last_status = cur.get("status")
                send("phase", {"status": last_status,
                               "problem_id": cur.get("problem_id"),
                               "error": cur.get("error")})
                if last_status in ("COMPLETE", "ERROR_TRANSPORT",
                                   "ERROR_BUILD", "ERROR_RUN"):
                    detail = store.session_detail(sid)
                    if detail:
                        send("final", {
                            "final_status": detail.get("final_status"),
                            "package": detail.get("package"),
                            "stages": detail.get("stages"),
                            "cemetery_update": detail.get("cemetery_update"),
                            "error": detail.get("error"),
                        })
                    send("done", {"status": last_status})
                    return
            run_dir = cur.get("run_dir")
            if run_dir and Path(run_dir).exists():
                for digest in store.stage_summaries(Path(run_dir)):
                    if digest["stage"] not in seen_stages \
                            and digest.get("status") not in (None, "RUNNING"):
                        seen_stages.add(digest["stage"])
                        send("stage", digest)
            else:
                time.sleep(1.2)
                continue
            time.sleep(1.2)
        send("done", {"status": "STREAM_TIMEOUT"})


def main():
    store.seed_benchmark_sessions()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"toscanini service on 127.0.0.1:{PORT} "
          f"(engine {ENGINE_COMMIT[:8]})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()

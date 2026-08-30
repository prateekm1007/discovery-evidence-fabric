"""Session store — the UI's conversation history.

Constitutional note (Art. X): the ENGINE RUN DIRECTORY is the authoritative
record of what happened. This store is an INDEX: session_id -> where the
truth lives (run_dir, final_state, package), plus UI-only metadata (title,
timestamps, share ids). If the store and a run artifact disagree, the run
artifact wins — session_detail() always re-reads the run dir.

Seeding: the six-domain benchmark runs (2026-08-30) are ingested as REAL
historical sessions with their actual outcomes — labeled with their true
origin, never presented as UI-generated.
"""
from __future__ import annotations

import fcntl
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
STORE_DIR = REPO_ROOT / "TOSCANINI_UI"
SESSIONS_PATH = STORE_DIR / "sessions.json"
SHARES_PATH = STORE_DIR / "shares.json"
ENGINE_RUNS = REPO_ROOT / "ENGINE_RUNS"

STAGES = ["RETRIEVE", "FREEZE", "SYNTHESIZE", "VERIFY",
          "MULTI_SOURCE_DISCOVERY", "COLLISION", "ATTACK",
          "CONTRADICTION", "KILLER_EXPERIMENT", "ADJUDICATION",
          "CLASSIFY", "NEXT_BEST_ACTION", "RANK"]

# ---------------------------------------------------------------------------
# Run-dir derived detail (the AUTHORITY — re-read from disk every time)
# ---------------------------------------------------------------------------

def _locked_read(path: Path):
    if not path.exists():
        return {}
    with open(path, "r") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            return json.load(f)
        except (json.JSONDecodeError, ValueError):
            # A store file truncated by a crashed writer is absent data,
            # not fabricated data — read as empty (Art. XXV: honest absent).
            return {}
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _locked_write(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(data, f, indent=1, ensure_ascii=False)
        fcntl.flock(f, fcntl.LOCK_UN)


def list_sessions() -> List[Dict[str, Any]]:
    return sorted(_locked_read(SESSIONS_PATH).get("sessions", []),
                  key=lambda s: s.get("created_at", ""), reverse=True)


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    for s in list_sessions():
        if s.get("session_id") == session_id:
            return s
    return None


def update_session(session_id: str, **fields) -> Optional[Dict[str, Any]]:
    data = _locked_read(SESSIONS_PATH)
    for s in data.get("sessions", []):
        if s.get("session_id") == session_id:
            s.update(fields)
            _locked_write(SESSIONS_PATH, data)
            return s
    return None


def create_session(title: str, user_text: str, domain_hint: str = "") -> Dict[str, Any]:
    session = {
        "session_id": f"ts_{uuid.uuid4().hex[:12]}",
        "title": title[:120],
        "user_text": user_text[:4000],
        "domain_hint": domain_hint,
        "origin": "toscanini_ui",
        "status": "BUILDING_PROBLEM",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run_dir": None,
        "problem_id": None,
        "final_status": None,
        "package": None,
        "share_id": None,
        "error": None,
    }
    data = _locked_read(SESSIONS_PATH)
    data.setdefault("sessions", []).append(session)
    _locked_write(SESSIONS_PATH, data)
    return session


# ---------------------------------------------------------------------------
# Share registry (read-only public invention views)
# ---------------------------------------------------------------------------

def create_share(session_id: str) -> Optional[str]:
    s = get_session(session_id)
    if not s:
        return None
    if s.get("share_id"):
        return s["share_id"]
    share_id = uuid.uuid4().hex[:16]
    data = _locked_read(SHARES_PATH)
    data[share_id] = {"session_id": session_id,
                      "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                  time.gmtime())}
    _locked_write(SHARES_PATH, data)
    update_session(session_id, share_id=share_id)
    return share_id


def share_session(share_id: str) -> Optional[str]:
    data = _locked_read(SHARES_PATH)
    entry = data.get(share_id)
    return entry["session_id"] if entry else None


# ---------------------------------------------------------------------------
# Run-dir derived detail (the AUTHORITY — re-read from disk every time)
# ---------------------------------------------------------------------------

def _read_json(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return None


def stage_summaries(run_dir: Path) -> List[Dict[str, Any]]:
    """One digest per engine stage, in canonical order, from persisted
    envelopes. Absent envelope = stage not reached yet (honest)."""
    out = []
    for stage in STAGES:
        env = _read_json(run_dir / f"envelope_{stage}.json")
        if env is None:
            continue
        log = None
        for entry in reversed(env.get("stage_log") or []):
            if entry.get("stage") == stage:
                log = entry
                break
        digest: Dict[str, Any] = {
            "stage": stage,
            "status": (log or {}).get("status", "UNKNOWN"),
            "started_at": (log or {}).get("started_at"),
            "finished_at": (log or {}).get("finished_at"),
        }
        if stage == "RETRIEVE":
            digest["records_found"] = len(env.get("evidence") or [])
            digest["sources"] = sorted({
                (e.get("source") or "?") for e in (env.get("evidence") or [])})
            digest["sample_titles"] = [
                (e.get("title") or "")[:140]
                for e in (env.get("evidence") or [])[:5]]
        elif stage == "SYNTHESIZE":
            mm = env.get("mechanism_map") or {}
            digest["mechanism"] = mm.get("mechanism")
            digest["intervention"] = mm.get("intervention")
            digest["expected_effect"] = mm.get("expected_effect")
            digest["falsification_test"] = mm.get("falsification_test")
        elif stage == "MULTI_SOURCE_DISCOVERY":
            pa = env.get("prior_art") or []
            if isinstance(pa, dict):
                pa = pa.get("results") or []
            digest["prior_art_count"] = len(pa) if isinstance(pa, list) else 0
            digest["prior_art_titles"] = [
                (p.get("title") or "")[:140]
                for p in (pa[:5] if isinstance(pa, list) else [])]
        elif stage == "COLLISION":
            cr = env.get("collision_results")
            digest["collisions"] = []
            if isinstance(cr, dict):
                for universe, blk in list(cr.items())[:5]:
                    if isinstance(blk, dict):
                        digest["collisions"].append({
                            "universe": universe,
                            "verdict": blk.get("mapped_status")
                            or blk.get("legacy_status"),
                            "result_count": blk.get("result_count"),
                        })
            elif isinstance(cr, list):
                for c in cr[:5]:
                    digest["collisions"].append({
                        "verdict": (c.get("verdict")
                                    or c.get("collision_risk") if isinstance(c, dict) else str(c)[:80]),
                        "note": ((c.get("note") or c.get("reason") or "")
                                 [:200] if isinstance(c, dict) else ""),
                    })
        elif stage == "ATTACK":
            ar = env.get("attack_results") or {}
            if isinstance(ar, dict):
                digest["overall"] = ar.get("overall")
                digest["challenges"] = [
                    {"challenge": dim, "verdict": verdict,
                     "response": (ar.get("reason") or "")[:240]}
                    for dim, verdict in (ar.get("attacks") or {}).items()]
            elif isinstance(ar, list):
                digest["challenges"] = [
                    {"challenge": (a.get("challenge")
                                   or a.get("attack") or "")[:200],
                     "verdict": a.get("verdict") or a.get("result"),
                     "response": (a.get("response") or "")[:240]}
                    for a in ar[:6] if isinstance(a, dict)]
                verdicts = [a.get("verdict") or a.get("result")
                            for a in ar if isinstance(a, dict)]
                digest["overall"] = (
                    "FAIL" if any(v == "FAIL" for v in verdicts)
                    else "PASS" if verdicts else "UNKNOWN")
        elif stage == "CONTRADICTION":
            ct = env.get("contradictions") or {}
            items = ct.get("contradictions") if isinstance(ct, dict) else ct
            items = items if isinstance(items, list) else []
            digest["contradictions"] = [
                ((c.get("description") or str(c))
                 [:240] if isinstance(c, dict) else str(c)[:240])
                for c in items[:4]]
            digest["count"] = len(items)
        elif stage == "KILLER_EXPERIMENT":
            ke = env.get("killer_experiment") or {}
            digest["experiment"] = ke
        elif stage == "ADJUDICATION":
            ad = env.get("adjudication") or {}
            council = ad.get("council") or {}
            digest["verdict"] = council.get("verdict")
            digest["evidence_verified"] = (
                ad.get("evidence_verification") or {}).get("verified")
            digest["reason"] = (council.get("reason")
                                or (ad.get("evidence_verification")
                                    or {}).get("evidence_class") or "")[:300]
        elif stage == "CLASSIFY":
            digest["epistemic_state"] = env.get("epistemic_state")
        elif stage == "NEXT_BEST_ACTION":
            digest["action"] = env.get("next_best_action")
        elif stage == "RANK":
            rk = env.get("ranking") or {}
            digest["score"] = rk.get("score") or rk.get("total")
            digest["breakdown"] = rk.get("breakdown") or {}
        out.append(digest)
    return out


def package_info(run_dir: Path) -> Optional[Dict[str, Any]]:
    report = _read_json(run_dir / "PACKAGE_REPORT.json")
    if not report:
        return None
    zip_path = None
    dl = run_dir / "DOWNLOAD"
    if dl.exists():
        zips = sorted(dl.glob("*.zip"))
        if zips:
            zip_path = str(zips[0])
    return {
        "complete": report.get("complete"),
        "maturity": report.get("maturity"),
        "posture": report.get("posture"),
        "traceability_passed": report.get("traceability_passed"),
        "depth_contract_passed": report.get("depth_contract_passed"),
        "folder": report.get("folder"),
        "zip": zip_path,
        "zip_name": Path(zip_path).name if zip_path else None,
        "rendered": report.get("rendered"),
    }


def session_detail(session_id: str) -> Optional[Dict[str, Any]]:
    s = get_session(session_id)
    if not s:
        return None
    detail = dict(s)
    run_dir = Path(s["run_dir"]) if s.get("run_dir") else None
    if run_dir and run_dir.exists():
        detail["stages"] = stage_summaries(run_dir)
        detail["final_state"] = _read_json(run_dir / "final_state.json")
        manifest = _read_json(run_dir / "run_manifest.json") or {}
        detail["failed_stages"] = manifest.get("failed_stages") or {}
        if s.get("status") == "COMPLETE":
            detail["package"] = package_info(run_dir)
        inv = _read_json(run_dir / "INVENTION_SPECIFICATION.json")
        if inv:
            detail["invention_specification"] = inv
        eng = _read_json(run_dir / "ENGINEERING_SPECIFICATION.json")
        if eng:
            detail["engineering_specification"] = eng
        dex = _read_json(run_dir / "DECISIVE_EXPERIMENT.json")
        if dex:
            detail["decisive_experiment"] = dex
        surv = _read_json(run_dir / "SURVIVOR_SELECTION.json")
        if surv:
            detail["survivor_selection"] = surv
        cem = _read_json(run_dir / "cemetery_update.json")
        if cem:
            detail["cemetery_update"] = cem
    else:
        detail["stages"] = []
    detail.pop("evidence_pack", None)
    ep_path = STORE_DIR / f"evidence_{session_id}.json"
    ep = _read_json(ep_path)
    if ep:
        detail["evidence_pack"] = ep
    return detail


def save_evidence_pack(session_id: str, pack: Dict) -> None:
    _locked_write(STORE_DIR / f"evidence_{session_id}.json", pack)


# ---------------------------------------------------------------------------
# Seeding: six-domain benchmark as historical sessions (REAL, labeled)
# ---------------------------------------------------------------------------

SEED_CAMPAIGN = REPO_ROOT / "discovery_campaigns" / "TOSCANINI_6DOMAIN_2026-08-30"

DEMO_TITLES = {
    "medical": "Why do infusion pumps fail to detect downstream occlusion in time?",
    "energy": "How can EV traction-battery thermal runaway initiation be prevented?",
    "aerospace": "Why do aircraft lithium-battery installations suffer thermal events?",
    "materials": "Why do rails fracture in service under fatigue loading?",
    "industrial": "Why does rolling-stock equipment fail en route?",
    "electronics": "Why do consumer lithium-ion products catch fire?",
}


def seed_benchmark_sessions() -> int:
    """Ingest the real six-domain runs as history. Idempotent."""
    added = 0
    existing_ids = {s.get("problem_id") for s in list_sessions()}
    for domain in ("medical", "energy", "aerospace", "materials",
                   "industrial", "electronics"):
        rec = _read_json(SEED_CAMPAIGN / f"RUN_{domain}.json")
        if not rec:
            continue
        run_dir = REPO_ROOT / rec.get("run_dir", "_missing_")
        if rec.get("problem_id") in existing_ids:
            continue
        if not run_dir.exists():
            continue
        fs = _read_json(run_dir / "final_state.json") or {}
        session = {
            "session_id": f"ts_seed_{domain}",
            "title": DEMO_TITLES.get(domain, rec.get("problem_id")),
            "user_text": DEMO_TITLES.get(domain, ""),
            "domain_hint": domain,
            "origin": "six_domain_benchmark_2026-08-30",
            "status": "COMPLETE",
            "created_at": (fs.get("timestamp")
                           or "2026-08-30T12:00:00Z"),
            "run_dir": str(run_dir),
            "problem_id": rec.get("problem_id"),
            "final_status": fs.get("final_status"),
            "package": package_info(run_dir),
            "share_id": None,
            "error": None,
        }
        data = _locked_read(SESSIONS_PATH)
        data.setdefault("sessions", []).append(session)
        _locked_write(SESSIONS_PATH, data)
        added += 1
    return added


# ---------------------------------------------------------------------------
# Cemetery (engine's own MECHANISM_CEMETERY — summarized for the UI)
# ---------------------------------------------------------------------------

def cemetery_summary(limit: int = 50) -> Dict[str, Any]:
    path = REPO_ROOT / "MECHANISM_CEMETERY" / "CEMETERY.json"
    data = _read_json(path)
    if not data:
        return {"entries": [], "total": 0}
    entries = data.get("entries") or []
    out = []
    for e in entries[-limit:]:
        out.append({
            "entry_id": e.get("entry_id"),
            "territory_id": e.get("territory_id"),
            "mechanism_name": (e.get("mechanism_name") or "")[:220],
            "kill_reason": (e.get("kill_reason") or "")[:220],
            "what_was_proposed": (e.get("what_was_proposed") or "")[:300],
            "reusable_constraint": (e.get("reusable_constraint")
                                    or e.get("what_we_learned") or "")[:300],
            "killed_at": e.get("killed_at") or e.get("timestamp"),
        })
    return {"entries": list(reversed(out)), "total": len(entries)}

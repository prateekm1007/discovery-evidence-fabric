#!/usr/bin/env python3
"""R484 — the decisive loop-closure proof: the SAME geothermal problem
on the deployed LAYER JOIN (a500bfaa — the R483 join 1eb049c6 + the
R484 flock fd fix), measured for the auditor's one decisive question:

  does the IMPROVE kill-point SEE a conductor-surface death and
  answer CHILDREN_ADMITTED (a mutated child re-enters the gauntlet)
  or the honest NO_CHILD_ADMITTED?

The r483 driver REUSED BY IMPORT with three deltas:
  1. EXPECTED_IDENTITY -> this round's deployed tip a500bfaa.
  2. OUT / SESSION / SESSION_TRACKED -> the R484 paths (the session
     persists OUTSIDE the tracked tree — BS-021).
  3. THE HARVEST JOINS THE RUN DIR BY SESSION ID: the r483 driver
     picked the lexicographically-newest calcite dir, which is now
     attempt-3's RELEASED dir (_594319) — any future calcite run
     would harvest THE WRONG RUN (the wrong-run class their own
     records disclosed as the pre-correction parse). The R484
     harvest greps each durable run dir's run_manifest /
     EVENT_JOURNAL for THIS session id, and adds the join's own
     evidence legs (the ATTACK kill, the cemetery append, the
     release status).

Everything else — the case text (the decisive comparison: the
retrieval that surfaced the title-only record twice), the identity
gate, the owner-key session persistence, the terminal vocabulary,
the outcome typing (LOOP_CLOSED_ADMITTED / LOOP_CLOSED_REKILLED /
NO_KILL_EVIDENCE / IMPROVE_ABSENT) — is the r483 driver's,
unchanged.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import r483_live_proof as r483  # noqa: E402

DEPLOYED = "b0f3e91337460c27028ebbcedbbfd522999d2247"

r483.EXPECTED_IDENTITY = DEPLOYED
r483.OUT = REPO / "R484" / "LIVE_PROOF.json"
r483.SESSION = Path(
    "/home/z/my-project/scripts/r484_live_session.json")
r483.SESSION_TRACKED = REPO / "R484" / "LIVE_PROOF_SESSION.json"


def _show(path: str) -> str:
    p = subprocess.run(
        ["git", "show", f"origin/runtime-state-hf:{path}"],
        cwd=str(REPO), capture_output=True, text=True, timeout=60)
    return p.stdout if p.returncode == 0 else ""


def _durable_harvest_by_session(session_id: str) -> Dict[str, Any]:
    """The R484 harvest: the run dir JOINED BY SESSION ID + the
    join's own evidence legs. Best-effort and honest — a lagging
    branch returns harvested:False with the reason recorded."""
    out: Dict[str, Any] = {}
    try:
        subprocess.run(["git", "fetch", "origin", "runtime-state-hf"],
                       cwd=str(REPO), capture_output=True, timeout=120)
        tree = subprocess.run(
            ["git", "ls-tree", "--name-only",
             "origin/runtime-state-hf:runs"],
            cwd=str(REPO), capture_output=True, text=True,
            timeout=60).stdout.split()
        rdir = None
        for t in tree:
            blob = (_show(f"runs/{t}/run_manifest.json")
                    or _show(f"runs/{t}/EVENT_JOURNAL.jsonl"))
            if session_id in blob:
                rdir = t
                break
        if not rdir:
            return {"harvested": False,
                    "reason": "no durable run dir carries this "
                              "session id yet"}
        out["durable_run_dir"] = rdir

        for env in ("SYNTHESIZE", "VERIFY", "IMPROVE", "ATTACK"):
            txt = _show(f"runs/{rdir}/envelope_{env}.json")
            if not txt:
                continue
            try:
                d = json.loads(txt)
            except Exception:  # noqa: BLE001
                continue
            if env == "SYNTHESIZE":
                rc = ((d.get("mechanism_map") or {}).get("raw_candidate")
                      or {})
                se = rc.get("source_evidence") or {}
                out["synthesis_route"] = {
                    "provider": rc.get("provider"),
                    "model": rc.get("model"),
                    "source_id": se.get("source_id"),
                    "source_span_chars": len(se.get("source_span") or ""),
                    "span_corrective_retry": rc.get(
                        "span_corrective_retry"),
                    "synthesis_rotation": rc.get("synthesis_rotation"),
                }
            elif env == "VERIFY":
                ev = ((d.get("adjudication") or {})
                      .get("evidence_verification") or {})
                out["verify"] = {
                    "verified": ev.get("verified"),
                    "issues": ev.get("issues"),
                    "span_extraction": ev.get("span_extraction"),
                    "verifier_assist": ev.get("verifier_assist"),
                }
            elif env == "IMPROVE":
                sl = d.get("stage_log") or []
                out["improve_entries"] = [
                    {k: e.get(k) for k in ("stage", "status",
                                           "result_meta")}
                    for e in sl if e.get("stage") == "IMPROVE"]
            elif env == "ATTACK":
                # the join's INPUT: the conductor-surface kill
                ar = d.get("attack_results") or {}
                out["attack"] = {
                    "overall": ar.get("overall"),
                    "killed_count": ar.get("killed_count"),
                    "reason": str(ar.get("reason") or "")[:300],
                }

        # the join's OUTPUT legs: the cemetery append + the release
        cem = _show(f"runs/{rdir}/cemetery_update.json")
        if cem:
            try:
                cd = json.loads(cem)
                app = cd.get("appended") or {}
                out["cemetery"] = {
                    "appended_entry_id": app.get("entry_id"),
                    "kill_reason": str(app.get("kill_reason")
                                       or "")[:300],
                    "total_entries": cd.get("total_entries"),
                }
            except Exception:  # noqa: BLE001
                out["cemetery"] = {"raw_len": len(cem)}
        rel = _show(f"runs/{rdir}/DISCOVERY_RELEASE.json")
        if rel:
            try:
                rd = json.loads(rel)
                out["release"] = {
                    "status": rd.get("status"),
                    "invention_id": rd.get("invention_id"),
                }
            except Exception:  # noqa: BLE001
                out["release"] = {"raw_len": len(rel)}
        out["harvested"] = True
    except Exception as exc:  # noqa: BLE001 — honest harvest failure
        out["harvested"] = False
        out["reason"] = f"{type(exc).__name__}: {exc}"
    return out


# the delta wiring: main() resolves these as module globals at call
# time — the harvest is replaced wholesale (the session-joined pick)
r483._durable_harvest = _durable_harvest_by_session


if __name__ == "__main__":
    sys.exit(r483.main())

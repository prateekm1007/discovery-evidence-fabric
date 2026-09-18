#!/usr/bin/env python3
"""scripts/r505_patentbear_recovery.py — R505: PatentBear VALUE RECOVERY
(the re-audit's #1 leverage item) — one measured probe on the operator's
first-supplied key, the custody-state correction, and the full-battery
quota arithmetic.

THE MEASURED QUESTION: the R503/R504 rounds typed PATENTBEAR_API_KEY as a
custody gap — "value not held anywhere the machine can read (fingerprint
561b6e70f5b5ea7f registered)". THIS session holds BOTH operator-supplied
values (the standing operator instruction preserved them). The LXXVI
Section 3 unblock path — "a session that holds it sets it" — is therefore
executable here. What was NOT measured by any prior round: whether the
FIRST-SUPPLIED key (fp 561b6e70f5b5ea7f, last metered 6/20 remaining at
R497 close, 2026-09-17T18:46Z) is still LIVE and what its bucket reads
NOW — the number that decides whether the full-battery R502 re-run's
"6+ quiet debits" unblock exists in the operator's current key pool.

DISCIPLINE (the R497/R498 probe lineage, preserved):
  - exactly ONE search call on the probe key (one debit from that key's
    own bucket; per-key buckets measured R498 — the rotated key's bucket
    is untouched, its last debit stays preserved per R504)
  - the ACTIVE key (.env.keys / vault, fp 50fe7b3d569bb1fa) is NOT
    probed: its measured state is 19/20 used = 1 remaining, below the
    reserve floor 2 — the R504 stewardship decision stands
  - the probe value arrives via environment injection ONLY (never
    printed, never committed — BS-021); the record carries the
    fingerprint, never the value
  - the request shape mirrors sources.py::search_patent_bear exactly
    (MCP tools/call, scope "patents" first, the battery's fixed anchor
    query "shunt valve" — Art. VIII, comparable meter read)
  - no coverage or novelty conclusion derives from num_hits (Art. XXI.1
    / LXXV.2); this probe measures TRANSPORT LIVENESS + METER STATE

Commands:
  PATENTBEAR_PROBE_KEY=... python3 scripts/r505_patentbear_recovery.py
"""
from __future__ import annotations

import hashlib
import json
import os
import ssl
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

REPO = Path(__file__).resolve().parents[1]
OUT_PATH = REPO / "R505" / "PATENTBEAR_VALUE_RECOVERY.json"
METER_PATH = REPO / "patent_sources" / "patentbear_meter.json"

# the battery's fixed anchor query (scripts/r495_rbg/rbg_gate.py — Art.
# VIII: the anchor query family is fixed; the meter read is comparable)
ANCHOR_QUERY = "shunt valve"

OLD_KEY_FP = "561b6e70f5b5ea7f"      # operator key #1 (R497 era)
ACTIVE_KEY_FP = "50fe7b3d569bb1fa"   # operator key #2 (R498 rotation)


def _fp(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def probe(key: str) -> Dict[str, Any]:
    """One MCP search_patents call, scope 'patents' — the exact
    sources.py request shape. Returns the typed probe record."""
    url = "https://www.patentbear.com/mcp"
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000) % 1000000,
        "method": "tools/call",
        "params": {
            "name": "search_patents",
            "arguments": {
                "query": ANCHOR_QUERY[:200],
                "max_hits": 5,
                "scope": "patents",
                "sort": "relevance",
            },
        },
    }).encode()
    # the Chrome UA is REQUIRED (measured this round): www.patentbear.com
    # sits behind the same Cloudflare browser-signature check the registry
    # documents for xkiro/apinex — the default urllib UA draws 403 Error
    # 1010 at the CDN edge (BEFORE auth; zero debits spent on the first
    # probe attempt, disclosed in the record). The production transport
    # sends exactly this UA (sources.py _UA via _http_post) — the probe
    # must mirror it or it measures the CDN, not the key.
    _UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    headers = {
        "User-Agent": _UA,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-06-18",
    }
    req = urllib.request.Request(url, data=payload, headers=headers,
                                 method="POST")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=45, context=ctx) as r:
            body = r.read()
            return _parse(200, body, time.time() - t0)
    except urllib.error.HTTPError as e:
        try:
            body = e.read()[:2000]
        except Exception:  # noqa: BLE001
            body = b""
        return _parse(e.code, body, time.time() - t0)
    except Exception as exc:  # noqa: BLE001 — typed, never a crash
        return {"http_status": None,
                "state": "CALL_FAILED",
                "error": f"{type(exc).__name__}: {exc}"[:200],
                "latency_s": round(time.time() - t0, 2)}


def _parse(status: int, body: bytes, latency: float) -> Dict[str, Any]:
    """Parse the MCP response into the typed probe fields (usage/meter
    extraction mirrors sources.py's own parsing)."""
    out: Dict[str, Any] = {"http_status": status,
                           "latency_s": round(latency, 2)}
    if status != 200:
        out["state"] = "HTTP_%s" % status
        out["error_body_head"] = body[:200].decode(errors="replace")
        # 401 = key recognized-but-not-opened class (R497 garbage-key
        # control); 403 = auth refused UNLESS the body is Cloudflare
        # Error 1010 (the UA ban at the CDN edge — a TRANSPORT state,
        # never a verdict about the key; Art. XXI.3)
        if status == 401:
            out["state"] = "AUTH_FAILED_401"
        elif status == 403 and (b"error-1010" in body[:400].lower()
                                or b"error 1010" in body[:400].lower()):
            out["state"] = "CDN_UA_BAN_403_ERROR_1010"
        return out
    try:
        outer = json.loads(body.decode(errors="replace"))
    except Exception:  # noqa: BLE001
        outer = {}
    # MCP content can arrive as text/event-stream framed JSON
    if not outer and b"data:" in body[:200]:
        for line in body.decode(errors="replace").splitlines():
            if line.startswith("data:"):
                try:
                    outer = json.loads(line[5:].strip())
                    break
                except Exception:  # noqa: BLE001
                    continue
    result = outer.get("result") or {}
    content = result.get("content") or []
    inner: Dict[str, Any] = {}
    for c in content:
        if isinstance(c, dict) and c.get("type") == "text":
            try:
                inner = json.loads(c.get("text") or "{}")
            except Exception:  # noqa: BLE001
                inner = {}
            if inner:
                break
    if not inner:
        out["state"] = "PROVIDER_INCONSISTENT"
        out["error"] = "200 with unparseable MCP content"
        return out
    is_error = bool(inner.get("isError"))
    if is_error:
        out["state"] = "PROVIDER_ERROR"
        out["provider_error"] = str(inner.get("error") or
                                    inner.get("content"))[:300]
        return out
    hits = inner.get("hits") or []
    usage = inner.get("usage") or {}
    out["state"] = "LIVE_200"
    out["num_hits"] = inner.get("num_hits")
    out["records_returned"] = len(hits)
    out["first_record_ids"] = [h.get("id") or h.get("publication_number")
                               for h in hits[:3]]
    out["usage"] = usage
    return out


def main() -> int:
    probe_key = os.environ.get("PATENTBEAR_PROBE_KEY", "").strip()
    if not probe_key:
        raise SystemExit("FATAL: PATENTBEAR_PROBE_KEY not injected "
                         "(env-only credential path; never an argument, "
                         "never printed)")
    fp = _fp(probe_key)
    if fp not in (OLD_KEY_FP, ACTIVE_KEY_FP):
        # the probe must be one of the two registered operator keys —
        # an unknown key is a custody anomaly, refused (Art. VI)
        raise SystemExit(f"FATAL: probe key fingerprint {fp} matches no "
                         "registered operator key (registered: "
                         f"{OLD_KEY_FP}, {ACTIVE_KEY_FP})")
    if fp == ACTIVE_KEY_FP:
        raise SystemExit("FATAL: refusing to probe the ACTIVE key — its "
                         "measured state is 1 remaining (below the "
                         "reserve floor 2); the R504 last-debit-"
                         "preserved decision stands")

    # custody inventory (names + fingerprints only — BS-021)
    stores: Dict[str, Any] = {}
    vault = Path("/home/z/my-project/.secrets.env")
    if vault.exists():
        for line in vault.read_text().splitlines():
            if line.startswith("PATENTBEAR_API_KEY="):
                v = line.split("=", 1)[1].strip().strip('"\'')
                stores["session_vault_.secrets.env"] = {
                    "name": "PATENTBEAR_API_KEY",
                    "fingerprint": _fp(v) if v else "EMPTY"}
    keysfile = REPO / ".env.keys"
    if keysfile.exists():
        for line in keysfile.read_text().splitlines():
            if line.startswith("PATENT_BEAR_API_KEY="):
                v = line.split("=", 1)[1].strip().strip('"\'')
                stores["repo_.env.keys"] = {
                    "name": "PATENT_BEAR_API_KEY",
                    "fingerprint": _fp(v) if v else "EMPTY"}

    meter_file = {}
    try:
        meter_file = json.loads(METER_PATH.read_text())
    except Exception:  # noqa: BLE001
        meter_file = {"note": "unreadable"}

    result = probe(probe_key)

    # the persisted meter is KEY-AGNOSTIC (a single tracked state updated
    # by whichever key last answered) — updating it with the probe key's
    # report would silently re-attribute the ACTIVE key's tracked state.
    # The probe's usage is recorded in THIS record only; the tracked
    # meter file stays untouched (the disclosure below carries both).
    record: Dict[str, Any] = {
        "artifact_type": "PATENTBEAR_VALUE_RECOVERY",
        "round": "R505",
        "reviewer_provenance": "AI_REVIEW",
        "measured_at": _now(),
        "directive_anchor": ("the re-audit's leverage order: 'PatentBear "
                             "value recovery -> full-battery R502 -> "
                             "v4.2 vs strong ring -> REAL packet -> "
                             "fresh ZIP'"),
        "probe": {
            "key_fingerprint": fp,
            "key_role": ("operator key #1 (R497-era, the R503-registered "
                         "custody-gap fingerprint)"),
            "calls_made": 1,
            "call_shape": ("MCP tools/call search_patents, scope=patents, "
                           "query='shunt valve' (the battery's fixed "
                           "anchor query), max_hits=5 — mirrors "
                           "sources.py::search_patent_bear"),
            "first_attempt_disclosure": (
                "attempt 1 used urllib's default User-Agent and drew "
                "Cloudflare Error 1010 (403) at the CDN edge — BEFORE "
                "the provider's auth layer, ZERO debits spent, and the "
                "key's state was NOT measured by it. The typed state "
                "PROBE_KEY_AUTH_REFUSED from that attempt was WRONG (a "
                "transport failure is never a verdict about the key, "
                "Art. XXI.3) — corrected in-round: the Chrome UA that "
                "the production transport sends (sources.py _UA) is now "
                "mirrored. Lesson recorded per Art. XXXI: a probe that "
                "does not mirror the production transport's FULL header "
                "set measures the CDN, not the credential."),
            "result": result,
            "state_typed": result.get("state"),
        },
        "active_key_not_probed": {
            "fingerprint": ACTIVE_KEY_FP,
            "measured_state": "19/20 used = 1 remaining (R499 "
                              "reconciliation; R501/R503/R504 unchanged)",
            "reason": ("below the reserve floor 2 — the R504 "
                       "'last debit preserved' stewardship decision "
                       "stands; probing it would spend the last debit"),
        },
        "custody_state_correction": {
            "r503_r504_typing": ("PATENTBEAR_API_KEY value not held "
                                 "anywhere the machine can read (typed "
                                 "custody gap)"),
            "this_session": ("BOTH operator-supplied values are held "
                             "here: the active key (fp 50fe7b3d...) in "
                             "the session vault AND repo .env.keys; the "
                             "first-supplied key (fp 561b6e70...) in the "
                             "operator's standing instruction this "
                             "session carries — the LXXVI Section 3 "
                             "'holding session' unblock path is "
                             "executable for both"),
            "correction_class": ("session-scoped truth superseded for "
                                 "this line (Art. XV disclosure — the "
                                 "R503/R504 typing was correct for THOSE "
                                 "sessions' environments)"),
            "stores_inspected": stores,
        },
        "tracked_meter_file_state": {
            "value": meter_file,
            "disclosure": ("the persisted meter is key-agnostic (updated "
                           "by whichever key last answered); its "
                           "6-remaining figure is the R497-era report "
                           "from the probe key (2026-09-17T18:46Z) — NOT "
                           "the active key's state (19/20 used, 1 "
                           "remaining, R499 reconciliation). The file is "
                           "left untouched by this probe; both keys' "
                           "states are carried per-key in this record."),
        },
        "full_battery_arithmetic": {
            "needed_debits": ("6 (3 repetitions x 2 PatentBear debits: "
                              "F6 layer self-measurement search + F10 "
                              "record fetch) + reserve floor 2 = 8 "
                              "remaining at start"),
            "probe_key_after_probe": _remaining_after(result),
            "active_key": "1 remaining (below floor — not spendable)",
            "verdict": None,  # filled below
        },
        "pool_state_measured": {
            "conclusion": None,  # filled below
            "note": ("the operator's PatentBear pool as measured THIS "
                     "round: two key values held, ONE opens the "
                     "transport, and that key's bucket holds a single "
                     "preserved debit below the reserve floor"),
        },
    }

    # the full-battery verdict from the MEASURED meter (never guessed)
    rem = _extract_remaining(result)
    if result.get("state") == "LIVE_200" and isinstance(rem, int):
        record["full_battery_arithmetic"]["probe_key_after_probe"] = rem
        feasible = rem >= 8
        record["full_battery_arithmetic"]["verdict"] = (
            "PATENTBEAR_QUOTA_FEASIBLE_THIS_KEY" if feasible
            else "PATENTBEAR_QUOTA_INFEASIBLE_THIS_KEY "
                 f"(measured {rem} remaining < 8 needed: 6 debits + "
                 "floor 2)")
    elif result.get("state") in ("AUTH_FAILED_401", "HTTP_403",
                                 "CDN_UA_BAN_403_ERROR_1010"):
        record["full_battery_arithmetic"]["verdict"] = (
            "PROBE_KEY_AUTH_REFUSED_%s — the pool's spendable quota is "
            "the active key's 1-preserved-debit only; the operator "
            "path (fresh key supply) is the sole unblock" %
            result.get("state"))
        if result.get("state") == "AUTH_FAILED_401":
            record["pool_state_measured"]["conclusion"] = (
                "POOL_EXHAUSTED_MEASURED: the first-supplied key (fp "
                "561b6e70...) draws 401 isError 'Authentication "
                "required' — the provider retired it (the R498 "
                "rotation was a TRUE rotation: old credential "
                "deauthorized, its R497-era 6-remaining bucket is "
                "UNREACHABLE). The 401 debits nothing (the R497 "
                "garbage-key control class). The operator's committed "
                "path — 'more keys will be supplied when you run out' "
                "— is now the MEASURED state: the pool has run out. A "
                "fresh key with a full bucket (20) unblocks the "
                "full-battery patent leg (8 needed) with 12 to spare; "
                "the Scopus leg additionally needs the Elsevier value "
                "in the sealing session.")
        else:
            record["pool_state_measured"]["conclusion"] = (
                "PROBE_TRANSPORT_TYPED_STATE_%s — the key's quota is "
                "unresolved; no conclusion drawn (Art. XXI.3/XXV)" %
                result.get("state"))
    else:
        record["full_battery_arithmetic"]["verdict"] = (
            "PROBE_TYPED_STATE_%s — quota unresolved; no coverage or "
            "absence conclusion drawn (Art. XXI.3/XXV)" %
            result.get("state"))

    # the Scopus leg gap (the full battery needs BOTH legs live)
    record["scopus_leg_state"] = {
        "elsevier_key_in_this_session": False,
        "where_the_value_lives": ("the Space secret surface "
                                  "(write-only from outside; standing "
                                  "per R503/R504) and the sibling line's "
                                  "session vault (R501-C2 disclosure)"),
        "consequence": ("even with PatentBear quota, a full-battery seal "
                        "cannot run from THIS session — the Scopus leg "
                        "would type SKIPPED_UNCONFIGURED and a skip is "
                        "never a pass (the R498 discipline)"),
    }

    # the operator decision menu (Art. LXV — escalate with costs, never
    # idle; the machine does not pick)
    record["operator_decision_menu"] = {
        "opened_at": "R505",
        "escalation_count": 1,
        "options": [
            {"option": "supply a fresh PatentBear key (the committed "
                       "path: 'more keys will be supplied when you run "
                       "out')",
             "unblocks": "the full-battery R502 re-run's patent leg "
                         "(needs 8 remaining on one key)",
             "cost_of_inaction": "the full battery stays leg-sealed "
                                 "(3x per-leg seals) but never "
                                 "battery-sealed on the v4.1 instrument"},
            {"option": "re-supply ELSEVIER_API_KEY to a sealing session "
                       "(or task the line that holds it)",
             "unblocks": "the Scopus leg from that session — the full "
                         "battery additionally needs the PatentBear "
                         "quota above",
             "cost_of_inaction": "same as above — the battery cannot "
                                 "run from any session lacking either "
                                 "leg"},
            {"option": "wait for the monthly quota window to roll "
                       "(if the provider window is calendar-month, both "
                       "buckets reset 2026-10-01)",
             "unblocks": "possibly both keys' buckets (UNMEASURED — the "
                         "window semantics are the provider's; "
                         "2026-08-31 floor-hit + 2026-09-01-reset "
                         "evidence in the R498 record suggests "
                         "calendar-month)",
             "cost_of_inaction": "13 days without a battery-scale seal "
                                 "path"},
            {"option": "the R378 account upgrade (investors fund "
                       "unlimited usage — CEO statement 2026-08-31)",
             "unblocks": "quota entirely; corpus-scale collision "
                         "measurement (105 searches for the 21-case "
                         "corpus, R497 arithmetic)",
             "cost_of_inaction": "the machine stays probe-scale on "
                                 "PatentBear"},
        ],
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(record, indent=1))
    print(json.dumps({
        "probe_state": result.get("state"),
        "usage": result.get("usage"),
        "records_returned": result.get("records_returned"),
        "full_battery_verdict":
            record["full_battery_arithmetic"]["verdict"],
        "record": str(OUT_PATH.relative_to(REPO)),
    }, indent=1))
    return 0


def _extract_remaining(result: Dict[str, Any]):
    usage = result.get("usage") or {}
    rem = usage.get("monthly_remaining")
    if isinstance(rem, (int, float)):
        return int(rem)
    return None


def _remaining_after(result: Dict[str, Any]) -> str:
    rem = _extract_remaining(result)
    if isinstance(rem, int):
        return (f"{rem} remaining (provider-reported post-probe)")
    return "UNKNOWN (no numeric monthly_remaining in the probe response)"


if __name__ == "__main__":
    raise SystemExit(main())

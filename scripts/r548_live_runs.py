"""R548 Round C live behavior proof (revised): submit 2 fresh terminal
runs on the deployed Space, ANSWER the one-question clarification pause
(the deterministic clarify gate, clarification.py — zero LLM, asks one
information-efficient question), poll to terminal, and verify the
served finished flag equals the committed source's recompute (BS-042).

Handles are persisted IMMEDIATELY after submit (a killed shell must
never orphan the owner keys again). Each run's full terminal detail is
recorded to R548/ the moment it lands, before the next run starts.
"""
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(r"C:\Users\Administrator\Documents\Default Project\discovery-evidence-fabric")
OUT_DIR = REPO / "R548"
HANDLES = OUT_DIR / "r548_live_handles.json"
BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
TERMINAL = ("COMPLETE", "INTERRUPTED", "ERROR_RUN", "ERROR_TRANSPORT",
            "ERROR_STUCK", "RUN_BLOCKED_TRANSPORT",
            "RUN_BLOCKED_CAPABILITY", "ERROR_CANCELED", "ERROR_BUILD",
            "ERROR_SPAWN")

CASES = [
    {
        "idx": 1,
        "problem": ("2015 Toyota Camry: the battery warning light flashes "
                    "intermittently only when the engine is idle and the "
                    "temperature is below 0C, then clears after driving. "
                    "What mechanism would cause a cold-idle-only "
                    "battery-sensing fault, and what single test settles "
                    "it?"),
        "answer": ("Use exactly what is stated and proceed: 2015 Toyota "
                   "Camry; intermittent battery-warning-light fault that "
                   "occurs only at idle and below 0C ambient, then "
                   "clears after driving; the question is the underlying "
                   "mechanism plus the single settling test. No other "
                   "vehicle, sensor, or configuration is in scope."),
    },
    {
        "idx": 2,
        "problem": ("Why does a 3D printer skip a layer when printing "
                    "polycarbonate above 35C ambient, and what is the "
                    "single measurement that settles it?"),
        "answer": ("Use exactly what is stated and proceed: a 3D printer "
                   "printing polycarbonate above 35C ambient temperature "
                   "skips a layer; the question is the underlying "
                   "mechanism plus the single settling measurement. No "
                   "other printer, material, or setup is in scope."),
    },
]


def post(path, payload, owner, timeout=60):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application", "X-Tosca-Owner": owner},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def get(path, owner):
    req = urllib.request.Request(BASE + path,
                                 headers={"X-Tosca-Owner": owner})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def submit(c):
    # a fresh random owner per call — use it for the whole lifetime of
    # this session
    key = get("/api/sessions", "").get("owner_key") or ""
    for attempt in range(20):
        try:
            resp = post("/api/discoveries", {"text": c["problem"]}, key)
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:160]
            print(f"  submit attempt {attempt}: {e.code} {body}",
                  flush=True)
            if e.code in (503, 429):
                time.sleep(20)
                continue
            raise
    sid = resp.get("session_id") or (resp.get("session") or {}).get(
        "session_id")
    owner = resp.get("owner_key") or key
    return sid, owner


def run_one(c, resume=None):
    idx = c["idx"]
    print(f"=== run {idx} ===", flush=True)
    if resume:
        sid, owner = resume["session_id"], resume["owner_key"]
        print(f"  resuming {sid}", flush=True)
    else:
        sid, owner = submit(c)
        if not sid:
            print("  SUBMIT FAILED - no session_id", flush=True)
            return None
        # persist handles IMMEDIATELY (a kill must not orphan them)
        handles = json.loads(HANDLES.read_text(encoding="utf-8")) \
            if HANDLES.exists() else {"cases": {}}
        handles["cases"][str(idx)] = {
            "session_id": sid, "owner_key": owner,
            "problem": c["problem"], "answer": c["answer"],
            "submitted_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                               time.gmtime())}
        HANDLES.write_text(json.dumps(handles, indent=1),
                           encoding="utf-8")
        print(f"  submitted {sid} (owner persisted)", flush=True)

    detail = None
    answered = 0
    deadline = time.time() + 1800  # 30 min to terminal
    while time.time() < deadline:
        time.sleep(45)
        try:
            detail = get(f"/api/sessions/{sid}", owner)
        except Exception as e:
            print(f"  poll: {type(e).__name__} {str(e)[:90]}", flush=True)
            continue
        st = detail.get("status") or ""
        if st == "AWAITING_CLARIFICATION" and answered < 2:
            q = detail.get("clarification") or {}
            ans = post(f"/api/run/{sid}/answer",
                       {"answer": c["answer"],
                        "field": q.get("field") or ""}, owner)
            answered += 1
            print(f"  answered clarification {answered} "
                  f"(field={q.get('field')!r}): "
                  f"{json.dumps(ans)[:200]}", flush=True)
            continue
        if st in TERMINAL:
            break
    out = {
        "idx": idx,
        "sid": sid,
        "owner_key": owner,
        "terminal": bool(detail and detail.get("status") in TERMINAL),
        "answers_sent": answered,
        "status": (detail or {}).get("status"),
        "final_status": (detail or {}).get("final_status"),
        "user_state": ((detail or {}).get("user_state_view") or {})
                       .get("user_state"),
        "recorded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                         time.gmtime())}
    (OUT_DIR / f"r548_live_run{idx}.json").write_text(
        json.dumps({"verify": out, "detail": detail}, indent=1),
        encoding="utf-8")
    print(f"  RUN {idx}: terminal={out['terminal']} "
          f"status={out['status']}/{out['final_status']} "
          f"user_state={out['user_state']} -> "
          f"R548/r548_live_run{idx}.json", flush=True)
    return out


def main(only=None):
    cases = [c for c in CASES if only in (None, c["idx"])]
    handles = json.loads(HANDLES.read_text(encoding="utf-8")) \
        if HANDLES.exists() else {"cases": {}}
    results = []
    for c in cases:
        existing = (OUT_DIR / f"r548_live_run{c['idx']}.json")
        h = handles["cases"].get(str(c["idx"]))
        if existing.exists() and h and h.get("session_id"):
            out = json.loads(existing.read_text(encoding="utf-8"))[
                "verify"]
            if out.get("terminal"):
                print(f"run {c['idx']} already recorded terminal "
                      f"({out['status']}/{out['final_status']})",
                      flush=True)
                results.append(out)
                continue
        results.append(run_one(c, resume=h))
    summary = {"runs": [r for r in results if r],
               "all_terminal": all(r and r.get("terminal")
                                   for r in results if r),
               "recorded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                 time.gmtime())}
    (OUT_DIR / "r548_live_runs_summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    print("SUMMARY all_terminal =", summary["all_terminal"], flush=True)


if __name__ == "__main__":
    import sys
    only = int(sys.argv[1]) if len(sys.argv) > 1 else None
    main(only)

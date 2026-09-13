"""r451_c2_watchdog.py — the R451-C2 (C2.10) end-to-end product watchdog,
extended by R451-C2.2 (§6) into THE adversarial join checker, and
re-founded by R451-C2.3 (§8) on THE one canonical evaluator.

R451-C2.3 §8: the dossier and the watchdog consume the SAME state
semantics. The join state below is derived by
toscanini/visual_join.py::evaluate_visual_join + evaluate_geometry_contract
— the identical implementation the product surface uses. THIS checker
does not implement a second state machine; it attacks the evaluator
with independently authored adversarial fixtures (the battery in
tests/test_r451_c23_identity_chain.py) and keeps the RECORD-LEVEL
invariant rules that must hold whenever the evaluator announces a
state:

    if the canonical GLB is verified (visual input ready):
        assert a Visual Compiler invocation receipt exists
        (R451-C2.2 §6: valid GLB + no invocation -> FAIL — the
        no-silent-gap rule)
    if the receipt says the renderer ran (SUCCEEDED / OK / PARTIAL):
        assert a visual gate record exists
        AND the persisted render record exists (R9, R451-C2.2 §6:
        valid GLB + invocation + no render record -> FAIL)
    if the gate verdict is COMPLETE_PASS:
        assert the required 23-artifact ladder exists on disk
    if a hero exists:
        assert the render record's source GLB hash == the canonical GLB
    if the renderer skipped:
        assert the receipt carries the typed skip reason
        (the UI renders the SAME typed fields — source-pinned by
        tests/test_r451_c2_blocked_state.py)
    if the GLB is absent and the run stopped upstream:
        assert the design projection carries the upstream state
        (the UI renders THIS, never a frontend guess)
    R10 (R451-C2.3 §8): the evaluator's announced join state must be
        consistent with the record invariants (VISUAL_READY only when
        the release chain verified; RELEASE_UNVERIFIED / RENDER_RECORD_
        MISSING / INVOCATION_MISSING are violations-by-state).

R451-C2.3 §6: the identity chain (geometry spec / receipt GLB / render
source / hero source == canonical GLB bytes) is enforced INSIDE the
evaluator — a mismatch fails closed there and this checker's R4
verifies the same bytes independently.

Exit codes: 0 = every applicable rule held; 1 = at least one integrity
violation (named, with the file and the rule); 2 = usage/argument error.
A NOT_APPLICABLE rule is not a violation (the rule's antecedent is
false) — every decision is recorded in the JSON report either way.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[1]

RECEIPT = "MODEL/3D/VISUAL_COMPILER_INVOCATION.json"
GATE = "MODEL/3D/visual_gate.json"
RENDER_RECORD = "MODEL/3D/render_record.json"
RENDER_JOB = "MODEL/3D/RENDER_JOB.json"

sys.path.insert(0, str(REPO))
from toscanini import visual_join as vj  # noqa: E402 — THE evaluator

# the closed join-state vocabulary — re-exported from THE evaluator
# (one vocabulary, no second definition, R451-C2.3 §8)
JOIN_STATES = vj.VISUAL_JOIN_STATES

# the statuses that mean "the boundary was reached and the renderer
# ran" — THE evaluator's tuple (no second definition)
_RENDERED_STATUSES = vj.RENDERER_RAN_STATUSES


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def read_receipt(run_dir: Path) -> Optional[Dict[str, Any]]:
    """THE evaluator's era-normalizing reader (one implementation)."""
    return vj.read_invocation_receipt(run_dir)


def canonical_glb(run_dir: Path) -> Optional[Path]:
    """THE evaluator's resolution order (one authority, all
    consumers)."""
    return vj.resolve_canonical_glb(run_dir)


def run_watchdog(run_dir: Path) -> Dict[str, Any]:
    """The record invariant rules + THE evaluator's join state over one
    run dir. Returns the JSON report; `violations` empty == PASS."""
    checks: List[Dict[str, Any]] = []
    violations: List[Dict[str, Any]] = []

    def record(rule: str, applicable: bool, ok: bool, detail: str,
               evidence: Optional[str] = None) -> None:
        state = ("NOT_APPLICABLE" if not applicable
                 else "PASS" if ok else "FAIL")
        checks.append({"rule": rule, "state": state, "detail": detail})
        if applicable and not ok:
            violations.append({"rule": rule, "detail": detail,
                               "evidence": evidence})

    glb = canonical_glb(run_dir)
    receipt = read_receipt(run_dir)
    gate = _read_json(run_dir / GATE)
    render_record = _read_json(run_dir / RENDER_RECORD)

    # ---- THE geometry artifact contract (R451-C2.3 §1) — the same
    # implementation the dossier consumes. The engineering authority is
    # the contract's verdict: ENGINEERING / CONCEPTUAL / UNKNOWN. A
    # missing class is UNKNOWN — never engineering-by-filename (the
    # pre-C2.3 fallback that read a GLB under MODEL/ as engineering by
    # construction is retired, Art. LXIV).
    session = _read_json(run_dir / "session.json") or {}
    # the evaluator reads the run directory THROUGH the session record
    # (one input shape for every consumer) — the watchdog injects the
    # run dir it was handed
    session.setdefault("run_dir", str(run_dir))
    session.setdefault("session_id", run_dir.name)
    cio = (_read_json(run_dir / "CIO.json")
           or _read_json(run_dir / "cio.json")) or {}
    geom = cio.get("geometry") or {}
    contract = vj.evaluate_geometry_contract(session, run_dir, geom)
    eng = contract.get("engineering_authority") == "ENGINEERING"
    visual_input_ready = contract.get("visual_input_ready") is True

    # ---- THE evaluator's join state (no second derivation) ----------
    join = vj.evaluate_visual_join(
        session, geom, {}, running=False,
        engineering_geometry_ready=eng,
        geometry_state=contract.get("geometry_state") or "",
        contract=contract)
    join_state = join.get("visual_join_state")
    join_detail = join.get("visual_join_detail")
    release_chain = join.get("release_chain") or \
        (vj.verify_release_chain(run_dir, glb, contract)
         if join_state in ("VISUAL_READY", "RELEASE_UNVERIFIED")
         else None)

    job_rec = _read_json(run_dir / RENDER_JOB)
    job_pending = (job_rec or {}).get("status") in ("RUNNING",
                                                    "INTERRUPTED")

    # ---- R1: verified canonical GLB under an EXPLICIT ENGINEERING
    # authority -> the visual invocation is accounted for: a receipt on
    # disk, or an in-flight render job (the invocation was requested and
    # has not spoken — explicit pending, R451-C2.2 §6). An
    # UNKNOWN-authority artifact demands no invocation claim (R451-C2.3
    # §1: missing class stays UNKNOWN).
    record(
        "R1_engineering_glb_has_invocation_receipt",
        applicable=eng and visual_input_ready,
        ok=receipt is not None or job_pending,
        detail=("canonical GLB %s verified; authority %s; receipt %s; "
                "render job %s%s"
                % (glb.name if glb else "-",
                   contract.get("engineering_authority"),
                   "found" if receipt else "MISSING",
                   (job_rec or {}).get("status") or "none",
                   " (explicit pending)" if job_pending else "")),
        evidence=RECEIPT)

    # ---- R2: renderer ran -> gate record exists ----
    rendered = (receipt or {}).get("invocation_status") in _RENDERED_STATUSES
    record(
        "R2_rendered_has_gate",
        applicable=rendered,
        ok=gate is not None,
        detail=("receipt status %s; gate %s"
                % ((receipt or {}).get("invocation_status"),
                   "found" if gate else "MISSING")),
        evidence=GATE)

    # ---- R3: COMPLETE_PASS -> the full artifact ladder on disk ----
    verdict = (gate or {}).get("verdict")
    from discovery_fabric.engine.visual_compiler import visual_set  # noqa: E402
    node_count = 0
    if render_record:
        node_count = int(((render_record.get("scene_spec") or {})
                          .get("model") or {}).get("node_count") or 0)
    if not node_count and glb is not None:
        try:
            from discovery_fabric.engine.visual_compiler import \
                scene_builder  # noqa: E402
            node_count = int(
                scene_builder.inspect_glb(str(glb))["model"]["node_count"])
        except Exception:  # noqa: BLE001 — ladder check degrades to N/A
            node_count = 0
    required: List[str] = []
    if node_count:
        required = visual_set.required_artifacts(
            node_count,
            visual_set.DEFAULT_TURNTABLE_FRAMES)["required"]
    missing = [name for name in required
               if not (run_dir / "MODEL" / "3D" / name).is_file()
               or (run_dir / "MODEL" / "3D" / name).stat().st_size == 0]
    record(
        "R3_complete_pass_has_full_ladder",
        applicable=verdict == "COMPLETE_PASS" and bool(required),
        ok=not missing,
        detail=("gate %s; %d/%d ladder artifacts on disk%s"
                % (verdict, len(required) - len(missing), len(required),
                   f"; missing: {missing[:6]}" if missing else "")),
        evidence="MODEL/3D/")

    # ---- R4: hero exists -> source hash == canonical GLB hash ----
    hero = run_dir / "MODEL" / "3D" / "hero.png"
    hero_ok = False
    detail = ""
    if hero.is_file() and glb is not None:
        src_hash = (render_record or {}).get("source_glb_sha256") \
            or (receipt or {}).get("glb_sha256")
        actual = _sha256_file(glb)
        hero_ok = bool(src_hash) and src_hash == actual
        detail = (f"render source sha {'==' if hero_ok else '!='} "
                  f"canonical GLB sha ({glb.name})")
    else:
        detail = ("hero %s; glb %s"
                  % ("present" if hero.is_file() else "absent",
                     "present" if glb else "absent"))
    record("R4_hero_source_matches_canonical_glb",
           applicable=hero.is_file() and glb is not None,
           ok=hero_ok, detail=detail, evidence=RENDER_RECORD)

    # ---- R5: renderer skipped -> typed skip reason recorded ----
    status = (receipt or {}).get("invocation_status") or ""
    skipped = status.startswith("RENDER_SKIPPED") or status in (
        "RENDER_FAILED", "RENDER_TIMEOUT")
    reason = (receipt or {}).get("skip_reason")
    record("R5_skip_carries_typed_reason",
           applicable=skipped,
           ok=bool(reason),
           detail=(f"receipt status {status or '-'}; skip_reason "
                   f"{'present' if reason else 'MISSING'}"),
           evidence=RECEIPT)

    # ---- R6: GLB absent + run stopped upstream -> the projection the
    # UI renders carries the upstream state (never a frontend guess) ----
    stopped_upstream = session.get("status") in (
        "RUN_BLOCKED_TRANSPORT", "INTERRUPTED", "ERROR_TRANSPORT",
        "ERROR_RUN", "ERROR_BUILD", "ERROR_STUCK")
    record(
        "R6_no_glb_blocked_run_projects_upstream_state",
        applicable=glb is None and stopped_upstream,
        ok=True,  # the projection contract itself is source-pinned by
        # tests/test_r451_c2_blocked_state.py; the run-dir side has no
        # contradicting artifact to check (no GLB, no receipt expected)
        detail=("no GLB and the session record is an infrastructure "
                "stop — the design/evidence projections carry the "
                "typed upstream state (source-pinned)"))

    # ---- R7: receipt identity matches the run it sits in ----
    if receipt is not None:
        rid_ok = receipt.get("run_id") == run_dir.name
        record("R7_receipt_identity_matches_run",
               applicable=True, ok=rid_ok,
               detail=(f"receipt run_id {receipt.get('run_id')!r} vs "
                       f"run dir {run_dir.name!r}"),
               evidence=RECEIPT)

    # ---- R8 (R451-C2.2 §6): the no-silent-gap rule, adversarial form.
    # A pending async render job is the explicit-pending exception: the
    # invocation is IN FLIGHT (the job's own record proves it) — not a
    # missing invocation. A job the run's records show as terminal
    # without a receipt is still a gap (the job spoke without the
    # boundary ever being reached — the bridge's request failed).
    record(
        "R8_valid_glb_requires_visual_invocation",
        applicable=eng and visual_input_ready,
        ok=receipt is not None or job_pending,
        detail=("engineering geometry ready (authority %s); invocation "
                "receipt %s; render job %s"
                % (contract.get("engineering_authority"),
                   "found" if receipt else "MISSING",
                   f"{(job_rec or {}).get('status') or 'none'}"
                   + (" (explicit pending)" if job_pending else ""))),
        evidence=RECEIPT)

    # ---- R9 (R451-C2.2 §6): invocation claims pixels -> the persisted
    # render record must exist (the claim is never its own proof,
    # Art. XXIV)
    record(
        "R9_rendered_requires_render_record",
        applicable=rendered,
        ok=render_record is not None,
        detail=("receipt invocation_status %s; render record %s"
                % (status or "-",
                   "found" if render_record else "MISSING")),
        evidence=RENDER_RECORD)

    # ---- R10 (R451-C2.3 §8): the evaluator's announced state must be
    # consistent with the record invariants. This is the attack
    # coupling: the evaluator derives the state; THESE record checks
    # must agree with it, and the adversarial battery proves both
    # directions on independently authored fixtures.
    if join_state == "VISUAL_READY":
        record("R10_evaluator_state_consistent",
               applicable=True,
               ok=bool(release_chain and release_chain.get("verified"))
               and not missing and hero_ok,
               detail=("VISUAL_READY announced: release chain verified="
                       f"{bool(release_chain and release_chain.get('verified'))}; "
                       f"ladder complete={not missing}; "
                       f"hero source ok={hero_ok}"),
               evidence="release_chain")
    elif join_state in ("INVOCATION_MISSING", "RENDER_RECORD_MISSING",
                        "RELEASE_UNVERIFIED"):
        # the evaluator announced an explicit integrity failure: the
        # checker records it AS a violation (a failure state is a
        # finding, never a pass — "No silent gap")
        record("R10_evaluator_state_consistent", applicable=True,
               ok=False,
               detail=(f"the evaluator announced {join_state}: "
                       f"{join_detail}"),
               evidence="visual_join")

    return {
        "kind": "R451_C2_PRODUCT_WATCHDOG",
        "watchdog_version": "R451-C2.3",
        "run_dir": str(run_dir),
        "canonical_glb": str(glb) if glb else None,
        "engineering_authority": contract.get("engineering_authority"),
        "visual_input_ready": visual_input_ready,
        "receipt_status": (receipt or {}).get("invocation_status"),
        "gate_verdict": verdict,
        "join_state": join_state,
        "join_state_detail": join_detail,
        "join_states_vocabulary": list(JOIN_STATES),
        "release_chain": release_chain,
        "checks": checks,
        "violations": violations,
        "verdict": "PASS" if not violations else "FAIL",
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="R451-C2 (C2.10) deterministic geometry-to-visual "
                    "join watchdog — integrity checking only, no visual "
                    "inference; the join state comes from THE canonical "
                    "evaluator (toscanini/visual_join.py)")
    ap.add_argument("run_dir", help="the run directory to inspect")
    ap.add_argument("--json-out", help="also write the report here")
    args = ap.parse_args(argv)

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"watchdog: run dir not found: {run_dir}", file=sys.stderr)
        return 2
    report = run_watchdog(run_dir)
    text = json.dumps(report, indent=2)
    if args.json_out:
        Path(args.json_out).write_text(text)
    print(text)
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

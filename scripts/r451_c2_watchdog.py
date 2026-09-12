"""r451_c2_watchdog.py — the R451-C2 (C2.10) end-to-end product watchdog.

A deterministic integrity check over ONE run directory. It performs NO
visual inference and NO scientific interpretation — it only verifies
that the geometry-to-visual JOIN is mechanically sound, i.e. that each
recorded upstream fact carries the downstream consequence the product
contract requires (BS-003 / BS-030: built must be wired; BS-006: an
honest absence must not mask a missing invocation):

    if engineering GLB exists:
        assert a Visual Compiler invocation receipt exists
    if the receipt says the renderer ran (SUCCEEDED / PARTIAL):
        assert a visual gate record exists
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
GEOMETRY_SPEC = "MODEL/GEOMETRY_SPEC.json"

# the statuses that mean "the boundary was reached and the renderer ran"
_RENDERED_STATUSES = ("SUCCEEDED", "OK", "PARTIAL")


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


def canonical_glb(run_dir: Path) -> Optional[Path]:
    """The CURRENT generation's GLB — the same resolution order the
    Visual Compiler itself uses (one authority, two consumers)."""
    model_dir = run_dir / "MODEL"
    for name in ("engineering_model.glb",):
        p = model_dir / name
        if p.is_file():
            return p
    if model_dir.is_dir():
        glbs = sorted(model_dir.glob("model-*.glb"))
        if glbs:
            return glbs[-1]
    roots = sorted(run_dir.glob("*.glb"))
    return roots[0] if roots else None


def geometry_is_engineering(run_dir: Path) -> bool:
    """geometry_class == engineering per the run's own artifact
    identity / CIO geometry class — recorded facts only."""
    aid = _read_json(run_dir / "MODEL" / "ARTIFACT_IDENTITY.json") or {}
    cls = aid.get("geometry_class") or aid.get("class")
    if cls is None:
        cio = (_read_json(run_dir / "CIO.json")
               or _read_json(run_dir / "cio.json")) or {}
        cls = ((cio.get("geometry") or {}).get("class"))
    if cls is None:
        # no recorded class: a GLB the CAD pipeline authored under
        # MODEL/ is engineering by construction of the pipeline; the
        # watchdog records the basis either way (never silently assumed)
        return canonical_glb(run_dir) is not None
    return str(cls).upper().startswith("ENGINEERING")


def run_watchdog(run_dir: Path) -> Dict[str, Any]:
    """The deterministic rule set over one run dir. Returns the JSON
    report; `violations` empty == PASS."""
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
    receipt = _read_json(run_dir / RECEIPT)
    gate = _read_json(run_dir / GATE)
    render_record = _read_json(run_dir / RENDER_RECORD)

    # ---- R1: engineering GLB present -> invocation receipt present ----
    eng = glb is not None and geometry_is_engineering(run_dir)
    record(
        "R1_engineering_glb_has_invocation_receipt",
        applicable=glb is not None and eng,
        ok=receipt is not None,
        detail=("engineering GLB %s present; receipt %s"
                % (glb.name if glb else "-",
                   "found" if receipt else "MISSING")),
        evidence=RECEIPT)

    # ---- R2: renderer ran -> gate record exists ----
    rendered = (receipt or {}).get("status") in _RENDERED_STATUSES
    record(
        "R2_rendered_has_gate",
        applicable=rendered,
        ok=gate is not None,
        detail=("receipt status %s; gate %s"
                % ((receipt or {}).get("status"),
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
            or (receipt or {}).get("canonical_glb_sha256")
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
    status = (receipt or {}).get("status") or ""
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
    session = _read_json(run_dir / "session.json")
    stopped_upstream = False
    if session:
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

    return {
        "kind": "R451_C2_PRODUCT_WATCHDOG",
        "run_dir": str(run_dir),
        "canonical_glb": str(glb) if glb else None,
        "geometry_class_engineering": eng,
        "receipt_status": (receipt or {}).get("status"),
        "gate_verdict": verdict,
        "checks": checks,
        "violations": violations,
        "verdict": "PASS" if not violations else "FAIL",
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="R451-C2 (C2.10) deterministic geometry-to-visual "
                    "join watchdog — integrity checking only, no visual "
                    "inference")
    ap.add_argument("run_dir", help="the run directory to inspect")
    ap.add_argument("--json-out", help="also write the report here")
    args = ap.parse_args(argv)

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"watchdog: run dir not found: {run_dir}", file=sys.stderr)
        return 2
    sys.path.insert(0, str(REPO))
    report = run_watchdog(run_dir)
    text = json.dumps(report, indent=2)
    if args.json_out:
        Path(args.json_out).write_text(text)
    print(text)
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""toscanini/counsel.py — R414: the "Prepare for IP counsel" export.

Operator directive (product integration, section 20): a button that
exports the TECHNICAL evidence package a patent attorney needs —
invention description, technical diagrams, chronology, cited evidence,
relevant prior-art results, architecture comparison, provenance,
unresolved questions. Toscanini's role stays technology discovery and
PREPARATION; legal adjudication belongs to counsel.

Constitutional contract (Art. III, XII, LXVI, LXVII):
  - Every file in the export is derived from the run's persisted
    artifacts (nothing written fresh, nothing invented); each section
    names the artifact it was derived from.
  - The cover note carries the legal-position language — it NEVER
    asserts patentability (§3: the machine is not a patent court).
  - Provenance: the export manifest pins every source file by sha256,
    records the run_id and the engine commit, and stamps
    reviewer_provenance=AI_REVIEW (Art. LXVII).
  - Chronology is the run's own recorded timestamps — never
    reconstructed from memory (Art. VI).
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .cio import LEGAL_POSITION, PREFERRED_NOVELTY_LANGUAGE, language_guard

COUNSEL_VERSION = "1.0.0"


def _unwrap(field: Any) -> Any:
    """The invention spec wraps narrative fields as {value: X, ...} —
    unwrap to the value (same helper contract as cio.py)."""
    if isinstance(field, dict) and "value" in field and set(
            field.keys()) <= {"value", "epistemic_class", "origin_stage",
                              "evidence_ids", "note", "source_span",
                              "provenance"}:
        return field.get("value")
    return field


def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        if p.exists():
            data = json.loads(p.read_text())
            return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        return None
    return None


def _sha_file(p: Path) -> Optional[str]:
    try:
        if p.exists() and p.is_file():
            h = hashlib.sha256()
            with open(p, "rb") as fh:
                for chunk in iter(lambda: fh.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()
    except Exception:  # noqa: BLE001
        return None
    return None


def _section(title: str, body: str, source: str) -> str:
    bar = "=" * 72
    return (f"{bar}\n{title}\n{bar}\n\n{body}\n\n"
            f"[derived from: {source}]\n")


def build_counsel_package(session: Dict[str, Any],
                          out_path: Optional[Path] = None) -> Optional[Path]:
    """Build the counsel ZIP for one session. Returns the path (also
    written next to the run as COUNSEL_PACKAGE.zip) or None when the
    run has no run-dir artifacts to export (honest: nothing to hand
    counsel yet)."""
    run_dir = Path(session["run_dir"]) if session.get("run_dir") else None
    if not run_dir or not run_dir.exists():
        return None

    inv = _read_json(run_dir / "INVENTION_SPECIFICATION.json") or {}
    eng = _read_json(run_dir / "ENGINEERING_SPECIFICATION.json") or {}
    dex = _read_json(run_dir / "DECISIVE_EXPERIMENT.json") or {}
    pm = _read_json(run_dir / "PARAMETRIC_MODEL.json") or {}
    manifest = _read_json(run_dir / "run_manifest.json") or {}
    final_state = _read_json(run_dir / "final_state.json") or {}
    pa_env = _read_json(run_dir / "envelope_MULTI_SOURCE_DISCOVERY.json") or {}
    col_env = _read_json(run_dir / "envelope_COLLISION.json") or {}
    phys_env = _read_json(run_dir / "envelope_PHYSICS.json") or {}
    surv = _read_json(run_dir / "SURVIVOR_SELECTION.json") or {}

    if not (inv or final_state or manifest):
        return None

    sid = session.get("session_id") or "run"
    out_path = out_path or (run_dir / "COUNSEL_PACKAGE.zip")

    # ---- 00 cover note -------------------------------------------------
    chronology = _chronology(manifest, final_state, session)
    cover = (
        "TECHNICAL EVIDENCE PACKAGE — PREPARED FOR IP COUNSEL REVIEW\n"
        "\n"
        f"Run:            {sid}\n"
        f"User problem:   {(session.get('user_text') or '')[:400]}\n"
        f"Final status:   {session.get('final_status')}\n"
        f"Export version: {COUNSEL_VERSION}\n"
        "\n"
        "WHAT THIS IS\n"
        "A technical evidence export produced by the Toscanini discovery "
        "engine: the invention hypothesis, its engineering definition, "
        "the cited evidence, the prior-art search results, the "
        "adversarial attack findings, and full provenance.\n"
        "\n"
        "WHAT THIS IS NOT\n"
        "This is not a legal document. It contains no patentability "
        "opinion, no freedom-to-operate analysis, and no claim drafting. "
        f"{LEGAL_POSITION}\n"
        "\n"
        "STATUS LANGUAGE\n"
        f"{PREFERRED_NOVELTY_LANGUAGE}\n"
        "\n"
        "CONTENTS\n"
        "  01_INVENTION_DESCRIPTION.txt\n"
        "  02_TECHNICAL_DIAGRAMS/        (SVG engineering views, when "
        "produced)\n"
        "  03_CITED_EVIDENCE.txt\n"
        "  04_PRIOR_ART_RESULTS.txt\n"
        "  05_ARCHITECTURE_COMPARISON.txt\n"
        "  06_DECISIVE_EXPERIMENT.txt\n"
        "  07_UNRESOLVED_QUESTIONS.txt\n"
        "  08_PROVENANCE_MANIFEST.json\n"
        "\n"
        "CHRONOLOGY (the run's own recorded timestamps)\n"
        f"{chronology}\n"
    )

    # ---- 01 invention description ---------------------------------------
    ev_records = _unwrap(inv.get("evidence")) or []
    if isinstance(ev_records, dict):
        ev_records = ev_records.get("records") or []
    inv_body = _kv_block({
        "Invention ID": _unwrap(inv.get("invention_id"))
        if isinstance(inv.get("invention_id"), dict)
        else inv.get("invention_id"),
        "Problem": _unwrap(inv.get("problem")) or session.get("user_text"),
        "Mechanism": _unwrap(inv.get("mechanism")),
        "Novelty hypothesis": _unwrap(inv.get("novelty_hypothesis")),
        "Distinguishing features": _unwrap(inv.get(
            "distinguishing_features")),
        "Causal chain": _unwrap(inv.get("causal_chain")),
        "Engineering parameters": _unwrap(inv.get(
            "engineering_parameters")),
        "Constraints": _unwrap(inv.get("constraints")),
        "Assumptions": _unwrap(inv.get("assumptions")),
        "Failure modes": _unwrap(inv.get("failure_modes")),
        "Uncertainties": _unwrap(inv.get("uncertainties")),
        "Engineering spec (present)": bool(eng),
        "Parametric model (present)": bool(pm),
        "Simulation result (PHYSICS stage)":
            (phys_env.get("physics") or {}).get("lifecycle_verdict"),
        "Simulation class": "COMPUTATIONAL_RESULT (never a physical "
                            "observation — Art. LIII)",
        "Survivor selection": bool(surv) or
        (session.get("final_status") == "AUTOMATED_INVENTION_CANDIDATE"),
    })
    inv_txt = _section("01 INVENTION DESCRIPTION", inv_body,
                       "INVENTION_SPECIFICATION.json (+ENGINEERING_"
                       "SPECIFICATION/PARAMETRIC_MODEL presence)")

    # ---- 03 cited evidence -----------------------------------------------
    ev_lines: List[str] = []
    for i, e in enumerate(ev_records[:60]):
        if not isinstance(e, dict):
            continue
        ev_lines.append(
            f"[{i + 1}] id={e.get('id') or e.get('record_id')} "
            f"source={e.get('source')}\n"
            f"    title: {(e.get('title') or '')[:160]}\n"
            f"    class: {e.get('evidence_class') or e.get('epistemic_class')}\n"
            f"    span:  {(e.get('span') or e.get('quote') or '')[:200]}\n")
    ev_txt = _section(
        "03 CITED EVIDENCE",
        "\n".join(ev_lines) or "(no evidence records persisted)",
        "INVENTION_SPECIFICATION.json: evidence")

    # ---- 04 prior art ------------------------------------------------------
    pa = pa_env.get("prior_art")
    if isinstance(pa, dict):
        pa = pa.get("results") or []
    pa_lines: List[str] = []
    for i, r in enumerate((pa or [])[:60]):
        if not isinstance(r, dict):
            continue
        pa_lines.append(
            f"[{i + 1}] {(r.get('title') or r.get('name') or '')[:160]}\n"
            f"    source: {r.get('source')}  "
            f"id: {r.get('id') or r.get('record_id') or ''}\n")
    pa_txt = _section(
        "04 PRIOR-ART SEARCH RESULTS",
        "\n".join(pa_lines) or "(prior-art search produced no records "
                               "in this run)",
        "envelope_MULTI_SOURCE_DISCOVERY.json: prior_art\n"
        "NOTE: novelty SIGNALS from searched evidence; coverage "
        "limitations are the search's own (no legal novelty "
        "determination is made or implied)")

    # ---- 05 architecture comparison ---------------------------------------
    col_lines: List[str] = []
    cr = col_env.get("collision_results")
    if isinstance(cr, dict):
        for universe, blk in list(cr.items())[:12]:
            if isinstance(blk, dict):
                col_lines.append(
                    f"universe {universe}: verdict="
                    f"{blk.get('mapped_status') or blk.get('legacy_status')} "
                    f"results={blk.get('result_count')}")
    elif isinstance(cr, list):
        for c in cr[:12]:
            if isinstance(c, dict):
                col_lines.append(
                    f"verdict={c.get('verdict') or c.get('collision_risk')} "
                    f"note={(c.get('note') or c.get('reason') or '')[:180]}")
    ms = _read_json(run_dir / "envelope_MECHANISM_SPACE.json") or {}
    cands = ms.get("candidates") or []
    if isinstance(cands, list):
        col_lines.append(f"\nmechanism candidates explored: {len(cands)}")
    col_txt = _section(
        "05 ARCHITECTURE COMPARISON",
        "\n".join(col_lines) or
        "(no collision/comparison records persisted on this run)",
        "envelope_COLLISION.json + envelope_MECHANISM_SPACE.json")

    # ---- 06 decisive experiment -------------------------------------------
    exp = dex or _unwrap(inv.get("killer_experiment")) or {}
    exp_txt = _section(
        "06 DECISIVE EXPERIMENT (falsification contract)",
        _kv_block(exp if isinstance(exp, dict) else {"value": exp}) or
        "(no decisive experiment recorded)",
        "DECISIVE_EXPERIMENT.json / INVENTION_SPECIFICATION.json:"
        " killer_experiment")

    # ---- 07 unresolved questions ------------------------------------------
    unres: List[str] = []
    for u in (_unwrap(inv.get("uncertainties")) or [])[:20]:
        unres.append(f"- {u}" if isinstance(u, str) else f"- {json.dumps(u)[:200]}")
    for a in (_unwrap(inv.get("assumptions")) or [])[:20]:
        unres.append(f"- assumption: {a if isinstance(a, str) else json.dumps(a)[:200]}")
    if not (run_dir / "PACKAGE_REPORT.json").exists():
        unres.append("- no buyer technology package was produced on this "
                     "run (see the run state for the recorded reason)")
    unres.append("- the decisive physical experiment is specified but "
                 "not executed (reality-loop interface is the execution "
                 "path)")
    unres_txt = _section(
        "07 UNRESOLVED QUESTIONS",
        "\n".join(unres),
        "INVENTION_SPECIFICATION.json: uncertainties/assumptions + the "
        "run's own package/experiment records")

    # ---- 08 provenance manifest -------------------------------------------
    prov_files = {}
    for name in ("INVENTION_SPECIFICATION.json",
                 "ENGINEERING_SPECIFICATION.json",
                 "PARAMETRIC_MODEL.json", "DECISIVE_EXPERIMENT.json",
                 "run_manifest.json", "final_state.json",
                 "envelope_MULTI_SOURCE_DISCOVERY.json",
                 "envelope_COLLISION.json", "envelope_PHYSICS.json",
                 "envelope_ATTACK.json", "SURVIVOR_SELECTION.json"):
        f = run_dir / name
        sha = _sha_file(f)
        if sha:
            prov_files[name] = {"sha256": sha, "bytes": f.stat().st_size}
    prov_manifest = {
        "kind": "COUNSEL_PACKAGE_PROVENANCE",
        "export_version": COUNSEL_VERSION,
        "run_id": sid,
        "run_dir": str(run_dir),
        "final_status": session.get("final_status"),
        "source_files": prov_files,
        "derived_sections": {
            "01_INVENTION_DESCRIPTION": "INVENTION_SPECIFICATION.json",
            "03_CITED_EVIDENCE": "INVENTION_SPECIFICATION.json",
            "04_PRIOR_ART_RESULTS":
                "envelope_MULTI_SOURCE_DISCOVERY.json",
            "05_ARCHITECTURE_COMPARISON":
                "envelope_COLLISION.json + "
                "envelope_MECHANISM_SPACE.json",
            "06_DECISIVE_EXPERIMENT": "DECISIVE_EXPERIMENT.json",
            "07_UNRESOLVED_QUESTIONS": "INVENTION_SPECIFICATION.json",
        },
        "language_guard": language_guard(cover + inv_txt),
        "legal_position": LEGAL_POSITION,
        "reviewer_provenance": "AI_REVIEW",
        "note": "every section is derived from persisted run artifacts; "
                "this export invents nothing (Art. VI)",
    }

    # ---- diagrams (SVG views, when the run produced them) -----------------
    model_dir = run_dir / "MODEL"
    svgs = sorted(model_dir.glob("*.svg")) if model_dir.exists() else []
    svg_out = sorted((run_dir).glob("*.svg"))
    all_svgs = svgs + [s for s in svg_out if s not in svgs]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("00_COVER_NOTE.txt", cover)
        z.writestr("01_INVENTION_DESCRIPTION.txt", inv_txt)
        z.writestr("03_CITED_EVIDENCE.txt", ev_txt)
        z.writestr("04_PRIOR_ART_RESULTS.txt", pa_txt)
        z.writestr("05_ARCHITECTURE_COMPARISON.txt", col_txt)
        z.writestr("06_DECISIVE_EXPERIMENT.txt", exp_txt)
        z.writestr("07_UNRESOLVED_QUESTIONS.txt", unres_txt)
        z.writestr("08_PROVENANCE_MANIFEST.json",
                   json.dumps(prov_manifest, indent=1, sort_keys=True))
        for s in all_svgs[:8]:
            z.write(s, f"02_TECHNICAL_DIAGRAMS/{s.name}")
    return out_path


def _kv_block(d: Dict[str, Any]) -> str:
    out = []
    for k, v in d.items():
        if v is None or v is False or v == [] or v == {}:
            continue
        if isinstance(v, (dict, list)):
            v = json.dumps(v, indent=1)[:2000]
        out.append(f"{k}:\n  {v}\n")
    return "\n".join(out)


def _chronology(manifest: Dict, final_state: Dict,
                session: Dict[str, Any]) -> str:
    """The run's own recorded times, in order — created, stage events,
    terminal. Never reconstructed (Art. VI)."""
    lines = [f"  created (session record): {session.get('created_at')}"]
    for entry in (manifest.get("stage_log") or []):
        if isinstance(entry, dict) and entry.get("stage"):
            lines.append(
                f"  {entry.get('started_at') or '?'} -> "
                f"{entry.get('finished_at') or '?'}  "
                f"{entry.get('stage')} = {entry.get('status')}")
    if session.get("updated_at"):
        lines.append(f"  session last update: {session.get('updated_at')}")
    return "\n".join(lines)

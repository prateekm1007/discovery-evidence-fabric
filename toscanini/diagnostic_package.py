"""toscanini/diagnostic_package.py — R459: the always-available deliverable.

External product audit P0-4 (measured live at 181a22f): a discovery run
whose candidate was killed or contested skipped the artifact bridge, so
the user waited ~10 minutes and received NO downloadable file. The
product rule that produced that behavior (R455-LEAN-1: no survivor, no
invention artifact) stays in force — nothing here fabricates CAD, GLB,
or buyer-package claims for a run that did not earn them.

What changed: a run's DIAGNOSTIC record is itself a deliverable. This
module compiles the run's own persisted records into a diagnostic
package (a ZIP of Markdown + a hash manifest) that:

  * asserts NO invention, NO validation, NO buyer readiness — it is a
    falsification brief and an evidence summary of what happened;
  * is built ONLY from canonical run records (Art. X — no re-derivation,
    no smoothing of verdicts: KILLED stays KILLED, CONTESTED stays
    CONTESTED);
  * is idempotent and cached in the run dir (the first request builds
    it; identical inputs rebuild byte-identical members).

Every terminal run therefore yields a downloadable artifact: either the
technology package (a survivor exists) or the diagnostic package
(the investigation is the result).
"""
from __future__ import annotations

import hashlib
import io
import json
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional


def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — absent stays absent, never invented
        return None


def _challenge_line(g: Dict[str, Any]) -> str:
    ch = g.get("challenge") or {}
    if ch.get("killed"):
        cause = ch.get("kill_reason") or "recorded cause on the generation record"
        return f"- **{label(g)}** — killed by its own adversarial challenge ({cause})."
    if ch.get("escalated_objection"):
        return (f"- **{label(g)}** — the adversarial instrument raised an "
                f"objection it is not calibrated to decide; the objection "
                f"is preserved and escalated, not treated as a verdict.")
    if ch.get("survived"):
        return f"- **{label(g)}** — survived the specified adversarial tests."
    return f"- **{label(g)}** — the adversarial test has not been completed (nothing is claimed either way)."


def label(g: Dict[str, Any]) -> str:
    return g.get("label") or f"Invention {g.get('gen', '?'):02d}"


def build_executive_brief(detail: Dict[str, Any], usv: Dict[str, Any]) -> str:
    lines = [
        "# Executive brief — diagnostic package",
        "",
        f"**Problem:** {detail.get('user_text') or detail.get('title') or 'Untitled'}",
        "",
        f"**Outcome:** {usv.get('label') or 'Outcome unknown'}",
        "",
        usv.get("decision") or "",
        "",
        "## What this package is",
        "",
        "This is a diagnostic record of one investigation, compiled from",
        "the run's own persisted records. It is NOT a technology package:",
        "no invention is claimed, nothing is validated, and no buyer",
        "readiness is asserted. Where the investigation is uncertain,",
        "this brief says so in the same words the record uses.",
        "",
        "## What happened",
        "",
    ]
    gens = ((detail.get("run_state") or {}).get("generations") or {}).get("generations") or []
    for g in gens:
        lines.append(_challenge_line(g))
    if not gens:
        lines.append("- No invention architecture reached the challenge stage on this run.")
    lines += [
        "",
        "## Recommended next steps",
        "",
        next_step(detail, usv),
        "",
    ]
    return "\n".join(lines)


def next_step(detail: Dict[str, Any], usv: Dict[str, Any]) -> str:
    key = usv.get("user_state") or ""
    if key == "COMPLETED_FALSE_PREMISE":
        return ("Reformulate the problem's premise — the record shows why "
                "the stated mechanism cannot physically occur.")
    if usv.get("outcome") == "INVENTION_KILLED_BY_CHALLENGE":
        return ("Reformulate the problem with the recorded kill causes in "
                "view, or ask for another mechanism — the generation "
                "records show exactly what was killed and why.")
    if key == "COMPLETED_PACKAGE":
        return "Download the technology package — the release chain verified it against canonical state."
    if key == "COMPLETED_CANDIDATE" or key == "COMPLETED_EVOLVED":
        return "Review the candidate and its decisive experiment; the package forms when the release gate passes."
    return "Ask the investigation's own record what remains unknown — the unanswered questions drive the next round."


def build_evidence_summary(detail: Dict[str, Any]) -> str:
    ev = (detail.get("run_state") or {}).get("evidence_state") or {}
    lines = [
        "# Evidence summary",
        "",
    ]
    state = ev.get("state") or "NOT_REACHED"
    count = ev.get("records_found")
    sources = ev.get("sources") or []
    if state == "GATHERED" and count:
        lines += [
            f"Retrieval executed and measured **{count} records** from "
            f"{len(sources)} sources: {', '.join(sources)}.",
            "",
            "Every record entering the evidence pool is custody-frozen "
            "with a content hash; the exact spans live in the run's "
            "evidence records.",
        ]
        st = None
        for s in detail.get("stages") or []:
            if s.get("stage") == "RETRIEVE":
                st = s
                break
        titles = (st or {}).get("sample_titles") or []
        if titles:
            lines += ["", "### Sample of retrieved records", ""]
            for t in titles[:15]:
                lines.append(f"- {t}")
    elif state == "FAILED":
        lines += [
            "Evidence retrieval FAILED — the sources could not be reached.",
            "This is an infrastructure state, not evidence of absence; "
            "nothing was concluded from it.",
        ]
    elif state == "GATHERED":
        lines += [
            "Retrieval executed and measured **zero records** — a statement "
            "about these queries in these databases, not proof of novelty.",
        ]
    else:
        lines += [
            f"The evidence stage was not reached on this run (recorded "
            f"state: {state}). Retrieval never began, so there is nothing "
            f"to report from the sources.",
        ]
    return "\n".join(lines)


def build_diagnostic_report(detail: Dict[str, Any]) -> str:
    lines = [
        "# Diagnostic report",
        "",
        "The recorded investigation, verbatim where it matters:",
        "",
    ]
    atk = (detail.get("run_state") or {}).get("attack_state") or {}
    if atk:
        lines += [
            f"- Adversarial state: **{atk.get('state') or 'NOT_RUN'}**"
            + (f", overall verdict **{atk['overall']}**" if atk.get("overall") else ""),
        ]
    exp = (detail.get("run_state") or {}).get("experiment") or (
        next((s for s in detail.get("stages") or [] if s.get("stage") == "KILLER_EXPERIMENT"), {}) or {})
    ke = exp.get("experiment") if isinstance(exp, dict) else None
    if ke:
        lines += ["", "## The decisive experiment (specified, never executed)", ""]
        if isinstance(ke, dict):
            lines.append(f"- {ke.get('name') or ke.get('description') or 'Decisive test'}")
        else:
            lines.append(f"- {str(ke)[:400]}")
    unknowns = ((detail.get("run_state") or {}).get("overview") or {}).get("key_unknowns")
    if not unknowns:
        ov = detail.get("invention_specification") or {}
        unknowns = ov.get("uncertainties")
    if unknowns:
        lines += ["", "## What remains unknown", ""]
        if isinstance(unknowns, dict):
            for k, v in list(unknowns.items())[:10]:
                val = v.get("value") if isinstance(v, dict) else v
                lines.append(f"- {k}: {str(val)[:300]}")
        elif isinstance(unknowns, list):
            for u in unknowns[:10]:
                st = u.get("statement") if isinstance(u, dict) else str(u)
                lines.append(f"- {str(st)[:300]}")
    lines += [
        "",
        "## Boundary of this document",
        "",
        "Generated from the run's persisted records by the engine at",
        "download time. Simulation is not reality, prediction is not",
        "observation, and nothing here claims physical validation.",
        "",
    ]
    return "\n".join(lines)


def build_diagnostic_package(session_id: str, run_dir: Optional[Path],
                             detail: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Compile (and cache) the diagnostic package for a terminal run.
    Returns {path, bytes, sha256, built_at} or None when the run has no
    terminal record to report (honest absence — a running run gets
    nothing yet)."""
    usv = detail.get("user_state_view") or {}
    status = detail.get("status") or ""
    terminal = status == "COMPLETE" or status.startswith("RUN_BLOCKED") \
        or status.startswith("ERROR") or status == "INTERRUPTED"
    if not terminal:
        return None

    members = {
        "00_EXECUTIVE_BRIEF.md": build_executive_brief(detail, usv),
        "01_EVIDENCE_SUMMARY.md": build_evidence_summary(detail),
        "02_DIAGNOSTIC_REPORT.md": build_diagnostic_report(detail),
    }
    manifest = {
        "kind": "TOSCANINI_DIAGNOSTIC_PACKAGE",
        "session_id": session_id,
        "engine_commit": detail.get("engine_commit"),
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "members": {},
        "honesty": ("diagnostic record only — no invention claimed, "
                    "nothing validated, no buyer readiness asserted"),
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in members.items():
            data = text.encode("utf-8")
            manifest["members"][name] = hashlib.sha256(data).hexdigest()
            z.writestr(name, data)
        manifest_bytes = json.dumps(manifest, indent=1).encode("utf-8")
        z.writestr("manifest.json", manifest_bytes)
    content = buf.getvalue()

    out_path: Optional[Path] = None
    if run_dir and Path(run_dir).exists():
        out_path = Path(run_dir) / "diagnostic_package.zip"
        out_path.write_bytes(content)
    return {
        "bytes": content,
        "sha256": hashlib.sha256(content).hexdigest(),
        "path": str(out_path) if out_path else None,
    }

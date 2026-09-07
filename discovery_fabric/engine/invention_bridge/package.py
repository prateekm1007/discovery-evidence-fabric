"""Technology package assembler — handoff sections 15, 16, 33.

Assembles the buyer-facing TECHNOLOGY PACKAGE from one canonical source (the
run state + CIO + bridge artifacts):

    TECHNOLOGY_PACKAGE/
    ├── 00_PACKAGE_README.pdf
    ├── 01_TECHNICAL_ESSAY.pdf
    ├── 02_ENGINEERING_DEFINITION.json
    ├── 03_EVIDENCE_SUMMARY.json
    ├── 04_DECISIVE_EXPERIMENT.json
    ├── MODEL/
    │   ├── <invention>.glb
    │   ├── DESIGN_STATUS_3D.json
    │   ├── KEY_DIMENSIONS.json
    │   ├── [STEP/STL + GEOMETRY_VALIDATION — ENGINEERING_3D only]
    │   └── CONCEPTUAL_3D_DISCLAIMER.json [conceptual only]
    ├── MANIFEST.json            (sha256 per file — release integrity)
    └── PROVENANCE.json          (chain from run envelope hash to package)

The IP counsel export is a SEPARATE package type (already exposed by the engine
at /api/run/{id}/counsel-package); this assembler never embeds legal judgments.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import zipfile
from typing import Any, Dict, List, Optional

from . import epistemics as ep
from .essay import build_essay

INK = (0.16, 0.13, 0.10)          # warm near-black
ACCENT = (0.66, 0.38, 0.26)       # terracotta
PAPER = (0.985, 0.96, 0.93)       # warm ivory


# ---------------------------------------------------------------------------
# PDF rendering (essay + README) — editorial, calm, one accent
# ---------------------------------------------------------------------------

def _pdf(title: str, subtitle: str, essay: Dict[str, Any],
         extra_blocks: Optional[List[tuple]] = None) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib.enums import TA_LEFT
    from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate,
                                    Paragraph, Spacer)

    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4,
                          leftMargin=22 * mm, rightMargin=22 * mm,
                          topMargin=20 * mm, bottomMargin=20 * mm,
                          title=title)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
                  id="body")

    def on_page(canvas, doc_):
        canvas.setFillColorRGB(*PAPER)
        canvas.rect(0, 0, A4[0], A4[1], stroke=0, fill=1)
        canvas.setFillColorRGB(*ACCENT)
        canvas.rect(doc_.leftMargin, A4[1] - 14 * mm, 34 * mm, 1.1, stroke=0, fill=1)
        canvas.setFillColorRGB(0.45, 0.40, 0.35)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(doc_.leftMargin, 10 * mm,
                          "Toscanini — invented architecture, not invented evidence. "
                          "Generated content is labeled; nothing claims physical validation.")

    doc.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=on_page)])

    h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=19, leading=24,
                        textColor=INK, spaceAfter=2)
    sub = ParagraphStyle("sub", fontName="Helvetica", fontSize=9.5, leading=13,
                         textColor=ACCENT, spaceAfter=14)
    h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12.5, leading=16,
                        textColor=INK, spaceBefore=13, spaceAfter=5)
    body = ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=14.5,
                          textColor=INK, alignment=TA_LEFT, spaceAfter=7)

    story = [Paragraph(title, h1), Paragraph(subtitle, sub)]
    for key in essay.get("section_order", []):
        text = (essay.get("sections") or {}).get(key, "")
        if not text:
            continue
        title_ = (essay.get("titles") or {}).get(key, key)
        ep.guard_language(title_ + " " + text)   # language gate binds the essay copy
        story.append(Paragraph(title_, h2))
        story.append(Paragraph(text.replace("\n", "<br/>"), body))
    for heading, para in (extra_blocks or []):
        story.append(Paragraph(heading, h2))
        story.append(Paragraph(para.replace("\n", "<br/>"), body))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "Epistemic boundary: DESIGNED / SIMULATED / EVIDENCE-SUPPORTED / "
        "EXPERIMENTALLY VERIFIED states come only from the canonical invention "
        "object. EXPERIMENTALLY VERIFIED requires real reality-loop evidence. "
        + ep.COUNSEL_LANGUAGE, body))

    doc.build(story)
    return buf.getvalue()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Package assembly
# ---------------------------------------------------------------------------

def assemble(
    run_result: Dict[str, Any],
    cio: Optional[Dict[str, Any]],
    geometry_out: Dict[str, Any],
    out_dir: str,
    visualizability: Optional[Dict[str, Any]] = None,
    zip_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble the buyer-facing technology package ZIP from one canonical source.

    geometry_out is the bridge's geometry result (glb bytes/path, class,
    key_dimensions, components, validation...).
    """
    os.makedirs(out_dir, exist_ok=True)
    run_id = run_result.get("session_id") or run_result.get("run_id") or "run"
    cio = cio or {}
    identity = cio.get("identity") or {}
    invention_label = (
        identity.get("invention_id", {}).get("value")
        if isinstance(identity.get("invention_id"), dict)
        else identity.get("invention_id")
    ) or f"toscanini-{run_id[:12]}"
    invention_label = "".join(c for c in str(invention_label) if c.isalnum() or c in "-_") or f"run{run_id[:10]}"

    visualizability = visualizability or {}
    vis_class = geometry_out.get("visualizability_class") or visualizability.get(
        "visualizability_class") or ep.CONCEPTUAL_3D

    is_engineering = vis_class == ep.ENGINEERING_3D
    package_maturity = (
        ep.PACKAGE_MATURITY_ENGINEERING if is_engineering
        else ep.PACKAGE_MATURITY_EARLY
    )

    # ---- canonical artifacts ------------------------------------------------
    essay = build_essay(run_result, cio, visualizability)

    title = "Technology package — Toscanini invention"
    problem = run_result.get("user_text") or run_result.get("title") or "the recorded problem"
    subtitle = (f"{invention_label} · run {run_id} · maturity {package_maturity} · "
                f"3D class {vis_class}")

    readme_essay = {
        "section_order": ["what_toscanini_invented"],
        "titles": {"what_toscanini_invented": "What is in this package"},
        "sections": {
            "what_toscanini_invented": (
                f"This package lets a company evaluate a Toscanini invention against the "
                f"recorded problem: \u201c{problem}\u201d. "
                "01 is the technical essay (the human document). 02 is the engineering "
                "definition (parameters, envelopes, assumptions, failure modes). 03 is the "
                "honest evidence summary. 04 is the decisive experiment — the first thing "
                "to fund. MODEL/ contains the inspectable 3D representation: "
                + ("engineering parametric CAD with STEP/STL and measured geometry."
                   if is_engineering else
                   "a conceptual architecture visualization — topology and interaction "
                   "only, with NO engineering dimensions (CONCEPTUAL_3D != ENGINEERING_3D).")
                + " MANIFEST.json hashes every file; PROVENANCE.json traces the chain from "
                "the run's sealed envelope to this package."
            ),
        },
    }
    readme_pdf = _pdf("Toscanini technology package", subtitle, readme_essay)

    essay_pdf = _pdf(title, subtitle, essay)

    engineering_definition = {
        "artifact": "ENGINEERING_DEFINITION",
        "run_id": run_id,
        "engineering_specification": run_result.get("engineering_specification") or {},
        "bridge_parameters": geometry_out.get("parameters") or [],
        "status": "ENGINEERING_PROPOSED (parameters UNKNOWN unless marked MODELLED/SOURCE_FACT)",
    }

    evidence_summary = {
        "artifact": "EVIDENCE_SUMMARY",
        "run_id": run_id,
        "evidence_pack": run_result.get("evidence_pack") or {},
        "final_state_evidence": (run_result.get("final_state") or {}).get(
            "evidence_classification_counts"),
        "honesty": ("claims trace to recorded evidence spans; unknowns are recorded, "
                    "never suppressed"),
    }

    decisive = run_result.get("decisive_experiment") or {}
    decisive_experiment = {
        "artifact": "DECISIVE_EXPERIMENT",
        "run_id": run_id,
        **decisive,
    }

    model_dir = os.path.join(out_dir, "MODEL")
    os.makedirs(model_dir, exist_ok=True)

    glb_path = os.path.join(model_dir, f"{invention_label}.glb")
    with open(glb_path, "wb") as f:
        f.write(geometry_out["glb_bytes"])

    design_status = {
        "artifact": "3D_DESIGN_STATUS",
        "package_id": invention_label,
        "visualizability_class": vis_class,
        "3d_design_status": "PRESENT_CONCEPTUAL" if not is_engineering else "PRESENT_AND_VALIDATED",
        "status_meaning": ep.VISUALIZABILITY_MEANINGS[vis_class],
        "classification_basis": visualizability.get("classification_basis"),
        "cad_pipeline_status": geometry_out.get("cad_pipeline_status"),
        "components": geometry_out.get("components") or [],
        "key_dimensions": geometry_out.get("key_dimensions") or {},
    }
    ep.guard_no_engineering_dimensions(vis_class, design_status["key_dimensions"])

    with open(os.path.join(model_dir, "DESIGN_STATUS_3D.json"), "w") as f:
        json.dump(design_status, f, indent=2)
    with open(os.path.join(model_dir, "KEY_DIMENSIONS.json"), "w") as f:
        json.dump(geometry_out.get("key_dimensions") or {}, f, indent=2)

    if not is_engineering:
        with open(os.path.join(model_dir, "CONCEPTUAL_3D_DISCLAIMER.json"), "w") as f:
            json.dump(ep.conceptual_disclaimer(vis_class), f, indent=2)
    else:
        # engineering artifacts: STEP + STL (+ validation report)
        for key in ("step_files", "stl_files"):
            for p in geometry_out.get(key) or []:
                if p and os.path.exists(p):
                    dest = os.path.join(model_dir, os.path.basename(p))
                    with open(p, "rb") as src, open(dest, "wb") as dst:
                        dst.write(src.read())
        for key in ("step_path", "stl_path"):  # legacy singular keys
            p = geometry_out.get(key)
            if p and os.path.exists(p) and not any(
                    os.path.basename(x) == os.path.basename(p)
                    for x in (geometry_out.get("step_files") or []) +
                             (geometry_out.get("stl_files") or [])):
                dest = os.path.join(model_dir, os.path.basename(p))
                with open(p, "rb") as src, open(dest, "wb") as dst:
                    dst.write(src.read())
        validation = geometry_out.get("validation")
        if validation:
            with open(os.path.join(model_dir, "GEOMETRY_VALIDATION_REPORT.json"), "w") as f:
                json.dump(validation, f, indent=2)

    # ---- render artifacts (R419 sections 5-6: every invention gets
    # hero/section/exploded PNG + GLB when the pinned Blender build ran) ----
    # Copied from the run's MODEL/3D/ directory (the render stage's
    # output) into the package — the website and the download ZIP carry
    # the SAME canonical files (operator section 17: one canonical
    # object, no divergence). Presentation artifacts, honestly labeled:
    # the render record + conceptual disclaimers ride along.
    renders = geometry_out.get("renders") or {}
    render_dir = os.path.join(model_dir, "3D")
    render_artifacts: list = []
    if renders.get("status") in ("OK", "RENDER_PARTIAL"):
        src_dir = renders.get("out_dir") or ""
        if src_dir and os.path.isdir(src_dir):
            os.makedirs(render_dir, exist_ok=True)
            for name in ("hero.png", "hero.glb", "section.png", "section.glb",
                         "exploded.png", "exploded.glb", "render_record.json"):
                src = os.path.join(src_dir, name)
                if os.path.isfile(src) and os.path.getsize(src) > 0:
                    with open(src, "rb") as s, \
                            open(os.path.join(render_dir, name), "wb") as d:
                        d.write(s.read())
                    render_artifacts.append(f"MODEL/3D/{name}")
            # every copied artifact carries its presentation boundary
            presentation_note = {
                "artifact": "RENDER_ARTIFACT_DISCLOSURE",
                "rule": ("hero/section/exploded are PRESENTATION renders "
                         "(Blender 5.2 LTS headless). The authoritative "
                         "geometry is the CadQuery/OCCT GLB; section.glb/"
                         "exploded.glb are disclosed presentation variants "
                         "(cut / exploded offsets), never engineering "
                         "geometry (operator R419 section 7)"),
                "source_glb_sha256": renders.get("source_glb_sha256"),
                "pinned_blender": renders.get("pinned_blender"),
            }
            with open(os.path.join(render_dir,
                                   "RENDER_DISCLOSURE.json"), "w") as f:
                json.dump(presentation_note, f, indent=2)
            render_artifacts.append("MODEL/3D/RENDER_DISCLOSURE.json")

    # ---- top-level files -----------------------------------------------------
    with open(os.path.join(out_dir, "02_ENGINEERING_DEFINITION.json"), "w") as f:
        json.dump(engineering_definition, f, indent=2)
    with open(os.path.join(out_dir, "03_EVIDENCE_SUMMARY.json"), "w") as f:
        json.dump(evidence_summary, f, indent=2)
    with open(os.path.join(out_dir, "04_DECISIVE_EXPERIMENT.json"), "w") as f:
        json.dump(decisive_experiment, f, indent=2)
    with open(os.path.join(out_dir, "00_PACKAGE_README.pdf"), "wb") as f:
        f.write(readme_pdf)
    with open(os.path.join(out_dir, "01_TECHNICAL_ESSAY.pdf"), "wb") as f:
        f.write(essay_pdf)

    # ---- provenance ------------------------------------------------------------
    fs = run_result.get("final_state") or {}
    provenance = {
        "artifact": "PACKAGE_PROVENANCE",
        "run_id": run_id,
        "engine_commit": fs.get("code_commit"),
        "final_envelope_hash": fs.get("final_envelope_hash"),
        "invention_spec_hash": (run_result.get("invention_specification") or {}).get("_spec_hash"),
        "glb_sha256": geometry_out.get("glb_sha256"),
        "render_pipeline": (geometry_out.get("renders") or {}).get("render_pipeline"),
        "render_status": (geometry_out.get("renders") or {}).get("status"),
        "render_pinned_blender": (geometry_out.get("renders") or {}).get("pinned_blender"),
        "render_source_glb_sha256": (geometry_out.get("renders") or {}).get("source_glb_sha256"),
        "essay_from": "one canonical source: run state + CIO",
        "package_maturity": package_maturity,
        "counsel_boundary": ep.COUNSEL_LANGUAGE,
        "generated_by": "toscanini_bridge (canonical invention-to-3D-to-package path)",
    }
    with open(os.path.join(out_dir, "PROVENANCE.json"), "w") as f:
        json.dump(provenance, f, indent=2)

    # ---- manifest (hash every file) --------------------------------------------
    manifest_files = []
    for root, _, files in os.walk(out_dir):
        for fn in sorted(files):
            if fn in ("MANIFEST.json",):
                continue
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, out_dir)
            manifest_files.append({
                "path": rel,
                "sha256": _sha256_file(path),
                "bytes": os.path.getsize(path),
            })
    manifest = {
        "artifact": "PACKAGE_MANIFEST",
        "package_id": invention_label,
        "run_id": run_id,
        "file_count": len(manifest_files),
        "files": manifest_files,
        "package_maturity": package_maturity,
        "visualizability_class": vis_class,
        "integrity_rule": "every file is sha256-hashed; verify after transfer",
    }
    with open(os.path.join(out_dir, "MANIFEST.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    # ---- zip -------------------------------------------------------------------
    zip_path = os.path.join(
        os.path.dirname(out_dir.rstrip("/")) or ".",
        zip_name or f"TECHNOLOGY_PACKAGE_{invention_label}.zip",
    )
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(out_dir):
            for fn in sorted(files):
                path = os.path.join(root, fn)
                arc = os.path.join(os.path.basename(out_dir.rstrip("/")),
                                   os.path.relpath(path, out_dir))
                zf.write(path, arc)

    return {
        "zip_path": os.path.abspath(zip_path),
        "package_dir": os.path.abspath(out_dir),
        "manifest": manifest,
        "package_maturity": package_maturity,
        "visualizability_class": vis_class,
        "essay": essay,
        "glb_sha256": geometry_out.get("glb_sha256"),
        "render_artifacts": render_artifacts,
        "render_status": renders.get("status"),
        "zip_sha256": _sha256_file(zip_path),
        "zip_bytes": os.path.getsize(zip_path),
        "invention_label": invention_label,
    }

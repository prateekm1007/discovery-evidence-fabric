"""The ELITE technology transfer package factory — R424.

One technology -> one canonical invention state -> ONE ELITE
TECHNOLOGY TRANSFER PACKAGE (R423A named the single artifact;
R424 gives it the elite class). Everything is DERIVED from the
canonical run state by THIS factory — no hand-authored enrichment,
no operator assembly, no separate bridge/counsel packaging:

    TECHNOLOGY_PACKAGE/
    ├── 00_PACKAGE_README.pdf                        plain orientation
    ├── 01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf             one-page executive
    ├── 02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf  technical core
    ├── 03_BUYER_DECISION_CARD.pdf                   nine questions
    ├── 04_EVIDENCE_SUMMARY.pdf                      evidence by role
    ├── 05_TRANSFER_MANIFEST.pdf                     what transfers
    ├── PACKAGE_MANIFEST.json                        (sha256 per file)
    ├── ENGINEERING_TRACEABILITY.json                DI->DO->FM->VF graph
    ├── MATURITY_BASIS.json                          evidence-derived tier
    ├── COMMERCIAL_EVIDENCE.json                     Art. LXVI discipline
    ├── EQUATION_REGISTRY.json / NOT_APPLICABLE      real bindings
    ├── UNKNOWN_ROADMAP.json                         actionable unknowns
    ├── VALIDATION_ECONOMICS.json                    no invented dollars
    ├── LOOP_STATE.json                              Art. XXXVII state
    ├── PROVENANCE.json                              REAL engine commit
    ├── 05_TECHNICAL_EVALUATION.json (machine layer)
    ├── 02_ENGINEERING_DEFINITION.json (machine layer, REAL derivation)
    ├── 03_EVIDENCE_STRUCTURE.json + 04_DECISIVE_EXPERIMENT.json
    └── MODEL/  parametric source + parameters + manifest + status
        + lineage + provenance + validation + 3D_EVIDENCE/ when earned

The weak-package failure baseline (empty engineering definition,
empty decisive experiment, unknown engine commit, thin evidence,
no buyer architecture) is closed HERE — by the factory, never by
hand enrichment.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import epistemics as ep
from . import elite_package as _elite
from . import elite_documents as _edocs
from . import elite_model_layer as _emodel
from .essay import build_essay

INK = (0.16, 0.13, 0.10)          # warm near-black
ACCENT = (0.66, 0.38, 0.26)       # terracotta
PAPER = (0.985, 0.96, 0.93)       # warm ivory

from reportlab.lib.units import mm  # noqa: E402 — the cover flowable
from reportlab.platypus import Flowable  # noqa: E402


# ---------------------------------------------------------------------------
# PDF rendering (essay + README) — editorial, calm, one accent
# ---------------------------------------------------------------------------

class _CoverImage(Flowable):
    """Full-bleed cover image (object-fit: cover). The render is drawn
    ONCE — the exact approved PNG bytes the gate measured — scaled to
    COVER the page, center-cropped. No decoration is invented on top
    beyond the typed title band."""

    def __init__(self, path: str, page_w: float, page_h: float,
                 band: str = ""):
        super().__init__()
        self.path = path
        self.page_w = page_w
        self.page_h = page_h
        self.band = band
        self.width = page_w
        self.height = page_h

    def draw(self):
        c = self.canv
        c.saveState()
        p = c.beginPath()
        p.rect(0, 0, self.page_w, self.page_h)
        c.clipPath(p, stroke=0, fill=0)
        try:
            from reportlab.lib.utils import ImageReader
            img = ImageReader(self.path)
            iw, ih = img.getSize()
            scale = max(self.page_w / iw, self.page_h / ih)
            dw, dh = iw * scale, ih * scale
            c.drawImage(img, (self.page_w - dw) / 2,
                        (self.page_h - dh) / 2, dw, dh)
        except Exception:  # noqa: BLE001 — a missing render degrades to
            pass          # the paper background, never a broken PDF
        c.restoreState()
        if self.band:
            c.setFillColorRGB(0.05, 0.05, 0.06)
            bh = 16 * mm
            c.rect(0, 0, self.page_w, bh, stroke=0, fill=1)
            c.setFillColorRGB(0.92, 0.92, 0.94)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(12 * mm, bh / 2 - 3 * mm, self.band[:90])
            c.setFont("Helvetica", 7)
            c.drawString(12 * mm, 4 * mm,
                         "Toscanini Visual Compiler render — gate-approved "
                         "(Article LXXII); identical render as the website")


def _pdf(title: str, subtitle: str, essay: Dict[str, Any],
         extra_blocks: Optional[List[tuple]] = None) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib.enums import TA_LEFT
    from reportlab.platypus import (BaseDocTemplate, Flowable, Frame,
                                    Image, NextPageTemplate, PageBreak,
                                    Paragraph, Spacer, Table, TableStyle,
                                    PageTemplate)

    buf = io.BytesIO()
    cover = essay.pop("__cover__", None) if isinstance(essay, dict) else None
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

    cover_frame = Frame(0, 0, A4[0], A4[1],
                        leftPadding=0, rightPadding=0,
                        topPadding=0, bottomPadding=0, id="coverframe")
    # when the gate approved a cover, the FULL-BLEED template leads
    # (page 1 IS the hero); otherwise the framed body template is the
    # only template (text-only doc, unchanged from R424)
    has_cover = bool(cover and cover.get("gate") in ("PASS",
                                                     "COMPLETE_PASS"))
    doc.addPageTemplates([
        *([PageTemplate(id="cover", frames=[cover_frame])] if has_cover
          else []),
        PageTemplate(id="page", frames=[frame], onPage=on_page),
    ])

    h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=19, leading=24,
                        textColor=INK, spaceAfter=2)
    sub = ParagraphStyle("sub", fontName="Helvetica", fontSize=9.5, leading=13,
                         textColor=ACCENT, spaceAfter=14)
    h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12.5, leading=16,
                        textColor=INK, spaceBefore=13, spaceAfter=5)
    body = ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=14.5,
                          textColor=INK, alignment=TA_LEFT, spaceAfter=7)

    # ---- R441 PDF Constitution cover pages --------------------------------
    # page 1 full-page hero; 2 exploded; 3 orthographic; 4 dimensions —
    # the buyer reads the invention VISUALLY before the narrative. The
    # pages exist ONLY when the Visual Quality Gate PASSED (Article
    # LXXII: a render the gate rejected is embedded NOWHERE).
    story: List[Any] = []
    cover_pages = 0
    if has_cover:
        import os as _os
        hero = cover.get("hero")
        if hero and _os.path.isfile(hero):
            story.append(_CoverImage(hero, A4[0], A4[1],
                                     band=cover.get("label", title)))
            story.append(PageBreak())
            cover_pages += 1
            exploded = cover.get("exploded")
            if exploded and _os.path.isfile(exploded):
                story.append(_CoverImage(exploded, A4[0], A4[1],
                                         band="Exploded view — disclosed "
                                              "presentation variant"))
                story.append(PageBreak())
                cover_pages += 1
            ortho = [p_ for p_ in (cover.get("orthographic") or [])
                     if _os.path.isfile(p_)]
            if ortho:
                cell_w = (doc.width - 8 * mm) / 2
                cell_h = cell_w / 1.5
                story.append(Spacer(1, 4 * mm))
                for i in range(0, len(ortho), 2):
                    row = ortho[i:i + 2]
                    tbl: List[Any] = []
                    for p_ in row:
                        try:
                            tbl.append(Image(p_, width=cell_w,
                                             height=cell_h,
                                             kind="proportional"))
                        except Exception:  # noqa: BLE001
                            pass
                    if tbl:
                        t = Table([tbl], colWidths=[cell_w + 4 * mm] * len(tbl))
                        t.setStyle(TableStyle([
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 2),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 2)]))
                        story.append(t)
                        story.append(Spacer(1, 4 * mm))
                story.append(PageBreak())
                cover_pages += 1
            dimension = cover.get("dimension")
            if dimension and _os.path.isfile(dimension):
                story.append(_CoverImage(dimension, A4[0], A4[1] - 10 * mm,
                                         band="Dimensioned view — measured "
                                              "W/D/H in glTF units"))
                story.append(PageBreak())
                cover_pages += 1

    if cover_pages:
        # the body reverts to the framed page template
        story.append(NextPageTemplate("page"))
        story.append(PageBreak())
    story.extend([Paragraph(title, h1), Paragraph(subtitle, sub)])
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


def _visual_release_ok(gate: Dict) -> bool:
    """R443: the ONLY gate state that releases visuals to a buyer
    surface. COMPLETE_PASS is the R443 vocabulary (every quality rule
    passed AND the full required visual ladder present); legacy
    "PASS" from a pre-R443 record stays accepted only while the
    record declares no completeness block. A declared visual_set
    that is NOT complete blocks — "three artifacts exist" is never
    silently reinterpreted as "visual set passed"."""
    if not isinstance(gate, dict):
        return False
    if gate.get("verdict") not in ("PASS", "COMPLETE_PASS"):
        return False
    vs = gate.get("visual_set")
    if isinstance(vs, dict) and not vs.get("complete", True):
        return False
    return True


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
    engine_identity: Optional[Tuple[Optional[str], str]] = None,
) -> Dict[str, Any]:
    """Assemble the ELITE technology transfer package from one canonical
    source (run state + CIO + bridge geometry). R424: every layer is
    derived here — the weak-package gaps are closed by this factory.

    geometry_out is the bridge's geometry result (glb bytes/path, class,
    key_dimensions, components, validation, parametric_source...).
    engine_identity: (commit, source) from the caller's artifact
    identity resolution (the hosted engine's authority); when absent
    the factory resolves it honestly (never "unknown" while available).
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

    # ---- the canonical engineering projection (R424 §4/§6) ---------------
    proj = _elite.derive_engineering_projection(run_result, geometry_out)
    proj["decisive_selected"] = (run_result.get("decisive_experiment")
                                 or {}).get("selected")
    package_maturity = _elite.build_maturity(proj, is_engineering,
                                             run_result)

    # ---- canonical narrative (one source: run state + CIO) ----------------
    essay = build_essay(run_result, cio, visualizability)

    title = "Technology transfer package — Toscanini invention"
    problem = run_result.get("user_text") or run_result.get("title") or "the recorded problem"
    subtitle = (f"{invention_label} · run {run_id} · maturity {package_maturity} · "
                f"3D class {vis_class}")

    # ---- the six elite documents (R424 §3) ---------------------------------
    # R441 PDF Constitution: the DOSSIER opens VISUALLY — page 1
    # full-page hero, 2 exploded, 3 orthographic, 4 dimensions, then the
    # narrative and the decisive experiment. The cover exists ONLY when
    # the Visual Quality Gate PASSED (Article LXXII: NO HERO on a gate
    # failure — the buyer never sees a rejected render, in any medium).
    dossier_doc = _edocs.build_dossier(
        proj, run_result, essay, package_maturity, geometry_out,
        is_engineering)
    renders = geometry_out.get("renders") or {}
    gate = renders.get("visual_gate") or {}
    if renders.get("status") in ("OK", "PARTIAL") \
            and _visual_release_ok(gate):
        src3d = renders.get("out_dir") or ""
        if src3d:
            def _v(rel):
                p_ = os.path.join(src3d, rel)
                return p_ if os.path.isfile(p_) else None
            dossier_doc["__cover__"] = {
                "gate": "PASS",
                "label": f"{invention_label} · {vis_class}",
                "hero": _v("hero.png"),
                "exploded": _v("exploded.png"),
                "dimension": _v("dimension.png"),
                "orthographic": [
                    _v("orthographic/front.png"),
                    _v("orthographic/side.png"),
                    _v("orthographic/top.png"),
                    _v("orthographic/iso.png"),
                ],
            }
    docs = {
        "00_PACKAGE_README.pdf": _edocs.build_readme(
            proj, run_result, invention_label, package_maturity,
            is_engineering, vis_class),
        "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf": _edocs.build_executive_brief(
            proj, run_result, package_maturity),
        "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf": dossier_doc,
        "03_BUYER_DECISION_CARD.pdf": _edocs.build_decision_card(
            proj, run_result, package_maturity),
        "04_EVIDENCE_SUMMARY.pdf": _edocs.build_evidence_summary(
            proj, run_result),
        "05_TRANSFER_MANIFEST.pdf": _edocs.build_transfer_manifest(
            proj, run_result, invention_label, package_maturity,
            is_engineering, vis_class),
    }
    for fname, doc in docs.items():
        pdf_bytes = _pdf(title if fname.startswith("02") else
                         "Toscanini " + fname[:-4].replace("_", " ").lower(),
                         subtitle, doc)
        with open(os.path.join(out_dir, fname), "wb") as f:
            f.write(pdf_bytes)

    # ---- the machine-readable elite layers (R424 §2) -----------------------
    machine = {
        "ENGINEERING_TRACEABILITY.json": _elite.build_traceability(
            proj, invention_label, run_result),
        "MATURITY_BASIS.json": _elite.build_maturity_basis(
            proj, invention_label, package_maturity, run_result),
        "EQUATION_REGISTRY.json": _elite.build_equation_registry(
            proj, invention_label),
        "UNKNOWN_ROADMAP.json": _elite.build_unknown_roadmap(
            proj, invention_label),
        "VALIDATION_ECONOMICS.json": _elite.build_validation_economics(
            proj, invention_label,
            run_result.get("decisive_experiment")),
        "LOOP_STATE.json": _elite.build_loop_state(proj, invention_label),
        "COMMERCIAL_EVIDENCE.json": _elite.build_commercial_evidence(
            proj, invention_label, run_result),
    }
    for fname, layer in machine.items():
        with open(os.path.join(out_dir, fname), "w") as f:
            json.dump(layer, f, indent=2, ensure_ascii=False)

    # ---- 02 machine layer: the REAL engineering definition (R424 §4) ------
    engineering_definition = _engineering_definition(
        proj, run_id, geometry_out, is_engineering)
    with open(os.path.join(out_dir, "02_ENGINEERING_DEFINITION.json"), "w") as f:
        json.dump(engineering_definition, f, indent=2, ensure_ascii=False)

    # ---- 03/04 machine layers -----------------------------------------------
    evidence_summary = _evidence_structure(proj, run_id, run_result)
    with open(os.path.join(out_dir, "03_EVIDENCE_SUMMARY.json"), "w") as f:
        json.dump(evidence_summary, f, indent=2, ensure_ascii=False)
    decisive_experiment = _decisive_experiment_layer(
        proj, run_id, run_result)
    with open(os.path.join(out_dir, "04_DECISIVE_EXPERIMENT.json"), "w") as f:
        json.dump(decisive_experiment, f, indent=2, ensure_ascii=False)

    # ---- 05 machine layer: the technical evaluation -------------------------
    technical_evaluation = _technical_evaluation(
        proj, run_id, package_maturity, vis_class, geometry_out,
        is_engineering, run_result)
    with open(os.path.join(out_dir, "05_TECHNICAL_EVALUATION.json"), "w") as f:
        json.dump(technical_evaluation, f, indent=2, ensure_ascii=False)

    # ---- MODEL/ elite layer (R424 §9) ---------------------------------------
    model_dir = os.path.join(out_dir, "MODEL")
    os.makedirs(model_dir, exist_ok=True)
    glb_path = os.path.join(model_dir, f"{invention_label}.glb")
    with open(glb_path, "wb") as f:
        f.write(geometry_out["glb_bytes"])
    model_layer = _emodel.build_model_layer(
        out_dir, run_result, geometry_out, vis_class, invention_label,
        generation_models=geometry_out.get("generation_models"),
        renders=geometry_out.get("renders"))
    if not is_engineering:
        with open(os.path.join(model_dir, "CONCEPTUAL_3D_DISCLAIMER.json"),
                  "w") as f:
            json.dump(ep.conceptual_disclaimer(vis_class), f, indent=2)

    # ---- render artifacts (R419 §5-6, presentation-only) --------------------
    renders = geometry_out.get("renders") or {}
    render_dir = os.path.join(model_dir, "3D")
    render_artifacts: list = []
    if renders.get("status") in ("OK", "RENDER_PARTIAL"):
        src_dir = renders.get("out_dir") or ""
        if src_dir and os.path.isdir(src_dir):
            os.makedirs(render_dir, exist_ok=True)
            visual_set = [
                "hero.png", "hero.glb", "poster.png", "dimension.png",
                "section.png", "exploded.png", "exploded.glb",
                "orthographic/front.png", "orthographic/side.png",
                "orthographic/top.png", "orthographic/iso.png",
                "scene_spec.json", "visual_gate.json",
                "render_record.json",
            ]
            for frame in sorted(
                    Path(src_dir, "turntable").glob("frame-*.png")) \
                    if os.path.isdir(os.path.join(src_dir, "turntable")) \
                    else []:
                visual_set.append(f"turntable/{frame.name}")
            for name in visual_set:
                src = os.path.join(src_dir, name)
                if os.path.isfile(src) and os.path.getsize(src) > 0:
                    dst = os.path.join(render_dir, name)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    with open(src, "rb") as s, open(dst, "wb") as d:
                        d.write(s.read())
                    render_artifacts.append(f"MODEL/3D/{name}")
            presentation_note = {
                "artifact": "RENDER_ARTIFACT_DISCLOSURE",
                "rule": ("the visual set (hero/turntable/exploded/section/"
                         "orthographic/dimension/poster) is a "
                         "PRESENTATION render (R441 Visual Compiler: "
                         "headless Chromium + Three.js, the same renderer "
                         "family as the website). The authoritative "
                         "geometry is the CadQuery/OCCT GLB; exploded.glb "
                         "is a disclosed presentation variant (offsets "
                         "recorded), never engineering geometry (operator "
                         "R419 section 7, carried)"),
                "source_glb_sha256": renders.get("source_glb_sha256"),
                "scene_spec_sha256": renders.get("scene_spec_sha256"),
                "renderer_stack": renders.get("renderer_stack"),
            }
            with open(os.path.join(render_dir,
                                   "RENDER_DISCLOSURE.json"), "w") as f:
                json.dump(presentation_note, f, indent=2)
            render_artifacts.append("MODEL/3D/RENDER_DISCLOSURE.json")

            # ---- Article LXXII — no 3D artifact ships without passing
            # the Visual Compiler. A gate FAIL suppresses the hero in
            # this package (the buyer never sees a render the gate
            # rejected) and blocks the release; NOT_RUN (renderer
            # skipped/failed) fails closed the same way; R443 adds
            # PARTIAL (visual set NOT_COMPLETE) — a full-ladder
            # release requires verdict COMPLETE_PASS, never "some
            # artifacts exist".
            # R443 Workstream 4: the render record is validated
            # BEFORE any consumer field is read — a malformed record
            # never reaches this logic (it fails closed as NOT_RUN
            # with the schema violation as the reason).
            gate = renders.get("visual_gate") or {}
            gate_path = os.path.join(render_dir, "visual_gate.json")
            if os.path.isfile(gate_path):
                try:
                    gate = json.loads(Path(gate_path).read_text())
                except Exception:  # noqa: BLE001 — unreadable gate = fail closed
                    gate = {"verdict": "NOT_RUN",
                            "reasons": ["visual_gate.json unreadable"]}
            try:
                from discovery_fabric.engine.visual_compiler\
                    import render_record_schema as _rrs
                _rrs.validate_render_record(renders)
                _record_schema_error = None
            except Exception as exc:  # noqa: BLE001 — malformed = fail closed
                _record_schema_error = str(exc)
                gate = {"verdict": "NOT_RUN",
                        "reasons": [f"render record schema violation: "
                                    f"{exc}"]}
            gate_verdict = gate.get("verdict") or (
                "NOT_RUN" if renders.get("status") not in
                ("OK", "RENDER_PARTIAL") else "PASS")
            # COMPLETE_PASS is the ONLY release-passing verdict (R443
            # vocabulary); legacy "PASS" from a pre-R443 record stays
            # accepted ONLY while the record carries no visual_set
            # completeness block (fail closed once completeness is
            # declared and false).
            _vs = gate.get("visual_set")
            _complete_ok = (True if not isinstance(_vs, dict)
                            else bool(_vs.get("complete", True)))
            hero_suppressed = (
                gate_verdict not in ("PASS", "COMPLETE_PASS")
                or not _complete_ok
                or _record_schema_error is not None)
            with open(os.path.join(render_dir,
                                   "HERO_RELEASE_STATE.json"), "w") as f:
                json.dump({
                    "artifact": "HERO_RELEASE_STATE",
                    "article": "LXXII",
                    "gate_verdict": gate_verdict,
                    "hero_suppressed": hero_suppressed,
                    "release_blocked": hero_suppressed,
                    "failed_rules": gate.get("failed_rules", []),
                    "reasons": gate.get("reasons", []),
                }, f, indent=2)
            render_artifacts.append("MODEL/3D/HERO_RELEASE_STATE.json")
            if hero_suppressed:
                for suppressed in ("hero.png", "poster.png"):
                    sp = os.path.join(render_dir, suppressed)
                    if os.path.isfile(sp):
                        os.remove(sp)
                        render_artifacts.remove(f"MODEL/3D/{suppressed}")
                render_artifacts.append("MODEL/3D/HERO_SUPPRESSED.txt")
                with open(os.path.join(render_dir,
                                       "HERO_SUPPRESSED.txt"), "w") as f:
                    f.write("NO HERO — the Visual Quality Gate did not "
                            "pass; the hero is suppressed and the "
                            "package is blocked from release "
                            "(Article LXXII).\n\nFailed rules: "
                            + ", ".join(gate.get("failed_rules", []))
                            + "\n\nReasons:\n"
                            + "\n".join(f"- {r}" for r in
                                         gate.get("reasons", []))
                            + "\n")
    else:
        # fail closed (Art. V): a render that never ran CANNOT pass the
        # gate — the hero is suppressed and the release is blocked, with
        # the typed renderer status as the reason (Art. XXV: unknown
        # stays unknown)
        os.makedirs(render_dir, exist_ok=True)
        with open(os.path.join(render_dir, "HERO_RELEASE_STATE.json"),
                  "w") as f:
            json.dump({
                "artifact": "HERO_RELEASE_STATE",
                "article": "LXXII",
                "gate_verdict": "NOT_RUN",
                "hero_suppressed": True,
                "release_blocked": True,
                "failed_rules": [],
                "reasons": [f"renderer status: "
                            f"{renders.get('status', 'ABSENT')} — the "
                            "gate refuses to pass what it cannot "
                            "measure"],
            }, f, indent=2)
        render_artifacts.append("MODEL/3D/HERO_RELEASE_STATE.json")

    # ---- provenance (R424 §11: REAL engine identity, never lazy unknown) ---
    fs = run_result.get("final_state") or {}
    engine_commit, engine_commit_source = _elite.resolve_engine_commit(
        run_result, engine_identity)
    model_dir_path = Path(out_dir) / "MODEL"
    cad_source = {}
    if is_engineering and (model_dir_path / "CAD_SOURCE_PROVENANCE.json"
                           ).is_file():
        try:
            cad_source = {
                "relationship": "MODEL/PARAMETRIC_MODEL_SOURCE.py is "
                                "EXPORTED from the canonical "
                                "engineering_geometry.FORM_LIBRARY "
                                "builder (R425 §2: one CAD source of "
                                "truth)",
                "record": "MODEL/CAD_SOURCE_PROVENANCE.json",
                "drift_detection": "engineering_geometry."
                                   "verify_cad_source_provenance()",
            }
        except Exception:  # noqa: BLE001 — provenance stays honest
            cad_source = {}
    provenance = {
        "artifact": "PACKAGE_PROVENANCE",
        "run_id": run_id,
        "engine_commit": engine_commit,
        "engine_commit_source": engine_commit_source,
        "package_version": "R425_ELITE.1.1.0",
        "package_version_basis": (
            "R425: one CAD source of truth (canonical export), "
            "semantic maturity gates, complete traceability graph, "
            "buyer-runnable decisive-experiment contract, specific "
            "unknown roadmap, hardened renderer process boundary"),
        "cad_source_of_truth": cad_source or (
            "CONCEPTUAL class — no parametric CAD source exists "
            "(nothing fabricated)"),
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                          time.gmtime()),
        "final_envelope_hash": fs.get("final_envelope_hash"),
        "invention_spec_hash": (run_result.get("invention_specification") or {}).get("_spec_hash"),
        "canonical_invention_state_identity": {
            "invention_spec_hash": (run_result.get(
                "invention_specification") or {}).get("_spec_hash"),
            "final_envelope_hash": fs.get("final_envelope_hash"),
            "invention_id": invention_label,
            "run_id": run_id,
        },
        "glb_sha256": geometry_out.get("glb_sha256"),
        "model_layer_files": model_layer.get("files"),
        "render_pipeline": (geometry_out.get("renders") or {}).get("render_pipeline"),
        "render_status": (geometry_out.get("renders") or {}).get("status"),
        "render_pinned_blender": (geometry_out.get("renders") or {}).get("pinned_blender"),
        "render_source_glb_sha256": (geometry_out.get("renders") or {}).get("source_glb_sha256"),
        "derivation_relationships": (
            "documents + machine layers derive from the canonical run "
            "state (engineering_specification, invention_specification, "
            "final_state, evidence_pack) and the bridge geometry_out; "
            "MODEL/3D_EVIDENCE derives from re-executing the shipped "
            "parametric source; every file hash is in PACKAGE_MANIFEST"),
        "essay_from": "one canonical source: run state + CIO",
        "package_maturity": package_maturity,
        "counsel_boundary": ep.COUNSEL_LANGUAGE,
        "generated_by": ("toscanini_bridge elite package factory "
                         "(R424; canonical invention-to-package path)"),
    }
    with open(os.path.join(out_dir, "PROVENANCE.json"), "w") as f:
        json.dump(provenance, f, indent=2, ensure_ascii=False)

    # ---- manifest (hash every file) --------------------------------------------
    manifest_files = []
    for root, _, files in os.walk(out_dir):
        for fn in sorted(files):
            if fn in ("PACKAGE_MANIFEST.json",):
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
    # R424 §2: the elite manifest name
    with open(os.path.join(out_dir, "PACKAGE_MANIFEST.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    # ---- zip (R423A: ONE canonical customer artifact) -------------------------
    zip_path = os.path.join(
        os.path.dirname(out_dir.rstrip("/")) or ".",
        zip_name or f"TECHNOLOGY_TRANSFER_PACKAGE_{invention_label}.zip",
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
        "engine_commit": engine_commit,
        "package_version": provenance["package_version"],
    }


# ---------------------------------------------------------------------------
# Machine-layer derivations (R424 §2/§4)
# ---------------------------------------------------------------------------

def _engineering_definition(proj: Dict, run_id: str,
                            geometry_out: Dict,
                            is_engineering: bool) -> Dict:
    """R424 §4 — the REAL engineering definition: derived design inputs,
    outputs, constraints, parameters, subsystem architecture, failure
    modes, verification items, build steps, equations, technical
    evaluation, experiment requirements. Every quantity keeps its
    epistemic class; missing fields stay UNKNOWN (never plausible AI
    text)."""
    return {
        "artifact": "ENGINEERING_DEFINITION",
        "run_id": run_id,
        "status": "ENGINEERING_PROPOSED (parameters UNKNOWN unless marked "
                  "MODELLED/SOURCE_FACT)",
        "design_inputs": proj["design_inputs"],
        "design_outputs": proj["design_outputs"],
        "constraints": proj["constraints"],
        "parameters": proj["critical_parameters"],
        "subsystem_architecture": proj["subsystems"],
        "failure_modes": proj["failure_modes"],
        "verification_items": proj["verification"],
        "build_steps": proj["build_plan"],
        "governing_equations": proj["equations"],
        "experiment_requirements": _experiment_requirements(proj),
        "technical_evaluation": "see 05_TECHNICAL_EVALUATION.json",
        "bridge_parameters": geometry_out.get("parameters") or [],
        "build_path": {
            "geometry_sources": (
                ["MODEL/" + os.path.basename(p)
                 for p in (geometry_out.get("step_files") or [])]
                + ["MODEL/" + os.path.basename(p)
                   for p in (geometry_out.get("stl_files") or [])]
                + (["MODEL/PARAMETRIC_MODEL_SOURCE.py"]
                   if is_engineering else [])
                or ["MODEL/ (conceptual architecture — no engineering "
                    "geometry to build from)"]),
            "cad_authority": "CadQuery/OCCT (STEP is the engineering "
                             "exchange format; STL is the print format; "
                             "GLB is the inspectable visualization)",
            "parameters": "MODEL/PARAMETERS.json — every value carries "
                          "its provenance class; unmarked values are "
                          "UNKNOWN, never assumed",
            "not_yet_defined": (
                "manufacturing tolerances, material selection, and "
                "process qualification are NOT established by this "
                "package — they are the recipient's engineering work, "
                "starting from the recorded geometry and parameters"),
        },
        "epistemic_discipline": (
            "every quantity retains its recorded class (SOURCE_FACT / "
            "MODELLED / UNKNOWN / COMPUTATIONAL_RESULT / "
            "EXTERNAL_PRECEDENT); no field is filled with plausible "
            "AI text (R424 §4)"),
    }


def _experiment_requirements(proj: Dict) -> List[Dict]:
    reqs = []
    for v in (proj.get("verification") or [])[:8]:
        reqs.append({
            "requirement_id": v.get("id"),
            "requirement": (v.get("requirement") or "")[:300],
            "result": v.get("result", "UNKNOWN"),
            "acceptance": (v.get("acceptance") or
                           "UNKNOWN — pre-register before the test"),
        })
    if not reqs:
        return [{"requirement_id": None,
                 "requirement": "UNKNOWN (no verification items recorded)",
                 "result": "UNKNOWN",
                 "acceptance": "UNKNOWN"}]
    return reqs


def _evidence_structure(proj: Dict, run_id: str,
                        run_result: Dict) -> Dict:
    """R424 §3 (04) — evidence by role with exact provenance."""
    fs = run_result.get("final_state") or {}
    counts = fs.get("evidence_classification_counts") or {}
    retrieval = (run_result.get("evidence_pack") or {}).get(
        "retrieval") or []
    return {
        "artifact": "EVIDENCE_STRUCTURE",
        "run_id": run_id,
        "roles": [
            {"role": "DIRECT_SUPPORT",
             "count": counts.get("DIRECT_SUPPORT", 0),
             "meaning": "spans that state the claimed proposition"},
            {"role": "PARTIAL_SUPPORT",
             "count": counts.get("PARTIAL_SUPPORT", 0),
             "meaning": "spans that support part of the claim"},
            {"role": "BACKGROUND", "count": counts.get("BACKGROUND", 0),
             "meaning": "contextual, not claim-bearing"},
            {"role": "ANALOGY", "count": counts.get("ANALOGY", 0),
             "meaning": "adjacent-domain transfer, weaker class"},
            {"role": "CONTRADICTION",
             "count": counts.get("CONTRADICTORY", 0),
             "meaning": "spans that contradict the claim"},
            {"role": "UNAVAILABLE_SOURCES",
             "count": sum(1 for r in retrieval
                          if isinstance(r, dict) and r.get("error")),
             "meaning": "retrieval failures — absence is never evidence "
                        "(Art. XXI.3)"},
        ],
        "provenance": ("counts derive from the run's own "
                       "final_state.evidence_classification_counts; "
                       "per-span custody chains live in the run record"),
        "coverage_limitations": (
            f"{sum(1 for r in retrieval if isinstance(r, dict) and r.get('error'))} "
            "retrieval failure(s) recorded; unknown records stay "
            "UNKNOWN (Art. XXV)"),
        "evidence_pack": run_result.get("evidence_pack") or {},
    }


def _decisive_experiment_layer(proj: Dict, run_id: str,
                               run_result: Dict) -> Dict:
    """R425 §5 — the decisive experiment as a BUYER-RUNNABLE contract.

    Every field of the contract is derived from the canonical state
    where the record actually carries it; a field the canonical state
    does not define is emitted as NOT_DEFINED_IN_CANONICAL_STATE with
    the exact provenance basis (which record was inspected and found
    lacking) — never generic filler such as 'further testing required'
    and never an invented value (Art. I/XXV/LII).
    """
    recorded = run_result.get("decisive_experiment") or {}
    ke = proj.get("killer_experiment") or {}
    inv = run_result.get("invention_specification") or {}
    fs = run_result.get("final_state") or {}
    eng = run_result.get("engineering_specification") or {}
    wps = eng.get("engineering_build_plan") or []
    vfs = eng.get("verification_matrix") or []
    cps = (eng.get("engineering_core") or {}).get(
        "critical_parameters") or []
    selected = recorded.get("selected")
    if isinstance(selected, str):
        try:
            import ast
            selected = ast.literal_eval(selected)
        except (ValueError, SyntaxError):
            selected = None
    sel = selected if isinstance(selected, dict) else {}

    def _field(value, provenance_basis: str, status: str = "DEFINED"):
        return {
            "value": value,
            "status": status,
            "provenance_basis": provenance_basis,
        }

    def _not_defined(basis: str):
        return _field("NOT_DEFINED_IN_CANONICAL_STATE", basis,
                      "NOT_DEFINED_IN_CANONICAL_STATE")

    # ---- the 14-field contract -------------------------------------------
    hypotheses = [
        {"name": h.get("name"),
         "description": h.get("description"),
         "prior_probability": h.get("prior_probability"),
         "provenance_class": ((h.get("provenance") or {}).get(
             "epistemic_class"))}
        for h in (ke.get("hypotheses") or [])
        if isinstance(h, dict)][:8]

    cc = inv.get("causal_chain")
    cc_val = cc.get("value") if isinstance(cc, dict) else None
    intervention_rec = (cc_val or {}).get("intervention") if isinstance(
        cc_val, dict) else None
    if not intervention_rec:
        intervention_rec = (cc_val or {}).get("mechanism") if isinstance(
            cc_val, dict) else None

    first_wp = next((w for w in wps if w.get("test_article")), None) \
        or (wps[0] if wps else None)
    falsification_vf = next(
        (v for v in vfs if "falsification" in str(
            (v.get("invention_tie") or {}).get("linkage_kind")
            or "").lower()), None)
    decision_vf = falsification_vf or (vfs[0] if vfs else None)
    kill_arm = next((h for h in hypotheses
                     if h.get("name") == "H_effect_fails"), None)

    experiment_id = sel.get("experiment") or ke.get("selected")

    contract = {
        "experiment_id": (
            _field(
                experiment_id,
                "decisive_experiment.selected.experiment "
                "(the loop's own selection)")
            if experiment_id else
            _not_defined("decisive_experiment.selected and "
                         "invention_specification.killer_experiment "
                         "carry no experiment selection")),
        "hypothesis": _field(
            hypotheses,
            "invention_specification.killer_experiment.hypotheses "
            "(recorded names, descriptions, priors)")
            if hypotheses else
            _not_defined("invention_specification.killer_experiment "
                         "carries no hypotheses array"),
        "intervention": _field(
            intervention_rec,
            "invention_specification.causal_chain."
            + ("intervention" if (cc_val or {}).get("intervention")
               else "mechanism")
            + " (the recorded causal mechanism under test)")
            if intervention_rec else
            _not_defined("invention_specification.causal_chain "
                         "carries no intervention/mechanism value"),
        "baseline_control": (
            _not_defined(
                "verification_matrix "
                + str((decision_vf or {}).get("id"))
                + ".requirement mentions a baseline comparison in "
                "prose, but the canonical record carries no structured "
                "baseline_arm/control_arm field — the arms are the "
                "recipient's pre-registration work, fixed from the "
                "measured baseline per the recorded acceptance rule")
            if decision_vf else
            _not_defined("no verification_matrix record exists")),
        "test_article": _field(
            (first_wp or {}).get("test_article"),
            "engineering_build_plan "
            + str((first_wp or {}).get("work_package"))
            + ".test_article (the recorded article to build)")
            if (first_wp or {}).get("test_article") else
            _not_defined("engineering_build_plan carries no "
                         "test_article field"),
        "measurable_variables": _field(
            [{"parameter_id": p.get("parameter_id"),
              "name": p.get("name") or p.get("parameter"),
              "symbol": p.get("symbol"),
              "unit": p.get("unit"),
              "value_status": p.get("value_status"),
              "value_class": p.get("value_class")}
             for p in cps[:12]],
            "engineering_core.critical_parameters (recorded symbols, "
            "units, and value_status — UNKNOWN values stay UNKNOWN)")
            if cps else
            _not_defined("engineering_core.critical_parameters is "
                         "empty"),
        "apparatus_instrumentation": _field(
            (first_wp or {}).get("equipment"),
            "engineering_build_plan "
            + str((first_wp or {}).get("work_package"))
            + ".equipment (the recorded equipment requirement)")
            if (first_wp or {}).get("equipment") else
            _not_defined("engineering_build_plan carries no equipment "
                         "field"),
        "procedure": _field(
            {"verification_requirement": (decision_vf or {}).get(
                "requirement"),
             "work_package_measurement": (first_wp or {}).get(
                 "measurement")},
            "verification_matrix "
            + str((decision_vf or {}).get("id"))
            + ".requirement + engineering_build_plan "
            + str((first_wp or {}).get("work_package"))
            + ".measurement (the recorded procedure texts)")
            if (decision_vf or {}).get("requirement") else
            _not_defined("verification_matrix carries no requirement"),
        "acceptance_rule": _field(
            {"rule": (decision_vf or {}).get("acceptance"),
             "status": (decision_vf or {}).get("acceptance_status")
             or (decision_vf or {}).get("result")},
            "verification_matrix "
            + str((decision_vf or {}).get("id"))
            + ".acceptance (the recorded pre-registration rule — the "
            "numeric margin is fixed from the measured baseline at "
            "pre-registration, never invented here)")
            if (decision_vf or {}).get("acceptance") else
            _not_defined("verification_matrix carries no acceptance "
                         "rule"),
        "falsification_rule": _field(
            {"kill_arm": kill_arm,
             "rule_basis": (decision_vf or {}).get("acceptance"),
             "kill_probability": sel.get("kill_probability")},
            "invention_specification.killer_experiment.hypotheses "
            "(H_effect_fails is the recorded falsification arm) + "
            "verification_matrix "
            + str((decision_vf or {}).get("id"))
            + ".acceptance (the failing side of the recorded rule) + "
            "decisive_experiment.selected.kill_probability (UNKNOWN "
            "where no sourced base rate exists)")
            if kill_arm else
            _not_defined("the killer-experiment record carries no "
                         "explicit falsification arm hypothesis"),
        "expected_discriminating_outcomes": _field(
            [{"outcome": h.get("name"),
              "meaning": h.get("description"),
              "prior_probability": h.get("prior_probability")}
             for h in hypotheses],
            "invention_specification.killer_experiment.hypotheses — "
            "the recorded arms the experiment separates (Bayesian EIG "
            "over MODEL_DERIVED priors per the recorded basis)")
            if hypotheses else
            _not_defined("no recorded hypothesis arms"),
        "dependencies": _field(
            sel.get("dependency"),
            "decisive_experiment.selected.dependency (the recorded "
            "precondition)")
            if sel.get("dependency") else
            _not_defined("decisive_experiment.selected carries no "
                         "dependency field"),
        "safety_operational_constraints": _field(
            {"regulatory_pathway": (eng.get("regulatory") or {}).get(
                "pathway"),
             "candidate_standards": (eng.get("regulatory") or {}).get(
                 "candidate_standards")},
            "engineering_specification.regulatory (the recorded "
            "regulatory determination — UNKNOWN pathway stays UNKNOWN "
            "per the R370C correction; never inferred from device "
            "class)")
            if (eng.get("regulatory") or {}).get("pathway") else
            _not_defined("engineering_specification.regulatory carries "
                         "no pathway"),
        "decision_mapping": _field(
            {"next_best_action": fs.get("next_best_action"),
             "selection_explanation": recorded.get("explanation"),
             "decision_impact": sel.get("decision_impact"),
             "prior_update_rule": (
                 "the measured outcome updates the recorded priors "
                 "(Bayesian, per decisive_experiment.selected.basis "
                 + repr(sel.get("basis")) + ")")},
            "final_state.next_best_action + decisive_experiment."
            "explanation/selected (the recorded decision semantics)")
            if (fs.get("next_best_action")
                    or recorded.get("explanation")) else
            _not_defined("final_state.next_best_action and "
                         "decisive_experiment.explanation are absent"),
        "next_technical_state_transition": _field(
            {"current_state": ((fs.get("evolution") or {}).get(
                "current_invention") or {}).get("state"),
             "transition": (
                 "the experiment's recorded arms map the transition: "
                 "H_effect_holds graduates the recorded "
                 "INVENTION_REQUIRES_EXPERIMENT state to a sourced "
                 "measurement; H_effect_fails terminates the lineage "
                 "(the recorded kill arm)")},
            "final_state.evolution.current_invention.state (the "
            "recorded technical state) + the recorded hypothesis arms")
            if ((fs.get("evolution") or {}).get("current_invention")
                    or {}).get("state") else
            _not_defined("final_state.evolution.current_invention "
                         "carries no state"),
    }

    # ---- the honest contract-level summary -------------------------------
    defined = [k for k, v in contract.items()
               if v["status"] != "NOT_DEFINED_IN_CANONICAL_STATE"]
    return {
        "artifact": "DECISIVE_EXPERIMENT",
        "schema": "R425_DECISIVE_EXPERIMENT_CONTRACT",
        "run_id": run_id,
        "contract": contract,
        "contract_completeness": {
            "fields_total": len(contract),
            "fields_defined_in_canonical_state": len(defined),
            "fields_not_defined": len(contract) - len(defined),
            "not_defined_fields": [
                k for k, v in contract.items()
                if v["status"] == "NOT_DEFINED_IN_CANONICAL_STATE"],
            "discipline": (
                "every field is either derived from a named canonical "
                "record or emitted as NOT_DEFINED_IN_CANONICAL_STATE "
                "with the exact record inspected — no generic filler, "
                "no invented values (R425 §5)"),
        },
        "recorded_layer": {
            k: v for k, v in recorded.items() if k != "artifact"},
        "discriminating_contract": (
            _elite.experiment_contract_assessment(proj, run_result)
            if hasattr(_elite, "experiment_contract_assessment")
            else None),
    }


def _first_verification(proj: Dict) -> Optional[Dict]:
    for v in (proj.get("verification") or [])[:1]:
        return {"requirement": (v.get("requirement") or "")[:300],
                "acceptance": (v.get("acceptance") or
                               "UNKNOWN — pre-register before the test"),
                "result": v.get("result")}
    return None


def _technical_evaluation(proj: Dict, run_id: str, maturity: str,
                          vis_class: str, geometry_out: Dict,
                          is_engineering: bool,
                          run_result: Dict) -> Dict:
    """R423A Phase 3 layer, now with the R424 maturity basis inline."""
    return {
        "artifact": "TECHNICAL_EVALUATION",
        "run_id": run_id,
        "package_maturity": maturity,
        "maturity_meaning": ep.PACKAGE_MATURITY_MEANINGS.get(
            maturity, maturity),
        "maturity_basis": "see MATURITY_BASIS.json (evidence-derived)",
        "visualizability_class": vis_class,
        "visualizability_meaning": ep.VISUALIZABILITY_MEANINGS.get(
            vis_class, vis_class),
        "geometry_validation": geometry_out.get("validation") or {
            "status": "NOT_APPLICABLE_CONCEPTUAL"},
        "cad_pipeline_status": geometry_out.get("cad_pipeline_status"),
        "render_status": (geometry_out.get("renders") or {}).get("status"),
        "simulation": {
            "executed": bool((run_result.get("final_state") or {}).get(
                "simulation_executed")),
            "class": "COMPUTATIONAL_RESULT at most — never a physical "
                     "observation (Art. XXXVIII)",
        },
        "physical_validation": {
            "status": "NOT_PERFORMED",
            "meaning": "nothing in this package was measured in reality; "
                       "EXPERIMENTALLY VERIFIED is not claimed anywhere",
        },
        "what_is_earned": [
            "the invention architecture survived the recorded "
            "adversarial challenge and adjudication stages",
            "the 3D representation exists with the class recorded "
            "above" + (" and passed deterministic geometry gates"
                       if is_engineering else
                       " (conceptual topology — engineering CAD is "
                       "unearned)"),
            "every claim in this package traces to the run's recorded "
            "evidence spans (PROVENANCE.json + PACKAGE_MANIFEST.json)",
        ],
        "what_is_proposed_not_earned": [
            "parameter values without a SOURCE_FACT/MODELLED class are "
            "UNKNOWN",
            "no physical experiment has been run (see the decisive "
            "experiment section for the cheapest one)",
            "buyer-release quality gates were not applied to this "
            "package (the release chain is a separate authority)",
        ],
        "reviewer_provenance": "AI_REVIEW",
    }

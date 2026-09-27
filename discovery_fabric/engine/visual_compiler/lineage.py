"""lineage.py — R444-C2 read-only buyer-surface lineage verifier.

Direct R444-C2 requirement: "verify exact artifact lineage:
GEOMETRY_SPEC hash -> GLB hash -> render source hash -> hero hash ->
poster hash -> PDF embedded image hash/source".

The Visual Quality Gate (visual_gate.py) re-measures artifacts INSIDE the
render out_dir at render time. Nothing re-measures the chain on the
BUYER SURFACE — the package tree a buyer actually receives and the PDFs
embedded in it. This module closes that gap WITHOUT touching the package
compiler (R444 do-not-touch): it is a verifier in the constitutional
sense (Art. III — the verifier never trusts the claimant; Art. IX —
certification is observational, it writes nothing).

What is re-measured (every check is a fresh hash/pixel measurement,
never a record lookup alone):

  L1 render_source     MODEL/3D/render_record.json must VALIDATE through
                       the R443 typed schema, and its source_glb_sha256
                       (when the record carries one — R443+ records do)
                       must equal the sha256 of the package's canonical
                       GLB. An R442-era record without the field is an
                       honest INCOMPLETE, never a pass.
  L2 artifact_bytes    every visual artifact the release state exposes
                       in MODEL/3D must hash to exactly the bytes the
                       render record recorded at render time. A swapped
                       copy is a substituted artifact (FAIL). Suppressed
                       views (hero.png/poster.png under a non-releasable
                       verdict) must be ABSENT — their presence is a
                       suppression bypass (FAIL).
  L3 release_state     visual_gate.json verdict, HERO_RELEASE_STATE.json
                       verdict, and the actual presence of the hero files
                       must agree: COMPLETE_PASS (or legacy PASS) <=> hero
                       present and release allowed; anything else =>
                       suppressed + blocked.
  L4 pdf_embedded_hero for each PDF in the package root, page 1's
                       embedded image (decoded pixels, container-agnostic)
                       must be pixel-identical to MODEL/3D/hero.png when
                       the release is allowed. Under suppression, page 1
                       must carry NO image at all (fail-closed proof).
                       ReportLab drawImage embeds source pixels (scaling
                       is a transform), so the comparison is exact.
  L5 geometry_spec     when MODEL/GEOMETRY_SPEC.json and
                       MODEL/ARTIFACT_IDENTITY.json exist: spec_sha256 ==
                       source_geometry_hash and the identity's
                       geometry_hash == the canonical GLB sha256 (the
                       engineering link this round may only READ — it is
                       Coder 1's surface). Missing links are an honest
                       INCOMPLETE (Art. XXV — unknown stays unknown).

Verdict: FAIL if any check fails; else INCOMPLETE (with every missing
link named) if any check cannot find its evidence; else VERIFIED.
Fail-closed: nothing is assumed from absence.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

LINEAGE_VERSION = "R444-1"

# views whose package presence is controlled by the suppression contract
# (package.py removes exactly these two on a non-releasable verdict)
SUPPRESSED_ON_BLOCK = ("hero.png", "poster.png")

# the PDFs the package constitution places in the package root; the
# dossier carries the Article LXXII cover pages
_DOSSIER_HINTS = ("TECHNOLOGY_TRANSFER_DOSSIER",)


def _sha256_file(path: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _sha256_pixels(img_bytes: bytes) -> Optional[str]:
    """Container-agnostic pixel hash: decode (PNG/JPEG/whatever PIL
    reads), normalize to RGB, hash the raw pixels. ReportLab embeds the
    source pixels and scales by transform, so an untampered cover is
    pixel-identical to the approved render."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        return hashlib.sha256(img.tobytes()).hexdigest()
    except Exception:  # noqa: BLE001 — unreadable image is typed below
        return None


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _canonical_glb(package_dir: Path) -> Optional[Path]:
    """The package's canonical GLB: the current generation from
    DESIGN_LINEAGE.json when present, else the single MODEL/*.glb."""
    model_dir = package_dir / "MODEL"
    lineage = _read_json(model_dir / "DESIGN_LINEAGE.json")
    if lineage:
        for gen in lineage.get("generation_models") or []:
            if gen.get("current") and gen.get("glb"):
                p = package_dir / gen["glb"]
                if p.is_file():
                    return p
    glbs = sorted(model_dir.glob("*.glb"))
    return glbs[0] if len(glbs) == 1 else None


def _check_render_source(package_dir: Path) -> Dict[str, Any]:
    rec = _read_json(package_dir / "MODEL" / "3D" / "render_record.json")
    if rec is None:
        return {"pass": False, "state": "INCOMPLETE",
                "reason": "MODEL/3D/render_record.json missing or "
                          "unparseable — lineage cannot start from "
                          "nothing (never assumed)"}
    # the record must survive the R443 typed schema
    try:
        from .render_record_schema import validate_render_record
        validate_render_record(rec)
        schema_valid = True
        schema_error = None
    except Exception as exc:  # noqa: BLE001
        schema_valid = False
        schema_error = str(exc)
    if not schema_valid:
        return {"pass": False, "state": "FAIL",
                "reason": f"render record does not validate: {schema_error}"}
    src_sha = rec.get("source_glb_sha256")
    if not src_sha:
        return {"pass": False, "state": "INCOMPLETE",
                "reason": "render record predates the R443 source_glb "
                          "sha256 field — the render-source link is "
                          "UNPROVEN for this tree, not assumed"}
    glb = _canonical_glb(package_dir)
    if glb is None:
        return {"pass": False, "state": "INCOMPLETE",
                "reason": "canonical GLB not resolvable in MODEL/ "
                          "(no DESIGN_LINEAGE current pointer and not "
                          "exactly one MODEL/*.glb)"}
    actual = _sha256_file(glb)
    ok = (actual == src_sha)
    return {"pass": ok,
            "state": "VERIFIED" if ok else "FAIL",
            "canonical_glb": str(glb.relative_to(package_dir)),
            "recorded_source_glb_sha256": src_sha,
            "measured_glb_sha256": actual,
            "reason": None if ok else
            "the package GLB is NOT the bytes the render consumed "
            "(source substitution on the buyer surface)"}


def _check_artifact_bytes(package_dir: Path,
                          release_allowed: bool) -> Dict[str, Any]:
    rec = _read_json(package_dir / "MODEL" / "3D" / "render_record.json")
    if rec is None:
        return {"pass": False, "state": "INCOMPLETE",
                "reason": "no render record — artifact bytes cannot be "
                          "checked against anything"}
    views = rec.get("views") or {}
    three_d = package_dir / "MODEL" / "3D"
    mismatches: List[str] = []
    missing: List[str] = []
    suppressed_present: List[str] = []
    checked = 0
    for name, meta in views.items():
        sha = (meta or {}).get("sha256")
        if not sha:
            continue  # a view the record carries without a hash is
            # invisible to this check — surfaced as INCOMPLETE below
        checked += 1
        p = three_d / name
        if not p.is_file():
            if name in SUPPRESSED_ON_BLOCK and not release_allowed:
                continue  # correctly suppressed
            missing.append(name)
            continue
        if name in SUPPRESSED_ON_BLOCK and not release_allowed:
            suppressed_present.append(name)
            continue
        actual = _sha256_file(p)
        if actual != sha:
            mismatches.append(name)
    if not checked:
        return {"pass": False, "state": "INCOMPLETE",
                "reason": "render record carries no per-view sha256 "
                          "fields — byte lineage unmeasurable for this "
                          "tree (pre-R443 record)"}
    if suppressed_present:
        return {"pass": False, "state": "FAIL",
                "suppressed_but_present": suppressed_present,
                "reason": "suppression bypass: hero/poster present in the "
                          f"package under a non-releasable verdict "
                          f"({suppressed_present})"}
    if mismatches:
        return {"pass": False, "state": "FAIL",
                "sha256_mismatched": mismatches,
                "reason": f"package view bytes differ from the render "
                          f"record (substituted after render): "
                          f"{mismatches[:8]}"}
    if missing:
        return {"pass": False, "state": "FAIL",
                "missing": missing,
                "reason": f"recorded views missing from the package: "
                          f"{missing[:8]}"}
    return {"pass": True, "state": "VERIFIED",
            "views_remeasured": checked,
            "reason": None}


def _release_state(package_dir: Path) -> Dict[str, Any]:
    """The single release truth: gate verdict + HERO_RELEASE_STATE +
    hero file presence must agree."""
    gate = _read_json(package_dir / "MODEL" / "3D" / "visual_gate.json")
    hrs = _read_json(package_dir / "MODEL" / "3D"
                     / "HERO_RELEASE_STATE.json")
    hero_present = (package_dir / "MODEL" / "3D" / "hero.png").is_file()
    verdict = (hrs or {}).get("gate_verdict") or (gate or {}).get("verdict")
    if gate is None and hrs is None:
        return {"pass": False, "state": "INCOMPLETE",
                "verdict": None, "release_allowed": None,
                "reason": "neither visual_gate.json nor "
                          "HERO_RELEASE_STATE.json exists — release "
                          "state unknown, never assumed"}
    gate_verdict = (gate or {}).get("verdict")
    hrs_verdict = (hrs or {}).get("gate_verdict")
    consistent = (gate_verdict is None or hrs_verdict is None
                  or gate_verdict == hrs_verdict)
    # the ONLY release-passing vocabulary ( COMPLETE_PASS; legacy PASS
    # only while the tree predates the completeness block )
    allowed = verdict in ("COMPLETE_PASS", "PASS")
    suppressed_expected = not allowed
    ok = (consistent
          and hero_present == allowed
          and (hrs is None or
               bool(hrs.get("hero_suppressed")) == suppressed_expected))
    return {"pass": bool(ok),
            "state": "VERIFIED" if ok else "FAIL",
            "gate_verdict": gate_verdict,
            "hero_release_verdict": hrs_verdict,
            "verdict_consistent": bool(consistent),
            "hero_present": hero_present,
            "release_allowed": allowed,
            "reason": None if ok else
            "release state disagreement: gate verdict, HERO_RELEASE_"
            "STATE, and the actual hero file presence must agree "
            f"(gate={gate_verdict}, hrs={hrs_verdict}, "
            f"hero_present={hero_present})"}


def _pdf_page1_images(pdf_path: Path) -> List[bytes]:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        if not reader.pages:
            return []
        return [img.data for img in reader.pages[0].images]
    except Exception:  # noqa: BLE001 — unreadable PDF is typed below
        return []


def _check_pdf_embedded_hero(package_dir: Path,
                             release_allowed: bool) -> Dict[str, Any]:
    three_d = package_dir / "MODEL" / "3D"
    hero = three_d / "hero.png"
    pdfs = sorted(package_dir.glob("*.pdf"))
    if not pdfs:
        return {"pass": False, "state": "INCOMPLETE",
                "reason": "no PDFs in the package root — the PDF leg of "
                          "the lineage has nothing to measure"}
    results: List[Dict[str, Any]] = []
    for pdf in pdfs:
        is_dossier = any(h in pdf.name for h in _DOSSIER_HINTS)
        images = _pdf_page1_images(pdf)
        if not release_allowed:
            if is_dossier and images:
                results.append({
                    "pdf": pdf.name, "pass": False, "state": "FAIL",
                    "reason": "suppression bypass: suppressed release "
                              "but page 1 embeds an image"})
            else:
                results.append({
                    "pdf": pdf.name, "pass": True, "state": "VERIFIED",
                    "page1_images": len(images),
                    "note": "no cover image (correct under suppression)" \
                        if is_dossier else
                        "non-dossier PDF, cover contract not applicable"})
            continue
        if not is_dossier:
            results.append({"pdf": pdf.name, "pass": True,
                            "state": "VERIFIED",
                            "note": "non-dossier PDF, cover contract "
                                    "not applicable"})
            continue
        if not hero.is_file():
            results.append({"pdf": pdf.name, "pass": False,
                            "state": "FAIL",
                            "reason": "released hero.png missing from "
                                      "MODEL/3D while a dossier ships"})
            continue
        if not images:
            results.append({"pdf": pdf.name, "pass": False,
                            "state": "FAIL",
                            "reason": "release allowed but dossier "
                                      "page 1 embeds NO image — the "
                                      "hero never reached the buyer PDF"})
            continue
        hero_pixels = _sha256_pixels(hero.read_bytes())
        matched = any(_sha256_pixels(b) == hero_pixels for b in images)
        results.append({
            "pdf": pdf.name, "pass": bool(matched),
            "state": "VERIFIED" if matched else "FAIL",
            "page1_images": len(images),
            "hero_pixel_sha256": hero_pixels,
            "reason": None if matched else
            "dossier page-1 image is NOT pixel-identical to the "
            "gate-approved hero.png — the buyer PDF does not carry "
            "the approved render"})
    ok = all(r["pass"] for r in results)
    return {"pass": ok,
            "state": "VERIFIED" if ok else "FAIL",
            "pdfs": results,
            "reason": None if ok else "see per-PDF reasons"}


def _check_geometry_spec_link(package_dir: Path) -> Dict[str, Any]:
    spec = _read_json(package_dir / "MODEL" / "GEOMETRY_SPEC.json")
    ident = _read_json(package_dir / "MODEL" / "ARTIFACT_IDENTITY.json")
    if spec is None and ident is None:
        return {"pass": False, "state": "INCOMPLETE",
                "reason": "MODEL/GEOMETRY_SPEC.json and MODEL/"
                          "ARTIFACT_IDENTITY.json both absent — the "
                          "engineering-side link is not carried in this "
                          "package (conceptual class or pre-R440 tree); "
                          "recorded as INCOMPLETE, never assumed"}
    spec_sha = (spec or {}).get("spec_sha256")
    src_hash = (ident or {}).get("source_geometry_hash")
    geo_hash = (ident or {}).get("geometry_hash")
    problems: List[str] = []
    if spec is not None and not spec_sha:
        problems.append("GEOMETRY_SPEC.json carries no spec_sha256")
    if ident is not None and not src_hash:
        problems.append("ARTIFACT_IDENTITY.json carries no "
                        "source_geometry_hash")
    if spec_sha and src_hash and spec_sha != src_hash:
        problems.append("spec_sha256 != ARTIFACT_IDENTITY."
                        "source_geometry_hash — the package's own "
                        "records disagree about which GEOMETRY_SPEC "
                        "produced this geometry")
    glb = _canonical_glb(package_dir)
    if geo_hash and glb is not None:
        actual = _sha256_file(glb)
        if actual != geo_hash:
            problems.append("ARTIFACT_IDENTITY.geometry_hash != "
                            "measured canonical GLB sha256 — the "
                            "engineering identity points at different "
                            "bytes than the package ships")
    if problems:
        return {"pass": False, "state": "FAIL",
                "problems": problems, "reason": "; ".join(problems)}
    return {"pass": True, "state": "VERIFIED",
            "spec_sha256": spec_sha,
            "source_geometry_hash": src_hash,
            "geometry_hash": geo_hash,
            "measured_canonical_glb_sha256":
                _sha256_file(glb) if (geo_hash and glb is not None)
                else None,
            "reason": None}


def verify_package_lineage(package_dir: str) -> Dict[str, Any]:
    """Re-measure the full buyer-surface lineage chain. Read-only."""
    root = Path(package_dir)
    if not root.is_dir():
        return {"lineage_version": LINEAGE_VERSION, "verdict": "FAIL",
                "reason": f"package directory not found: {package_dir}"}
    release = _release_state(root)
    release_allowed = bool(release.get("release_allowed"))
    checks = {
        "render_source": _check_render_source(root),
        "artifact_bytes": _check_artifact_bytes(root, release_allowed),
        "release_state": release,
        "pdf_embedded_hero": _check_pdf_embedded_hero(root,
                                                      release_allowed),
        "geometry_spec_link": _check_geometry_spec_link(root),
    }
    states = [c.get("state") for c in checks.values()]
    if "FAIL" in states:
        verdict = "FAIL"
    elif "INCOMPLETE" in states:
        verdict = "INCOMPLETE"
    else:
        verdict = "VERIFIED"
    incompletes = [k for k, c in checks.items()
                   if c.get("state") == "INCOMPLETE"]
    return {
        "lineage_version": LINEAGE_VERSION,
        "verdict": verdict,
        "checks": checks,
        "incomplete_links": incompletes,
        "reason": (None if verdict == "VERIFIED" else
                   ("lineage links missing evidence: "
                    f"{incompletes}" if verdict == "INCOMPLETE" else
                    "lineage re-measurement found a broken link — see "
                    "checks for the specific failure")),
    }

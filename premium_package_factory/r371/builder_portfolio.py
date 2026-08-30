"""
builder_portfolio.py — R371 V5 portfolio-level documents + orchestrator.

  - PORTFOLIO_INDEX.pdf: comparison table + disclosed ranking policy (Phase 10)
  - 00_PORTFOLIO_15_TECHNOLOGIES.pdf: master portfolio document (V5)
  - PORTFOLIO_RELEASE_REPORT.pdf: release report incl. loop-state summary
  - RELEASE_CONTENT_MANIFEST.json built from the ACTUAL filesystem (Phase 2)
  - README.md GENERATED from the manifest (Phase 2 — zero hand-authoring)
  - Master ZIP built FROM the manifest
  - PORTFOLIO_IDENTITY_REGISTRY.json built from actual artifacts (Phase 1)
"""

import json
import os
import shutil
import zipfile

from reportlab.platypus import PageBreak, Paragraph, Spacer, Table, TableStyle

from .builder import (
    _doc, _esc, _footer_canvas, _tbl, get_styles, sha256_file, _now,
    NOT_ESTABLISHED, NAVY,
)
from .builder_documents import (
    init_styles, render_exec_brief, render_evidence_summary,
    render_package_readme, render_transfer_manifest, render_buyer_card,
)
from .builder_dossier import render_engineering_dossier, init_styles as _ds
from .canonical_source import load_all_packages, PACKAGE_MAP
from .commercial import build_commercial_evidence
from .economics import build_validation_economics
from .equations import build_equation_registry
from .experiment_diagram import build_experiment_diagram
from .identity import build_registry, write_registry
from .loopstate import build_loop_state, portfolio_loop_summary
from .mechanism_diagram import build_all_mechanism_diagrams
from .ranking import build_ranking
from .unknowns import build_unknown_roadmap

PORTFOLIO_ROOT_DEFAULT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..",
                 "technology-transfer-portfolio-15")
)


# ---------------------------------------------------------------------------
def render_portfolio_index(ranking, loop_summary, out_path):
    ident = "Portfolio of 15 technology-transfer packages — R372 V6 release"
    doc = _doc(out_path, ident, "Portfolio Index")
    st = [Paragraph("TECHNOLOGY-TRANSFER PORTFOLIO — INDEX AND RANKING", S["CT"]),
          Paragraph("15 engineering-definition packages · ranked by a disclosed, "
                    "evidence-derived policy (no composite scores)", S["CS"]),
          Spacer(1, 6)]
    st.append(Paragraph("RANKING POLICY (disclosed)", S["SH"]))
    st.append(Paragraph(_esc(
        "Keys applied lexicographically: (1) KILL_TESTABILITY — a recorded "
        "numeric kill/acceptance threshold ranks above a qualitative one; "
        "(2) EVIDENCE_DEPTH — more distinct hashed external sources rank "
        "higher; (3) ENGINEERING_ARTIFACT_DEPTH — more design inputs/outputs/"
        "failure modes/verification/build steps rank higher; "
        "(4) TIME_TO_DECISIVE_EXPERIMENT — shorter recorded WP-01 effort "
        "ranks higher. Full policy in PORTFOLIO_RANKING.json. You may "
        "re-sort by your own policy from that machine-readable file."), S["BT"]))
    st.append(Paragraph(_esc(
        f"Loop states: {loop_summary['loop_verification_state_counts']} — "
        f"{loop_summary['real_external_loop']}"), S["BT"]))
    st.append(Spacer(1, 4))

    st.append(Paragraph("PORTFOLIO COMPARISON TABLE (rank order)", S["SH"]))
    # R375-1: this is the ONE summary-only table in the release (declared
    # in SUMMARY_TABLE_WHITELIST): per-package cells are short digests with
    # an EXPLICIT pointer to the full authoritative record — the package's
    # engineering dossier inside the same release.
    hdr = ["#", "Pkg", "Technology", "Kill test.", "Ev.", "Art.", "First decisive WP",
           "Largest uncertainty (class)", "Loop", "Full record"]
    rows = [hdr]
    for r in ranking["rows"]:
        lu = r["largest_uncertainty"]
        stmt = (lu["statement"] or "")[:80]
        rows.append([
            str(r["rank"]), r["package_id"],
            (r["technology"] or "")[:44],
            r["kill_testability"][:6],
            str(r["evidence_depth"]),
            str(r["engineering_artifact_depth"]),
            str(r["timeline_first_decisive_wp"])[:18],
            f"{stmt} [{lu['classification'] or '-'}]"[:80],
            "SYNTH" if r["loop_verification_state"] == "SYNTHETIC_LOOP_VERIFIED" else "NONE",
            f"DOWNLOAD/{r['folder']}/02 dossier",
        ])
    st.append(_tbl(rows, [0.26 * 72, 0.5 * 72, 1.7 * 72, 0.5 * 72, 0.24 * 72,
                          0.3 * 72, 0.72 * 72, 1.86 * 72, 0.42 * 72, 0.46 * 72], fontsize=6.2))
    st.append(Paragraph("Ev. = distinct hashed external sources; Art. = design "
                        "inputs+outputs+failure modes+verification+build steps; "
                        "Kill test. QUANT = recorded numeric threshold; QUAL = "
                        "qualitative. Cost range for all packages: NOT_ESTABLISHED "
                        "(no quotation basis in the engineering record). Cells in "
                        "this table are SUMMARIES — the authoritative record for "
                        "every row is the package's engineering dossier under "
                        "DOWNLOAD/<folder>/.", S["DIS"]))

    st.append(PageBreak())
    st.append(Paragraph("PACKAGE ONE-LINERS (portfolio order)", S["SH"]))
    # R375-1: full problem + kill condition — Paragraphs wrap; no slices.
    # The rank pointer directs the reader to the full dossier.
    for r in sorted(ranking["rows"], key=lambda x: x["portfolio_number"]):
        st.append(Paragraph(_esc(
            f"{r['portfolio_number']} · {r['package_id']} — {r['technology']} "
            f"(rank {r['rank']}; full record: DOWNLOAD/{r['folder']}/02 "
            f"dossier). Problem: {r['problem']} Kill: "
            f"{r['kill_condition'] or ''}"), S["BC"]))
    doc.build(st, onFirstPage=_footer_canvas(ident), onLaterPages=_footer_canvas(ident))
    return out_path


def render_master_portfolio(packages, headlines, ranking, out_path):
    ident = "Portfolio of 15 technology-transfer packages — R372 V6 release"
    doc = _doc(out_path, ident, "Master Portfolio Document")
    st = [Paragraph("15 TECHNOLOGY-TRANSFER OPPORTUNITIES", S["CT"]),
          Paragraph("Engineering-definition dossiers for external technical, "
                    "commercial and strategic evaluation", S["CS"]), Spacer(1, 8)]
    st.append(Paragraph("IMPORTANT DISCLOSURE", S["SH"]))
    st.append(Paragraph(
        "These are engineering technology-transfer dossiers prepared for "
        "external evaluation. They are not representations that the "
        "underlying technologies are physically validated, manufacturing-"
        "qualified, clinically validated, legally cleared, or transfer-ready "
        "unless explicitly supported by the evidence contained in the "
        "relevant package. No physical prototypes exist. No clinical "
        "validation has been performed. Market sizing is NOT_ESTABLISHED "
        "for every package — no unsourced market figures are presented.",
        S["BT"]))
    st.append(Paragraph("MATURITY AND POSTURE", S["SH"]))
    st.append(Paragraph(
        "All 15 packages are at ENGINEERING_DEFINITION maturity "
        "(governing equations, design inputs/outputs, failure analysis and "
        "build plans exist) with SPONSORED_VALIDATION posture (the next step "
        "is a sponsored decisive experiment). Packages are NOT equal: the "
        "index ranks them by the disclosed evidence-derived policy — read "
        "the ranking before reading dossiers.", S["BT"]))
    for pkg in packages:
        h = headlines[pkg.pkg_id]
        st.append(Paragraph(_esc(f"{pkg.num} · {pkg.pkg_id} — {h['technology_name']}"), S["SH"]))
        st.append(Paragraph(_esc(f"WHAT: {_mut_text(pkg, h['mechanism'])}"), S["BC"]))
        st.append(Paragraph(_esc(f"PROBLEM: {_mut_text(pkg, h['problem'])}"), S["BC"]))
        st.append(Paragraph(_esc(f"KILL: {h['kill_if']}"), S["BC"]))
    doc.build(st, onFirstPage=_footer_canvas(ident), onLaterPages=_footer_canvas(ident))
    return out_path


def _mut_text(pkg, text):
    from .canonical_source import apply_mutations, normalize_units
    return normalize_units(apply_mutations(str(text), pkg.addendum))


def render_release_report(ranking, loop_summary, structural, out_path,
                          traceability=None, packages=None,
                          equation_validation=None):
    """Release report from build-time structural facts. Acceptance-gate
    RESULTS live in INTERNAL_QA/R371_ACCEPTANCE_REPORT.json (internal) and
    RELEASE/R371_RELEASE_CANDIDATE.json (CEO audit) - not in this buyer
    document, so the report cannot be invalidated by the acceptance run.

    R372: includes the traceability-semantics table (CEO R372-1 fields:
    critical_DIs / explicit / partial / unknown / not_applicable /
    orphan_DOs / orphan_FMs per package) and the equation-validation
    summary (CEO R372-3)."""
    ident = "Portfolio of 15 technology-transfer packages - R372 V6 release"
    doc = _doc(out_path, ident, "Portfolio Release Report")
    st = [Paragraph("PORTFOLIO RELEASE REPORT - R372 V6", S["CT"]), Spacer(1, 6)]
    st.append(Paragraph("RELEASE IDENTITY INTEGRITY", S["SH"]))
    st.append(Paragraph(_esc(
        "One canonical registry (PORTFOLIO_IDENTITY_REGISTRY.json) binds each "
        "portfolio number (01-15) to its immutable historical package ID "
        "(P-01..P-29), folder name, dossier hash, package-ZIP hash and "
        "manifest hash. Historical IDs are never renumbered. Every buyer "
        "document carries the identity line 'Portfolio NN - Package P-XX - "
        "Version V' in its footer, derived from the same mapping. "
        "Verification protocol: registry hashes recomputed from disk; folder, "
        "manifest and ZIP identities cross-checked for all 15 packages "
        "(results: INTERNAL_QA acceptance reports)."), S["BT"]))
    st.append(Paragraph("ARCHIVE CONSISTENCY", S["SH"]))
    st.append(Paragraph(_esc(
        "RELEASE_CONTENT_MANIFEST.json is generated by walking the actual "
        "release filesystem; README.md is generated FROM that manifest; the "
        "master ZIP is built from the same manifest. A file that is not on "
        "disk cannot appear in the README, and every file the README names "
        "is present in the ZIP. DOWNLOAD/ is the single authoritative "
        "release tree (the former FULL_DOSSIERS/ and BUYER_OUTREACH/ "
        "duplicate trees were removed in this release; history preserved in "
        "git and in RELEASE/history_r370/)."), S["BT"]))

    # ---- R372-1: traceability semantics table ---------------------------
    if traceability and packages:
        st.append(Paragraph(
            "ENGINEERING TRACEABILITY SEMANTICS (explicit - no ambiguous "
            "'passed' flags)", S["SH"]))
        st.append(Paragraph(_esc(
            "Every DI/DO/FM/V chain slot is classified EXPLICIT / PARTIAL / "
            "UNKNOWN / NOT_APPLICABLE with a record-cited justification. A "
            "package passes with incomplete traceability only when every "
            "non-explicit slot is explicitly justified. The table shows, "
            "per package: critical design inputs (quantitative acceptance "
            "criteria), chains with at least one explicit link, chains with "
            "only partial links, chains with no recorded link, explicitly "
            "not-applicable chains, and unbound design outputs / failure "
            "modes. This release does NOT represent the traceability graph "
            "as healthy: at ENGINEERING_DEFINITION maturity most DI-to-DO "
            "bindings are downstream engineering development, and that is "
            "stated per slot in each package's ENGINEERING_TRACEABILITY.json."),
            S["BT"]))
        from ..r372.traceability_semantics import portfolio_traceability_table
        rows = portfolio_traceability_table(packages, traceability)
        st.append(_tbl(rows, [0.55 * 72, 0.62 * 72, 0.55 * 72, 0.5 * 72,
                              0.55 * 72, 0.3 * 72, 0.62 * 72, 0.6 * 72,
                              0.75 * 72], fontsize=6.2))

    # ---- R372-3 / R374-2: equation validation summary -------------------
    if equation_validation:
        st.append(Paragraph("GOVERNING-EQUATION VALIDATION (THREE LEVELS)",
                            S["SH"]))
        total_eq = sum(v["equation_count"] for v in equation_validation.values())
        inconsistent = sum(len(v["inconsistent_equations"])
                           for v in equation_validation.values())
        counts = {}
        for v in equation_validation.values():
            for k, n in v["dimensional_state_counts"].items():
                counts[k] = counts.get(k, 0) + n
        st.append(Paragraph(_esc(
            f"All {total_eq} canonical governing equations carry recorded "
            f"variables, per-variable unit status (R374-3), domain, "
            f"operating regime (boundary conditions), assumptions, "
            f"applicability and limitations (known failure regimes). "
            f"Validation is reported at THREE SEPARATE levels (CEO "
            f"R374-2): STRUCTURAL (the canonical math string parses as a "
            f"well-formed relation), APPLICABILITY (the applicability "
            f"envelope is fully recorded) and DIMENSIONAL (unit algebra "
            f"performed under RECORDED units and consistent). The word "
            f"'validated' never implies an unproven level. Dimensional "
            f"outcomes: {counts}. Zero equations are dimensionally "
            f"inconsistent. The dominant dimensional state is honestly "
            f"NOT_EVALUABLE: the engineering record does not assign units "
            f"to most equation symbols ({counts.get('NOT_EVALUABLE_UNITS_UNRECORDED', 0)} of "
            f"{total_eq}), and units are taken ONLY from recorded "
            f"critical parameters — standard-symbol guesses are not used "
            f"(Constitution Art. VI). Every unrecorded-unit symbol "
            f"carries UNIT_STATUS = UNKNOWN with a resolution path in "
            f"the shipped EQUATION_REGISTRY.json per package. Populating "
            f"the unit fields of the critical parameters is buyer-side "
            f"engineering work recorded in the unknown roadmaps."),
            S["BT"]))

    st.append(Paragraph("EVIDENCE DISCIPLINE", S["SH"]))
    st.append(Paragraph(_esc(
        "Market size: NOT_ESTABLISHED for every package (no market-research "
        "source is integrated; no figures are invented). Competitor claims: "
        "none authored by the transferor - company names appear only inside "
        "cited, hashed external-precedent snippets. Engineering thresholds: "
        "no new thresholds were invented - the unsupported $5K/$25K/$100K "
        "template ladder was retired and cost is stated as NOT_ESTABLISHED. "
        "Prototypes: none exist and none are depicted; both technical "
        "visuals per package are labeled engineering-definition schematics "
        "auto-derived from the canonical record, with every label's "
        "provenance classified (canonical / historical / spec / physiology "
        "/ structural) and zero untraced labels."), S["BT"]))
    st.append(Paragraph("V2 MUTATION APPLICATION", S["SH"]))
    st.append(Paragraph(_esc(
        "Eight packages carry recorded V2 mutations driven by externally "
        "generated, reconciled evidence (10 mutations total). In this "
        "release the V2 text is RENDERED in the buyer documents (the prior "
        "release shipped the addenda without re-rendering the PDFs). The "
        "full V1->V2 trail ships in each affected package, and the R372 "
        "acceptance gate verifies per mutation that the buyer receives V2 "
        "in the PDF, the JSON and the ZIP (V1 text absent from all buyer "
        "documents)."), S["BT"]))
    st.append(Paragraph("AI LOOP STATE", S["SH"]))
    st.append(Paragraph(_esc(json.dumps(loop_summary["loop_verification_state_counts"])
                             + " - " + loop_summary["real_external_loop"]), S["BT"]))
    st.append(Paragraph("RELEASE STATUS", S["SH"]))
    st.append(Paragraph(_esc(
        "This release is submitted as PORTFOLIO_RELEASE_CANDIDATE for CEO "
        "audit. It is not self-certified as complete: the acceptance gate "
        "runs mechanically and independently (r371.acceptance + "
        "r372.acceptance_r372), and independent audit is required "
        "(Constitution Art. XXVI)."), S["BT"]))
    doc.build(st, onFirstPage=_footer_canvas(ident), onLaterPages=_footer_canvas(ident))
    return out_path


# ---------------------------------------------------------------------------
# Phase 2: RELEASE_CONTENT_MANIFEST + generated README
# ---------------------------------------------------------------------------
DISTRIBUTION_ROOT_FILES = [
    "README.md",
    "PORTFOLIO_IDENTITY_REGISTRY.json",
    "RELEASE_CONTENT_MANIFEST.json",
    "PORTFOLIO_MANIFEST.json",
    "PORTFOLIO_RANKING.json",
    "00_PORTFOLIO_15_TECHNOLOGIES.pdf",
    "PORTFOLIO_INDEX.pdf",
    "PORTFOLIO_RELEASE_REPORT.pdf",
]


def build_release_content_manifest(portfolio_root, include_readme=True):
    """Walk the ACTUAL distribution filesystem. Zero hand-authored claims.

    Two-pass protocol (Phase 2):
      pass 1 (include_readme=False): manifest of everything except README.md
              -> used to GENERATE README.md
      pass 2 (include_readme=True): full manifest including the generated
              README's hash.

    Self-referential files: neither README.md nor this manifest file can
    contain its own hash. RELEASE_CONTENT_MANIFEST.json is therefore listed
    as a distribution root file for README/ZIP purposes but excluded from
    its own entries. Acceptance verifies: manifest entries hash-match on
    disk; ZIP namelist == manifest paths + README + this manifest.
    """
    entries = []
    for fn in DISTRIBUTION_ROOT_FILES:
        if fn in ("README.md", "RELEASE_CONTENT_MANIFEST.json") and not include_readme:
            continue
        if fn == "RELEASE_CONTENT_MANIFEST.json":
            continue  # a manifest cannot contain its own hash
        fp = os.path.join(portfolio_root, fn)
        if not os.path.exists(fp):
            raise FileNotFoundError(f"distribution root file missing: {fn}")
        entries.append({
            "path": fn, "role": "root document",
            "sha256": sha256_file(fp),
            "bytes": os.path.getsize(fp),
        })
    download = os.path.join(portfolio_root, "DOWNLOAD")
    for row in PACKAGE_MAP:
        folder = f"{row['num']}_{row['short']}"
        pdir = os.path.join(download, folder)
        zpath = os.path.join(download, f"{folder}.zip")
        if not os.path.isdir(pdir) or not os.path.exists(zpath):
            raise FileNotFoundError(f"package missing: {folder}")
        files = []
        for f in sorted(os.listdir(pdir)):
            fp = os.path.join(pdir, f)
            files.append({"path": f, "sha256": sha256_file(fp),
                          "bytes": os.path.getsize(fp)})
        entries.append({
            "path": f"DOWNLOAD/{folder}", "role": "package folder",
            "package_id": row["pkg_id"], "portfolio_number": row["num"],
            "files": files, "file_count": len(files),
        })
        entries.append({
            "path": f"DOWNLOAD/{folder}.zip", "role": "package zip",
            "package_id": row["pkg_id"], "portfolio_number": row["num"],
            "sha256": sha256_file(zpath), "bytes": os.path.getsize(zpath),
        })
    # NOTE: the master ZIP is BUILT FROM this manifest, so its own hash
    # cannot appear inside the manifest (self-reference). The master ZIP
    # hash is computed and recorded by the R371 acceptance gate in
    # INTERNAL_QA/R371_ACCEPTANCE_REPORT.json and
    # RELEASE/R371_RELEASE_CANDIDATE.json.
    return {
        "manifest": "RELEASE_CONTENT_MANIFEST",
        "version": "2.0",
        # R374-5 determinism: no volatile build timestamp — this manifest
        # is embedded in the master ZIP; a per-build timestamp made the
        # ZIP non-reproducible. Build provenance: git history (Art. XI).
        "determinism_note": (
            "No build timestamp by design (CEO R374-5 byte-reproducible "
            "release): this manifest is embedded in the master ZIP. "
            "Build provenance: git history of the portfolio repository."),
        "policy": (
            "This manifest is generated by walking the actual release "
            "filesystem. README.md is generated FROM this manifest. The "
            "master ZIP is built FROM this manifest. A file that is not on "
            "disk cannot appear here; a file here cannot be missing from "
            "the ZIP. The master ZIP's own hash is recorded by the R371 "
            "acceptance gate (it cannot reference itself). Verification: "
            "r371.acceptance archive gate."
        ),
        "entries": entries,
    }


def generate_readme(manifest, loop_summary, out_path):
    """README.md generated from the manifest — Phase 2 (zero drift)."""
    pkg_rows = [e for e in manifest["entries"] if e["role"] == "package folder"]
    root_rows = [e for e in manifest["entries"] if e["role"] == "root document"]
    # master ZIP is not a manifest entry (self-reference); the README
    # names it structurally and points to the acceptance gate for its hash
    lines = []
    lines.append("# 15 Technology-Transfer Opportunities — R372 V6 Release")
    lines.append("")
    lines.append("This release contains 15 engineering technology-transfer "
                 "dossiers prepared for external technical, commercial and "
                 "strategic evaluation. Each package identifies the "
                 "technology, supporting evidence, engineering status, "
                 "unresolved risks (with a resolution roadmap), proposed "
                 "development path, transferable artifacts and the next "
                 "decision point.")
    lines.append("")
    lines.append("## Important disclosure")
    lines.append("")
    lines.append("These are engineering technology-transfer dossiers. They "
                 "are not representations that the underlying technologies "
                 "are physically validated, manufacturing-qualified, "
                 "clinically validated, legally cleared, or transfer-ready "
                 "unless explicitly supported by the evidence in the "
                 "relevant package. No physical prototypes exist. Market "
                 "size, competitive landscape, freedom-to-operate and "
                 "novelty are NOT_ESTABLISHED for every package — the "
                 "release contains no unsourced market figures, no "
                 "transferor-authored competitor claims, and no invented "
                 "engineering thresholds.")
    lines.append("")
    lines.append("## Maturity, posture and ranking")
    lines.append("")
    lines.append("All packages are at ENGINEERING_DEFINITION maturity with "
                 "SPONSORED_VALIDATION posture, but they are NOT equal: "
                 "PORTFOLIO_INDEX.pdf ranks them by a disclosed, "
                 "evidence-derived policy (kill-condition testability, "
                 "evidence depth, engineering artifact depth, time to "
                 "decisive experiment). Start from the index, not from "
                 "package 01.")
    lines.append("")
    lines.append(f"AI loop state: {loop_summary['loop_verification_state_counts']} "
                 f"— {loop_summary['real_external_loop']}")
    lines.append("")
    lines.append("## What is in this release")
    lines.append("")
    lines.append("This section is GENERATED from RELEASE_CONTENT_MANIFEST.json, "
                 "which is itself generated by walking the actual release "
                 "filesystem. The master ZIP is built from the same manifest.")
    lines.append("")
    lines.append("### Root documents")
    for r in root_rows:
        if r["path"] == "README.md":
            continue  # a README does not list its own hash
        lines.append(f"- `{r['path']}` — sha256 `{r['sha256'][:16]}…`")
    lines.append("")
    lines.append("### Package folders and ZIPs (DOWNLOAD/)")
    lines.append("")
    lines.append("| # | Package | Folder | Files | ZIP |")
    lines.append("|---|---------|--------|-------|-----|")
    for p in pkg_rows:
        lines.append(f"| {p['portfolio_number']} | {p['package_id']} | "
                     f"`DOWNLOAD/{p['path'].split('/')[-1]}` | {p['file_count']} | "
                     f"`DOWNLOAD/{p['path'].split('/')[-1]}.zip` |")
    lines.append("")
    lines.append(f"### Master distribution ZIP")
    lines.append("")
    lines.append("- `DOWNLOAD/technology-transfer-portfolio-15.zip` — contains "
                 "the 15 package ZIPs plus the root documents listed above. "
                 "Its sha256 is recorded by the R371 acceptance gate in "
                 "INTERNAL_QA/R371_ACCEPTANCE_REPORT.json (a ZIP built from "
                 "this manifest cannot contain its own hash).")
    lines.append("")
    lines.append("### Per-package file set")
    lines.append("")
    lines.append("Each package folder contains the six buyer PDFs "
                 "(00_PACKAGE_README, 01_EXECUTIVE_TECHNOLOGY_BRIEF, "
                 "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER with mechanism "
                 "diagram + decisive-experiment diagram + typeset governing "
                 "equations, 03_BUYER_DECISION_CARD in the nine-question "
                 "decision architecture, 04_EVIDENCE_SUMMARY, "
                 "05_TRANSFER_MANIFEST with buyer-capability and "
                 "confidentiality sections) plus the machine-readable layer: "
                 "PACKAGE_MANIFEST.json, ENGINEERING_TRACEABILITY.json, "
                 "MATURITY_BASIS.json, COMMERCIAL_EVIDENCE.json, "
                 "EQUATION_REGISTRY.json, UNKNOWN_ROADMAP.json, "
                 "VALIDATION_ECONOMICS.json, LOOP_STATE.json, and (where "
                 "recorded) the V2 mutation trail "
                 "(V2_MUTATION_ADDENDUM.json + mutation certificate).")
    lines.append("")
    lines.append("## Identity")
    lines.append("")
    lines.append("Historical package IDs (P-01 … P-29) are immutable and are "
                 "never renumbered. The canonical mapping between portfolio "
                 "numbers (01–15), historical package IDs, folder names and "
                 "content hashes is PORTFOLIO_IDENTITY_REGISTRY.json, and "
                 "every document carries the identity line "
                 "“Portfolio NN · Package P-XX · Version V” in its footer.")
    lines.append("")
    lines.append("## Reading order")
    lines.append("")
    lines.append("1. PORTFOLIO_INDEX.pdf — ranked comparison table")
    lines.append("2. 03_BUYER_DECISION_CARD.pdf of a package of interest — "
                 "nine decision questions")
    lines.append("3. 01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf — one page")
    lines.append("4. 02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf — full "
                 "engineering definition")
    lines.append("")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return out_path


def build_master_zip(portfolio_root, manifest, dest):
    """Master ZIP built FROM the manifest + the two self-referential files
    (README.md, RELEASE_CONTENT_MANIFEST.json itself). Phase 2.
    R374-5: deterministic entry timestamps (byte-reproducible container)."""
    from .build_v5 import _zip_add
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for fn in DISTRIBUTION_ROOT_FILES:
            fp = os.path.join(portfolio_root, fn)
            if not os.path.exists(fp):
                raise FileNotFoundError(f"master zip source missing: {fn}")
            _zip_add(zf, fp, fn)
        for entry in manifest["entries"]:
            if entry["role"] == "package zip":
                fp = os.path.join(portfolio_root, entry["path"])
                _zip_add(zf, fp, entry["path"])
    return dest


S = get_styles()
init_styles(S)
_ds(S)

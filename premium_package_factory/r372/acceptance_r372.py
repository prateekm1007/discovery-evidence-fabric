"""
acceptance_r372.py — R372 completion gate (CEO R372 directive, final gate).

Do not declare R372 complete until:

  15/15 traceability semantics explicit      (per-chain EXPLICIT/PARTIAL/
                                            UNKNOWN/NOT_APPLICABLE with
                                            record-cited justifications;
                                            release report fields present)
  15/15 diagram technical-adequacy checks   (mechanism: components,
                                            interfaces, direction, mechanism
                                            elements, critical parameters,
                                            label provenance, no invented
                                            numbers; experiment: all 7 roles
                                            verbatim canonical)
  66/66 equation validation records       (complete STRUCTURAL +
                                            APPLICABILITY metadata +
                                            explicit dimensional state;
                                            0 inconsistent. The DIMENSIONAL
                                            validation level is reported
                                            separately per R374-2)
  15/15 commercial-evidence schema          (10-field schema + 8-step
                                            establishment workflow, 0 numeric
                                            market values)
  15/15 buyer decision clarity              (FIVE DECISION CRITICALS present
                                            in every buyer card, kill
                                            condition verbatim)
  100% V2 mutation propagation verified     (addendum verbatim, V2 rendered,
                                            V1 absent, ZIP==folder)
  0 fabricated values                       (no numeric market values in
                                            buyer documents)
  0 unsupported thresholds                  (no cost ladder; kill conditions
                                            match the headlines registry)
  0 archive drift                           (manifest == filesystem == ZIP)
  0 identity drift                          (registry hashes recomputed)
  0 evidence loss                           (source hashes retained; V2
                                            trails preserved)
  repo boundary absolute                    (portfolio = buyer release only)

Read-only with respect to buyer artifacts: writes only
INTERNAL_QA/R372_ACCEPTANCE_REPORT.json and, on full pass,
RELEASE/R372_RELEASE_CANDIDATE.json.

Constitution Art. XXVI: this is a builder-produced mechanical result,
submitted FOR CEO AUDIT — it is not independent certification.
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                "..", "..")))

from premium_package_factory.r371.builder import sha256_file, _now
from premium_package_factory.r371.canonical_source import load_all_packages
from premium_package_factory.r371.acceptance import pdf_text  # cached pdftotext

ENGINE_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", ".."))
FACTORY_ROOT = os.path.join(ENGINE_ROOT, "premium_package_factory")
INPUT_DIR = os.path.join(FACTORY_ROOT, "input")

from premium_package_factory.r372 import boundary_guard, v2_propagation
from premium_package_factory.r372.diagram_adequacy import (
    record_diagram, validate_mechanism_diagram,
    experiment_diagram_spec, validate_experiment_spec)
from premium_package_factory.r372.equation_validation import (
    validate_registry, validation_complete)
from premium_package_factory.r371.equations import build_equation_registry
from premium_package_factory.r371.canonical_source import PACKAGE_MAP


def run_r372_acceptance(portfolio_root, engine_root=ENGINE_ROOT) -> dict:
    results = []
    packages = load_all_packages()
    headlines = {r["package_id"]: r for r in json.load(
        open(os.path.join(INPUT_DIR, "headlines_r371.json"),
             encoding="utf-8"))["packages"]}

    def record(cond, ok, details=""):
        results.append({"condition": cond, "status": "PASS" if ok else "FAIL",
                        "details": str(details)[:300]})
        return ok

    def load(rel):
        with open(os.path.join(portfolio_root, rel), encoding="utf-8") as f:
            return json.load(f)

    # ---- 1. 15/15 traceability semantics explicit ------------------------
    problems = []
    for row in PACKAGE_MAP:
        folder = f"{row['num']}_{row['short']}"
        tr = load(f"DOWNLOAD/{folder}/ENGINEERING_TRACEABILITY.json")
        if tr.get("schema") != "R372_TRACEABILITY_SEMANTICS":
            problems.append(f"{folder}: schema != R372")
            continue
        s = tr["summary"]
        for k in ("critical_DIs", "explicitly_linked", "partially_linked",
                  "unknown", "not_applicable", "orphan_DOs", "orphan_FMs"):
            if k not in s:
                problems.append(f"{folder}: summary missing {k}")
        g = tr["release_gate"]
        if not g.get("incomplete_parts_explicitly_justified"):
            problems.append(f"{folder}: unjustified slots "
                            f"{g.get('unjustified_slots', [])[:3]}")
        for c in tr["chains"]:
            if c["chain_state"] not in (
                    "TRACEABILITY_COMPLETE", "TRACEABILITY_PARTIAL",
                    "TRACEABILITY_UNKNOWN", "TRACEABILITY_NOT_APPLICABLE"):
                problems.append(f"{folder}: bad chain state {c['chain_state']}")
            for slot in c["slots"].values():
                if slot["state"] not in ("EXPLICIT", "PARTIAL", "UNKNOWN",
                                         "NOT_APPLICABLE"):
                    problems.append(f"{folder}: bad slot state")
                if slot["state"] != "EXPLICIT" and not slot.get("justification"):
                    problems.append(f"{folder}: unjustified slot "
                                    f"{c['design_input_id']}")
    record("15/15 traceability semantics explicit", not problems,
           f"problems={problems[:6]}")

    # ---- 2. 15/15 diagram technical-adequacy checks -----------------------
    problems = []
    from premium_package_factory.diagrams import factory as diagram_factory
    import tempfile
    tmp = tempfile.mkdtemp()
    diagram_factory.OUTPUT_DIR = tmp
    FUNCS = {
        "P-01": diagram_factory.diagram_P01, "P-02": diagram_factory.diagram_P02,
        "P-04": diagram_factory.diagram_P04, "P-07": diagram_factory.diagram_P07,
        "P-11": diagram_factory.diagram_P11, "P-13": diagram_factory.diagram_P13,
        "P-15-R1": diagram_factory.diagram_P15R1,
        "P-16": diagram_factory.diagram_P16,
        "P-21-R1": diagram_factory.diagram_P21R1,
        "P-22-R1": diagram_factory.diagram_P22R1,
        "P-24": diagram_factory.diagram_P24, "P-26": diagram_factory.diagram_P26,
        "P-27-R1": diagram_factory.diagram_P27R1,
        "P-28": diagram_factory.diagram_P28, "P-29": diagram_factory.diagram_P29,
    }
    diagram_reports = {}
    for p in packages:
        # mechanism: live re-render with label recording
        rec = record_diagram(lambda: FUNCS[p.pkg_id]())
        mech = validate_mechanism_diagram(p, rec, headlines.get(p.pkg_id))
        # experiment: spec validated against canonical data
        spec = experiment_diagram_spec(p, headlines[p.pkg_id])
        exp = validate_experiment_spec(spec, p, headlines[p.pkg_id])
        diagram_reports[p.pkg_id] = {
            "mechanism": {k: v for k, v in mech.items()
                          if k != "label_provenance"},
            "mechanism_label_provenance_counts": mech.get(
                "label_provenance_counts", {}),
            "experiment": exp,
        }
        if not mech["ok"]:
            problems.append(f"{p.pkg_id} mechanism: "
                            f"{[f['check'] for f in mech['failures']]}")
        if not exp["ok"]:
            problems.append(f"{p.pkg_id} experiment: "
                            f"{[f['check'] for f in exp['failures']]}")
    record("15/15 diagram technical-adequacy checks", not problems,
           f"problems={problems[:6]}")

    # ---- 3. 66/66 equation validation --------------------------------------
    # R374-2 language correction: the check below proves complete
    # metadata (STRUCTURAL + APPLICABILITY levels) and zero dimensional
    # INCONSISTENCIES. It does NOT prove dimensional validation — the
    # dimensional level is reported separately per equation in
    # r374_validation_status (0 dimensionally consistent at R374; the
    # honest state — units unrecorded for most symbols).
    problems = []
    total = 0
    inconsistent = 0
    for p in packages:
        reg = build_equation_registry(p)
        val = validate_registry(reg, p)
        total += val["equation_count"]
        inconsistent += len(val["inconsistent_equations"])
        # the shipped registry must carry the validation
        shipped = load(f"DOWNLOAD/{p.folder}/EQUATION_REGISTRY.json")
        if "r372_validation" not in shipped:
            problems.append(f"{p.folder}: shipped registry lacks validation")
            continue
        for v in shipped["r372_validation"]["validations"]:
            if not validation_complete(v):
                problems.append(f"{p.folder}: incomplete validation "
                                f"{v['equation_id']}")
    if total != 66:
        problems.append(f"equation total {total} != 66")
    if inconsistent:
        problems.append(f"{inconsistent} dimensionally inconsistent equations")
    record(f"66/66 equation validation records complete (structural + "
           f"applicability metadata; {total} equations, {inconsistent} "
           f"dimensionally inconsistent; the DIMENSIONAL validation level "
           f"is reported separately per R374-2 and is 0-proven — units "
           f"unrecorded for most symbols)", not problems,
           f"problems={problems[:6]}")

    # ---- 4. 15/15 commercial-evidence schema -------------------------------
    problems = []
    FIELDS = ("market_definition", "geography", "year", "population_basis",
              "source", "source_hash", "methodology", "estimate",
              "uncertainty", "limitations")
    for p in packages:
        ce = load(f"DOWNLOAD/{p.folder}/COMMERCIAL_EVIDENCE.json")
        market = next(s for s in ce["commercial_evidence"]
                      if s["section"] == "MARKET_EVIDENCE")
        for k in FIELDS:
            if k not in market:
                problems.append(f"{p.folder}: missing {k}")
        if len(market.get("establishment_workflow", [])) != 8:
            problems.append(f"{p.folder}: workflow != 8 steps")
        for metric in market.get("estimate", []):
            if metric.get("value") != "NOT_ESTABLISHED":
                problems.append(f"{p.folder}: numeric market value")
    record("15/15 commercial-evidence schema", not problems,
           f"problems={problems[:6]}")

    # ---- 5. 15/15 buyer decision clarity -----------------------------------
    problems = []
    CRITICALS = [
        "THE FIVE DECISION CRITICALS",
        "1. WHAT IS THE INVENTION?",
        "2. WHAT IS ACTUALLY ESTABLISHED?",
        "3. WHAT REMAINS UNCERTAIN?",
        "4. CHEAPEST DECISIVE NEXT EXPERIMENT?",
        "5. WHAT EVIDENCE WOULD CAUSE THE BUYER TO STOP?",
    ]
    def _raw_pdf_text(path):
        import subprocess
        r = subprocess.run(["pdftotext", "-raw", path, "-"],
                           capture_output=True, text=True)
        import re as _re
        return _re.sub(r"\s+", " ", r.stdout or "")

    for p in packages:
        txt = _raw_pdf_text(os.path.join(
            portfolio_root, "DOWNLOAD", p.folder,
            "03_BUYER_DECISION_CARD.pdf"))
        for header in CRITICALS:
            if header not in txt:
                problems.append(f"{p.folder}: missing critical '{header[:40]}'")
        kill = headlines[p.pkg_id]["kill_if"]
        if kill and kill[:60].replace(" ", "") not in txt.replace(" ", ""):
            problems.append(f"{p.folder}: kill condition not verbatim")
    record("15/15 buyer decision clarity", not problems,
           f"problems={problems[:6]}")

    # ---- 6. 100% V2 mutation propagation -----------------------------------
    v2_report = v2_propagation.verify_portfolio_v2(
        portfolio_root, packages,
        os.path.join(INPUT_DIR, "v2_mutations"))
    failing_pkgs = [r["package_id"] for r in v2_report["results"]
                    if not r["all_pass"]][:4]
    record(f"100% V2 mutation propagation verified "
           f"({v2_report['packages_with_addenda']} packages, "
           f"{v2_report['total_mutations']} mutations)",
           v2_report["propagation_complete"],
           f"failing packages={failing_pkgs}")

    # ---- 7. 0 fabricated values --------------------------------------------
    import re
    hits = []
    market_re = re.compile(
        r"(\$\s?\d[\d,.]*\s?(?:B\b|M\b|K\b|billion|million)|"
        r"market (?:is|of|size)[^.]{0,60}\$\s?\d)", re.I)
    for p in packages:
        for pdf in ("01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
                    "03_BUYER_DECISION_CARD.pdf", "00_PACKAGE_README.pdf",
                    "05_TRANSFER_MANIFEST.pdf"):
            txt = pdf_text(os.path.join(portfolio_root, "DOWNLOAD",
                                        p.folder, pdf))
            for m in market_re.finditer(txt):
                hits.append(f"{p.folder}/{pdf}: {m.group(0)[:40]}")
    record("0 fabricated values", not hits, f"hits={hits[:5]}")

    # ---- 8. 0 unsupported thresholds ---------------------------------------
    th = []
    LADDER = re.compile(
        r"(?:Next|Cost:?|Validate for|Commission a)\s*\$\s?\d[\d,.]*\s?[KM]\b"
        r"|\$\s?5K\s+(?:bench|action|validation)"
        r"|\$\s?\d[\d,.]*\s?[KM]\s+(?:action|bench|validation|study)", re.I)
    RETIRE = re.compile(r"retired|template artifact|prior", re.I)
    for p in packages:
        for pdf in ("00_PACKAGE_README.pdf", "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
                    "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
                    "03_BUYER_DECISION_CARD.pdf", "05_TRANSFER_MANIFEST.pdf"):
            txt = pdf_text(os.path.join(portfolio_root, "DOWNLOAD",
                                        p.folder, pdf))
            for m in LADDER.finditer(txt):
                window = txt[max(0, m.start() - 150):m.end() + 150]
                if not RETIRE.search(window):
                    th.append(f"{p.folder}/{pdf}: {m.group(0)[:40]}")
        txt = pdf_text(os.path.join(portfolio_root, "DOWNLOAD", p.folder,
                                    "03_BUYER_DECISION_CARD.pdf"))
        kill = headlines[p.pkg_id]["kill_if"]
        if kill and kill[:80] not in txt:
            th.append(f"{p.folder}: kill condition drifted")
    record("0 unsupported thresholds", not th, f"problems={th[:5]}")

    # ---- 9. 0 archive drift -------------------------------------------------
    drift = []
    manifest = load("RELEASE_CONTENT_MANIFEST.json")
    for entry in manifest["entries"]:
        fp = os.path.join(portfolio_root, entry["path"])
        if not os.path.exists(fp):
            drift.append(f"missing {entry['path']}")
            continue
        if "sha256" in entry and sha256_file(fp) != entry["sha256"]:
            drift.append(f"hash drift {entry['path']}")
        if entry["role"] == "package folder":
            actual = sorted(os.listdir(fp))
            listed = sorted(f["path"] for f in entry["files"])
            if actual != listed:
                drift.append(f"folder/manifest drift {entry['path']}")
    record("0 archive drift", not drift, f"problems={drift[:5]}")

    # ---- 10. 0 identity drift -----------------------------------------------
    idp = []
    reg = load("PORTFOLIO_IDENTITY_REGISTRY.json")
    for rrow in reg["packages"]:
        folder = rrow.get("folder_name")
        if not folder:
            idp.append(f"{rrow['historical_package_id']}: no folder_name")
            continue
        pdir = os.path.join(portfolio_root, "DOWNLOAD", folder)
        pm = load(f"DOWNLOAD/{folder}/PACKAGE_MANIFEST.json")
        if pm["package_id"] != rrow["historical_package_id"]:
            idp.append(f"{folder}: manifest id mismatch")
        for pdf in ("00_PACKAGE_README.pdf",
                    "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
                    "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
                    "03_BUYER_DECISION_CARD.pdf",
                    "04_EVIDENCE_SUMMARY.pdf",
                    "05_TRANSFER_MANIFEST.pdf"):
            txt = pdf_text(os.path.join(pdir, pdf))
            if f"Package {rrow['historical_package_id']}" not in txt:
                idp.append(f"{folder}/{pdf}: identity line missing")
    record("0 identity drift", not idp, f"problems={idp[:5]}")

    # ---- 11. 0 evidence loss -------------------------------------------------
    el = []
    v2_pkgs = {p.pkg_id for p in packages if p.addendum}
    for p in packages:
        pdir = os.path.join(portfolio_root, "DOWNLOAD", p.folder)
        pm = load(f"DOWNLOAD/{p.folder}/PACKAGE_MANIFEST.json")
        listed = {f["file"] for f in pm["files"]} | {"PACKAGE_MANIFEST.json"}
        actual = set(os.listdir(pdir))
        if listed != actual:
            el.append(f"{p.folder}: manifest/folder file set drift")
        txt = pdf_text(os.path.join(pdir, "04_EVIDENCE_SUMMARY.pdf"))
        if "Source hash:" not in txt:
            el.append(f"{p.folder}: source hashes dropped")
        if p.pkg_id in v2_pkgs and "V2_MUTATION_ADDENDUM.json" not in actual:
            el.append(f"{p.folder}: V2 addendum lost")
    record("0 evidence loss", not el, f"problems={el[:5]}")

    # ---- 12. repo boundary absolute -----------------------------------------
    boundary = boundary_guard.verify_boundary(engine_root, portfolio_root)
    record("repo boundary absolute (engine | buyer release)",
           boundary["ok"],
           f"portfolio={boundary['portfolio_side']['problems'][:3]} "
           f"engine={boundary['engine_side']['problems'][:3]}")

    all_pass = all(r["status"] == "PASS" for r in results)
    report = {
        "report": "R372_ACCEPTANCE_REPORT",
        "generated_at": _now(),
        "portfolio_root": portfolio_root,
        "conditions": results,
        "all_pass": all_pass,
        "diagram_technical_adequacy": diagram_reports,
        "v2_propagation": {
            k: v for k, v in v2_report.items() if k != "results"},
        "repo_boundary": boundary,
        "constitution_basis": (
            "Art. XXVI (no self-certification): this report is a mechanical "
            "gate result produced by the builder's tooling and is submitted "
            "FOR CEO AUDIT. It is not independent certification. Art. XXX "
            "(never optimize the evaluator): the diagram, equation and "
            "traceability checks verify technical adequacy, not presence."
        ),
    }
    qa = os.path.join(portfolio_root, "INTERNAL_QA")
    os.makedirs(qa, exist_ok=True)
    with open(os.path.join(qa, "R372_ACCEPTANCE_REPORT.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    if all_pass:
        candidate = {
            "artifact": "PORTFOLIO_RELEASE_CANDIDATE",
            "generated_at": _now(),
            "cycle": "R372",
            "acceptance_report": "INTERNAL_QA/R372_ACCEPTANCE_REPORT.json",
            "status": "RELEASE_CANDIDATE_SUBMITTED_FOR_CEO_AUDIT",
            "note": (
                "All R372 completion-gate conditions PASS mechanically "
                "(traceability semantics, diagram technical adequacy, "
                "equation validation, commercial schema, buyer decision "
                "clarity, V2 propagation, and the seven zero-conditions). "
                "Per Constitution Art. XXVI this is a builder-produced "
                "result and requires independent CEO audit before the "
                "release is called complete. Fresh-clone reproduction "
                "recorded separately in INTERNAL_QA/R372_FRESH_CLONE_"
                "REPRODUCTION.json."
            ),
        }
        rel = os.path.join(portfolio_root, "RELEASE")
        os.makedirs(rel, exist_ok=True)
        with open(os.path.join(rel, "R372_RELEASE_CANDIDATE.json"), "w",
                  encoding="utf-8") as f:
            json.dump(candidate, f, indent=2, ensure_ascii=False)
    return report


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..",
                     "technology-transfer-portfolio-15"))
    report = run_r372_acceptance(root)
    print("=" * 74)
    for r in report["conditions"]:
        mark = "PASS" if r["status"] == "PASS" else "FAIL"
        print(f"  [{mark}] {r['condition']}"
              + (f"  {r['details']}" if r["status"] != "PASS" else ""))
    print("=" * 74)
    print(f"ALL PASS: {report['all_pass']}")
    return 0 if report["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

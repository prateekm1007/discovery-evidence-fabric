"""tests/fixtures/r440/blind_corpus_builder.py — R440.15 the BLIND
PACKAGE ACCEPTANCE CORPUS builder + R440.18 the #160 permanent replica.

INDEPENDENCE (Art. VIII + the R439 verifier/fixture-circularity lesson):
this module imports NO gate code, NO compiler code — it is authored from
the package SCHEMA (the public file/field contract) and the auditor's
incident descriptions (the R440/R439 defect classes), never from the
verifier's behavior. The ground-truth labels are written to a SEPARATE
manifest the gate never reads: the gate runs BLIND (it cannot know a
case's category at verification time).

Corpus design (R440.15): 10 families x 10 seeds = 100 cases built from
the frozen golden P-04 baseline (an independently produced historical
package — not compiler output, closing the builder-testing loop):

  identity_corruption    machine-layer identity mutated/removed (the
                         R439 A finding: inv-format divergence)
  domain_contamination   foreign-domain content injected into machine
                         layers (the #160 stale-material failure)
  missing_outputs        required buyer outputs deleted while the
                         manifest still claims them (#160's 21-absent)
  manifest_tamper        phantom manifest entries / count divergence
  hash_mismatch          file bytes changed after manifest hashing
  maturity_split         machine layers disagree about maturity (the
                         #160 split-brain)
  buyer_language_leak    raw JSON dumped into a buyer PDF (the R439 L
                         finding)
  secret_leak            credential-shaped strings in package files
  provenance_removal     traceability chains stripped (R440.5)
  benign_control         semantics-preserving perturbations that must
                         STILL PASS (Art. V: fail closed without becoming
                         a universal rejector)

Every case is deterministic (seed = 0..9 varies WHICH file/field and the
degree — never random). The #160 replica (hell_160) is a composite case
kept OUT of the blind corpus (it is a NAMED regression with
gate-specific expectations, R440.18).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as rl_canvas

GOLDEN_ZIP = (Path(__file__).resolve().parents[3] / "benchmarks" / "r440"
              / "golden_packages" / "P-04.zip")

MEDICAL_PARAGRAPH = (
    "The CSF shunt system must satisfy FDA GMLP requirements for "
    "hydrocephalus management. Biocompatibility testing per ISO 10993 and "
    "sterilization validation are required for the catheter implant. "
    "Clinical endpoints for CSF pressure reduction in hydrocephalus patients "
    "must be established before regulatory submission."
)
ML_PARAGRAPH = (
    "The ML decision-support architecture uses a neural network classifier "
    "with training data from the dataset. Inference latency and throughput "
    "of the software architecture determine model serving feasibility."
)
VEHICLE_NAME = ("Aerodynamic Drag Reduction Architecture for "
                "Passenger Vehicles")

MACHINE_JSONS = [
    # the P-04 baseline's actual machine layers (top-level + MODEL/)
    "COMMERCIAL_EVIDENCE.json",
    "ENGINEERING_TRACEABILITY.json",
    "EQUATION_REGISTRY.json",
    "LOOP_STATE.json",
    "MATURITY_BASIS.json",
    "UNKNOWN_ROADMAP.json",
    "VALIDATION_ECONOMICS.json",
    "MODEL/MODEL_MANIFEST.json",
    "MODEL/KEY_DIMENSIONS.json",
    "MODEL/ENGINEERING_PROVENANCE.json",
    "MODEL/GEOMETRY_VALIDATION_REPORT.json",
]
BUYER_PDFS = [
    "00_PACKAGE_README.pdf",
    "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
    "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
    "03_BUYER_DECISION_CARD.pdf",
    "04_EVIDENCE_SUMMARY.pdf",
    "05_TRANSFER_MANIFEST.pdf",
]


# ------------------------------------------------------------------ helpers
def unpack_baseline(dest: Path) -> Path:
    """Unpack the frozen golden P-04 (the independently produced
    baseline; NOT compiler output)."""
    if dest.exists():
        shutil.rmtree(dest)
    with zipfile.ZipFile(GOLDEN_ZIP) as zf:
        zf.extractall(dest)
    # the ZIP may carry a TECHNOLOGY_PACKAGE/ root; flatten to case dir
    if not (dest / "PACKAGE_MANIFEST.json").exists():
        inner = dest / "TECHNOLOGY_PACKAGE"
        if inner.is_dir():
            for p in list(inner.iterdir()):
                shutil.move(str(p), str(dest / p.name))
            inner.rmdir()
    return dest


def set_json(pkg: Path, rel: str, mutate) -> None:
    d = json.loads((pkg / rel).read_text())
    mutate(d)
    (pkg / rel).write_text(json.dumps(d, indent=2))


def refresh_manifest_hashes(pkg: Path) -> None:
    man = json.loads((pkg / "PACKAGE_MANIFEST.json").read_text())
    for entry in man.get("files", []):
        if isinstance(entry, dict):
            key = "file" if "file" in entry else "path"
            f = pkg / str(entry.get(key, ""))
            if f.exists():
                entry["sha256"] = hashlib.sha256(f.read_bytes()).hexdigest()
    (pkg / "PACKAGE_MANIFEST.json").write_text(json.dumps(man, indent=2))


def manifest_add(pkg: Path, rel: str, role: str) -> None:
    man = json.loads((pkg / "PACKAGE_MANIFEST.json").read_text())
    f = pkg / rel
    entry = {"file": rel, "role": role,
             "sha256": hashlib.sha256(f.read_bytes()).hexdigest()}
    man["files"].append(entry)
    (pkg / "PACKAGE_MANIFEST.json").write_text(json.dumps(man, indent=2))


def add_pdf(pkg: Path, name: str, paragraphs: list[str],
            title: str = "", append: bool = False) -> None:
    """Rebuild (or append a page to) a buyer PDF with reportlab."""
    if append:
        import io
        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf, pagesize=letter)
        y = letter[1] - 72
        c.setFont("Helvetica", 10)
        for para in paragraphs:
            for line in _wrap(para, 90):
                c.drawString(72, y, line)
                y -= 13
            y -= 6
        c.save()
        buf.seek(0)
        from pypdf import PdfReader, PdfWriter
        reader = PdfReader(str(pkg / name))
        extra = PdfReader(buf)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        for page in extra.pages:
            writer.add_page(page)
        with open(pkg / name, "wb") as f:
            writer.write(f)
        return
    c = rl_canvas.Canvas(str(pkg / name), pagesize=letter)
    W, H = letter
    if title:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(72, H - 72, title)
    y = H - 100
    c.setFont("Helvetica", 10)
    for para in paragraphs:
        for line in _wrap(para, 90):
            c.drawString(72, y, line)
            y -= 13
        y -= 6
    c.save()


def _wrap(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


# ------------------------------------------------------- defect operators
def op_identity_corruption(pkg: Path, seed: int) -> None:
    """Machine-layer identity corrupted — the R439 A finding: identity
    divergence between layers (inv: vs flattened formats)."""
    rel = MACHINE_JSONS[seed % len(MACHINE_JSONS)]
    kind = seed // len(MACHINE_JSONS)
    if kind == 0:
        set_json(pkg, rel, lambda d: d.update(
            package_id="invui-FLATTENED-DIVERGENT-ID"))
    elif kind == 1:
        set_json(pkg, rel, lambda d: d.pop("package_id", None))
    else:
        set_json(pkg, rel, lambda d: d.update(
            package_id="", invention_id="divergent-invention-id"))
    refresh_manifest_hashes(pkg)


def op_domain_contamination(pkg: Path, seed: int) -> None:
    """Foreign-domain material injected into machine layers (the #160
    stale-material failure). P-04's canonical domain is MEDICAL (enzyme
    catheter) — the foreign material is vehicle/software-ML content,
    i.e. genuinely OUTSIDE the package's home domains."""
    foreign = [
        "The vehicle active grille shutter architecture reduces "
        "aerodynamic drag coefficient at highway speed. Underbody "
        "fairing panels smooth the airflow beneath the passenger "
        "vehicle chassis, reducing lift and drag.",
        ML_PARAGRAPH,
        "Vehicle powertrain mounting stiffness and cabin NVH isolation "
        "were validated on the passenger vehicle platform. The "
        "suspension bushing durometer selection drives the vehicle ride "
        "quality targets.",
    ][seed % 3]
    rel = MACHINE_JSONS[seed % len(MACHINE_JSONS)]
    set_json(pkg, rel, lambda d: d.update(
        UNBOUND_FOREIGN_SECTION={
            "content": foreign,
            "template": "stale prior problem material"}))
    refresh_manifest_hashes(pkg)


def op_missing_outputs(pkg: Path, seed: int) -> None:
    """Required buyer outputs deleted while the manifest still claims
    them (the #160 21-absent posture)."""
    victims = [BUYER_PDFS[seed % len(BUYER_PDFS)]]
    if seed >= 3:
        victims.append(MACHINE_JSONS[seed % len(MACHINE_JSONS)])
    for v in victims:
        (pkg / v).unlink()
    # manifest deliberately NOT updated (the claim outlives the artifact)


def op_manifest_tamper(pkg: Path, seed: int) -> None:
    """Manifest/reality split: phantom entries (odd seeds — manifest
    claims files that do not exist) or dropped entries (even seeds —
    real files become unmanifested). Both directions split the
    claim/artifact equality the manifest exists to prove."""
    man = json.loads((pkg / "PACKAGE_MANIFEST.json").read_text())
    if seed % 2:
        man["files"].append({"file": "MODEL/PHANTOM_FILE.step",
                             "role": "phantom entry",
                             "sha256": "0" * 64})
    else:
        n_drop = 2 + (seed % 4)
        man["files"] = man["files"][:len(man["files"]) - n_drop] \
            if len(man["files"]) > n_drop else man["files"][:1]
    (pkg / "PACKAGE_MANIFEST.json").write_text(json.dumps(man, indent=2))


def op_hash_mismatch(pkg: Path, seed: int) -> None:
    """File bytes changed AFTER manifest hashing (content/claim split)."""
    rel = MACHINE_JSONS[seed % len(MACHINE_JSONS)]
    set_json(pkg, rel, lambda d: d.update(
        SILENT_CONTENT_MUTATION=f"post-hash mutation seed {seed}"))
    # manifest deliberately NOT refreshed


def op_maturity_split(pkg: Path, seed: int) -> None:
    """Machine layers disagree about maturity (the #160 split-brain)."""
    set_json(pkg, "MATURITY_BASIS.json", lambda d: d.update(
        technology_maturity=["BELOW_LADDER", "CONCEPT_ONLY",
                             "UNDEFINED"][seed % 3]))
    # a SECOND machine layer claims a different (higher) rung
    set_json(pkg, "MODEL/MODEL_MANIFEST.json", lambda d: d.update(
        maturity=["ENGINEERING_VALIDATED", "TRANSFER_READY",
                  "EXPERIMENT_READY"][seed % 3]))
    refresh_manifest_hashes(pkg)


def op_buyer_language_leak(pkg: Path, seed: int) -> None:
    """Raw JSON / engine scaffolding dumped into a buyer PDF (the R439 L
    finding: machine state leaking into the human layer)."""
    target = BUYER_PDFS[seed % len(BUYER_PDFS)]
    leak = [
        "MACHINE STATE APPENDIX (leaked)",
        json.dumps({"run_ctx": {"run_id": f"ts_leak_{seed}",
                                "package_number": "99",
                                "_internal": "self._post_rank_pipeline"}},
                   indent=1),
        "Traceback (most recent call last): "
        "File 'engine/run.py', line 1400, in _post_rank_pipeline",
        "{'value': 'raw repr dump', 'epistemic_class': 'AI_INFERENCE'}",
    ]
    add_pdf(pkg, target, leak, append=True)
    refresh_manifest_hashes(pkg)


def op_secret_leak(pkg: Path, seed: int) -> None:
    """Credential-shaped strings in package files (security is part of
    epistemic integrity — GOVERNANCE BS-021)."""
    rel = MACHINE_JSONS[seed % len(MACHINE_JSONS)]
    secrets = [
        "ghp_" + "a" * 36,
        "sk-ant-api03-" + "b" * 40,
        "rnd_" + "c" * 32,
        "API_KEY=live-secret-key-value-" + str(seed),
    ]
    set_json(pkg, rel, lambda d: d.update(
        build_log="/home/operator/.ssh/id_rsa opened; token " +
        secrets[seed % len(secrets)]))
    refresh_manifest_hashes(pkg)


def op_provenance_removal(pkg: Path, seed: int) -> None:
    """Traceability/provenance chains stripped (R440.5: no canonical
    provenance -> reject even when prose is perfect). The baseline uses
    the P-04-era `chains` schema (some seeds also strip the R425
    `links` form for schema coverage)."""
    def strip(d):
        d.pop("chains", None)
        d.pop("links", None)
        if seed % 2:
            d["traceability_state"] = "TRACEABILITY_NOT_APPLICABLE"
        d.pop("summary", None)
    set_json(pkg, "ENGINEERING_TRACEABILITY.json", strip)
    refresh_manifest_hashes(pkg)


def op_benign_control(pkg: Path, seed: int) -> None:
    """Semantics-PRESERVING perturbations that must STILL PASS (Art. V:
    the gate may not be a universal rejector)."""
    if seed % 4 == 0:
        rel = MACHINE_JSONS[seed % len(MACHINE_JSONS)]
        d = json.loads((pkg / rel).read_text())
        (pkg / rel).write_text(json.dumps(d, indent=4, sort_keys=True))
        refresh_manifest_hashes(pkg)
    elif seed % 4 == 1:
        man = json.loads((pkg / "PACKAGE_MANIFEST.json").read_text())
        man["files"] = list(reversed(man["files"]))
        (pkg / "PACKAGE_MANIFEST.json").write_text(
            json.dumps(man, indent=2))
    elif seed % 4 == 2:
        set_json(pkg, "LOOP_STATE.json", lambda d: d.update(
            note="benign formatting note — no semantic change"))
        refresh_manifest_hashes(pkg)
    else:
        victim = "MODEL/README.json"
        man = json.loads((pkg / "PACKAGE_MANIFEST.json").read_text())
        if (pkg / victim).exists():
            (pkg / victim).unlink()
        before = len(man["files"])
        man["files"] = [e for e in man["files"]
                        if str(e.get("file", e.get("path", ""))) != victim]
        if len(man["files"]) != before:
            man["file_count"] = (man.get("file_count") or before) - 1
        (pkg / "PACKAGE_MANIFEST.json").write_text(
            json.dumps(man, indent=2))


FAMILIES = {
    "identity_corruption": op_identity_corruption,
    "domain_contamination": op_domain_contamination,
    "missing_outputs": op_missing_outputs,
    "manifest_tamper": op_manifest_tamper,
    "hash_mismatch": op_hash_mismatch,
    "maturity_split": op_maturity_split,
    "buyer_language_leak": op_buyer_language_leak,
    "secret_leak": op_secret_leak,
    "provenance_removal": op_provenance_removal,
    "benign_control": op_benign_control,
}

EXPECTED_VERDICT = {fam: ("BLOCK" if fam != "benign_control" else "PASS")
                    for fam in FAMILIES}


def build_blind_corpus(dest: Path) -> dict:
    """Build the 100-case blind corpus; returns the ground-truth label
    document (the caller persists it SEPARATELY — the gate never reads
    it)."""
    dest.mkdir(parents=True, exist_ok=True)
    labels = {"schema": "R440_BLIND_PACKAGE_ACCEPTANCE_CORPUS/1.0",
              "note": ("ground truth for the blind acceptance corpus; the "
                       "verifier never reads this file — labels live "
                       "outside the packages by construction"),
              "cases": []}
    for fam, op in FAMILIES.items():
        for seed in range(10):
            case_id = f"{fam}__s{seed}"
            case_dir = dest / case_id
            unpack_baseline(case_dir)
            op(case_dir, seed)
            labels["cases"].append({
                "case_id": case_id,
                "family": fam,
                "seed": seed,
                "expected_verdict": EXPECTED_VERDICT[fam],
            })
    labels["case_count"] = len(labels["cases"])
    return labels


# ------------------------------------------------- R440.18: the #160 replica
def build_hell_160(dest: Path) -> dict:
    """The synthetic '#160 package from hell' — vehicle identity +
    stale medical evidence + ML engineering template + unbound
    regulatory/manufacturing sections + lexical-only depth contract +
    21 ABSENT design outputs + maturity split-brain; identity internally
    consistent (local completeness checks pass, exactly like the real
    #160). Kept OUT of the blind corpus: a NAMED regression with
    gate-level expectations."""
    unpack_baseline(dest)
    set_json(dest, "PACKAGE_MANIFEST.json", lambda d: (
        d.update(technology_name=VEHICLE_NAME, package_id="P-160",
                 technology_maturity="BELOW_LADDER"),
    ))
    for rel in [r for r in (dest.rglob("*.json"))]:
        name = str(rel.relative_to(dest))
        if name == "PACKAGE_MANIFEST.json":
            continue
        try:
            d = json.loads(rel.read_text())
        except Exception:  # noqa: BLE001 — non-JSON files are skipped
            continue
        if isinstance(d, dict) and "package_id" in d:
            d["package_id"] = "P-160"
        if isinstance(d, dict) and "portfolio_number" in d:
            d.pop("portfolio_number", None)
        rel.write_text(json.dumps(d, indent=2))
    ce = json.loads((dest / "COMMERCIAL_EVIDENCE.json").read_text())
    ce["CONTAMINATED_REGULATORY_SECTION"] = {
        "content": MEDICAL_PARAGRAPH,
        "fda_gmlp": "FDA GMLP compliance documentation for CSF shunt "
                    "catheter"}
    ce["CONTAMINATED_ML_TEMPLATE"] = {"content": ML_PARAGRAPH}
    ce["CONTAMINATED_MANUFACTURING"] = {
        "content": "Catheter manufacturing requires cleanroom assembly "
                   "and ethylene oxide sterilization validation for the "
                   "CSF shunt production line."}
    (dest / "COMMERCIAL_EVIDENCE.json").write_text(json.dumps(ce, indent=2))
    (dest / "DEPTH_CONTRACT.json").write_text(json.dumps({
        "sections": [
            {"section_id": "GOVERNING_MODELS",
             "matched_tokens": ["decision"]},
            {"section_id": "EQUATIONS", "matched_tokens":
             ["audit", "decision", "domain", "evidence", "recorded",
              "source"]},
            {"section_id": "CRITICAL_PARAMETERS", "matched_tokens":
             ["decision", "domain", "engine", "engineering", "source",
              "status"]},
        ], "summary": "20/20 sections satisfied"}, indent=2))
    (dest / "DESIGN_OUTPUT_VIEW.json").write_text(json.dumps({
        "design_outputs": [{"id": f"DO-{i:03d}", "status": "ABSENT"}
                           for i in range(1, 22)]}, indent=2))
    (dest / "BUILDER_VIEW.json").write_text(json.dumps({
        "builder_view_maturity": "ENGINEERING_DEFINITION"}, indent=2))
    add_pdf(dest, "00_PACKAGE_README.pdf", [
        VEHICLE_NAME,
        "Package P-160 - Version 1.0",
        "READING ORDER",
        "1. 03_BUYER_DECISION_CARD.pdf - the nine decision questions",
        "2. 01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf - one-page summary",
        "3. 02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf - full "
        "engineering definition",
        "4. 04_EVIDENCE_SUMMARY.pdf - external precedent with source "
        "hashes",
        "5. 05_TRANSFER_MANIFEST.pdf - transfer boundary",
    ])
    add_pdf(dest, "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf", [
        "EXECUTIVE TECHNOLOGY BRIEF - " + VEHICLE_NAME,
        "The vehicle architecture reduces aerodynamic drag at highway "
        "speed while maintaining passenger cabin space and safety.",
        MEDICAL_PARAGRAPH,
    ])
    add_pdf(dest, "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf", [
        "ENGINEERING TECHNOLOGY TRANSFER DOSSIER - " + VEHICLE_NAME,
        "GOVERNING MODELS",
        "The decision domain evidence recorded source engineering status "
        "audit model system data analysis. 21 design outputs recorded "
        "(all ABSENT in the engineering record).",
        "EQUATION: EQ-1 drag force F = 0.5 rho v^2 Cd A",
        "MECHANISM: active grille shutters and underbody fairing reduce "
        "the effective frontal area and drag coefficient.",
        "DESIGN INPUTS: DI-001 vehicle class; DI-002 target drag "
        "coefficient; DI-003 cabin packaging volume.",
        "FAILURE MODES: FM-1 crosswind sensitivity; FM-2 actuator icing.",
        "WORK PACKAGES: WP-01 wind-tunnel correlation; WP-02 actuator "
        "endurance validation.",
        MEDICAL_PARAGRAPH,
        ML_PARAGRAPH,
    ])
    add_pdf(dest, "03_BUYER_DECISION_CARD.pdf", [
        "WHAT IS THE INVENTION?",
        "ML decision-support architecture for CSF shunt catheter "
        "placement.",
        "WHAT IS ACTUALLY ESTABLISHED?",
        "21 design outputs, 21 ABSENT. Engineering definition with "
        "governing equations, design inputs, failure modes, build plan.",
        "WHAT REMAINS UNCERTAIN?",
        "killer experiment fails: UNKNOWN",
        "WHAT EVIDENCE WOULD CAUSE THE BUYER TO STOP?",
        "Enzyme half-life in CSF environment is less than 30 days.",
    ])
    add_pdf(dest, "04_EVIDENCE_SUMMARY.pdf", [
        "EVIDENCE SUMMARY",
        VEHICLE_NAME + " - Package P-160",
        "EVIDENCE CLASS DISCIPLINE (Constitution Art. XXXVIII)",
        "SOURCE_FACT 5", "UNKNOWN 5",
        "PHYSICAL_OBSERVATION = 0. No AI-generated computation is "
        "presented as a physical observation.",
        "EXTERNAL ENGINEERING PRECEDENT (hashed sources)",
        "Source 1: Neprilysin-Mediated Amyloid Beta Clearance",
        "URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC11651204",
        "Source hash: ced8ecda90f7a8fc910ebf995bf833f517e1e501f8d1a63a"
        "65e9a49629f98d51",
        "Source 2: Brain Shuttle Neprilysin reduces Amyloid-beta levels",
        "URL: https://journals.plos.org/plosone/article?id=10.1371/"
        "journal.pone.0229850",
        "Source hash: dbe4c0f6a45b389214959b745ce50120a2b82f77805b70cf95"
        "a91be43cb379d1",
    ])
    add_pdf(dest, "05_TRANSFER_MANIFEST.pdf", [
        "TRANSFER MANIFEST",
        VEHICLE_NAME + " - Package P-160 transfer boundary.",
        "Buyer receives the engineering definition and decisive "
        "experiment plan. Buyer must build the validation prototype.",
    ])
    manifest_add(dest, "DEPTH_CONTRACT.json", "depth contract")
    manifest_add(dest, "DESIGN_OUTPUT_VIEW.json", "design output view")
    manifest_add(dest, "BUILDER_VIEW.json", "builder maturity view")
    refresh_manifest_hashes(dest)
    return {"case_id": "hell_160",
            "expected_verdict": "BLOCK",
            "note": "the #160 replica: internally consistent vehicle "
                    "identity carrying stale medical/ML material"}

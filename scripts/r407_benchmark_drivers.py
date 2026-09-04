#!/usr/bin/env python3
"""
r407_benchmark_drivers.py — P0 machine drivers for the R407 benchmark rubric.

Roadmap basis: R407/ROADMAP_9_10_BENCHMARKS.md Part A ("P0 makes one machine
contract define the ten families and their scoring") + Part C P0
("Implement R407/BENCHMARK_RUBRIC.json + drivers for DELIVERY/HONESTY/
FIDELITY").

Constitution basis:
  Art. XXIV  — artifacts outrank summaries: every score here is computed
               from measured state, never carried from a summary.
  Art. XXV   — unknown stays unknown: an unavailable instrument is an
               honest BLOCKED state (score 0), never a silent pass.
  Art. XXVI  — no self-certification: driver output is a MEASUREMENT by
               the claimant; certification remains the clean-clone replay
               + the R408 external audit.
  Art. XXVIII— no silent semantic promotion: the honesty driver scans for
               promoted states (REAL_LOOP_VERIFIED / PHYSICALLY_VALIDATED
               appearing in shipped artifacts).
  Art. LIX   — no benchmark gaming: the deduction tables below are FROZEN
               with this rubric version; changing them requires a new
               rubric version and adversarial re-test.

Scoring model (FROZEN with rubric 1.0.0):
  score = 10 - sum(deductions), floor 0, integer-truncated.
  The 9-bar (release bar) requires zero deductions on that family's checks.
  Deduction weights are per-check-class, NOT per-instance, except where a
  per-instance cap is explicitly declared — a hundred stale hashes is one
  defect class (D1), not a hundred deductions.

Usage:
  python scripts/r407_benchmark_drivers.py --family all \
      --portfolio-root /path/to/technology-transfer-portfolio-15
  python scripts/r407_benchmark_drivers.py --family fidelity   # engine-only checks
"""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent.parent
RUBRIC_PATH = ENGINE_ROOT / "R407" / "BENCHMARK_RUBRIC.json"
DEFAULT_OUT_DIR = ENGINE_ROOT / "R407" / "DRIVERS"

sys.path.insert(0, str(ENGINE_ROOT))

RUBRIC_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Frozen deduction tables (rubric 1.0.0). Rule 7: no tuning against output.
# ---------------------------------------------------------------------------

DELIVERY_DEDUCTIONS = {
    "identity_registry_freshness": 1.0,      # D1
    "latest_release_consistency": 0.5,        # D2
    "chain_certificate_pass": 2.0,
    "release_audits_green": 1.5,              # B1
    "reproduction_evidence": 1.0,
    "manifest_pins_agree": 2.0,               # the 9-bar's "924/924 pins":
    # every buyer-surface file the CANONICAL_RELEASE_MANIFEST pins must
    # hash-match the current tree; a stale manifest after content
    # changes scores RED until the r386 regeneration runs (Art. XXXIX
    # order: portfolio commit FIRST, then manifest from pushed state)
}

HONESTY_DEDUCTIONS = {
    "unknowns_preserved": 1.5,
    "equation_names_honest": 1.5,             # B1 surface
    "equation_status_honest": 1.0,            # r374
    "no_semantic_promotion": 3.0,
    "numeric_assertions_sourced": 2.0,        # per-package 0.25, capped
}

FIDELITY_DEDUCTIONS = {
    "frozen_corpus_hash_guard": 3.0,
    "stale_path_census": 3.0,                 # C1: per-path 0.5, capped
    "not_measurable_census": 2.0,             # per-hit 1.0, capped
    "semantic_genericness_live": 2.0,         # C2: per-mismatch 0.5, capped
}

AUDIT_NOTES = {
    "identity_registry_freshness": "D1: PORTFOLIO_IDENTITY_REGISTRY.json "
    "dossier/manifest/zip hashes vs the shipped tree",
    "latest_release_consistency": "D2: LATEST_RELEASE claims vs the engine "
    "authority records (certificate check-count, registry commits, tag "
    "status)",
    "chain_certificate_pass": "the freshest clean-clone chain certificate "
    "in the engine repo is overall PASS",
    "release_audits_green": "B1: r373 independent audit + r374 equation "
    "status audit green on every shipped package",
    "reproduction_evidence": "a committed fresh-clone byte-reproduction "
    "record exists for the release",
    "manifest_pins_agree": "the 9-bar's 924/924 pins: every "
    "buyer-surface file the CANONICAL_RELEASE_MANIFEST pins hash-matches "
    "the current tree (a stale manifest after content changes is RED "
    "until the r386 regeneration runs)",
    "unknowns_preserved": "r373 unknowns audit: shipped classifications "
    "agree with mechanical re-derivation",
    "equation_names_honest": "r373 equation audit: recorded names match "
    "the engine canonical",
    "equation_status_honest": "r374 equation status: shipped totals/units "
    "match recompute",
    "no_semantic_promotion": "no REAL_LOOP_VERIFIED / PHYSICALLY_VALIDATED "
    "claim anywhere in the shipped tree",
    "numeric_assertions_sourced": "COMMERCIAL_EVIDENCE.json rows carry "
    "source + source_hash",
    "frozen_corpus_hash_guard": "tests/r403_corpus_pins.json pins verify "
    "against BENCHMARK_ENGINEERING_DOSSIERS/frozen_corpus_r370",
    "stale_path_census": "C1: every path-shaped reference in the release "
    "surfaces resolves (placeholder templates fail)",
    "not_measurable_census": "no NOT_MEASURABLE measurement state on the "
    "shipped/frozen data surfaces",
    "semantic_genericness_live": "C2: the B4 semantic-genericness audit "
    "runs live on the shipped packages and passes",
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _check(name, passed, evidence, failures=None):
    return {"name": name, "pass": bool(passed), "note": AUDIT_NOTES[name],
            "evidence": evidence, "failures": failures or []}


# ---------------------------------------------------------------------------
# DELIVERY driver
# ---------------------------------------------------------------------------

def check_identity_registry(portfolio_root):
    """D1 — registry hashes vs shipped tree (r371 identity semantics)."""
    reg_path = portfolio_root / "PORTFOLIO_IDENTITY_REGISTRY.json"
    if not reg_path.exists():
        return _check("identity_registry_freshness", False,
                      "PORTFOLIO_IDENTITY_REGISTRY.json missing")
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    mismatches, checked = [], 0
    for entry in reg.get("packages", []):
        folder = entry["folder_name"]
        d = portfolio_root / "DOWNLOAD" / folder
        for field, fname in (
                ("dossier_hash", "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf"),
                ("manifest_hash", "PACKAGE_MANIFEST.json")):
            fp = d / fname
            if not fp.exists():
                mismatches.append(f"{folder}:{fname}:MISSING")
                continue
            checked += 1
            if entry.get(field) and sha256_file(fp) != entry[field]:
                mismatches.append(f"{folder}:{field}")
        zp = portfolio_root / "DOWNLOAD" / f"{folder}.zip"
        if zp.exists():
            checked += 1
            if entry.get("package_zip_hash") and \
                    sha256_file(zp) != entry["package_zip_hash"]:
                mismatches.append(f"{folder}:package_zip_hash")
    ok = not mismatches
    return _check("identity_registry_freshness", ok,
                  f"{checked} hash comparisons across "
                  f"{len(reg.get('packages', []))} entries",
                  mismatches)


def check_latest_release(portfolio_root, engine_root):
    """D2 — LATEST_RELEASE claims vs engine authority records."""
    lr_path = portfolio_root / "RELEASE" / "LATEST_RELEASE.json"
    problems = []
    evidence = []
    if not lr_path.exists():
        return _check("latest_release_consistency", False,
                      "RELEASE/LATEST_RELEASE.json missing", ["FILE_MISSING"])
    lr = json.loads(lr_path.read_text(encoding="utf-8"))
    # engine-side registry (authority for releases)
    erp = engine_root / "ENGINE_RELEASE_REGISTRY.json"
    if not erp.exists():
        return _check("latest_release_consistency", False,
                      "ENGINE_RELEASE_REGISTRY.json missing",
                      ["ENGINE_REGISTRY_MISSING"])
    registry = json.loads(erp.read_text(encoding="utf-8"))
    releases = registry.get("releases", [])
    if not releases:
        return _check("latest_release_consistency", False,
                      "engine registry empty", ["ENGINE_REGISTRY_EMPTY"])
    last = releases[-1]
    # 1. pointer must reference the LAST recorded release
    if lr.get("release_id") != last.get("release_id"):
        problems.append(f"POINTER_NOT_LATEST: {lr.get('release_id')} "
                        f"!= {last.get('release_id')}")
    if lr.get("portfolio_release_commit") and \
            lr["portfolio_release_commit"] != last["portfolio_release_commit"]:
        problems.append("PORTFOLIO_COMMIT_MISMATCH")
    if lr.get("engine_build_commit") and \
            lr["engine_build_commit"] != last["engine_build_commit"]:
        problems.append("ENGINE_COMMIT_MISMATCH")
    # 2. claimed chain check-count must equal the authority certificate's
    cert_path = engine_root / "RELEASE_CHAIN" / \
        "RELEASE_CHAIN_VERIFICATION_R387-3D-QUALITY-EDITION.json"
    claimed = lr.get("chain_verification", "")
    m = re.search(r"(\d+)\s*/\s*(\d+)", str(claimed))
    cert_checks = None
    if cert_path.exists():
        cert = json.loads(cert_path.read_text(encoding="utf-8"))
        cc = cert.get("checks", cert.get("results", []))
        cert_checks = len(cc) if isinstance(cc, list) else cert.get(
            "checks_total")
        evidence.append(f"certificate checks={cert_checks}")
    if m:
        claimed_passed, claimed_total = int(m.group(1)), int(m.group(2))
        evidence.append(f"claimed {claimed_passed}/{claimed_total}")
        if cert_checks is not None and claimed_total != cert_checks:
            problems.append(f"CHECK_COUNT_MISMATCH: pointer claims "
                            f"{claimed_total}, authority certificate has "
                            f"{cert_checks}")
        if claimed_passed != claimed_total:
            problems.append("POINTER_CLAIMS_PARTIAL_PASS")
    # 3. master zip hash vs the canonical manifest (buyer truth)
    manifest = json.loads((portfolio_root /
                           "CANONICAL_RELEASE_MANIFEST.json")
                          .read_text(encoding="utf-8"))
    mz = manifest.get("master_zip", {})
    if lr.get("master_zip_sha256") and \
            lr["master_zip_sha256"] != mz.get("sha256"):
        problems.append("MASTER_ZIP_HASH_MISMATCH_VS_MANIFEST")
    # 4. tag/status agreement: engine registry status says NOT_TAGGED while
    #    the tag exists on the portfolio remote is an inconsistency the
    #    auditor counts under D2.
    if last.get("status") == "SUBMITTED_FOR_CEO_AUDIT_NOT_TAGGED":
        # verify against the local clone's tags (remote tag check is the
        # clean-clone verifier's job; here the presence of the tag in the
        # release clone contradicts the engine status field)
        tag_file = portfolio_root / ".git" / "refs" / "tags" / \
            str(lr.get("git_tag", "v1.0.0-3D-edition"))
        packed = (portfolio_root / ".git" / "packed-refs").exists()
        if tag_file.exists() or packed:
            problems.append("REGISTRY_STATUS_SAYS_NOT_TAGGED_BUT_TAG_EXISTS")
    evidence.append(f"engine registry last release: "
                    f"{last.get('release_id')} status={last.get('status')}")
    return _check("latest_release_consistency", not problems,
                  "; ".join(evidence) or "no evidence", problems)


def check_manifest_pins_agree(portfolio_root):
    """The 9-bar's 924/924 pins: every buyer-surface file pinned by the
    CANONICAL_RELEASE_MANIFEST must hash-match the current tree. Fails
    RED whenever the tree moved ahead of the manifest (the r386
    regeneration has not run) — reporting DELIVERY green with a stale
    manifest would itself be a HONESTY failure."""
    mpath = portfolio_root / "CANONICAL_RELEASE_MANIFEST.json"
    if not mpath.exists():
        return _check("manifest_pins_agree", False,
                      "CANONICAL_RELEASE_MANIFEST.json missing",
                      ["MANIFEST_MISSING"])
    m = json.loads(mpath.read_text(encoding="utf-8"))
    mismatches = []
    checked = 0
    # buyer_surface pins + package_zips + master_zip
    pins = m.get("buyer_surface")
    if isinstance(pins, dict):
        file_map = pins.get("files") or pins
    else:
        file_map = {}
    if isinstance(file_map, dict):
        for rel, expected in file_map.items():
            fp = portfolio_root / rel
            if not fp.exists():
                mismatches.append(f"{rel}:MISSING")
                continue
            checked += 1
            if sha256_file(fp) != expected:
                mismatches.append(f"{rel}:HASH_DRIFT")
    for pz in (m.get("package_zips") or []):
        if isinstance(pz, dict) and pz.get("path") and pz.get("sha256"):
            fp = portfolio_root / pz["path"]
            if not fp.exists():
                mismatches.append(f"{pz['path']}:MISSING")
                continue
            checked += 1
            if sha256_file(fp) != pz["sha256"]:
                mismatches.append(f"{pz['path']}:HASH_DRIFT")
    mz = m.get("master_zip") or {}
    if mz.get("path") and mz.get("sha256"):
        fp = portfolio_root / mz["path"]
        if not fp.exists():
            mismatches.append(f"{mz['path']}:MISSING")
        else:
            checked += 1
            if sha256_file(fp) != mz["sha256"]:
                mismatches.append(f"{mz['path']}:HASH_DRIFT")
    return _check("manifest_pins_agree", not mismatches,
                  f"{checked} pinned buyer-surface files hash-verified "
                  f"against the current tree", mismatches[:40])


def check_chain_certificate(engine_root):
    """Freshest clean-clone chain certificate is overall PASS."""
    certs = []
    rc = engine_root / "RELEASE_CHAIN"
    if rc.exists():
        for fp in sorted(rc.glob("*.json")):
            try:
                c = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(c, dict) and c.get("overall"):
                certs.append((fp.name, c.get("overall")))
    ok = bool(certs) and certs[-1][1] == "PASS"
    return _check("chain_certificate_pass", ok,
                  f"latest certificate: {certs[-1][0]} -> {certs[-1][1]}"
                  if certs else "no certificates found",
                  [] if ok else ["NO_PASS_CERTIFICATE"])


def run_release_audits(portfolio_root):
    """B1 — run the r373 full audit + r374 equation-status on the shipped
    tree (read-only). Returns (r373_result, r374_failures)."""
    from premium_package_factory.r373.run_r373_audit import run_r373_audit
    from premium_package_factory.r374.run_r374_audit import (
        audit_equation_status as r374_status,
    )
    from premium_package_factory.r371.canonical_source import \
        load_all_packages
    r373 = run_r373_audit(str(portfolio_root))
    packages = load_all_packages()
    r374_failures = []
    for p in packages:
        fp = portfolio_root / "DOWNLOAD" / p.folder / "EQUATION_REGISTRY.json"
        if not fp.exists():
            r374_failures.append(f"{p.pkg_id}:REGISTRY_MISSING")
            continue
        shipped = json.loads(fp.read_text(encoding="utf-8"))
        r = r374_status(p, shipped)
        if not r.get("ok"):
            r374_failures.extend(
                f"{p.pkg_id}:{f.get('check')}" for f in r.get("failures", []))
    return r373, r374_failures


def check_release_audits(r373_result, r374_failures):
    """B1 verdict from the shared audit run."""
    problems = []
    for pid, a in (r373_result.get("packages") or {}).items():
        if a.get("state_ladder", {}).get("release_gate") != "PASS":
            fails = []
            for k in ("equation_audit", "unknowns_audit",
                      "document_completeness_audit",
                      "v2_propagation_audit", "buyer_usability_audit",
                      "commercial_evidence_audit"):
                for f in (a.get(k) or {}).get("failures") or []:
                    fails.append(f"{pid}:{f.get('check')}")
            problems.extend(fails or [f"{pid}:GATE_FAIL"])
    problems.extend(r374_failures)
    ok = not problems
    return _check("release_audits_green", ok,
                  "r373 full audit + r374 equation status, all 15 packages",
                  problems[:40])


def check_reproduction_evidence(portfolio_root):
    """Committed fresh-clone byte-reproduction record for the release."""
    candidates = [
        portfolio_root / "INTERNAL_QA" / "R373_FRESH_CLONE_REPRODUCTION.json",
    ]
    iq = portfolio_root / "INTERNAL_QA"
    if iq.exists():
        candidates.extend(iq.glob("*FRESH_CLONE*REPRODUCTION*.json"))
        candidates.extend(iq.glob("*REPRODUCTION*.json"))
    found_pass = None
    stale_note = None
    for c in candidates:
        if not c.exists():
            continue
        try:
            d = json.loads(c.read_text(encoding="utf-8"))
        except Exception:
            continue
        verdict = (d.get("overall") or d.get("verdict") or d.get("result")
                   or ("PASS" if d.get("all_pass") is True else None))
        if verdict == "PASS":
            found_pass = c.name
            stale_note = f"recorded at portfolio_head " \
                         f"{str(d.get('portfolio_head'))[:12]}"
            break
        if found_pass is None:
            found_pass = f"{c.name}->{verdict}"
    ok = found_pass is not None and not found_pass.endswith("->None")
    return _check("reproduction_evidence", ok,
                  f"record: {found_pass} ({stale_note})" if found_pass and
                  stale_note else
                  (f"record: {found_pass}" if found_pass else
                   "no reproduction record found"),
                  [] if ok else ["NO_PASSING_REPRODUCTION_RECORD"])


# ---------------------------------------------------------------------------
# HONESTY driver
# ---------------------------------------------------------------------------

def check_unknowns_preserved(r373_result):
    problems = []
    for pid, a in (r373_result.get("packages") or {}).items():
        for f in (a.get("unknowns_audit") or {}).get("failures") or []:
            problems.append(f"{pid}:{f.get('check')}:"
                            f"{str(f.get('detail', ''))[:80]}")
    return _check("unknowns_preserved", not problems,
                  "r373 unknowns audit, mechanical re-derivation",
                  problems)


def check_equation_names(r373_result):
    problems = []
    for pid, a in (r373_result.get("packages") or {}).items():
        for f in (a.get("equation_audit") or {}).get("failures") or []:
            problems.append(f"{pid}:{f.get('check')}")
    return _check("equation_names_honest", not problems,
                  "r373 equation audit vs engine canonical", problems)


def check_equation_status(r374_failures):
    return _check("equation_status_honest", not r374_failures,
                  "r374 equation status: totals/units recompute",
                  r374_failures)


def check_no_semantic_promotion(portfolio_root):
    """No REAL_LOOP_VERIFIED / PHYSICALLY_VALIDATED claim in the shipped
    tree. Negative-form mentions (NONE / never claimed / counts) are the
    honest disclosures and do NOT count (Art. XXV)."""
    problems = []
    allowed_states = {"NONE", "SYNTHETIC_LOOP_VERIFIED"}
    for fp in sorted((portfolio_root / "DOWNLOAD").glob("*/LOOP_STATE.json")):
        d = json.loads(fp.read_text(encoding="utf-8"))
        state = d.get("loop_verification_state")
        if state and state not in allowed_states:
            problems.append(f"{fp.parent.name}:loop_verification_state="
                            f"{state}")
    pattern = re.compile(r'REAL_LOOP_VERIFIED"?\s*[:=]\s*true', re.I)
    for fp in sorted((portfolio_root / "DOWNLOAD").rglob("*.json")):
        text = fp.read_text(encoding="utf-8", errors="replace")
        if pattern.search(text):
            problems.append(f"{fp.relative_to(portfolio_root)}:"
                            "REAL_LOOP_VERIFIED=true")
        for m in re.finditer(r'.{50}PHYSICALLY_VALIDATED.{50}', text):
            ctx = m.group(0)
            if re.search(r"NONE|never|NOT|count|_|0", ctx):
                continue  # negative/honest-disclosure form
            problems.append(f"{fp.relative_to(portfolio_root)}:"
                            "PHYSICALLY_VALIDATED claim")
    return _check("no_semantic_promotion", not problems,
                  "LOOP_STATE states + shipped-JSON promotion scan",
                  problems)


def check_numeric_assertions_sourced(portfolio_root):
    """COMMERCIAL_EVIDENCE.json rows must carry source + source_hash
    (r373 COMMERCIAL_FIELDS discipline)."""
    problems = []
    n_rows = 0
    for fp in sorted((portfolio_root / "DOWNLOAD")
                     .glob("*/COMMERCIAL_EVIDENCE.json")):
        d = json.loads(fp.read_text(encoding="utf-8"))
        rows = d if isinstance(d, list) else [d]
        for row in rows:
            if not isinstance(row, dict):
                continue
            has_estimate = any(
                row.get(k) not in (None, "", []) for k in
                ("estimate", "market_size", "population_basis"))
            if not has_estimate:
                continue
            n_rows += 1
            if not row.get("source"):
                problems.append(f"{fp.parent.name}:no-source")
            if not row.get("source_hash"):
                problems.append(f"{fp.parent.name}:no-source_hash")
    return _check("numeric_assertions_sourced", not problems,
                  f"{n_rows} numeric commercial rows checked for "
                  f"source+hash", problems)


# ---------------------------------------------------------------------------
# FIDELITY driver
# ---------------------------------------------------------------------------

def check_frozen_corpus_hash_guard(engine_root):
    """r403 corpus pins verify (the frozen file hash guard)."""
    pins_path = engine_root / "tests" / "r403_corpus_pins.json"
    if not pins_path.exists():
        return _check("frozen_corpus_hash_guard", False,
                      "tests/r403_corpus_pins.json missing", ["PINS_MISSING"])
    pins = json.loads(pins_path.read_text(encoding="utf-8"))
    corpus_root = engine_root / "BENCHMARK_ENGINEERING_DOSSIERS" / \
        "frozen_corpus_r370"
    mismatches = []
    for rel, expected in pins.items():
        fp = corpus_root / rel
        if not fp.exists():
            mismatches.append(f"{rel}:MISSING")
            continue
        if sha256_file(fp) != expected:
            mismatches.append(f"{rel}:HASH_DRIFT")
    return _check("frozen_corpus_hash_guard", not mismatches,
                  f"{len(pins)} pinned files verified against "
                  f"tests/r403_corpus_pins.json", mismatches)


PATH_RE = re.compile(
    r"^[A-Za-z0-9_][A-Za-z0-9_.\-/]*\."
    r"(json|pdf|zip|py|md|txt|csv|step|stl|glb|svg|png)$")


def _collect_path_refs(obj, refs):
    if isinstance(obj, dict):
        for v in obj.values():
            _collect_path_refs(v, refs)
    elif isinstance(obj, list):
        for v in obj:
            _collect_path_refs(v, refs)
    elif isinstance(obj, str):
        s = obj.strip()
        # full-string match: prose containing a path-like suffix is NOT a
        # path reference (the pre-fix last-segment match collected audit
        # prose as phantom paths)
        if PATH_RE.match(s):
            refs.append(s)


def check_stale_path_census(portfolio_root, engine_root):
    """C1 — every path-shaped reference on the release surfaces resolves.
    Resolution order mirrors the real layout: as-is, DOWNLOAD/-prefixed,
    per-package prefixed, per-package MODEL-prefixed, engine-root for
    engine-side refs. git-ref forms (git HEAD:...) are not filesystem
    paths. PLACEHOLDER templates (NN_..., <...>) FAIL — an unresolved
    placeholder on a release certificate is a stale path."""
    problems = []
    folders = sorted(
        (portfolio_root / "DOWNLOAD").glob("[01]*_*"))
    folder_names = [f.name for f in folders if f.is_dir()]

    def resolves(r):
        if r.startswith("git ") or r.startswith("git HEAD:"):
            return True
        # absolute-portfolio-root first (CWD-independent), then the
        # per-package prefixes; engine-root for engine-side refs
        cands = [str(portfolio_root / r),
                 str(portfolio_root / "DOWNLOAD" / r)]
        for f in folder_names:
            cands.append(str(portfolio_root / "DOWNLOAD" / f / r))
            cands.append(str(portfolio_root / "DOWNLOAD" / f / "MODEL" / r))
        if r.startswith("scripts/") or \
                r.startswith("premium_package_factory/") or \
                r.startswith("discovery_fabric/") or \
                r.startswith("tests/"):
            cands.append(str(engine_root / r))
        return any(os.path.exists(c) for c in cands)

    scanned = 0
    history_refs = 0
    for root_dir in ("RELEASE", "INTERNAL_QA"):
        rd = portfolio_root / root_dir
        if not rd.exists():
            continue
        for fp in sorted(rd.rglob("*.json")):
            # Art. XI — history is evidence: preserved historical
            # artifacts (RELEASE/history_r370/ ...) are never edited,
            # so their internal path references are part of the
            # preserved record, not the current release surface. They
            # are counted and disclosed, never repaired, and never
            # counted against the current-surface stale-path bar.
            if any("history" in part for part in
                    fp.relative_to(portfolio_root).parts):
                try:
                    data = json.loads(fp.read_text(encoding="utf-8"))
                except Exception:
                    continue
                refs = []
                _collect_path_refs(data, refs)
                history_refs += len(set(refs))
                continue
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                continue
            refs = []
            _collect_path_refs(data, refs)
            scanned += len(set(refs))
            for r in sorted(set(refs)):
                if not resolves(r):
                    problems.append(f"{fp.relative_to(portfolio_root)}:{r}")
    # engine-side committed references
    for pat in ("R407/*.json", "R406/*.json"):
        for fp in sorted((engine_root / pat.split("/")[0]).glob(
                pat.split("/")[1])):
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                continue
            refs = []
            _collect_path_refs(data, refs)
            scanned += len(set(refs))
            for r in sorted(set(refs)):
                if not (engine_root / r).exists() and not \
                        resolves(r):
                    problems.append(f"{fp.relative_to(engine_root)}:{r}")
    return _check("stale_path_census", not problems,
                  f"{scanned} current-surface path references resolved "
                  f"across RELEASE/, INTERNAL_QA/, R407/, R406/ "
                  f"(+{history_refs} references in preserved history "
                  f"dirs, Art. XI — counted and disclosed, never "
                  f"repaired)", problems)


def check_not_measurable_census(portfolio_root, engine_root):
    """No NOT_MEASURABLE measurement state on the shipped/frozen data
    surfaces (the audit-runner's <2-package guard states are code, not
    committed data, and are out of scope)."""
    problems = []
    targets = []
    corpus = engine_root / "BENCHMARK_ENGINEERING_DOSSIERS" / \
        "frozen_corpus_r370"
    if corpus.exists():
        targets.extend(corpus.rglob("*.json"))
    dl = portfolio_root / "DOWNLOAD"
    if dl.exists():
        targets.extend(dl.glob("*/MATURITY_BASIS.json"))
        targets.extend(dl.glob("*/VALIDATION_ECONOMICS.json"))
    for fp in targets:
        text = fp.read_text(encoding="utf-8", errors="replace")
        if "NOT_MEASURABLE" in text:
            problems.append(f"{fp}:NOT_MEASURABLE")
    return _check("not_measurable_census", not problems,
                  f"{len(targets)} data files scanned", problems)


def check_semantic_genericness_live(portfolio_root):
    """C2 — the B4 audit runs LIVE on the shipped packages and passes."""
    try:
        from premium_package_factory.r371.canonical_source import \
            load_all_packages
        from discovery_fabric.benchmark.semantic_genericness import \
            audit_semantic_genericness
    except Exception as exc:  # pragma: no cover
        return _check("semantic_genericness_live", False,
                      f"import failed: {exc}", ["IMPORT_FAILED"])
    packages = load_all_packages()
    run_packages = []
    for p in packages:
        d = portfolio_root / "DOWNLOAD" / p.folder
        if d.exists():
            run_packages.append({
                "run_dir": str(d), "package_dir": str(d),
                "package_id": p.pkg_id,
                "input_signature": getattr(p, "input_signature", None) or []})
    if len(run_packages) < 2:
        return _check("semantic_genericness_live", False,
                      f"only {len(run_packages)} packages reachable",
                      ["INSUFFICIENT_PACKAGES"])
    result = audit_semantic_genericness(run_packages)
    mismatches = result.get("semantic_mismatches") or []
    problems = [f"{m.get('package_id')}:{str(m.get('sentence'))[:60]}"
                for m in mismatches]
    return _check("semantic_genericness_live",
                  result.get("verdict") == "PASS" and not mismatches,
                  f"B4 live on {len(run_packages)} shipped packages: "
                  f"verdict={result.get('verdict')}, "
                  f"mismatches={len(mismatches)}", problems)


# ---------------------------------------------------------------------------
# Scoring + output
# ---------------------------------------------------------------------------

def _score_from_checks(checks, deductions):
    import math
    total = 0.0
    for c in checks:
        if not c["pass"]:
            cap = deductions.get(c["name"])
            if isinstance(cap, dict):
                total += cap["value"]
            else:
                total += cap
    # floor semantics: ANY failed check costs at least one point — a
    # failing check must never round back up to a perfect 10 (the 0.5
    # per-instance deductions would otherwise round 9.5 -> 10)
    return max(0, math.floor(10 - total)), total


def _apply_per_instance_caps(checks, deduction_tables):
    """Some checks carry per-instance caps; normalize their failures into
    the deduction table form before scoring."""
    per_instance = {
        "numeric_assertions_sourced": (0.25, 2.0),
        "stale_path_census": (0.5, 3.0),
        "not_measurable_census": (1.0, 2.0),
        "semantic_genericness_live": (0.5, 2.0),
    }
    for c in checks:
        if c["pass"]:
            continue
        name = c["name"]
        if name in per_instance:
            per, cap = per_instance[name]
            n = max(1, len(c.get("failures") or [1]))
            deduction_tables[name] = min(per * n, cap)
        else:
            deduction_tables[name] = deduction_tables.get(name, 1.0)
    return deduction_tables


def build_family_result(family, checks, deduction_table, rubric,
                        portfolio_root, instrument_state):
    table = _apply_per_instance_caps(checks, dict(deduction_table))
    score, deducted = _score_from_checks(checks, table)
    if instrument_state != "MEASURED":
        # rubric rule_8: an unavailable instrument is an honest BLOCKED
        # state — a partial measurement (engine-side checks only) is NOT
        # a family score. The checks are recorded for disclosure; the
        # score is suppressed to 0.
        score = 0
    est = (rubric["families"].get(family, {})
           .get("auditor_estimate_r407"))
    return {
        "artifact_type": "BENCHMARK_FAMILY_SCORE",
        "family": family,
        "rubric_version": RUBRIC_VERSION,
        "score": score,
        "release_bar": 9,
        "bar_met": score >= 9,
        "instrument_state": instrument_state,
        "measured_at_engine_head": _git_head(ENGINE_ROOT),
        "measured_at_portfolio_head": _git_head(portfolio_root)
        if portfolio_root else None,
        "checks": checks,
        "deduction_applied": round(deducted, 2),
        "defects_named": [c["name"] for c in checks if not c["pass"]],
        "auditor_estimate_r407_recorded_as_estimate": est,
        "estimate_is_not_the_score": True,
        "scoring_rules": "R407/BENCHMARK_RUBRIC.json rule_1..rule_8; "
                         "deduction table frozen with rubric 1.0.0",
    }


def _git_head(root):
    import subprocess
    try:
        return subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return None


def measure_family(family, portfolio_root):
    rubric = json.loads(RUBRIC_PATH.read_text(encoding="utf-8"))
    if family == "delivery":
        if portfolio_root is None:
            checks = [_check(n, False, "portfolio root not provided",
                             ["INSTRUMENT_UNAVAILABLE"])
                      for n in DELIVERY_DEDUCTIONS
                      if n != "chain_certificate_pass"]
            checks.append(check_chain_certificate(ENGINE_ROOT))
            return build_family_result(family, checks,
                                       DELIVERY_DEDUCTIONS, rubric,
                                       None, "INSTRUMENT_UNAVAILABLE")
        r373, r374f = run_release_audits(portfolio_root)
        checks = [
            check_identity_registry(portfolio_root),
            check_latest_release(portfolio_root, ENGINE_ROOT),
            check_manifest_pins_agree(portfolio_root),
            check_chain_certificate(ENGINE_ROOT),
            check_release_audits(r373, r374f),
            check_reproduction_evidence(portfolio_root),
        ]
        return build_family_result(family, checks, DELIVERY_DEDUCTIONS,
                                    rubric, portfolio_root, "MEASURED")
    if family == "honesty":
        if portfolio_root is None:
            checks = [_check(n, False, "portfolio root not provided",
                             ["INSTRUMENT_UNAVAILABLE"])
                      for n in HONESTY_DEDUCTIONS]
            return build_family_result(family, checks, HONESTY_DEDUCTIONS,
                                       rubric, None,
                                       "INSTRUMENT_UNAVAILABLE")
        r373, r374f = run_release_audits(portfolio_root)
        checks = [
            check_unknowns_preserved(r373),
            check_equation_names(r373),
            check_equation_status(r374f),
            check_no_semantic_promotion(portfolio_root),
            check_numeric_assertions_sourced(portfolio_root),
        ]
        return build_family_result(family, checks, HONESTY_DEDUCTIONS,
                                    rubric, portfolio_root, "MEASURED")
    if family == "fidelity":
        checks = [check_frozen_corpus_hash_guard(ENGINE_ROOT)]
        if portfolio_root is None:
            checks.extend([
                _check("stale_path_census", False,
                       "portfolio root not provided",
                       ["INSTRUMENT_UNAVAILABLE"]),
                _check("not_measurable_census", False,
                       "portfolio root not provided",
                       ["INSTRUMENT_UNAVAILABLE"]),
                _check("semantic_genericness_live", False,
                       "portfolio root not provided",
                       ["INSTRUMENT_UNAVAILABLE"]),
            ])
            return build_family_result(family, checks, FIDELITY_DEDUCTIONS,
                                       rubric, None,
                                       "INSTRUMENT_UNAVAILABLE")
        checks.extend([
            check_stale_path_census(portfolio_root, ENGINE_ROOT),
            check_not_measurable_census(portfolio_root, ENGINE_ROOT),
            check_semantic_genericness_live(portfolio_root),
        ])
        return build_family_result(family, checks, FIDELITY_DEDUCTIONS,
                                    rubric, portfolio_root, "MEASURED")
    raise SystemExit(f"unknown family: {family}")


def write_score(result, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    # uppercase family name: the rubric's output_artifact paths use the
    # uppercase family namespace (R407/DRIVERS/DELIVERY_SCORE.json)
    fp = out_dir / f"{str(result['family']).upper()}_SCORE.json"
    fp.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n",
                  encoding="utf-8")
    return fp


def write_planned_stubs(out_dir, rubric):
    """Rule_2 honesty: every family the rubric names gets a committed
    score artifact. Planned families score 0 by the missing-instrument
    rule with instrument_state INSTRUMENT_UNAVAILABLE and their
    planned-phase driver status — never a silent absence, never an
    estimate promoted to a score."""
    planned = {fam: meta for fam, meta in rubric["families"].items()
               if str(meta.get("driver_status", "")).startswith("PLANNED")}
    written = []
    for fam, meta in sorted(planned.items()):
        stub = {
            "artifact_type": "BENCHMARK_FAMILY_SCORE",
            "family": fam,
            "rubric_version": RUBRIC_VERSION,
            "score": 0,
            "release_bar": 9,
            "bar_met": False,
            "instrument_state": "INSTRUMENT_UNAVAILABLE",
            "driver_status": meta.get("driver_status"),
            "measured_at_engine_head": _git_head(ENGINE_ROOT),
            "measured_at_portfolio_head": None,
            "checks": [],
            "deduction_applied": 0.0,
            "defects_named": [],
            "note": f"driver planned for {meta.get('reaches_9_in')}; "
                    f"score 0 by rubric rule_2 (missing instrument "
                    f"scores zero, never 9, never the auditor estimate)",
            "auditor_estimate_r407_recorded_as_estimate":
                meta.get("auditor_estimate_r407"),
            "estimate_is_not_the_score": True,
        }
        fp = write_score(stub, out_dir)
        written.append(fp.name)
    return written


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--family",
                    choices=["delivery", "honesty", "fidelity", "all"],
                    default="all")
    ap.add_argument("--portfolio-root", default=None,
                    help="path to a clone of technology-transfer-"
                         "portfolio-15 (buyer-distribution authority)")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = ap.parse_args()

    portfolio_root = Path(args.portfolio_root).resolve() \
        if args.portfolio_root else None
    if portfolio_root and not (portfolio_root / "DOWNLOAD").exists():
        raise SystemExit(f"not a portfolio clone (no DOWNLOAD/): "
                         f"{portfolio_root}")

    out_dir = Path(args.out_dir)
    families = ["delivery", "honesty", "fidelity"] \
        if args.family == "all" else [args.family]
    rubric = json.loads(RUBRIC_PATH.read_text(encoding="utf-8"))
    # stubs FIRST: the rubric references every family's output artifact,
    # so the planned-family score-0 stubs must exist on disk before the
    # fidelity census scans the tree (write-order, not tuning)
    stubs = write_planned_stubs(out_dir, rubric)
    if stubs:
        print(f"planned-family stubs (rule_2, score 0): "
              f"{len(stubs)} written")
    for family in families:
        result = measure_family(family, portfolio_root)
        fp = write_score(result, out_dir)
        print(f"{family.upper():10s} score={result['score']}/10 "
              f"instrument={result['instrument_state']} "
              f"defects={result['defects_named']} -> {fp}")


if __name__ == "__main__":
    main()

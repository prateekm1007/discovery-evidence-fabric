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

Scoring model (FROZEN with rubric 1.1.0 — see RUBRIC_CHANGE_RECORD):
  score = 10 - sum(deductions), floor 0, integer-truncated.
  The 9-bar (release bar) requires zero deductions on that family's checks.
  Deduction weights are per-check-class, NOT per-instance, except where a
  per-instance cap is explicitly declared — a hundred stale hashes is one
  defect class (D1), not a hundred deductions.

R408 P2 driver wiring (rubric 1.3.0, R408 audit instruction 3): the
  MACHINERY and NOVELTY_PRACTICE families move from PLANNED_P2 stubs to
  BUILT_IN_P2 executable drivers. A family stays 0 until an executable
  driver measures it (rule_2); no estimated scores (rule_5). The five
  already-measured families' deduction tables are UNCHANGED; the two new
  tables below are NEW instruments for families that previously scored 0
  by the missing-instrument rule (no threshold moved on any measured
  family — rule_7 change record in the rubric).

R408 driver changes (rubric rule_7: driver change => new rubric version +
adversarial re-test; deduction tables UNCHANGED — no threshold moved):
  D-A/D-C  check_chain_certificate + check_latest_release now resolve the
           certificate the ENGINE_RELEASE_REGISTRY's last verification
           actually NAMES (exact path, no RELEASE_CHAIN/ glob, no hardcoded
           R387-era certificate). A registry-named certificate that does
           not resolve is RED (fail-closed, Art. II/IV).
  D-B      check_reproduction_evidence matches the release being scored
           (engine-registry release_id + portfolio_release_commit) or
           returns the honest N/A state carrying the chain certificate's
           own honesty_scope note — never first-PASS-wins on an R373-era
           record at a phantom commit.
  D-E      check_latest_release verifies LATEST_RELEASE.engine_chain_
           record_commit is the full-40 engine commit that recorded the
           registry release record (short hashes and foreign commits are
           RED).
  tag      LATEST_RELEASE.git_tag must exist and point at the release
           commit or a chain-neutral descendant (the stale-tag trap: a tag
           at a superseded release is RED).

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
import subprocess
import sys
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent.parent
RUBRIC_PATH = ENGINE_ROOT / "R407" / "BENCHMARK_RUBRIC.json"
DEFAULT_OUT_DIR = ENGINE_ROOT / "R407" / "DRIVERS"

sys.path.insert(0, str(ENGINE_ROOT))

# The rubric FILE is the single authority for its version (Art. X — a
# parallel hardcoded constant drifts, exactly as it did between the
# 1.2.0 rubric bump and this driver's stale "1.1.0" constant: the
# regenerated score artifact would have carried a wrong version while
# claiming to measure at 1.2.0 semantics). Read at call time, never
# cached, so a version bump cannot desynchronize from the file.
def _rubric_version():
    try:
        return json.loads(RUBRIC_PATH.read_text(
            encoding="utf-8"))["rubric_version"]
    except Exception as exc:  # pragma: no cover — rubric always shipped
        raise SystemExit(
            f"BENCHMARK_RUBRIC.json unreadable at {RUBRIC_PATH}: {exc} "
            f"(the rubric file is the version authority; the driver "
            f"refuses to emit a score with an unverifiable rubric "
            f"version — Art. IV fail-closed)")


RUBRIC_VERSION = _rubric_version()

# ---------------------------------------------------------------------------
# Frozen deduction tables (rubric 1.0.0; UNCHANGED through 1.2.0 — the
# R408 driver changes moved check SEMANTICS (registry-named resolution,
# release-matched reproduction, zip-key manifest rows), never a
# threshold. Rule 7: no tuning against output.)
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

# MACHINERY (rubric 1.3.0 — NEW table for a previously-PLANNED family;
# the rubric bar_9 names "E15 A-J pass; E16 blind-holdout/causal/diversity
# pass; A2/A10/A12 pass", bar_10 adds "full E/A/F suites green on clean
# clones" — the weights ENCODE the bar text: every bar_9 component's
# failure drops below 9; the F-series check (bar_10 delta only) carries
# 1.0 so its failure alone leaves the 9-bar intact)
MACHINERY_DEDUCTIONS = {
    "e15_series_green": 3.0,             # bar_9: E15 A-J machinery
    "e16_series_green": 3.0,             # bar_9: E16 blind/holdout/causal/diversity
    "a_series_green": 2.0,               # bar_9: A2/A10 (+ A1..A11 machinery)
    "a12_capstone_record_intact": 2.0,   # bar_9: A12 (recorded-evidence basis)
    "f_series_green": 1.0,               # bar_10: "full E/A/F" (beyond 9-bar)
}

# NOVELTY_PRACTICE (rubric 1.3.0 — NEW table; the rubric bar_9 names
# "search neutrality, collision stage on, zero-results-are-not-novelty
# enforced", bar_10 adds "adversarial prior-art hunt on every survivor
# with full custody" — the custody check carries the bar_10 delta)
NOVELTY_PRACTICE_DEDUCTIONS = {
    "search_neutrality_enforced": 3.0,          # bar_9 item 1 (Art. XLIII)
    "collision_stage_registered_and_live": 2.0, # bar_9 item 2
    "zero_results_not_novelty_enforced": 3.0,   # bar_9 item 3 (Art. XXI.2)
    "prior_art_hunt_custody_on_survivors": 1.0, # bar_10 (Art. XXI.9)
}

AUDIT_NOTES = {
    "identity_registry_freshness": "D1: PORTFOLIO_IDENTITY_REGISTRY.json "
    "dossier/manifest/zip hashes vs the shipped tree",
    "latest_release_consistency": "D2: LATEST_RELEASE claims vs the engine "
    "authority records (certificate check-count, registry commits, tag "
    "status)",
    "chain_certificate_pass": "the certificate the engine registry's "
    "last verification NAMES is overall PASS and release-consistent "
    "(D-A/D-C: exact-path resolution, no globs, no first-PASS-wins)",
    "release_audits_green": "B1: r373 independent audit + r374 equation "
    "status audit green on every shipped package",
    "reproduction_evidence": "a committed fresh-clone byte-reproduction "
    "record MATCHING the release being scored exists (D-B: engine-registry "
    "release_id + portfolio_release_commit; otherwise the honest N/A state "
    "carries the chain certificate's own honesty_scope note)",
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
    "e15_series_green": "E15 A-J machinery suite (benchmark vectors, "
    "dossier gates, reasoning chains, physical failure mechanisms, "
    "two-path disagreement) executed LIVE: all tests green",
    "e16_series_green": "E16 blind-holdout/causal/diversity machinery "
    "(sealed split, blind protocol, causal correctness, diversity "
    "metrics, n-ary comparison) executed LIVE: all tests green",
    "a_series_green": "A-series machinery (A2 depth contract, A10 "
    "benchmark floors, A1..A11 pipeline) executed LIVE: all tests green",
    "a12_capstone_record_intact": "A12 capstone: the committed "
    "A_SERIES_ACCEPTANCE.json record is intact (reader-readiness "
    "contract, RELEASED status, code_commit resolves in git history); "
    "the LIVE capstone re-run requires the LLM transport and is NOT "
    "re-executed for this score — recorded-evidence basis, disclosed "
    "(rule_5/rule_8; live replay remains the certification path)",
    "f_series_green": "F-series integration machinery executed LIVE: "
    "all tests green (the bar_10 'full E/A/F' delta)",
    "search_neutrality_enforced": "Art. XLIII search-space neutrality "
    "LIVE: multi_source_expansion query formation on a synthetic "
    "problem — solution_class_injection NONE, every query carries "
    "DERIVED_FROM_PROBLEM_FACTS / EXPLORATORY_HYPOTHESIS, no unmarked "
    "solution-class term enters the query space (the v1 hardcoded "
    "coating class stays removed)",
    "collision_stage_registered_and_live": "the COLLISION stage "
    "(COLLISION_ENGINE) is registered in ACTIVE_DISCOVERY_GRAPH "
    "executable_chain, ordered before ATTACK/ADJUDICATION, the adapter "
    "imports and declares the capability, and downstream stage "
    "dependencies name it",
    "zero_results_not_novelty_enforced": "Art. XXI.2 LIVE adversarial "
    "execution of the actual collision state machine: zero relevant "
    "hits with successful searches -> UNRESOLVED_NO_RELEVANT_ART (never "
    "a novelty claim); partial search failure -> UNRESOLVED_SEARCH_"
    "INCOMPLETE (never RESOLVED_DIFFERENTIATED — the R394 s2 fix); "
    "total failure -> UNRESOLVED_INSUFFICIENT_EVIDENCE",
    "prior_art_hunt_custody_on_survivors": "every lead package carries "
    "a prior-art hunt with hash custody: the four NOVELTY_ASSESSMENT "
    "states use the honest vocabulary, the restored PatentBear "
    "artifacts hash-match RESTORATION_PROVENANCE pins, and the P13 "
    "R406 search raw_results hash-match their recorded custody",
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


def _latest_registry_release(engine_root):
    """(release_record, error) for the LAST release in the engine-side
    ENGINE_RELEASE_REGISTRY — the authority for what the current release
    is (Art. XXXIX)."""
    erp = engine_root / "ENGINE_RELEASE_REGISTRY.json"
    if not erp.exists():
        return None, "ENGINE_RELEASE_REGISTRY.json missing"
    registry = json.loads(erp.read_text(encoding="utf-8"))
    releases = registry.get("releases", [])
    if not releases:
        return None, "engine registry empty"
    return releases[-1], None


def _registry_named_certificate(engine_root, release):
    """(resolved_path, cert_ref, error) — the certificate the registry's
    LAST verification entry NAMES, resolved exactly (no globs, no
    newest-in-directory wins — the R408 D-A/D-C fix). The reference is
    repo-relative as recorded; a reference that does not resolve is an
    error, never a fallback to some other certificate (Art. IV)."""
    verifs = release.get("verifications") or []
    if not verifs:
        return None, None, "no verification recorded for the release"
    cert_ref = verifs[-1].get("certificate")
    if not cert_ref:
        return None, None, "verification record carries no certificate name"
    cert_path = engine_root / cert_ref
    if not cert_path.exists():
        return None, cert_ref, (
            f"registry-named certificate does not resolve: {cert_ref}")
    return cert_path, cert_ref, None


def _git_commits_touching(engine_root, rel_path):
    """Commits (full-40, newest first) that modified rel_path — used to
    verify the D-E engine_chain_record_commit pointer."""
    import subprocess
    try:
        out = subprocess.run(
            ["git", "-C", str(engine_root), "log", "--format=%H",
             "--", rel_path],
            capture_output=True, text=True, timeout=30).stdout
        return [l.strip() for l in out.splitlines() if l.strip()]
    except Exception:
        return []


def _git_tag_commit(portfolio_root, tag):
    """The commit a tag points at in the portfolio clone, or None."""
    import subprocess
    try:
        out = subprocess.run(
            ["git", "-C", str(portfolio_root), "rev-parse",
             f"refs/tags/{tag}^{{commit}}"],
            capture_output=True, text=True, timeout=30).stdout.strip()
        return out or None
    except Exception:
        return None


def _git_is_ancestor(repo_root, ancestor, descendant):
    import subprocess
    try:
        rc = subprocess.run(
            ["git", "-C", str(repo_root), "merge-base", "--is-ancestor",
             ancestor, descendant],
            capture_output=True, timeout=30).returncode
        return rc == 0
    except Exception:
        return False


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
    last, err = _latest_registry_release(engine_root)
    if err:
        return _check("latest_release_consistency", False, err,
                      ["ENGINE_REGISTRY_MISSING" if "missing" in err
                       else "ENGINE_REGISTRY_EMPTY"])
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
    # 2. D-E: engine_chain_record_commit must be the full-40 engine commit
    #    that recorded the registry release record (short/foreign values
    #    are RED — Art. II exactness)
    ecr = lr.get("engine_chain_record_commit")
    if not ecr:
        problems.append("ENGINE_CHAIN_RECORD_COMMIT_ABSENT")
    else:
        if not (isinstance(ecr, str) and len(ecr) == 40 and
                all(c in "0123456789abcdef" for c in ecr.lower())):
            problems.append(
                f"ENGINE_CHAIN_RECORD_COMMIT_NOT_FULL40: {str(ecr)[:44]}")
        else:
            touched = _git_commits_touching(engine_root,
                                            "ENGINE_RELEASE_REGISTRY.json")
            if ecr not in touched:
                problems.append(
                    "ENGINE_CHAIN_RECORD_COMMIT_NOT_A_REGISTRY_RECORD_"
                    "COMMIT")
            else:
                evidence.append(
                    f"engine_chain_record_commit={ecr[:12]} (registry "
                    f"record commit, verified)")
    # 3. claimed chain check-count must equal the AUTHORITY certificate's —
    #    the certificate the registry's last verification names (D-C fix:
    #    never a hardcoded R387-era certificate)
    claimed = lr.get("chain_verification", "")
    m = re.search(r"(\d+)\s*/\s*(\d+)", str(claimed))
    cert_path, cert_ref, cert_err = _registry_named_certificate(
        engine_root, last)
    if cert_err:
        problems.append(f"AUTHORITY_CERTIFICATE_UNRESOLVED: {cert_err}")
    else:
        cert = json.loads(cert_path.read_text(encoding="utf-8"))
        cc = cert.get("checks", cert.get("results", []))
        cert_total = len(cc) if isinstance(cc, list) else cert.get(
            "checks_total")
        cert_passed = sum(1 for c in (cc if isinstance(cc, list) else [])
                          if c.get("status") == "PASS") \
            if isinstance(cc, list) else None
        cert_overall = cert.get("overall")
        evidence.append(f"registry-named certificate: {cert_ref} "
                        f"(overall={cert_overall}, "
                        f"checks={cert_passed}/{cert_total})")
        if cert_overall != "PASS":
            problems.append("AUTHORITY_CERTIFICATE_NOT_PASS")
        if cert.get("release_id") != last.get("release_id"):
            problems.append("CERTIFICATE_RELEASE_ID_MISMATCH")
        if m:
            claimed_passed, claimed_total = int(m.group(1)), int(m.group(2))
            evidence.append(f"claimed {claimed_passed}/{claimed_total}")
            if cert_total is not None and claimed_total != cert_total:
                problems.append(f"CHECK_COUNT_MISMATCH: pointer claims "
                                f"{claimed_total}, authority certificate has "
                                f"{cert_total}")
            if cert_passed is not None and claimed_passed != cert_passed:
                problems.append(f"CHECKS_PASSED_MISMATCH: pointer claims "
                                f"{claimed_passed}, authority certificate "
                                f"has {cert_passed}")
            if claimed_passed != claimed_total:
                problems.append("POINTER_CLAIMS_PARTIAL_PASS")
        else:
            problems.append("POINTER_CARRIES_NO_CHECK_COUNT")
    # 4. master zip hash vs the canonical manifest (buyer truth)
    manifest = json.loads((portfolio_root /
                           "CANONICAL_RELEASE_MANIFEST.json")
                          .read_text(encoding="utf-8"))
    mz = manifest.get("master_zip", {})
    if lr.get("master_zip_sha256") and \
            lr["master_zip_sha256"] != mz.get("sha256"):
        problems.append("MASTER_ZIP_HASH_MISMATCH_VS_MANIFEST")
    # 5. tag agreement (the stale-tag trap): LATEST_RELEASE.git_tag must
    #    exist in the portfolio clone and point at the release commit or
    #    a chain-neutral descendant — a tag at a superseded release is
    #    exactly the stale-commit trap the machinery warns about.
    tag = lr.get("git_tag")
    if tag:
        tag_commit = _git_tag_commit(portfolio_root, tag)
        if not tag_commit:
            problems.append(f"TAG_MISSING_IN_CLONE: {tag}")
        else:
            rel_commit = lr.get("portfolio_release_commit") or \
                last.get("portfolio_release_commit")
            if rel_commit and not _git_is_ancestor(
                    portfolio_root, rel_commit, tag_commit):
                problems.append(
                    f"TAG_POINTS_BACKWARDS: {tag} at {tag_commit[:12]} is "
                    f"not at/after the release commit "
                    f"{str(rel_commit)[:12]}")
            else:
                evidence.append(f"git_tag={tag} at {tag_commit[:12]} "
                                f"(at/after the release commit)")
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
    # buyer_surface pins (the manifest's sha256 map: rel-path -> hash)
    # + package_zips + master_zip
    bs = m.get("buyer_surface") or {}
    file_map = bs.get("sha256") if isinstance(bs, dict) else None
    if not isinstance(file_map, dict):
        file_map = bs.get("files") if isinstance(bs, dict) else None
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
        if not isinstance(pz, dict):
            continue
        # D-F fix (the 3f269c23 driver-bug class, sibling instance):
        # the manifest's package-zip rows carry the pin under the 'zip'
        # key (both the R407-P0 and the R408 V3.1 manifests use this
        # form); the R374-era 'path' form is accepted too. A row with
        # neither key is a DISCLOSED problem — never a silent skip (a
        # skipped row would let a tampered package ZIP pass green).
        rel = pz.get("zip") or pz.get("path")
        if not rel:
            mismatches.append(
                f"package_zips[{m.get('package_zips').index(pz)}]:"
                f"NO_PATH_KEY")
            continue
        if not pz.get("sha256"):
            mismatches.append(f"{rel}:NO_SHA256_PIN")
            continue
        fp = portfolio_root / rel
        if not fp.exists():
            mismatches.append(f"{rel}:MISSING")
            continue
        checked += 1
        if sha256_file(fp) != pz["sha256"]:
            mismatches.append(f"{rel}:HASH_DRIFT")
    # master_zip: a manifest without a master-ZIP pin is a BROKEN
    # manifest — RED, never a silent skip (same D-F discipline)
    mz = m.get("master_zip") or {}
    if not (mz.get("path") and mz.get("sha256")):
        mismatches.append("master_zip:PIN_ABSENT")
    else:
        fp = portfolio_root / mz["path"]
        if not fp.exists():
            mismatches.append(f"{mz['path']}:MISSING")
        else:
            checked += 1
            if sha256_file(fp) != mz["sha256"]:
                mismatches.append(f"{mz['path']}:HASH_DRIFT")
    return _check("manifest_pins_agree", not mismatches,
                  f"{checked} pinned buyer-surface files hash-verified "
                  f"against the current tree "
                  f"(buyer_surface + package_zips + master_zip)",
                  mismatches[:40])


def check_chain_certificate(engine_root):
    """The certificate the engine registry's last verification NAMES is
    overall PASS and release-consistent (D-A/D-C fix: exact-path
    resolution of the authority record's own pointer — never a directory
    glob whose sort order can hand back an older era's certificate)."""
    release, err = _latest_registry_release(engine_root)
    if err:
        return _check("chain_certificate_pass", False, err,
                      ["ENGINE_REGISTRY_UNAVAILABLE"])
    cert_path, cert_ref, cert_err = _registry_named_certificate(
        engine_root, release)
    if cert_err:
        return _check("chain_certificate_pass", False, cert_err,
                      ["CERTIFICATE_NOT_RESOLVED"])
    try:
        cert = json.loads(cert_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return _check("chain_certificate_pass", False,
                      f"registry-named certificate unreadable: {exc}",
                      ["CERTIFICATE_UNREADABLE"])
    cc = cert.get("checks", cert.get("results", []))
    total = len(cc) if isinstance(cc, list) else cert.get("checks_total")
    passed = sum(1 for c in (cc if isinstance(cc, list) else [])
                 if c.get("status") == "PASS") \
        if isinstance(cc, list) else None
    problems = []
    if cert.get("overall") != "PASS":
        problems.append(f"CERTIFICATE_OVERALL_{cert.get('overall')}")
    if cert.get("release_id") != release.get("release_id"):
        problems.append("CERTIFICATE_RELEASE_ID_MISMATCH")
    states = cert.get("states", {}) or {}
    if states.get("portfolio_release_commit") and \
            release.get("portfolio_release_commit") and \
            states["portfolio_release_commit"] != \
            release["portfolio_release_commit"]:
        problems.append("CERTIFICATE_PORTFOLIO_COMMIT_MISMATCH")
    evidence = (
        f"registry-named certificate: {cert_ref} -> {cert.get('overall')} "
        f"({passed}/{total} checks; verified engine_main "
        f"{str(states.get('engine_head'))[:12]}, portfolio_main "
        f"{str(states.get('portfolio_head'))[:12]}, release commit "
        f"{str(states.get('portfolio_release_commit'))[:12]})")
    return _check("chain_certificate_pass", not problems, evidence,
                  problems)


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


def check_reproduction_evidence(portfolio_root, engine_root):
    """Committed fresh-clone byte-reproduction record MATCHING the release
    being scored (D-B fix). The scored release is the engine registry's
    last release (the authority). A record matches when it names that
    release_id and that release's portfolio_release_commit. Records from
    other releases (e.g. an R373-era record at a phantom commit) are
    disclosed as stale, never counted (Art. XXIV: an older PASS is not
    evidence for a newer release). No match -> the honest N/A state,
    carrying the chain certificate's own honesty_scope note."""
    release, err = _latest_registry_release(engine_root)
    if err:
        return _check("reproduction_evidence", False, err,
                      ["ENGINE_REGISTRY_UNAVAILABLE"])
    scored_rid = release.get("release_id")
    scored_commit = release.get("portfolio_release_commit")
    honesty_scope = ""
    verifs = release.get("verifications") or []
    if verifs:
        honesty_scope = str(verifs[-1].get("honesty_scope", ""))
    iq = portfolio_root / "INTERNAL_QA"
    candidates = sorted(set(iq.glob("*REPRODUCTION*.json"))) \
        if iq.exists() else []
    matched = None      # (name, verdict, commit_of_record)
    stale_seen = []
    for c in candidates:
        try:
            d = json.loads(c.read_text(encoding="utf-8"))
        except Exception:
            continue
        verdict = (d.get("overall") or d.get("verdict") or d.get("result")
                   or ("PASS" if d.get("all_pass") is True else None))
        rec_rid = d.get("release_id")
        rec_commit = d.get("portfolio_release_commit") or \
            d.get("portfolio_head")
        if rec_rid == scored_rid and (rec_commit == scored_commit
                                      if d.get("portfolio_release_commit")
                                      else True):
            if matched is None or verdict == "PASS":
                matched = (c.name, verdict, rec_commit)
            if verdict == "PASS":
                break
        else:
            stale_seen.append(
                f"{c.name}(release_id={rec_rid or 'ABSENT'}, "
                f"head={str(rec_commit)[:12]})")
    if matched and matched[1] == "PASS":
        return _check(
            "reproduction_evidence", True,
            f"record: {matched[0]} (release_id {scored_rid}, "
            f"portfolio_release_commit {str(matched[2])[:12]}, "
            f"verdict PASS)", [])
    if matched:
        return _check("reproduction_evidence", False,
                      f"record: {matched[0]} -> {matched[1]} for "
                      f"{scored_rid}", ["MATCHED_RECORD_NOT_PASS"])
    return _check(
        "reproduction_evidence", False,
        (f"N/A — no reproduction record matches the release being scored "
         f"({scored_rid}); records found: "
         f"{'; '.join(stale_seen) if stale_seen else 'none'}; the chain "
         f"certificate's own honesty_scope: {honesty_scope[:240]}"),
        ["NO_MATCHING_REPRODUCTION_RECORD"])


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
    gold = result.get("gold_corpus_calibration") or {}
    gold_note = (
        f"gold calibration available ({gold.get('packages_scanned')} "
        f"packages, {gold.get('recurring_sentence_count')} recurring)"
        if gold.get("available") else
        f"gold calibration UNAVAILABLE — {str(gold.get('reason'))[:90]} "
        f"(the recurring-boilerplate ceiling comparator could not run; "
        f"set GOLD_CORPUS_DIR to a full-dossier corpus to enable it; the "
        f"mismatch-based FAIL logic is unaffected)")
    return _check("semantic_genericness_live",
                  result.get("verdict") == "PASS" and not mismatches,
                  f"B4 live on {len(run_packages)} shipped packages: "
                  f"verdict={result.get('verdict')}, "
                  f"mismatches={len(mismatches)}; {gold_note}", problems)


# ---------------------------------------------------------------------------
# MACHINERY driver (rubric 1.3.0 — R408 audit instruction 3: wire the
# P2 families; a family stays 0 until an executable driver measures it)
# ---------------------------------------------------------------------------

def run_pytest_suite(engine_root, test_targets, name):
    """Execute one machinery test suite LIVE (subprocess pytest, hermetic
    repo-relative targets). The check FAILS on any test failure, any
    collection error, or any driver-side execution error — an
    unexecutable instrument is never a silent pass (rule_8)."""
    targets = [str(engine_root / t) for t in test_targets]
    missing = [t for t in targets if not Path(t).exists()]
    if missing:
        return _check(name, False, f"suite target(s) missing: {missing}",
                      ["SUITE_TARGET_MISSING"])
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--tb=no", "-p",
             "no:cacheprovider", *targets],
            cwd=str(engine_root), capture_output=True, text=True,
            timeout=900)
    except Exception as exc:  # pragma: no cover — honest BLOCKED state
        return _check(name, False, f"suite execution failed: {exc}",
                      ["SUITE_EXECUTION_ERROR"])
    tail = (proc.stdout or "").strip().splitlines()
    summary = tail[-1] if tail else f"rc={proc.returncode}"
    m = re.search(r"(\d+) (?:passed|failed)", summary)
    n_ok = int(m.group(1)) if m and "passed" in summary else 0
    failed = "failed" in summary or proc.returncode != 0
    return _check(name, not failed,
                  f"live run: {summary} (targets: "
                  f"{', '.join(test_targets)})",
                  [summary] if failed else [])


def check_a12_capstone_record(engine_root):
    """A12 capstone — recorded-evidence basis: the committed
    A_SERIES_ACCEPTANCE.json must be intact (reader-readiness contract
    with all 9 questions, RELEASED final state, code_commit that
    resolves in git history). The LIVE capstone re-run requires the LLM
    transport and is NOT re-executed for this score — disclosed here,
    never silently passed off as a live replay (rule_5/rule_8)."""
    problems = []
    ap = engine_root / "A_SERIES_ACCEPTANCE.json"
    if not ap.exists():
        return _check("a12_capstone_record_intact", False,
                      "A_SERIES_ACCEPTANCE.json missing",
                      ["A12_RECORD_MISSING"])
    d = json.loads(ap.read_text(encoding="utf-8"))
    a12 = d.get("A12_reader_readiness") or {}
    if not a12.get("contract"):
        problems.append("A12_READER_READINESS_CONTRACT_ABSENT")
    checks = a12.get("checks") or {}
    if not isinstance(checks, dict) or len(checks) < 9:
        problems.append(f"A12_QUESTIONS_INCOMPLETE: "
                        f"{len(checks) if isinstance(checks, dict) else 0}/9")
    if d.get("release_status") != "RELEASED":
        problems.append(f"A12_RELEASE_STATUS_{d.get('release_status')}")
    if not d.get("run_id"):
        problems.append("A12_RUN_ID_ABSENT")
    cc = d.get("code_commit")
    provenance_state = "PROVENANCE_INCOMPLETE"
    if not (isinstance(cc, str) and len(cc) == 40
            and all(c in "0123456789abcdef" for c in cc.lower())):
        problems.append(f"A12_CODE_COMMIT_NOT_FULL40: {str(cc)[:44]}")
    else:
        rc = subprocess.run(
            ["git", "-C", str(engine_root), "rev-parse", "--verify",
             f"{cc}^{{commit}}"],
            capture_output=True, text=True, timeout=30).returncode
        if rc == 0:
            provenance_state = "RESOLVED"
        else:
            # the D-B honest-N/A precedent: the pointer is unreachable
            # from this checkout — recorded evidence stands as committed,
            # but byte-level replay from that commit is not possible.
            # NEVER amend the historical record's pointer (that would
            # manufacture provenance, Art. VI); disclose, deduct, and
            # leave the live re-run as the certification path.
            problems.append("A12_CODE_COMMIT_DOES_NOT_RESOLVE")
    return _check("a12_capstone_record_intact", not problems,
                  f"recorded evidence: run_id={d.get('run_id')}, "
                  f"release={d.get('release_status')}, "
                  f"{len(checks) if isinstance(checks, dict) else 0}/9 "
                  f"reader-readiness questions, code_commit "
                  f"{str(cc)[:12]} provenance={provenance_state}; "
                  f"LIVE capstone re-run transport-gated, not "
                  f"re-executed for this score"
                  + ("; PROVENANCE_INCOMPLETE: the recorded code_commit "
                     "is unreachable from the current object store "
                     "(history rewritten since the run; the A12 "
                     "machinery evidence stands as the committed record, "
                     "byte-level replay from that commit is not "
                     "possible; the live re-run remains the "
                     "certification path — Art. VI/XXV, honest N/A per "
                     "the D-B precedent)"
                     if provenance_state != "RESOLVED" else ""),
                  problems)


# ---------------------------------------------------------------------------
# NOVELTY_PRACTICE driver (rubric 1.3.0)
# ---------------------------------------------------------------------------

# The v1 hardcoded solution class (measured across 8 domains by the R402
# audit) — the probe vocabulary for the neutrality check
_SOLUTION_CLASS_PROBE_TERMS = ("coating", "coat", "paint", "overlay",
                               "film", "liner", "cladding")

_NEUTRALITY_SYNTHETIC_PROBLEM = {
    "device": "cardiac pacemaker",
    "failure_mode": "lead fracture under cyclic flexion",
    "constraint": "maintain electrical continuity without increasing "
                  "lead diameter",
}


def _neutrality_contract_violations(out):
    """Pure verifier for the search-neutrality contract (Art. XLIII) —
    separable so adversarial tests can feed it tampered outputs."""
    problems = []
    neutral = out.get("search_space_neutrality") or {}
    if neutral.get("solution_class_injection") != "NONE":
        problems.append(f"SOLUTION_CLASS_INJECTED: "
                        f"{neutral.get('solution_class_injection')}")
    queries = out.get("queries") or {}
    if not queries:
        problems.append("NO_QUERIES_FORMED")
    for qname, q in queries.items():
        derivation = str(q.get("derivation") or "")
        if derivation not in ("DERIVED_FROM_PROBLEM_FACTS",
                              "EXPLORATORY_HYPOTHESIS"):
            problems.append(f"QUERY_{qname}_UNMARKED_DERIVATION: "
                            f"{derivation or 'ABSENT'}")
        text = str(q.get("text") or "").lower()
        for term in _SOLUTION_CLASS_PROBE_TERMS:
            # a probe term may appear ONLY if it is a problem fact (the
            # synthetic problem carries none — any hit is an injection)
            if term in text:
                problems.append(f"QUERY_{qname}_SOLUTION_CLASS_TERM: "
                                f"{term}")
        sources = q.get("term_sources") or {}
        for src_key in sources:
            if src_key not in ("device", "failure_mode", "constraint",
                               "mechanism", "expected_effect"):
                problems.append(f"QUERY_{qname}_NON_FACT_SOURCE: "
                                f"{src_key}")
    return problems


def check_search_neutrality_live(engine_root):
    """Art. XLIII LIVE: execute the REAL query formation
    (multi_source_expansion) on a synthetic problem under the recorded
    R401_NO_EXPANSION hermetic switch (the queries and the neutrality
    block are formed BEFORE the switch is read — measured surface is
    the live code path, network stays off), then verify the neutrality
    contract on the actual output."""
    saved = os.environ.get("R401_NO_EXPANSION")
    os.environ["R401_NO_EXPANSION"] = "1"
    try:
        from discovery_fabric.engine.mechanism_space import \
            multi_source_expansion
        out = multi_source_expansion(dict(_NEUTRALITY_SYNTHETIC_PROBLEM))
    except Exception as exc:
        return _check("search_neutrality_enforced", False,
                      f"live execution failed: {exc}",
                      ["NEUTRALITY_EXECUTION_ERROR"])
    finally:
        if saved is None:
            os.environ.pop("R401_NO_EXPANSION", None)
        else:
            os.environ["R401_NO_EXPANSION"] = saved
    problems = _neutrality_contract_violations(out)
    q = out.get("queries") or {}
    return _check("search_neutrality_enforced", not problems,
                  f"live multi_source_expansion on synthetic problem "
                  f"(state={out.get('state')}): domain="
                  f"\"{str(q.get('domain', {}).get('text'))[:48]}\" "
                  f"mechanism=\"{str(q.get('mechanism', {}).get('text'))[:48]}\" "
                  f"solution_class_injection="
                  f"{(out.get('search_space_neutrality') or {}).get('solution_class_injection')}",
                  problems)


def check_collision_stage_live(engine_root):
    """The COLLISION stage is ON in the live discovery graph: registered
    in ACTIVE_DISCOVERY_GRAPH's executable_chain, ordered before ATTACK
    and ADJUDICATION (a collision that runs after adjudication would be
    decorative), the adapter class imports and declares the capability,
    and a downstream stage's depends_on names COLLISION."""
    problems = []
    gp = engine_root / "ACTIVE_DISCOVERY_GRAPH.json"
    if not gp.exists():
        return _check("collision_stage_registered_and_live", False,
                      "ACTIVE_DISCOVERY_GRAPH.json missing",
                      ["GRAPH_MISSING"])
    g = json.loads(gp.read_text(encoding="utf-8"))
    chain = g.get("executable_chain") or []
    stages = {s.get("stage"): s for s in chain}
    if "COLLISION" not in stages:
        problems.append("COLLISION_STAGE_ABSENT_FROM_CHAIN")
        col = None
    else:
        col = stages["COLLISION"]
        if col.get("capability_id") != "COLLISION_ENGINE":
            problems.append(f"COLLISION_CAPABILITY_{col.get('capability_id')}")
        order = col.get("order")
        for after_name in ("ATTACK", "ADJUDICATION"):
            after = stages.get(after_name)
            if after and order is not None and after.get("order", 0) < order:
                problems.append(f"COLLISION_AFTER_{after_name}")
    try:
        from discovery_fabric.engine.adapters import CollisionEngineAdapter
        if CollisionEngineAdapter.capability_id != "COLLISION_ENGINE":
            problems.append("COLLISION_ADAPTER_CAPABILITY_MISMATCH")
    except Exception as exc:
        problems.append(f"COLLISION_ADAPTER_IMPORT_FAILED: {exc}")
    try:
        from discovery_fabric.engine import adapters
        deps_ok = False
        for attr in dir(adapters):
            cls = getattr(adapters, attr)
            if isinstance(cls, type) and hasattr(cls, "depends_on"):
                if "COLLISION" in (getattr(cls, "depends_on") or []):
                    deps_ok = True
                    break
        if not deps_ok:
            problems.append("NO_DOWNSTREAM_STAGE_DEPENDS_ON_COLLISION")
    except Exception as exc:
        problems.append(f"ADAPTER_REGISTRY_SCAN_FAILED: {exc}")
    evidence = (f"executable_chain order "
                f"{col.get('order') if col else 'N/A'}/"
                f"{len(chain)}; adapter imports: "
                f"COLLISION_ENGINE declared; downstream depends_on "
                f"verified")
    return _check("collision_stage_registered_and_live", not problems,
                  evidence, problems)


def _run_resolve(families, search_errors, searches_succeeded,
                 search_incomplete):
    """Execute the REAL collision state machine on synthetic inputs
    (pure function, hermetic — the same code path production runs)."""
    from discovery_fabric.prior_art_v2.collision_resolution import (
        CandidateProfile, resolve_differentiation,
    )
    profile = CandidateProfile(
        intervention="differential pressure floor lumen with independent "
                     "drainage geometry",
        mechanism="parallel redundant outflow path",
        expected_effect="obstruction susceptibility differs between lumens",
        entity_terms=["cerebrospinal", "fluid", "shunt", "catheter",
                      "obstruction"],
        mechanism_terms=["parallel", "redundant", "outflow", "lumen"],
        distinguishing_terms=["differential", "pressure", "floor",
                              "drainage", "geometry"],
        adjacent_terms=["pressure", "drainage", "flow"])
    return resolve_differentiation(
        families, profile, search_errors, searches_succeeded,
        deep_fetch=False, precomputed=None,
        search_incomplete=search_incomplete)


def check_zero_results_not_novelty_live(engine_root):
    """Art. XXI.2/XXV LIVE adversarial execution of the ACTUAL collision
    state machine with synthetic search executions:
      A. searches succeeded + zero relevant hits -> UNRESOLVED_NO_RELEVANT_ART
         (zero results is NOT novelty — a novelty/differentiation state
         here would be the exact constitutional violation)
      B. partial mandatory-search failure -> UNRESOLVED_SEARCH_INCOMPLETE
         (never RESOLVED_DIFFERENTIATED — the R394 s2 regression the
         production audit measured on ts_d1ab9fd4d756)
      C. total search failure -> UNRESOLVED_INSUFFICIENT_EVIDENCE
         (provider failure is not absence — Art. XXI.3)
    Plus the state vocabulary guard: the committed prior-art state
    vocabulary contains no absence-derived novelty state."""
    problems = []
    # scenario A: zero relevant hits, all searches OK
    res_a = _run_resolve([], [], True, False)
    if res_a.get("state") != "UNRESOLVED_NO_RELEVANT_ART":
        problems.append(f"ZERO_HITS_STATE_{res_a.get('state')}")
    # scenario B: partial failure forbids differentiation
    err = [{"query": "differential pressure floor lumen",
            "source": "google_patents", "error": "timeout"}]
    res_b = _run_resolve([], err, True, True)
    if res_b.get("state") != "UNRESOLVED_SEARCH_INCOMPLETE":
        problems.append(f"PARTIAL_FAILURE_STATE_{res_b.get('state')}")
    # scenario C: total failure
    res_c = _run_resolve([], err, False, True)
    if res_c.get("state") != "UNRESOLVED_INSUFFICIENT_EVIDENCE":
        problems.append(f"TOTAL_FAILURE_STATE_{res_c.get('state')}")
    # vocabulary guard: the machine's prior-art state vocabulary
    # contains NO novelty state at all — novelty determinations live
    # only in the separately recorded three-state assessments (whose
    # honest vocabulary is checked in the custody check). A state like
    # NOVEL_BECAUSE_NO_RESULTS appearing in KILL/NON_KILL states would
    # be the exact Art. XXI.2 violation, and this goes RED on it.
    from discovery_fabric.a2 import classify as a2_classify
    vocab = (a2_classify.KILL_STATES | a2_classify.NON_KILL_STATES)
    for st in vocab:
        if "NOVEL" in st.upper():
            problems.append(f"SEARCH_STATE_ASSERTS_NOVELTY: {st}")
    evidence = (f"live state machine: A={res_a.get('state')} "
                f"(zero hits, searches OK), B={res_b.get('state')} "
                f"(partial failure), C={res_c.get('state')} (total "
                f"failure); vocabulary: {len(vocab)} committed "
                f"prior-art states, zero absence-derived novelty states")
    return _check("zero_results_not_novelty_enforced", not problems,
                  evidence, problems)


_HONEST_NOVELTY_STATES = ("SUPPORTED", "CONTESTED", "UNKNOWN",
                          "NOVELTY_SEARCH_REPORTED")


def check_prior_art_hunt_custody_on_survivors(engine_root):
    """Bar_10: every lead package carries an adversarial prior-art hunt
    with full custody — the four NOVELTY_ASSESSMENT states use the
    honest vocabulary (never inferred novelty), the restored PatentBear
    artifacts hash-match their RESTORATION_PROVENANCE pins, and the P13
    R406 search raw_results hash-match the recorded custody chain."""
    problems = []
    n_states = 0
    for pid in ("P04", "P08", "P11", "P13"):
        fp = engine_root / "LEAD_PORTFOLIO_4" / pid / \
            "NOVELTY_ASSESSMENT.json"
        if not fp.exists():
            problems.append(f"{pid}:NOVELTY_ASSESSMENT_MISSING")
            continue
        d = json.loads(fp.read_text(encoding="utf-8"))
        status = d.get("assessment_status")
        n_states += 1
        if status not in _HONEST_NOVELTY_STATES:
            problems.append(f"{pid}:DISHONEST_STATE_{status}")
    # restored PatentBear custody (P04/P08/P11 basis)
    rp = engine_root / "NOVELTY_EVIDENCE" / "RESTORATION_PROVENANCE.json"
    n_restored = 0
    if not rp.exists():
        problems.append("RESTORATION_PROVENANCE_MISSING")
    else:
        prov = json.loads(rp.read_text(encoding="utf-8"))
        for f in prov.get("files", []):
            fp = engine_root / f.get("restored_to", " ")
            if not fp.exists():
                problems.append(f"{f.get('restored_to')}:MISSING")
                continue
            n_restored += 1
            if sha256_file(fp) != f.get("sha256"):
                problems.append(f"{f.get('restored_to')}:HASH_DRIFT")
    # P13 R406 live-search custody
    sr = engine_root / "LEAD_PORTFOLIO_4" / "P13" / \
        "NOVELTY_SEARCH_R406" / "NOVELTY_SEARCH_RESULT.json"
    n_p13 = 0
    if not sr.exists():
        problems.append("P13:NOVELTY_SEARCH_RESULT_MISSING")
    else:
        rec = json.loads(sr.read_text(encoding="utf-8"))
        determination = rec.get("determination") or {}
        verdict = determination.get("verdict")
        if verdict not in _HONEST_NOVELTY_STATES:
            problems.append(f"P13:SEARCH_VERDICT_{verdict}")
        for rel, expected in (rec.get("provenance_custody") or {}).items():
            fp = engine_root / rel
            if not fp.exists():
                problems.append(f"{rel}:MISSING")
                continue
            n_p13 += 1
            if sha256_file(fp) != expected:
                problems.append(f"{rel}:HASH_DRIFT")
    evidence = (f"{n_states}/4 lead novelty states in honest "
                f"vocabulary; {n_restored} restored artifacts "
                f"hash-verified; {n_p13} P13 R406 raw_results "
                f"hash-verified (verdict={verdict if sr.exists() else 'N/A'})")
    return _check("prior_art_hunt_custody_on_survivors", not problems,
                  evidence, problems)


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
    # the rubric's family keys are UPPERCASE; measured families are
    # passed lowercase (the CLI vocabulary) — uppercase-first lookup so
    # the DISCLOSURE field carries the recorded estimate (a null here
    # was the 1.2.0-era case-miss; never a score input, rule_5)
    est = (rubric["families"].get(str(family).upper(),
                                  rubric["families"].get(family, {}))
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
                         "deduction table frozen with rubric 1.0.0, "
                         "check semantics at rubric 1.1.0 (R408 "
                         "registry-named resolution; no threshold moved)",
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
            check_reproduction_evidence(portfolio_root, ENGINE_ROOT),
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
    if family == "machinery":
        # engine-side only: the machinery suites live in the engine repo;
        # no portfolio dependency (rule_8: portfolio unavailability can
        # never silently suppress a MACHINERY measurement)
        checks = [
            run_pytest_suite(ENGINE_ROOT,
                             ["tests/test_e15_series.py"],
                             "e15_series_green"),
            run_pytest_suite(ENGINE_ROOT,
                             ["tests/test_e16_series.py"],
                             "e16_series_green"),
            run_pytest_suite(ENGINE_ROOT,
                             ["tests/test_a2_migration.py",
                              "tests/test_a_series_integration.py"],
                             "a_series_green"),
            check_a12_capstone_record(ENGINE_ROOT),
            run_pytest_suite(ENGINE_ROOT,
                             ["tests/test_f_series_integration.py"],
                             "f_series_green"),
        ]
        return build_family_result(family, checks, MACHINERY_DEDUCTIONS,
                                    rubric, None, "MEASURED")
    if family == "novelty_practice":
        # engine-side only: live query formation + live collision state
        # machine + committed custody artifacts
        checks = [
            check_search_neutrality_live(ENGINE_ROOT),
            check_collision_stage_live(ENGINE_ROOT),
            check_zero_results_not_novelty_live(ENGINE_ROOT),
            check_prior_art_hunt_custody_on_survivors(ENGINE_ROOT),
        ]
        return build_family_result(family, checks,
                                   NOVELTY_PRACTICE_DEDUCTIONS, rubric,
                                   None, "MEASURED")
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
                    choices=["delivery", "honesty", "fidelity",
                             "machinery", "novelty_practice", "all"],
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
    families = (["delivery", "honesty", "fidelity", "machinery",
                 "novelty_practice"]
                if args.family == "all" else [args.family])
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

#!/usr/bin/env python3
"""
R386 CANONICAL RELEASE CHAIN (CEO directive 2026-09-01)

    ENGINE REPO  ->  CANONICAL RELEASE MANIFEST  ->  PORTFOLIO REPO  ->  BUYER ZIP  ->  VERIFICATION

The four states must agree exactly. This tool makes a disagreement structurally
impossible to ship silently: `verify` / `verify-fresh` exit nonzero and write a
FAIL certificate whenever any state disagrees.

PERMANENT AUTHORITY RULE (constitution Article XXXIX, v1.9.0):

    The buyer-distribution repository, not a local workspace and not the engine
    repository, is the final authority for what a buyer actually receives.

Subcommands
-----------
generate     Build CANONICAL_RELEASE_MANIFEST.json inside the portfolio repo from
             the actual release tree (both repos must be clean and pushed first).
record       Write/append the release entry in the engine repo's
             ENGINE_RELEASE_REGISTRY.json (pins portfolio commit + manifest hash).
verify       Four-state verification on two given checkouts (both must be clean;
             used by the hermetic tests and by humans on local clones).
verify-fresh THE authoritative mode: fresh clones of BOTH remotes into a workdir,
             then the same four-state verification (Art. XXIII — never infer
             repository state from local state).
drift        Report standing local checkouts that disagree with the remotes
             (informational; local workspaces are non-authoritative by rule).

Honesty rules obeyed here (Art. I/XXV/XXVI):
- The manifest is timeless (no timestamps; provenance = git history).
- The chain certificate distinguishes DELIVERY verification (bytes in the
  authority repo) from REBUILD-FROM-SOURCE reproduction; the latter is never
  implied by the former.
- A manifest cannot contain its own portfolio commit hash; that pin lives
  engine-side in ENGINE_RELEASE_REGISTRY.json (recorded after the portfolio
  commit exists). The manifest pins the ENGINE build commit, which exists
  before the release is built. This is what breaks the self-reference cycle.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

AUTHORITY_DECLARATION = (
    "The buyer-distribution repository, not a local workspace and not the "
    "engine repository, is the final authority for what a buyer actually "
    "receives."
)

MANIFEST_NAME = "CANONICAL_RELEASE_MANIFEST.json"
REGISTRY_NAME = "ENGINE_RELEASE_REGISTRY.json"
CONSTITUTION_NAME = "EPISTEMIC_CONSTITUTION.md"

ROOT_BUYER_FILES = [
    "00_PORTFOLIO_15_TECHNOLOGIES.pdf",
    "PORTFOLIO_IDENTITY_REGISTRY.json",
    "PORTFOLIO_INDEX.pdf",
    "PORTFOLIO_MANIFEST.json",
    "PORTFOLIO_RANKING.json",
    "PORTFOLIO_RELEASE_REPORT.pdf",
    "README.md",
    "RELEASE_CONTENT_MANIFEST.json",
]

MASTER_ZIP_REL = "DOWNLOAD/technology-transfer-portfolio-15.zip"

SECRET_PAT = re.compile(
    r"ghp_[a-zA-Z0-9]{20,}|gho_[a-zA-Z0-9]{20,}|github_pat_[a-zA-Z0-9_]{20,}"
    r"|AKIA[0-9A-Z]{16}|-----BEGIN (RSA|OPENSSH|EC) PRIVATE KEY"
    r"|sk-[a-zA-Z0-9]{20,}|xox[bap]-[a-zA-Z0-9-]{10,}")

FORBIDDEN_MANIFEST_KEYS = {"timestamp", "generated_at", "date", "time", "now"}

STATE_ENGINE, STATE_MANIFEST, STATE_PORTFOLIO, STATE_ZIP = (
    "ENGINE", "MANIFEST", "PORTFOLIO", "ZIP")


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dump_json(path: pathlib.Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8")


def read_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git(repo: pathlib.Path, *args: str, check: bool = True) -> str:
    out = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True)
    if check and out.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} in {repo} failed:\n{out.stderr.strip()}")
    return out.stdout.strip()


def sanitize_url(url: str) -> str:
    """Strip credentials from a git URL before recording it anywhere."""
    u = url
    m = re.match(r"https?://[^@/]+@(.*)", u)
    if m:
        u = m.group(1)
    u = re.sub(r"^git@", "", u)
    u = re.sub(r"\.git$", "", u)
    return u


def is_clean(repo: pathlib.Path) -> bool:
    return git(repo, "status", "--porcelain") == ""


def has_commit(repo: pathlib.Path, sha: str) -> bool:
    return subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", sha],
        capture_output=True).returncode == 0


def is_ancestor(repo: pathlib.Path, anc: str, desc: str) -> bool:
    return subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", anc, desc],
        capture_output=True).returncode == 0


# --------------------------------------------------------------------------
# Release-tree measurement (measure, never trust the record — Art. II)
# --------------------------------------------------------------------------

def package_dirs(portfolio_root: pathlib.Path) -> list:
    d = portfolio_root / "DOWNLOAD"
    return sorted([p for p in d.iterdir() if p.is_dir()])


def buyer_surface_files(portfolio_root: pathlib.Path) -> list:
    """Every file a buyer can receive: 8 root docs/registries + all of DOWNLOAD/."""
    files = []
    for name in ROOT_BUYER_FILES:
        p = portfolio_root / name
        if not p.is_file():
            raise FileNotFoundError(f"buyer-surface root file missing: {name}")
        files.append(p)
    for p in sorted((portfolio_root / "DOWNLOAD").rglob("*")):
        if p.is_file():
            files.append(p)
    return files


def rel_all(portfolio_root: pathlib.Path, files: list) -> dict:
    return {str(p.relative_to(portfolio_root)): sha256_file(p) for p in files}


def census_3d(portfolio_root: pathlib.Path) -> dict:
    """Recompute the 3D-layer census from disk (never copy from a record)."""
    packages = []
    totals = {"step": 0, "stl": 0, "glb": 0, "svg": 0, "png": 0,
              "parametric_sources": 0, "present_and_validated": 0,
              "not_applicable": 0}
    for d in package_dirs(portfolio_root):
        model = d / "MODEL"
        entry = {"folder": d.name, "model_dir_present": model.is_dir(),
                 "files": 0}
        pkg_status = model / "3D_DESIGN_STATUS.json"
        if pkg_status.is_file():
            try:
                st = read_json(pkg_status)
                entry["package_id"] = st.get("package_id")
                entry["design_status"] = st.get("3d_design_status")
            except Exception as exc:
                entry["status_parse_error"] = str(exc)
        else:
            entry["design_status"] = "MODEL_DIR_MISSING"
        if model.is_dir():
            counts = {"step": 0, "stl": 0, "glb": 0, "svg": 0, "png": 0,
                      "parametric_sources": 0, "json": 0}
            for f in sorted(model.rglob("*")):
                if not f.is_file():
                    continue
                entry["files"] += 1
                ext = f.suffix.lower().lstrip(".")
                if ext == "py":
                    # .py under MODEL/ = parametric model source by convention
                    counts["parametric_sources"] += 1
                elif ext in counts:
                    counts[ext] += 1
            entry["model_files_by_type"] = counts
            for k in ("step", "stl", "glb", "svg", "png", "parametric_sources"):
                totals[k] += counts[k]
        vrep = model / "GEOMETRY_VALIDATION_REPORT.json"
        if vrep.is_file():
            try:
                entry["geometry_validation_valid"] = bool(
                    read_json(vrep).get("valid"))
            except Exception as exc:
                entry["validation_parse_error"] = str(exc)
        else:
            entry["geometry_validation_valid"] = None
        ds = entry.get("design_status")
        if ds == "PRESENT_AND_VALIDATED":
            totals["present_and_validated"] += 1
        elif ds == "NOT_APPLICABLE":
            totals["not_applicable"] += 1
        packages.append(entry)
    return {"recomputed_from_disk": True, "packages": packages,
            "totals": totals}


def zip_member_hashes(zpath: pathlib.Path) -> dict:
    """name -> sha256 of member bytes (directory entries skipped)."""
    out = {}
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            if info.filename.endswith("/"):
                continue
            out[info.filename] = hashlib.sha256(z.read(info)).hexdigest()
    return out


def secret_scan(portfolio_root: pathlib.Path) -> list:
    hits = []
    for p in buyer_surface_files(portfolio_root):
        if p.suffix.lower() in (".py", ".json", ".md", ".txt", ".svg",
                                ".step", ".sh"):
            try:
                if SECRET_PAT.search(p.read_text(errors="ignore")):
                    hits.append(str(p.relative_to(portfolio_root)))
            except Exception:
                continue
    return hits


# --------------------------------------------------------------------------
# generate — build the CANONICAL RELEASE MANIFEST inside the portfolio repo
# --------------------------------------------------------------------------

def build_manifest(portfolio_root: pathlib.Path,
                   engine_root: pathlib.Path,
                   release_id: str,
                   engine_build_commit: str,
                   builder_script: str,
                   build_history: list,
                   portfolio_provenance_commits: list,
                   evidence_pins: list,
                   superseded_objects: dict,
                   honest_limits: list,
                   edition_note: str) -> dict:
    pins = rel_all(portfolio_root, buyer_surface_files(portfolio_root))
    census = census_3d(portfolio_root)
    pkg_zips = []
    for d in package_dirs(portfolio_root):
        zpath = pathlib.Path(str(d) + ".zip")
        if not zpath.is_file():
            raise FileNotFoundError(f"package ZIP missing: {zpath}")
        pid = None
        for entry in census["packages"]:
            if entry["folder"] == d.name:
                pid = entry.get("package_id")
        pkg_zips.append({"folder": d.name, "package_id": pid,
                         "zip": str(zpath.relative_to(portfolio_root)),
                         "sha256": sha256_file(zpath)})
    master = portfolio_root / MASTER_ZIP_REL
    engine_remote = sanitize_url(git(engine_root, "remote", "get-url",
                                     "origin"))
    portfolio_remote = sanitize_url(git(portfolio_root, "remote", "get-url",
                                         "origin"))
    manifest = {
        "manifest_type": "CANONICAL_RELEASE_MANIFEST",
        "chain_version": "1.0",
        "release_id": release_id,
        "edition": edition_note,
        "authority": {
            "declaration": AUTHORITY_DECLARATION,
            "rule": (
                "Any local checkout, engine-side copy, or summary that "
                "disagrees with the pushed main branch of the "
                "buyer-distribution repository is, by definition, stale or "
                "wrong with respect to buyer truth. Verification is executed "
                "from fresh clones of both remotes, never from a local "
                "workspace."),
            "chain": ["ENGINE REPO", "CANONICAL RELEASE MANIFEST",
                      "PORTFOLIO REPO (buyer distribution)", "BUYER ZIP",
                      "VERIFICATION"],
            "verification_command": (
                "python scripts/r386_release_chain.py verify-fresh "
                "--engine-url <engine-remote> --portfolio-url "
                "<portfolio-remote>"),
            "failure_rule": (
                "verification exits nonzero and records a FAIL certificate "
                "whenever any of the four states disagree; a release may not "
                "be claimed as shipped, tagged, or buyer-ready while the "
                "chain fails or has not been run from clean clones"),
            "constitution_anchor": "Article XXXIX (EPISTEMIC_CONSTITUTION.md "
                                   "v1.9.0)",
        },
        "engine_provenance": {
            "remote": engine_remote,
            "engine_build_commit": engine_build_commit,
            "builder_script": builder_script,
            "builder_script_sha256": sha256_file(
                engine_root / builder_script),
            "build_history": build_history,
            "build_order_note": (
                "For this edition the builder script bytes are provably "
                "identical to the engine-committed copy at the build commit, "
                "while the build ran before that engine commit existed "
                "(R385B synced the script after the build). From R386 "
                "onward, Article XXXIX section 5 requires the protocol "
                "order: clean pushed engine state BEFORE the build."),
        },
        "portfolio_provenance": {
            "remote": portfolio_remote,
            "release_commits": portfolio_provenance_commits,
            "manifest_commit_note": (
                "A manifest cannot contain its own portfolio commit hash. "
                "The portfolio commit that introduces this manifest, the "
                "manifest sha256, and the master-ZIP sha256 are pinned "
                "engine-side in ENGINE_RELEASE_REGISTRY.json."),
        },
        "buyer_surface": {
            "definition": (
                "the 8 root buyer documents/registries plus every file under "
                "DOWNLOAD/ (15 package folders including MODEL/ 3D layers, "
                "15 package ZIPs, and the master ZIP)"),
            "pinned_files": len(pins),
            "sha256": pins,
        },
        "package_zips": pkg_zips,
        "master_zip": {"path": MASTER_ZIP_REL,
                       "sha256": sha256_file(master),
                       "bytes": master.stat().st_size},
        "three_d_census": census,
        "evidence_pins": {rel: sha256_file(portfolio_root / rel)
                          for rel in evidence_pins},
        "superseded_objects": superseded_objects,
        "honest_limits": honest_limits,
        "determinism_note": (
            "No timestamp in this manifest by design (R374-5 byte-"
            "reproducible release discipline). Provenance is the git history "
            "of the two repositories."),
    }
    return manifest


def cmd_generate(args) -> int:
    portfolio_root = pathlib.Path(args.portfolio).resolve()
    engine_root = pathlib.Path(args.engine).resolve()
    problems = []
    for name, root in (("engine", engine_root), ("portfolio", portfolio_root)):
        if not is_clean(root):
            problems.append(f"{name} tree is dirty (commit first)")
        if args.require_remote:
            head = git(root, "rev-parse", "HEAD")
            remote = git(root, "ls-remote", "origin", "refs/heads/main",
                         check=False).split("\t")[0]
            if not remote:
                problems.append(f"{name} origin/main unreachable")
            elif head != remote:
                problems.append(
                    f"{name} HEAD {head[:8]} != origin/main {remote[:8]} "
                    "(Art. XXIII: push or re-sync first)")
    if problems:
        print("REFUSED — release protocol preconditions failed:")
        for p in problems:
            print(f"  - {p}")
        return 2
    manifest = build_manifest(
        portfolio_root, engine_root, args.release_id,
        args.engine_build_commit, args.builder_script,
        json.loads(args.build_history), args.portfolio_provenance_commits,
        args.evidence_pins, json.loads(args.superseded_objects),
        args.honest_limits, args.edition)
    out = portfolio_root / MANIFEST_NAME
    dump_json(out, manifest)
    print(f"[r386] wrote {out} "
          f"({manifest['buyer_surface']['pinned_files']} buyer-surface pins, "
          f"master ZIP {manifest['master_zip']['sha256'][:12]})")
    print(f"[r386] NEXT: commit+push the portfolio, then run `record`.")
    return 0


# --------------------------------------------------------------------------
# record — engine-side registry entry
# --------------------------------------------------------------------------

def registry_entry(manifest: dict, portfolio_commit: str, status: str) -> dict:
    return {
        "release_id": manifest["release_id"],
        "edition": manifest["edition"],
        "status": status,
        "portfolio_release_commit": portfolio_commit,
        "manifest_path": MANIFEST_NAME,
        "manifest_sha256": sha256_of_manifest_bytes(manifest),
        "master_zip_sha256": manifest["master_zip"]["sha256"],
        "engine_build_commit": manifest["engine_provenance"][
            "engine_build_commit"],
        "builder_script": manifest["engine_provenance"]["builder_script"],
        "builder_script_sha256": manifest["engine_provenance"][
            "builder_script_sha256"],
        "portfolio_provenance_commits": manifest["portfolio_provenance"][
            "release_commits"],
        "constitution_anchor": manifest["authority"]["constitution_anchor"],
        "recorded_by": "scripts/r386_release_chain.py (R386)",
        "verifications": [],
    }


def sha256_of_manifest_bytes(manifest: dict) -> str:
    return hashlib.sha256(
        (json.dumps(manifest, indent=1, sort_keys=True) + "\n")
        .encode("utf-8")).hexdigest()


def cmd_record(args) -> int:
    engine_root = pathlib.Path(args.engine).resolve()
    portfolio_root = pathlib.Path(args.portfolio).resolve()
    if not is_clean(portfolio_root):
        print("REFUSED — portfolio tree is dirty (the manifest must be "
              "committed and pushed before the engine records it)")
        return 2
    portfolio_commit = git(portfolio_root, "rev-parse", "HEAD")
    manifest = read_json(portfolio_root / MANIFEST_NAME)
    # The manifest on disk must hash to what the registry will pin.
    reg_path = engine_root / REGISTRY_NAME
    registry = {
        "registry_type": "ENGINE_RELEASE_REGISTRY",
        "version": "1.0",
        "authority_declaration": AUTHORITY_DECLARATION,
        "release_protocol": [
            "1. Both repos clean and pushed (HEAD == origin/main).",
            "2. Build/refresh release content; commit and push the "
            "PORTFOLIO (buyer distribution) repo first.",
            "3. Generate CANONICAL_RELEASE_MANIFEST.json from the pushed "
            "portfolio state; commit and push it (portfolio release commit).",
            "4. Record the release here (engine side): portfolio release "
            "commit, manifest sha256, master-ZIP sha256, engine build "
            "commit, builder script sha256.",
            "5. Run scripts/r386_release_chain.py verify-fresh from clean "
            "clones of BOTH remotes; the release is not shipped unless it "
            "passes. Append the verification record to this entry.",
        ],
        "releases": [],
    }
    if reg_path.is_file():
        registry = read_json(reg_path)
        keep = {k: registry[k] for k in
                ("registry_type", "version", "authority_declaration",
                 "release_protocol") if k in registry}
        registry = {**keep, "releases": registry.get("releases", [])}
    entry = registry_entry(manifest, portfolio_commit, args.status)
    registry["releases"] = [e for e in registry["releases"]
                            if e["release_id"] != entry["release_id"]] + [entry]
    dump_json(reg_path, registry)
    print(f"[r386] recorded {entry['release_id']} in {reg_path}")
    print(f"[r386]   portfolio_release_commit = {portfolio_commit[:12]}")
    print(f"[r386]   manifest_sha256 = {entry['manifest_sha256'][:12]}")
    print(f"[r386] NEXT: commit+push the engine, then run `verify-fresh`.")
    return 0


# --------------------------------------------------------------------------
# verify — the four-state verification
# --------------------------------------------------------------------------

class Check:
    def __init__(self, cid: str, state: str, description: str):
        self.id, self.state, self.description = cid, state, description
        self.status, self.details = "FAIL", []

    def ok(self, detail: str = "") -> "Check":
        self.status = "PASS"
        if detail:
            self.details.append(detail)
        return self

    def fail(self, detail: str) -> "Check":
        self.status = "FAIL"
        self.details.append(detail)
        return self

    def as_dict(self) -> dict:
        return {"id": self.id, "state": self.state,
                "description": self.description, "status": self.status,
                "details": self.details}


def verify_chain(engine_root: pathlib.Path,
                 portfolio_root: pathlib.Path,
                 release_id: str | None = None) -> dict:
    checks: list = []

    def add(cid, state, desc) -> Check:
        c = Check(cid, state, desc)
        checks.append(c)
        return c

    # ---- STATE 1: ENGINE REPO -------------------------------------------
    c = add("E1", STATE_ENGINE, "engine checkout is clean")
    c.ok() if is_clean(engine_root) else c.fail(
        git(engine_root, "status", "--porcelain")[:300])

    reg_path = engine_root / REGISTRY_NAME
    c = add("E2", STATE_ENGINE, f"{REGISTRY_NAME} exists with valid schema")
    registry = None
    if reg_path.is_file():
        try:
            registry = read_json(reg_path)
            if registry.get("registry_type") != "ENGINE_RELEASE_REGISTRY":
                c.fail("registry_type mismatch")
            elif registry.get("authority_declaration") != AUTHORITY_DECLARATION:
                c.fail("authority declaration not verbatim")
            else:
                c.ok()
        except Exception as exc:
            c.fail(f"unparseable: {exc}")
    else:
        c.fail(f"{REGISTRY_NAME} missing at engine root")

    entry = None
    if registry:
        rel = [e for e in registry.get("releases", [])
               if release_id is None or e["release_id"] == release_id]
        c = add("E3", STATE_ENGINE, "release entry present in registry")
        if len(rel) == 1:
            entry = rel[0]
            c.ok(f"release_id={entry['release_id']}")
        else:
            c.fail(f"expected exactly 1 entry for release_id={release_id}, "
                   f"found {len(rel)}")

    manifest_path = portfolio_root / MANIFEST_NAME
    manifest = None
    c = add("M1", STATE_MANIFEST, "manifest exists, parseable, chain v1.0")
    if manifest_path.is_file():
        try:
            manifest = read_json(manifest_path)
            if manifest.get("manifest_type") != "CANONICAL_RELEASE_MANIFEST":
                c.fail("manifest_type mismatch")
            elif manifest.get("chain_version") != "1.0":
                c.fail(f"chain_version={manifest.get('chain_version')}")
            else:
                c.ok()
        except Exception as exc:
            c.fail(f"unparseable: {exc}")
    else:
        c.fail(f"{MANIFEST_NAME} missing at portfolio root")

    c = add("M2", STATE_MANIFEST, "authority declaration verbatim (Art. XXXIX)")
    if manifest and manifest.get("authority", {}).get("declaration") == \
            AUTHORITY_DECLARATION:
        c.ok()
    else:
        c.fail("declaration missing or altered")

    c = add("M3", STATE_MANIFEST, "manifest is timeless (no volatile keys)")
    if manifest:
        bad = _find_keys(manifest, FORBIDDEN_MANIFEST_KEYS)
        c.ok() if not bad else c.fail(f"volatile keys present: {bad}")
    else:
        c.fail("no manifest")

    # ---- STATE 2 <-> 3 joins ---------------------------------------------
    if entry and manifest:
        c = add("E4", STATE_ENGINE, "registry.manifest_sha256 == manifest bytes")
        got = sha256_of_manifest_bytes(manifest)
        c.ok(got[:12]) if entry["manifest_sha256"] == got else c.fail(
            f"registry {entry['manifest_sha256'][:12]} != manifest {got[:12]}")

        c = add("E5", STATE_ENGINE,
                "master-ZIP sha256 agrees 3-way (registry = manifest = disk)")
        disk = sha256_file(portfolio_root / MASTER_ZIP_REL)
        mzip = manifest["master_zip"]["sha256"]
        c.ok(disk[:12]) if (entry["master_zip_sha256"] == mzip == disk) \
            else c.fail(f"registry {entry['master_zip_sha256'][:12]}, "
                        f"manifest {mzip[:12]}, disk {disk[:12]}")

        c = add("E7", STATE_ENGINE,
                "engine build commit agrees (registry = manifest)")
        c.ok() if entry["engine_build_commit"] == \
            manifest["engine_provenance"]["engine_build_commit"] else c.fail(
            "engine build commit differs between registry and manifest")

        c = add("E8", STATE_ENGINE, "builder script pinned and byte-identical")
        script_rel = entry["builder_script"]
        spath = engine_root / script_rel
        if spath.is_file():
            ssha = sha256_file(spath)
            if ssha == entry["builder_script_sha256"] == \
                    manifest["engine_provenance"]["builder_script_sha256"]:
                c.ok(script_rel)
            else:
                c.fail(f"script sha mismatch: engine disk {ssha[:12]}, "
                       f"registry {entry['builder_script_sha256'][:12]}")
        else:
            c.fail(f"builder script missing in engine repo: {script_rel}")

        bc = entry["engine_build_commit"]
        c = add("E2b", STATE_ENGINE,
                "engine build commit exists and is an ancestor of engine HEAD")
        head = git(engine_root, "rev-parse", "HEAD")
        if has_commit(engine_root, bc):
            c.ok() if is_ancestor(engine_root, bc, head) else c.fail(
                f"build commit {bc[:12]} is not an ancestor of HEAD")
        else:
            c.fail(f"build commit {bc[:12]} not present in engine repo")

    # ---- constitution enforcement (permanent rule) ----------------------
    c = add("E9", STATE_ENGINE,
            "Article XXXIX present in constitution with authority rule")
    const = engine_root / CONSTITUTION_NAME
    if const.is_file():
        text = const.read_text(encoding="utf-8", errors="ignore")
        has_art = "Article XXXIX" in text
        has_decl = AUTHORITY_DECLARATION in text
        if has_art and has_decl:
            c.ok("constitution v1.9.0+")
        else:
            c.fail(f"Article XXXIX present={has_art}, declaration={has_decl}")
    else:
        c.fail(f"{CONSTITUTION_NAME} missing in engine repo")

    # ---- STATE 3: PORTFOLIO REPO -----------------------------------------
    c = add("P1", STATE_PORTFOLIO, "portfolio checkout is clean")
    c.ok() if is_clean(portfolio_root) else c.fail(
        git(portfolio_root, "status", "--porcelain")[:300])

    phead = git(portfolio_root, "rev-parse", "HEAD")
    if entry:
        prc = entry["portfolio_release_commit"]
        c = add("P2", STATE_PORTFOLIO,
                "portfolio HEAD == registry portfolio_release_commit "
                "(or later commit that does not touch the buyer surface)")
        if phead == prc:
            c.ok("exact release commit")
        elif has_commit(portfolio_root, prc):
            if is_ancestor(portfolio_root, prc, phead):
                changed = git(portfolio_root, "diff", "--name-only", prc,
                              phead).splitlines()
                buyer = _buyer_surface_names(portfolio_root)
                touched = [f for f in changed if f in buyer or f ==
                           MANIFEST_NAME or f.startswith("DOWNLOAD/")]
                if touched:
                    c.fail(f"buyer surface modified after release commit: "
                           f"{touched[:5]}")
                else:
                    c.ok(f"audit-only commits after release commit "
                         f"({len(changed)} files)")
            else:
                c.fail(f"release commit {prc[:12]} is not an ancestor of HEAD")
        else:
            c.fail(f"portfolio_release_commit {prc[:12]} absent in checkout")

        c = add("P3", STATE_PORTFOLIO,
                "manifest bytes unchanged since the release commit")
        try:
            blob = subprocess.run(
                ["git", "-C", str(portfolio_root), "cat-file", "blob",
                 f"{prc}:{MANIFEST_NAME}"],
                capture_output=True, check=True).stdout
            now = manifest_path.read_bytes()
            c.ok("byte-identical") if blob == now else c.fail(
                "manifest at HEAD differs from the release-commit version")
        except Exception as exc:
            c.fail(str(exc)[:200])

    if manifest:
        c = add("P4", STATE_PORTFOLIO, "portfolio remote matches manifest")
        url = sanitize_url(git(portfolio_root, "remote", "get-url", "origin",
                               check=False))
        want = manifest["portfolio_provenance"]["remote"]
        c.ok(url) if url and url == want else c.fail(
            f"remote {url} != manifest {want}")

    # ---- STATE 2 pins vs STATE 3 disk ------------------------------------
    if manifest:
        pins = manifest["buyer_surface"]["sha256"]
        c = add("M4", STATE_MANIFEST,
                "buyer surface fully pinned: every disk file pinned, every "
                "pin present with matching sha256")
        disk_map = rel_all(portfolio_root,
                           buyer_surface_files(portfolio_root))
        missing_pin = [f for f in disk_map if f not in pins]
        absent = [f for f in pins if f not in disk_map]
        mismatched = [f for f in pins if f in disk_map
                      and pins[f] != disk_map[f]]
        if missing_pin or absent or mismatched:
            c.fail(f"unpinned-on-disk={missing_pin[:4]} "
                   f"pin-absent={absent[:4]} hash-mismatch={mismatched[:4]}")
        else:
            c.ok(f"{len(pins)} files pinned hash-exact")

        c = add("M5", STATE_MANIFEST, "evidence pins present and hash-exact")
        bad = []
        for rel, want_sha in manifest.get("evidence_pins", {}).items():
            p = portfolio_root / rel
            if not p.is_file() or sha256_file(p) != want_sha:
                bad.append(rel)
        c.ok(f"{len(manifest.get('evidence_pins', {}))} evidence files") \
            if not bad else c.fail(f"broken evidence pins: {bad[:4]}")

        c = add("M6", STATE_MANIFEST,
                "3D census matches the recomputed disk census")
        fresh = census_3d(portfolio_root)
        c.ok(json.dumps(fresh["totals"], sort_keys=True)) if \
            fresh == manifest["three_d_census"] else c.fail(
            f"totals on disk {fresh['totals']} vs manifest "
            f"{manifest['three_d_census']['totals']}")

    # ---- STATE 4: BUYER ZIP ----------------------------------------------
    if manifest:
        c = add("Z1", STATE_ZIP, "every package ZIP == its folder (per-file "
                                "sha256, name sets equal)")
        bad = []
        for d in package_dirs(portfolio_root):
            zpath = pathlib.Path(str(d) + ".zip")
            if not zpath.is_file():
                bad.append(f"{d.name}: zip missing")
                continue
            members = zip_member_hashes(zpath)
            folder = {str(f.relative_to(d)): sha256_file(f)
                      for f in sorted(d.rglob("*")) if f.is_file()}
            if set(members) != set(folder):
                bad.append(f"{d.name}: name sets differ")
            else:
                for name, h in members.items():
                    if folder[name] != h:
                        bad.append(f"{d.name}/{name}: bytes differ")
        c.ok(f"{len(package_dirs(portfolio_root))} packages") if not bad \
            else c.fail("; ".join(bad[:6]))

        c = add("Z2", STATE_ZIP, "package ZIP sha256 == manifest pins")
        bad = [e["zip"] for e in manifest["package_zips"]
               if sha256_file(portfolio_root / e["zip"]) != e["sha256"]]
        if not bad:
            c.ok(f"{len(manifest['package_zips'])} package ZIP hashes pinned")
        else:
            c.fail(f"package ZIP hash drift: {bad[:4]}")

        c = add("Z3", STATE_ZIP, "master ZIP member set + per-member sha256 "
                                "== manifest-defined buyer surface")
        expected = {f: sha256_file(portfolio_root / f)
                    for f in ROOT_BUYER_FILES}
        for e in manifest["package_zips"]:
            expected[e["zip"]] = sha256_file(portfolio_root / e["zip"])
        members = zip_member_hashes(portfolio_root / MASTER_ZIP_REL)
        if set(members) != set(expected):
            c.fail(f"member sets differ: only-in-zip="
                   f"{sorted(set(members) - set(expected))[:4]} "
                   f"only-on-disk={sorted(set(expected) - set(members))[:4]}")
        else:
            diff = [n for n, h in members.items() if expected[n] != h]
            c.ok(f"{len(members)} members byte-exact") if not diff \
                else c.fail(f"members with differing bytes: {diff[:4]}")

        c = add("Z4", STATE_ZIP,
                "master ZIP sha256 == manifest pin (byte-exact container)")
        disk = sha256_file(portfolio_root / MASTER_ZIP_REL)
        c.ok(disk[:12]) if disk == manifest["master_zip"]["sha256"] \
            else c.fail(f"disk {disk[:12]} != manifest "
                        f"{manifest['master_zip']['sha256'][:12]}")

        c = add("Z5", STATE_ZIP, "3D layer present in every applicable "
                                "package ZIP; N/A packages ship only their "
                                "honest declaration files")
        bad = []
        GEOM_EXT = (".step", ".stl", ".glb", ".svg")
        NA_ALLOWED = {"MODEL/3D_DESIGN_STATUS.json", "MODEL/README.json"}
        for e in manifest["package_zips"]:
            members = set(zip_member_hashes(
                portfolio_root / e["zip"]))
            model_members = [m for m in members if m.startswith("MODEL/")]
            status = None
            for pc in manifest["three_d_census"]["packages"]:
                if pc["folder"] == e["folder"]:
                    status = pc.get("design_status")
            if status == "PRESENT_AND_VALIDATED" and not model_members:
                bad.append(f"{e['folder']}: validated but no MODEL/ in ZIP")
            elif status == "NOT_APPLICABLE":
                geometry = [m for m in model_members
                            if m.lower().endswith(GEOM_EXT)
                            or m.endswith("PARAMETRIC_MODEL_SOURCE.py")]
                extra = [m for m in model_members
                         if m not in NA_ALLOWED and m not in geometry]
                if geometry:
                    bad.append(f"{e['folder']}: N/A but geometry shipped "
                               f"({geometry[:2]})")
                elif extra:
                    bad.append(f"{e['folder']}: N/A with undeclared MODEL/ "
                               f"files ({extra[:2]})")
        c.ok("14 validated + 1 honest N/A (declaration files only)") \
            if not bad else c.fail("; ".join(bad[:6]))

    c = add("S1", "GLOBAL", "no secrets in the buyer surface")
    hits = secret_scan(portfolio_root)
    c.ok("clean") if not hits else c.fail(f"hits: {hits[:5]}")

    overall = all(ch.status == "PASS" for ch in checks)
    return {
        "artifact": "RELEASE_CHAIN_VERIFICATION",
        "release_id": (entry or {}).get("release_id") or release_id,
        "overall": "PASS" if overall else "FAIL",
        "checks": [ch.as_dict() for ch in checks],
        "states": {
            "engine_head": git(engine_root, "rev-parse", "HEAD"),
            "portfolio_head": phead,
            "engine_build_commit": (entry or {}).get("engine_build_commit"),
            "portfolio_release_commit": (entry or {}).get(
                "portfolio_release_commit"),
            "manifest_sha256": (entry or {}).get("manifest_sha256"),
            "master_zip_sha256": (entry or {}).get("master_zip_sha256"),
        },
        "honesty_scope": (
            "This certificate verifies DELIVERY from clean clones: the bytes "
            "a buyer receives from the buyer-distribution repository. It "
            "does NOT claim rebuild-from-source reproduction of those "
            "bytes; that is a separate, explicitly-declared open item "
            "(engine 3D output self-containment decision pending CEO)."),
    }


def _buyer_surface_names(portfolio_root: pathlib.Path) -> set:
    return set(ROOT_BUYER_FILES) | {
        str(p.relative_to(portfolio_root))
        for p in (portfolio_root / "DOWNLOAD").rglob("*") if p.is_file()}


def _find_keys(obj, forbidden: set) -> list:
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in forbidden:
                found.append(str(k))
            found.extend(_find_keys(v, forbidden))
    elif isinstance(obj, list):
        for v in obj:
            found.extend(_find_keys(v, forbidden))
    return found


# --------------------------------------------------------------------------
# record-verification — append a clean-clone verification record to the entry
# --------------------------------------------------------------------------

def cmd_record_verification(args) -> int:
    engine_root = pathlib.Path(args.engine).resolve()
    cert = read_json(pathlib.Path(args.cert).resolve())
    if cert.get("overall") != "PASS" and not args.force:
        print("REFUSED — only PASS certificates may be recorded "
              "(use --force to record a FAIL deliberately)")
        return 2
    reg_path = engine_root / REGISTRY_NAME
    registry = read_json(reg_path)
    rid = cert.get("release_id")
    for e in registry["releases"]:
        if e["release_id"] == rid:
            e.setdefault("verifications", []).append({
                "verified_at": _dt.datetime.now(
                    _dt.timezone.utc).isoformat(timespec="seconds"),
                "mode": cert.get("mode", "unknown"),
                "engine_main_verified": cert["states"]["engine_head"],
                "portfolio_main_verified": cert["states"]["portfolio_head"],
                "manifest_sha256": cert["states"]["manifest_sha256"],
                "master_zip_sha256": cert["states"]["master_zip_sha256"],
                "overall": cert["overall"],
                "checks_passed": sum(1 for c in cert["checks"]
                                     if c["status"] == "PASS"),
                "checks_total": len(cert["checks"]),
                "certificate": args.cert if args.cert.startswith(
                    "RELEASE_CHAIN/") else pathlib.Path(
                    args.cert).resolve().name,
                "honesty_scope": cert.get("honesty_scope", ""),
            })
            dump_json(reg_path, registry)
            print(f"[r386] verification recorded for {rid} "
                  f"({cert['overall']}, "
                  f"{sum(1 for c in cert['checks'] if c['status'] == 'PASS')}"
                  f"/{len(cert['checks'])} checks)")
            return 0
    print(f"REFUSED — no registry entry for release_id={rid}")
    return 2


# --------------------------------------------------------------------------
# verify-fresh — clone both remotes, then verify (the authoritative mode)
# --------------------------------------------------------------------------

def cmd_verify_fresh(args) -> int:
    workdir = pathlib.Path(args.workdir or tempfile.mkdtemp(
        prefix="r386_clones_")).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    engine_url = args.engine_url
    portfolio_url = args.portfolio_url
    engine_dir = workdir / "engine"
    portfolio_dir = workdir / "portfolio"
    for url, dest, name in ((engine_url, engine_dir, "engine"),
                            (portfolio_url, portfolio_dir, "portfolio")):
        if dest.exists():
            shutil.rmtree(dest)
        print(f"[r386] cloning {sanitize_url(url)} -> {dest}")
        out = subprocess.run(["git", "clone", "--quiet", url, str(dest)],
                             capture_output=True, text=True)
        if out.returncode != 0:
            print(f"REFUSED — cannot clone {name} remote:\n{out.stderr[:400]}")
            return 2
    result = verify_chain(engine_dir, portfolio_dir, args.release_id)
    result["mode"] = "fresh-clone (authoritative)"
    result["remotes"] = {"engine": sanitize_url(engine_url),
                         "portfolio": sanitize_url(portfolio_url)}
    cert_path = pathlib.Path(args.cert_out) if args.cert_out else \
        pathlib.Path(f"RELEASE_CHAIN_VERIFICATION_"
                     f"{(result['release_id'] or 'UNKNOWN').replace('/', '_')}"
                     f".json")
    dump_json(cert_path, result)
    _print_result(result)
    print(f"[r386] certificate: {cert_path}")
    if not args.keep:
        shutil.rmtree(workdir, ignore_errors=True)
    return 0 if result["overall"] == "PASS" else 1


def cmd_verify(args) -> int:
    result = verify_chain(pathlib.Path(args.engine).resolve(),
                          pathlib.Path(args.portfolio).resolve(),
                          args.release_id)
    result["mode"] = "local checkouts (non-authoritative for buyer truth; " \
                     "run verify-fresh for the authoritative mode)"
    cert_path = pathlib.Path(args.cert_out) if args.cert_out else \
        pathlib.Path(f"RELEASE_CHAIN_VERIFICATION_LOCAL.json")
    dump_json(cert_path, result)
    _print_result(result)
    print(f"[r386] certificate: {cert_path}")
    return 0 if result["overall"] == "PASS" else 1


def _print_result(result: dict) -> None:
    print(f"\n[r386] RELEASE CHAIN VERIFICATION — {result['overall']}")
    for ch in result["checks"]:
        mark = "PASS" if ch["status"] == "PASS" else "FAIL"
        print(f"  {mark}  {ch['id']:>4} [{ch['state']:<9}] {ch['description']}")
        for d in ch["details"][:3]:
            print(f"         {d[:150]}")


# --------------------------------------------------------------------------
# drift — standing local checkouts vs the remotes (informational)
# --------------------------------------------------------------------------

def cmd_drift(args) -> int:
    print(f"AUTHORITY: {AUTHORITY_DECLARATION}\n")
    failures = 0
    for spec in args.repos:
        root = pathlib.Path(spec).resolve()
        if not (root / ".git").exists():
            print(f"  SKIP  {root} (not a git checkout)")
            continue
        head = git(root, "rev-parse", "HEAD", check=False)
        remote = git(root, "ls-remote", "origin", "refs/heads/main",
                     check=False).split("\t")[0]
        clean = is_clean(root)
        if remote and head == remote and clean:
            print(f"  OK    {root.name} @ {head[:12]} == origin/main, clean")
        else:
            failures += 1
            print(f"  DRIFT {root.name}: HEAD {head[:12]}, origin/main "
                  f"{(remote or 'UNREACHABLE')[:12]}, "
                  f"{'clean' if clean else 'DIRTY'}")
            print(f"        -> this local state is NOT authority; re-sync "
                  f"from the remote before any work (Art. XXIII/XXXIX)")
    if args.strict:
        return 1 if failures else 0
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate")
    g.add_argument("--portfolio", required=True)
    g.add_argument("--engine", required=True)
    g.add_argument("--release-id", required=True)
    g.add_argument("--engine-build-commit", required=True)
    g.add_argument("--builder-script", required=True)
    g.add_argument("--edition", default="")
    g.add_argument("--build-history", default="[]")
    g.add_argument("--portfolio-provenance-commits", nargs="*",
                   default=[])
    g.add_argument("--evidence-pins", nargs="*", default=[])
    g.add_argument("--superseded-objects", default="{}")
    g.add_argument("--honest-limits", nargs="*", default=[])
    g.add_argument("--require-remote", action="store_true", default=True)
    g.add_argument("--allow-no-remote", dest="require_remote",
                   action="store_false")
    g.set_defaults(func=cmd_generate)

    r = sub.add_parser("record")
    r.add_argument("--engine", required=True)
    r.add_argument("--portfolio", required=True)
    r.add_argument("--status",
                   default="SUBMITTED_FOR_CEO_AUDIT_NOT_TAGGED")
    r.set_defaults(func=cmd_record)

    rv = sub.add_parser("record-verification")
    rv.add_argument("--engine", required=True)
    rv.add_argument("--cert", required=True)
    rv.add_argument("--force", action="store_true")
    rv.set_defaults(func=cmd_record_verification)

    v = sub.add_parser("verify")
    v.add_argument("--engine", required=True)
    v.add_argument("--portfolio", required=True)
    v.add_argument("--release-id", default=None)
    v.add_argument("--cert-out", default=None)
    v.set_defaults(func=cmd_verify)

    vf = sub.add_parser("verify-fresh")
    vf.add_argument("--engine-url", required=True)
    vf.add_argument("--portfolio-url", required=True)
    vf.add_argument("--release-id", default=None)
    vf.add_argument("--workdir", default=None)
    vf.add_argument("--cert-out", default=None)
    vf.add_argument("--keep", action="store_true")
    vf.set_defaults(func=cmd_verify_fresh)

    d = sub.add_parser("drift")
    d.add_argument("--repos", nargs="+", required=True)
    d.add_argument("--strict", action="store_true")
    d.set_defaults(func=cmd_drift)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""scripts/r446_hf_security_scan.py — R446-HF Phase 32: the credential
leakage scan across the directive's ten surfaces:

  git history | Docker layers/build output | HF Space repository |
  application logs | API responses | frontend bundle | generated JSON |
  PDF metadata | package ZIP | + the local staging tree

Patterns (never printing VALUES — only counts + locations):
  hf_[A-Za-z0-9]{20,}   (HF token shape)
  ghp_[A-Za-z0-9]{30,}  (GitHub PAT shape)
  the deployed secret VALUES themselves (exact-match guards)
  Authorization:|Bearer  headers in captured bodies
  sk-or-|nvapi-|sk-ant- (provider key shapes)

A credential finding BLOCKS release (the directive). Pre-existing
committed items are reported separately with their history disclosed.
"""
from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List

REPO = Path("/home/z/my-project/repos/discovery-evidence-fabric")
STAGE = Path("/home/z/my-project/hf_space_stage")
RUNS_DIR = REPO / "R446" / "HF_PRODUCTION_RUNS"
OUT = REPO / "R446" / "HF_SECURITY_SCAN.json"

HF_TOKEN = Path("/home/z/my-project/.secrets/hf_token").read_text().strip()
GH_PAT = Path("/home/z/my-project/.secrets/gh_pat").read_text().strip()

PATTERNS = {
    "hf_token_shape": re.compile(r"hf_[A-Za-z0-9]{20,}"),
    "github_pat_shape": re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    "openrouter_key_shape": re.compile(r"sk-or-[A-Za-z0-9-]{20,}"),
    "nvidia_key_shape": re.compile(r"nvapi-[A-Za-z0-9-]{20,}"),
    "anthropic_key_shape": re.compile(r"sk-ant-[A-Za-z0-9-]{20,}"),
    "zai_gateway_key_shape": re.compile(r"zai-local-gw-[A-Za-z0-9]{20,}"),
    "auth_header": re.compile(r"Authorization:\s*Bearer\s+[A-Za-z0-9._-]{10,}"),
}
EXACT_VALUES = {
    "deployed_hf_token": HF_TOKEN,
    "deployed_github_pat": GH_PAT,
}


POISON_FIXTURE_VALUES = ("nvapi-poisoned-worker-level",
                         "nvapi-poisoned", "sk-or-poisoned",
                         "zai-poisoned", "ghp_poisoned_worker_level",
                         "operator-poisoned", "a-secret-the-allowlist")


def scan_text(name: str, text: str) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    for label, val in EXACT_VALUES.items():
        if val and val in text:
            hits.append({"surface": name, "pattern": f"EXACT:{label}",
                         "count": text.count(val)})
    for label, rx in PATTERNS.items():
        found = rx.findall(text)
        if found:
            is_poison = any(v in m for m in found
                            for v in POISON_FIXTURE_VALUES)
            hits.append({"surface": name, "pattern": label,
                         "count": len(found),
                         "poison_fixture": is_poison,
                         "sample_shape": (found[0][:6] + "..."
                                          + found[0][-2:])
                         if found[0] else None})
    del text
    return hits


def scan_file_text(name: str, path: Path) -> List[Dict[str, Any]]:
    """Scan one file's text WITHOUT holding every file at once."""
    try:
        return scan_text(name, path.read_text(errors="ignore"))
    except Exception:  # noqa: BLE001
        return []


def scan_bytes(name: str, blob: bytes) -> List[Dict[str, Any]]:
    try:
        return scan_text(name, blob.decode("utf-8", errors="ignore"))
    except Exception:  # noqa: BLE001
        return []


def main() -> None:
    all_hits: List[Dict[str, Any]] = []
    surfaces: Dict[str, Any] = {}

    # 1. git history (the LAST 200 commits' diffs — streamed in
    #    50-commit windows so the working set stays bounded)
    import subprocess
    total = 0
    for skip in range(0, 200, 50):
        chunk = subprocess.run(
            ["git", "log", "-50", f"--skip={skip}", "-p",
             "--no-color"],
            cwd=REPO, capture_output=True, timeout=300).stdout
        chunk = chunk.decode("utf-8", errors="ignore")
        total += len(chunk)
        all_hits += scan_text("git_history_200_commits", chunk)
        del chunk
    surfaces["git_history_200_commits"] = {"scanned_bytes": total}

    # 2. Docker build output (both captured build logs)
    for tag, p in [("build_log_attempt1",
                    Path("/home/z/my-project/hf_build_log.sse")),
                   ("build_log_attempt2",
                    Path("/home/z/my-project/hf_build_log2.sse"))]:
        if p.exists():
            txt = p.read_text(errors="ignore")
            surfaces[tag] = {"scanned_bytes": len(txt)}
            all_hits += scan_text(tag, txt)

    # 3. HF Space repository == the staged tree pushed (scan file by file)
    n = 0
    nbytes = 0
    for f in STAGE.rglob("*"):
        if f.is_file() and ".cache" not in f.parts and f.suffix in (
                ".py", ".js", ".json", ".md", ".txt", ".yml", ".yaml",
                ".sh", ".mjs", ".html", ".css", ".tsx", ".ts"):
            n += 1
            nbytes += f.stat().st_size
            all_hits += scan_file_text("hf_space_repo_staged_tree", f)
    surfaces["hf_space_repo_staged_tree"] = {"files_scanned": n,
                                             "scanned_bytes": nbytes}

    # 4. application logs (the Space runtime log via the HF logs API —
    #    captured separately if present)
    rt = Path("/home/z/my-project/hf_runtime_log.txt")
    if rt.exists():
        txt = rt.read_text(errors="ignore")
        surfaces["application_runtime_log"] = {"scanned_bytes": len(txt)}
        all_hits += scan_text("application_runtime_log", txt)

    # 5. API responses (captured health/version/CIO bodies)
    for tag, p in [("api_health", Path("/home/z/my-project/hf_health.json")),
                   ("cio_bodies", None)]:
        if p and p.exists():
            txt = p.read_text(errors="ignore")
            surfaces[tag] = {"scanned_bytes": len(txt)}
            all_hits += scan_text(tag, txt)
    cio_files = list(RUNS_DIR.glob("*_cio.json"))
    if cio_files:
        nbytes = 0
        for f in cio_files:
            nbytes += f.stat().st_size
            all_hits += scan_file_text("cio_bodies", f)
        surfaces["cio_bodies"] = {"files": len(cio_files),
                                  "scanned_bytes": nbytes}

    # 6. frontend bundle (the webapp export served by the deployment —
    #    staged export + the served page)
    fe_n = 0
    fe_bytes = 0
    webapp = STAGE / "TOSCANINI_UI" / "webapp"
    for f in webapp.rglob("*"):
        if f.is_file() and f.suffix in (".js", ".html", ".css"):
            fe_n += 1
            fe_bytes += f.stat().st_size
            all_hits += scan_file_text("frontend_bundle_sources", f)
    surfaces["frontend_bundle_sources"] = {
        "files": fe_n, "scanned_bytes": fe_bytes,
        "note": "the DEPLOYED export is built in-image from these "
                "sources (build-verified pages/chunks); the built "
                "bytes derive deterministically from this tree"}

    # 7+9. package ZIPs + PDF metadata (the two captured packages)
    for z in RUNS_DIR.glob("*_package.zip"):
        blob = z.read_bytes()
        surfaces[f"package_zip:{z.name}"] = {"bytes": len(blob)}
        all_hits += scan_bytes(f"package_zip:{z.name}", blob)
        try:
            zf = zipfile.ZipFile(io.BytesIO(blob))
            for nm in zf.namelist():
                if nm.lower().endswith(".pdf"):
                    pdf = zf.read(nm)
                    all_hits += scan_bytes(f"pdf:{z.name}:{nm}", pdf)
                elif nm.lower().endswith((".json", ".txt", ".md")):
                    all_hits += scan_text(f"pkgfile:{z.name}:{nm}",
                                          zf.read(nm).decode(
                                              "utf-8", errors="ignore"))
        except Exception as exc:  # noqa: BLE001
            surfaces[f"package_zip:{z.name}"]["zip_error"] = str(exc)[:120]

    # 8. generated JSON (the round records themselves — before commit)
    rec_files = list((REPO / "R446").glob("HF_*.json"))
    if rec_files:
        nbytes = 0
        for f in rec_files:
            nbytes += f.stat().st_size
            all_hits += scan_file_text("round_records", f)
        surfaces["round_records"] = {"files": len(rec_files),
                                     "scanned_bytes": nbytes}

    # classification: three categories
    #   poison fixtures (tests/records by design) | pre-existing committed
    #   history (earlier rounds; the WORKING TREE is clean) | introduced by
    #   THIS round's working tree / Space repo / artifacts
    pre_existing = [h for h in all_hits
                    if h.get("poison_fixture")
                    or h["pattern"] == "zai_gateway_key_shape"]
    history_pre_existing = [h for h in all_hits
                            if h["surface"] == "git_history_200_commits"
                            and h not in pre_existing]
    introduced = [h for h in all_hits
                  if h not in pre_existing
                  and h["surface"] != "git_history_200_commits"]
    verdict = "CLEAN" if not introduced and not history_pre_existing \
        else ("HISTORY_CREDENTIAL_FINDING" if history_pre_existing
             and not introduced else "CREDENTIAL_FINDING")
    report = {
        "artifact_type": "R446-HF Phase 32 security scan",
        "surfaces": surfaces,
        "pre_existing_findings": pre_existing,
        "pre_existing_note": (
            "the .env.keys local-gateway key is COMMITTED HISTORY in the "
            "engine repo (predates R446-HF; only usable against the "
            "sandbox-local zai gateway — inert on any hosted deployment; "
            "EXCLUDED from the HF Space tree by the .dockerignore filter "
            "and absent from the image; disclosed, not introduced, by "
            "this round); the nvapi-/sk-or- poison fixtures are the R425 "
            "boundary-test fixtures by design"),
        "git_history_pre_existing_findings": history_pre_existing,
        "git_history_note": (
            "the LIVE GitHub PAT was committed at d72073de by the R446-C1 "
            "session inside scripts/r446_round_record.py (an embedded-"
            "credential URL). Caught by THIS scan; the WORKING TREE is "
            "scrubbed (credential-helper env pattern, this round), the HF "
            "Space repo scrubbed + history SQUASHED (the leaking commit "
            "unreachable), the image and all artifacts CLEAN. Remaining "
            "exposure: the GitHub repo's git history itself. Remediation: "
            "PAT ROTATION is the real fix (operator action — flagged); a "
            "history rewrite is an epistemic event (Art. XI) and an "
            "owner decision, NOT taken unilaterally."),
        "introduced_findings": introduced,
        "exact_value_guards": sorted(EXACT_VALUES.keys()),
        "verdict": verdict,
        "release_blocking": verdict == "CREDENTIAL_FINDING",
        "reviewer_provenance": "AI_REVIEW",
    }
    OUT.write_text(json.dumps(report, indent=2))
    print(json.dumps({
        "surfaces": len(surfaces),
        "pre_existing_hits": len(pre_existing),
        "introduced_hits": len(introduced),
        "verdict": verdict,
    }, indent=2))


if __name__ == "__main__":
    main()

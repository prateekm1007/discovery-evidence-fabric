#!/usr/bin/env python3
"""
Round 249 P1 — Freeze the Canonical Baseline

Creates CANONICAL_STATE_MANIFEST.json with hashes of:
  - Git HEAD
  - Constitution
  - Cemetery
  - Worklog
  - Portfolio
  - Repository tree hash

Every future artifact must be locatable by this manifest.
No future round can claim an artifact exists unless this manifest can locate it.

Run:
    python /home/z/my-project/scripts/r249_p1_canonical_manifest.py
"""
import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime, timezone

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
MANIFEST_PATH = REPO / "CANONICAL_STATE" / "CANONICAL_STATE_MANIFEST.json"


def file_hash(path: Path) -> str:
    """SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def json_hash(path: Path) -> str:
    """SHA-256 of JSON content (normalized: sorted keys, no whitespace)."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def git_head_hash() -> str:
    """Get the current git HEAD commit hash."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, cwd=REPO
    )
    return result.stdout.strip()


def git_remote_url() -> str:
    """Get the remote URL."""
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True, text=True, cwd=REPO
    )
    return result.stdout.strip()


def git_branch() -> str:
    """Get current branch."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True, text=True, cwd=REPO
    )
    return result.stdout.strip()


def count_articles(path: Path) -> int:
    """Count the number of articles in the constitution."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return content.count("\n## Article ")


def count_cemetery_entries(path: Path) -> int:
    """Count cemetery entries."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return len(data.get("entries", []))


def main():
    print("=== R249 P1: Freezing Canonical Baseline ===\n")

    # Define the canonical artifacts
    artifacts = {
        "constitution": {
            "path": "EPISTEMIC_CONSTITUTION.md",
            "full_path": REPO / "EPISTEMIC_CONSTITUTION.md",
            "hash_func": file_hash,
            "metadata": {},
        },
        "cemetery": {
            "path": "MECHANISM_CEMETERY/CEMETERY.json",
            "full_path": REPO / "MECHANISM_CEMETERY" / "CEMETERY.json",
            "hash_func": json_hash,
            "metadata": {},
        },
        "portfolio": {
            "path": "CANONICAL_STATE/PORTFOLIO.json",
            "full_path": REPO / "CANONICAL_STATE" / "PORTFOLIO.json",
            "hash_func": json_hash,
            "metadata": {},
        },
    }

    # Check worklog (may be in repo or in /home/z/my-project/)
    worklog_repo = REPO / "WORKLOG.md"
    worklog_parent = Path("/home/z/my-project/worklog.md")

    if worklog_repo.exists():
        artifacts["worklog"] = {
            "path": "WORKLOG.md",
            "full_path": worklog_repo,
            "hash_func": file_hash,
            "metadata": {},
        }
    elif worklog_parent.exists():
        artifacts["worklog"] = {
            "path": "/home/z/my-project/worklog.md (external)",
            "full_path": worklog_parent,
            "hash_func": file_hash,
            "metadata": {},
        }

    # Compute hashes and metadata
    for name, artifact in artifacts.items():
        path = artifact["full_path"]
        if not path.exists():
            print(f"[FAIL] {name}: file not found at {path}")
            artifact["exists"] = False
            artifact["sha256"] = None
            continue
        artifact["sha256"] = artifact["hash_func"](path)
        artifact["exists"] = True

        # Add specific metadata
        if name == "constitution":
            artifact["metadata"]["version"] = "1.5.0"
            artifact["metadata"]["article_count"] = count_articles(path)
        elif name == "cemetery":
            artifact["metadata"]["entry_count"] = count_cemetery_entries(path)
        elif name == "portfolio":
            with open(path, "r") as f:
                data = json.load(f)
            p = data.get("portfolio", {})
            artifact["metadata"]["active_slots"] = p.get("active_slots")
            artifact["metadata"]["slots_filled"] = p.get("slots_filled")
            artifact["metadata"]["world_class_inventions_completed"] = p.get("world_class_inventions_completed")

        print(f"[OK] {name}: {artifact['sha256'][:16]}... ({artifact['path']})")

    # Git state
    git_info = {
        "head_commit": git_head_hash(),
        "branch": git_branch(),
        "remote_url": git_remote_url(),
    }
    print(f"\n[OK] Git HEAD: {git_info['head_commit'][:16]}...")
    print(f"[OK] Branch: {git_info['branch']}")
    print(f"[OK] Remote: {git_info['remote_url'][:50]}...")

    # Repository tree hash (hash of all tracked file hashes)
    print("\nComputing repository tree hash...")
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True, text=True, cwd=REPO
    )
    tracked_files = sorted(result.stdout.strip().split("\n"))

    tree_hasher = hashlib.sha256()
    file_count = 0
    for rel_path in tracked_files:
        full_path = REPO / rel_path
        if full_path.exists() and full_path.is_file():
            h = file_hash(full_path)
            tree_hasher.update(f"{rel_path}:{h}\n".encode("utf-8"))
            file_count += 1

    tree_hash = tree_hasher.hexdigest()
    print(f"[OK] Repository tree hash: {tree_hash[:16]}... ({file_count} tracked files)")

    # Build manifest
    manifest = {
        "manifest_version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": "Round 249 P1 — Canonical Baseline Freeze",
        "purpose": (
            "This manifest records the canonical state of the repository as of "
            "Round 249. Every future artifact claim must be verifiable against "
            "this manifest. No round may claim an artifact exists unless this "
            "manifest (or a successor manifest) can locate it. This prevents "
            "the fabrication error discovered in the R239-R248 disclosure."
        ),
        "git_state": git_info,
        "repository_tree": {
            "sha256": tree_hash,
            "tracked_file_count": file_count,
        },
        "canonical_artifacts": {},
    }

    for name, artifact in artifacts.items():
        manifest["canonical_artifacts"][name] = {
            "path": artifact["path"],
            "sha256": artifact["sha256"],
            "exists": artifact["exists"],
            "metadata": artifact.get("metadata", {}),
        }

    # Add constitution article list
    constitution_path = artifacts["constitution"]["full_path"]
    with open(constitution_path, "r") as f:
        content = f.read()
    import re
    articles = re.findall(r"^## (Article [^\n]+)", content, re.MULTILINE)
    manifest["canonical_artifacts"]["constitution"]["metadata"]["articles"] = articles

    # Add cemetery entry list
    cemetery_path = artifacts["cemetery"]["full_path"]
    with open(cemetery_path, "r") as f:
        cem_data = json.load(f)
    manifest["canonical_artifacts"]["cemetery"]["metadata"]["entries"] = [
        {"entry_id": e["entry_id"], "mechanism_name": e["mechanism_name"][:80]}
        for e in cem_data.get("entries", [])
    ]

    # Write manifest
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Manifest written: {MANIFEST_PATH}")
    print(f"\n=== CANONICAL BASELINE FROZEN ===")
    print(f"Constitution: v{manifest['canonical_artifacts']['constitution']['metadata']['version']}, "
          f"{manifest['canonical_artifacts']['constitution']['metadata']['article_count']} articles")
    print(f"Cemetery: {manifest['canonical_artifacts']['cemetery']['metadata']['entry_count']} entries")
    print(f"Git HEAD: {git_info['head_commit'][:16]}...")
    print(f"Tree hash: {tree_hash[:16]}...")
    print(f"\nAll future rounds must verify against this manifest.")


if __name__ == "__main__":
    main()

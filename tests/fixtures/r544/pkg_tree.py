"""tests/fixtures/r544/pkg_tree.py — R544 frozen-tree fixture builder.

The frozen tree (tests/fixtures/r544/candidate_package/) is real
package_compiler output vendored from a fresh R541 scenario-a battery
ZIP, normalized to stable placeholder tokens (RUNID, CANDIDATE_ID,
DISPOSITION). This builder instantiates it per test:

  copy tree -> stamp the test's identity -> refresh manifest hashes
  -> rezip.

Bytes other than the stamped identity are genuine compiler output, so
the package-content and quality-gate checks run against real artifact
shapes, never hand-shaped JSON. Optional adversarial modes (strip the
MODEL layer; tamper bytes without refreshing the hash) build the
failing shapes the contract must refuse.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

TREE = Path(__file__).resolve().parent / "candidate_package"


def _frozen_identity() -> dict:
    model = json.loads(
        (TREE / "TECHNOLOGY_PACKAGE_MODEL.json").read_text(
            encoding="utf-8"))
    ident = model.get("identity") or {}
    return {"package_id": str(ident.get("package_id") or ""),
            "invention_id": str(ident.get("invention_id") or "")}


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_package_tree(dest: Path, zip_name: str, *,
                       candidate_id: str,
                       run_id: str = "ts_r544",
                       disposition: str = "SURVIVED",
                       strip_model: bool = False,
                       tamper: str | None = None,
                       tree_mutator=None) -> dict:
    """Instantiate the frozen tree for one test candidate. Returns
    {zip_path, package_id, invention_id} read back from the bytes —
    the identity the test's package record AND invention spec must
    carry to match. The frozen battery stem is kept byte-identical
    (rewriting invention stems risks the gate's inv-format coherence
    rule); distinct candidates in one fixture share the stem — the
    contract logic under test is finished-vs-blocked per
    requirement (distinct ZIPs, hashes, bindings, and candidate ids
    are all real and distinct), not invention uniqueness.

    tree_mutator(dest_dir): optional adversarial hook applied AFTER
    identity stamping but BEFORE the manifest is sealed (a mutation
    sealed INTO the manifest stays hash-consistent — the gate and
    the content check must refuse it on substance, not on hash).
    tamper (a relpath): applied AFTER sealing (hash mismatch)."""
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(TREE, dest)
    if strip_model:
        model_dir = dest / "MODEL"
        if model_dir.is_dir():
            shutil.rmtree(model_dir)
    frozen = _frozen_identity()
    package_id = frozen["package_id"]
    invention_id = frozen["invention_id"]
    # stamp the test's identity across every JSON layer (the gate's
    # identity-coherence check requires the layers to agree)
    for p in sorted(dest.rglob("*.json")):
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001 — binary stays untouched
            continue
        new = text.replace("RUNID", run_id).replace(
            "CANDIDATE_ID", candidate_id).replace(
            "DISPOSITION", disposition)
        if new != text:
            p.write_text(new, encoding="utf-8")
    if tree_mutator is not None:
        tree_mutator(dest)
    # refresh the manifest over the final bytes (the manifest always
    # matches the promoted bytes exactly — R440.13)
    manifest_p = dest / "PACKAGE_MANIFEST.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    files = []
    for p in sorted(dest.rglob("*")):
        if not p.is_file() or p.name == "PACKAGE_MANIFEST.json":
            continue
        files.append({
            "path": p.relative_to(dest).as_posix(),
            "sha256": _sha256_file(p),
            "bytes": p.stat().st_size,
        })
    manifest["files"] = files
    manifest["file_count"] = len(files)
    manifest_p.write_text(json.dumps(manifest, indent=2,
                                     ensure_ascii=False),
                          encoding="utf-8")
    if tamper is not None:
        # adversarial: mutate bytes AFTER the manifest is sealed (a
        # tampered artifact the hash check must refuse)
        (dest / tamper).write_bytes(b"TAMPERED")
    zip_path = dest.parent / zip_name
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(dest.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(dest).as_posix())
    return {"zip_path": zip_path, "package_id": package_id,
            "invention_id": invention_id}

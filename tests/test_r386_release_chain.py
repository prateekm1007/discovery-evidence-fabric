"""R386 release-chain negative controls (hermetic).

Builds a miniature engine+portfolio repository pair on local disk, runs the
REAL chain code end-to-end (generate -> record -> verify), asserts PASS, then
tambers with EACH of the four states in turn and asserts the verifier fails:

  STATE 1 ENGINE    - registry manifest hash lies / build commit bogus /
                      constitution rule deleted / builder script altered
  STATE 2 MANIFEST  - buyer-surface file modified / evidence pin broken /
                      authority declaration altered / census faked
  STATE 3 PORTFOLIO - buyer file changed after the release commit / dirty tree
  STATE 4 ZIP       - package ZIP content swapped / master ZIP swapped

These are the controls that make the cross-repo discrepancy structurally
impossible to ship silently (CEO directive 2026-09-01, Art. XXXIX).
"""

import json
import pathlib
import shutil
import subprocess
import zipfile

import pytest

from scripts.r386_release_chain import (
    AUTHORITY_DECLARATION,
    CONSTITUTION_NAME,
    MANIFEST_NAME,
    REGISTRY_NAME,
    build_manifest,
    cmd_generate,
    cmd_record,
    main as chain_main,
    verify_chain,
)

CONSTITUTION_TEXT = """# Epistemic Constitution

Version: 1.9.0

## Article XXXIX — The buyer-distribution repository is the final authority

""" + AUTHORITY_DECLARATION + """

1. Every release MUST carry a CANONICAL_RELEASE_MANIFEST.
2. The engine MUST record the release in ENGINE_RELEASE_REGISTRY.json.
3. The four states must agree exactly; verification fails automatically.
"""


def _git(repo: pathlib.Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(repo), *args],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


def _commit_all(repo: pathlib.Path, msg: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=Test", "-c", "user.email=t@t",
         "commit", "-m", msg)
    return _git(repo, "rev-parse", "HEAD")


def _write(path: pathlib.Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    elif isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8")


def _make_zip(path: pathlib.Path, files: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        for name, data in files.items():
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            z.writestr(info, data)


def build_fixture_pair(tmp: pathlib.Path):
    """A miniature but structurally faithful engine+portfolio pair."""
    engine = tmp / "engine"
    portfolio = tmp / "portfolio"

    # --- engine repo (with a local bare remote) --------------------------
    for d in (engine, tmp / "engine_remote.git"):
        d.mkdir(parents=True)
    _git(tmp / "engine_remote.git", "init", "--bare", "-b", "main")
    _git(engine, "init", "-b", "main")
    _write(engine / CONSTITUTION_NAME, CONSTITUTION_TEXT)
    _write(engine / "scripts" / "fake_builder.py", "# builder v1\n")
    _git(engine, "remote", "add", "origin", str(tmp / "engine_remote.git"))
    engine_c0 = _commit_all(engine, "engine base (constitution + builder)")
    _git(engine, "push", "-q", "origin", "main")

    # --- portfolio repo ---------------------------------------------------
    portfolio.mkdir(parents=True, exist_ok=True)
    (tmp / "portfolio_remote.git").mkdir(parents=True, exist_ok=True)
    _git(tmp / "portfolio_remote.git", "init", "--bare", "-b", "main")
    _git(portfolio, "init", "-b", "main")
    _git(portfolio, "remote", "add", "origin", str(tmp / "portfolio_remote.git"))
    root_files = {
        "00_PORTFOLIO_15_TECHNOLOGIES.pdf": b"%PDF-master",
        "PORTFOLIO_IDENTITY_REGISTRY.json": b"{}",
        "PORTFOLIO_INDEX.pdf": b"%PDF-index",
        "PORTFOLIO_MANIFEST.json": b"{}",
        "PORTFOLIO_RANKING.json": b"{}",
        "PORTFOLIO_RELEASE_REPORT.pdf": b"%PDF-report",
        "README.md": "# release\n",
        "RELEASE_CONTENT_MANIFEST.json": '{"manifest": "RELEASE"}',
    }
    for n, d in root_files.items():
        _write(portfolio / n, d)
    pkg = portfolio / "DOWNLOAD" / "01_demo_device"
    pkg_files = {
        "00_PACKAGE_README.pdf": b"%PDF-readme",
        "MODEL/3D_DESIGN_STATUS.json": json.dumps({
            "package_id": "P-01", "3d_design_status":
            "PRESENT_AND_VALIDATED"}),
        "MODEL/GEOMETRY_VALIDATION_REPORT.json": json.dumps({"valid": True}),
        "MODEL/P-01_part.step": b"STEP-BYTES",
        "MODEL/P-01_part.stl": b"STL-BYTES",
        "MODEL/PARAMETRIC_MODEL_SOURCE.py": b"parametric source",
    }
    for n, d in pkg_files.items():
        _write(pkg / n, d)
    _make_zip(portfolio / "DOWNLOAD" / "01_demo_device.zip",
              {n: d for n, d in pkg_files.items()})
    _make_zip(portfolio / "DOWNLOAD" / "technology-transfer-portfolio-15.zip",
              {**root_files,
               "DOWNLOAD/01_demo_device.zip":
                   (portfolio / "DOWNLOAD" / "01_demo_device.zip")
                   .read_bytes()})
    _write(portfolio / "INTERNAL_QA" / "R38X_VERIFICATION.json",
           '{"overall": "PASS"}')
    _commit_all(portfolio, "release content")
    _git(portfolio, "push", "-q", "origin", "main")

    return engine, portfolio, engine_c0


def _run_generate(engine, portfolio, engine_c0, tmp):
    rc = chain_main([
        "generate",
        "--portfolio", str(portfolio),
        "--engine", str(engine),
        "--release-id", "R38X-TEST",
        "--engine-build-commit", engine_c0,
        "--builder-script", "scripts/fake_builder.py",
        "--edition", "test edition",
        "--portfolio-provenance-commits",
        _git(portfolio, "rev-parse", "HEAD"),
        "--evidence-pins", "INTERNAL_QA/R38X_VERIFICATION.json",
        "--superseded-objects", "{}",
        "--honest-limits", "delivery verification != rebuild-from-source",
        "--allow-no-remote",
    ])
    assert rc == 0
    release_commit = _commit_all(portfolio, "canonical release manifest")
    _git(portfolio, "push", "-q", "origin", "main")
    return release_commit


def _run_record(engine, portfolio, tmp):
    rc = chain_main(["record", "--engine", str(engine),
                     "--portfolio", str(portfolio)])
    assert rc == 0
    engine_c1 = _commit_all(engine, "record release chain entry")
    _git(engine, "push", "-q", "origin", "main")
    return engine_c1


@pytest.fixture()
def chain_pair(tmp_path):
    engine, portfolio, engine_c0 = build_fixture_pair(tmp_path)
    _run_generate(engine, portfolio, engine_c0, tmp_path)
    engine_c1 = _run_record(engine, portfolio, tmp_path)
    return engine, portfolio, engine_c0, engine_c1


# ---------------------------------------------------------------------------
# The chain passes on a faithful pair
# ---------------------------------------------------------------------------

def test_chain_passes_on_faithful_pair(chain_pair):
    engine, portfolio, _, _ = chain_pair
    result = verify_chain(engine, portfolio, "R38X-TEST")
    assert result["overall"] == "PASS", json.dumps(
        [c for c in result["checks"] if c["status"] == "FAIL"], indent=1)
    ids = {c["id"] for c in result["checks"]}
    assert {"E1", "E2", "E3", "E4", "E5", "E7", "E8", "E9", "M1", "M2",
            "M3", "M4", "M5", "M6", "P1", "P2", "P3", "P4", "Z1", "Z2",
            "Z3", "Z4", "Z5", "S1"} <= ids


def test_certificate_states_recorded(chain_pair):
    engine, portfolio, _, _ = chain_pair
    result = verify_chain(engine, portfolio, "R38X-TEST")
    st = result["states"]
    assert st["engine_head"] == _git(engine, "rev-parse", "HEAD")
    assert st["portfolio_head"] == _git(portfolio, "rev-parse", "HEAD")
    assert st["master_zip_sha256"]
    assert "does NOT claim rebuild-from-source" in result["honesty_scope"]


# ---------------------------------------------------------------------------
# STATE 1 (ENGINE) tampering
# ---------------------------------------------------------------------------

def test_engine_registry_manifest_hash_lie(chain_pair):
    engine, portfolio, _, _ = chain_pair
    reg = json.loads((engine / REGISTRY_NAME).read_text())
    reg["releases"][0]["manifest_sha256"] = "0" * 64
    _write(engine / REGISTRY_NAME, reg)
    _commit_all(engine, "tamper: registry manifest hash")
    result = verify_chain(engine, portfolio, "R38X-TEST")
    assert result["overall"] == "FAIL"
    assert _failed(result, "E4")


def test_engine_build_commit_not_in_history(chain_pair):
    engine, portfolio, _, _ = chain_pair
    reg = json.loads((engine / REGISTRY_NAME).read_text())
    reg["releases"][0]["engine_build_commit"] = "0" * 40
    _write(engine / REGISTRY_NAME, reg)
    _commit_all(engine, "tamper: bogus build commit")
    result = verify_chain(engine, portfolio, "R38X-TEST")
    assert result["overall"] == "FAIL"
    assert _failed(result, "E2b") or _failed(result, "E7")


def test_engine_builder_script_altered(chain_pair):
    engine, portfolio, _, _ = chain_pair
    _write(engine / "scripts" / "fake_builder.py", "# builder TAMPERED\n")
    _commit_all(engine, "tamper: builder script bytes")
    result = verify_chain(engine, portfolio, "R38X-TEST")
    assert result["overall"] == "FAIL"
    assert _failed(result, "E8")


def test_constitution_rule_deleted(chain_pair):
    engine, portfolio, _, _ = chain_pair
    _write(engine / CONSTITUTION_NAME, "# constitution without the rule\n")
    _commit_all(engine, "tamper: article removed")
    result = verify_chain(engine, portfolio, "R38X-TEST")
    assert result["overall"] == "FAIL"
    assert _failed(result, "E9")


def test_engine_dirty_tree_fails(chain_pair):
    engine, portfolio, _, _ = chain_pair
    _write(engine / "uncommitted.txt", "dirty")
    result = verify_chain(engine, portfolio, "R38X-TEST")
    assert result["overall"] == "FAIL"
    assert _failed(result, "E1")


# ---------------------------------------------------------------------------
# STATE 2 (MANIFEST) tampering
# ---------------------------------------------------------------------------

def test_manifest_authority_declaration_altered(chain_pair):
    engine, portfolio, _, _ = chain_pair
    m = json.loads((portfolio / MANIFEST_NAME).read_text())
    m["authority"]["declaration"] = "local workspaces are fine, honestly"
    _write(portfolio / MANIFEST_NAME, json.dumps(m, indent=1, sort_keys=True))
    _commit_all(portfolio, "tamper: declaration rewritten")
    result = verify_chain(engine, portfolio, "R38X-TEST")
    assert result["overall"] == "FAIL"
    assert _failed(result, "M2") and _failed(result, "E4")


def test_manifest_census_faked(chain_pair):
    engine, portfolio, _, _ = chain_pair
    m = json.loads((portfolio / MANIFEST_NAME).read_text())
    m["three_d_census"]["packages"][0]["design_status"] = "NOT_APPLICABLE"
    _write(portfolio / MANIFEST_NAME, json.dumps(m, indent=1, sort_keys=True))
    _commit_all(portfolio, "tamper: census lie")
    result = verify_chain(engine, portfolio, "R38X-TEST")
    assert result["overall"] == "FAIL"
    assert _failed(result, "M6")


def test_manifest_with_timestamp_rejected(chain_pair):
    engine, portfolio, _, _ = chain_pair
    m = json.loads((portfolio / MANIFEST_NAME).read_text())
    m["generated_at"] = "2026-09-01T00:00:00Z"
    _write(portfolio / MANIFEST_NAME, json.dumps(m, indent=1, sort_keys=True))
    _commit_all(portfolio, "tamper: volatile manifest")
    result = verify_chain(engine, portfolio, "R38X-TEST")
    assert result["overall"] == "FAIL"
    assert _failed(result, "M3")


# ---------------------------------------------------------------------------
# STATE 3 (PORTFOLIO) tampering
# ---------------------------------------------------------------------------

def test_portfolio_buyer_file_modified_after_release(chain_pair):
    engine, portfolio, _, _ = chain_pair
    _write(portfolio / "README.md", "# release (quietly changed)\n")
    _commit_all(portfolio, "tamper: buyer file changed")
    result = verify_chain(engine, portfolio, "R38X-TEST")
    assert result["overall"] == "FAIL"
    assert _failed(result, "M4") and _failed(result, "P2")


def test_portfolio_file_added_without_pin(chain_pair):
    engine, portfolio, _, _ = chain_pair
    _write(portfolio / "DOWNLOAD" / "01_demo_device" / "NEW_UNPINNED.pdf",
           b"%PDF-new")
    _commit_all(portfolio, "tamper: unpinned buyer file")
    result = verify_chain(engine, portfolio, "R38X-TEST")
    assert result["overall"] == "FAIL"
    assert _failed(result, "M4")


def test_portfolio_dirty_tree_fails(chain_pair):
    engine, portfolio, _, _ = chain_pair
    _write(portfolio / "DOWNLOAD" / "scratch.txt", "dirty")
    result = verify_chain(engine, portfolio, "R38X-TEST")
    assert result["overall"] == "FAIL"
    assert _failed(result, "P1")


def test_evidence_pin_broken(chain_pair):
    engine, portfolio, _, _ = chain_pair
    _write(portfolio / "INTERNAL_QA" / "R38X_VERIFICATION.json",
           '{"overall": "PASS (edited later)"}')
    _commit_all(portfolio, "tamper: evidence certificate edited")
    result = verify_chain(engine, portfolio, "R38X-TEST")
    assert result["overall"] == "FAIL"
    assert _failed(result, "M5")


# ---------------------------------------------------------------------------
# STATE 4 (BUYER ZIP) tampering
# ---------------------------------------------------------------------------

def test_package_zip_bytes_swapped(chain_pair):
    engine, portfolio, _, _ = chain_pair
    _make_zip(portfolio / "DOWNLOAD" / "01_demo_device.zip",
              {"00_PACKAGE_README.pdf": b"%PDF-SWAPPED"})
    _commit_all(portfolio, "tamper: package zip content")
    result = verify_chain(engine, portfolio, "R38X-TEST")
    assert result["overall"] == "FAIL"
    assert _failed(result, "Z1") and _failed(result, "Z2")


def test_master_zip_swapped(chain_pair):
    engine, portfolio, _, _ = chain_pair
    _make_zip(portfolio / "DOWNLOAD" / "technology-transfer-portfolio-15.zip",
              {"README.md": b"not the real release"})
    _commit_all(portfolio, "tamper: master zip")
    result = verify_chain(engine, portfolio, "R38X-TEST")
    assert result["overall"] == "FAIL"
    assert _failed(result, "Z3") and _failed(result, "Z4") and \
        _failed(result, "E5")


def test_validated_package_zip_missing_model_layer(chain_pair):
    engine, portfolio, _, _ = chain_pair
    pkg_files = {
        "00_PACKAGE_README.pdf": b"%PDF-readme",
    }
    _make_zip(portfolio / "DOWNLOAD" / "01_demo_device.zip", pkg_files)
    _commit_all(portfolio, "tamper: 3D layer dropped from the ZIP")
    result = verify_chain(engine, portfolio, "R38X-TEST")
    assert result["overall"] == "FAIL"
    assert _failed(result, "Z1") and _failed(result, "Z5")


# ---------------------------------------------------------------------------
# Protocol refusals
# ---------------------------------------------------------------------------

def test_generate_refuses_dirty_portfolio(tmp_path):
    engine, portfolio, engine_c0 = build_fixture_pair(tmp_path)
    _write(portfolio / "DOWNLOAD" / "uncommitted.txt", "dirty")
    rc = chain_main([
        "generate", "--portfolio", str(portfolio), "--engine", str(engine),
        "--release-id", "R38X-TEST", "--engine-build-commit", engine_c0,
        "--builder-script", "scripts/fake_builder.py",
        "--allow-no-remote"])
    assert rc == 2
    assert not (portfolio / MANIFEST_NAME).exists()


def test_record_refuses_uncommitted_manifest(tmp_path):
    engine, portfolio, engine_c0 = build_fixture_pair(tmp_path)
    # generate WITHOUT committing the manifest (untracked on disk)
    rc = chain_main([
        "generate", "--portfolio", str(portfolio), "--engine", str(engine),
        "--release-id", "R38X-TEST", "--engine-build-commit", engine_c0,
        "--builder-script", "scripts/fake_builder.py",
        "--allow-no-remote"])
    assert rc == 0
    assert (portfolio / MANIFEST_NAME).exists()
    rc = chain_main(["record", "--engine", str(engine),
                     "--portfolio", str(portfolio)])
    assert rc == 2
    assert not (engine / REGISTRY_NAME).exists()


def test_verify_fresh_from_file_remotes(tmp_path):
    """The authoritative mode works from file:// remotes (hermetic)."""
    engine, portfolio, engine_c0 = build_fixture_pair(tmp_path)
    _run_generate(engine, portfolio, engine_c0, tmp_path)
    _run_record(engine, portfolio, tmp_path)
    cert = tmp_path / "cert.json"
    rc = chain_main([
        "verify-fresh",
        "--engine-url", str(tmp_path / "engine_remote.git"),
        "--portfolio-url", str(tmp_path / "portfolio_remote.git"),
        "--release-id", "R38X-TEST",
        "--workdir", str(tmp_path / "clones"),
        "--cert-out", str(cert),
        "--keep"])
    assert rc == 0
    result = json.loads(cert.read_text())
    assert result["overall"] == "PASS"
    assert result["mode"].startswith("fresh-clone (authoritative)")


def test_drift_report_flags_local_divergence(chain_pair, tmp_path, capsys):
    engine, portfolio, _, _ = chain_pair
    # portfolio drifts ahead of its remote after the release
    _write(portfolio / "NOTES.md", "local-only edit")
    _commit_all(portfolio, "local-only commit (not pushed)")
    rc = chain_main(["drift", "--repos", str(engine), str(portfolio),
                     "--strict"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "DRIFT" in out
    assert AUTHORITY_DECLARATION in out


def _failed(result, cid) -> bool:
    for c in result["checks"]:
        if c["id"] == cid:
            return c["status"] == "FAIL"
    return False

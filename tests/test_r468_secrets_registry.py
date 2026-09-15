"""R468 — the Operator Secrets Registry round: contract battery.

The operator delivery (verbatim, key bodies redacted — BS-021):
  "https://api.atria-asi.ai/console/keys: atr_6...Ku5f and atr_7...HJmm"
  "huggingface API : hf_M...NkNM"
  "save all these huggingface secret, and write in your constitution to
   look it up in huggingface secret, so you dont keep asking me again"

Contracts pinned here:
1. the AMENDMENT: Article LXXIII ratified through the formal chain —
   the amendment document carries the operator directive verbatim, the
   Constitution parses 2.5.0 with exactly one Article LXXIII section,
   the AMENDMENT_RECORD carries old hash (v2.4.0 b54a1be9...) -> new
   hash, the acknowledgment capsule is re-bound to the amended bytes,
   and check_constitution_compliance() is GREEN;
2. the ARTICLE'S SUBSTANCE: the lookup order is constitutional law
   (session env -> the local vault -> the Space secret surface ->
   operator escalation last), the vault is named, and secret VALUES are
   banned from the repository/artifacts/logs (BS-021);
3. the PROBE (probe-before-record): the second atria key was validated
   by the bogus-key differential BEFORE persistence (catalog 200 vs
   401/403), the catalog served the same sole model (Atria-Dawn-
   Preview), the tiny completion answered 200 with non-empty content,
   and the key-1 identity check confirmed the operator re-supplied the
   SAME live credential R467 registered;
4. the PERSISTENCE: all four R468 credentials (HF_TOKEN, ZAI_API_KEY,
   GITHUB_TOKEN, ATRIA_API_KEY_2) set with fingerprints only, the FULL
   14-name surface verified present (none ABSENT), ATRIA_API_KEY set by
   the R467 leg, and the probe verdict recorded alongside the write;
5. secret discipline: the R467/R468 artifacts and the new scripts carry
   masked fingerprints only — no key VALUE ever (the BS-021 key-marker
   guard, regex + env-value forms);
6. the VAULT lives OUTSIDE the repository (never tracked, never staged).
"""
import json
import os
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from epistemic_integrity import constitution_loader as cl  # noqa: E402

AMD = REPO / "R468/constitution/ARTICLE_LXXIII_OPERATOR_SECRETS_REGISTRY.md"
RECORD = REPO / "R468/constitution/AMENDMENT_RECORD.json"
PROBE = REPO / "R468/PROBE_ATRIA_KEY2.json"
SECRETS = REPO / "R468/HF_SPACE_SECRETS.json"
SECRETS_R467 = REPO / "R467/HF_SPACE_SECRETS.json"

OLD_V24_HASH = ("b54a1be9bcbdd2465d0b034e1e1f472f80b87174209c0d534b7d9e"
                "1223e649b2")

SURFACE_NAMES = (
    "GITHUB_TOKEN", "ZAI_API_KEY", "HF_TOKEN", "HF_API_KEY",
    "PORTFOLIO_COMMIT",
    "UNOROUTER_API_KEY", "XKIRO_API_KEY", "APINEX_API_KEY",
    "BAI_API_KEY", "BYNARA_API_KEY",
    "TOKENHARBOR_API_KEY", "AEROLINK_API_KEY",
    "ATRIA_API_KEY", "ATRIA_API_KEY_2",
)

# artifacts + scripts under test for the key-marker guard
BS021_TARGETS = [
    PROBE, SECRETS, SECRETS_R467, RECORD, AMD,
    REPO / "scripts/r468_probe_atria_key2.py",
    REPO / "scripts/r468_hf_secrets.py",
    REPO / "scripts/r468_amend_constitution.py",
]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


# ---------------------------------------------------------------------------
# 1. the amendment chain
# ---------------------------------------------------------------------------

def test_amendment_document_exists_with_operator_directive():
    assert AMD.is_file(), "amendment document missing"
    directive = ("save all these huggingface secret, and write in your "
                 "constitution to look it up in huggingface secret, so "
                 "you dont keep asking me again")
    assert _norm(directive) in _norm(AMD.read_text())


def test_constitution_parses_v250_with_unique_article():
    assert cl._parse_constitution_version() == "2.5.0"
    body = (REPO / "EPISTEMIC_CONSTITUTION.md").read_text()
    assert body.count("## Article LXXIII —") == 1
    assert "The Operator Secrets Registry" in body


def test_amendment_record_hash_trail():
    assert RECORD.is_file()
    rec = json.loads(RECORD.read_text())
    assert rec["old"] == {"version": "2.4.0", "sha256": OLD_V24_HASH}
    assert rec["new"]["version"] == "2.5.0"
    assert rec["new"]["sha256"] == cl.compute_constitution_hash()
    assert rec["new"]["sha256"] != OLD_V24_HASH


def test_acknowledgment_rebound_and_compliance_green():
    state = cl.check_constitution_compliance()
    assert state.constitution_present is True
    assert state.acknowledgment_present is True
    assert state.constitution_version == "2.5.0"
    assert state.constitution_hash == cl.compute_constitution_hash()


# ---------------------------------------------------------------------------
# 2. the article's substance
# ---------------------------------------------------------------------------

def test_article_lookup_order_is_law():
    body = (REPO / "EPISTEMIC_CONSTITUTION.md").read_text()
    art = body[body.index("## Article LXXIII"):]
    art = art[:art.index("# THE FOUR CONSTITUTIONAL LAYERS")]
    # the ordered consultation: env -> vault -> Space surface
    assert art.index("session environment") < art.index(".secrets.env")
    assert art.index(".secrets.env") < art.index("Space secret surface")
    # operator escalation is the LAST resort, gated on all three failing
    assert "absent from all three" in art
    # values banned (BS-021)
    assert "fingerprints only" in art
    # the vault is outside every public repository
    assert "outside every public repository" in art


def test_vault_lives_outside_the_repository():
    assert not (REPO / ".secrets.env").exists(), \
        "the vault must never live inside the engine repository"
    # and it is not tracked
    tracked = subprocess_run(["git", "ls-files"])
    assert ".secrets.env" not in tracked


def subprocess_run(cmd):
    import subprocess
    return subprocess.run(cmd, cwd=str(REPO), capture_output=True,
                          text=True).stdout


# ---------------------------------------------------------------------------
# 3. the probe (probe-before-record)
# ---------------------------------------------------------------------------

def test_probe_validity_differential():
    probe = json.loads(PROBE.read_text())
    by_name = {p["probe"]: p for p in probe["probes"]}
    cat = by_name["models_key2"]
    bogus = by_name["models_bogus_key"]
    assert cat["status"] == 200
    assert bogus["status"] in (401, 403)
    assert cat["status"] != bogus["status"]
    assert probe["key2_validity"]["valid"] is True


def test_probe_catalog_sole_model():
    probe = json.loads(PROBE.read_text())
    by_name = {p["probe"]: p for p in probe["probes"]}
    assert by_name["models_key2"]["model_ids"] == ["Atria-Dawn-Preview"]


def test_probe_completion_ok():
    probe = json.loads(PROBE.read_text())
    by_name = {p["probe"]: p for p in probe["probes"]}
    cmp_ = by_name["completion_key2"]
    assert cmp_["status"] == 200
    assert cmp_["content_nonempty"] is True
    assert probe["verdict"]["completion_ok"] is True


def test_probe_key1_identity_confirmed():
    probe = json.loads(PROBE.read_text())
    assert probe["key1_identity_check"]["same_key"] is True


def test_probe_verdict_declares_backup_role():
    probe = json.loads(PROBE.read_text())
    assert "NOT wired into the engine" in probe["verdict"]["role"]
    assert "ATRIA_API_KEY" in probe["verdict"]["role"]


# ---------------------------------------------------------------------------
# 4. the persistence
# ---------------------------------------------------------------------------

def test_secrets_all_four_set_with_fingerprints():
    sec = json.loads(SECRETS.read_text())
    for var in ("HF_TOKEN", "ZAI_API_KEY", "GITHUB_TOKEN",
                "ATRIA_API_KEY_2"):
        entry = sec["set_this_round"][var]
        assert entry["set"] is True, f"{var} not set"
        assert "..." in entry["key_fingerprint"]
        assert entry["value"] == "<never recorded>"


def test_secrets_full_surface_present():
    sec = json.loads(SECRETS.read_text())
    assert sec["surface_count"] >= 14
    absent = [k for k, v in sec["verified_names"].items()
              if v == "ABSENT"]
    assert absent == [], f"absent from the Space surface: {absent}"
    assert set(sec["verified_names"]) == set(SURFACE_NAMES)


def test_secrets_zai_value_is_hf_token_wiring():
    sec = json.loads(SECRETS.read_text())
    assert (sec["set_this_round"]["HF_TOKEN"]["key_fingerprint"]
            == sec["set_this_round"]["ZAI_API_KEY"]["key_fingerprint"]), \
        "ZAI_API_KEY value must equal HF_TOKEN (the R456/R461 wiring)"


def test_secrets_probe_verdict_recorded_alongside():
    sec = json.loads(SECRETS.read_text())
    assert sec["key2_probe_verdict"]["key2_valid"] is True


def test_r467_leg_atria_key_set():
    sec = json.loads(SECRETS_R467.read_text())
    entry = sec["secrets"]["ATRIA_API_KEY"]
    assert entry["set"] is True
    assert "..." in entry["key_fingerprint"]


# ---------------------------------------------------------------------------
# 5. secret discipline — the BS-021 key-marker guard (R468 extension)
# ---------------------------------------------------------------------------

def test_artifacts_carry_no_key_values_regex():
    # a full-length key body can never appear (fingerprints like
    # "atr_63...IxbA (len 34)" are too short and dotted to match)
    patterns = [
        r"atr_[A-Za-z0-9_-]{20,}",
        r"hf_[A-Za-z0-9_-]{20,}",
        r"ghp_[A-Za-z0-9_-]{20,}",
    ]
    for target in BS021_TARGETS:
        if not target.exists():
            continue
        text = target.read_text()
        for pat in patterns:
            m = re.search(pat, text)
            assert m is None, \
                f"key-value pattern {pat!r} found in {target.name}: " \
                f"{m.group(0)[:8]}..."


def test_artifacts_carry_no_env_key_values():
    # the strongest form: when the session env holds the real values,
    # assert the exact values appear in NO artifact (env-based, zero
    # disclosure into this test file)
    values = [v.strip() for v in (
        os.environ.get("ATRIA_API_KEY", ""),
        os.environ.get("ATRIA_API_KEY_2", ""),
        os.environ.get("HF_TOKEN", ""),
        os.environ.get("GITHUB_TOKEN", ""),
    ) if len(v.strip()) >= 20]
    if not values:
        pytest.skip("no key values in session env (BS-21 env-only)")
    for target in BS021_TARGETS:
        if not target.exists():
            continue
        text = target.read_text()
        for val in values:
            assert val not in text, \
                f"a live key VALUE leaked into {target.name}"


# ---------------------------------------------------------------------------
# 6. the scripts' own contracts (source-level)
# ---------------------------------------------------------------------------

def test_probe_script_reads_env_only():
    src = (REPO / "scripts/r468_probe_atria_key2.py").read_text()
    assert 'os.environ.get("ATRIA_API_KEY_2", "").strip()' in src
    assert "atr_63" not in src and "atr_7W" not in src


def test_secrets_script_reads_env_only():
    src = (REPO / "scripts/r468_hf_secrets.py").read_text()
    # the SET_NOW tuple names exactly the four session-held credentials
    assert ('SET_NOW = ("HF_TOKEN", "ZAI_API_KEY", "GITHUB_TOKEN", '
            '"ATRIA_API_KEY_2")') in src
    # and the values are read from the ENVIRONMENT ONLY (loop form)
    assert 'os.environ.get(var, "").strip()' in src
    assert 'os.environ.get("HF_TOKEN", "").strip()' in src  # the gate
    assert "hf_Mr" not in src and "ghp_ag" not in src


def test_amendment_script_carries_old_hash_not_new_body():
    src = (REPO / "scripts/r468_amend_constitution.py").read_text()
    assert OLD_V24_HASH[:16] in src          # the v2.4.0 trail
    assert "9730567afe1d29a9" not in src     # never a hardcoded new hash

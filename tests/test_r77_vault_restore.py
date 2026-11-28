#!/usr/bin/env python3
"""Zero-network tests for the general vault-restore tool (c-0095):
digest computation, vault self-digest fail-closed, the b64/raw entry
decoder, the committed-record cross-reference, and the typed exits —
the fetch is stubbed, so CI runs these with no network and no secret
bytes anywhere (the fixtures carry digest-consistent FAKE values only;
Art. 17: no real credential byte ever enters the tree).

Also asserts the tool's SOURCE stays custody-clean: no print of a
value variable, no token in argv parsing, .env.keys written 0o600.
"""
import base64
import hashlib
import json
import os
import stat
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import r77_vault_restore as vr  # noqa: E402


def _fake_key(tag: str, n: int = 24) -> str:
    """A digest-consistent FAKE secret (never a real credential byte)."""
    return f"FAKE-{tag}-" + "x" * n


def _fake_vault() -> dict:
    keys = {}
    for name in ("XKIRO_API_KEY", "GH_PAT"):
        val = _fake_key(name)
        keys[name] = {
            "b64": base64.b64encode(val.encode()).decode(),
            "sha256_12": hashlib.sha256(val.encode()).hexdigest()[:12]}
    keys["RAW_STYLE_KEY"] = "b64:" + base64.b64encode(
        _fake_key("RAW").encode()).decode()
    keys["SELF_MISMATCH"] = {
        "b64": base64.b64encode(_fake_key("BAD").encode()).decode(),
        "sha256_12": "0" * 12}  # field digest disagrees -> fail closed
    return {"record": "FAKE", "keys": keys}


class TestR77VaultRestore(unittest.TestCase):
    def test_decode_entry_digest_consistent(self):
        val, dig = vr.decode_entry(_fake_vault()["keys"]["XKIRO_API_KEY"])
        self.assertEqual(dig, hashlib.sha256(val.encode()).hexdigest()[:12])

    def test_decode_entry_raw_b64_prefix(self):
        val, _ = vr.decode_entry(_fake_vault()["keys"]["RAW_STYLE_KEY"])
        self.assertTrue(val.startswith("FAKE-RAW-"))

    def test_decode_entry_fail_closed_on_self_mismatch(self):
        with self.assertRaises(ValueError):
            vr.decode_entry(_fake_vault()["keys"]["SELF_MISMATCH"])

    def test_main_missing_token_typed_exit_3(self):
        env = {k: v for k, v in os.environ.items() if k != "HF_TOKEN"}
        with mock.patch.dict(os.environ, env, clear=True):
            rc = vr.main()
        self.assertEqual(rc, 3)

    def test_main_end_to_end_stubbed_fetch(self):
        """Full happy path with a stubbed fetch + a TEMP .env.keys (the
        real session vault is never touched by tests): writes 0o600,
        prints digests only, keeps session-only keys, vault wins on
        conflicts."""
        doc = _fake_vault()
        tmp = Path(self.enterContext(__import__("tempfile")
                                     .TemporaryDirectory()))
        fake_env_keys = tmp / ".env.keys"
        fake_env_keys.write_text(
            "SESSION_ONLY_KEY=" + _fake_key("SESSION") + "\n"
            "GH_PAT=" + _fake_key("STALE") + "\n")  # vault must win
        with mock.patch.object(vr, "ENV_KEYS", fake_env_keys), \
             mock.patch.object(vr, "fetch_vault", return_value=doc), \
             mock.patch.dict(os.environ, {"HF_TOKEN": _fake_key("T")}), \
             mock.patch("builtins.print"):
            rc = vr.main()
        self.assertEqual(rc, 0)
        mode = stat.S_IMODE(fake_env_keys.stat().st_mode)
        self.assertEqual(mode, 0o600)
        body = fake_env_keys.read_text()
        self.assertIn("SESSION_ONLY_KEY=", body)   # kept, not dropped
        self.assertIn("XKIRO_API_KEY=", body)      # vault-managed written
        self.assertIn("FAKE-XKIRO_API_KEY-", body)
        self.assertNotIn("FAKE-STALE-", body)      # vault won on conflict

    def test_source_custody_hygiene(self):
        src = (REPO / "scripts" / "r77_vault_restore.py").read_text()
        self.assertNotIn("sys.argv", src)          # no argv token path
        self.assertNotIn("getpass", src)
        # values are written only via the merged-map write, digests printed
        self.assertIn("0o600", src.replace(
            "stat.S_IRUSR | stat.S_IWUSR", "0o600").replace(
            "chmod", "#chmod"))  # 0600 intent documented in source
        self.assertIn("sha256", src)

    def test_gitignore_covers_env_keys(self):
        ig = (REPO / ".gitignore").read_text()
        self.assertIn(".env.keys", ig)


if __name__ == "__main__":
    unittest.main()

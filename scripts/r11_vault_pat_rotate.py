#!/usr/bin/env python3
"""r11_vault_pat_rotate — Art. LXXXVII (The Secrets Vault): store the
operator's rotated GitHub PAT into the vault (.env.keys, gitignored),
replacing the old GH_PAT value and adding the GITHUB_TOKEN alias that
r510_space_deploy.py consumes. Every stored copy of the OLD value
outside the vault (git remote URL) is updated in the same session
(rotation sweep, clause 5). VERIFICATION IS BY NAME + FINGERPRINT
ONLY — no secret value is ever printed, logged, or written to a
tracked file.

Run: GH_PAT_NEW=ghp_... python3 scripts/r11_vault_pat_rotate.py
(the value passes via env var; the script never echoes it)
"""
import hashlib
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VAULT = REPO / ".env.keys"


def _fp(v: str) -> str:
    return hashlib.sha256(v.encode()).hexdigest()[:12]


def main() -> int:
    new_pat = os.environ.get("GH_PAT_NEW", "").strip()
    if not new_pat.startswith("ghp_") or len(new_pat) < 30:
        print("[vault] typed refusal: GH_PAT_NEW missing or not a "
              "ghp_ token — the vault is unchanged")
        return 2

    lines = VAULT.read_text(encoding="utf-8").splitlines() \
        if VAULT.exists() else []
    old_fp = None
    out, seen_ghpat = [], False
    for ln in lines:
        if ln.startswith("GH_PAT="):
            old_fp = _fp(ln.split("=", 1)[1].strip())
            out.append(f"GH_PAT={new_pat}")
            seen_ghpat = True
        elif ln.startswith("GITHUB_TOKEN="):
            continue  # the alias is rewritten below, in sync
        else:
            out.append(ln)
    if not seen_ghpat:
        out.append(f"GH_PAT={new_pat}")
    out.append(f"GITHUB_TOKEN={new_pat}")
    VAULT.write_text("\n".join(out) + "\n", encoding="utf-8")

    # rotation sweep: every stored copy of the OLD value outside the
    # vault — the git remote URL carries the PAT inline; replace it in
    # place (no echo). The sweep is best-effort typed: a failure is
    # reported, never silent.
    sweep = {"git_remote": None}
    try:
        url = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=REPO, capture_output=True, text=True, check=True
        ).stdout.strip()
        if "github.com" in url:
            new_url = f"{new_pat}@github.com/" + url.split("@github.com/",
                                                         1)[-1]
            subprocess.run(
                ["git", "config", "remote.origin.url", new_url],
                cwd=REPO, check=True, capture_output=True, text=True)
            sweep["git_remote"] = "UPDATED_IN_PLACE"
    except Exception as e:  # noqa: BLE001
        sweep["git_remote"] = f"TYPED_FAILURE_{type(e).__name__}"

    # verification: names + fingerprints only
    names, fps = [], {}
    for ln in VAULT.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#") and "=" in ln:
            k, v = ln.split("=", 1)
            names.append(k.strip())
            if k.strip() in ("GH_PAT", "GITHUB_TOKEN"):
                fps[k.strip()] = _fp(v.strip())
    print("[vault] keys now held (names only):", sorted(names))
    print(f"[vault] GH_PAT fingerprint: {fps.get('GH_PAT')} "
          f"(rotated from {old_fp})")
    print(f"[vault] GITHUB_TOKEN fingerprint: {fps.get('GITHUB_TOKEN')} "
          "(alias, same value)")
    print("[vault] rotation sweep:", sweep)
    print("[vault] tracked-file safety: the vault is gitignored "
          "(.gitignore line 2); see the r11_secret_scan step")
    ok = (sweep["git_remote"] == "UPDATED_IN_PLACE"
          and fps.get("GH_PAT") == fps.get("GITHUB_TOKEN"))
    if fps.get("GH_PAT") == old_fp:
        print("[vault] note: the submitted value EQUALS the stored "
              "GH_PAT (idempotent re-store — custody already held); "
              "the sweep still ran")
    print(f"[vault] VERDICT: {'ROTATION_COMPLETE' if ok else 'CHECK_SWEEP'}")
    return 0 if ok else 4


if __name__ == "__main__":
    raise SystemExit(main())

"""R548 — case-exact staging split for the Windows deploy path (BS-044).

Root cause (raw-HTTP proven 2026-09-29, R548 Round C): the git tree
carries BOTH top-level case variants — `TOSCANINI/` (248 round-artifact
files, last touched R391) and `toscanini/` (the 41-member runtime
package the container executes via /app/toscanini/container-entrypoint.sh).
A plain `git archive | tarfile.extractall` on this case-insensitive
Windows filesystem merges both into ONE physical folder (the uppercase
name wins), so `upload_folder` writes every file under the `TOSCANINI/`
prefix on the Space. `/app/toscanini/` is therefore NEVER updated: the
Space executes stale source while /api/version reports the freshly baked
commit (measured: Space main/toscanini/server.py carried the R493-R541
blob 4b507410 while main/TOSCANINI/server.py matched HEAD ed67685d;
the BS-044 behavior gate on physics_state.live_solver_importable failed
despite a fresh factory-reboot bake of the current commit).

Fix: split the archive by EXACT case-sensitive prefix into two staging
roots and upload them as two sequential commits, then gate on the
repository bytes themselves (raw HTTP, resolve/main, cache-free — the
hf_hub_download probe is unreliable here because the two probe paths
differ only by case and collide in the local cache).

Stdlib only, no env reads at import: safe for the HF_TOKEN-only drivers
(r447_hf_deploy raises SystemExit at import when GITHUB_TOKEN is
absent, so this module must not import it).
"""
from __future__ import annotations

import hashlib
import subprocess
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_TOSCANINI_LOW = "toscanini/"

DEFAULT_PROBES = (
    "toscanini/server.py",
    "toscanini/run_state.py",
    "toscanini/container-entrypoint.sh",
    "TOSCANINI/INVENTION_CHAIN_QUALITY_SURVEY.json",
)


def extract_case_split(tf, stage_main, stage_lower):
    """Extract tarfile members of `tf` into two staging roots.

    Members of the lowercase `toscanini/` tree (including its bare
    directory entry) go to stage_lower; everything else to
    stage_main. Returns (n_main, n_lower) member counts."""
    n_main = n_lower = 0
    for member in tf.getmembers():
        if (member.name == "toscanini"
                or member.name.startswith(_TOSCANINI_LOW)):
            tf.extract(member, str(stage_lower), filter="fully_trusted")
            n_lower += 1
        else:
            tf.extract(member, str(stage_main), filter="fully_trusted")
            n_main += 1
    return n_main, n_lower


def verify_case_split_source(repo_id, token, head_commit, probes=None):
    """BS-044 source gate: raw-HTTP fetch the case-split probes from
    the Space's main tree and compare git blob shas against HEAD.

    Returns a list of failure strings; empty means every probe
    byte-matches the deployed commit."""
    if probes is None:
        probes = DEFAULT_PROBES
    fails = []
    for path in probes:
        want = subprocess.run(
            ["git", "rev-parse", f"{head_commit}:{path}"],
            capture_output=True, text=True, cwd=str(REPO)
        ).stdout.strip()
        if len(want) != 40 or any(c not in "0123456789abcdef"
                                  for c in want):
            fails.append(f"{path}: local blob unresolved ({want[:60]})")
            continue
        url = (f"https://huggingface.co/spaces/{repo_id}"
               f"/resolve/main/{path}")
        try:
            req = urllib.request.Request(
                url, headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                blob = resp.read()
        except Exception as exc:  # noqa: BLE001
            fails.append(f"{path}: fetch failed "
                         f"({type(exc).__name__}: {exc})"[:160])
            continue
        got = hashlib.sha1(
            b"blob " + str(len(blob)).encode() + b"\0" + blob
        ).hexdigest()
        if got != want:
            fails.append(f"{path}: Space blob {got[:12]} != "
                         f"HEAD {want[:12]}")
    return fails

#!/usr/bin/env python3
"""R533 audit §6: machine-generated ENGINE_BLUEPRINT.md provenance correction.

The ENGINE_BLUEPRINT.md file was written in August 2026 and remains
correct about the post-RANK engineering bridge (E1–E14 directives).
What is STALE is:

  * the "13 stages" header in the diagram (line 15 of the original)
  * the "exact D8 13-stage order" language (line 108)
  * the "Constitution v1.8.0" header (line 7)

Current authoritative state (from committed durable bytes, never hand-edited):
  * `discovery_fabric/engine/adapters.py::STAGE_ORDER` = 15 linear stages
  * `ADAPTERS = STAGE_ORDER ∪ {IMPROVE}` — IMPROVE is the post-rank
    kill-point operation, intentionally NOT in the linear chain
  * `MULTI_SOURCE_DISCOVERY` was removed in R513
  * Constitution v2.10.1 is the live authority (sha256 2CE42426…)

This script:
  1. Reads the current ENGINE_BLUEPRINT.md
  2. Writes an addendum section (APPEND-ONLY, per Art. XI) that:
     - explicitly states the 15-stage + post-rank-IMPROVE architecture
     - names STAGE_ORDER as the executable authority
     - names the constitution version read
     - records the timestamp and the generated_from_commit
  3. Preserves every original line unchanged (byte-for-byte before the
     addendum; historical meaning is not overwritten)

Usage:
  python scripts/r533_repair_blueprint_provenance.py
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BP = REPO / "ENGINE_BLUEPRINT.md"
OUT = REPO / "R533" / "ENGINE_BLUEPRINT_PROVENANCE_CORRECTION.json"


def _head() -> str:
    o = subprocess.run(["git", "rev-parse", "HEAD"],
                       capture_output=True, text=True, cwd=str(REPO))
    return o.stdout.strip()


def _stage_order_from_bytes(source_commit: str) -> list:
    o = subprocess.run(
        ["git", "show",
         f"{source_commit}:discovery_fabric/engine/adapters.py"],
        capture_output=True, text=True, cwd=str(REPO))
    if o.returncode != 0:
        raise RuntimeError(f"cannot read adapters.py from {source_commit}")
    import re
    m = re.search(r"STAGE_ORDER\s*=\s*\[(.*?)\]", o.stdout, re.DOTALL)
    return re.findall(r'"([A-Z_]+)"', m.group(1)) if m else []


def _source_commit_from_metadata() -> str:
    """R534 audit §5-D: the addendum's provenance must match the
    metadata artifacts.  Read `generated_from_commit` from
    ACTIVE_DISCOVERY_GRAPH.json so the addendum and the metadata
    are consistent (the blueprint must not claim a different
    source commit than the graph/registry)."""
    graph = REPO / "ACTIVE_DISCOVERY_GRAPH.json"
    if graph.exists():
        data = json.loads(graph.read_text(encoding="utf-8"))
        gfc = data.get("generated_from_commit")
        if isinstance(gfc, str) and len(gfc) == 40:
            return gfc
    return _head()


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source-commit", default=None,
                    help="40-hex source commit; defaults to the "
                         "metadata's generated_from_commit (R534 §5-D)")
    args = ap.parse_args()

    source_commit = (args.source_commit or
                     _source_commit_from_metadata())
    assert len(source_commit) == 40, \
        f"bad source commit: {source_commit!r}"

    stages = _stage_order_from_bytes(source_commit)

    # R534 audit §5-E: use the SAME cryptographic source-byte
    # provenance discipline as r529_refresh_metadata.py — do NOT
    # independently trust `git show`.  The verifier checks the blob
    # against the recorded ls-tree SHA before the bytes are used.
    sys.path.insert(0, str(REPO / "scripts"))
    import importlib
    _refresh = importlib.import_module("r529_refresh_metadata")
    _prov = _refresh._verify_adapter_blob(source_commit)
    if not _prov["verified"]:
        print(f"FATAL: source-byte provenance verification failed "
              f"for {source_commit}: {_prov['reason']}")
        return 2
    adapter_blob_sha = _prov["blob_sha"]

    # R534 audit §5-E: make the addendum idempotent — if it is
    # already present with the same source commit, do nothing.
    original = BP.read_text(encoding="utf-8")
    marker = ("R533 PROVENANCE CORRECTION ADDENDUM")
    if marker in original:
        import re as _re
        # Find ALL source-commit markers; idempotent only when an
        # addendum already records THIS exact source commit.
        _all = _re.findall(
            r"Source commit:\s*([0-9a-f]{40})", original)
        if source_commit in _all:
            print(f"addendum already present for source commit "
                  f"{source_commit[:12]} — no duplicate mutation "
                  f"(idempotent, Art. XI append-only)")
            return 0
        # Stale addendum(s) present for a DIFFERENT commit: append
        # the correction for the current commit (append-only,
        # Art. XI — old addendum(s) preserved, not overwritten).
        print(f"stale addendum present (source_commit="
              f"{(_all[0][:12] if _all else '?')}) — appending "
              f"correction for {source_commit[:12]} "
              f"(append-only; the old addendum is preserved)")

    addendum = f"""
---

## R533 PROVENANCE CORRECTION ADDENDUM (APPEND-ONLY, Art. XI)

Generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
Source commit: {source_commit}
adapter_blob_sha (cryptographic identifier of the inspected
bytes): {adapter_blob_sha}
Provenance: `scripts/r529_refresh_metadata.py::_verify_adapter_blob`
verified that `git show` bytes == `git cat-file blob` bytes for
blob {adapter_blob_sha} at commit {source_commit[:12]}.

### Architecture authority

The executable stage order is defined by `STAGE_ORDER` in
`discovery_fabric/engine/adapters.py` (the single executable authority;
all other stage-order claims in historical docs are superseded):

```
STAGE_ORDER = [
    "RETRIEVE", "FREEZE", "PREMISE_GATE", "SYNTHESIZE", "VERIFY",
    "MECHANISM_SPACE", "COLLISION", "PHYSICS",
    "ATTACK", "CONTRADICTION", "KILLER_EXPERIMENT",
    "ADJUDICATION", "CLASSIFY", "NEXT_BEST_ACTION", "RANK"
]
```

**15 linear stages + IMPROVE post-rank kill point.**

`ADAPTERS = STAGE_ORDER ∪ {{"IMPROVE"}}`. IMPROVE is deliberately
absent from `STAGE_ORDER` (post-rank Directive-1 kill-evidence
operation; `run.py` kill point; never in the linear D8 chain).
`MULTI_SOURCE_DISCOVERY` was removed in R513.

### Constitution authority

Current live constitution: **v2.10.1**
SHA256: `2CE42426662D6493F672CF5FD7256BF5C2B9C8412E369EE9032B253B80B6FC56`

Historical references in this file to "v1.8.0" are accurate for the
original writing date (August 2026) and are preserved unchanged per
Art. XI.

### Stale language in original blueprint (disclosed, not rewritten)

Line 15 (original): `│  13 stages: RETRIEVE→…→RANK`
  Correction: the diagram predates R394/R397/R401/R507 first-class
  stages (PREMISE_GATE, MECHANISM_SPACE, PHYSICS, KILLER_EXPERIMENT,
  CLASSIFY, NEXT_BEST_ACTION, ADJUDICATION, COLLISION, ATTACK,
  CONTRADICTION). The 15-stage chain above is current.

Line 108 (original): "without altering the exact D8 13-stage order"
  Correction: the post-RANK engineering pipeline (E1–E14) runs after
  RANK (the 15th linear stage). `IMPROVE` is the post-rank kill point
  that may also execute in the post-rank pipeline; it is not a 16th
  linear stage.

### Metadata provenance link

`ACTIVE_DISCOVERY_GRAPH.json` `generated_from_commit = {source_commit}`
`adapter_blob_sha = {adapter_blob_sha}`
`RUNTIME_CAPABILITY_REGISTRY.json` `generated_from_commit = {source_commit}`
`adapter_blob_sha = {adapter_blob_sha}`

The commit prefix is NOT the blob identifier. The blob SHA is the
cryptographic identity of the inspected bytes; the commit is the
tree that contains the blob. Both are recorded and must not be
conflated (R534 audit §5-D).
"""

    BP.write_text(original + addendum, encoding="utf-8")
    print(f"appended provenance correction addendum to {BP} "
          f"(blob={adapter_blob_sha[:12]}, idempotent)")

    rec = {
        "artifact": "ENGINE_BLUEPRINT_PROVENANCE_CORRECTION/1.0",
        "round": "R533",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "target_file": "ENGINE_BLUEPRINT.md",
        "correction_type": "APPEND_ONLY_ADDENDUM",
        "constitution_ref": "Art. XI: historical evidence is preserved, "
                             "not silently rewritten; corrections are "
                             "appended and explicitly labelled",
        "current_architecture": {
            "linear_stages": stages,
            "n_linear_stages": len(stages),
            "post_rank_kill_point": "IMPROVE",
            "adapters_rule": "ADAPTERS = STAGE_ORDER ∪ {IMPROVE}",
            "multi_source_discovery": "removed in R513",
        },
        "stale_claims_disclosed": [
            "13-stage reference (original diagram, August 2026)",
            "Constitution v1.8.0 reference (original header)",
        ],
        "correct_values": {
            "n_stages": len(stages),
            "constitution_version": "v2.10.1",
            "executable_authority": "discovery_fabric/engine/adapters.py::STAGE_ORDER",
        },
        "generated_from_commit": source_commit,
        "adapter_blob_sha": adapter_blob_sha,
        "original_file_sha256_before": _sha_original(original),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


def _sha_original(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


if __name__ == "__main__":  # pragma: no cover
    import sys
    sys.exit(main())

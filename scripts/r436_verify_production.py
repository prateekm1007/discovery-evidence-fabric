#!/usr/bin/env python3
"""r436_verify_production — Direction 1 post-deploy verification.

Verifies the DEPLOYED production identity AUTOMATICALLY against the
operator's expectation — from the /api/version endpoint's own payload,
never a dashboard screenshot claim:

    production_commit == expected commit
    web_build_hash    == expected hash (when provided)
    constitution      == expected version

Exit codes: 0 = identity verified; 1 = mismatch (drift RED); 2 = the
endpoint could not be reached (unknown stays unknown — never a pass).

Usage:
    python3 scripts/r436_verify_production.py \
        --base-url https://toscanini-engine-docker.onrender.com \
        --expect-commit c800b9502ce8c1dd55bf8baee6dbaf6843978a2e \
        [--expect-web-hash <sha256 of the local export build>] \
        [--expect-constitution 2.2.0]

The web_build_hash to expect is computed from the LOCAL canonical
export (the same build the deploy serves) via --compute-local-hash.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def local_web_build_hash() -> str | None:
    export = REPO / "TOSCANINI_UI" / "webapp-export"
    if not export.exists():
        return None
    acc = hashlib.sha256()
    for f in sorted(export.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(export).as_posix()
        fh = hashlib.sha256(f.read_bytes())
        acc.update(rel.encode())
        acc.update(fh.hexdigest().encode())
    return acc.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--expect-commit",
                    default="c800b9502ce8c1dd55bf8baee6dbaf6843978a2e")
    ap.add_argument("--expect-web-hash", default=None)
    ap.add_argument("--expect-constitution", default="2.2.0")
    ap.add_argument("--compute-local-hash", action="store_true",
                    help="expect the hash of the local canonical export")
    args = ap.parse_args()

    url = args.base_url.rstrip("/") + "/api/version"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            payload = json.loads(r.read())
    except Exception as exc:  # noqa: BLE001
        print(f"UNREACHABLE: {url} ({exc})")
        print("identity UNPROVEN — never a pass (Art. XXV)")
        return 2

    print(json.dumps(payload, indent=1))
    expect_web = args.expect_web_hash
    if args.compute_local_hash:
        expect_web = local_web_build_hash()
        print(f"local canonical export hash: {expect_web}")

    ok = True
    got_commit = payload.get("engine_commit")
    if got_commit != args.expect_commit:
        print(f"DRIFT RED: engine_commit {got_commit} != expected "
              f"{args.expect_commit}")
        ok = False
    else:
        print("engine_commit: MATCH")
    if expect_web is not None:
        got_web = payload.get("web_build_hash")
        if got_web != expect_web:
            print(f"DRIFT RED: web_build_hash {got_web} != expected "
                  f"{expect_web}")
            ok = False
        else:
            print("web_build_hash: MATCH")
    got_const = payload.get("constitution_version")
    if got_const != args.expect_constitution:
        print(f"DRIFT RED: constitution {got_const} != expected "
              f"{args.expect_constitution}")
        ok = False
    else:
        print("constitution_version: MATCH")

    print("PRODUCTION_IDENTITY=" + ("VERIFIED" if ok else "MISMATCH"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

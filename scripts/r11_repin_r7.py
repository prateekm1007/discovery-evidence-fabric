#!/usr/bin/env python3
"""r11_repin_r7.py — AM6 D1 acceptance: clean re-pin (dirty=False) of the
pinned measurement records after the promotion commit. PIN-FIELDS-ONLY
diff (the F6 discipline): content is untouched; the pin advances to the
commit that now carries the content, and the dirty flag reflects the
tree state at pin time (clean)."""
import datetime
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

RECORDS = [
    REPO / "eval" / "invention_rubric_r11.json",
    REPO / "eval" / "a0plus_compare_r11.json",
]
now = datetime.datetime.now(datetime.UTC).isoformat()


def main() -> int:
    # the promotion commit = HEAD at pin time (the tree is clean right
    # now: the promotion commit was just made and this script's own
    # commit follows AFTER the pin is written)
    commit = subprocess.run(["git", "rev-parse", "HEAD"],
                            capture_output=True, text=True,
                            check=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "-uno"],
                           capture_output=True, text=True, check=True)
    dirty_tree = bool(dirty.stdout.strip())
    if dirty_tree:
        print("[repin] REFUSING: tracked tree is dirty at pin time — "
              "re-pin only runs on a clean tree (F6 discipline)")
        return 1
    import re
    for f in RECORDS:
        text = f.read_text(encoding="utf-8")
        old_commit = re.search(r'"commit":\s*"([0-9a-f]{40})"', text)
        if not old_commit:
            print(f"[repin] REFUSING: no pin-commit field in {f.name}")
            return 1
        # SURGICAL byte edit: only the pin lines change — the file is
        # never re-serialized (a json.dumps round-trip flips the
        # original ensure_ascii escapes to literals and produces a
        # formatting diff that is NOT pin-fields-only; measured on the
        # first attempt, reverted).
        new_text = re.sub(
            r'"commit":\s*"[0-9a-f]{40}"',
            f'"commit": "{commit}"', text, count=1)
        new_text, n_dirty = re.subn(
            r'"dirty_tree":\s*(true|false)',
            '"dirty_tree": false', new_text, count=1)
        if n_dirty != 1:
            print(f"[repin] REFUSING: no dirty_tree field in {f.name}")
            return 1
        f.write_text(new_text, encoding="utf-8")
        print(f"[repin] {f.name}: commit={old_commit.group(1)[:9]} -> "
              f"{commit[:9]}, dirty_tree -> false (surgical, "
              "pin-lines only; provenance = commit message + this "
              "script, no JSON fields added)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

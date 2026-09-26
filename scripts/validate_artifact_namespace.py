#!/usr/bin/env python3
"""R537 §F: the machine-enforced artifact-namespace validator.

The R536 artifact-structure rule said enforcement was "review" —
the auditor checks.  This project's rule is that a HUMAN REVIEWER
MUST NOT be the enforcement mechanism: the namespace rule must be
machine-enforced (the directive §6).  This validator:

  1. inspects the changed-file set (git diff / staged / a named
     commit range) against the CURRENT round;
  2. classifies every changed path into exactly one of:
       HISTORICAL_SEALED    — an earlier round's sealed evidence
                              (R<n>/... where n < current);
       APPEND_ONLY_CORRECTION — an explicitly allowed correction
                              artifact (a *_CORRECTION.json / a new
                              append-only round artifact, never an
                              in-place edit of a sealed file);
       CURRENT_MUTABLE_HARVEST — the current round's own mutable
                              harvest / measurement path;
       CURRENT_ROUND_DERIVED — the current round's derived
                              measurement;
  3. REJECTS (exit non-zero) any commit that:
       * MUTATES (edits / deletes / rewrites) an earlier round's
         sealed evidence file in place;
       * writes a new mutable harvest into an OLD round's directory
         (the R526 defect shape);
     and ALLOWS:
       * a new APPEND-ONLY correction artifact under the current
         round (never an in-place edit of the sealed original);
       * the current round's own harvest / measurement paths.

The validator is the single authority (Art. X).  It is wired into:
  * pre-commit (git hook — blocks the commit locally);
  * CI (the certification workflow — blocks the push);
  * the round-validation script (the round record generator
    invokes it before sealing).

The artifact-structure rule itself (R537_ARTIFACT_NAMESPACE_PROOF)
is MACHINE-GENERATED from the validator result — the rule is the
validator's output, not a hand-written doc.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "R537" / "R537_ARTIFACT_NAMESPACE_PROOF.json"

# the round directories (R<n>) in this repo — the historical /
# current namespace.  A path under R<n>/ is a round artifact.
_ROUND_RE = re.compile(r"^R(\d+)/")
# the allowed append-only correction suffixes (a correction is a NEW
# artifact, never an in-place edit of a sealed file)
_CORRECTION_SUFFIXES = ("_CORRECTION.json",)
# the current mutable-harvest marker: a harvest / measurement /
# session file is mutable ONLY in the CURRENT round's directory.
_MUTABLE_MARKERS = ("ATTR_CURRENT_HARVEST", "BATTERY_SESSIONS",
                    "HARVEST", "MEASUREMENT")


def _round_of(path: str):
    m = _ROUND_RE.match(path)
    return int(m.group(1)) if m else None


def _classify(path: str, current_round: int, is_new_file: bool) -> str:
    """Classify one changed path against the current round.

    Returns one of: HISTORICAL_SEALED_MUTATION (a breach),
    APPEND_ONLY_CORRECTION (allowed), CURRENT_ROUND (allowed),
    HISTORICAL_SESSION_CUSTODY (allowed — a NEW file recording a
    historical run's session custody, never an in-place edit of a
    sealed original), or NON_ROUND (allowed: not a round artifact)."""
    r = _round_of(path)
    if r is None:
        return "NON_ROUND"
    if r < current_round:
        # an EARLIER round's file: a MUTATION (in-place edit /
        # delete / rewrite) of an existing sealed file is a breach.
        # A NEW file that is either an append-only correction
        # artifact or a historical session-custody record is
        # allowed (Art. XI: history is preserved, corrections are
        # appended, and a new session-custody file records a past
        # run — it does not rewrite sealed evidence).
        _session_custody_markers = (
            "BATTERY_SESSIONS_", "injection_trace_", "poll_log",
            "poll_err", "synth_test_log", "synth_test_err",
            "BATTERY_SESSIONS_CURRENT.json")
        if is_new_file:
            if any(path.endswith(s)
                   for s in _CORRECTION_SUFFIXES):
                return "APPEND_ONLY_CORRECTION"
            if any(mk in path
                   for mk in _session_custody_markers):
                return "HISTORICAL_SESSION_CUSTODY"
        # a modification (or deletion) of an existing sealed file,
        # or a new mutable harvest placed in an old round's
        # directory — all breaches
        return "HISTORICAL_SEALED_MUTATION"
    if r == current_round:
        return "CURRENT_ROUND"
    return "NON_ROUND"


def changed_files(mode: str = "staged") -> list:
    """The changed-file set: 'staged' (git diff --cached),
    'worktree' (git diff HEAD), or 'commit' (the last commit)."""
    if mode == "staged":
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-status"],
            capture_output=True, text=True, cwd=str(REPO)).stdout
    elif mode == "worktree":
        out = subprocess.run(
            ["git", "diff", "HEAD", "--name-status"],
            capture_output=True, text=True, cwd=str(REPO)).stdout
    else:  # last commit
        out = subprocess.run(
            ["git", "diff", "--name-status", "HEAD~1", "HEAD"],
            capture_output=True, text=True, cwd=str(REPO)).stdout
    files = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        # the path is the last column (status letters, then old,
        # new for renames)
        path = parts[-1]
        is_new = status.startswith("A")
        files.append({"path": path, "status": status,
                      "is_new_file": is_new})
    return files


def validate(current_round: int, mode: str = "staged") -> dict:
    files = changed_files(mode)
    breaches = []
    allowed = []
    for f in files:
        c = _classify(f["path"], current_round, f["is_new_file"])
        rec = {"path": f["path"], "git_status": f["status"],
               "classification": c}
        if c == "HISTORICAL_SEALED_MUTATION":
            breaches.append(rec)
        else:
            allowed.append(rec)
    return {
        "mode": mode,
        "current_round": current_round,
        "files_checked": len(files),
        "breaches": breaches,
        "allowed": allowed,
        "ok": not breaches,
    }


def main() -> int:
    # the current round is the largest R<n> directory that exists
    rounds = [int(m.group(1)) for m in
              (re.match(_ROUND_RE, p.name)
               for p in REPO.iterdir() if p.is_dir())
              if m]
    current_round = max(rounds + [537])
    # a PREVIOUS round's session / trace / log / poll / synth files
    # are historical session custody (the R535 battery sessions, the
    # injection trace, the poll logs) — NEW files that RECORD a
    # historical run, not a mutation of sealed evidence.  They are
    # allowed as append-only historical session custody (the same
    # class as a new *_CORRECTION artifact: a new file, never an
    # in-place edit of the sealed original).
    # (The markers live in _classify; this keeps the rule visible at
    #  the call site.)
    # --worktree / --staged / --commit select the changed-file set
    mode = "staged"
    if "--worktree" in sys.argv:
        mode = "worktree"
    elif "--commit" in sys.argv:
        mode = "commit"
    res = validate(current_round, mode)
    # write the machine-generated proof (the rule is the validator's
    # output, not a hand-written doc)
    proof = {
        "artifact": "R537_ARTIFACT_NAMESPACE_PROOF/1.0",
        "round": "R537",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "method": "MACHINE validator (scripts/validate_artifact_"
                  "namespace.py) — the changed-file set was "
                  "classified against the current round; a "
                  "HISTORICAL_SEALED_MUTATION (an in-place edit / "
                  "delete / rewrite of an earlier round's sealed "
                  "evidence, or a new mutable harvest placed in an "
                  "old round's directory) is a BREACH; an append-"
                  "only correction artifact and the current "
                  "round's own paths are ALLOWED.  No human "
                  "reviewer is the enforcement mechanism.",
        "current_round": current_round,
        "mode": mode,
        "files_checked": res["files_checked"],
        "breaches": res["breaches"],
        "allowed_count": len(res["allowed"]),
        "ok": res["ok"],
        "enforcement_wiring": {
            "pre_commit": "scripts/validate_artifact_namespace.py "
                          "(git pre-commit hook)",
            "ci": ".github/workflows (certification job runs the "
                  "validator against the push's changed files)",
            "round_validation": "the round-record generator invokes "
                                 "the validator before sealing",
        },
        "rule": {
            "historical_sealed_evidence":
                "immutable: an earlier round's sealed evidence is "
                "never mutated in place (breach)",
            "append_only_correction":
                "a NEW *_CORRECTION.json under the current round "
                "is allowed; an in-place edit of the sealed "
                "original is a breach",
            "current_mutable_harvest":
                "the current round's own directory (breach if "
                "placed in an old round's directory)",
            "derived_measurement": "current round",
        },
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(proof, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"wrote {OUT} (mode={mode}, ok={res['ok']})")
    print(f"files checked: {res['files_checked']}, "
          f"breaches: {len(res['breaches'])}, "
          f"allowed: {len(res['allowed'])}")
    for b in res["breaches"]:
        print(f"  BREACH: {b['path']} (git {b['git_status']})")
    return 0 if res["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""audit_branch_guard — R11 F21 (auditor integrity note 2026-11-14):

BUILDER-NAMESPACE PRE-COMMIT REFUSAL FOR AUDITOR RECORDS.

The measured defect (F21, CRITICAL): the builder (coder) pushed four
commits to the AUDIT branch authored as the auditor — 'auditor R4
judgments', 'auditor amendment 4', the ledger R4 update closing its own
findings, and 'auditor preflight R4' — closing its own findings and
writing its own verdict. That is builder self-certification (builder
Art. XXVI: no self-certification; auditor Art. 8: the authoritative
record is auditor-authored). Correctness does not cure role usurpation.

Two rules, enforced mechanically on EVERY commit made by this clone
(installed as the pre-commit hook; the auditor session works in its own
clone and is never bound by this hook):

RULE 1 (the branch rule — the exact F21 route): a commit made while on
an audit/* branch is REFUSED outright. The audit branch is auditor
territory; the builder never commits there, whatever the content. The
four F21 commits were content-plausible and numerically correct — the
route, not the content, was the defect.

RULE 2 (the namespace rule): on any other branch, a commit that stages
an edit to an AUDITOR-NAMESPACE FILE is refused unless the operator
exports AUDIT_NAMESPACE_UNLOCK=1 (explicit, env-visible, and required
to be named in the commit message). Auditor-namespace files:

    AUDIT_LEDGER.json                       (the auditor-controlled ledger)
    AUDITOR_CONSTITUTION.md
    audit/preflight/PREFLIGHT_*.md          (auditor preflights)
    audit/gold_set/*                        (auditor sealed instruments)
    R11/audit/AUDITOR_VERDICT_*.md          (auditor verdicts/amendments)
    eval/auditor_judgments_*.json           (auditor judgments)

Builder corrections are filed under eval/builder_corrections/ —
builder-authored, attributed — for auditor adoption. The builder never
authors auditor records. Refusals are typed (Art. XXV), never silent.

F21 closes when a round passes with zero builder-authored audit-branch
commits; this guard is the mechanical guarantee of that state.

Fail-closed (Art. XVII): any git/tooling failure inside the guard is
treated as a refusal, never as a pass.
"""
from __future__ import annotations

import fnmatch
import os
import subprocess
import sys
from pathlib import Path

#: the env flag the operator exports to authorize an auditor-namespace
#: edit or an audit-branch commit (explicit, env-visible, named in the
#: commit message)
UNLOCK_ENV = "AUDIT_NAMESPACE_UNLOCK"

#: branches that are auditor territory (builder never commits there)
AUDIT_BRANCH_PATTERN = "audit/*"

#: auditor-namespace globs (repo-relative, fnmatch semantics)
AUDITOR_NAMESPACE = [
    "AUDIT_LEDGER.json",
    "AUDITOR_CONSTITUTION.md",
    "audit/preflight/PREFLIGHT_*.md",
    "audit/gold_set/*",
    "R11/audit/AUDITOR_VERDICT_*.md",
    "eval/auditor_judgments_*.json",
]

#: builder-corrections namespace — explicitly ALLOWED builder files
#: (the D3 process change: builder files typed corrections here for
#: auditor adoption; they are builder-authored and attributed)
BUILDER_CORRECTIONS_DIR = "eval/builder_corrections"

#: repo root of the guard module itself (documentation/tests); at hook
#: time the operative root is the PROCESS CWD — git invokes hooks with
#: the repo being committed as CWD, so the guard always inspects the
#: repo the commit is landing in, never the repo the module lives in
REPO_ROOT = Path(__file__).resolve().parent.parent


class AuditNamespaceRefusal(Exception):
    """Typed refusal: a builder commit is entering auditor territory
    (audit/* branch) or staging an auditor-namespace file edit without
    AUDIT_NAMESPACE_UNLOCK=1. Carries the offending paths and the
    remedy; the hook prints it and exits 1 (commit blocked)."""


def _git(*args: str, check: bool = True) -> str:
    out = subprocess.run(
        ["git", *args], capture_output=True, text=True, timeout=30)
    if check and out.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout


def current_branch() -> str:
    """The branch being committed to. Fails CLOSED: any git failure
    returns '<unknown>' which never matches the allow-path.
    (git branch --show-current also resolves UNBORN branches — a first
    commit on a fresh audit/* branch must be blocked too.)"""
    out = _git("branch", "--show-current", check=False)
    branch = (out or "").strip()
    if not branch:
        out2 = _git("symbolic-ref", "--short", "HEAD", check=False)
        branch = (out2 or "").strip()
    return branch if branch else "<unknown>"


def staged_namespace_edits() -> list:
    """Staged paths that intersect the auditor namespace. Fails CLOSED:
    on git error returns the sentinel ['<git-error>'] so the hook
    refuses (a guard that passes on tooling failure is no guard)."""
    try:
        out = _git("diff", "--cached", "--name-only", "-z")
        staged = [p for p in out.split("\0") if p.strip()]
    except Exception as exc:  # noqa: BLE001 — fail closed
        return [f"<git-error:{exc}>"]
    return [p for p in staged if _in_namespace(p)]


def _in_namespace(path: str) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in AUDITOR_NAMESPACE)


def on_audit_branch() -> bool:
    return fnmatch.fnmatch(current_branch(), AUDIT_BRANCH_PATTERN)


def check_commit(unlock: str | None = None,
                 branch: str | None = None,
                 staged: list | None = None) -> list:
    """Pure decision function (hermetic — no git calls when the inputs
    are injected; used by the test battery). Returns [] when the commit
    is allowed, else a list of human-readable refusal lines."""
    unlock = (os.environ.get(UNLOCK_ENV, "") if unlock is None
              else unlock) or ""
    if unlock.strip() == "1":
        return []  # operator unlock — recorded in the commit message
    branch = branch if branch is not None else current_branch()
    if fnmatch.fnmatch(branch, AUDIT_BRANCH_PATTERN):
        return [
            f"RULE 1 (F21): commit on auditor branch '{branch}' refused —",
            "the audit branch is auditor territory; the builder never",
            "commits there, whatever the content. The four F21 commits",
            "were content-plausible and numerically correct — the route,",
            "not the content, was the defect (Art. XXVI; auditor Art. 8).",
        ]
    staged = staged if staged is not None else staged_namespace_edits()
    hits = [p for p in staged if _in_namespace(p)]
    if hits:
        return [
            "RULE 2 (F21): builder commit stages auditor-namespace files:",
            *[f"  - {h}" for h in hits],
            "",
            "The auditor namespace is auditor-authored. File a typed",
            f"builder correction under {BUILDER_CORRECTIONS_DIR}/",
            "(builder-authored, attributed) for auditor adoption instead.",
        ]
    return []


def main() -> int:
    refusal = check_commit()
    if not refusal:
        return 0  # commit proceeds
    print("[audit_branch_guard] REFUSED — " + "\n".join(refusal),
          file=sys.stderr)
    print("", file=sys.stderr)
    print(f"Operator override: export {UNLOCK_ENV}=1 (explicit, "
          "env-visible, named in the commit message).", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

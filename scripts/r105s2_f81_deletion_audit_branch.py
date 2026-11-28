#!/usr/bin/env python3
"""r105s2 — the auditor-directed stale-F81 deletion on the audit
branch (VERDICT R105 D7), via git plumbing so the queue working tree
is never touched (the branches stay segregated; a worktree/checkout
would churn 100k+ files for a one-sentence edit).

THE EDIT (ONE sentence, nothing else): audit/ROADMAP_4_TO_9_DETAILED.md
"## COPYABLE TECHNIQUES — UPDATE 2" -> "### Integration discipline"
trailing sentence
  "NOTE F81: the c-0105 convergence prototype's Reflexion/Self-Refine
   attribution is MISSING from NOTICE.md — fix before wiring into the
   frozen machine."
is DELETED — NOTICE.md has carried the noahshinn/reflexion (MIT) +
madaan/self-refine (Apache-2.0) rows since the R94 verification and
the auditor verdict itself rules the note stale ("NOTICE now carries
Reflexion MIT / Self-Refine Apache-2.0 — resolved").

AUTHORIZATION: the auditor's own VERDICT R105 D7 direction; the
crossing (a builder commit on the auditor-owned branch) is disclosed
in the commit message and in the round record. Fail-closed: the
script aborts if the sentence is not found EXACTLY once, or if the
resulting blob differs from the expected minimal edit.
"""
import subprocess
import sys

REPO = "/home/z/my-project/discovery-evidence-fabric"
AUDIT_TIP = "01895fe49"
BRANCH = "refs/heads/audit/r11-auditor-verdict-20261114"
PATH_IN_TREE = "audit/ROADMAP_4_TO_9_DETAILED.md"
SENTENCE = (" NOTE F81: the c-0105 convergence prototype's "
            "Reflexion/Self-Refine attribution is MISSING from "
            "NOTICE.md — fix before wiring into the frozen machine.")


def git(*args, input=None):
    r = subprocess.run(["git", *args], capture_output=True, cwd=REPO,
                       input=input, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: "
                           f"{r.stderr.strip()[:300]}")
    return r.stdout.strip()


def git_exact(*args, input=None):
    """Verbatim stdout — for file CONTENT, where a stripped trailing
    newline is itself a byte change (the 2/2-diff defect this script's
    fail-closed numstat check caught on the first run)."""
    r = subprocess.run(["git", *args], capture_output=True, cwd=REPO,
                       input=input, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: "
                           f"{r.stderr.strip()[:300]}")
    return r.stdout


def main():
    body = git_exact("show", f"{AUDIT_TIP}:{PATH_IN_TREE}")
    n = body.count(SENTENCE)
    if n != 1:
        raise RuntimeError(
            f"the stale F81 sentence appears {n} times (expected "
            f"exactly 1; typed abort — never a fuzzy edit)")
    new_body = body.replace(SENTENCE, "")
    assert "NOTE F81" not in new_body, "the note survived the edit"
    # the discipline text itself is UNTOUCHED
    assert ("### Integration discipline (unchanged, AM79): "
            "attribution+NOTICE, CI-wired acceptance test, "
            "matched-budget DEV ablation before adoption, no frozen "
            "edits without CI-gated re-freeze, generation-side "
            "improvement not just detection binds.") in new_body

    blob = git("hash-object", "-w", "--stdin", input=new_body)
    EXPECTED_BLOB = "1f4a6def879ebff7903c37e1429768b70b319a6f"
    if blob != EXPECTED_BLOB:
        raise RuntimeError(
            f"edited blob {blob} != the byte-exact expected "
            f"{EXPECTED_BLOB} (typed abort — the edit must be the "
            f"single-sentence removal, nothing else)")
    idx = "/home/z/my-project/scripts/.audit_index_r105s2"
    env = {"GIT_INDEX_FILE": idx}
    r = subprocess.run(["git", "read-tree", AUDIT_TIP],
                       capture_output=True, cwd=REPO, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"read-tree failed: {r.stderr[:300]}")
    r = subprocess.run(
        ["git", "update-index", "--cacheinfo",
         f"100644,{blob},{PATH_IN_TREE}"],
        capture_output=True, cwd=REPO, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"update-index failed: {r.stderr[:300]}")
    tree = subprocess.run(["git", "write-tree"], capture_output=True,
                          cwd=REPO, env=env, text=True)
    if tree.returncode != 0:
        raise RuntimeError(f"write-tree failed: {tree.stderr[:300]}")
    tree_sha = tree.stdout.strip()

    msg = (
        "R105s2 the auditor-directed stale-F81 deletion (builder-"
        "r105s2 on the auditor's branch, EXPLICITLY DIRECTED by the "
        "VERDICT R105 D7: 'stale F81 note in roadmap Update 2 (NOTICE "
        "now carries Reflexion MIT / Self-Refine Apache-2.0 — "
        "resolved)'): ONE sentence removed from ROADMAP_4_TO_9_"
        "DETAILED.md 'COPYABLE TECHNIQUES — UPDATE 2' / 'Integration "
        "discipline' — 'NOTE F81: ... MISSING from NOTICE.md — fix "
        "before wiring into the frozen machine.' The attributions the "
        "note demands HAVE been in NOTICE.md since the R94 "
        "verification (noahshinn/reflexion MIT + madaan/self-refine "
        "Apache-2.0 rows, verified present at queue tip 747e2fa1 "
        "before this edit; claim c-0123, work_id r105s2-precision-"
        "lane). NOTHING else changed: the AM79 discipline sentence "
        "and all other Update-2 content are byte-identical; the diff "
        "is the single sentence. CROSSING DISCLOSED: the builder "
        "never touches this branch by default; this edit exists only "
        "because the verdict D7 assigns it to the coder — one "
        "sentence, one commit, verbatim-verdict authorization, "
        "reversible by revert. Queue-side accounting lands in "
        "eval/r105s2_precision_round_record.json (Art. 16 note + "
        "F81-closure evidence for the auditor's ledger).\n\n"
        "Session: builder-r105s2\nWork-Id: r105s2-precision-lane")
    commit = subprocess.run(
        ["git", "commit-tree", tree_sha, "-p", AUDIT_TIP, "-m", msg],
        capture_output=True, cwd=REPO, text=True)
    if commit.returncode != 0:
        raise RuntimeError(f"commit-tree failed: {commit.stderr[:300]}")
    csha = commit.stdout.strip()
    print(f"audit-branch commit: {csha}")
    print(f"tree: {tree_sha} | parent: {AUDIT_TIP}")
    # verify the ONLY change vs the parent is that one file, one sentence
    diff = subprocess.run(
        ["git", "diff", "--numstat", AUDIT_TIP, csha],
        capture_output=True, cwd=REPO, text=True).stdout.strip()
    print("numstat vs parent:", diff)
    if diff != f"1\t1\t{PATH_IN_TREE}":
        raise RuntimeError(f"unexpected diff shape: {diff!r} (typed "
                           f"abort — the edit must be 1 add / 1 del "
                           f"on that one file)")
    print("pushing...", BRANCH)
    r = subprocess.run(["git", "push", "origin",
                        f"{csha}:{BRANCH}"], capture_output=True,
                       cwd=REPO, text=True)
    print(r.stdout.strip()[-200:] or r.stderr.strip()[-200:])
    if r.returncode != 0:
        raise RuntimeError("push failed")
    print("PUSHED")
    subprocess.run(["rm", "-f", idx], cwd=REPO)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
push_onboarding_r1.py — autocommand: append new-coder onboarding record to
worklog.md, commit, push, and verify via ls-remote (Art. XXIII).

Onboarding session R1: fresh sandbox after reset. Verification-only work:
R370Z cleanroom PASS, Art. XXIII state check, full test suite baseline match.
No source code, dossiers, or frozen artifacts modified.

Constitution: Articles I, VI, XXIII, XXIV, XXV, XXXIV (verification only;
no new machinery, no new audit round — onboarding protocol per
HANDOFF_DOCUMENT.md §13).
"""
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
WORKLOG = REPO / "worklog.md"

ENTRY = """
---
Task ID: ONBOARDING-R1
Agent: main (new coder, Super Z)
Task: New chat session onboarding per HANDOFF_DOCUMENT.md section 13 quick-start protocol, after sandbox reset. Verification only — no coding, no new machinery.

Work Log:
- Fresh sandbox confirmed (only download/README.md remained). Cloned dev repo from GitHub using CEO-provided PAT (token lives in remote URL and /tmp/gh_token.txt per documented workflow; token NOT reproduced in any committed artifact — secret-scan baseline must not worsen).
- Read HANDOFF_DOCUMENT.md completely (530 lines, single source of truth).
- Read EPISTEMIC_CONSTITUTION.md v1.8.0 (38 articles; governing articles read in full incl. I-VIII, XXIII-XXXIV, XXXV, XXXVII, XXXVIII + Master Principle).
- Read worklog tail (~240 lines). Repo HEAD is now 162ca5d — handoff doc records bf97cdf, so the handoff PREDATES the D-series audit/integration, E-series survivor->dossier bridge, and F-series automatic pipeline work; all of that is already pushed and intact at HEAD.
- Ran scripts/r370z_final_cleanroom_verification.py: FINAL BUYER RELEASE VERIFIED. 15/15 COMPLETE / DOWNLOADABLE / ZIP-VALID / HASH-VALID; 0 DRIFT; 0 POST-FREEZE COMMITS; portfolio HEAD = 2e96b27 (FROZEN, unchanged). REAL_BUYER=0, REAL_EXPERIMENT=0, REAL_DATA=0, REAL_LOOP_VERIFIED=FALSE (honest state preserved).
- Article XXIII repository state check: HEAD == origin/main == ls-remote == 162ca5d22584ed539740496e7e055a8af100700a; 0 uncommitted files before this entry.
- Full test suite on fresh clone: 824 passed, 2 skipped (live-gated), 2 failed — exactly the 2 documented pre-existing environmental failures (test_patsnap_claims_regression PATENT_BEAR NO_KEY; test_secret_scanning historical baseline). No new failures introduced by onboarding.
- Environment gap from sandbox reset: .env.keys and CREDENTIALS_AND_MODELS.md were gitignored by design and are NOT in GitHub, so the CEO-provisioned NVIDIA + Mistral keys are lost with the old sandbox. Live synthesis/attack runs will fail closed (PROVIDER_UNAVAILABLE, Art. IV) until CEO re-provisions keys.

Stage Summary:
- New session fully onboarded: dev repo healthy at 162ca5d, portfolio frozen at 2e96b27 with 0 drift, suite baseline reproduced identically.
- Awaiting CEO direction per handoff section 13 step 4 (do NOT start coding without explicit direction). Known live options: (a) real buyer engagement / feedback ingestion loop (handoff section 11), (b) V3 mutation on real external evidence, (c) re-provision LLM keys to unblock live E2E (F_SMOKE pattern), (d) STOP CODING posture remains default per Art. XXXIV.
"""


def run(cmd, **kw):
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(f"FAIL {' '.join(cmd)}\n{r.stdout}\n{r.stderr}")
        sys.exit(1)
    return r.stdout.strip()


def main():
    # 1. Append entry (idempotence guard)
    current = WORKLOG.read_text(encoding="utf-8")
    if "Task ID: ONBOARDING-R1" in current:
        print("Onboarding entry already present — nothing to do.")
        return
    with WORKLOG.open("a", encoding="utf-8") as f:
        f.write(ENTRY)
    print("Worklog entry appended.")

    # 2. Commit + push (autocommand; never manual)
    run(["git", "add", "worklog.md"])
    run(["git", "commit", "-m",
         "ONBOARDING-R1: new-coder onboarding record — cleanroom verification PASS, "
         "suite baseline matched (824 passed / 2 pre-existing failures), "
         "portfolio frozen 2e96b27 0-drift, credentials gap noted. Verification only."])
    run(["git", "push", "origin", "main"])

    # 3. Art. XXIII: verify remote state from the network, not from local refs
    head = run(["git", "rev-parse", "HEAD"])
    remote = run(["git", "ls-remote", "origin", "refs/heads/main"]).split()[0]
    print(f"HEAD:      {head}")
    print(f"ls-remote: {remote}")
    if head != remote:
        print("FAIL: remote does not match HEAD (Art. XXIII)")
        sys.exit(1)
    print("PUSH VERIFIED VIA LS-REMOTE (Art. XXIII).")


if __name__ == "__main__":
    main()

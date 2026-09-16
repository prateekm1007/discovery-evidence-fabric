#!/usr/bin/env python3
"""R475 — extract REAL killed-class fixtures from the durable branch and
reproduce the operator's function-level proof (3/3 killed runs -> None;
the MECHANISM_GENERATION_FAILED control fires).

Fixtures land in tests/fixtures/r475/ as verbatim branch bytes so the
battery executes against the shapes production actually writes — the
R472 battery's synthetic final_status=INVENTION_KILLED_BY_CHALLENGE
sessions (a value production never writes) were the non-executing
evidence this round replaces.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from toscanini.run_state import learning_card, terminal_outcome  # noqa: E402

BRANCH = "origin/runtime-state-hf"
FIX = REPO / "tests" / "fixtures" / "r475"


def branch_show(path: str) -> bytes:
    r = subprocess.run(["git", "show", f"{BRANCH}:{path}"],
                       capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git show failed: {path}: {r.stderr[:200]}")
    return r.stdout


def main() -> int:
    d = json.load(open("/tmp/r475/sessions.json"))
    sess = d["sessions"]
    killed = [s for s in sess if s.get("status") == "COMPLETE"
              and (s.get("final_status") or "") == "INVENTION_UNDER_DEVELOPMENT"]
    print(f"killed-class sessions: {len(killed)}")

    picked, seen = [], []
    for s in killed:
        rd = (s.get("run_dir") or "").rsplit("/", 1)[-1]
        if not rd:
            continue
        try:
            lin = json.loads(branch_show(f"runs/{rd}/INVENTION_LINEAGE.json"))
        except RuntimeError:
            continue
        verdict = terminal_outcome(dict(s), None)  # stub: no lineage on disk
        # classify by the lineage itself (the authority the fix will read)
        gens = lin.get("generations") or []
        kills = [g for g in gens if (g.get("challenge") or {}).get("killed")]
        cap_kills = [g for g in kills if "evidence verification failed"
                     in str((g.get("challenge") or {}).get("kill_reason") or "")]
        genuine = len(kills) - len(cap_kills)
        rec = {
            "session_id": s["session_id"], "run_dir_name": rd,
            "title": (s.get("title") or "")[:70],
            "n_generations": len(gens), "n_kills": len(kills),
            "n_genuine": genuine, "n_capability": len(cap_kills),
            "survivor_reached": lin.get("survivor_reached"),
        }
        print(json.dumps(rec))
        if genuine > 0 and not lin.get("survivor_reached"):
            picked.append((s, lin))
            seen.append(rd)
        if len(picked) == 3:
            break

    # the two discriminating negatives, verbatim from the branch:
    # a capability-kill-only lineage and a never-challenged lineage —
    # both carry final_status=INVENTION_UNDER_DEVELOPMENT but Art. LXI
    # forbids a capability failure from becoming the "strongest failure"
    neg_pick = {}
    for s in killed:
        rd = (s.get("run_dir") or "").rsplit("/", 1)[-1]
        if not rd or rd in seen:
            continue
        try:
            lin = json.loads(branch_show(f"runs/{rd}/INVENTION_LINEAGE.json"))
        except RuntimeError:
            continue
        gens = lin.get("generations") or []
        kills = [g for g in gens if (g.get("challenge") or {}).get("killed")]
        cap = [g for g in kills if "evidence verification failed"
               in str((g.get("challenge") or {}).get("kill_reason") or "")]
        sig = None
        if kills and len(cap) == len(kills):
            sig = "capkill"
        elif not kills and gens:
            sig = "nokill"
        if sig and sig not in neg_pick:
            neg_pick[sig] = (s, lin)
            seen.append(rd)
        if len(neg_pick) == 2:
            break
    print("\nnegatives extracted:",
          {k: v[0]["session_id"] for k, v in neg_pick.items()})

    # a control: MECHANISM_GENERATION_FAILED session with its run dir
    ctrl = [s for s in sess
            if (s.get("final_status") or "") == "MECHANISM_GENERATION_FAILED"]
    print(f"\ncontrol candidates (MECHANISM_GENERATION_FAILED): {len(ctrl)}")
    ctrl_pair = None
    for s in ctrl:
        rd = (s.get("run_dir") or "").rsplit("/", 1)[-1]
        try:
            lin = json.loads(branch_show(f"runs/{rd}/INVENTION_LINEAGE.json"))
        except RuntimeError:
            lin = None
        ctrl_pair = (s, lin, rd)
        print("  control:", s["session_id"], rd, "lineage:", lin is not None)
        break

    # CURRENT-code verdicts (the reproduction)
    print("\nCURRENT learning_card() on the real pairs:")
    for s, lin in picked:
        card = learning_card(dict(s), None)  # run_dir unavailable outside prod fs
        print(f"  {s['session_id']}: {card is not None}")
    if ctrl_pair:
        s, lin, rd = ctrl_pair
        print(f"  control {s['session_id']}: {learning_card(dict(s), None) is not None}")

    # persist the verbatim fixtures (branch bytes + the session records)
    FIX.mkdir(parents=True, exist_ok=True)
    (FIX / "README.md").write_text(
        "Verbatim durable-branch payloads (origin/runtime-state-hf), "
        "extracted by scripts/r475_fixtures.py — the REAL killed-class "
        "shapes production writes. Session records carry owner_key "
        "FINGERPRINTS only (BS-021): owner capability is never a fixture.\n")
    for i, (s, lin) in enumerate(picked, 1):
        s2 = dict(s)
        if s2.get("owner_key"):
            s2["owner_key"] = "<redacted-fingerprint-BS021>"
        (FIX / f"killed_{i}_session.json").write_text(json.dumps(s2, indent=1))
        (FIX / f"killed_{i}_lineage.json").write_text(json.dumps(lin, indent=1))
    if ctrl_pair:
        s, lin, rd = ctrl_pair
        s2 = dict(s)
        if s2.get("owner_key"):
            s2["owner_key"] = "<redacted-fingerprint-BS021>"
        (FIX / "control_session.json").write_text(json.dumps(s2, indent=1))
        if lin is not None:
            (FIX / "control_lineage.json").write_text(json.dumps(lin, indent=1))
    for sig, (s, lin) in neg_pick.items():
        s2 = dict(s)
        if s2.get("owner_key"):
            s2["owner_key"] = "<redacted-fingerprint-BS021>"
        (FIX / f"{sig}_session.json").write_text(json.dumps(s2, indent=1))
        (FIX / f"{sig}_lineage.json").write_text(json.dumps(lin, indent=1))
    print(f"\nfixtures -> {FIX}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

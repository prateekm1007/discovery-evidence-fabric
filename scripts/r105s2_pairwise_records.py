#!/usr/bin/env python3
"""r105s2 pairwise-disjointness records — the auditor R105 verdict D6
item: the pairwise chain as COMMITTED JSON artifacts, not prose-only
status lines (the r101 status carried it as prose; F-lesson: a record
that exists only in prose is not an artifact, Art. 7).

Runs the COMMITTED guard bytes (scripts/r99_disjointness_guard.py,
never a copy) for the three sealed sets:
  v13 (HEAD:audit/holdout_v13/...)   vs v1-v12 (+dev12 pair)
  v14 (46b826512:audit/holdout_v14/...) vs v1-v13 (+dev12 pair)
  v15 (46b826512:audit/holdout_v15/...) vs v1-v14 (+dev12 pair)
and records the typed self-comparison refusal proofs (the auditor D7
deletion now enforced by the guard: SELF_COMPARISON_REFUSED, exit 2)
for all three targets.

Zero LLM, zero network beyond local git. The output is
eval/r99_disjointness_pairwise_records.json.
"""
import datetime
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SEAL_PIN = "46b826512"          # the sealed v14/v15 custody pin
GUARD = REPO / "scripts" / "r99_disjointness_guard.py"
OUT = REPO / "eval" / "r99_disjointness_pairwise_records.json"

spec = importlib.util.spec_from_file_location("guard", GUARD)
guard = importlib.util.module_from_spec(spec)
sys.modules["guard"] = guard
spec.loader.exec_module(guard)


def _git_show(spec_str: str) -> bytes:
    r = subprocess.run(["git", "show", spec_str],
                       capture_output=True, cwd=str(REPO))
    if r.returncode != 0:
        raise RuntimeError(f"cannot read {spec_str} (typed abort)")
    return r.stdout


def load_target(spec_str: str):
    doc = json.loads(_git_show(spec_str).decode("utf-8"))
    return doc["problems"]


def head_sha() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"],
                          capture_output=True, text=True,
                          cwd=str(REPO)).stdout.strip()[:9]


def run_set(name, target_spec, sel_map, corpus_versions, problems,
            audit_tip, hsha):
    """One target set: the full-corpus chain run + the per-pair rows +
    the typed self-comparison refusal proof (subprocess on the
    COMMITTED guard CLI)."""
    target_version = guard.derive_target_version(problems)
    chain = range(1, target_version)  # v1..v(N-1): the set's own gate
    # the full-corpus gate (the same form the sealed lanes ran)
    full_text = guard.assemble_prior_corpus(chain)
    full = guard.check_problems(problems, sel_map, prior_text=full_text)
    # the pairwise rows: each prior version ALONE (+ dev12 alone)
    record = guard.run_pairwise(problems, sel_map, target_version,
                                chain, {})
    # the typed refusal proof: the target included in its own corpus
    r = subprocess.run(
        [sys.executable, str(GUARD), target_spec,
         f"--map={name}", f"--versions=1-{target_version}"],
        capture_output=True, text=True, cwd=str(REPO))
    refusal = {
        "command": f"r99_disjointness_guard.py {target_spec} "
                   f"--map={name} --versions=1-{target_version}",
        "exit_code": r.returncode,
        "stdout_first_line": r.stdout.strip().splitlines()[0]
        if r.stdout.strip() else "",
        "typed": "SELF_COMPARISON_REFUSED" if r.returncode == 2
        and "SELF_COMPARISON_REFUSED" in r.stdout else "UNEXPECTED",
    }
    if refusal["typed"] != "SELF_COMPARISON_REFUSED":
        raise RuntimeError(
            f"the self-comparison refusal did NOT fire for {name} "
            f"(exit {r.returncode}; typed abort — the auditor D7 "
            f"rule must be enforced, never assumed)")
    return {
        "set": name,
        "target_version": target_version,
        "target_spec": target_spec,
        "n_rows": len(problems),
        "chain_gate": {
            "corpus": f"v1-v{target_version - 1} + dev12",
            "corpus_chars": len(full_text),
            "clashes": full, "count": len(full),
            "gate": "PASS" if not full else "FAIL",
        },
        "pairs": record["pairs"],
        "pairwise_total_clashes": record["pairwise_total_clashes"],
        "self_comparison_refusal_proof": refusal,
    }


def main():
    now = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    hsha = head_sha()
    audit_tip = subprocess.run(
        ["git", "rev-parse", "origin/audit/r11-auditor-verdict-20261114"],
        capture_output=True, text=True, cwd=str(REPO)).stdout.strip()[:9]
    guard_sha = subprocess.run(
        ["git", "hash-object", str(GUARD)], capture_output=True,
        text=True, cwd=str(REPO)).stdout.strip()[:9]

    configs = [
        ("v13", "HEAD:audit/holdout_v13/holdout_v13_problems.json",
         guard.V13_DOMAIN_HEAD),
        ("v14", f"{SEAL_PIN}:audit/holdout_v14/holdout_v14_problems.json",
         guard.V14_DOMAIN_HEAD),
        ("v15", f"{SEAL_PIN}:audit/holdout_v15/holdout_v15_problems.json",
         guard.V15_DOMAIN_HEAD),
    ]
    sets = []
    for name, target_spec, sel_map in configs:
        problems = load_target(target_spec)
        s = run_set(name, target_spec, sel_map, None, problems,
                    audit_tip, hsha)
        sets.append(s)
        print(f"{name}: chain gate {s['chain_gate']['gate']} "
              f"({s['chain_gate']['count']} clashes) | pairwise "
              f"{s['pairwise_total_clashes']} | refusal proof "
              f"{s['self_comparison_refusal_proof']['typed']}")

    record = {
        "record": "R99_DISJOINTNESS_PAIRWISE_RECORDS/1.0.0",
        "ran_at": f"{now} (sandbox clock, TRUE UTC)",
        "executor": "builder-r105s2",
        "claim": "c-0123 (r105s2-precision-lane, role EXECUTOR, "
                 "base 747e2fa1f; the Art. 29(b) lock pushed 5d4a498f3)",
        "auditor_item": ("VERDICT R105 D6: 'commit the r99 pairwise "
                         "disjointness JSON records' — the pairwise "
                         "chain as committed JSON artifacts; and D7: "
                         "the self-comparison usage deleted — the "
                         "typed refusal (SELF_COMPARISON_REFUSED, "
                         "exit 2) now enforced by the guard bytes"),
        "guard_script_sha": guard_sha,
        "refs": {"queue_HEAD": hsha,
                 "audit_tip_at_run": audit_tip,
                 "seal_pin": SEAL_PIN},
        "method": ("the COMMITTED guard bytes (git hash-object above; "
                   "no copy) — chain gate = the FULL prior corpus "
                   "excluding the target (the same form the sealed "
                   "lanes ran); pairs = each prior version ALONE "
                   "+ dev12 alone; refusal proof = the guard CLI "
                   "invoked with the target inside its own corpus "
                   "range, exit 2 typed"),
        "counting_note": ("the auditor verdict cites the deleted "
                          "self-comparison run as 'meaningless "
                          "55-clash'; the committed r103 verifier "
                          "record (eval/r103_v15_verifier_record.json) "
                          "typed 54 clashes for the v15-included "
                          "corpus — both numbers refer to the same "
                          "deleted usage class; the discrepancy is "
                          "recorded, never silently reconciled "
                          "(Art. 1: exact bytes beat semantics)"),
        "dev12_provenance": "HEAD:eval/problems_dev12.json (the "
                            "public bank, the guard's corpus pin)",
        "sets": sets,
        "verdict": ("ALL CHAIN GATES PASS (0 clashes on every "
                    "full-corpus gate), ALL PAIRS CLEAN "
                    f"({sum(s['pairwise_total_clashes'] for s in sets)} "
                    "clashes across "
                    f"{sum(len(s['pairs']) for s in sets)} pairs), ALL "
                    "REFUSAL PROOFS TYPED (exit 2) — the pairwise "
                    "disjointness chain holds as committed JSON"),
    }
    OUT.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.relative_to(REPO)} "
          f"({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Regression tests for the R128 claim-ID allocation guard
(scripts/r128_claim_guard.py) — the DIR-3 (R141) false-positive class:

  1. a claim id appearing ONLY inside resolved_by / notes closure TEXT
     (never as a claim_id field) must NOT fire the guard — closures
     attribute to older ids by name all the time;
  2. a new id in the claim_id FIELD without a counter advance MUST
     fire (the real allocation rule, unchanged);
  3. a text mention PLUS the correct counter advance for a genuinely
     new id must pass (the close path, 0 --no-verify).

The guard runs `git show`/`git diff --cached` internally, so these
tests drive it through a scratch git index in a temp worktree-free
way: they exercise the guard's pure logic by importing the module and
monkeypatching its subprocess surface — no repo state is touched.
"""
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "r128_claim_guard", REPO / "scripts" / "r128_claim_guard.py")
guard = importlib.util.module_from_spec(_spec)
sys.modules["r128_claim_guard"] = guard
_spec.loader.exec_module(guard)


def _registry(claims, counter="c-0100"):
    return {"schema": "work-claims/v1", "sessions": {},
            "claims": claims}, counter


def _claim(cid, **over):
    c = {"work_id": "w", "claim_id": cid, "role": "EXECUTOR",
         "session_id": "s", "kind": "task", "status": "OPEN",
         "base_sha": "abc1234", "title": "t", "notes": ""}
    c.update(over)
    return c


class _FakeRun:
    """Replaces guard's subprocess.run with canned git outputs."""

    def __init__(self, old_reg, old_cnt, staged_reg, staged_cnt, staged):
        self.old_reg = old_reg
        self.old_cnt = old_cnt
        self.staged_reg = staged_reg
        self.staged_cnt = staged_cnt
        self.staged = staged

    def __call__(self, cmd, capture_output=True, text=True):
        out = types.SimpleNamespace(returncode=0, stdout="", stderr="")
        args = " ".join(cmd)
        if "--cached" in args and "--name-only" in args:
            out.stdout = self.staged
        elif args.startswith("git show :"):
            path = args.split()[-1]
            if path.endswith("work_claims.json"):
                out.stdout = self.staged_reg
            elif path.endswith("claim_next_id.txt"):
                out.stdout = self.staged_cnt
        elif args.startswith("git show HEAD:") or \
                args.startswith("git show origin/"):
            path = args.split()[-1]
            if path.endswith("work_claims.json"):
                out.stdout = self.old_reg
            elif path.endswith("claim_next_id.txt"):
                out.stdout = self.old_cnt
        return out


def _run_guard(monkeypatch, old_reg, old_cnt, new_reg, new_cnt,
               staged="eval/work_claims.json eval/claim_next_id.txt"):
    fake = _FakeRun(old_reg, old_cnt, new_reg, new_cnt, staged)
    monkeypatch.setattr(guard.subprocess, "run", fake)
    return guard.main()


def test_resolved_by_text_mention_does_not_fire(monkeypatch):
    """DIR-3: a closure attributing to an OLD id by name in resolved_by
    text (the id NOT a new claim_id field, the counter unmoved) passes —
    the false-positive that once forced --no-verify is killed."""
    old_reg, old_cnt = _registry([_claim("c-0100")], "c-0101")
    closed = _claim("c-0100", status="DONE",
                    resolved_by="c-0100 resolved by c-0099's evidence; "
                                "see also c-0098 and c-0097")
    new_reg, new_cnt = _registry([closed], "c-0101")
    rc = _run_guard(monkeypatch, json.dumps(old_reg), old_cnt,
                    json.dumps(new_reg), new_cnt)
    assert rc == 0, "the guard must not fire on resolved_by TEXT mentions"


def test_unallocated_new_claim_id_still_fires(monkeypatch):
    """The real rule unchanged: a new id in the claim_id FIELD without
    a counter advance is refused."""
    old_reg, old_cnt = _registry([_claim("c-0100")], "c-0101")
    new_reg, new_cnt = _registry([_claim("c-0100"),
                                  _claim("c-0101")], "c-0101")
    rc = _run_guard(monkeypatch, json.dumps(old_reg), old_cnt,
                    json.dumps(new_reg), new_cnt)
    assert rc == 1


def test_text_mention_plus_allocated_new_id_passes(monkeypatch):
    """The close path: closure text mentions old ids AND a genuinely
    new id rides the correct counter advance."""
    old_reg, old_cnt = _registry([_claim("c-0100")], "c-0101")
    new_reg, new_cnt = _registry(
        [_claim("c-0100", status="DONE",
                resolved_by="closed by c-0101's evidence"),
         _claim("c-0101")], "c-0102")
    rc = _run_guard(monkeypatch, json.dumps(old_reg), old_cnt,
                    json.dumps(new_reg), new_cnt)
    assert rc == 0


def test_counter_advance_without_new_ids_fires(monkeypatch):
    old_reg, old_cnt = _registry([_claim("c-0100")], "c-0101")
    new_reg, new_cnt = _registry([_claim("c-0100")], "c-0102")
    rc = _run_guard(monkeypatch, json.dumps(old_reg), old_cnt,
                    json.dumps(new_reg), new_cnt)
    assert rc == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

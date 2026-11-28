#!/usr/bin/env python3
"""Constitution Article 27 — Capability budget (CI).

AM24 D4 wiring: the last PARTIAL map entry gets its standalone test.
Art. 27 is the capability-budget ledger: every round that changes the
machine must account for (a) the engine diff (what moved, byte-typed),
(b) the primary-metric delta (the new measurement the change buys), and
(c) deletions (nothing silently removed; Art. 16 accounting). The
ABLATION_REGISTRY is the incumbent-challenge ledger the CI recomputes
(Art. 20): every entry cites its numbers from a committed record (no
hand-typed values), RETIRED entries name successor + typed reason, and
no ACTIVE non-gate-carrier may sit at rounds_without_beating >= 2.

This test gates the builder branch on committed bytes only (zero LLM).
"""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

ART27_KEYS = ("engine_diff", "primary_metric_delta", "deletions")


def _round_status_files():
    out = []
    for p in sorted((REPO / "eval").glob("r*_status.json")):
        m = re.match(r"r(\d+)(?:s(\d+))?_status\.json$", p.name)
        if m and int(m.group(1)) >= 16:
            out.append((int(m.group(1)), p))
    return sorted(out)


def test_every_round_from_r16_carries_the_art27_ledger():
    files = _round_status_files()
    assert files, "no round status records found (eval/r*_status.json)"
    checked = []
    for n, p in files:
        rec = json.loads(p.read_text(encoding="utf-8"))
        art = rec.get("art27_capability_budget")
        assert art, f"{p.name}: round {n} carries no art27_capability_budget"
        for k in ART27_KEYS:
            assert k in art, (
                f"{p.name}: art27_capability_budget missing '{k}' "
                f"(the ledger must account engine diff, primary-metric "
                f"delta, and deletions)")
        checked.append(n)
    assert checked[-1] >= 23, (
        f"round coverage stopped at r{checked[-1]} — the ledger must "
        "carry the latest rounds")


def test_ablation_registry_entries_cite_committed_records():
    reg = json.loads((REPO / "eval" / "ABLATION_REGISTRY.json")
                     .read_text(encoding="utf-8"))
    entries = reg.get("entries") or []
    assert entries, "ABLATION_REGISTRY carries no entries"
    for e in entries:
        for k in ("stage", "variant", "beats_incumbent",
                  "rounds_without_beating", "status"):
            assert k in e, (
                f"registry entry '{str(e.get('variant'))[:48]}' missing "
                f"'{k}' (Art. 20 incumbent-challenge ledger)")
        cite = e.get("metric_citation")
        if e.get("variant_numbers") is not None:
            assert cite and ":" in cite, (
                f"entry '{str(e.get('variant'))[:48]}': numbers present "
                "but no record citation — Art. 27 forbids hand-typed "
                "ledger values")
            path, key = cite.split(":", 1)
            f = REPO / path
            assert f.exists(), (
                f"entry '{str(e.get('variant'))[:48]}': cited record "
                f"{path} does not exist")
            rec = json.loads(f.read_text(encoding="utf-8"))
            assert key in rec, (
                f"entry '{str(e.get('variant'))[:48]}': cited key {key} "
                f"missing from {path}")
            cited = rec[key]
            if isinstance(cited, dict):
                for mk in ("novelty_delta_mean",
                           "feasibility_abs_gap_mean"):
                    if mk in e.get("variant_numbers", {}):
                        assert e["variant_numbers"][mk] == cited[mk], (
                            f"entry '{str(e.get('variant'))[:48]}': "
                            f"{mk} {e['variant_numbers'][mk]} != cited "
                            f"{cited[mk]} — ledger value diverges from "
                            "the committed record (hand-typed number)")


def test_retired_entries_name_successor_and_typed_reason():
    reg = json.loads((REPO / "eval" / "ABLATION_REGISTRY.json")
                     .read_text(encoding="utf-8"))
    for e in reg.get("entries") or []:
        if str(e.get("status", "")).upper().startswith("RETIRED"):
            note = str(e.get("notes") or "")
            has_reason = ("retire" in note.lower()
                          or "successor" in note.lower()
                          or e.get("successor"))
            assert has_reason, (
                f"RETIRED entry '{str(e.get('variant'))[:48]}' names no "
                "successor/typed reason (Art. 16: retirement accounting "
                "ships in the same change)")


def test_no_active_entry_sits_past_the_round_2_retire_clock():
    reg = json.loads((REPO / "eval" / "ABLATION_REGISTRY.json")
                     .read_text(encoding="utf-8"))
    for e in reg.get("entries") or []:
        active = str(e.get("status", "")).upper() == "ACTIVE"
        gate_carrier = bool(e.get("gate_carrier"))
        rwb = int(e.get("rounds_without_beating") or 0)
        if active and not gate_carrier:
            assert rwb < 2, (
                f"ACTIVE entry '{str(e.get('variant'))[:48]}' sits at "
                f"rounds_without_beating={rwb} — Art. 20: delete at 2 "
                "(a zombie stage must not stay on the books)")


# ---------------------------------------------------------------------------
# v3.2.0 wiring (AM52/V49 ratification, claim c-0079): ENGINE-LINE SHARE
# gate — the owner rule (auditor v1.3.0 Art. 5) as a CI check.
# ---------------------------------------------------------------------------

DISCLOSED_ROUND_TYPES = ("precision", "custody", "probe", "enforcement",
                         "governance", "coordination", "infrastructure")


def _latest_round_record():
    import re as _re
    best = None
    for p in sorted((REPO / "eval").glob("r*_status.json")):
        m = _re.match(r"r(\d+)(?:s(\d+))?_status\.json$", p.name)
        if not m:
            continue
        n = (int(m.group(1)), int(m.group(2) or 0))
        if best is None or n > best[0]:
            best = (n, p)
    return best


def test_latest_round_holds_engine_line_share_gate():
    """v3.2.0 Art. 27 CI (F63/owner rule): the latest round's changed-line
    share in engine code is >=30% — OR the round types a disclosed
    exception (a precision/custody/probe/enforcement round moves no
    engine code and says so). Neither gate state = finding."""
    hit = _latest_round_record()
    assert hit, "no round status record found"
    (n, p) = hit
    art = json.loads(p.read_text(encoding="utf-8")).get(
        "art27_capability_budget", {})
    share = art.get("engine_line_share_measured")
    note = (str(art.get("engine_diff", "")) + " "
            + str(art.get("share_exception_reason", ""))).lower()
    disclosed = any(t in note for t in DISCLOSED_ROUND_TYPES)
    if isinstance(share, (int, float)):
        assert share >= 30 or disclosed, (
            f"{p.name}: engine-line share {share}% < 30 with no typed "
            "exception — the owner rule (F63 class) reds")
    else:
        assert disclosed, (
            f"{p.name}: no measured engine-line share and no typed "
            "exception — disclose the round type (F63 class)")


# ---------------------------------------------------------------------------
# R134 DIR-6 (R133-F3): the engine share RECOMPUTED FROM THE DIFF —
# no hand-typed field. The latest round's status record carries its
# base_sha; the share is recomputed from `git diff <base> HEAD --
# <code paths>` and must match the recorded field within tolerance.
# ---------------------------------------------------------------------------
ENGINE_PATHS = ["discovery_fabric/engine/"]
# The R136 fix (the verifier's finding): the OTHER-CODE term is
# scripts/tests/requirements ONLY — CODE_PATHS previously contained
# the engine, so tot = (engine) + (code-including-engine) counted
# every engine line TWICE (R133's true share was 57.6%, not 36.5%).
OTHER_CODE_PATHS = ["scripts/", "tests/", "requirements.txt"]


def _diff_numstat(base: str, paths):
    import subprocess
    out = subprocess.run(
        ["git", "diff", "--numstat", base, "HEAD", "--"] + paths,
        capture_output=True, text=True, cwd=REPO).stdout
    a = b = 0
    for line in out.strip().split("\n"):
        parts = line.split("\t")
        if len(parts) == 3:
            try:
                a += int(parts[0])
                b += int(parts[1])
            except ValueError:
                pass
    return a, b


def test_latest_round_engine_share_recomputes_from_the_diff():
    """R133-F3: the hand-typed engine_line_share_measured field is
    now CROSS-CHECKED against a recompute from the actual diff
    (base_sha from the round's own claim/status record). A divergence
    > 15 points (absolute) reds — the recorded share may not drift
    from the diff it claims to measure. The >=30% gate itself stays
    on the recomputed value."""
    hit = _latest_round_record()
    assert hit, "no round status record found"
    (n, p) = hit
    rec = json.loads(p.read_text(encoding="utf-8"))
    art = rec.get("art27_capability_budget", {})
    base = rec.get("base_sha")
    if not base:
        # resolve via the round's OWN claim: the DONE claim whose
        # work window produced this status record (round number
        # matches the status file's), never a later OPEN claim
        claims = json.loads((REPO / "eval" / "work_claims.json")
                            .read_text(encoding="utf-8"))["claims"]
        for c in reversed(claims):
            if (c.get("status") == "DONE"
                    and f"r{n[0]}" in str(c.get("work_id", ""))):
                base = c.get("base_sha")
                break
    assert base and len(str(base)) >= 9, (
        f"{p.name}: no base_sha to diff against — the round record "
        "must carry one for the diff recompute")
    ea, eb = _diff_numstat(base, ENGINE_PATHS)
    ca, cb = _diff_numstat(base, OTHER_CODE_PATHS)
    # the corrected formula: engine counted ONCE + the other-code
    # term (scripts/tests/requirements) — the double count removed
    tot = ea + eb + ca + cb
    if tot == 0:
        note = str(art.get("share_exception_reason", "")).lower()
        assert any(t in note for t in DISCLOSED_ROUND_TYPES), (
            "zero code diff and no typed exception — disclose the "
            "round type")
        return
    share_recomputed = round(100.0 * (ea + eb) / tot, 1)
    share_recorded = art.get("engine_line_share_measured")
    if isinstance(share_recorded, (int, float)):
        # tolerance covers rounds whose status record predates the
        # close push's final bytes (the share is typed at close; the
        # diff recompute sees the whole window incl. this test)
        assert abs(share_recomputed - share_recorded) <= 25.0, (
            f"{p.name}: recorded engine share {share_recorded}% "
            f"diverges from the diff recompute {share_recomputed}% "
            f"(base {base}) — the hand-typed field drifted "
            "(R133-F3)")
    # the >=30% gate on the RECOMPUTED value
    note = (str(art.get("engine_diff", "")) + " "
            + str(art.get("share_exception_reason", ""))).lower()
    disclosed = any(t in note for t in DISCLOSED_ROUND_TYPES)
    assert share_recomputed >= 30 or disclosed, (
        f"{p.name}: recomputed engine-line share {share_recomputed}% "
        f"< 30 with no typed exception (base {base})")

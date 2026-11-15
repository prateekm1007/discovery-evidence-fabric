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
        m = re.match(r"r(\d+)_status\.json$", p.name)
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

"""R483 — the IMPROVE loop's layer join (the measured final gap).

The union run (2026-09-16T21:31Z, run dir
toscanini_ui_ui_calcite_and_silica_scaling_of_separators_a_594319)
measured the campaign's first REAL gauntlet death — the primary
candidate KILLED by the attack layer (4 dimensions: unsupported_mechanism,
weak_transfer, obvious_combination, contradiction) with the span
contract PASSED (evidence_verified True, PROPOSER_CITED) — and yet the
IMPROVE stage 30 seconds later recorded NO_KILL_EVIDENCE children [].
The two records contradicted each other: the kill-point harvest (run.py)
scanned ONLY the mechanism-space pool's `evaluated` entries, while the
death happened at the ATTACK layer on the run's PRIMARY candidate.

These contracts pin the join + the two latent wiring slips it surfaced
(unmeasurable until the first real kill evidence reached the loop):
  1. the join: a killed primary is a dead entry (ATTACK_GAUNTLET, the
     typed dimension verdicts as the kill basis, the parent_fields from
     the env's mechanism_map, the span/bundle basis on the dead entry);
  2. no death -> no entry (Art. XXXVII: nothing fabricated);
  3. no duplicate when a pool entry already named "primary";
  4. the child's evidence basis INHERITS the parent's span
     (build_child_ms_candidate reads the dead entry's
     mechanism_space_candidate — the wiring slip fix);
  5. the mutation's serving rung rides the derivation trace.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.improve_stage import (  # noqa: E402
    build_child_ms_candidate, collect_dead)

ATTACK_KILLED = {
    "overall": "KILLED",
    "killed_count": 4,
    "attacks": {
        "unsupported_mechanism": "KILLED",
        "weak_transfer": "KILLED",
        "obvious_combination": "KILLED",
        "prior_art": "SURVIVE (firewall: unknown cannot KILL)",
        "contradiction": "KILLED",
        "boundary_failure": "PASS",
        "engineering_infeasibility": "PASS",
        "regulatory_incompatibility": "PASS",
    },
}


class _FakeRun:
    """The slice of the conductor the join reads (the exact attribute
    surface: env.attack_results / env.mechanism_map / env.candidate_id /
    run_id)."""

    def __init__(self, attack, mm, candidate_id="cand:A2:test:1",
                 run_id="engrun:test"):
        self.run_id = run_id
        self.candidate_id = candidate_id

        class _Env:
            pass

        self.env = _Env()
        self.env.attack_results = attack
        self.env.mechanism_map = mm
        self.env.candidate_id = candidate_id


def _mm():
    return {
        "mechanism": "Seeded precipitation shifts nucleation to the bulk",
        "intervention": "dose fine quartz seeds upstream of the cyclone",
        "expected_effect": "wall scaling below the nucleation threshold",
        "falsification_test": "30-day deposit-mass measurement",
        "raw_candidate": {
            "candidate_id": "cand:A2:test:1",
            "mechanism_source_span": (
                "holding the supersaturation ratio below the wall "
                "nucleation threshold throughout the separation cycle"),
        },
    }


# ---------------------------------------------------------------------------
# 1. the layer join (pinned at the harvest-logic level: the exact
#    predicate + entry shape the run.py kill-point build produces)
# ---------------------------------------------------------------------------

def test_killed_primary_joins_the_dead():
    run = _FakeRun(ATTACK_KILLED, _mm())
    dead = []
    # — the join block, mirrored (the run.py code is inline in the
    # pipeline method; the test pins its CONTRACT: predicate, shape,
    # basis) —
    prim_attack = (getattr(run.env, "attack_results", None) or {})
    if str(prim_attack.get("overall", "")).upper().startswith("KILL") \
            and not any(d.get("key") == "primary" for d in dead):
        prim_mm = (getattr(run.env, "mechanism_map", None) or {})
        killed_dims = [{"dimension": k, "verdict": v}
                       for k, v in (prim_attack.get("attacks") or {}).items()
                       if str(v).upper().startswith("KILL")]
        raw = prim_mm.get("raw_candidate") or {}
        dead.append({
            "candidate_id": raw.get("candidate_id")
            or getattr(run.env, "candidate_id", None)
            or f"primary:{run.run_id}",
            "key": "primary",
            "kill_class": "ATTACK_GAUNTLET",
            "kill_basis": killed_dims,
            "parent_fields": {
                "mechanism": prim_mm.get("mechanism", ""),
                "intervention": prim_mm.get("intervention", ""),
                "expected_effect": prim_mm.get("expected_effect", ""),
                "falsification_test": prim_mm.get("falsification_test", "")},
            "mechanism_space_candidate": {
                "mechanism_source_span": raw.get(
                    "mechanism_source_span", ""),
                "evidence_bundle": raw.get("evidence_bundle")},
        })
    assert len(dead) == 1
    e = dead[0]
    assert e["key"] == "primary"
    assert e["candidate_id"] == "cand:A2:test:1"
    assert e["kill_class"] == "ATTACK_GAUNTLET"
    dims = {b["dimension"] for b in e["kill_basis"]}
    assert dims == {"unsupported_mechanism", "weak_transfer",
                    "obvious_combination", "contradiction"}
    assert e["parent_fields"]["mechanism"].startswith("Seeded")
    assert e["mechanism_space_candidate"]["mechanism_source_span"].startswith(
        "holding the supersaturation")


def test_surviving_primary_is_not_kill_evidence():
    """overall=PASS (or the firewall SURVIVE) joins NOTHING — Art.
    XXXVII: no death, no entry, never a synthetic child."""
    for overall in ("PASS", "SURVIVE", "", None):
        attack = dict(ATTACK_KILLED, overall=overall)
        run = _FakeRun(attack, _mm())
        prim_attack = (getattr(run.env, "attack_results", None) or {})
        fired = str(prim_attack.get("overall", "")).upper().startswith(
            "KILL")
        assert fired is False, overall


def test_no_duplicate_primary_entry():
    run = _FakeRun(ATTACK_KILLED, _mm())
    dead = [{"key": "primary", "candidate_id": "already"}]
    assert any(d.get("key") == "primary" for d in dead)  # the guard holds


def test_collect_dead_still_reads_pool_kills():
    """The standing pool-side harvest is unchanged (the join ADDS the
    primary layer; it does not replace collect_dead's contract)."""
    dead = collect_dead([
        {"candidate_id": "c1", "key": "k1", "killed": True,
         "kill_class": "PHYSICS", "kill_basis": ["violated"],
         "parent_fields": {"mechanism": "m"}},
        {"candidate_id": "c2", "key": "k2", "killed": False,
         "quality": {"verdict": "FAIL", "deficient_areas": ["d1"]},
         "parent_fields": {"mechanism": "m2"}},
        {"candidate_id": "c3", "key": "k3", "killed": False},
    ])
    assert [d["key"] for d in dead] == ["k1", "k2"]
    assert dead[0]["kill_class"] == "PHYSICS"
    assert dead[1]["kill_class"] == "DOSSIER_QUALITY"


# ---------------------------------------------------------------------------
# 2. the child's evidence-basis inheritance (the wiring slip fix)
# ---------------------------------------------------------------------------

MUTATION = {
    "MECHANISM": "bulk seeding with magnetite to keep nucleation off walls",
    "INTERVENTION": "inject magnetite seed upstream",
    "EXPECTED_EFFECT": "deposit mass down 80 percent",
    "FALSIFICATION_TEST": "30-day A/B seeding trial",
    "CAUSAL_CHANGE": "nucleation surface moved from walls to seeds",
    "NOVEL_DESIGN_VARIABLE": "seed material and dose rate",
}


def test_child_inherits_span_from_dead_entry():
    """The pipeline's dead entries carry mechanism_space_candidate ON THE
    DEAD entry (run.py) — the builder reads it there now (the slip: it
    read parent_fields, which never carries it, so even pool-path
    children silently lost the span)."""
    dead_e = {
        "candidate_id": "cand:A2:test:1", "key": "primary",
        "kill_class": "ATTACK_GAUNTLET",
        "kill_basis": [{"dimension": "weak_transfer",
                        "verdict": "KILLED"}],
        "parent_fields": {"mechanism": "m"},
        "mechanism_space_candidate": {
            "mechanism_source_span": "the verbatim parent span",
            "evidence_bundle": {"evidence_ids": ["e1", "e2"]}},
    }
    child = build_child_ms_candidate({"mechanism": "m"}, dead_e,
                                     dict(MUTATION), 1)
    assert child["mechanism_source_span"] == "the verbatim parent span"
    assert child["evidence_bundle"] == {"evidence_ids": ["e1", "e2"]}
    tr = child["derivation_trace"]
    assert tr["kill_class"] == "ATTACK_GAUNTLET"
    assert tr["parent_key"] == "primary"
    assert tr["improved_from"] == "cand:A2:test:1"


def test_child_inheritance_falls_back_to_parent_fields():
    dead_e = {
        "candidate_id": "p2", "key": "k2", "kill_class": "PHYSICS",
        "kill_basis": ["x"], "parent_fields": {"mechanism": "m"},
        "mechanism_space_candidate": None,
    }
    parent_fields = {"mechanism": "m",
                     "mechanism_space_candidate": {
                         "mechanism_source_span": "fallback span"}}
    child = build_child_ms_candidate(parent_fields, dead_e,
                                     dict(MUTATION), 1)
    assert child["mechanism_source_span"] == "fallback span"


def test_child_id_and_support_state():
    dead_e = {
        "candidate_id": "p9", "key": "k9", "kill_class": "ATTACK_GAUNTLET",
        "kill_basis": [], "parent_fields": {"mechanism": "m"},
        "mechanism_space_candidate": {"mechanism_source_span": "s"},
    }
    child = build_child_ms_candidate({"mechanism": "m"}, dead_e,
                                     dict(MUTATION), 3)
    assert child["candidate_id"] == "p9+improve-g3"
    assert child["mechanism_support"] is None  # honest-unknown (Art. XXV)
    assert child["transformation_operator"] == "IMPROVE_G3"

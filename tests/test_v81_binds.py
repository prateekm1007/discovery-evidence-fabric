#!/usr/bin/env python3
"""tests/test_v81_binds.py — the AM42 D1+D2 bind suite (zero-LLM,
zero-network, deterministic): the computed-physics relations on known
values, the TRIZ mapping determinism + diversity, the selection bind,
the frozen V8.0 machine's byte-integrity, and the Art. 16 retirement
accounting. Wired into the queue surface via pytest."""
from __future__ import annotations

import hashlib
import math
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from v81_physics import (  # noqa: E402
    arrhenius_ratio, npsh_available, langelier_saturation_index,
    carnot_cop, larson_miller_parameter, dewpoint_frost_threshold,
    fouling_resistance_growth, scan_computed_physics)
from triz_principles import (  # noqa: E402
    PRINCIPLES, seed_for, distinct_principles, CONTRADICTION_MAP)
from r45_machine_v81 import (  # noqa: E402
    _candidate_plans, _score, select_best, MACHINE_DESCRIPTOR)


def test_arrhenius_known_value():
    # Ea=80 kJ/mol, 300->350 K: ratio = exp(80000/8.31446 * (1/300-1/350))
    r = arrhenius_ratio(80000.0, 300.0, 350.0)
    expected = math.exp(-80000.0 / 8.314462618 * (1 / 350 - 1 / 300))
    assert abs(r["value"] - expected) < 1e-9
    assert 60 < r["value"] < 110  # ~79x — the textbook scale
    assert r["units"]["value"] == "dimensionless"


def test_npsh_known_value():
    # water 20 C: P_atm 101325, P_vap 2339, rho 998.2, z=3 m, loss=1 m
    r = npsh_available(101325.0, 2339.0, 998.2, 3.0, 1.0)
    expected = (101325.0 - 2339.0) / (998.2 * 9.80665) + 3.0 - 1.0
    assert abs(r["value"] - expected) < 1e-9
    assert 11.5 < r["value"] < 12.5  # 10.11 (vapor head) + 3 - 1


def test_lsi_sign_direction():
    # scaling water (high pH, high Ca) must read LSI > 0;
    # aggressive water must read LSI < 0
    scaling = langelier_saturation_index(8.2, 400.0, 25.0, 150.0, 120.0)
    aggressive = langelier_saturation_index(6.5, 50.0, 25.0, 10.0, 10.0)
    assert scaling["value"] > 0.2
    assert aggressive["value"] < -0.5


def test_carnot_cop_ceiling():
    r = carnot_cop(273.15, 308.15)
    assert abs(r["value"] - 273.15 / 35.0) < 1e-9
    try:
        carnot_cop(300.0, 300.0)
        raise AssertionError("T_hot == T_cold must raise (typed)")
    except ValueError:
        pass


def test_larson_miller_known_value():
    r = larson_miller_parameter(900.0, 1000.0, 20.0)
    assert abs(r["value"] - 900.0 * (20 + 3)) < 1e-9  # 20700


def test_dewpoint_known_value():
    r = dewpoint_frost_threshold(20.0, 50.0)
    assert 8.5 < r["value"] < 10.5  # ~9.3 degC at 20C/50%RH
    frost = dewpoint_frost_threshold(0.0, 80.0)
    assert frost["value"] < 0  # frost-forming conditions


def test_fouling_asymptote():
    r = fouling_resistance_growth(2e-4, 7200.0, 7200.0)
    assert 0 < r["value"] < 2e-4  # asymptotic: never exceeds R_f_inf
    r2 = fouling_resistance_growth(2e-4, 7200.0, 1e9)
    assert abs(r2["value"] - 2e-4) < 1e-9  # -> R_f_inf at large t


def test_scan_computed_physics_consistent():
    answer = (
        "NOVELTY STATEMENT:\n proposes thermal-aging relief via "
        "material substitution.\n"
        "PHYSICS CHECK:\n The governing relation is the Arrhenius "
        "acceleration factor: with Ea = 80 kJ/mol, raising the "
        "temperature from 300 K to 350 K gives a reaction-rate factor "
        "of about 79 (dimensionless).\n"
        "IMPLEMENTATION BILL:\n standard alloy.\n")
    prob = {"problem_id": "T1", "device": "d", "failure": "f",
            "question": "q", "question_type": "intervention-proposal"}
    f = scan_computed_physics(prob, answer)
    assert "COMPUTED_PHYSICS_CONSISTENT" in f, f
    assert "COMPUTED_PHYSICS_INCONSISTENT" not in f


def test_scan_computed_physics_inconsistent_flagged():
    answer = (
        "PHYSICS CHECK:\n Arrhenius acceleration: Ea = 80 kJ/mol from "
        "300 K to 350 K gives a rate factor of about 2 (dimensionless)."
        "\nIMPLEMENTATION BILL:\n x.\n")
    prob = {"problem_id": "T2", "device": "d", "failure": "f",
            "question": "q", "question_type": "intervention-proposal"}
    f = scan_computed_physics(prob, answer)
    assert "COMPUTED_PHYSICS_INCONSISTENT" in f, f


def test_scan_computed_physics_uncomputable_typed():
    answer = "PHYSICS CHECK:\n the mechanism conserves energy.\n"
    prob = {"problem_id": "T3", "device": "d", "failure": "f",
            "question": "q", "question_type": "intervention-proposal"}
    f = scan_computed_physics(prob, answer)
    assert ("COMPUTED_PHYSICS_UNCOMPUTABLE_NO_INPUTS" in f
            or "COMPUTED_PHYSICS_RELATION_UNMAPPED" in f), f


def test_triz_map_deterministic_and_diverse():
    s1 = seed_for("a pump suffers cavitation at the suction eye")
    assert s1[0] and s1[0][0] in PRINCIPLES
    assert seed_for("a pump suffers cavitation") == \
        seed_for("a pump suffers cavitation")  # deterministic
    seeds = [seed_for(t) for t in (
        "pump cavitation at the suction eye",
        "hot spot thermal degradation of the winding",
        "fouling deposits on the condenser tubes")]
    assert distinct_principles(seeds), seeds


def test_candidate_plans_shape():
    prob = {"problem_id": "T4", "device": "centrifugal pump",
            "failure": "cavitation erosion on the impeller",
            "question": "design an intervention",
            "question_type": "intervention-proposal"}
    plans = _candidate_plans(prob)
    assert len(plans) == 3, plans
    classes = [c for c, _ in plans]
    pids = [p for _, p in plans]
    assert len(set(classes)) == 3  # distinct counted classes
    assert len(set(pids)) == 3  # distinct TRIZ principles
    assert all(p in PRINCIPLES for p in pids)


def test_selection_prefers_clean_non_duty_computed():
    cands = [
        {"index": 0, "final": "a", "vio": {"X": 1}, "score": (1, 1, 0),
         "computed_ok": 0, "cls": "duty-cycle modulation", "pid": 19},
        {"index": 1, "final": "b", "vio": {"X": 1}, "score": (1, 0, -1),
         "computed_ok": 1, "cls": "surface-condition management",
         "pid": 3},
        {"index": 2, "final": "c", "vio": {"Y": 1, "Z": 1},
         "score": (2, 0, 0), "computed_ok": 0,
         "cls": "interface isolation", "pid": 39},
    ]
    best = select_best(cands, Counter())
    assert best["index"] == 1  # clean tie -> computed-consistent wins


def test_score_penalizes_monoculture():
    vio_duty = {"MECHANISM_TEMPLATE_MONOCULTURE": ["3rd of class"]}
    s = _score(vio_duty, "x")
    assert s[1] == 1  # duty/monoculture penalty active


def test_v80_machine_byte_frozen():
    """The retired V8.0 machine is BYTE-UNCHANGED from 88e693581."""
    import shutil
    git = shutil.which("git")
    want = subprocess.run(
        [git, "show", "88e693581:scripts/r43_machine_v8.py"],
        capture_output=True, text=True, cwd=str(REPO)).stdout
    have = (REPO / "scripts" / "r43_machine_v8.py").read_text(
        encoding="utf-8")
    assert hashlib.sha256(want.encode()).hexdigest() == \
        hashlib.sha256(have.encode()).hexdigest()


def test_machine_descriptor_v81():
    assert MACHINE_DESCRIPTOR["machine"] == "V8.1"
    assert MACHINE_DESCRIPTOR["k_candidates"] == 3
    assert MACHINE_DESCRIPTOR["request_model"] == "glm-4-plus"


def test_retirement_ledger_accounting():
    led = (REPO / "eval" / "retirement_ledger.json")
    d = __import__("json").loads(led.read_text(encoding="utf-8"))
    entries = {e["retired"]: e for e in d["retirements"]}
    assert any("r43_machine_v8" in k for k in entries), list(entries)
    e = next(v for k, v in entries.items() if "r43_machine_v8" in k)
    assert e["successor"] == "V8.1 (scripts/r45_machine_v81.py)"
    assert "AM42" in e["reason"] or "delete-list" in e["reason"]

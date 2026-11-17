#!/usr/bin/env python3
"""tests/test_v8_generation_binds.py — the V8 generation-binds
acceptance suite (claim c-0060, the R42 verdict D1/D2/D5).

Zero-LLM: every leg runs the deterministic V8 scans over COMMITTED
bytes (the burned v7 rows, the burned v6/v4 holdout rows) and the
LABELLED FIXTURES in eval/r43_scan_labels.json (each fixture typed
FIXTURE — mechanics-proving per Art. 22; no fixture ever counts as a
fresh-problem capability measurement, which is the v8 one-shot's).

ACCEPTANCE (the R42 verdict's numbers):
  D2/F57 — precision >= 0.9 AND recall >= 0.9 on the labelled set,
            per scan class (input availability; allowed rows).
  D1/F58 — the cap COUNTS INFERRED classes: an omitted MECHANISM
            CLASS declaration no longer escapes the diversity
            histogram; the declaration parse strips markdown
            emphasis (the delete-list item).
  D1c    — 0 unpriced duty cycles: the quantified-OPERATIONAL-COST
            requirement fires on the 4 labelled unpriced v7 rows and
            stays silent on the quantified / explicit-zero controls.
  D1a    — the CANDIDATE CLASSES bind is active (fires on pre-bind
            bills; the structured control parses clean).
  D5     — the predictor direction-of-effect framing fires on the
            labelled conflated rows (HO7-09/10/12) and stays silent
            on the detection-framed control.

NOT testable on committed bytes (measured at the v8 one-shot, D4):
the >= 80% non-duty-cycle fraction where physics admits, and the
mean-repairs/row fall — both are run-time properties of the frozen
V8 machine on the sealed v8 problems; the binds here are the
generation-side levers that move them.
"""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r43_v8_binds import (  # noqa: E402
    scan_candidate_classes_v8, scan_mechanism_class_v8,
    scan_duty_pricing_v8, scan_input_availability_v8,
    scan_allowed_rows_v8, scan_predictor_direction_v8,
    counted_class, infer_mechanism_class, _strip_md)

LABELS = json.loads(
    (REPO / "eval" / "r43_scan_labels.json").read_text())
V7_FIELDS = {p["problem_id"]: p for p in json.loads(
    (REPO / "eval" / "r43_v7_problem_fields_burned.json")
    .read_text())["problems"]}


def _row(path):
    return json.loads((REPO / path).read_text())


def _problem_for(path, extra=None):
    pid = _row(path)["problem_id"]
    if extra:
        return extra
    return V7_FIELDS[pid]


def _answer(path):
    return _row(path)["a1_answer"]


# ---------------------------------------------------------------------------
# D2/F57 — input availability: precision + recall on the labelled set
# ---------------------------------------------------------------------------

def test_input_availability_precision_on_labelled_negatives():
    """All 7 v7 rows the retired free-prose scan FALSE-flagged must
    stay silent under the structured extraction (INPUT_UNAVAILABLE
    only; the new mandatory-declaration findings are a different
    class and do not count against input precision)."""
    negs = LABELS["classes"]["input_availability"]["negatives"]
    fired = []
    for neg in negs:
        prob = _problem_for(neg["row"])
        out = scan_input_availability_v8(prob, _answer(neg["row"]))
        if out.get("INPUT_UNAVAILABLE"):
            fired.append((neg["row"], out["INPUT_UNAVAILABLE"]))
    precision_den = len(negs)
    assert not fired, f"structured scan false-fired on: {fired}"
    assert precision_den >= 7  # the corpus is the 8-FP verdict set


def test_input_availability_recall_on_labelled_positives():
    """The TRUE unavailable-input classes must fire: the committed
    HO6-12 row (the AM37 D2 basis — the stated relation consumes
    unpermitted water-chemistry quantities) and the two authored
    labelled fixtures."""
    pos = LABELS["classes"]["input_availability"]["positives"]
    missed = []
    for p in pos:
        if "fixture" in p:
            prob = p["fixture"]
            ans = p["fixture"]["answer"]
            prob = {k: v for k, v in prob.items() if k != "answer"}
        else:
            prob = p["problem_fields"]
            ans = _answer(p["row"])
        out = scan_input_availability_v8(prob, ans)
        if not out.get("INPUT_UNAVAILABLE"):
            missed.append(p.get("row", "fixture"))
    assert not missed, f"structured scan missed TRUE positives: {missed}"


def test_input_availability_precision_recall_threshold():
    """The F57 acceptance: P >= 0.9 AND R >= 0.9 on the labelled set
    (computed from the same corpus the two legs above prove: 8
    negatives -> 0 firings; 3 positives -> 3 firings)."""
    negs = LABELS["classes"]["input_availability"]["negatives"]
    poss = LABELS["classes"]["input_availability"]["positives"]
    fp = 0
    for neg in negs:
        out = scan_input_availability_v8(
            _problem_for(neg["row"]), _answer(neg["row"]))
        fp += bool(out.get("INPUT_UNAVAILABLE"))
    tp = 0
    for p in poss:
        if "fixture" in p:
            prob = {k: v for k, v in p["fixture"].items()
                    if k != "answer"}
            ans = p["fixture"]["answer"]
        else:
            prob = p["problem_fields"]
            ans = _answer(p["row"])
        tp += bool(scan_input_availability_v8(prob, ans)
                   .get("INPUT_UNAVAILABLE"))
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / len(poss)
    assert precision >= 0.9, f"precision {precision:.2f} < 0.9"
    assert recall >= 0.9, f"recall {recall:.2f} < 0.9"


# ---------------------------------------------------------------------------
# D2/F57 — allowed rows: the parsing artifacts gone; the TRUE class
# violations still fire
# ---------------------------------------------------------------------------

def test_allowed_rows_no_parsing_artifacts_on_v7():
    """The 4 unambiguous parsing artifacts (replaced-old-item,
    comparative echo, burden echo, mid-sentence fragment) must stay
    silent under the structured head-object extraction. The labels
    are PER-FINDING: a row that also carries an ADJUDICATION-PENDING
    apparatus finding (HO7-04's probe) may fire THAT finding — the
    assertion is that the labelled artifact SPAN is gone from the
    scan's findings, not that the whole row is silent."""
    negs = LABELS["classes"]["allowed_rows"]["negatives"]
    artifact_spans = {
        "HO7-01": ["standard surfactant"],
        "HO7-04": ["vs. standard practice"],
        "HO7-06": ["consumables or maintenance", "pressure transducer"],
    }
    for neg in negs:
        pid = next(k for k in artifact_spans
                   if k in neg["row"])
        out = scan_allowed_rows_v8(
            _problem_for(neg["row"]), _answer(neg["row"]))
        blob = json.dumps(out)
        for span in artifact_spans[pid]:
            assert span not in blob, (
                f"parsing artifact '{span}' survived on {neg['row']}: "
                f"{out}")


def test_allowed_rows_precision_on_all_v7_rows():
    """Beyond the labelled 4: the retired scan's COMPLETE v7 firing
    set was 7 findings on 4 rows (the verifier inventory); the
    structured scan must fire on NO v7 row except the 3
    apparatus-class PENDING rows (tolerated, excluded from the
    denominator)."""
    pending_rows = {p["row"] for p in
                    LABELS["classes"]["allowed_rows"]["pending"]}
    fired = []
    # enumerate the committed v7 rows directly
    for rowf in sorted((REPO / "eval" / "v7_run" / "rows")
                       .glob("HO7-*.json")):
        d = json.loads(rowf.read_text())
        prob = V7_FIELDS[d["problem_id"]]
        out = scan_allowed_rows_v8(prob, d["a1_answer"])
        if out.get("ALLOWED_ROW_OUTSIDE"):
            rel = str(rowf.relative_to(REPO))
            if rel not in pending_rows:
                fired.append((rel, out["ALLOWED_ROW_OUTSIDE"][:1]))
    assert not fired, f"new ALLOWED_ROW_OUTSIDE firings on v7: {fired}"


def test_allowed_rows_recall_on_ho4_positives():
    """The AM29-documented TRUE class violations (HO4-04 shield/
    support/exhaust-cooler rows; HO4-05 washer row under param-
    exhaustive permitted sets) must still fire."""
    poss = LABELS["classes"]["allowed_rows"]["positives"]
    for p in poss:
        out = scan_allowed_rows_v8(
            p["problem_fields"], _answer(p["row"]))
        assert out.get("ALLOWED_ROW_OUTSIDE") or \
            out.get("ACTUATION_DEVICE_AS_MEASURE"), (
            f"TRUE class violation missed on {p['row']}: {out}")


# ---------------------------------------------------------------------------
# D1c — quantified operational cost
# ---------------------------------------------------------------------------

def test_duty_pricing_fires_on_labelled_unpriced():
    for p in LABELS["classes"]["duty_pricing"]["positives"]:
        out = scan_duty_pricing_v8(_answer(p["row"]))
        assert out.get("UNPRICED_DUTY_CYCLE"), (
            f"unpriced duty cycle missed on {p['row']}: {out}")


def test_duty_pricing_silent_on_quantified_controls():
    for neg in LABELS["classes"]["duty_pricing"]["negatives"]:
        out = scan_duty_pricing_v8(neg["fixture_answer"])
        assert not out.get("UNPRICED_DUTY_CYCLE"), (
            f"quantified cost control fired: {out}")


def test_duty_pricing_phrase_only_escape_closed():
    """The V7.7 escape — the phrase 'OPERATIONAL COST' present with
    NO number on it — no longer prices a duty cycle (the HO7-03
    pricing-control class)."""
    ans = ("NOVELTY STATEMENT (INTERVENTION) — A pulsed schedule.\n"
           "MECHANISM CLASS: dosing schedule\n\n"
           "IMPLEMENTATION BILL\n"
           "- (c) Parameter change: timer set to 15 min on / 2 h off "
           "on the existing dosing pump.\n"
           "OPERATIONAL COST: the trade-off is acceptable given the "
           "mist reduction.\n"
           "\nBURDEN LEDGER (STANDARD-PRACTICE PARITY)\n"
           "- Same as standard practice.\n")
    out = scan_duty_pricing_v8(ans)
    assert out.get("UNPRICED_DUTY_CYCLE"), (
        f"the phrase-only escape is still open: {out}")


# ---------------------------------------------------------------------------
# D1b/F58 — the cap counts inferred classes; emphasis stripped
# ---------------------------------------------------------------------------

def test_mechanism_class_undeclared_rows_fire_and_count():
    undeclared = LABELS["classes"]["mechanism_class_cap"][
        "undeclared_rows"]
    for u in undeclared:
        out = scan_mechanism_class_v8(_answer(u["row"]), used=None)
        assert out.get("MECHANISM_CLASS_UNSTATED"), (
            f"missing declaration not typed on {u['row']}: {out}")


def test_cap_counts_inferred_classes_f58():
    """F58: the three UNDECLARED v7 interventions all ship the
    schedule/duty template (the F54 monoculture); with their INFERRED
    classes counted, the histogram reaches the cap and the third
    fires MECHANISM_TEMPLATE_MONOCULTURE — an omitted declaration no
    longer escapes the diversity cap."""
    undeclared = LABELS["classes"]["mechanism_class_cap"][
        "undeclared_rows"]
    counted = [counted_class(_answer(u["row"])) for u in undeclared]
    # the inference must not collapse everything to one class nor
    # scatter trivially — the F54 finding says these are the SAME
    # duty-cycle template: at least two must share a class
    from collections import Counter
    hist = Counter(counted)
    assert hist.most_common(1)[0][1] >= 2, (
        f"the inferred classes of the F54 monoculture rows do not "
        f"reproduce the shared template: {counted}")
    # the cap fires when the shared class already holds 2
    shared = hist.most_common(1)[0][0]
    used = Counter({shared: 2})
    fired = False
    for u, c in zip(undeclared, counted):
        out = scan_mechanism_class_v8(_answer(u["row"]), used=used)
        if c == shared and out.get("MECHANISM_TEMPLATE_MONOCULTURE"):
            fired = True
    assert fired, (
        "the cap never fired on the third row of the shared INFERRED "
        f"class ({shared}; counted={counted}) — the F58 bypass is "
        "still open")


def test_declaration_parse_strips_markdown_emphasis():
    """The delete-list item: HO7-05's declaration carries a trailing
    '**' — the V8 parse strips emphasis (the counted class is clean
    and matches the declared phrase)."""
    declared = [d for d in LABELS["classes"]["mechanism_class_cap"]
                ["declared_rows"] if "HO7-05" in d["row"]][0]
    c = counted_class(_answer(declared["row"]))
    assert "*" not in c, f"markdown emphasis reached the class: {c!r}"
    assert c == "programmable current-density modulation", (
        f"the stripped declaration does not parse to the declared "
        f"phrase: {c!r}")


def test_declared_rows_count_by_declaration():
    for d in LABELS["classes"]["mechanism_class_cap"]["declared_rows"]:
        c = counted_class(_answer(d["row"]))
        assert "*" not in c
        assert c == _strip_md(d["declared"]).strip().lower(), (
            f"counted class {c!r} != declared {d['declared']!r}")


# ---------------------------------------------------------------------------
# D1a — the candidate-class enumeration bind
# ---------------------------------------------------------------------------

def test_candidate_classes_missing_fires_on_prebind_bills():
    """Every v7 intervention predates the clause — the bind must be
    ACTIVE on them (CANDIDATE_CLASSES_MISSING): the generator is now
    required to enumerate before selecting."""
    rows = [u["row"] for u in
            LABELS["classes"]["mechanism_class_cap"]["undeclared_rows"]]
    for r in rows:
        out = scan_candidate_classes_v8(_answer(r))
        assert out.get("CANDIDATE_CLASSES_MISSING"), (
            f"the candidate-classes bind is not active on {r}: {out}")


def test_candidate_classes_structured_control_parses():
    """A conformant CANDIDATE CLASSES section (3 distinct, a
    non-duty-cycle candidate, SELECTED with the physics rejection of
    the duty-cycle alternative) stays silent."""
    ans = ("NOVELTY STATEMENT (INTERVENTION) — A night-reset "
           "schedule plus a permitted-solvent wipe.\n"
           "MECHANISM CLASS: maintenance schedule\n"
           "CANDIDATE CLASSES\n"
           "- chemistry dissolution via the permitted solvent — "
           "attacks the deposit directly but reaction kinetics are "
           "too slow for the 30-min cycle (rejected: physics)\n"
           "- mechanical abrasion removal — removes the deposit but "
           "needs an added drive (rejected: burden)\n"
           "- night-window reset schedule — clears accumulation "
           "off-production\n"
           "SELECTED: night-window reset schedule — zero production "
           "impact; selected over the chemistry class because the "
           "dissolution kinetics cannot keep pace with the daily "
           "accumulation rate\n\n"
           "IMPLEMENTATION BILL\n"
           "- (c) Parameter change: reset cycle runs 02:00-04:00 "
           "nightly.\nSIGNALS USED: none (open-loop)\n"
           "OPERATIONAL COST: zero (night window, non-producing "
           "interval)\n")
    out = scan_candidate_classes_v8(ans)
    assert not out, f"conformant candidate section fired: {out}"


def test_candidate_classes_duty_preference_unproven():
    """A duty-cycle SELECTED over an enumerated non-duty-cycle
    candidate with NO physics rejection fires the preference bind."""
    ans = ("NOVELTY STATEMENT (INTERVENTION) — A duty-cycle.\n"
           "MECHANISM CLASS: setpoint schedule\n"
           "CANDIDATE CLASSES\n"
           "- chemistry dissolution via the permitted solvent — "
           "attacks the deposit\n"
           "- mechanical abrasion removal — removes the deposit\n"
           "- setpoint schedule — cycles the operating point\n"
           "SELECTED: setpoint schedule — simplest to implement\n\n"
           "IMPLEMENTATION BILL\n"
           "- (c) Parameter change: timer 15 min on / 2 h off.\n"
           "SIGNALS USED: none (open-loop)\n"
           "OPERATIONAL COST: 3% throughput during the windows.\n")
    out = scan_candidate_classes_v8(ans)
    assert out.get("DUTY_CYCLE_PREFERENCE_UNPROVEN"), (
        f"the duty-cycle preference bind did not fire: {out}")


def test_candidate_classes_nonduty_absent():
    """An all-duty-cycle enumeration fires NONDUTY_CANDIDATE_ABSENT —
    the generator must LOOK at non-duty-cycle physics before
    defaulting to the template."""
    ans = ("NOVELTY STATEMENT (INTERVENTION) — A duty-cycle.\n"
           "MECHANISM CLASS: setpoint schedule\n"
           "CANDIDATE CLASSES\n"
           "- setpoint schedule — cycles the operating point\n"
           "- duty-cycle modulation — periodic reset\n"
           "- derate schedule — lowers load periodically\n"
           "SELECTED: setpoint schedule — simplest\n\n"
           "IMPLEMENTATION BILL\n"
           "- (c) Parameter change: timer 15 min on / 2 h off.\n"
           "SIGNALS USED: none (open-loop)\n"
           "OPERATIONAL COST: 3% throughput during the windows.\n")
    out = scan_candidate_classes_v8(ans)
    assert out.get("NONDUTY_CANDIDATE_ABSENT"), (
        f"the non-duty-candidate bind did not fire: {out}")


# ---------------------------------------------------------------------------
# D5 — predictor direction-of-effect framing
# ---------------------------------------------------------------------------

def test_predictor_direction_fires_on_labelled_conflated_rows():
    for p in LABELS["classes"]["predictor_direction"]["positives"]:
        out = scan_predictor_direction_v8(_answer(p["row"]))
        assert out and any(
            k in out for k in ("PREDICTOR_DIRECTION_FRAMING",
                               "PREDICTOR_DIRECTION_UNSTATED")), (
            f"the conflated direction line on {p['row']} did not "
            f"fire: {out}")


def test_predictor_direction_silent_on_detection_framed_control():
    for neg in LABELS["classes"]["predictor_direction"]["negatives"]:
        out = scan_predictor_direction_v8(neg["fixture_answer"])
        assert not out, f"detection-framed control fired: {out}"


def test_predictor_direction_intervention_action_detected():
    """The exact HO7-09 conflation shape — 'the mechanism raises it'
    — is typed as a FRAMING defect, not just unstated."""
    line = ("PHYSICS CHECK\nGoverning relation: COP = Q/P.\n"
            "DIRECTION OF EFFECT: the mechanism raises the heat "
            "transfer rate by maintaining the approach temperature "
            "via compressor power increase, which reduces the "
            "fouling driver.\n")
    out = scan_predictor_direction_v8(line)
    assert out.get("PREDICTOR_DIRECTION_FRAMING"), (
        f"the intervention-action framing was not typed: {out}")


# ---------------------------------------------------------------------------
# the V8 machine surface (import-level: the binds are wired into the
# generation loop, not just present as functions)
# ---------------------------------------------------------------------------

def test_v8_machine_contract_carries_the_binds():
    from r43_v8_binds import (SYS_A1_INT_V8, SYS_A1F_V8,
                              contract_for_v8)
    for token in ("CANDIDATE CLASSES", "SELECTED:", "MECHANISM CLASS:",
                  "OPERATIONAL COST", "SIGNALS USED:"):
        assert token in SYS_A1_INT_V8, f"intervention bind {token!r} missing"
    for token in ("INPUT INVENTORY:", "DIRECTION OF EFFECT:"):
        assert token in SYS_A1F_V8, f"predictor bind {token!r} missing"
    assert contract_for_v8("intervention-proposal") is SYS_A1_INT_V8
    assert contract_for_v8("predictor-design") is SYS_A1F_V8


def test_v8_machine_loop_uses_the_v8_scans():
    import inspect
    from r43_machine_v8 import machine_generate_v8
    src = inspect.getsource(machine_generate_v8)
    for fn in ("scan_candidate_classes_v8",
               "scan_input_availability_v8",
               "scan_duty_pricing_v8",
               "scan_mechanism_class_v8"):
        assert fn in src, f"the V8 loop does not call {fn}"
    for retired in ("scan_input_availability(", "scan_duty_cycle_"
                    "pricing(", "scan_mechanism_template("):
        assert retired not in src, (
            f"the retired free-prose scan {retired!r} is still in "
            "the V8 loop")


def test_v8_machine_histogram_counts_inferred_classes():
    """The driver's counted_template binds on counted_class —
    declared when present, INFERRED otherwise (F58)."""
    from r43_machine_v8 import counted_template
    from r43_v8_binds import counted_class
    undeclared = LABELS["classes"]["mechanism_class_cap"][
        "undeclared_rows"][0]["row"]
    assert counted_template(_answer(undeclared)) == \
        counted_class(_answer(undeclared))
    assert counted_template(_answer(undeclared)) == \
        infer_mechanism_class(_answer(undeclared))


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))

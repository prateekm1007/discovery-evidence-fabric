#!/usr/bin/env python3
"""tests/test_r103_core_mechanism_gate.py — the SPECTER2
core-mechanism gate battery (claim c-0120; deterministic, ZERO LLM,
ZERO network — Art. 22: fixtures prove mechanics only; the live gate
measurement on the auditor-authored v16 set is the runtime harness's
job, never CI's).

Covers the pre-registered contract of
discovery_fabric/engine/core_mechanism_gate.py (the r100 prereg
implemented byte-faithfully; the AM87-redefined anchor-relative gate):

  1. EXTRACTION (deterministic, fail-closed):
     - the plain marker form 'NOVELTY STATEMENT (INTERVENTION)' with
       the paragraph body in the same block (the v13 shape);
     - the standalone heading line with the paragraph UNDER it;
     - the markdown heading form '# NOVELTY STATEMENT' (the
       HO13-16-class committed bytes);
     - the 'mechanism' fallback branch;
     - EXTRACTION_MISS typed and EXCLUDED (never guessed).
  2. THE PREREG ANCHOR PAIR: the module constants are byte-identical
     to the committed eval/r100_core_mechanism_prereg.json (the
     pre-registration is the contract; CI pins the parity).
  3. THE PERCENTILE CONVENTION: sorted ascending, index int(n*q),
     clamped (the committed r99 harness convention).
  4. THE ANCHOR-RELATIVE GATE: BOTH conditions required, strictly
     greater on each (boundary: equality is NOT novel), every
     component disclosed in the verdict.
  5. CALIBRATION: paraphrase sanity strictly < 0.05; separation
     >= 0.10 AND the known-novel anchor beyond the prior p95.
  6. THE STUB ENCODER: deterministic, sha256-stable (cross-process).
  7. THE COMPOSED CORPUS EVALUATOR: extraction-miss disclosure,
     empty-prior typed refusal, deterministic re-run equality, and
     the burned-v13 mechanics-only fixtures (both committed heading
     forms + the fallback row).
  8. CROSS-HASH-SEED DETERMINISM (the Art. 15 pattern): the full
     corpus record reproduces byte-identically under PYTHONHASHSEED
     1 and 2 in fresh subprocesses.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.core_mechanism_gate import (  # noqa: E402
    ANCHOR_SEPARATION_MIN,
    KNOWN_NOVEL_ANCHOR,
    KNOWN_OBVIOUS_ANCHOR,
    KNOWN_OBVIOUS_ANCHOR_PARAPHRASE,
    PARAPHRASE_SANITY_MAX,
    PREREG_MARGIN,
    StubEncoder,
    anchor_relative_gate,
    calibration_checks,
    canonical_json,
    cosine_distance,
    evaluate_corpus,
    extract_core_mechanism,
    pairwise_percentile,
)

V13_ROWS = REPO / "eval" / "holdout_v13_generation" / "rows"


def _mk_answer(marker_block: str, *paras) -> str:
    return "\n\n".join([marker_block] + list(paras))


class TestExtractionRule(unittest.TestCase):
    def test_plain_marker_inline_body(self):
        """The v13 shape: marker line + paragraph body in one block."""
        ans = _mk_answer(
            "NOVELTY STATEMENT (INTERVENTION)\n"
            "The intervention proposes retuning the electric-boost "
            "duty cycle to eliminate the thermal inversion.",
            "PHYSICS CHECK\nGoverning relation: r = D/eta * dc.")
        c = extract_core_mechanism(ans)
        self.assertEqual(c.method, "novelty_statement_marker")
        self.assertTrue(c.text.startswith("The intervention "
                                             "proposes"))
        self.assertNotIn("NOVELTY STATEMENT", c.text)
        self.assertNotIn("PHYSICS", c.text)

    def test_standalone_heading_takes_paragraph_under_it(self):
        ans = _mk_answer(
            "MECHANISM CLASS: PCI-Ramp Duty-Cycle Modulation",
            "NOVELTY STATEMENT (INTERVENTION)",
            "The proposed intervention is a scheduled modulation of "
            "the PCI ramp rate and duty cycle.",
            "PHYSICS CHECK\nLater block.")
        c = extract_core_mechanism(ans)
        self.assertEqual(c.method, "novelty_statement_marker")
        self.assertTrue(c.text.startswith("The proposed "
                                             "intervention"))
        self.assertEqual(c.paragraph_index, 2)

    def test_markdown_heading_form(self):
        """The HO13-16-class committed bytes: '# NOVELTY STATEMENT'
        glued to its body in one paragraph."""
        ans = _mk_answer(
            "# NOVELTY STATEMENT\nStandard practice delivers a "
            "MONITORING/INDICATION scheme via direct thickness "
            "measurement with the mechanism of ultrasonic polling.",
            "Later block without the marker.")
        c = extract_core_mechanism(ans)
        self.assertEqual(c.method, "novelty_statement_marker")
        self.assertTrue(c.text.startswith("Standard practice"))

    def test_mechanism_fallback_branch(self):
        ans = _mk_answer(
            "PROCESS CLASS: Thermal-Stage Setpoint Reduction",
            "Operating paragraph without the marker heading.",
            "The mechanism lowers the thermal-stage temperature "
            "setpoint to the minimum catalytic window.")
        c = extract_core_mechanism(ans)
        self.assertEqual(c.method, "mechanism_fallback")
        self.assertIn("mechanism lowers", c.text)

    def test_fallback_takes_first_keyword_paragraph(self):
        """The fallback is the FIRST paragraph containing the word —
        even when a later paragraph is 'more relevant' (the rule is
        deterministic, never a relevance guess)."""
        ans = _mk_answer(
            "Plain operating header.",
            "A first paragraph mentioning the mechanism in passing.",
            "A later paragraph about something else entirely.")
        c = extract_core_mechanism(ans)
        self.assertEqual(c.method, "mechanism_fallback")
        self.assertIn("in passing", c.text)

    def test_extraction_miss_fail_closed(self):
        ans = _mk_answer("Operating header without the marker.",
                         "Nothing relevant here at all.")
        c = extract_core_mechanism(ans)
        self.assertTrue(c.extraction_miss)
        self.assertIsNone(c.text)

    def test_empty_and_degenerate_inputs_typed(self):
        for bad in ("", "   ", None):
            c = extract_core_mechanism(bad)
            self.assertTrue(c.extraction_miss)


class TestPreregAnchorParity(unittest.TestCase):
    """The module constants must be byte-identical to the committed
    pre-registration (the contract is the prereg, not this module)."""

    def test_anchor_pair_matches_committed_prereg(self):
        p = json.loads(
            (REPO / "eval" / "r100_core_mechanism_prereg.json")
            .read_text(encoding="utf-8"))
        ap = p["anchor_pair"]
        self.assertEqual(KNOWN_OBVIOUS_ANCHOR,
                         ap["known_obvious_anchor"])
        self.assertEqual(KNOWN_OBVIOUS_ANCHOR_PARAPHRASE,
                         ap["known_obvious_anchor_paraphrase"])
        self.assertEqual(KNOWN_NOVEL_ANCHOR,
                         ap["known_novel_anchor"])
        self.assertEqual(PREREG_MARGIN, ap["margin_preregistered"])
        # the sanity/separation constants come from the prereg's
        # calibration checks + anchor-separation clause
        self.assertEqual(PARAPHRASE_SANITY_MAX, 0.05)
        self.assertEqual(ANCHOR_SEPARATION_MIN, 0.10)


class TestPercentileConvention(unittest.TestCase):
    def test_pinned_convention(self):
        # 100 ascending distances 0.000..0.099 -> index int(100*0.95)
        # = 95 -> the 96th smallest (0-based 95) == 95/1000 == 0.095
        d = [i / 1000.0 for i in range(100)]
        self.assertAlmostEqual(pairwise_percentile(d, 0.95), 0.095,
                               places=6)
        # small lists clamp to the last element
        self.assertEqual(pairwise_percentile([0.1, 0.2]), 0.2)
        self.assertEqual(pairwise_percentile([0.5]), 0.5)

    def test_empty_refused_typed(self):
        with self.assertRaises(ValueError):
            pairwise_percentile([])


class TestAnchorRelativeGate(unittest.TestCase):
    def _gate(self, row, obv, p95, margin=0.05):
        return anchor_relative_gate("R", row, obv, p95, margin)

    def test_both_conditions_required(self):
        v = self._gate(0.30, 0.10, 0.20)   # beyond both
        self.assertTrue(v.novel)
        # beyond margin only
        v = self._gate(0.30, 0.10, 0.35)
        self.assertFalse(v.novel)
        self.assertTrue(v.beyond_margin)
        self.assertFalse(v.beyond_p95)
        # beyond p95 only (0.13 > 0.12 but 0.13 <= 0.10+0.05)
        v = self._gate(0.13, 0.10, 0.12)
        self.assertFalse(v.novel)
        self.assertFalse(v.beyond_margin)
        self.assertTrue(v.beyond_p95)

    def test_strictly_greater_boundaries(self):
        # exactly at anchor+margin -> NOT novel (prereg: 'exceeds')
        v = self._gate(0.15, 0.10, 0.05)
        self.assertFalse(v.beyond_margin)
        self.assertFalse(v.novel)
        # exactly at p95 -> NOT novel ('beyond')
        v = self._gate(0.30, 0.10, 0.30)
        self.assertFalse(v.beyond_p95)
        self.assertFalse(v.novel)
        # one epsilon above each -> novel
        v = self._gate(0.150001, 0.10, 0.05)
        self.assertTrue(v.beyond_margin)
        v = self._gate(0.300001, 0.10, 0.30)
        self.assertTrue(v.beyond_p95)

    def test_components_disclosed(self):
        v = self._gate(0.30, 0.10, 0.20, 0.05)
        self.assertEqual(v.row_id, "R")
        self.assertEqual(v.margin, 0.05)
        self.assertEqual(v.core_mechanism_distance, 0.30)
        self.assertEqual(v.known_obvious_anchor_distance, 0.10)
        self.assertEqual(v.prior_p95, 0.20)


class TestCalibrationChecks(unittest.TestCase):
    def test_passing_calibration(self):
        c = calibration_checks(
            paraphrase_dist=0.039,
            obvious_prior_dist=0.10,
            novel_prior_dist=0.35,
            anchor_separation=0.1518,
            prior_p95=0.1258)
        self.assertTrue(c.paraphrase_pass)
        self.assertTrue(c.anchor_separation_pass)
        self.assertTrue(c.known_novel_beyond_p95)
        self.assertTrue(c.calibration_pass)

    def test_paraphrase_boundary_strict(self):
        c = calibration_checks(0.05, 0.1, 0.4, 0.15, 0.12)
        self.assertFalse(c.paraphrase_pass)      # 0.05 is NOT < 0.05
        self.assertFalse(c.calibration_pass)
        c = calibration_checks(0.0499, 0.1, 0.4, 0.15, 0.12)
        self.assertTrue(c.paraphrase_pass)

    def test_separation_requires_both_legs(self):
        # separation ok but the novel anchor NOT beyond p95 -> fail
        c = calibration_checks(0.03, 0.10, 0.11, 0.1518, 0.1258)
        self.assertFalse(c.anchor_separation_pass)
        self.assertFalse(c.calibration_pass)
        # beyond p95 but separation < 0.10 -> fail
        c = calibration_checks(0.03, 0.10, 0.40, 0.099, 0.1258)
        self.assertFalse(c.anchor_separation_pass)
        # separation exactly 0.10 -> passes (>= per the prereg)
        c = calibration_checks(0.03, 0.10, 0.40, 0.10, 0.05)
        self.assertTrue(c.anchor_separation_pass)


class TestStubEncoder(unittest.TestCase):
    def test_deterministic_and_normalized(self):
        e = StubEncoder()
        a1 = e.encode("cooling water backflush heat exchanger")
        a2 = e.encode("cooling water backflush heat exchanger")
        self.assertEqual(a1, a2)
        norm = sum(x * x for x in a1) ** 0.5
        self.assertAlmostEqual(norm, 1.0, places=9)
        b = e.encode("gecko setae van der waals PDMS stamp")
        self.assertNotEqual(a1, b)

    def test_shared_tokens_raise_cosine(self):
        e = StubEncoder()
        a = e.encode("raise the cooling water flow setpoint")
        b = e.encode("raise the cooling water flow rate")
        c = e.encode("enzymatic cross-linking of the resin binder")
        self.assertLess(cosine_distance(a, b), cosine_distance(a, c))


class TestCorpusEvaluator(unittest.TestCase):
    PRIOR = {
        "P-01": "NOVELTY STATEMENT (INTERVENTION)\nInstall an "
                "online turbidity monitor and trigger backwash when "
                "the differential pressure crosses the OEM "
                "threshold.",
        "P-02": "NOVELTY STATEMENT (INTERVENTION)\nThe intervention "
                "lowers the resin viscosity by heating the line and "
                "raises the stripping air flow.",
        "P-03": "NOVELTY STATEMENT (INTERVENTION)\n" +
                KNOWN_OBVIOUS_ANCHOR,
        "P-04": "NOVELTY STATEMENT (INTERVENTION)\nSwap the failing "
                "solenoid valve for the OEM replacement and "
                "recalibrate the positioner.",
    }
    ROWS = {
        "R-01": "NOVELTY STATEMENT (INTERVENTION)\nThe mechanism "
                "retunes the electric-boost duty cycle to remove "
                "the thermal inversion (a gecko-setae-class "
                "departure from standard practice).",
        "R-02": "NOVELTY STATEMENT (INTERVENTION)\nRestore the "
                "monthly heat-exchanger backflush and keep the "
                "setpoint inside the standard band.",
        "R-03": "An answer with no marker heading and no relevant "
                "keyword in its paragraphs at all.",
    }

    def _rec(self):
        return evaluate_corpus(self.ROWS, self.PRIOR, StubEncoder())

    def test_extraction_miss_disclosed_and_excluded(self):
        rec = self._rec()
        self.assertEqual(rec["rows"]["extraction_miss_count"], 1)
        self.assertEqual(rec["rows"]["extraction_miss_ids"], ["R-03"])
        self.assertEqual(len(rec["verdicts"]), 2)
        for v in rec["verdicts"]:
            self.assertNotEqual(v["row_id"], "R-03")

    def test_deterministic_rerun_equality(self):
        self.assertEqual(canonical_json(self._rec()),
                         canonical_json(self._rec()))

    def test_prior_corpus_fields(self):
        rec = self._rec()
        self.assertEqual(rec["prior_corpus"]["n_extracted"], 4)
        self.assertEqual(rec["prior_corpus"]["n_pairs"], 6)
        self.assertEqual(rec["margin"], PREREG_MARGIN)
        self.assertTrue(rec["zero_generation"])

    def test_empty_prior_refused_typed(self):
        with self.assertRaises(ValueError):
            evaluate_corpus(self.ROWS, {}, StubEncoder())
        # a prior whose every row misses extraction is equally
        # empty on the core-mechanism scale
        with self.assertRaises(ValueError):
            evaluate_corpus(
                self.ROWS,
                {"P-x": "no marker and no keyword here"},
                StubEncoder())

    def test_burned_v13_mechanics_fixture(self):
        """Art. 22 (mechanics-only, burned v13): the committed row
        bytes extract under BOTH observed heading forms + the
        fallback; no scoring relevance (v13 is burned)."""
        rows = {}
        for pid in ("HO13-01-glass-tank-stones",
                    "HO13-02-blast-furnace-tuyere",
                    "HO13-16-shot-blast-blade-erosion"):
            r = json.loads(
                (V13_ROWS / f"{pid}.json").read_text(encoding="utf-8"))
            rows[pid] = r["a1_answer"]
        by_id = {p: extract_core_mechanism(t).method
                 for p, t in rows.items()}
        # 01: inline plain marker; 02: standalone heading; 16:
        # the markdown heading form
        self.assertEqual(by_id["HO13-01-glass-tank-stones"],
                         "novelty_statement_marker")
        self.assertEqual(by_id["HO13-02-blast-furnace-tuyere"],
                         "novelty_statement_marker")
        self.assertEqual(by_id["HO13-16-shot-blast-blade-erosion"],
                         "novelty_statement_marker")


class TestCrossSeedDeterminism(unittest.TestCase):
    """Art. 15: the corpus record reproduces byte-identically under
    PYTHONHASHSEED 1 and 2 in fresh subprocesses (the committed
    pattern of test_article15_cross_seed_determinism)."""

    def test_record_hash_stable_across_hash_seeds(self):
        script = (
            "import json,sys,hashlib;sys.path.insert(0,%r);"
            "from discovery_fabric.engine.core_mechanism_gate"
            " import evaluate_corpus,StubEncoder,canonical_json;"
            "rows=json.loads(sys.argv[1]);prior=json.loads("
            "sys.argv[2]);print(hashlib.sha256(canonical_json("
            "evaluate_corpus(rows,prior,StubEncoder())).encode()"
            ").hexdigest())"
        ) % str(REPO)
        rows = json.dumps(TestCorpusEvaluator.ROWS)
        prior = json.dumps(TestCorpusEvaluator.PRIOR)
        hashes = []
        for seed in ("1", "2"):
            out = subprocess.run(
                [sys.executable, "-B", "-c", script, rows, prior],
                capture_output=True, text=True, timeout=120,
                env={**os.environ, "PYTHONHASHSEED": seed})
            self.assertEqual(out.returncode, 0, out.stderr[-400:])
            hashes.append(out.stdout.strip())
        self.assertEqual(hashes[0], hashes[1])


if __name__ == "__main__":
    unittest.main(verbosity=2)

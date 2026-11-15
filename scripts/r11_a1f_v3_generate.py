#!/usr/bin/env python3
"""r11_a1f_v3_generate.py — AM13 D2 (F30): feasibility-parity ideation.

V3 CHANGES (typed from the measured r8 structure, Art. XIX): the
NOVELTY STATEMENT moves FIRST (the judge anchors novelty from the
opener; the r8 novelty-negative answers opened with textbook physics);an ADJACENT-TECHNIQUE CLEARANCE step forces the observable away from
textbook relabels (Nernst-Einstein conductivity, relaxation
derivatives — the judge anchors those as standard practice somewhere);
COMPOSITE functionals of >=2 already-logged channels are named as
where untracked observables live (also the feasibility pattern of all
four gap=0 proofs: pure software derivation from existing channels).

The measured F30 tradeoff (audited at 575c7ee57): SYS_A1F's
STANDARD-PRACTICE PARITY section created gravity toward standard-
practice-shaped MECHANISMS (dev12 novelty -1.000; the model satisfied
parity by conventionalizing the indicator), while grounding improved
feasibility (2.0 -> 1.333, still failing). The v2 contract makes the
two axes ORTHOGONAL BY CONSTRUCTION instead of trading them:

  NOVELTY lives in the OBSERVABLE — the leading indicator is a new
  derived quantity that standard monitoring practice for this failure
  class does NOT track (a different physical quantity, a different
  inference from the same data, a different failure signature). The
  measurement PRINCIPLE is the departure.
  FEASIBILITY lives in the IMPLEMENTATION — the observable MUST be
  computable from the stated existing sensors/logging with standard
  engineering math; the deployment is deliberately conventional
  (off-the-shelf, boring, procurable today).
  PARITY becomes a BURDEN LEDGER — same deployment burden, different
  observable — and the contract explicitly forbids winning the parity
  comparison by conventionalizing the indicator (the measured F30
  failure mode, named in the prompt).

Basis (Art. XIX): this targets the mechanism the auditor typed, not a
scored pair; the battery problems are fixed and untouched (Art. LXXIX
tuning discipline: the contract is a system change recorded before the
measurement).

Generator: the curated GLM rung (zai gateway), the F29-consistent
generator. Set: eval/pairs/r11_a1f_r3/ — per-pair records with
generator + system_prompt + question_hash; bytes written per pair for
batch committing (AM10 D1 durability discipline).
"""
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")

OUT_DIR = REPO / "eval" / "pairs" / "r11_a1f_r3"
GW = "http://127.0.0.1:8787/v1/chat/completions"
now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")

SYS_A1_V2 = (
    "You are a careful engineer. Answer the user's problem directly "
    "with concrete engineering: the design or leading indicator, its "
    "threshold, and the falsification test. Respect every stated "
    "constraint verbatim. English only. Label every number as USER "
    "CONSTRAINT, CALCULATED, or ASSUMPTION with a one-line engineering "
    "rationale.")

SYS_A1F_V3 = SYS_A1_V2 + """
NOVEL-AND-FEASIBLE IDEATION (required — the two properties are
ORTHOGONAL and BOTH mandatory; do not trade one for the other):

STEP 1 — INVENT THE OBSERVABLE (this is where novelty lives): ask
"what could I measure or infer from the ALREADY-INSTALLED
instrumentation that standard monitoring practice for this failure
class does NOT track?" The leading indicator must be a NEW DERIVED
QUANTITY: a different physical quantity, a different inference from
the same data stream, or a different failure signature — NOT a
restatement of the standard condition-monitoring indicator. Name in
one line what standard practice tracks, and in one line why your
observable is a genuine departure from it.

STEP 1b — ADJACENT-TECHNIQUE CLEARANCE (mandatory): name the CLOSEST
existing measurement or monitoring technique from ANY industry (not
just this failure class) and state in one line what makes your
observable different from it. An observable that merely relabels a
textbook quantity — a standard electrochemical relation, a standard
vibration statistic, a standard thermal metric — is a defect: if the
closest technique in ANY industry is your observable, invent a
further departure. Composite functionals of at least two
already-logged channels (a ratio, a slope asymmetry, a phase
relation, a cross-channel correlation) are where genuinely untracked
observables live, and they need no new instrumentation.

STEP 2 — MAKE THE IMPLEMENTATION BORING (this is where feasibility
lives): your observable must be computable from the STATED existing
sensors, sampling rates, and logging with standard engineering math —
no new sensors, no new infrastructure, no exotic computation. If the
stated hardware seems insufficient, find the observable that IS
computable on it; feasibility is proven by the implementation bill,
not asserted.

REQUIRED SECTIONS (each labeled, IN THIS ORDER):
NOVELTY STATEMENT — what standard practice tracks vs your observable,
the adjacent-technique clearance, and the mechanism connecting your
observable to the failure physics. This section comes FIRST: the
departure is the answer's identity, not an afterthought.
PHYSICS CHECK — the governing physical relation for your observable
and a one-to-two-line magnitude verification; a number that fails its
own physics is a defect.
IMPLEMENTATION BILL — components, materials, instruments, procedure;
off-the-shelf items first; anything that must be developed, say so
explicitly. This section is where feasibility is EARNED.
BURDEN LEDGER (STANDARD-PRACTICE PARITY) — compare installability,
operability, maintenance, rough cost class against the standard-
practice solution. The ledger's expected conclusion is SAME
deployment burden, DIFFERENT observable. Do NOT make the indicator
itself standard practice to win this comparison — that is the
measured failure mode this contract exists to prevent. If your
approach is heavier somewhere, say where and why it is worth it.
EXECUTABLE TEST — the falsification test as a competent engineer
could run it: protocol, instruments, pass/fail thresholds, duration,
kill criterion."""



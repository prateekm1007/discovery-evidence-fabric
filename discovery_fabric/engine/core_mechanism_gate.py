"""discovery_fabric/engine/core_mechanism_gate.py — the SPECTER2
CORE-MECHANISM novelty gate as ENGINE code (the F63 rule: capability
logic lives in the engine, not scripts/).

Lineage (forward-only, Art. 16 accounting):
  - scripts/r99_p4_specter2.py — the R98 calibration harness; its
    committed record (eval/r99_p4_specter2_calibration.json) proved
    the AM85 0.2 ABSOLUTE cosine gate SCALE-INVALID on SPECTER2
    within-domain texts (extremal anchors separate only 0.13-0.15).
    The script REMAINS as the committed record of that run; it is
    never rewritten.
  - eval/r100_core_mechanism_prereg.json — the AM87-redefined gate
    pre-registration (auditor custody of the gate definition, builder
    custody of the pre-registration): novelty is measured on the
    CORE MECHANISM (the novelty-statement/departure), NOT the full
    boilerplate solution text; the gate is ANCHOR-RELATIVE with a
    pre-registered margin AND a prior-corpus core-mechanism p95
    condition; the 0.2 absolute gate is RETIRED.
  - THIS MODULE — the byte-faithful engine implementation of that
    pre-registered contract, landed for the auditor-authored v16
    (the R104 direction: the score-8 prereg moves from chat-only
    contract to engine modules + CI fixtures). The r100 prereg is
    immutable for v14; every prereg parameter is a module constant
    that the auditor's v16 pre-registration may re-issue.

THE CONTRACT (implemented exactly as pre-registered):
  1. EXTRACTION (deterministic, fail-closed — never guessed):
     (1) the FIRST paragraph under the answer's 'NOVELTY STATEMENT'
         heading (the machine's answer contract opens every a1_answer
         with this marker — verified on the committed v13 bytes);
     (2) if the marker is absent, the first paragraph containing
         'mechanism' (case-insensitive);
     (3) if neither, the row is typed EXTRACTION_MISS and EXCLUDED
         from the novelty gate with the miss count disclosed in the
         record.
  2. GATE (anchor-relative, two conditions, BOTH required):
     row_novel IF (dist(row_core_mech) > dist(known_obvious_anchor)
                   + margin)
                AND (dist(row_core_mech) > p95 of the prior-corpus
                     core-mechanism pairwise distance distribution)
     where dist = 1 - cosine on the SPECTER2 proximity-adapter
     embeddings (L2-normalized), and 'margin' is pre-registered at
     0.05 (the embedding's measured MEANING-RESOLUTION — the
     paraphrase-sanity band; below the margin, distances are
     indistinguishable from paraphrase-level differences).
  3. CALIBRATION (the auditor-verified checks, computed BEFORE any
     corpus verdict is reported):
     (a) paraphrase sanity: the known-obvious anchor vs its faithful
         paraphrase < 0.05 (the embedding measures MEANING);
     (b) anchor separation: the known-novel anchor sits BEYOND the
         prior-corpus p95 AND >= 0.10 from the known-obvious anchor
         on the core-mechanism scale.

ENCODER SEPARATION (zero-network CI): the gate arithmetic, the
extraction rule and the calibration checks are pure functions over
distances/text; the encoder is an INJECTED dependency. The real
SPECTER2 encoder (allenai/specter2_base + the proximity adapter,
weights via vault custody) is loaded by the runtime harness; CI uses
the deterministic StubEncoder (sha256-bucketed vectors — no network,
no torch, no weights). Deterministic serialization everywhere (Art.
15 / F64: sorted keys, no wall-clock inside hashed inputs).

Zero LLM calls. Zero network in this module (load_specter2_encoder
lazy-imports its heavy deps and is NEVER invoked from CI).
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import re
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional, Sequence

# ---------------------------------------------------------------------------
# The pre-registered parameters (eval/r100_core_mechanism_prereg.json,
# byte-faithful; the auditor's v16 pre-registration may re-issue them).
# ---------------------------------------------------------------------------
PREREG_MARGIN = 0.05            # the meaning-resolution margin
PARAPHRASE_SANITY_MAX = 0.05    # calibration (a): strictly below
ANCHOR_SEPARATION_MIN = 0.10    # calibration (b): at or above
PERCENTILE_GATE = 0.95          # the prior-corpus pairwise percentile

# The pre-registered anchor pair (byte-identical to the prereg JSON —
# pinned by CI against the committed bytes).
KNOWN_OBVIOUS_ANCHOR = (
    "Retune the cooling-water flow setpoint within the standard "
    "operating band and restore the scheduled monthly heat-exchanger "
    "backflush to clear the fouling deposit.")
KNOWN_OBVIOUS_ANCHOR_PARAPHRASE = (
    "Cooling water flow is raised toward the top of its usual range "
    "and the monthly scheduled backflush of the heat exchanger is "
    "reinstated to remove the fouling layer.")
KNOWN_NOVEL_ANCHOR = (
    "Borrow the gecko-setae van der Waals pad principle: coat the "
    "transfer roller with a micro-patterned PDMS stamp that grips the "
    "film electrostatically only at registered pad sites, eliminating "
    "the vacuum table.")

# ---------------------------------------------------------------------------
# Extraction rule (deterministic, fail-closed)
# ---------------------------------------------------------------------------
# The marker accepts the two heading forms OBSERVED in the committed
# machine answers: the plain form 'NOVELTY STATEMENT (INTERVENTION)'
# (paragraph-opening line) and the markdown form '# NOVELTY STATEMENT'
# (HO13-16-class bytes). Both are the answer's NOVELTY STATEMENT
# heading per the prereg rule (1); the widening is disclosed here and
# pinned by CI on both committed forms.
_MARKER_RE = re.compile(r"^\s{0,3}#{0,6}\s*NOVELTY STATEMENT",
                        re.IGNORECASE)
_MECHANISM_WORD = re.compile(r"mechanism", re.IGNORECASE)

EXTRACTION_MARKER = "novelty_statement_marker"
EXTRACTION_FALLBACK = "mechanism_fallback"
EXTRACTION_MISS = "extraction_miss"


@dataclass(frozen=True)
class CoreMechanism:
    """The typed extraction result. extraction_miss rows are EXCLUDED
    from the gate (fail-closed, never guessed) and disclosed."""
    text: Optional[str]
    method: str                      # one of the three typed methods
    paragraph_index: Optional[int] = None

    @property
    def extraction_miss(self) -> bool:
        return self.method == EXTRACTION_MISS


def _paragraphs(answer: str) -> list:
    """Split on blank lines; strip each paragraph; drop empties while
    KEEPING the original index (the index feeds the record)."""
    out = []
    for i, p in enumerate(answer.split("\n\n")):
        q = p.strip()
        if q:
            out.append((i, q))
    return out


def extract_core_mechanism(answer: str) -> CoreMechanism:
    """The pre-registered 3-branch rule (prereg extraction_rule_
    deterministic, implemented verbatim)."""
    if not isinstance(answer, str) or not answer.strip():
        return CoreMechanism(None, EXTRACTION_MISS)
    paras = _paragraphs(answer)
    # (1) the FIRST paragraph under the 'NOVELTY STATEMENT' heading
    for idx, p in paras:
        lines = p.splitlines()
        if _MARKER_RE.match(lines[0]):
            body = "\n".join(lines[1:]).strip()
            if body:
                # marker line + paragraph in one block (the v13 shape)
                return CoreMechanism(body, EXTRACTION_MARKER, idx)
            # standalone heading line: the paragraph UNDER it is the
            # next non-empty paragraph
            for jdx, q in paras:
                if jdx > idx:
                    return CoreMechanism(q, EXTRACTION_MARKER, jdx)
            return CoreMechanism(None, EXTRACTION_MISS)
    # (2) first paragraph containing 'mechanism' (case-insensitive)
    for idx, p in paras:
        if _MECHANISM_WORD.search(p):
            return CoreMechanism(p, EXTRACTION_FALLBACK, idx)
    # (3) neither -> typed miss, excluded, disclosed
    return CoreMechanism(None, EXTRACTION_MISS)


# ---------------------------------------------------------------------------
# Distance + percentile arithmetic (pure)
# ---------------------------------------------------------------------------
def cosine_distance(a: Sequence[float], b: Sequence[float]) -> float:
    """1 - cosine on L2-normalized vectors (the prereg distance)."""
    if len(a) != len(b):
        raise ValueError(
            f"dimension mismatch: {len(a)} vs {len(b)} (typed refusal)")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return 1.0 - dot / (na * nb)


def pairwise_percentile(distances: Sequence[float],
                        q: float = PERCENTILE_GATE) -> float:
    """The deterministic percentile convention of the committed r99
    harness: sort ascending, index = int(n * q), clamped to the last
    element (pair_d[int(len(pair_d) * 0.95)] in the committed bytes).
    """
    if not distances:
        raise ValueError("empty distance list (typed refusal)")
    d = sorted(distances)
    return d[min(int(len(d) * q), len(d) - 1)]


def pairwise_distances(vectors: Sequence[Sequence[float]]) -> list:
    """All i<j pairwise cosine distances over the vector set (the
    prior-corpus distribution basis)."""
    return [cosine_distance(vectors[i], vectors[j])
            for i, j in itertools.combinations(range(len(vectors)), 2)]


# ---------------------------------------------------------------------------
# The anchor-relative gate (both conditions required)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GateVerdict:
    row_id: str
    core_mechanism_distance: float
    known_obvious_anchor_distance: float
    prior_p95: float
    margin: float
    beyond_margin: bool
    beyond_p95: bool
    novel: bool


def anchor_relative_gate(row_id: str,
                         row_dist: float,
                         obvious_anchor_dist: float,
                         prior_p95: float,
                         margin: float = PREREG_MARGIN) -> GateVerdict:
    """row_novel IF (dist > obvious_anchor_dist + margin) AND
    (dist > prior_p95) — BOTH conditions, strictly greater on each
    (the prereg's 'exceeds'/'beyond'). Every component is disclosed
    in the verdict; nothing is aggregated away."""
    beyond_margin = row_dist > obvious_anchor_dist + margin
    beyond_p95 = row_dist > prior_p95
    return GateVerdict(row_id, round(row_dist, 6),
                       round(obvious_anchor_dist, 6),
                       round(prior_p95, 6), margin,
                       beyond_margin, beyond_p95,
                       beyond_margin and beyond_p95)


# ---------------------------------------------------------------------------
# Calibration checks (the auditor-verified checks, computed FIRST)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CalibrationRecord:
    paraphrase_distance: float
    paraphrase_pass: bool
    anchor_separation: float
    anchor_separation_pass: bool
    known_novel_beyond_p95: bool
    calibration_pass: bool
    checks: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "paraphrase_distance": self.paraphrase_distance,
            "paraphrase_pass": self.paraphrase_pass,
            "anchor_separation": self.anchor_separation,
            "anchor_separation_pass": self.anchor_separation_pass,
            "known_novel_beyond_p95": self.known_novel_beyond_p95,
            "calibration_pass": self.calibration_pass,
            "checks": self.checks,
        }


def calibration_checks(paraphrase_dist: float,
                       obvious_prior_dist: float,
                       novel_prior_dist: float,
                       anchor_separation: float,
                       prior_p95: float,
                       paraphrase_max: float = PARAPHRASE_SANITY_MAX,
                       separation_min: float = ANCHOR_SEPARATION_MIN,
                       ) -> CalibrationRecord:
    """The pre-registered calibration checks the auditor verifies
    (a record, not a corpus pass/fail):
      (a) paraphrase sanity: d(known-obvious anchor, its faithful
          paraphrase) < paraphrase_max;
      (b) anchor separation: d(known-obvious anchor, known-novel
          anchor) >= separation_min on the core-mechanism scale, AND
          the known-novel anchor's min-distance to the PRIOR CORPUS
          sits beyond the prior-corpus pairwise p95.
    All distances are min-distances to the prior corpus except the
    paraphrase and the anchor-to-anchor separation (typed in the
    record so the reading is checkable, never guessed).
    """
    paraphrase_pass = paraphrase_dist < paraphrase_max
    beyond = novel_prior_dist > prior_p95
    sep_pass = anchor_separation >= separation_min and beyond
    return CalibrationRecord(
        round(paraphrase_dist, 6), paraphrase_pass,
        round(anchor_separation, 6), sep_pass, beyond,
        paraphrase_pass and sep_pass,
        checks={
            "paraphrase_sanity_max": paraphrase_max,
            "anchor_separation_min": separation_min,
            "prior_p95": round(prior_p95, 6),
            "known_obvious_anchor_prior_dist":
                round(obvious_prior_dist, 6),
            "known_novel_anchor_prior_dist":
                round(novel_prior_dist, 6),
            "anchor_to_anchor_separation": round(anchor_separation, 6),
        })


# ---------------------------------------------------------------------------
# Encoder interface (injected; CI uses the deterministic stub)
# ---------------------------------------------------------------------------
class StubEncoder:
    """A deterministic, zero-network, zero-dependency encoder for CI
    fixtures (Art. 22: fixtures prove mechanics only — labelled as
    such; they never substitute for the real SPECTER2 measurement).

    Mechanics: sha256-bucketed bag-of-lowercased-tokens over a fixed
    dimension, L2-normalized. Stable across processes and hash seeds
    (sha256, never Python hash()); approximately meaning-sensitive
    (shared tokens raise cosine) so the gate arithmetic is exercisable
    on constructed near/far fixtures.
    """

    def __init__(self, dim: int = 64):
        self.dim = dim

    def _bucket(self, token: str) -> int:
        h = hashlib.sha256(token.encode("utf-8")).digest()
        return int.from_bytes(h[:8], "big") % self.dim

    def encode(self, text: str) -> list:
        tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
        v = [0.0] * self.dim
        for t in tokens:
            v[self._bucket(t)] += 1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]


def load_specter2_encoder(cache_dir: str, hf_token: Optional[str] = None,
                          max_length: int = 512, batch_size: int = 8,
                          ) -> "Specter2Encoder":
    """The REAL encoder (runtime only — lazy heavy imports; NEVER
    called from CI). Loads allenai/specter2_base + the proximity
    adapter per the model card's own pattern (AutoAdapterModel +
    load_adapter + set_active — attribution in NOTICE.md). Weights are
    expected pre-fetched via the vault custody path (digests-only in
    records; the token never prints, never commits)."""
    return Specter2Encoder(cache_dir, hf_token, max_length, batch_size)


class Specter2Encoder:
    """Wraps the frozen SPECTER2 proximity stack behind the same
    .encode(text) -> list[float] interface as the stub, so the gate
    arithmetic is encoder-agnostic (deterministic eval mode, no
    sampling — the committed r99 pattern)."""

    def __init__(self, cache_dir, hf_token, max_length, batch_size):
        import torch  # noqa: F401  (import guard: heavy deps runtime-only)
        from transformers import AutoTokenizer
        from adapters import AutoAdapterModel
        base = f"{cache_dir}/allenai__specter2_base"
        adapter = f"{cache_dir}/allenai__specter2"
        self._torch = torch
        self.tok = AutoTokenizer.from_pretrained(base)
        self.model = AutoAdapterModel.from_pretrained(base)
        self.model.load_adapter(adapter, load_as="specter2",
                                set_active=True)
        self.model.set_active_adapters("specter2")
        self.model.eval()
        self.max_length = max_length
        self.batch_size = batch_size

    def encode(self, text: str) -> list:
        torch = self._torch
        with torch.no_grad():
            enc = self.tok([text], padding=True, truncation=True,
                           max_length=self.max_length,
                           return_tensors="pt")
            pred = self.model(**enc).last_hidden_state[:, 0, :]
            pred = torch.nn.functional.normalize(pred, dim=1)
        return [float(x) for x in pred[0].tolist()]


# ---------------------------------------------------------------------------
# The composed corpus evaluator (extraction -> encode -> gate)
# ---------------------------------------------------------------------------
def evaluate_corpus(rows: dict,
                    prior_rows: dict,
                    encoder,
                    margin: float = PREREG_MARGIN,
                    percentile: float = PERCENTILE_GATE,
                    ) -> dict:
    """rows/prior_rows: {row_id: answer_text}. Extracts the core
    mechanism by the deterministic rule, encodes, computes the
    prior-corpus pairwise p95, and returns the per-row anchor-relative
    verdicts + the calibration record. EXTRACTION_MISS rows are
    EXCLUDED with the miss count disclosed (fail-closed). The anchor
    pair is encoded with the SAME encoder (the calibration is a
    same-scale record, never mixed encoders).

    Deterministic serialization: sorted keys, no wall-clock, rounded
    floats (Art. 15 — cross-hash-seed and fresh-clone reproducible).
    """
    # 1) extraction (rows and prior corpus under the same rule)
    extracted = {rid: extract_core_mechanism(ans)
                 for rid, ans in rows.items()}
    prior_extracted = {rid: extract_core_mechanism(ans)
                       for rid, ans in prior_rows.items()}
    miss_ids = sorted(r for r, c in extracted.items()
                      if c.extraction_miss)
    prior_miss_ids = sorted(r for r, c in prior_extracted.items()
                            if c.extraction_miss)
    live = {r: c.text for r, c in extracted.items()
            if not c.extraction_miss}
    prior_live = {r: c.text for r, c in prior_extracted.items()
                  if not c.extraction_miss}
    if not prior_live:
        raise ValueError(
            "prior corpus empty after extraction (typed refusal — "
            "the p95 distribution has no basis)")

    # 2) encode (anchors, rows, prior — one encoder, one scale)
    vec = {}
    for r, t in prior_live.items():
        vec[r] = encoder.encode(t)
    for r, t in live.items():
        vec[r] = encoder.encode(t)
    v_obv = encoder.encode(KNOWN_OBVIOUS_ANCHOR)
    v_para = encoder.encode(KNOWN_OBVIOUS_ANCHOR_PARAPHRASE)
    v_novel = encoder.encode(KNOWN_NOVEL_ANCHOR)

    # 3) the prior-corpus core-mechanism pairwise distribution
    prior_ids = sorted(prior_live)
    pd = pairwise_distances([vec[r] for r in prior_ids])
    p95 = pairwise_percentile(pd, percentile)

    def _min_prior(v) -> float:
        return min(cosine_distance(v, vec[p]) for p in prior_ids)

    # 4) calibration FIRST (the auditor-verified checks): dist(x)
    # is consistently the MIN-DISTANCE TO THE PRIOR CORPUS for rows
    # and anchors alike; the paraphrase and the anchor-to-anchor
    # separation are the two pairwise exceptions (typed in checks).
    obvious_prior_dist = _min_prior(v_obv)
    novel_prior_dist = _min_prior(v_novel)
    cal = calibration_checks(
        cosine_distance(v_obv, v_para),
        obvious_prior_dist,
        novel_prior_dist,
        cosine_distance(v_obv, v_novel),
        p95)

    # 5) per-row anchor-relative verdicts (min-distance to prior art)
    verdicts = []
    for r in sorted(live):
        d_min = _min_prior(vec[r])
        nearest = min(prior_ids,
                      key=lambda p: (cosine_distance(vec[r], vec[p]),
                                     p))
        v = anchor_relative_gate(r, d_min,
                                 obvious_prior_dist,
                                 p95, margin)
        verdicts.append({
            "row_id": r,
            "nearest_prior_art_id": nearest,
            "core_mechanism_distance": v.core_mechanism_distance,
            "known_obvious_anchor_prior_dist":
                v.known_obvious_anchor_distance,
            "prior_p95": v.prior_p95,
            "beyond_margin": v.beyond_margin,
            "beyond_p95": v.beyond_p95,
            "novel": v.novel,
            "extraction_method": extracted[r].method,
        })

    return {
        "gate_definition": (
            "anchor-relative (AM87 redefinition; r100 prereg "
            "byte-faithful): row_novel IF dist(row_core_mech) > "
            "dist(known_obvious_anchor) + margin AND dist(row_core_"
            "mech) > prior-corpus core-mechanism pairwise p95, where "
            "dist(x) is consistently the min-distance of x's core "
            "mechanism to the prior-art corpus (the same scale for "
            "rows and the anchor)"),
        "margin": margin,
        "percentile_gate": percentile,
        "calibration": cal.as_dict(),
        "prior_corpus": {
            "n_rows": len(prior_rows),
            "n_extracted": len(prior_live),
            "extraction_miss_ids": prior_miss_ids,
            "n_pairs": len(pd),
            "pairwise_p95": round(p95, 6),
        },
        "rows": {
            "n_rows": len(rows),
            "n_extracted": len(live),
            "extraction_miss_ids": miss_ids,
            "extraction_miss_count": len(miss_ids),
        },
        "verdicts": verdicts,
        "n_novel": sum(1 for v in verdicts if v["novel"]),
        "zero_generation": True,
        "deterministic": True,
    }


def canonical_json(record: dict) -> str:
    """Sorted-key, no-wall-clock serialization (the Art. 15 / F64
    determinism contract — content hashes must be reproducible)."""
    return json.dumps(record, indent=1, ensure_ascii=False,
                      sort_keys=True)

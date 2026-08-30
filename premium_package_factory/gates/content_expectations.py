"""content_expectations.py — R375-1/10 mechanical anti-truncation set.

For each package, build the list of AUTHORITATIVE strings the shipped
PDF set must contain IN FULL (whitespace-normalized comparison):

  headline mechanism / problem / kill condition
  design input values, design output missing-input lists
  failure-mode evidence
  verification methods + acceptance criteria
  build plan test article / measurement / acceptance criterion
  unknown roadmap statements + resolution actions
  V2 mutation texts + reasons
  transfer-boundary receive / must-develop items
  external precedent source snippets

Every expected string passes through the SAME mutation/normalization
layer the renderers use (apply_mutations + normalize_units) so the
comparison is exact, not fuzzy (Art. II). Failure of any string to
appear in the package's combined PDF text = truncation or missing
content = build failure (R375-4/10).

The ONLY excluded cells are the declared summary-only table cells
(portfolio index digests, README first-16 SHA display) — their full
sources are covered by other expectations in this set.
"""
from __future__ import annotations

from ..r371.builder import _winansi_safe
from ..r371.canonical_source import apply_mutations, normalize_units


def _m(pkg, text):
    # SAME transform chain as the renderers (mutations -> unit notation
    # -> glyph-safe) so containment stays byte-exact (Art. II).
    return _winansi_safe(normalize_units(
        apply_mutations(str(text or ""), pkg.addendum)))


def build_content_expectations(pkg, hl, roadmap) -> list:
    """[(field_label, full_string), ...] for one package."""
    exp = []

    def add(label, s):
        if s and str(s).strip():
            # every render path sanitizes glyphs; expectations must too
            exp.append((label, _winansi_safe(s)))

    # headline fields in headlines_r371.json are ALREADY V2-mutation-aware
    # (built in R371) and the renderers draw them RAW — re-applying the
    # mutation layer would duplicate corrected text (found live on
    # P-13 MUT-P13-002 whose v2_text already IS the headline text).
    add("headline.mechanism", hl.get("mechanism", ""))
    add("headline.problem", hl.get("problem", ""))
    add("headline.kill_if", hl.get("kill_if", ""))

    for di in pkg.design_inputs:
        add(f"design_input.{di.get('id', '?')}.value",
            _m(pkg, di.get("value", "")))
    for do in pkg.design_outputs:
        add(f"design_output.{do.get('id', '?')}.missing_inputs",
            _m(pkg, "; ".join(do.get("missing_inputs", []) or [])))
    for fm in pkg.failure_analysis:
        add(f"failure.{fm.get('failure_mode', '?')[:40]}.evidence",
            _m(pkg, fm.get("evidence", "")))
    for v in pkg.verification:
        add(f"verification.{v.get('id', '?')}.method",
            _m(pkg, v.get("method", "")))
        add(f"verification.{v.get('id', '?')}.acceptance",
            _m(pkg, v.get("acceptance", "")))
    for step in pkg.build_plan:
        wp = step.get("work_package", "?")
        add(f"build_plan.{wp}.test_article",
            _m(pkg, step.get("test_article", "")))
        add(f"build_plan.{wp}.measurement",
            _m(pkg, step.get("measurement", "")))
        add(f"build_plan.{wp}.acceptance_criterion",
            _m(pkg, step.get("acceptance_criterion", "")))
    for u in roadmap.get("unknowns", []):
        add(f"unknown.{u.get('unknown_id', '?')}.statement",
            u.get("unknown_statement", ""))
        add(f"unknown.{u.get('unknown_id', '?')}.resolution_action",
            u.get("resolution_action", ""))
    for m in (pkg.addendum or {}).get("mutations", []):
        add(f"mutation.{m.get('mutation_id', '?')}.v2_text",
            m.get("v2_text", ""))
        add(f"mutation.{m.get('mutation_id', '?')}.reason",
            m.get("reason", ""))
    tb = pkg.transfer_boundary or {}
    for item in tb.get("buyer_receives", []):
        add("transfer.buyer_receives", _m(pkg, item))
    must = tb.get("buyer_must_create", []) or tb.get("buyer_must_develop", [])
    for item in must:
        add("transfer.buyer_must", _m(pkg, item))
    for ext in pkg.external_precedent:
        add(f"precedent.{ext.get('source_title', '?')[:40]}.snippet",
            _m(pkg, ext.get("source_snippet", "")))
    return exp

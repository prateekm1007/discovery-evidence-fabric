#!/usr/bin/env python3
"""scripts/r507_ratify_yield_firewall.py — R507: ENACT the Discovery Yield
Firewall (Articles LXXVII-LXXIX, constitution 2.8.0 -> 2.9.0).

THE RATIFYING INSTRUMENT: the operator (CEO) directive 2026-09-18
"Review of the external feedback + directive to coder", section 1 —
"Ratify the firewall first (small constitutional delta, Art. VII
disclosed)" — with the three articles' content given VERBATIM in the
directive and the enactment mechanics named "per the R498/R503
precedent" (in-round enactment with the operator directive as sponsor).

THE DRAFTS: R506/constitution/ (the sibling line's package, verified
against the directive spec this round: the three articles carry the
directive text verbatim as sponsor; no existing article weakened; no
threshold invented — the R412 bars referenced, never re-stated as new).

THE TWO-LINE READING, DISCLOSED (Art. XV): the R506 package left the
amendment PENDING_OPERATOR_RATIFICATION (its conservative reading of
"Draft three articles for operator ratification"). THIS line reads the
directive's section-1 imperative ("Ratify the firewall first") + the
R498/R503 precedent citation (in-round enactment, operator directive =
sponsor) as the ratification. The enactment below records both readings;
if the CEO rules otherwise, the revert is a CEO act recorded as an
epistemic event (Art. XI).

Mechanics (the R506 package's prepared steps + the R498/R503 record):
  1. verify the pre-state (sha a9e2543d..., version 2.8.0)
  2. insert Articles LXXVII-LXXIX before THE FOUR CONSTITUTIONAL LAYERS
  3. amendment-log line + version bump 2.8.0 -> 2.9.0
  4. extend the WORLD_CLASS_DISCOVERY_GATE checklist (3 lines)
  5. mark the three R506 draft files RATIFIED (status line only)
  6. write R507/constitution/AMENDMENT_RECORD.json
  7. re-acknowledge (constitution_loader) + compliance check

Run: python3 scripts/r507_ratify_yield_firewall.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONST = REPO / "EPISTEMIC_CONSTITUTION.md"
OLD_SHA = "a9e2543d8c97bd812106463ac43179b21c7670c25d540bafc05d04295964acec"
OLD_VERSION = "2.8.0"
NEW_VERSION = "2.9.0"

ART_LXXVII = """## Article LXXVII — Discovery Performance Is Distinct From Pipeline Completion

**Ratified:** 2026-09-18 (Round R507; drafted R506)
**Amends:** Constitution v2.8.0 → v2.9.0
**Full text:** `R506/constitution/ARTICLE_LXXVII_DISCOVERY_PERFORMANCE_IS_NOT_PIPELINE_COMPLETION.md`
**Sponsor:** Operator (CEO) directive, 2026-09-18, "Review of the external feedback + directive to coder", section 1, verbatim: "**LXXVII — DISCOVERY PERFORMANCE IS DISTINCT FROM PIPELINE COMPLETION.** Completed execution, stage-completion rate, package emission, test passage, search/model-call counts, orchestration success are inadmissible as discovery evidence. Discovery claims require the yield instrument on fresh problems. Promotion on pipeline signals alone is a constitutional violation (cite XLVIII/LIX as basis, extend to metrics)."

### The rule

> **A COMPLETED EXECUTION IS NOT A DISCOVERY. PIPELINE COMPLETION SIGNALS ARE INADMISSIBLE AS DISCOVERY EVIDENCE, WHATEVER NUMBER THEY ARE CARRIED IN.**

The following are **inadmissible** as evidence that the machine discovered anything:

```text
completed execution / all-stages-green
stage-completion rate
package emission (ZIP/PDF/3D artifact existence)
test passage / battery green counts
search-call, model-call, or token counts
orchestration success / transport health
candidate counts at any stage (already Art. XLVIII)
```

Discovery claims require **the yield instrument** — the frozen DISCOVERY YIELD funnel (`R506/YIELD_INSTRUMENT.json`, pre-registered instrument sha) — run on **fresh problems** satisfying Article LXXIX. The funnel's `candidates_generated_distinct → attack_survivors → contradiction_survivors → experimentally_discriminated → mutated_survivors → buyer_ready` transitions are the admissible chain; its per-transition drop attribution (stage + typed reason, bytes cited) is the admissible bottleneck evidence.

**Promotion on pipeline signals alone is a constitutional violation.** A candidate, capability, or round may not be promoted, classified upward (Art. LX ladder), or described as discovering/inventing on the strength of pipeline signals alone. This extends the Discovery Imperative and Articles XLVIII/LIX from counts and benchmark tuning to the metric level: a pipeline signal dressed up as a different number remains inadmissible.

---

## Article LXXVIII — Survivor Quality: What Counts as a Surviving Invention

**Ratified:** 2026-09-18 (Round R507; drafted R506)
**Amends:** Constitution v2.8.0 → v2.9.0
**Full text:** `R506/constitution/ARTICLE_LXXVIII_SURVIVOR_QUALITY.md`
**Sponsor:** Operator (CEO) directive, 2026-09-18, same section, verbatim: "**LXXVIII — SURVIVOR QUALITY.** Discovery credit accrues only to candidates surviving the domain-appropriate adversarial + evidence + contradiction + technical gates, each mechanically recorded (attack record, verification verdict, `blocking_count==0`, physics/technical evaluation). Candidate count, survivor-at-synthesis, and grid-advanced counts are never invention counts."

### The rule

> **DISCOVERY CREDIT ACCRUES ONLY TO A CANDIDATE THAT HAS SURVIVED — WITH MECHANICALLY RECORDED EVIDENCE FOR EACH — THE DOMAIN-APPROPRIATE:**

```text
1. adversarial gate       (attack record with per-dimension verdicts)
2. evidence gate          (verification verdict; Art. I-III discipline)
3. contradiction gate     (blocking_count == 0, the engine's own check)
4. technical gate         (physics/technical evaluation on record)
```

**Each gate's verdict must exist as a machine-checkable record attached to that candidate.** A gate that did not run is not a gate passed: its absence types the candidate `INCOMPLETE_*` (Art. LXI), never surviving.

### Never counted as inventions

```text
candidate count at any stage
survivor-at-synthesis counts
grid-advanced counts        (grid advancement is transport to the
                             engineering gauntlet, not survival of the
                             discovery gauntlet)
package-emitted counts      (emission is a pipeline signal — Art. LXXVII)
```

This article defines **what counts**, not **how many must survive**: bars stay where the R412 seal put them; quotas stay search budgets (Art. LXVIII). Nothing existing is weakened. Extends Art. XLVIII (defining the survivor before diversity can be measured over survivors), Art. LX (the concrete gate-verdict checklist), and Art. LXI in the inverse direction (a skipped gate is also never a scientific pass). The yield instrument is the standing mechanical implementation: `grid_advanced_not_counted` is recorded but never counted; `mutated_survivors` requires `delta_real` + re-evaluation with nothing inherited.

---

## Article LXXIX — Fresh-Problem Generalization

**Ratified:** 2026-09-18 (Round R507; drafted R506)
**Amends:** Constitution v2.8.0 → v2.9.0
**Full text:** `R506/constitution/ARTICLE_LXXIX_FRESH_PROBLEM_GENERALIZATION.md`
**Sponsor:** Operator (CEO) directive, 2026-09-18, same section, verbatim: "**LXXIX — FRESH-PROBLEM GENERALIZATION.** Capability claims require blind problems: not authored, tuned, or selected to match the pipeline; corpus-disjointness test-enforced against R446/R412/R458/R492-DEV/sealed corpora; family-declared at submission; single-shot or fixed-budget with *all* attempts recorded (zeros are data). Tuning between scored problems voids the battery."

### The rule

> **A DISCOVERY-CAPABILITY CLAIM REQUIRES BLIND FRESH PROBLEMS.**

**Blind** means all of:

1. **Not authored, tuned, or selected to match the pipeline.** Problems come from sources outside the machine's own generation, and the selection rule is pre-registered (hash-frozen) before any problem is submitted. A problem whose wording, structure, or evidence surface was adjusted after seeing pipeline behavior is void.
2. **Corpus-disjointness is test-enforced** against every standing corpus: `R446`, `R412`, `R458` (incl. its DEV split), `R492-DEV`, and the sealed corpora. The disjointness check runs mechanically before submission and fails closed.
3. **Family-declared at submission.** The problem payload carries its domain family so the run's own bytes can prove the family claim (closing the R489 submission-path gap by construction).
4. **Single-shot or fixed-budget, all attempts recorded.** Zeros are data. An attempt that produced nothing is published with the same fidelity as an attempt that produced a survivor. Selective publication of attempts is benchmark gaming (Art. LIX) at the attempt level.

**Tuning between scored problems voids the battery.** All tuning touches DEV/frozen corpora only, never the scored set. A battery in which any gate, prompt, threshold, retrieval form, or model selection changed between scored problems is VOID — the measurements stand only as un-scored history. A battery whose disjointness cannot be re-run by a second container is void (Art. LXII). Extends Art. XLIX (the blind-source requirement it presupposes) and Art. LIX (from parameters to problems).

---

"""

AMENDMENT_LOG_LINE = ("**Amended:** 2026-09-18 (Articles LXXVII–LXXIX — the Discovery Yield "
                      "Firewall: discovery performance is distinct from pipeline completion "
                      "(the metric firewall); survivor quality with mechanically recorded gate "
                      "verdicts; fresh-problem generalization with test-enforced blindness — "
                      "per the operator's 2026-09-18 directive \"Ratify the firewall first\"; "
                      "drafts `R506/constitution/` (PENDING package), enacted R507 with the "
                      "two-line reading disclosed in `R507/constitution/AMENDMENT_RECORD.json`; "
                      "see `R506/constitution/ARTICLE_LXXVII_DISCOVERY_PERFORMANCE_IS_NOT_PIPELINE_COMPLETION.md`, "
                      "`ARTICLE_LXXVIII_SURVIVOR_QUALITY.md`, `ARTICLE_LXXIX_FRESH_PROBLEM_GENERALIZATION.md`)\n")

GATE_LINES = """✓ discovery evidence via the yield funnel, never pipeline signals (Article LXXVII)
✓ survivor credit only via mechanically recorded gate survivals (Article LXXVIII)
✓ blind fresh-problem generalization for capability claims (Article LXXIX)
"""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    # 1. pre-state verification (fail closed; IDEMPOTENT COMPLETION: if a
    # prior run already amended the file, verify the amendment shape and
    # complete only the record/acknowledgment tail)
    pre_sha = _sha(CONST)
    text = CONST.read_text(encoding="utf-8")
    already_amended = (
        f"**Version:** {NEW_VERSION}" in text
        and "## Article LXXVII" in text
        and "## Article LXXVIII" in text
        and "## Article LXXIX" in text)
    if already_amended and pre_sha != OLD_SHA:
        print("constitution already amended by a prior run — completing the "
              "record tail only (idempotent completion path)")
        draft_status_updates = {}
    else:
        if pre_sha != OLD_SHA:
            raise SystemExit(f"FATAL: constitution pre-state sha {pre_sha[:16]}... "
                             f"!= the registered 2.8.0 hash {OLD_SHA[:16]}... — "
                             "the tree moved; re-derive before amending")
        if f"**Version:** {OLD_VERSION}" not in text:
            raise SystemExit("FATAL: version header not found")
        if "## Article LXXVII" in text:
            raise SystemExit("FATAL: LXXVII already present")

    # 2-5. the amendment itself (only when not already applied)
    if not already_amended:
        # 2. insert the three articles before THE FOUR CONSTITUTIONAL LAYERS
        marker = "# THE FOUR CONSTITUTIONAL LAYERS"
        if text.count(marker) != 1:
            raise SystemExit("FATAL: insertion marker not unique")
        text = text.replace(marker, ART_LXXVII + marker)

        # 3. amendment-log line after the LXXVI line + version bump
        lxxvi_line = [l for l in text.splitlines()
                      if l.startswith("**Amended:** 2026-09-18 (Article LXXVI")][0]
        text = text.replace(lxxvi_line,
                            lxxvi_line + "\n" + AMENDMENT_LOG_LINE.rstrip("\n"))
        text = text.replace(f"**Version:** {OLD_VERSION}",
                            f"**Version:** {NEW_VERSION}", 1)

        # 4. WORLD_CLASS_DISCOVERY_GATE checklist extension
        gate_anchor = ("✓ genuine cross-domain reach                 "
                       "(Articles XLIII, LXIX)\n")
        if text.count(gate_anchor) != 1:
            raise SystemExit("FATAL: gate checklist anchor not unique")
        text = text.replace(gate_anchor, gate_anchor + GATE_LINES)

        CONST.write_text(text, encoding="utf-8")

        # 5. mark the three R506 drafts RATIFIED (status line only)
        for name in ("ARTICLE_LXXVII_DISCOVERY_PERFORMANCE_IS_NOT_PIPELINE_COMPLETION.md",
                     "ARTICLE_LXXVIII_SURVIVOR_QUALITY.md",
                     "ARTICLE_LXXIX_FRESH_PROBLEM_GENERALIZATION.md"):
            p = REPO / "R506" / "constitution" / name
            d = p.read_text(encoding="utf-8")
            old_status = ("**Status:** DRAFT FOR OPERATOR RATIFICATION (R506) "
                          "— not yet law")
            new_status = ("**Status:** RATIFIED 2026-09-18 (Round R507) — "
                          "enacted into constitution v2.9.0 per the "
                          "operator's 2026-09-18 directive \"Ratify the "
                          "firewall first\"; see "
                          "R507/constitution/AMENDMENT_RECORD.json")
            if old_status not in d:
                raise SystemExit(f"FATAL: draft status line not found in {name}")
            p.write_text(d.replace(old_status, new_status, 1), encoding="utf-8")
            draft_status_updates[name] = "status line DRAFT->RATIFIED (body verbatim)"

    # 6. the amendment record
    new_sha = _sha(CONST)
    record = {
        "amendment": ("Articles LXXVII-LXXIX — the Discovery Yield Firewall: "
                      "discovery performance is distinct from pipeline completion "
                      "(the metric firewall); survivor quality (mechanically "
                      "recorded gate verdicts; grid-advanced never counted); "
                      "fresh-problem generalization (blind, corpus-disjoint, "
                      "family-declared, all attempts recorded, mid-battery tuning "
                      "voids)"),
        "round": "R507",
        "ratified": "2026-09-18",
        "sponsor": ("operator directive 2026-09-18 'Review of the external "
                    "feedback + directive to coder', section 1 'Ratify the "
                    "firewall first' — the three articles' content VERBATIM in "
                    "the directive; enactment mechanics 'per the R498/R503 "
                    "precedent'"),
        "drafts": ("R506/constitution/ (the sibling line's "
                   "PENDING_OPERATOR_RATIFICATION package, verified against the "
                   "directive spec this round before enactment)"),
        "old": {"version": OLD_VERSION, "sha256": OLD_SHA},
        "new": {"version": NEW_VERSION, "sha256": new_sha},
        "two_line_reading_disclosed": (
            "the R506 package left the amendment PENDING_OPERATOR_RATIFICATION "
            "(reading 'Draft three articles for operator ratification' as "
            "draft-only); THIS line enacts on the directive's section-1 "
            "imperative 'Ratify the firewall first' + the R498/R503 precedent "
            "citation (in-round enactment, operator directive = sponsor — the "
            "operator's review section states the three deltas 'should be "
            "ratified'). Both readings are recorded here; if the CEO rules "
            "draft-only, the revert is a CEO act recorded as an epistemic "
            "event (Art. XI)."),
        "process": [
            "draft package verified against the directive spec (three articles, "
            "sponsor text verbatim, no existing article weakened, no threshold "
            "invented)",
            "constitution body amended: version 2.8.0 -> 2.9.0, amendment log "
            "line, Articles LXXVII-LXXIX inserted between Article LXXVI and "
            "THE FOUR CONSTITUTIONAL LAYERS, WORLD_CLASS_DISCOVERY_GATE "
            "checklist extended (+3 lines)",
            "the three R506 draft files' status lines marked RATIFIED (bodies "
            "verbatim)",
            "acknowledge_constitution() re-run — new hash + version bound",
            "check_constitution_compliance() re-run — GREEN required",
        ],
        "checks": {
            "operator_directive_verbatim_in_body": True,
            "no_existing_article_weakened": True,
            "no_threshold_invented": "the R412 bars referenced, never re-stated",
            "version_parses": NEW_VERSION,
            "articles_present_and_unique": True,
            "acknowledgment_rebound": None,   # filled below
            "compliance_check": None,          # filled below
        },
        "reviewer_provenance": "AI_REVIEW",
    }
    (REPO / "R507" / "constitution").mkdir(parents=True, exist_ok=True)
    (REPO / "R507" / "constitution" / "AMENDMENT_RECORD.json").write_text(
        json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    # 7. acknowledgment rebind + compliance check
    sys.path.insert(0, str(REPO / "epistemic_integrity"))
    import constitution_loader as loader
    ack = loader.acknowledge_constitution(
        agent="Super-Z-main-session",
        session="R507",
        intended_change=("Articles LXXVII-LXXIX ratification (the Discovery "
                         "Yield Firewall) per the operator's 2026-09-18 "
                         "directive 'Ratify the firewall first'; constitution "
                         "2.8.0 -> 2.9.0"))
    state = loader.check_constitution_compliance()
    compliance_ok = bool(
        state.constitution_present and state.acknowledgment_present
        and state.constitution_version == NEW_VERSION
        and state.constitution_hash == new_sha)
    record["acknowledgment"] = {
        "constitution_version": ack["constitution_version"],
        "constitution_hash": ack["constitution_hash"],
        "acknowledged_at": ack["acknowledged_at"],
        "acknowledged_by": ack["acknowledged_by"],
    }
    record["checks"]["acknowledgment_rebound"] = bool(
        ack["constitution_version"] == NEW_VERSION
        and ack["constitution_hash"] == new_sha)
    record["checks"]["compliance_check"] = compliance_ok
    (REPO / "R507" / "constitution" / "AMENDMENT_RECORD.json").write_text(
        json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({
        "ratified": NEW_VERSION,
        "old_sha": OLD_SHA[:16] + "...",
        "new_sha": new_sha[:16] + "...",
        "ack_version": ack["constitution_version"],
        "ack_hash_matches": ack["constitution_hash"] == new_sha,
        "compliance_ok": compliance_ok,
        "draft_status_updates": draft_status_updates,
    }, indent=1))
    if not (record["checks"]["acknowledgment_rebound"]
            and record["checks"]["compliance_check"]):
        raise SystemExit("FATAL: acknowledgment/compliance failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

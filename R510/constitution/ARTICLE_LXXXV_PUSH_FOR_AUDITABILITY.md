# Article LXXXV — Push for Auditability

**Status:** RATIFIED 2026-09-19 (Round R510) — enacted into constitution v2.10.1 per the operator's 2026-09-19 directive ("push the stack ... amend the constitution, so you push automatically in order to be audited"); see R510/constitution/AMENDMENT_RECORD_LXXXV.json
**Proposed amendment:** Constitution v2.10.0 → v2.10.1
**Sponsor:** Operator directive, 2026-09-19 (one-line intent; article text coder-drafted, operator review requested — see authorship note below).

## Authorship note (coder-recorded, Art. XV)

Unlike Articles LXXX–LXXXIV (operator-verbatim rule text), this article's wording is coder-drafted from the operator's one-line intent. It is ratified as written unless and until the operator substitutes verbatim text; a substitution would be recorded as an epistemic event (Art. XI), not a silent edit.

## The rule

> **Work that is not pushed cannot be audited. Work that cannot be audited cannot be called done.**

After completing a coherent change set, the coder pushes `origin/main` promptly so that auditors verify reachable bytes (merge-base/branch-containing proof against the remote). Until pushed, a commit is `LOCAL_UNVERIFIED`: it may not be cited as evidence of completion, verification, or deployment readiness. The auditor verifies only commits reachable from the remote; a coder report about unpushed bytes is a hypothesis, never evidence.

Push at minimum before any audit verdict is requested and before any round is reported complete. Classified or secret-bearing material is never pushed to satisfy this article (BS-021 outranks speed: sanitize first, then push).

## What this supersedes

The prior working convention ("finish never implies push; pushes require the literal word") is retired for audit-driven work: the push is now part of completing the work, not a separate authorization. Destructive operations (force-push, history rewrites of published commits, branch deletion) remain forbidden without explicit operator words.

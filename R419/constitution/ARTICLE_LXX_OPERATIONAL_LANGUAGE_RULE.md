# Article LXX — Operational Language Rule (English Only)

**Ratified:** 2026-09-07 (Round R419)
**Amends:** Constitution v2.1.0 → v2.2.0
**Sponsor:** Operator directive (CODER NEXT DIRECTIVE, section 1 — "ENGLISH ONLY — MAKE THIS FORMAL")
**Authority:** Constitutional — added through the formal amendment process (amendment document + version/hash update + re-acknowledgment + verification trail). The Constitution was NOT silently edited.

---

## The Rule (operator-proposed language, verbatim)

> **Operational Language Rule — English Only.** All project-authored code, comments, logs, tests, test names, error messages, worklogs, commit messages, reports, READMEs, governance additions, documentation, API-facing descriptive text, user-facing product copy, and generated technology-package prose shall be written in English unless the operator explicitly requests a translation for a separate user-facing purpose. This rule governs operational consistency and does not alter the epistemic authority of sources in other languages.

## Scope

The rule governs every **project-authored artifact**:

| Artifact class | Examples | English required |
|---|---|---|
| Code + comments | Python/TypeScript sources, docstrings | YES |
| Tests + test names | pytest names, describe blocks | YES |
| Logs + error messages | worker stderr, typed failure records | YES |
| Worklogs + reports | worklog.md sections, round reports | YES |
| Commit messages | git history | YES |
| Documentation | READMEs, ADRs, INTEGRATION, ACTIVE_PATH | YES |
| Governance artifacts | Constitution, GOVERNANCE/, blind-spot register | YES |
| API-facing text | /api/health wording, user_state copy | YES |
| Product copy + UI | webapp strings, package prose | YES |
| Generated package prose | technology-package essays, PDFs | YES |

The rule does NOT touch:

1. **Retrieved evidence** — a Chinese/German/Japanese paper is admissible exactly
   as a source with its original-language spans; Article II (exact evidence)
   forbids translating (and thereby mutating) the evidentiary span. Epistemic
   authority of non-English sources is unchanged.
2. **User input** — a user may type a problem in any language; the engine
   translates through MODEL_DERIVED extraction as it already does.
3. **Quoted operator text** — operator directives quoted verbatim in records
   keep their original wording (they are sources, not project authorship).
4. **Historical artifacts** — pre-R419 artifacts written in other languages are
   historical records (Art. XI); they are superseded going forward, never
   retroactively rewritten (a history rewrite is an epistemic event).

## Constitutional basis

- Extends **Article X** (one canonical authority): one operational language
  prevents semantic drift between two parallel wordings of the same rule.
- Extends **Article XXIV** (a summary is a cache): mixed-language artifacts
  create translation ambiguity that a single reader cannot resolve.
- Supports **Article LXVII** (tracked properties): the language of an artifact
  is now a defined, checkable property rather than an accident of authorship.

## Enforcement

1. **Honest-first**: the primary enforcement is the coder's discipline; every
   artifact authored after ratification is English.
2. **Test guard**: `tests/test_r419_english_only.py` scans newly authored
   artifacts (sources, tests, worklog sections dated ≥ 2026-09-07, commit
   messages of the round) for non-ASCII-script authorship (CJK, Hangul,
   Kana, Cyrillic, Arabic) with an explicit allowlist for (a) retrieved
   evidence paths, (b) quoted source spans, (c) proper nouns.
3. **Commit discipline**: commit messages for this round onward are English.
4. **No retroactive rewrite**: pre-existing artifacts are NOT rewritten
   (Art. XI); where a non-English artifact is actively superseded by new
   work, the replacement is English.

## Verification trail

| Item | Value |
|---|---|
| Pre-amendment version | 2.1.0 |
| Pre-amendment SHA-256 | `50ace8b30efeb72a90e5caa1af1913a74b8f9874327dc4ba1ac09b0537b92997` |
| Pre-amendment git blob | `084c8dd5f8f7218fdf3aa70ed2c8f8b6edd2c772` |
| Post-amendment version | 2.2.0 |
| Post-amendment SHA-256 | recorded in `R419/constitution/AMENDMENT_RECORD.json` at ratification |
| Amendment process | amendment document (this file) → Constitution body updated (version header + amendment log + Article LXX section) → `constitution_loader.acknowledge_constitution()` re-run (new hash + version bound into the acknowledgment capsule) → compliance check GREEN → committed in the R419 commit |
| Certification | the normal constitutional certification chain: acknowledgment file updated, `check_constitution_compliance()` re-run, CI (epistemic workflows) triggered by the push |

## Operator-mandated reading protocol (unchanged by this article)

The coder reads the full Constitution before every coding session and again
before the final commit; the auditor reads the current auditor governance
files before every substantive audit and rereads applicable blind-spot
principles before issuing a verdict (GOVERNANCE/AUDIT_LOOP_PROTOCOL_v1.md).

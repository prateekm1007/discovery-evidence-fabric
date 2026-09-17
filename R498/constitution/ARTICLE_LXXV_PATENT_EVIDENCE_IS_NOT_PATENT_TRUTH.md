# Article LXXV — Patent Evidence Is Not Patent Truth

**Ratified:** 2026-09-18 (Round R498)
**Amends:** Constitution v2.6.0 → v2.7.0
**Sponsor:** Operator directive (verbatim, R498 round-opening message) — a
research sweep of the free/open patent-source universe concluded with the
principle this article ratifies, plus the source-property distinction
codified below.

---

## The operator's directive, verbatim

> One major constitutional principle I would add
>
> **PATENT EVIDENCE IS NOT PATENT TRUTH**
>
> Add:
>
> **No patent database, search engine, dataset, embedding, classifier, or
> LLM output shall be treated as authoritative merely because it returned
> a patent match. Patent records are evidence objects whose provenance,
> publication identity, family relationship, temporal status, and source
> must be preserved.**
>
> And:
>
> **Search coverage must be measured independently from search-result
> count. Failure to retrieve a patent from one source MUST NOT be
> interpreted as evidence that no relevant patent exists.**
>
> And:
>
> **Secondary indexes may discover evidence; primary patent-office records
> should verify consequential assertions whenever available.**

And, on source properties:

> So Toscanini shouldn't assume: "free = anonymous." Instead define
> FREE / ACCESSIBLE / AUTOMATABLE / LICENSE-COMPATIBLE / RATE-LIMITED /
> AUTHENTICATED as separate properties. That's an important constitutional
> distinction.

---

## The Central Invariant

> **A PATENT MATCH IS EVIDENCE, NEVER TRUTH.**
>
> The machine may retrieve patents. It may not treat retrieval as
> authority. Every patent-derived assertion carries the same evidentiary
> burden as every other claim in this constitution: exact binding,
> independent verification, provenance custody, and typed failure states.

## Clause 1 — Patent records are evidence objects

No patent database, search engine, dataset, embedding, classifier, or LLM
output is authoritative merely because it returned a patent match. A
patent record entering the evidence pipeline is an **evidence object**
carrying five custody fields, preserved end to end:

```text
PROVENANCE            which source, which endpoint, which query, when
PUBLICATION IDENTITY  publication number, kind code, application reference
FAMILY RELATIONSHIP   simple patent family / INPADOC membership as known
TEMPORAL STATUS       publication/grant/lapse dates and legal-status basis
SOURCE                the specific provider that returned the record
```

A patent-derived assertion missing any of these fields is
`PROVENANCE_INCOMPLETE` (Article VI) and may not support a consequential
decision. This extends Article XVIII (the LLM is an untrusted component)
and Article XXI (discovery evidence is not search activity) to the patent
layer: the patent provider is exactly as untrusted as the model, and for
the same reason — it returns matches, not truths.

## Clause 2 — Coverage is measured, never inferred from counts

Search coverage must be measured independently from search-result count.
`num_hits` is a count signal only (Article XXI.1). Failure to retrieve a
patent from one source MUST NOT be interpreted as evidence that no
relevant patent exists — a per-source retrieval failure is typed
(`SEARCH_FAILED` / `AUTH_FAILED` / `TOKEN_OUT_OF_SCOPE` /
`KEY_RECOGNIZED_AUTH_NOT_OPENED` / `UNCONFIGURED`), never aggregated into
absence (Articles XXI.3, XXV), and absence from ALL configured sources is
still only `NO_COLLISION_FOUND` — never a novelty verdict (Article XLVI).

## Clause 3 — Secondary indexes discover; primary records verify

Secondary indexes (aggregators, discovery engines, commercial search
surfaces) MAY discover evidence. Primary patent-office records (USPTO,
EPO, WIPO and their official data services) SHOULD verify consequential
assertions whenever available. A consequential patent assertion — one
that feeds a release/reject/collision adjudication — is verified against
primary-record text when a primary source is reachable; when it is not,
the assertion is typed `SECONDARY_ONLY_VERIFICATION` with the limitation
disclosed, never silently promoted (Article XXVIII).

The already-sealed Retrieval-Backed Gate pattern is this clause's
standing local implementation: the search hit's title and abstract are
byte-verified against the INDEPENDENTLY fetched record text (R495 seal,
3/3; R498 patent-leg seal, 3/3) — the claimant's text is never the
verifier's text (Article III).

## The source-property vocabulary (six tracked properties, never collapsed)

Every patent source the machine consults is tracked with SIX SEPARATE
properties, because none implies another:

```text
FREE                 does the source claim to cost nothing?
ACCESSIBLE           can this machine actually reach it right now?
AUTOMATABLE          is there a programmatic path (API/bulk), vs web-only?
LICENSE-COMPATIBLE   are the terms compatible with this machine's use?
RATE-LIMITED         what call/quota budget applies, and is it metered?
AUTHENTICATED        what credential does it require, and is one held?
```

"Free" does not imply anonymous, accessible, automatable, or unlimited
(USPTO bulk data is free but account-gated; Espacenet is free but
explicitly not for bulk automated retrieval; PatentBear's free tier is
free but metered at 20 external calls/month — measured, R497/R498).
A source's properties are MEASURED states with provenance, never assumed
from the source's self-description (Article VI); operator research alone
types a property `OPERATOR_RESEARCH_UNVERIFIED` until measured. The
per-source instance data lives in the versioned source registry (the
operational layer — the Four Layers rule), not in this article.

## Machine-enforcement points

1. Every patent-derived evidence object entering the pipeline carries the
   five custody fields; a missing field types `PROVENANCE_INCOMPLETE`.
2. No surface may report a patent "not found" as a consequence of a
   typed provider failure (the existing typed-transport discipline,
   now constitutional at the patent layer).
3. No coverage or novelty conclusion may derive from `num_hits` or from
   any single source's zero-result state.
4. Consequential patent assertions require record-level byte binding
   (Art. II/III) and primary-record verification when reachable;
   otherwise the typed `SECONDARY_ONLY_VERIFICATION` limitation.
5. Source-property claims carry measurement provenance; the registry's
   per-source states are typed (LIVE_MEASURED / UNMEASURED_THIS_ROUND /
   REQUIRES_REGISTRATION / REQUIRES_KEY / REQUIRES_ACCOUNT /
   OPERATOR_RESEARCH_UNVERIFIED), never binary.

## Relationship to existing articles

- Extends **Article XXI** (discovery evidence is not search activity) to
  the patent layer with patent-specific custody fields.
- Extends **Articles XXV / XLVI** (unknown stays unknown; retrieval
  absence is not novelty) with the multi-source non-aggregation rule.
- Extends **Article XXVIII** (no silent semantic promotion) with the
  secondary→primary verification ladder.
- Extends **Article XXVII** (no threshold invention) to source quotas:
  a metered budget is a measured custody field (the R497/R498 quota
  ledgers), never a silently consumed resource.
- Operationalizes **Article XLVI**'s "no novelty verdict" vocabulary at
  the patent-evidence layer.

## What this article does NOT do

It does not ratify any specific provider, dataset, or architecture —
those live in the versioned source registry and the fabric policy
document (the Four Layers rule: implementation changes, the standard
does not). It does not require the machine to purchase any commercial
database. It does not authorize treating any free source's coverage as
sufficient — coverage sufficiency is a measured property, and today no
configured source's coverage is measured sufficient for a novelty claim
(which is why no novelty verdict exists, Article XLVI).

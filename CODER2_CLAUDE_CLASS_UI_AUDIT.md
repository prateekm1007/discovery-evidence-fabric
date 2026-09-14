# CODER2_CLAUDE_CLASS_UI_AUDIT.md

**Round:** R454-C2 — CODER 2: CLAUDE-CLASS CONVERSATIONAL UI (the 28-chapter briefing)
**Agent:** Coder 2 (conversational product surface / truth presentation)
**Base:** the R453-C2 Claude-class reconstruction (merged at `8d019f3`, deployed, acceptance-verified — its 16-section audit lives in git history and the R453-C2 worklog entries)
**Constitution:** v2.4.0 read IN FULL at round start (hash `b54a1be9…` verified); the five GOVERNANCE files + `ACTIVE_PATH.md` read in full; Constitution re-read immediately before the final commit.
**reviewer_provenance:** AI_REVIEW

---

## 0. Mission compliance summary

The product surface is a **calm conversational discovery engine with
progressive disclosure**: one conversation → one discovery, a contextual
workspace for substantial output, and one primary package action. The
R453-C2 reconstruction established that shape; this round (R454-C2) closes
the 28-chapter briefing's remaining deltas and produces its four
deliverables. No new backend machinery was built (brief §27 held); the
frontend remains a projection of canonical state (Art. X).

**This round's changes (all presentation-layer):**

| # | Change | Brief | File(s) |
|---|---|---|---|
| 1 | **The product event map** — backend science events reach the conversation ONLY through one pure mapping into first-person human sentences; machine summaries ("engine stage SYNTHESIZE recorded at …") stay in the technical record | §22, §25 | `lib/productEvents.ts` (NEW), `components/Conversation.tsx` |
| 2 | **Unknown geometry represented in the conversation** — terminal runs with no established geometry carry the honest sentence instead of silence | §13 | `lib/present.ts` |
| 3 | **Blocked runs never auto-open the workspace** — the stale-positive suppression extends to the auto-open; one action (Resume) | §14 | `app/page.tsx` |
| 4 | Brand wordmark nowrap at 390px | §18 | `app/globals.css` |

## 1. The 28-chapter compliance matrix

| § | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | No dashboard thinking (no gates/stages/counters/JSON/worker states as UX) | DONE (R453-C2) + re-verified | served-bundle machine-vocab scan (R453-C2 acceptance §B) + every DOM state's `no_machine_vocab` check |
| 2 | Home = DISCOVER. INVENT. ANYTHING. + one composer; text/files/URLs; no pre-classification | DONE + honest ingestion note | `app/page.tsx` NewDiscoveryPane; PDF/CAD/image ingestion named as a Coder-1 contract (§16.1 debt, below) |
| 3 | One conversation as the primary application | DONE | `Conversation.tsx`; the run view IS the conversation |
| 4 | Progressive disclosure (Investigating → found 18 sources → mechanisms → survivors) | DONE | `present.ts::deriveConversation` arc; §4 of the R453-C2 audit |
| 5 | Never hide epistemic state; human language == canonical truth | DONE | epi meta chips (FOUND/INFERRED/HYPOTHESIS/TESTED/UNKNOWN); five retrieval states; geometry/attack vocabularies |
| 6 | Right-side contextual workspace; conversation stays available; not every message is a card | DONE | `Workspace.tsx` (overview/model/evidence/engineering/experiment/package/journal); auto-open once, desktop only |
| 7 | Evidence surface: counts first, inspectable provenance behind "View evidence" | DONE + Coder-1 contract | evidence card ("18 relevant sources · 14 shaped the design") → EvidenceSection (source/claim/date/provenance); support/conflict/unresolved split needs a Coder-1 field (§16 below) |
| 8 | Mechanism surface (Observation → Mechanism → Expected effect → Design lever) without raw objects | DONE | conversation mechanism lines + overview/model surfaces reading canonical projections |
| 9 | Candidate surface answers what/why/evidence/attacks/uncertain | DONE | `CandidateView` (label, intervention, mechanism, why, whatChanged, risk/kill, attack state) |
| 10 | Attack surface in scientific language; never a bare green/red badge | DONE | `attackSentence` — CONTESTED escalation preserved; NOT_RUN explicit; challenge lines quoted |
| 11 | Error semantics non-negotiable (provider ≠ candidate failed; retrieval failed ≠ no evidence; not-run ≠ survived) | DONE + pinned | Tests B/C/D/F (16/16) + DOM states 3/7/8 |
| 12 | Retrieval-state UI: PENDING/NOT_REACHED/RETRIEVED_ZERO/RETRIEVED_POSITIVE/FAILED distinct | DONE | `deriveRetrievalState` (GATHERED+0 splits to RETRIEVED_ZERO; FAILED never absence) |
| 13 | Unknown geometry ("not yet established", never "unavailable"/"complete") | **CLOSED THIS ROUND** | conversation note (terminal runs) + workspace model surface; Test E + new §13 pins |
| 14 | Stale-positive attack fixture (BLOCKED + old COMPLETED + visual + engineering) | **STRENGTHENED THIS ROUND** | Test B (unit, 16/16) + DOM state 10 (desktop + mobile): zero stale positives; workspace auto-open now suppressed on blocked runs |
| 15 | Raw IDs under Technical details | DONE | journal surface ("Show the technical record"); event summaries ride `title` + journal; Settings shows engine identity only |
| 16 | Technology result: calm summary + ONE package action | DONE | positive outcome + single "Download the technology package"; §16 structure on the surfaces |
| 17 | Never call everything an invention (no presentation upgrade) | DONE | epi meta never upgraded client-side; maturity from the record; conceptual ≠ engineering vocabulary (R452 B2/B3 pins re-run ALL PASS) |
| 18 | Mobile-first (header/conversation/workspace/composer; sheets) | DONE + improved | mobile captures ×12 at 390px; brand nowrap fix; bottom-sheet workspace |
| 19 | Desktop 3-pane (nav / conversation / current artifact) | DONE | ≥1181px grid; captures ×12 at 1440px |
| 20 | Presentation deadweight audited (KEEP/MERGE/CONDITIONAL/DELETE; no scientific information deleted) | DONE (R453-C2 §2–4) + re-run | TechStage/HistoryRail/DeepDive deletions stand; the R451/R452 pin battery re-ran ALL PASS on the surviving surfaces |
| 21 | CanonicalState → PresentationState (one canonical mapping) | DONE + extended | `lib/present.ts` composes `presentationState.ts` + `renderAvailability.ts`; NEW: events via `productEvents.ts`; machine-readable twin: `CODER2_UI_STATE_MAP.json` (12 maps) |
| 22 | Conversation event rendering (MECHANISM_FOUND → human; BLOCKED_PROVIDER → "not been rejected") | **CLOSED THIS ROUND** | `lib/productEvents.ts`; `CODER2_PRODUCT_EVENT_MAP.json`; DOM states 1/8/10 show the mapped sentences |
| 23 | Never fake thinking (no animated reasoning, no chain-of-thought; task progress from records) | DONE | the cursor is the only animation; every line derives from a persisted event/record; no CoT anywhere |
| 24 | Empty state ("Start a discovery…", never "No records found") | DONE | sidebar empty states are conversational; home composer is the empty state |
| 25 | Loading states are meaningful actions (§25 register) | **CLOSED THIS ROUND** | event-mapped live lines: "Investigating evidence…", "Comparing mechanisms…", "Challenging the leading candidate…", "Designing the decisive experiment…" |
| 26 | Required visual tests (12 states × desktop + mobile) | **DELIVERED THIS ROUND** | `CODER2_VISUAL_REGRESSION_REPORT.md` — 12/12 DOM-verified, 24 captures |
| 27 | No new backend machinery; smallest contracts for Coder 1 | HELD | zero engine/Python files changed; three Coder-1 contracts documented (below) |
| 28 | The four deliverables | DELIVERED | this file + `CODER2_UI_STATE_MAP.json` + `CODER2_PRODUCT_EVENT_MAP.json` + `CODER2_VISUAL_REGRESSION_REPORT.md` |

## 2. Current UI deadweight (28-chapter audit at round start)

The R453-C2 deletion set stands (TechStage, HistoryRail, DeepDive, the home
story strip — Art. LXIV dispositions in git). This round's deadweight scan
of the surviving surface found one class: **machine-voiced event summaries
in the conversation's live area** (the journal's own sentences rendered as
chat). That was presentation deadweight in the human layer — closed by the
product event map; the raw sentences remain exactly where they belong
(journal surface, `title` attributes). No card/badge/icon/metric in the
remaining surface failed the keep/merge/delete scan; nothing scientific was
deleted this round.

## 3. Deleted / merged / kept (delta this round)

- **Deleted:** nothing (no superseded implementation was created; the event map REPLACES the raw-summary rendering in place — the superseded rendering path leaves no code behind).
- **Merged:** the conversation's live line and the event feed now speak through ONE function (`productEventSentence`) — previously two raw-summary paths.
- **Kept:** every DossierSections/RunNarrative/ScienceEvents surface (the journal intentionally keeps the raw summaries — brief §15).

## 4. Information hierarchy (unchanged shape, cleaner voice)

```text
HOME        brand statement → one composer → 4 suggestions
CONVERSATION user problem → progress in first person → evidence →
             candidates → attack → model/package cards → outcome →
             ONE next action → follow-up asks
WORKSPACE   model · evidence · engineering · experiment · package ·
             overview · journal (technical record, raw provenance)
SIDEBAR     New Discovery · Discoveries · Technology Packages ·
             Projects (honest empty) · Settings (engine identity)
```

## 5. Error / unknown / blocked vocabulary (unchanged contracts, now event-aware)

The §10 table of the R453-C2 audit stands verbatim (Test C/D/E/F pins).
This round extends the same discipline to the EVENT layer: an
infrastructure event sentence never names a scientific verdict and a
completed attack stage never announces survival (`test:events` G2/G3).

## 6. Adversarial evidence summary

| Layer | Battery | Result |
|---|---|---|
| Unit (state honesty) | `npm run test:present` | 16/16 PASS (14 prior + 2 new §13 pins incl. the rejection metamorphic) |
| Unit (event map) | `npm run test:events` | 12/12 PASS (G1 machine-vocab ban + metamorphic, G2 ×3, G3, G4 ×2, G5 ×3, closed vocabulary) |
| Regression (R451/R452 pins) | `node scripts/r451_c2_ui_tests.mjs` | ALL PASS |
| Build | `next build` | GREEN (all routes prerendered) |
| DOM (real browser, real build) | 12 states × desktop+mobile | 12/12 PASS (`DOM_VERIFICATION.json`) |

## 7. Production URL and deployed SHA (Art. LXXI)

- Production URL: `https://prateekm1-toscanini-prod-validation.hf.space` (the single canonical HF Space, R447-SPACE-OWNER)
- Deployed SHA at round start: `8d019f3` (the R453-C2 reconstruction; identity verified 8/8 in R453-C2 acceptance)
- This round's commit: recorded in the worklog; the Art. LXXI deploy tuple (push → deploy → `/api/version` + `/api/health` identity) closes in the round record — a commit that exists only locally is UNRELEASED and is named as such until the tuple is green.

## 8. Remaining UX debt / smallest Coder-1 contracts (brief §27)

1. **File/URL ingestion** — `POST /api/run` multipart or an attachments array with typed refs + provenance custody (the composer honestly names the gap today).
2. **Evidence relationship counts** (§7's "14 support / 3 conflict / 1 unresolved") — the ledger carries per-record `used_in_design` but not a relationship-to-mechanism classification; smallest contract: per-record `relationship: SUPPORTS|CONFLICTS_WITH|UNRESOLVED` on the evidence tab, derived by the existing verification stage — the UI renders the split only when the record carries it.
3. **Per-candidate challenge events** + **reality-loop conversation events** (`candidate.challenge`, `reality.observed`, `candidate.mutated`) — enumerated with exact field shapes in `CODER2_PRODUCT_EVENT_MAP.json` §coder1_contracts.
4. **Projects grouping contract** (sidebar stays an honest empty state).
5. **Mid-run asks** — queued-questions contract (the honest refusal stands today).
6. **Invention (showcase) view** keeps its R435 layout (documented debt).
7. **Streaming conversation updates** — per-message incremental streaming to remove poll-step jumps.
8. **Standing operator item** — rotation of the two long-lived credentials exposed in history (escalated since R451-C2; not re-pestered, kept on the record).

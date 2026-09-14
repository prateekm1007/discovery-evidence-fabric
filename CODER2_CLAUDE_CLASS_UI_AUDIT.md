# CODER2_CLAUDE_CLASS_UI_AUDIT.md

**Round:** R453-C2 — TOSCANINI CLAUDE-CLASS UI RECONSTRUCTION
**Agent:** Coder 2 (visual specialist / truth presentation)
**Branch:** `r453-c2/claude-class-ui` (from `09b44c5`, the R451-C2 tip)
**Constitution:** v2.4.0 read IN FULL at round start (hash `b54a1be9…` verified); governance five files + ACTIVE_PATH.md read in full; Constitution re-read before the final commit.
**reviewer_provenance:** AI_REVIEW

---

## 0. Mission compliance summary

The website was transformed from a stage-and-report engineering surface into a
**conversation-first discovery interface**: one conversation → one discovery,
with a contextual workspace for substantial output and a canonical-state
presentation layer (`lib/present.ts`) that every state sentence flows through.
No new backend, model, provider, retrieval system, database, or scientific
algorithm was added (brief §43). Zero new npm dependencies. The engine job API
is unchanged; the frontend remains a projection (Art. X).

---

## 1. Current UI problems (audit at round start)

| # | Problem | Evidence at audit | Severity |
|---|---------|-------------------|----------|
| P1 | **The run view was a report, not a conversation.** The user watched a stage + collapsible report; progress was pipeline-shaped (gauntlet cards + 13-stage sentence blocks visible on the primary surface). | `TechStage.tsx` layout: hero + 4 insight cards + journal below | High |
| P2 | **Navigation exposed machinery-shaped IA.** Sidebar = "Your runs" + "Released inventions — proof the engine produces technology packages" (internal narrative in nav copy). | `HistoryRail.tsx` | Medium |
| P3 | **The pipeline leaked as decoration**: home story strip `DISCOVER ↓ INVENT ↓ INSPECT ↓ CHALLENGE ↓ REBUILD ↓ EXPERIMENT`. | `page.tsx::STORY_STEPS` | Medium |
| P4 | **Ask was buried** in the deep layer (`DeepDive` section 8); the product's conversational follow-up was hidden behind a disclosure click. | `DeepDive.tsx` SECTIONS | High |
| P5 | **Three equally weighted actions** (Test this / Compare generations / Download package) — no single next-best-action recommendation. | `TechStage.tsx` stage-actions | Medium |
| P6 | **No contextual workspace.** Substantial outputs (model, evidence ledger, package) lived in one long inline scroll instead of a dedicated surface beside the conversation. | R435 single-column layout | High |
| P7 | **Honest loading gaps**: engine-unreachable during a run poll rendered a silent eternal "Loading investigation…" (BS-018 class: stale user-visible state). | `page.tsx` poll (pre-existing since R395) | Medium |
| P8 | Deep-dive section IDs (`journal/summary/model/…`) were the only access path to evidence/engineering/experiment/package — mobile required endless scrolling. | `DeepDive.tsx` | Medium |

## 2. Components deleted (Art. LXIV dispositions)

| Deleted | Superseded by | Disposition |
|---|---|---|
| `components/TechStage.tsx` (601 lines) | `Conversation.tsx` + `Workspace.tsx` | DELETED — the stage+report layout is superseded; the hero viewer moved into the workspace's model surface; git history preserves the file |
| `components/HistoryRail.tsx` (131 lines) | `components/Sidebar.tsx` | DELETED — replaced by the new IA navigation |
| `components/DeepDive.tsx` (357 lines) | `Workspace.tsx` surfaces | DELETED — its sections render inside the workspace; no second deep layer |
| Home story strip (`STORY_STEPS`) | 4 lightweight suggestion chips + composer hints | DELETED — pipeline-as-decoration (P3) |

No superseded implementation was left coexisting (Art. LXIV.1: `DELETED`, recorded here; verification: `rg -l "TechStage|HistoryRail|DeepDive"` shows no code imports, comments only).

## 3. Components merged

- **AskBox's `AnswerView` → Conversation**: one answer renderer now serves both the run conversation and the invention ask (exported from `AskBox.tsx`; honest refusal vocabulary identical everywhere).
- **TechStage's insight cards → conversation messages**: "What changed / Why it works / What supports it / What could kill it" became the evidence/candidates/attack/outcome message arc derived in `present.ts`.
- **DeepDive sections → Workspace surfaces**: identical section components (`DossierSections.tsx`, `RunNarrative`) reused unchanged — no second renderer, no drift.
- **Hero honest states (R436/R446 vocabulary) → Workspace model surface**: `renderAvailabilityNotice` sentences moved to `present.ts::renderAvailabilitySentence` (single owner); `DossierSections` delegates.

## 4. Components retained (audit verdict: ESSENTIAL / USEFUL)

- `ModelViewer` (the ONE 3D viewer; Article LXXII presentation-only), `DossierSections.tsx` (canonical projections), `RunNarrative.tsx` (the journal + `isTerminal`), `ScienceEvents.tsx` (epistemic badges — never upgraded), `AskBox.tsx` (invention mode), `InventionStage.tsx` (released-package view), `InventionArtifact.tsx`, `InventionStory.tsx`, `InventionEssay.tsx`, `EngineeringArgument.tsx`, `RealityLoopPanel.tsx`, `ModelViewer.tsx`.
- The transport dot + calm engine status text (honest health, never panic).
- The Visual Quality Gate badge (Art. LXXII compliance receipt) — retained, moved with the model surface.
- `/run` and `/showcase` redirect routes (old links keep working).

## 5. New information architecture (brief §5)

```text
SIDEBAR                MAIN                      RIGHT (contextual, when useful)
New Discovery          The conversation          model · evidence · engineering
Discoveries            (or the composer          experiment · package · overview
Technology Packages     on the home screen)      · journal (technical record)
Projects (honest empty state — the backend
Settings (engine identity, honest)  grouping contract does not exist yet)
```

Not 15 destinations; the pipeline is not navigation. Discoveries are states of
one discovery rendered as conversation. The right panel appears when a
substantial output exists (auto-open on desktop ≥1181px when a hero or package
exists; always user-openable from artifact cards; Escape/click closes). On
mobile it is a bottom sheet.

## 6. New discovery flow

1. **Home** = `DISCOVER. INVENT. ANYTHING.` + **What do you want to discover?** + one dominant composer (+ Attach for text files; URLs/specs/constraints typed or pasted naturally) + four suggestion chips. No dashboard wall, no KPI cards, no pipeline diagram.
2. **Start** = one interaction (Enter or the button); the engine infers domain/mechanism space; the user never fills a form first (a typed "not-ingestable" note names PDF/CAD honestly).
3. **Conversation** (derived in `lib/present.ts::deriveConversation`): user problem → opening → evidence (five canonical retrieval states, §10 below) → candidate mechanisms as competing hypotheses (label / why it might work / risk / attack status) → the attack ("now I'm trying to prove this wrong") → artifact cards (model/package) → outcome with ONE next-best action → follow-up asks answered from the record with honest refusals.
4. **Workspace** opens contextually for substantial output; the conversation stays available.
5. **Terminal** = honest outcome (positive / development / rejected / unknown / blocked) + single recommendation; "Show the technical record" opens the full journal (RunNarrative, engineering argument, essay, novelty/cemetery, gauntlet, event history with per-event provenance).

## 7. Mobile design

- Base CSS = phone: single column, conversation primary; composer sticky; sidebar behind ☰ (fixed drawer + backdrop, pre-existing pattern); workspace = bottom sheet (max-height 78vh, drag-handle bar, Escape/close button).
- Fixed during this round: the panel grid rule previously leaked `268px …` columns into mobile (conversation squeezed to ~120px) — the 3-column grid now exists ONLY inside `@media (min-width: 1181px)`; verified at 390px (iPhone 14) that `[data-ws-main]` occupies the full width and the sheet opens over the conversation.
- No dashboards crammed onto mobile; cards cap at 100% width; horizontal overflow defenses (pre-existing R393 wrap rules) retained.

## 8. Desktop design

- ≥1181px: persistent sidebar (268px) + conversation (max 720px measure, centered) + contextual workspace column (400–520px, sticky, independently scrollable).
- ≥880px <1181px: sidebar collapses to drawer; workspace becomes the sheet.
- The right panel appears **when useful** (auto-open once per run when a hero or package exists) — never permanently occupying the screen.

## 9. Canonical-state mapping (summary — machine-readable twin in `CODER2_UI_STATE_MAP.json`)

The frontend reads ONLY: `/api/run/{id}/result` (+embedded `run_state`, `user_state_view`), `/events`, `/dossier`, `/cio`, `/health`, `/sessions`, `/showcase`. **All presentation sentences are derived in `lib/present.ts`** — components render, never re-derive (Art. X; auditor principle 7). Key derivations: `deriveRetrievalState`, `deriveGeometryState`, `deriveAttackState`, `deriveCandidates`, `deriveNextAction`, `deriveConversation`, `suppressStalePositives`, `renderAvailabilitySentence`. Vocabulary ground truth: `toscanini/run_state.py` (evidence/attack/physics states), `toscanini/user_state.py` (user-facing keys), `CIO` maturity ladder (the UI cannot upgrade epistemic state; "invented/engineered/validated" wording never precedes canonical state — brief §26).

## 10. Error / unknown / blocked mapping (briefs §18, §28, §29; Art. XXV/LXI)

| Canonical state | User-facing sentence (verbatim source: `present.ts`) | Forbidden render |
|---|---|---|
| retrieval `PENDING` | "Evidence retrieval is in progress — I'm searching the indexed sources now." | "No evidence found" |
| retrieval `NOT_REACHED` | "The evidence stage was not reached… never began… not a finding about the problem." | "No evidence exists" |
| retrieval `GATHERED, 0` | "…returned no matching records. …not evidence that the concept is novel…" | "Nothing is known about this" |
| retrieval `FAILED` | "Evidence retrieval failed — infrastructure state, not evidence of absence…" | "No evidence exists" / rejection |
| geometry `NOT_ESTABLISHED` | "Engineering geometry is not established on this run…" | "Engineering unavailable" |
| geometry `UNAVAILABLE` | "Engineering geometry exists on this run; the visual rendering is unavailable right now…" | "Engineering failed" |
| renders `RENDER_SKIPPED_LOW_MEMORY` | "Engineering geometry available; visual rendering unavailable at current deployment capacity." | "rendering failed" / "visualization complete" |
| attack `NOT_RUN` | "The adversarial test has not been completed. Nothing is claimed either way…" | "Survived attack" |
| attack escalation (uncalibrated) | CONTESTED — "objection is preserved and escalated… not a verdict, and not a pass" | silent KILL or PASS |
| `RUN_BLOCKED_TRANSPORT` / `INTERRUPTED` / `ERROR*` | "Current run blocked" / "Run interrupted" — "infrastructure state, never a scientific result" + Resume | "The invention failed" |
| engine unreachable (browser) | "The discovery service is not responding right now. Your runs are persisted… nothing about any discovery outcome is implied by this." | eternal silent spinner |
| ask `NOT_IN_RECORD` / `REFUSED_OVERCLAIM` / `TRANSPORT_ERROR` | first-class honest answers (shared AnswerView) | fabricated answers |

## 11. Adversarial UI tests (brief §40)

`TOSCANINI_UI/webapp/tests/adversarial_present.test.mjs` — 14 tests, **14 PASS** (`npm run test:present`; compiles the React-free core with the repo's own `tsc`, runs `node --test`). The six required fixtures, all pinned as executable assertions:

- **Test A** `candidate=REJECTED, visual=complete` → outcome tone `rejected`, label "Rejected"; package artifact impossible; no package next-action.
- **Test B** `run=BLOCKED_TRANSPORT + stale COMPLETED_CANDIDATE + visual_complete + ENGINEERING(+package.complete)` → conversation renders "Current run blocked" + Resume; **zero candidate cards, zero artifact cards**; `suppressStalePositives` gates every positive surface; metamorphic variant: suppression holds with the outcome field missing; a second metamorphic pins that the blocked label is derived from CURRENT status, never the stale `user_state_view.label` (this exact bug was caught by the test and fixed).
- **Test C** `retrieval=PENDING` → "in progress", never "not found".
- **Test D** `retrieval=FAILED` → "failed… not evidence of absence"; siblings pin `RETRIEVED_ZERO` (query-scoped, never novelty) and `NOT_REACHED` (never a finding).
- **Test E** `geometry=UNKNOWN` → "not established" ≠ `UNAVAILABLE`'s sentence; sibling: conceptual never claims engineering geometry.
- **Test F** `attack=NOT_RUN` → "has not been completed", never "survived"; metamorphic: escalated objection = CONTESTED, never silently survived.
- Positive control: complete run with package → evidence card + candidates + SURVIVED + package artifact + "Download the technology package" next action.
- Next-action ladder + epistemic-meta (FOUND/INFERRED/HYPOTHESIS/TESTED/UNKNOWN) mappings pinned.

**Browser-level verification (fresh production build via `next start` + agent-browser, fresh context):**
- Home renders composer-first (brief §6/§45: brand, one composer, 4 suggestions; no pipeline UI) — desktop and 390px mobile screenshots captured.
- Suggestion click fills the composer; Enter starts.
- Test B fixture injected at the network layer → the REAL UI rendered "Current run blocked" with `data-conv-candidate` count = 0 and artifact count = 0 despite the stale positives (DOM-verified) + "Resume the investigation" button present.
- Positive-control fixture → full arc rendered (evidence card "18 relevant sources", INVENTION 01 card with "survived attack" chip, attack sentence, outcome + single next action, package artifact card) and the workspace auto-opened on the package surface (desktop).
- Engine-unreachable → the honest "discovery service is not responding" state (new this round; found by probing the fresh user path — BS-018 class fixed).
- Mobile: `[data-ws-main]` = 374/390px full width; bottom sheet opens on artifact tap (`ws-panel open`).
- Zero page errors observed across all probes.

## 12. Visual regression results

- `next build` **GREEN** (Next 15.4.5, all routes prerendered; type check + lint pass).
- `npm run test:present`: **14/14 PASS**.
- Presentation-layer compilation is part of the test script (`tsc --strict`): **GREEN**.
- Pre-existing engine-side batteries untouched (no Python changed this round — zero engine files modified).
- Manual visual regression of retained surfaces (hero honest states, gate badge, dossier sections, RunNarrative, invention view): component code unchanged; layout containers changed only as described in §3/§5.
- Screenshots captured (fresh browser): home desktop, home mobile, positive-control desktop with workspace, Test-B blocked conversation, mobile bottom sheet. (Paths in the round worklog; not committed to the repo.)

## 13. Before / after

**Before** (audit state): run page = stage hero + 4 insight cards + 3 equal buttons + pipeline-shaped journal + 8-section collapsible report; sidebar = "Your runs / Released inventions — proof the engine produces technology packages"; home = brand + composer + pipeline story strip; ask buried in deep layer.

**After**: run page = conversation (user → evidence → candidates → attack → outcome → next action → asks) with contextual right workspace; sidebar = New Discovery / Discoveries / Technology Packages / Projects (honest empty) / Settings; home = brand + one composer + 4 suggestions + attach; composer doubles as the follow-up ask box inside the conversation. The pipeline is visible as a story, not as machinery.

## 14. Production URL

`https://prateekm1-toscanini-prod-validation.hf.space` (the single canonical HF Space, R447-SPACE-OWNER). **This round's build is NOT yet deployed** — see §15.

## 15. Exact deployed commit — Art. LXXI delivery tuple

```json
{
  "target_sha": "THIS COMMIT (branch r453-c2/claude-class-ui; SHA recorded in the round worklog)",
  "pushed_to_origin_main": false,
  "deployed_sha": null,
  "health_check_result": "BLOCKED",
  "drift": "UNKNOWN",
  "blocked_by": "no GitHub credentials in this session environment (ls-remote fails; Art. XXII/XXIII live-remote verification impossible; the R451-C2 credential blocker persists, escalation count now 2 consecutive Coder-2 rounds)",
  "what_unblocks": "operator injects GitHub PAT (env-only per R451-C2 policy) so the branch can be pushed/merged to origin/main and the records-alignment Space deploy can serve it; then re-run /api/version + /api/health identity verification per Art. LXXI"
}
```

Per Art. LXXI Section 1/4 this round record declares **DELIVERY_BLOCKED**: the reconstruction is complete, tested, and production-built in the workspace, but a commit that exists only in a local workspace is UNRELEASED. Honest blocking is correct behavior; the blocker is named with its operator action. (The operator is ALSO reminded: rotation of the two long-lived credentials exposed in history, escalated since R451-C2, remains outstanding.)

## 16. Remaining UX debt (documented, not worked around — brief §43)

1. **File/URL ingestion contract (needs Coder 1):** the composer accepts text files client-side today; PDF/CAD/image ingestion needs the smallest engine contract — `POST /api/run` accepting multipart or an attachments array with typed refs + provenance custody. The UI note names this honestly; no fake upload path exists.
2. **Projects need a backend grouping contract** (`session.group_id` or a projects table + API). The sidebar Projects entry renders an honest empty state until then.
3. **Conversational follow-up mid-run**: `/ask` honestly refuses while a run is active; a queued-questions contract (ask → answered on completion) would make the composer fully conversational during runs. Current refusal wording explains this.
4. **Invention (showcase) view** keeps its R435 stage layout; migrating it into the conversation+workspace shell is straightforward follow-up work (its deep layer already reuses the same sections).
5. **Streaming conversation updates**: the conversation currently re-derives on poll/SSE events (5s cadence + SSE append); per-message incremental streaming (event → message diff) would remove the visible step-jumps on slow links.
6. **i18n**: operational language is English-only per Art. LXX; user-input languages are untouched by the UI.

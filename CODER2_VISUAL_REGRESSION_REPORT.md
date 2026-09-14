# CODER2_VISUAL_REGRESSION_REPORT.md

**Round:** R454-C2 — CLAUDE-CLASS CONVERSATIONAL UI (brief §26 "Required visual tests")
**Agent:** Coder 2 (conversational product surface)
**Constitution:** v2.4.0 (hash `b54a1be9…` verified at round start; re-read before the final commit)
**reviewer_provenance:** AI_REVIEW

---

## 1. What this report is

The briefing's §26 requires twelve visual states captured on **desktop and
mobile**. This round executes them against the **REAL production build**
(`next build` → `next start`, all routes prerendered) fed by a labeled
fixture API server implementing the exact job-API wire shapes observed in
production (`R453/PRODUCTION_ACCEPTANCE_R453C2/run_result.json`; Art. XXV —
no invented shapes). Every state is asserted **in the real DOM**, not merely
screenshot: a PNG existing proves nothing (auditor principle 34 /
BS-034). Result: **12/12 states PASS, 24 screenshots** (12 desktop at
1440×900 + 12 mobile at 390×844).

- Screenshots: `/home/z/my-project/download/R454-C2/visual_regression/` (`desktop_*.png`, `mobile_*.png` — not committed to the repo, per the R453-C2 practice)
- DOM verdicts: `/home/z/my-project/download/R454-C2/DOM_VERIFICATION.json`
- Executable drivers (committed to the sandbox scripts, reproducible):
  `scripts/r454_c2_visual_fixture_server.mjs`, `scripts/r454_c2_visual_capture.sh`, `scripts/r454_c2_dom_verify.sh`
- Production identity at report time: `https://prateekm1-toscanini-prod-validation.hf.space` serving engine commit `8d019f3` (the R453-C2 reconstruction; this round's redeploy SHA is recorded in §4 — Art. LXXI tuple in the round record).

## 2. The twelve states and their DOM-verified honesty contracts

| # | State (§26) | Fixture run | Desktop verified in the DOM | Mobile |
|---|---|---|---|---|
| 1 | fresh discovery | `v454fresh` | PASS — user problem bubble; opening line; evidence "in progress"; live event line is the product sentence ("I'm reading your problem — extracting what it claims…") with the INFERRED badge; **zero machine vocabulary** | PASS |
| 2 | evidence retrieval pending | `v454pending` | PASS — "Investigating evidence — I'm searching the indexed sources now." (the §25 register); never "no evidence"/"not found" | PASS |
| 3 | retrieval failed | `v454retrfail` | PASS — "One of the evidence sources could not be reached… absence is never concluded…"; **never "No evidence exists"** (Art. XXI.3/XXV; BS-013) | PASS |
| 4 | retrieval positive | `v454pos` | PASS — evidence card "18 relevant sources · 14 shaped the design" + "View evidence →"; event feed "Evidence came in from europepmc — 18 records." (§7 surface) | PASS |
| 5 | candidate rejected | `v454rejected` | PASS — candidate card "failed", attack sentence with the recorded cause, outcome label **"Rejected"**, next action "Reformulate the problem and run again"; never "promising" | PASS |
| 6 | candidate survives | `v454survive` | PASS — candidate card + "survived attack" chip + strongest-objection line + positive outcome | PASS |
| 7 | attack not run | `v454notrun` | PASS — "The adversarial test has not been completed. Nothing is claimed either way…"; **never "survived"** (brief §11; Test F) | PASS |
| 8 | transport blocked | `v454blocked` | PASS — "Current run blocked" + "infrastructure state, never a scientific result" + single Resume action; **the candidate is never called rejected** (Art. LXI) | PASS |
| 9 | geometry unknown | `v454geounk` | PASS — the §13 sentence **in the conversation**: "Engineering geometry is not established on this run. Nothing is rendered because nothing was established…"; no model card; never "unavailable"/"complete" | PASS |
| 10 | stale positive artifact | `v454stale` | PASS — BLOCKED run + stale `COMPLETED_CANDIDATE` snapshot + stale visual_complete + stale package: **zero candidate cards, zero package action, workspace does not auto-open**; "Current run blocked" + Resume is the one action (brief §14; Test B at the DOM level) | PASS |
| 11 | engineering complete | `v454eng` | PASS — "survived attack" + model artifact card whose body states the geometry is the run's canonical engineering geometry, "not an illustration" | PASS |
| 12 | technology package ready | `v454package` | PASS — positive outcome + **one** package action ("Download the technology package"); §16 calm-result structure (what supports it / what remains uncertain / decisive experiment on the surfaces) | PASS |

Global assertion on **every** state: the conversation contains no machine
vocabulary (`engine stage …`, `persisted its envelope`, `recorded at 20…`,
raw kind tokens) — the BS-009 class this round closes at the conversation
layer (`lib/productEvents.ts`).

## 3. What changed this round to make these pass

| Change | File | Why |
|---|---|---|
| The product event map (§22/§25) — backend events become first-person human sentences; machine summaries stay in the technical record | `lib/productEvents.ts` (NEW) + `components/Conversation.tsx` | the live line previously rendered raw journal summaries ("engine stage SYNTHESIZE recorded at …") — machine state in human UX |
| Unknown geometry is REPRESENTED in the conversation (§13) | `lib/present.ts::deriveConversation` | a terminal run with no established geometry used to be silent; now it carries the honest sentence (never "unavailable"/"complete"); a rejection keeps the terminal word (metamorphic pin) |
| Blocked runs never auto-open the workspace (§14) | `app/page.tsx` | the stale-positive fixture (state 10) previously auto-opened the package panel; now a blocked run presents exactly one action — Resume |
| Brand wordmark no longer wraps at 390px | `app/globals.css` | mobile capture showed "Toscani/ni" |

## 4. Batteries (all green at the captured build)

| Battery | Result |
|---|---|
| `npm run test:present` (state-honesty contracts incl. the two new §13 pins) | **16/16 PASS** |
| `npm run test:events` (product event map G1–G5 + closed vocabulary) | **12/12 PASS** |
| `scripts/r451_c2_ui_tests.mjs` (the R451/R452 presentation-pin regression) | **ALL PASS** |
| `next build` (production, all routes prerendered) | GREEN |
| DOM visual states (this report §2) | **12/12 PASS** |

## 5. Honest scope notes

1. The fixture server serves the **real wire shapes** with labeled fixture
   ids (`v454*`); it is an observation instrument for the UI layer, not a
   second backend (brief §27 held — no new product machinery).
2. The 3D viewer itself (WebGL canvas) is not exercised by these fixtures —
   the R451-C2 family already proves the viewer's honest states in the DOM
   (`R451/C2_PRODUCT/E2E*`); these captures verify the conversation layer
   around it, including the workspace surfaces' honest titles.
3. The stale-positive capture (state 10) is the briefing's exact fixture:
   current run `RUN_BLOCKED_TRANSPORT`, old candidate `COMPLETED`,
   visual complete, engineering true — and the DOM proves the suppression.
4. Production at report time serves `8d019f3` (the R453-C2
   reconstruction). This round's changes ride the R454-C2 commit; the
   Art. LXXI deploy tuple for it is recorded in the round record/worklog —
   the production URL is
   `https://prateekm1-toscanini-prod-validation.hf.space`.

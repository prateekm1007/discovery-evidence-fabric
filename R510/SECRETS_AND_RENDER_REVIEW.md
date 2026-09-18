# Secrets Review + Render Retire (R510) — names only, values never leave custody

## Operator decisions recorded (this turn, live words)

1. **Retire Render; Hugging Face only.** The legacy Render surface is retired as a
   production target by operator word. Coder-side effect: none available (the
   dashboard click is an owner act — ESCALATED back, single item). Interim
   measured state: legacy surface UNREACHABLE_THIS_ATTEMPT (HTTPS timeout);
   canonical target remains `prateekm1/toscanini-prod-validation` (live
   d15aaa75/2.9.0, drift none). No code change (owner act).
2. **Frontier keys in HF secrets usable instead of HF funding.** Standing
   (re-affirmed): use server-side transport; values never enter this container.

## Secrets review (32 names on the vault surface; usability paths, no values)

| Need | Name present | Value here | Usable path |
|---|---|---|---|
| GitHub push/fetch | GITHUB_TOKEN yes | session-env this turn (fp match) | direct (used) |
| HF Space API/deploy | HF_TOKEN yes | session-env this turn (fp match) | direct (used) |
| xkiro ring | XKIRO_API_KEY yes | no (server-side only) | production `/api/ops/a2-attack` pin (B2 proven 21/21) |
| zai ring | ZAI_API_KEY yes | no | production pin; live HEALTHY today |
| unorouter ring | UNOROUTER_API_KEY yes | no | production pin (AUTH_FAILURE measured R505) |
| atria ring | ATRIA_API_KEY_1..15 yes | no | production pin; **probe refused by harness identity gate** (see below), zero calls made |
| apinex/bai/bynara/tokenharbor/aerolink | yes | no | production pins if needed; unmeasured |
| PatentBear | absent (holding-sessions-only) | no | 19/20 untouched; no spend |
| ELSEVIER | ELSEVIER_API_KEY yes | no | server-side Scopus legs (previously LIVE) |
| Lens | LENS_API_TOKEN yes | no | TOKEN_OUT_OF_SCOPE stands |
| Tier-1 (EPO OPS/PatentsView) | absent | no | checklists stand (operator filing) |

## Harness orphan finding (Art. XV — blocks atria + future DEV runs, not a failure)

The atria 2-case probe made ZERO model calls: `r505` identity gate refuses
(deployed d15aaa75 vs pinned d7520b9b — the gate working as designed, never
measure a moved build silently). Consequence: every r505-derived DEV harness is
orphaned until its expected-build pin advances to d15aaa75. The nil-delta proof
(R510/NIL_DELTA_PROOF.json) justifies the advance, but the pin lives in round
instrumentation — banked as post-harvest harness maintenance, NOT edited this
turn (stop-list). B2 rerun stands (gated OK while d7520b9b was live).

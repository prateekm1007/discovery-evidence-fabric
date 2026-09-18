# B5 Collision-Scale Readiness (R510) — checklists + warm path + retry design; zero spend

## Measured this round

- EPO-LOD verification path warm: `R510/KEYLESS_WARM.json` — L1 GET + POST-form
  legs both `LIVE_PROTOCOL_SPARQL_JSON` HTTP 200 (435 bytes each), metered debits 0.
- PatentBear bucket untouched: still 19/20, floor 2 (B7 ledger row re-asserts).
- No PatentBear value exists anywhere machine-readable — accepted (directive B5).

## Tier-1 registration packets (operator filing acts — checklists, nothing filed by machine)

### EPO OPS (unblocks automated worldwide primary retrieval)
- [ ] Operator registers at developer.epo.org (free OPS account, OAuth consumer key/secret).
- [ ] Operator supplies key into the LXXIII vault (holding session sets it; machine never invents it — Art. VI/XXV).
- [ ] Coder then: `epo_ops_adapter.py` probe → registry `epo_ops` REQUIRES_REGISTRATION → LIVE_MEASURED; record in key-budget ledger.

### PatentsView (unblocks structured US graph + claim text)
- [ ] Operator obtains free PatentsView API key (patentsview.org).
- [ ] Vault set by holding session; coder probes → `patentsview` REQUIRES_KEY → LIVE_MEASURED.

### USPTO.gov account (unblocks US bulk data)
- [ ] Operator registers USPTO.gov account; same vault-then-probe sequence.

## Lens keyed-leg retry budget (DESIGN — `the_lens` is TOKEN_OUT_OF_SCOPE, no key held)

- Retry classes: 429/503 → bounded backoff (3 tries, 30/90/240 s) then typed
  PROVIDER_INCONSISTENT guard (the R497 scope-order pattern); 401/403 → no retry,
  typed AUTH failure, escalate per LXV; 5xx ×3 → circuit-open for the round.
- Budgets draw from the key-budget ledger reservation rows only (B7 protocol);
  no reservation row → no keyed call. Floor advisory respected.
- Code lands post-harvest with the collision item iff the funnel ranks it (Part 3.4).

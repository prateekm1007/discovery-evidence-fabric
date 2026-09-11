# R445 Baseline Identity

Recorded at round start (2026-09-11, before any code change).

| Identity | Value | Source |
|---|---|---|
| Local HEAD | `087f9955eae2a3738c55755c1443e576e1af536b` | `git rev-parse HEAD` |
| origin/main (ls-remote, live) | `087f9955eae2a3738c55755c1443e576e1af536b` | `git ls-remote` (PAT) |
| Local origin/main ref before fetch | `f115b85fff9e0ae746aab64cd44cb4755c9bb79a` | stale local ref; ls-remote confirms HEAD is pushed |
| Production /api/version engine_commit | `087f9955eae2a3738c55755c1443e576e1af536b` | `GET /api/version` (build_artifact), constitution_version 2.3.0 |
| Working tree | clean | `git status --short` |
| Constitution | v2.3.0, sha256 `7084be6435ff30a645f4ad16a5380cf897a59b6dd73f5e18af3713010131a9c5` | `sha256sum EPISTEMIC_CONSTITUTION.md` |

Baseline state: HEAD == remote main == deployed production SHA.
No STALE_LOCAL_CHECKOUT condition at round start.

Mandatory reads completed before coding: EPISTEMIC_CONSTITUTION.md v2.3.0
IN FULL (Preamble, Discovery Imperative, Articles I–LXXII, 16-step discovery
coding loop, Four Constitutional Layers, WORLD_CLASS_DISCOVERY_GATE);
GOVERNANCE/README.md, AUDITOR_SELF_GOVERNANCE_v1.md,
AUDITOR_BLINDSPOT_REGISTER.md, AUDITOR_REMEMBERED_STATE.md,
AUDIT_LOOP_PROTOCOL_v1.md; ACTIVE_PATH.md (incl. R442/R443/R444 addenda);
R444/R444_ROUND_RECORD.json (baseline f177fcf5; battery 16 problems;
TPR 12/12, false-kill 4/4, TNR 0; 3 dedicated evolution cases
TRANSPORT_BLOCKED; F1 = domain-family vocabulary divergence blocking ALL
packages; attacker NOT_CALIBRATED).

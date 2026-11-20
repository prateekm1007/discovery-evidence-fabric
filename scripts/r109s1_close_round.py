#!/usr/bin/env python3
"""r109s1_close_round.py — the round-close record: the claims progress
appends (c-0133..c-0137 -> DONE with typed outcomes) + the round
status record. Formatting preserved (indent=1, ensure_ascii=False)."""
import json
from datetime import datetime, timezone
from pathlib import Path

REG = Path(__file__).resolve().parents[1] / "eval" / "work_claims.json"
OUT = Path(__file__).resolve().parents[1] / "eval" / "r109s1_status.json"
NOW = datetime.now(timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)")

d = json.loads(REG.read_text(encoding="utf-8"))
by_id = {c["claim_id"]: c for c in d["claims"]}

UPDATES = {
    "c-0133": ("DONE", "the D6 PyMuPDF retirement MEASURED: zero fitz "
               "imports tree-wide; NOTICE row retired with the Art. 16 "
               "ledger entry; the pypdf/pdfplumber/pdftoppm port green "
               "on the golden regression (P-04/P-07 frozen structural "
               "references) + the blind-corpus verdicts + test_r443 "
               "(11/11 + exit 0); the parity record carries the "
               "evidence (eval/r109_d6_parity_record.json)"),
    "c-0134": ("DONE", "the D5 root-cause record (eval/"
               "r109_d5_rootcause.json: the rule counterfactuals — "
               "even the ANY-single-judge rule gives 0.2414 < 0.40; "
               "the J2-lenient asymmetry; the no-signal GT feature "
               "table; the raw-byte gap typed; the MOOSE-Chem2 2025 "
               "probe typed UNAVAILABLE — upstream has zero 2025 "
               "items) + the D8 family-swap bias probe (eval/"
               "r109_d8_bias_check.json + the RAW bytes in eval/"
               "r109_d8_bias_probe_raw/ — the two RECOVERED items "
               "regenerated ONE agnes generation each and re-judged "
               "under BOTH seat assignments on identical bytes: 0 "
               "adjudication flips, both families unanimous on the "
               "clear-recovery material; the calibrated claim needs "
               "the 25-item PARTIAL body, typed). Usage: 2 agnes + 4 "
               "zai + 4 xkiro calls"),
    "c-0135": ("DONE", "the D2 probe (7 third-family ids across 5 "
               "families all instant-403 on xkiro post-maintenance; "
               "agnes catalog = agnes-family only; the direct/azure "
               "transports typed UNFUNDED — keys absent from the "
               "vault, the ONE-reminder flag stands) + the D3 "
               "pre-registration committed BEFORE any v16 scoring "
               "(the 7-point anchors, the frozen calibration-set "
               "qualification, the dual disagreement statistics, the "
               "power note)"),
    "c-0136": ("DONE", "the D4 staging record (the gate failure "
               "anatomy from committed bytes: the known-novel anchor "
               "fails BOTH legs — 0.104 < p95 0.158 AND < margin leg "
               "0.1197; all 30 rows fail both; the three v16 "
               "candidates staged with their execution needs; "
               "candidate (c) alone still misclassifies the anchor)"),
    "c-0137": ("DONE", "typed BLOCKED__INSUFFICIENT_DISK: 5.7GB free "
               "vs ~11GB needed (eval/r109_d7_disk_probe.json; the "
               "resume condition + the validated 7zz path typed; the "
               "173-file two-bearing sample stands as the committed "
               "coverage)"),
}
for cid, (status, note) in UPDATES.items():
    c = by_id[cid]
    assert c["session_id"] == "builder-r109s1", cid
    c["status"] = status
    c["stage_progress"] = c.get("stage_progress", [])
    c["stage_progress"].append({"at": NOW, "status": status,
                                "note": note})

REG.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")

rec = {
    "record": "R109S1_STATUS/1.0.0",
    "at": NOW,
    "executor": "builder-r109s1",
    "base": "5940e9749",
    "d1_preflight": ("BOTH constitutions FULL-read (the epistemic "
                     "v3.3.0 at the audited 972272bbd — 29 articles + "
                     "4 amendment records + the Art. 28 addendum; the "
                     "auditor v1.3.0 at origin/"
                     "audit/r11-auditor-verdict-20261114 — 14 articles "
                     "+ 3 amendments); the vault restored exit 0 via "
                     "r77_vault_restore.py on the owner re-delivered "
                     "master token (digest 33bc7af22c62 "
                     "COMMITTED_RECORD_MATCH — the private-vault "
                     "grant landed, 6 keys incl. the AGNES rotation "
                     "pair; .env.keys caught at 755 on arrival, "
                     "reset 0600); the generator verified "
                     "agnes-3.0-flash on the live purposes with the "
                     "judge route separate"),
    "directions": {
        "D6_pymupdf": "DONE (zero fitz imports; suites green; NOTICE "
                      "row retired with accounting)",
        "D5_score9_rootcause": "DONE (record + the MOOSE 2025 probe "
                               "UNAVAILABLE + the raw-byte gap typed)",
        "D8_bias_check": "DONE (0 flips on the regenerated RECOVERED "
                         "items; raw bytes committed; the PARTIAL-body "
                         "extension typed)",
        "D2_third_family": "DONE (typed: 7 ids / 5 families all 403; "
                           "UNFUNDED direct transports; the ONE-"
                           "reminder flag for the funded credential)",
        "D3_agreement": "DONE (pre-registration committed before v16 "
                        "scoring)",
        "D4_gate_staging": "DONE (the auditor authors v16; the "
                           "candidate data staged)",
        "D7_xjtu_full": "TYPED BLOCKER (disk 5.7GB < 11GB; resume "
                        "condition recorded)",
    },
    "score_statement": ("score stands 7/10 per the ledger; NO "
                        "acceptance or score claim is made — the "
                        "score-8 and score-9 bars remain NOT MET and "
                        "the verdict is the auditor's"),
    "quota_disclosure": ("agnes: 2 generation calls (D8) + 2 cutoff-"
                         "probe-era... 0; zai: 4 judge calls; xkiro: "
                         "4 judge calls + 7 tiny D2 probe calls; "
                         "zero sealed bytes; all disclosed"),
    "typed_degradations": ("the pre-commit detect-secrets scan was "
                           "SKIPPED on the first commit (module "
                           "absent post-reprovision) — re-armed by "
                           "pip install before the later commits "
                           "(Art. 5 disclosure)"),
}
OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")
print("claims updated:", {k: v[0] for k, v in UPDATES.items()})
print("wrote", OUT)

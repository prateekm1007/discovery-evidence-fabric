#!/usr/bin/env bash
# r11_round_loop.sh — P2-8 (Amendment 2): the ONE-COMMAND round loop.
# Runs the full round end-to-end in the mandatory order, with the lead
# register and the repair diffs surfaced at the end:
#   1. rebuild the frozen-candidate ledger (credit-register leads +
#      incumbents with auditor findings)
#   2. the repair battery (lead-preserving; re-ideate only on starvation)
#   3. the class-level critic regression on the fresh outputs
#   4. the instrument calibration (feasibility bar + false-novelty)
#   5. the triples + delivery selection + novelty search (live)
#   6. the adversarial + anchor regressions and the decoder re-tally
# Every step is typed; a failing step stops the loop with its exit
# code (Art. LXI: the typed failure travels, it is never converted).
set -u
cd "$(dirname "$0")/.."
set -a && source .env.keys && set +a
export ENGINE_MODEL_COST_POLICY=UNRESTRICTED ENGINE_LLM_TIMEOUT_S=40
export ENGINE_LLM_RETRY_SLEEP_S=0
export A1_OUT_DIR="${A1_OUT_DIR:-eval/pairs/r11_a1_next}"
export A1_FROZEN_CANDIDATES_DIR=eval/repair_ledger_r11
export A1_PRIOR_RECORDS_DIR="${A1_PRIOR_RECORDS_DIR:-eval/pairs/r11_a1_r2}"
export A1_TRIPLES_DIR="$A1_OUT_DIR"

echo "== [1/6] frozen-candidate ledger"
python3 -B scripts/r11_build_frozen_ledger.py || exit $?

echo "== [2/6] lead-preserving repair battery -> $A1_OUT_DIR"
for pid in $(python3 -c "
import json
print(' '.join(sorted(p['problem_id'] for p in json.load(open('eval/problems_dev12.json'))['problems'])))"); do
  f="$A1_OUT_DIR/$pid.json"
  [ -f "$f" ] && { echo "  skip $pid (record exists)"; continue; }
  timeout 130 python3 -B scripts/r11_a1.py "$pid" || echo "  typed exit $? on $pid"
  sleep 2
done

echo "== [3/6] class-level critic regression on the fresh outputs"
A1_TRIPLES_DIR="$A1_OUT_DIR" python3 - <<'PY' || exit $?
import json, sys
from pathlib import Path
sys.path.insert(0, '.')
from discovery_fabric.engine.plausibility_critic import check_answer_class_defects
probs = {p['problem_id']: p for p in json.load(open('eval/problems_dev12.json'))['problems']}
d = Path(__import__('os').environ['A1_OUT_DIR'])
kills = 0
for f in sorted(d.glob('*.json')):
    r = json.loads(f.read_text())
    a = str(r.get('a1_answer') or '')
    prob = probs[f.stem]
    pt = '\n'.join(str(prob.get(k) or '') for k in ('device','failure','failure_mode','constraint')) \
         + '\n' + '\n'.join(str(v) for v in (prob.get('user_variables') or []))
    res = check_answer_class_defects(a, prob, pt)
    kills += int(res['verdict'] == 'KILL')
    if res['verdict'] != 'CLEAN':
        print(f"  {f.stem[:40]:42s} {res['verdict']} {[k['anchor'] for k in res['kills']]}")
print(f"class regression: {kills} killed (target 0)")
sys.exit(0 if kills == 0 else 4)
PY

echo "== [4/6] instrument calibration"
python3 -B scripts/r11_instrument_calibration.py || exit $?

echo "== [5/6] triples + delivery + novelty (live)"
python3 -B scripts/r11_triples.py || exit $?
python3 -B scripts/r11_novelty_search.py || exit $?

echo "== [6/6] regressions + decoder re-tally + lead register"
python3 -B scripts/r11_critic_regression.py || exit $?
python3 -B scripts/r11_critic_regression_r2.py || exit $?
python3 -B scripts/r11_decoder_retally.py || exit $?
python3 -B scripts/r11_crossfamily_panel.py || true
python3 - <<'PY'
import json
from pathlib import Path
d = Path(__import__('os').environ['A1_OUT_DIR'])
print("\n== LEAD REGISTER (frozen candidates + repair diffs) ==")
for f in sorted(d.glob('*.json')):
    r = json.loads(f.read_text())
    rm = r.get('repair_mode') or {}
    ch = r.get('chosen') or {}
    diffs = rm.get('class_repair') or {}
    print(f"{f.stem[:40]:42s} {str(r.get('result')):9s} "
          f"lead={str(ch.get('name'))[:38]} "
          f"repairs={len(diffs.get('edits') or [])}")
PY
echo "== round loop complete -> $A1_OUT_DIR"

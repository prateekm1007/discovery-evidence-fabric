#!/usr/bin/env bash
# Launch ONE visual-model benchmark run on HF Jobs (PRO credits).
# Usage: bash run_bench_job.sh <model-id> <case> <fixture-glb> <out-record>
# Verify current CLI flags with: hf jobs run --help
set -euo pipefail

MODEL_ID="${1:?model-id required}"
CASE="${2:?case required}"
FIXTURE="${3:?fixture-glb required}"
OUT="${4:?out record required}"
FLAVOR="${FLAVOR:-a100-80gb}"
RUNNER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

case "${CASE}" in
  case-A|case-B|case-C) ;;
  *) echo "case must be case-A, case-B or case-C" >&2; exit 2 ;;
esac

# License-blocked models (e.g. nvidia/PartPacker) additionally require:
#   INTERNAL_EVAL=1  -> research/internal evaluation only, stamped on the record
EXTRA_ARGS=()
if [[ "${INTERNAL_EVAL:-0}" == "1" ]]; then
  EXTRA_ARGS+=("--internal-eval-only")
fi

exec hf jobs run --flavor "${FLAVOR}" \
  python visual-lab/benchmark/runner_template.py \
    --model-id "${MODEL_ID}" \
    --case "${CASE}" \
    --fixture-glb "${FIXTURE}" \
    --registry visual-lab/registry/hf_visual_model_registry.json \
    --out "${OUT}" \
    "${EXTRA_ARGS[@]}"

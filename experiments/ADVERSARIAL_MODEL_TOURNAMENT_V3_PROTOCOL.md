# Adversarial Model Tournament V3 Protocol

**Frozen BEFORE first tournament API call.**

## Status
- V2 calibration: CALIBRATION_BLOCKED (Llama-3.1-8B, 34% accuracy, 60% false-kill rate)
- V3 objective: Select adversarial adjudication model empirically

## Oracle (unchanged)
- 35 cases from ADVERSARIAL_CALIBRATION_ORACLE_V1.json
- No rebuild, no post-hoc changes
- 7 categories × 5 cases

## Candidate Models
| ID | Model | Provider | Status |
|----|-------|----------|--------|
| A | meta/llama-3.1-8b-instruct | NVIDIA | Available (baseline) |
| B | z-ai/glm-5.2 | NVIDIA | Available |
| C | google/gemma-4-31b-it | NVIDIA | Available |
| D | deepseek-ai/deepseek-v4-pro | NVIDIA | UNAVAILABLE (HTTP 410) |
| E | deepseek-ai/deepseek-v4-flash-0731 | NVIDIA | UNAVAILABLE (timeout) |
| F | mistralai/mistral-medium-3.5-128b | NVIDIA | UNAVAILABLE (HTTP 410) |
| G | nvidia/nemotron-3-ultra-550b-a55b | NVIDIA | UNAVAILABLE (timeout) |
| H | qwen/qwen3-next-80b-a3b-instruct | NVIDIA | UNAVAILABLE (HTTP 410) |

## Configuration (identical for every model)
- Temperature: 0.0
- Max tokens: 8000
- Prompt: ATTACK_PROMPT (unchanged)
- System prompt: "You are a strict adversarial reviewer."
- V4 corrections: all wired

## Acceptance Gate
- Overall accuracy ≥ 80%
- Per-category accuracy ≥ 70%
- False-kill rate ≤ 20%
- Zero fabricated evidence
- Zero fabricated patent references
- Zero evaluator-failure-as-KILL
- Zero firewall violations

## Ranking Priority
1. False-kill rate (must be ≤20%)
2. Critical-category accuracy (must be ≥70%)
3. Overall accuracy (must be ≥80%)
4. Fabricated-evidence rate (must be 0)
5. Structured-output reliability
6. Latency (Pareto-optimal among passing)

## Prohibitions
- No cross-model voting, averaging, or correction
- No post-hoc oracle changes, prompt changes, or threshold changes
- No tuning of failing models
- No rerunning only failed categories

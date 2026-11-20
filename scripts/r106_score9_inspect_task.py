#!/usr/bin/env python3
"""r106_score9_inspect_task.py — the score-9 UNATTENDED 30-BATCH
harness, driven by Inspect AI (MIT, v0.3.291) — claim c-0127,
builder-r103s1.

HARNESS-OF-RECORD (typed): Inspect drives the batch (the dataset
assembly, the per-item solving, retries, the eval log, the scoring).
The GENERATOR rides Inspect's openai-api provider layer (the
registered agnes-3.0-flash route, api_key from the Art. 17 vault,
never a value in the code); the JUDGE seats stay ENGINE transports
(xkiro's browser-UA Cloudflare contract + the z-ai CLI are engine
custody per F63/Art. 17 — the typed reason they are not framework
providers). The protocol logic (sampling, prompts, parse contracts,
adjudication, acceptance arithmetic, the checkpoint schema) is ALL
engine (discovery_fabric/engine/rediscovery_protocol.py, F63).

ONE LOGICAL RUN (Art. 29(c)): the engine checkpoint
(/tmp/r106_score9_checkpoint.json) skips completed items; a resume
CONTINUES the same run — never double-serves.

UNATTENDED CONTRACT: no human enters the loop between the first
generation byte and the final record. interventions=0 is enforced by
the checkpoint counter and typed in the record.
"""
import asyncio
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from inspect_ai import Task, task                      # noqa: E402
from inspect_ai.dataset import Sample                  # noqa: E402
from inspect_ai.model import get_model, GenerateConfig  # noqa: E402
from inspect_ai.solver import Generate, solver             # noqa: E402
from inspect_ai.scorer import Score, scorer, Target    # noqa: E402

from discovery_fabric.engine import rediscovery_protocol as rp  # noqa
from discovery_fabric.engine import route_adapter as ra         # noqa

CORPUS = REPO / "eval/r106_score9_corpus/sampled_items.jsonl"
CHECKPOINT = Path("/tmp/r106_score9_checkpoint.json")
AGNES_BASE = "https://apihub.agnes-ai.com/v1"
AGNES_MODEL = "agnes-3.0-flash"
JUDGE_VISIBLE_TOKENS = 512
REASONING_HEADROOM = ra.REASONING_HEADROOM


def load_items():
    items = [json.loads(l) for l in
             CORPUS.read_text().strip().split("\n")]
    assert len(items) == rp.N_BATCH
    return items


import threading
_CP_LOCK = threading.Lock()


def ensure_checkpoint():
    with _CP_LOCK:
        cp = rp.load_checkpoint(CHECKPOINT)
        if cp is None:
            cp = rp.new_checkpoint()
            cp["run_id"] = "r106-score9-30batch"
            cp["interventions"] = 0
            CHECKPOINT.write_text(json.dumps(cp))
        return cp


def save_checkpoint(cp):
    # reload-before-save under the lock: concurrent solves merge their
    # own completed item into the FRESHEST on-disk state (a lost
    # update across items would silently shrink the ONE run)
    with _CP_LOCK:
        fresh = rp.load_checkpoint(CHECKPOINT)
        if fresh is not None:
            for k in ("usage", "typed_failures"):
                if k in cp:
                    merged = fresh.setdefault(k, {} if k == "usage"
                                              else [])
                    mine = cp[k]
                    if k == "usage":
                        for kk, vv in mine.items():
                            merged[kk] = max(int(merged.get(kk, 0)),
                                             int(vv))
                    else:
                        have = {(x.get("item_id"), x.get("seat"),
                                 x.get("state")) for x in merged}
                        for x in mine:
                            if (x.get("item_id"), x.get("seat"),
                                    x.get("state")) not in have:
                                merged.append(x)
            fresh["completed_items"].update(cp["completed_items"])
            cp = fresh
        CHECKPOINT.write_text(json.dumps(cp))


def vault_key(name):
    key = ra.resolve_vault_key(name)
    if not key:
        raise RuntimeError(f"typed custody refusal: {name} absent "
                           "from the vault (Art. 17)")
    return key


@solver(name="rediscovery_solver")
def rediscovery_solver():
    """Per-item: generation (Inspect provider layer, the registered
    route) -> two judge ratings (engine transports) -> engine
    adjudication. Checkpoint before and after every model byte."""

    async def solve(state, generate: Generate):
        cp = ensure_checkpoint()
        item = state.metadata["item"]
        item_id = item["item_id"]

        if item_id in cp["completed_items"]:
            done = cp["completed_items"][item_id]
            state.store.set("result", done)
            return state

        # ---- generation (the ONE generation per item, one run) ----
        prompt = rp.generator_prompt(item)
        gen_model = get_model(
            f"openai-api/agnes/{AGNES_MODEL}",
            base_url=AGNES_BASE,
            api_key=vault_key("AGNES_API_KEY"),
        )
        gen_out = await gen_model.generate(
            prompt,
            config=GenerateConfig(max_tokens=600 + REASONING_HEADROOM,
                                  temperature=0.0))
        gen_text = gen_out.completion
        cp["usage"]["agnes_calls"] += 1
        u = gen_out.usage or None
        cp["usage"]["agnes_tokens"] += int(getattr(u, "total_tokens", 0) or 0)
        try:
            gen = rp.parse_generator_output(gen_text)
        except ValueError as e:
            # the ONE repair retry (auditor direction 5, c-0129): a
            # mild-temperature repair call that sees its own raw
            # output + the typed parse error + the schema. Two
            # failures = typed exhaustion (the repair is DISCLOSED
            # in the item record, never silent).
            repair_attempted = True
            try:
                rep_model = get_model(
                    f"openai-api/agnes/{AGNES_MODEL}",
                    base_url=AGNES_BASE,
                    api_key=vault_key("AGNES_API_KEY"))
                rep_out = await rep_model.generate(
                    rp.repair_prompt(gen_text, str(e)[:300]),
                    config=GenerateConfig(
                        max_tokens=600 + REASONING_HEADROOM,
                        temperature=rp.REPAIR_TEMPERATURE))
                gen_text2 = rep_out.completion
                cp["usage"]["agnes_calls"] += 1
                cp["usage"]["agnes_repair_calls"] = \
                    cp["usage"].get("agnes_repair_calls", 0) + 1
                gen = rp.parse_generator_output(gen_text2)
            except ValueError as e2:
                done = {"item_id": item_id,
                        "state": "ITEM_GENERATION_PARSE_EXHAUSTION",
                        "detail": str(e2)[:200],
                        "repair_attempted": True,
                        "first_error": str(e)[:200],
                        "recovery": "PARTIAL"}
                cp["completed_items"][item_id] = done
                save_checkpoint(cp)
                state.store.set("result", done)
                return state

        # ---- judges (engine transports, two families) ----
        jp = rp.judge_prompt(item, gen)
        ratings = {}
        judge_fail = {"J1": False, "J2": False}

        def j1_call():
            out = "/tmp/r106_score9_j1.json"
            import subprocess
            r = subprocess.run(["z-ai", "chat", "-p", jp, "-o", out],
                               capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                raise RuntimeError(f"z-ai chat rc={r.returncode}: "
                                   f"{r.stderr[-160:]}")
            d = json.loads(Path(out).read_text())
            cp["usage"]["zai_calls"] += 1
            return d["choices"][0]["message"]["content"] or ""

        def j2_call():
            d = ra.xkiro_chat(
                [{"role": "user", "content": jp}],
                model="cohere/command-a",
                max_tokens=JUDGE_VISIBLE_TOKENS + REASONING_HEADROOM)
            cp["usage"]["xkiro_calls"] += 1
            cp["usage"]["xkiro_tokens"] += int(
                (d.get("usage") or {}).get("total_tokens") or 0)
            return d["content"]

        for seat, fn in (("J1", j1_call), ("J2", j2_call)):
            for attempt in (0, rp.RETRY_ONCE):
                try:
                    raw = await asyncio.to_thread(fn)
                    ratings[seat] = rp.parse_judge_output(raw)
                    judge_fail[seat] = False
                    break
                except Exception as e:
                    judge_fail[seat] = True
                    if attempt == rp.RETRY_ONCE:
                        ratings[seat] = None
                        cp.setdefault("typed_failures", []).append(
                            {"item_id": item_id, "seat": seat,
                             "state": "ITEM_RATING_FAIL",
                             "detail": str(e)[:200]})
            save_checkpoint(cp)

        rec_a = ratings.get("J1")
        rec_b = ratings.get("J2")
        a = rec_a["recovery"] if rec_a else None
        b = rec_b["recovery"] if rec_b else None
        adjudicated = rp.adjudicate(a, b)

        if judge_fail["J1"] and judge_fail["J2"]:
            item_state = "ITEM_RATING_FAIL_BOTH_SEATS"
        else:
            item_state = "OK"

        done = {
            "item_id": item_id,
            "state": item_state,
            "recovery": adjudicated,
            "judge_J1": ({"recovery": rec_a["recovery"],
                          "key_mechanism_gt": rec_a["key_mechanism_gt"],
                          "key_mechanism_gen": rec_a["key_mechanism_gen"],
                          "rationale": rec_a["rationale"]} if rec_a else None),
            "judge_J2": ({"recovery": rec_b["recovery"],
                          "key_mechanism_gt": rec_b["key_mechanism_gt"],
                          "key_mechanism_gen": rec_b["key_mechanism_gen"],
                          "rationale": rec_b["rationale"]} if rec_b else None),
            "generation": gen,
            "generation_sha16": __import__("hashlib").sha256(
                gen_text.encode()).hexdigest()[:16],
            "generation_raw": gen_text[:4000],
        }
        cp["completed_items"][item_id] = done
        save_checkpoint(cp)
        state.store.set("result", done)
        return state

    return solve


@scorer(metrics=[])
def recovery_scorer():
    async def score(state, target: Target):
        done = state.store.get("result")
        return Score(value=done.get("recovery", "PARTIAL")
                     if done else "NOT_RECOVERED",
                     answer=str(done.get("state")),
                     metadata={"item_id": (done or {}).get("item_id"),
                               "state": (done or {}).get("state")})
    return score


@task
def score9_rediscovery():
    items = load_items()
    return Task(
        dataset=[Sample(id=it["item_id"],
                        input=json.dumps(it["served"])[:200],
                        metadata={"item": it}) for it in items],
        solver=rediscovery_solver(),
        scorer=recovery_scorer(),
        name="score9_rediscovery",
    )


if __name__ == "__main__":
    from inspect_ai import eval as inspect_eval
    import os
    os.environ.setdefault("INSPECT_LOG_DIR",
                          str(REPO / "eval/r106_score9_inspect_logs"))
    logs = inspect_eval(score9_rediscovery(),
                        max_connections=1,
                        display="none")
    print("EVAL_DONE", len(logs))

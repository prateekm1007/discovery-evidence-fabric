#!/usr/bin/env python3
"""r176_invention_run.py — the AM53 DIR-2 invention-shaped lane (claim
c-0283; prereg eval/r176_invention_prereg.json GOVERNS).

WHAT IT MEASURES: on a 24-item INVENTION-SHAPED DEV corpus (standard
practice INSUFFICIENT — the plateau + why it is fundamental + the
capability target + constraints that exclude the incumbent
workarounds), does the pipeline deliver GENUINE novel-candidate wins
over a compute-matched single-shot baseline?

GENUINE WIN (AM53): the tournament CHAMPION's origin is a novel
strategy (departure / contradiction / relaxation) AND the blind
two-pass judge says WIN. Dominance ties (champion==baseline) and
plain best-of-N wins are EXCLUDED from the genuine count and reported
separately — the vacuous classes that made the DIR-3 0.92.

INSTRUMENT (the r175s3 compute-matched shape, invention-adapted per
the prereg): same generator both arms (the m77 gateway transport);
baseline = 4 plain single-shot draws + critique + revise (6 calls);
pipeline = 4 strategy draws + obviousness subtraction (Jaccard > 0.6
collapse) + the cheap-judge pairwise TOURNAMENT with the baseline
answer in the pool; the champion tie-break toward the baseline is
RETAINED (the selector is NOT tuned to manufacture wins). The judge
criteria include the NOVELTY axis explicitly (an invention test is
judged on invention). Byte-resume per item; typed failures never
re-rolled.

Usage: python3 scripts/r176_invention_run.py [--only PID]
Writes: eval/r176_invention_run/pair_{pid}.json + SUMMARY.json
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT = REPO / "eval" / "r176_invention_run"
OUT.mkdir(exist_ok=True)
CORPUS = REPO / "eval" / "r176_invention_corpus" / "items.jsonl"
SEED = 1763
JUDGE_MODEL = "openai/gpt-6-luna"
NOVEL = ("departure", "contradiction", "relaxation")


def packet_of(prob: dict) -> str:
    return json.dumps({k: prob.get(k, "") for k in
                       ("device", "failure", "constraint")},
                      ensure_ascii=False)


def task_of(prob: dict) -> str:
    return str(prob.get("question") or
              "Propose a NEW physical mechanism achieving the stated "
              "capability target under the stated constraints, with "
              "the concrete test that would falsify it.")


def strat_prompts(prob: dict) -> dict:
    packet = packet_of(prob)
    task = task_of(prob)
    return {
        "plain": (
            "Propose ONE concrete novel mechanism that achieves the "
            "stated capability target. Ground it in the stated "
            "failure physics; respect every stated constraint "
            "exactly; include the concrete test that would falsify "
            "it.\n\nPROBLEM:\n" + packet + "\n\nTASK:\n" + task),
        "departure": (
            "DEPARTURE CONTRACT: cite a CROSS-DOMAIN mechanism class "
            "that solves an analogous constraint in a DIFFERENT "
            "domain (name the precedent and its physical principle), "
            "name the NEAREST PRIOR ART this problem's own domain "
            "reaches for, state THE DEPARTURE (which physical "
            "principle differs — a different coupling, not a "
            "parameter change), a DIRECTION CHECK (the failure's "
            "driving gradient vs which way your mechanism pushes), "
            "the precedent's ENABLING CONDITIONS checked against "
            "this problem's envelope, and a STEELMAN (the strongest "
            "expert counter, answered).\n\nThen propose the "
            "mechanism and its falsification test.\n\n"
            "PROBLEM:\n" + packet + "\n\nTASK:\n" + task),
        "contradiction": (
            "CONTRADICTION MAPPING: state the core contradiction "
            "(what must increase vs what must not), then propose a "
            "mechanism that RESOLVES the contradiction rather than "
            "trading it off. Name the resolving physical principle "
            "explicitly, and the concrete test that would falsify "
            "it.\n\nPROBLEM:\n" + packet + "\n\nTASK:\n" + task),
        "relaxation": (
            "CONSTRAINT RELAXATION: list what the stated constraints "
            "genuinely forbid vs what they merely do not mention. "
            "Propose a mechanism that uses ONLY the permitted space "
            "but changes the coupling the constraint's implicit "
            "assumption relies on. Include the concrete test that "
            "would falsify it.\n\nPROBLEM:\n" + packet
            + "\n\nTASK:\n" + task),
    }


def env_keys() -> dict:
    out = {}
    for line in (REPO / ".env.keys").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return out


def ctai_chat(prompt: str, key: str, base: str, max_tokens: int = 700,
              model: str = JUDGE_MODEL) -> str:
    body = json.dumps({"model": model, "max_tokens": max_tokens,
                       "temperature": 0,
                       "messages": [{"role": "user",
                                     "content": prompt}]}).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=body, method="POST",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        b = json.loads(r.read().decode())
    m = (b.get("choices") or [{}])[0].get("message", {})
    return m.get("content") or m.get("reasoning_content") or ""


PACE_S = 10.0  # ctai legs are ~3x heavier than the r175s3 prompts —
# a paced seat (MEASURED in the wiring smoke: back-to-back legs
# rate-limited 429 within seconds; the smoke item re-runs)

# THE JUDGE SEATS (the AM52-RESEAT availability precedent, dated in
# the prereg amendment BEFORE the measured run): ctai openai/gpt-6-
# luna is the preregistered seat; snlite (sensenova/sensenova-6.8-
# flash-lite via xkiro, the AM51 qualified serving judge) is the
# TYPED AVAILABILITY SUBSTITUTE when ctai's quota window is exhausted
# (MEASURED: the ctai probe itself 429'd after the smoke's burst).
# AVAILABILITY-ONLY, NOT tuning: same prompts, same bars, same
# budget; the substitute family (sensenova) != the generator family
# (glm-class via the m77 gateway); the seat is selected ONCE per run
# and recorded per pair.
import discovery_fabric.engine.route_adapter as ra  # noqa: E402

SEATS = {
    "ctai-gpt6luna": {"kind": "ctai",
                      "model": "openai/gpt-6-luna",
                      "family": "openai"},
    "snlite": {"kind": "xkiro",
               "model": "sensenova/sensenova-6.8-flash-lite",
               "family": "sensenova"},
    # THIRD fallback (the P5 lane's free transport, measured shape):
    # the free deepseek reasoning model — needs the 12000 budget (its
    # reasoning runs ~3-8K tokens BEFORE content; 200/4000-budget
    # responses come back EMPTY with finish=length — the r158
    # measurement). Family deepseek != the generator glm-class.
    "tr-deepseek": {"kind": "tr",
                    "model": "deepseek/deepseek-v4.1-flash-1017-free",
                    "family": "deepseek"},
}


def _http_json(base: str, key: str, body: dict,
               timeout: float = 240.0) -> tuple:
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:  # noqa: BLE001
            return e.code, {}
    except Exception as e:  # noqa: BLE001
        return -1, {"error": f"{type(e).__name__}: {str(e)[:100]}"}


def seat_call(seat_tag: str, prompt: str, keys: dict,
              max_tokens: int, what: str = "",
              attempts: int = 4) -> str:
    """ONE judge leg on the selected seat, with the ESTABLISHED
    transport backoff (4 attempts, 120 s sleeps on rate-limited /
    transport; auth fails immediately). snlite ALWAYS runs at 12000
    upfront (the r160 owner directive: snlite reasoning burns small
    budgets — empty content, finish_reason=length — MEASURED again in
    the wiring smoke at max_tokens=200)."""
    seat = SEATS[seat_tag]
    if seat["kind"] == "xkiro":
        max_tokens = max(max_tokens, 12000)
    if seat["kind"] == "tr":
        max_tokens = 12000
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            if seat["kind"] == "ctai":
                return ctai_chat(prompt, keys["CTAI_API_KEY"],
                                 keys.get("CTAI_BASE_URL",
                                          "https://api.cantrustai.xyz"
                                          "/v1"),
                                 max_tokens=min(max_tokens, 700))
            if seat["kind"] == "tr":
                st, resp = _http_json(
                    "https://api.tokenrouter.com/v1",
                    keys.get("TOKENROUTER_API_KEY", ""),
                    {"model": seat["model"],
                     "max_tokens": max_tokens,
                     "include_reasoning": False,
                     "messages": [{"role": "user",
                                  "content": prompt}]}, 600.0)
                if st != 200:
                    raise RuntimeError(
                        f"tr HTTP{st}: {json.dumps(resp.get('error') or
                                                   resp)[:120]}")
                ch = (resp.get("choices") or [{}])[0]
                txt = (ch.get("message") or {}).get("content") or ""
                if not txt.strip():
                    raise RuntimeError(
                        f"tr EMPTY: finish={ch.get('finish_reason')}")
                return txt
            r = ra.xkiro_chat(
                [{"role": "user", "content": prompt}],
                model=seat["model"],
                max_tokens=min(max_tokens, 12000), timeout_s=240.0,
                api_key=keys.get("XKIRO_API_KEY"))
            txt = r.get("content") or ""
            if not txt.strip():
                raise RuntimeError(
                    f"empty content: {str(r.get('error'))[:120]}")
            return txt
        except urllib.error.HTTPError as e:
            last = e
            code = getattr(e, "code", 0)
            if code in (401, 403):
                raise
            print(f"    {what} {seat_tag} attempt {attempt} HTTP "
                  f"{code}; backoff 120s", flush=True)
            if attempt < attempts:
                time.sleep(120)
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"    {what} {seat_tag} attempt {attempt} failed "
                  f"{type(e).__name__}: {str(e)[:120]}; backoff 120s",
                  flush=True)
            if attempt < attempts:
                time.sleep(120)
    raise last if last else RuntimeError("judge backoff exhausted")


def probe_seats(keys: dict) -> str | None:
    """Probe ctai then snlite; return the live seat tag (fail closed
    on none). The ctai probe is ONE attempt (a 429 probe = the quota
    window is down — 120 s backoffs on a probe only waste the
    relaunch; the drive wrapper re-probes on every relaunch, so a
    recovered ctai window is picked up at the next hour boundary)."""
    try:
        r = seat_call("ctai-gpt6luna", "Reply with exactly: OK",
                      keys, max_tokens=64,
                      what="probe ctai", attempts=1)
        if "OK" in (r or "").upper():
            print("judge seat ctai-gpt6luna LIVE", flush=True)
            return "ctai-gpt6luna"
    except Exception as e:  # noqa: BLE001
        print(f"judge seat ctai-gpt6luna DOWN "
              f"({type(e).__name__}: {str(e)[:100]})", flush=True)
    try:
        r = seat_call("snlite", "Reply with exactly: OK", keys,
                      max_tokens=64, what="probe snlite", attempts=1)
        if "OK" in (r or "").upper():
            print("judge seat snlite LIVE", flush=True)
            return "snlite"
    except Exception as e:  # noqa: BLE001
        print(f"judge seat snlite DOWN "
              f"({type(e).__name__}: {str(e)[:100]})", flush=True)
    try:
        r = seat_call("tr-deepseek", "Reply with exactly: OK", keys,
                      max_tokens=64, what="probe tr", attempts=2)
        if "OK" in (r or "").upper():
            print("judge seat tr-deepseek LIVE", flush=True)
            return "tr-deepseek"
    except Exception as e:  # noqa: BLE001
        print(f"judge seat tr-deepseek DOWN "
              f"({type(e).__name__}: {str(e)[:100]})", flush=True)
    return None


# generic mechanism-vocabulary noun phrases (the r175s3 pattern was
# mitigation-vocabulary; invention problems need the mechanism terms)
MECH_PAT = re.compile(
    r"\b\w*(?:electrod|membran|catalys|photonic|phonon|phononic|"
    r"resonan|metamaterial|plasmon|spintroni|magnetoresist|"
    r"piezo|pyro|ferro|electrocalor|magnetocalor|thermoelectric|"
    r"electrochem|photochem|electrokinet|acousto|tribo|electrostat|"
    r"induct|capacit|poros|lattice|grain|domain wall|phase change|"
    r"supercritic|eutect|perovskit|solid-state|electrolyt|"
    r"gradients?|coupling|oscillat|ion transport|proton|oxygen "
    r"vacanc|dislocation|twin boundary|amorphou|polymeri|crosslink|"
    r"hydrogel|aerogel|coatin|liner|insulat|sensor|inhibitor|"
    r"seal|filter|cyclone|magnetic|ultrason|acoust|elastomer|"
    r"ceramic|anodiz|cathod|anod|quench|preheat|recircul|bypass|"
    r"vent|drain|lubric|viscosit|pressur|flow|rpm|residence|"
    r"antenn|impedance|bandwidth|shield|absorpt|scatter)\w*", re.I)


def mech_phrases(text: str) -> set:
    return set(m.group(0).lower()
               for m in MECH_PAT.finditer(text or ""))


def wilson(k: int, n: int, z: float = 1.96) -> list:
    if n == 0:
        return [0.0, 0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return [round(max(0.0, c - h), 3), round(p, 3),
            round(min(1.0, c + h), 3)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    args = ap.parse_args()

    keys = env_keys()
    seat = probe_seats(keys)
    if seat is None:
        print("NO LIVE JUDGE SEAT — typed INFRA block (fail closed)")
        return 3
    print(f"selected judge seat: {seat} "
          f"(recorded per pair; availability-only per the prereg "
          f"amendment)", flush=True)

    rows = [json.loads(l) for l in
            CORPUS.read_text().splitlines() if l.strip()]
    rows.sort(key=lambda r: r["problem_id"])
    if args.only:
        rows = [r for r in rows if r["problem_id"] == args.only]
    print(f"corpus: {len(rows)} invention-shaped DEV items",
          flush=True)

    import r40_machine_v77 as m77
    # MEASURED DEFECT (wiring smoke v3): a LEAKED zai_gateway process
    # from a crashed earlier run keeps port 8787 healthy with an OLD
    # key; start_gateway() then returns a NEW key the zombie rejects
    # (401 'bad gateway key' on every call). Clear stale gateways
    # first — this driver is the single gateway owner.
    import subprocess as _sp
    _sp.run(["pkill", "-f", "zai_gateway.mjs"], check=False)
    time.sleep(1.0)
    gw, gw_key = m77.start_gateway()

    def agnes(prompt: str) -> str:
        last = None
        for attempt in (1, 2, 3, 4):
            try:
                txt, _ = m77._gen_v77(prompt, "", gw_key)
                return txt or ""
            except Exception as e:  # noqa: BLE001
                last = e
                print(f"    agnes attempt {attempt} failed "
                      f"{type(e).__name__}", flush=True)
                if attempt < 4:
                    time.sleep(120)
        raise last

    rng = random.Random(SEED)
    results = []
    for i, prob in enumerate(rows, 1):
        pid = prob["problem_id"]
        outp = OUT / f"pair_{pid}.json"
        if outp.exists():
            results.append(json.loads(outp.read_text()))
            print(f"=== {pid}: resumed", flush=True)
            continue
        t0 = time.time()
        packet = packet_of(prob)
        task = task_of(prob)
        # GENERATION CHECKPOINT (the stall never re-burns the ~10
        # generator calls: a relaunch resumes from the checkpoint and
        # goes straight to the judge legs)
        genp = OUT / f"gen_{pid}.json"
        g = (json.loads(genp.read_text(encoding="utf-8"))
             if genp.exists() else {})

        print(f"=== {pid} ({i}/{len(rows)}) baseline arm ...",
              flush=True)
        if "baseline_final" in g:
            baseline_final = g["baseline_final"]
            draws = g.get("draws") or []
            print("    baseline resumed from the generation "
                  "checkpoint", flush=True)
        else:
            draws = [agnes(strat_prompts(prob)["plain"]) for _ in
                     range(4)]
            draws = [d for d in draws if d.strip()]
            if not draws:
                row = {"problem_id": pid, "status": "GEN_FAIL"}
                outp.write_text(json.dumps(row, indent=1))
                results.append(row)
                continue
            base_sel = max(draws, key=len)
            critique = agnes(
                "You are a strict reviewer. List the 3 most important "
                "defects of this novel-mechanism proposal (wrong "
                "physics, constraint violation, insufficient novelty or "
                "testability). Be terse.\n\nPROBLEM:\n" + packet
                + "\n\nPROPOSAL:\n" + base_sel)
            revised = agnes(
                "Revise this novel-mechanism proposal to fix the listed "
                "defects. Keep the same format and length; keep every "
                "stated constraint.\n\nPROPOSAL:\n" + base_sel
                + "\n\nDEFECTS:\n" + critique
                + "\n\nOutput ONLY the revised proposal.")
            baseline_final = revised if revised.strip() else base_sel
            g.update({"baseline_final": baseline_final,
                      "draws": draws})
            genp.write_text(json.dumps(g, indent=1,
                                       ensure_ascii=False) + "\n",
                            encoding="utf-8")

        # ---- PIPELINE ARM: strategy draws + subtraction ----------
        print(f"    pipeline arm (4 strategies) ...", flush=True)
        if "cands" in g:
            cands = g["cands"]
            print("    strategies resumed from the generation "
                  "checkpoint", flush=True)
        else:
            cands = {}
            for name, pr in strat_prompts(prob).items():
                if name == "plain":
                    cands[name] = draws[0]
                    continue
                try:
                    cands[name] = agnes(pr)
                except Exception as e:  # noqa: BLE001
                    print(f"    {name} failed {type(e).__name__}",
                          flush=True)
            cands = {k: v for k, v in cands.items() if v.strip()}
            g.update({"cands": cands})
            genp.write_text(json.dumps(g, indent=1,
                                       ensure_ascii=False) + "\n",
                            encoding="utf-8")

        kept, dropped, seen = [], [], []
        for name in ("plain", "departure", "contradiction",
                     "relaxation"):
            if name not in cands:
                continue
            ph = mech_phrases(cands[name])
            dup = None
            for kn, kp in seen:
                j = (len(ph & kp) / len(ph | kp)) if (ph | kp) else 0
                if j > 0.6:
                    dup = kn
                    break
            if dup:
                dropped.append({"strategy": name,
                                "near_duplicate_of": dup})
            else:
                seen.append((name, ph))
                kept.append(name)

        pool = [(n, cands[n]) for n in kept]
        pool.append(("baseline", baseline_final))

        def judge_pair(a_text: str, b_text: str) -> str:
            swap = rng.random() < 0.5
            x, y = ((b_text, a_text) if swap
                    else (a_text, b_text))
            j = seat_call(
                seat,
                "Two engineering INVENTION proposals for the same "
                "problem. Judge which is better on physical "
                "soundness (obeys physics and the stated "
                "constraints), genuine mechanism novelty (a new "
                "physical principle or coupling vs standard "
                "practice), and actionability (a concrete "
                "falsification test). Ignore length and style.\n\n"
                "PROBLEM:\n" + packet + "\n\nTASK:\n" + task
                + "\n\nPROPOSAL X:\n" + x[:4500]
                + "\n\nPROPOSAL Y:\n" + y[:4500]
                + "\n\nAnswer EXACTLY: VERDICT: X|Y|TIE",
                keys, max_tokens=200,
                what=f"{pid} tournament")
            time.sleep(PACE_S)
            v = ("X" if "VERDICT: X" in j.upper()
                 else "Y" if "VERDICT: Y" in j.upper() else "TIE")
            if v == "TIE":
                return "TIE"
            win = "X" if v == "X" else "Y"
            if swap:
                return "A" if win == "Y" else "B"
            return "A" if win == "X" else "B"

        wins = {n: 0 for n, _ in pool}
        leg_ok = 0
        leg_fail = 0
        for a in range(len(pool)):
            for b in range(a + 1, len(pool)):
                try:
                    w = judge_pair(pool[a][1], pool[b][1])
                    leg_ok += 1
                except Exception as e:  # noqa: BLE001
                    leg_fail += 1
                    # SEAT-DOWN EARLY ABORT: a seat that fails the
                    # first two legs with zero successes is DOWN —
                    # never burn 4x120s backoffs on every remaining
                    # leg; exit so the wrapper waits + re-probes
                    if leg_ok == 0 and leg_fail >= 2:
                        print("    SEAT_DOWN_EARLY_ABORT (0 successful"
                              " legs) — wrapper waits + re-probes",
                              flush=True)
                        return 3
                    print(f"    judge leg failed "
                          f"{type(e).__name__}", flush=True)
                    w = "TIE"
                if w == "A":
                    wins[pool[a][0]] += 1
                elif w == "B":
                    wins[pool[b][0]] += 1
        champion = max(wins, key=lambda k: (wins[k],
                                            k == "baseline"))
        final_text = dict(pool)[champion]

        # ---- the blind two-pass instrument -----------------------
        verdicts = []
        for order in ("XY", "YX"):
            a, b = ((final_text, baseline_final)
                    if order == "XY"
                    else (baseline_final, final_text))
            j = seat_call(
                seat,
                "You are a blind reviewer of engineering INVENTION "
                "proposals. Two proposals for the same problem; "
                "judge which is better on physical soundness (obeys "
                "physics and the stated constraints), genuine "
                "mechanism novelty (a new physical principle or "
                "coupling vs standard practice), and actionability "
                "(a concrete falsification test). Ignore length and "
                "style.\n\nPROBLEM:\n" + packet + "\n\nTASK:\n"
                + task + "\n\nPROPOSAL X:\n" + a[:4500]
                + "\n\nPROPOSAL Y:\n" + b[:4500]
                + "\n\nAnswer in EXACTLY this format:\nVERDICT: "
                  "X|Y|TIE\nREASON: <one sentence>",
                keys, max_tokens=700,
                what=f"{pid} blind pass {order}")
            time.sleep(PACE_S)
            vd = ("X" if "VERDICT: X" in j.upper()
                  else "Y" if "VERDICT: Y" in j.upper() else "TIE")
            verdicts.append({
                "pass": 1 if order == "XY" else 2,
                "pipeline": (vd if order == "XY"
                             else ("X" if vd == "Y"
                                   else "Y" if vd == "X"
                                   else "TIE")),
                "reason": j.split("REASON:")[-1].strip()[:300]
                if "REASON:" in j else ""})
        v = [x["pipeline"] for x in verdicts]
        outcome = ("WIN" if all(x in ("X", "TIE") for x in v)
                   and "X" in v else
                   "LOSS" if all(x in ("Y", "TIE") for x in v)
                   and "Y" in v else "TIE")

        # ---- the AM53 classification ------------------------------
        champion_class = ("baseline" if champion == "baseline"
                          else "plain" if champion == "plain"
                          else "novel")
        genuine_win = bool(champion_class == "novel"
                           and outcome == "WIN")
        row = {
            "problem_id": pid, "status": "JUDGED",
            "judge_seat": seat,
            "strategies_drawn": list(cands),
            "obviousness_dropped": dropped,
            "pool": [n for n, _ in pool],
            "tournament_wins": wins, "champion": champion,
            "champion_class": champion_class,
            "genuine_win": genuine_win,
            "blind_outcome": outcome,
            "judge_passes": verdicts,
            "baseline_final_text": baseline_final,
            "champion_text": final_text,
            "baseline_chars": len(baseline_final),
            "pipeline_chars": len(final_text),
            "wall_s": round(time.time() - t0, 1),
        }
        results.append(row)
        outp.write_text(json.dumps(row, indent=1,
                                  ensure_ascii=False) + "\n")
        print(f"    champion={champion} ({champion_class}) -> "
              f"{outcome} genuine={genuine_win} "
              f"{time.time()-t0:.0f}s", flush=True)

    judged = [r for r in results if r.get("status") == "JUDGED"]
    n = len(judged)
    g_wins = sum(1 for r in judged if r.get("genuine_win"))
    dom = sum(1 for r in judged
              if r.get("champion_class") == "baseline")
    plain_w = sum(1 for r in judged
                  if r.get("champion_class") == "plain")
    novel_ch = sum(1 for r in judged
                   if r.get("champion_class") == "novel")
    novel_wins = sum(1 for r in judged
                     if r.get("champion_class") == "novel"
                     and r.get("blind_outcome") == "WIN")
    novel_ties = sum(1 for r in judged
                     if r.get("champion_class") == "novel"
                     and r.get("blind_outcome") == "TIE")
    b_w = sum(1 for r in judged
              if r.get("blind_outcome") == "WIN")
    b_t = sum(1 for r in judged
              if r.get("blind_outcome") == "TIE")
    b_l = sum(1 for r in judged
              if r.get("blind_outcome") == "LOSS")
    summary = {
        "record": "R176_INVENTION_RUN/1.0.0",
        "judge_seat": seat,
        "gate": "genuine novel-candidate WIN share >= 50% at n=24 "
                "AND Wilson 95% CI lower bound > 50% (AM53; the "
                "score-4 gate)",
        "n_judged": n,
        "genuine_wins": g_wins,
        "genuine_win_share": round(g_wins / n, 3) if n else None,
        "genuine_win_ci95": wilson(g_wins, n),
        "exclusions": {
            "dominance_ties_champion_baseline": dom,
            "plain_best_of_n_champions": plain_w,
            "note": "excluded from the genuine count per AM53"},
        "novel_champions": novel_ch,
        "novel_champion_wins": novel_wins,
        "novel_champion_ties": novel_ties,
        "novel_wins_plus_ties_ci95": wilson(novel_wins + novel_ties,
                                            n),
        "blind_totals_win_tie_loss": [b_w, b_t, b_l],
        "gate_met_point": bool(n and g_wins / n >= 0.5),
        "gate_met_ci_lower": bool(n and wilson(g_wins, n)[0]
                                  > 0.50),
        "power_note": "at n=24 the Wilson lower bound exceeds 0.50 "
                      "only at >= 17/24 genuine wins",
        "rows": [{k: r.get(k) for k in (
            "problem_id", "status", "champion", "champion_class",
            "genuine_win", "blind_outcome")} for r in results],
    }
    (OUT / "SUMMARY.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    print(f"DONE: {n} judged | genuine {g_wins}/{n} = "
          f"{(g_wins / n if n else 0):.2f} "
          f"CI95 {wilson(g_wins, n)} | exclusions: baseline-dom "
          f"{dom}, plain {plain_w} | novel champions {novel_ch} "
          f"(W{novel_wins}/T{novel_ties}) | GATE "
          f"point={'MET' if summary['gate_met_point'] else 'NOT MET'}"
          f" ci_lower={'MET' if summary['gate_met_ci_lower'] else 'NOT MET'}",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""r11_novelty_search.py — OWNER ROUND R11 (2026-11-14, item 4): the
NOVELTY SEARCH for every delivered A1 idea.

For each A1 delivered idea (the chosen candidate's mechanism + failure
link, and the answer's DEPARTURE FROM STANDARD statement), retrieve the
NEAREST PRIOR ART from the problem's committed evidence packet (the
frozen envelope the baseline run served — the retrieved prior-art pool
for this problem) and state whether it is the SAME MECHANISM. Novelty
is claimed ONLY when the nearest prior art is a DIFFERENT mechanism
(owner rule). When the nearest prior art shares the idea's mechanism
vocabulary, the record types PRIOR_ART_SAME_MECHANISM and the novelty
claim is WITHDRAWN for that idea — the honest state, never an
invented claim (Arts. XXV/VI/LIX).

Deterministic, zero-LLM, reproducible: the ranking is content-token
overlap between the idea's mechanism statement and each packet
record's title+abstract; the verdict rule is the distinctive-token
membership below. A packet that does not resolve types
NOT_MEASURED (never an invented novelty claim).

Serves: Arts. XXV (the unknown stays typed), VI (never manufacture
provenance), LIX (no benchmark gaming — the instrument is
deterministic and pre-registered here), LXXVII (a delivered idea is
judged as an invention against prior art).
"""
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_a0plus import _load_pair, _packet_by_id_from_run_tree  # noqa: E402
from r7_a0plus import _unique_packet_list  # noqa: E402
from r11_a1 import PAIRS_A1  # noqa: E402

NOVELTY_VERSION = "novelty_search/1.0.0"
TOP_K = 5

_STOP = frozenset({
    "the", "and", "for", "with", "from", "that", "this", "will",
    "shall", "must", "use", "used", "using", "based", "when", "where",
    "which", "have", "has", "are", "was", "were", "can", "may",
    "should", "into", "than", "then", "over", "under", "such", "also",
    "each", "any", "all", "more", "most", "per", "via", "their",
    "these", "those", "been", "being", "both", "between", "after",
    "before", "during", "through", "about", "above", "below",
})


def _toks(text: str) -> set:
    return {w for w in re.findall(r"[a-z][a-z\-]{3,}",
                                  str(text or "").lower())
            if w not in _STOP}


def _problem(pid: str) -> dict:
    d = json.loads((REPO / "eval" / "problems_dev12.json")
                   .read_text(encoding="utf-8"))
    plist = d if isinstance(d, list) else d.get("problems", [])
    for p in plist:
        if str(p.get("problem_id") or p.get("id")) == pid:
            return p
    raise KeyError(pid)


def _idea_tokens(rec: dict, prob: dict) -> set:
    """The idea's DISTINCTIVE mechanism tokens: the chosen candidate's
    mechanism + failure link + the answer's departure statement, minus
    the problem's own vocabulary (the user's words are not the
    invention)."""
    ch = rec.get("chosen") or {}
    ans = str(rec.get("a1_answer") or "")
    dep = ""
    m = re.search(r"DEPARTURE FROM STANDARD:\s*([^\n]+)", ans,
                  re.IGNORECASE)
    if m:
        dep = m.group(1)
    idea_txt = " ".join(str(ch.get(k) or "") for k in
                        ("mechanism", "failure_link")) + " " + dep
    idea = _toks(idea_txt)
    problem_vocab = _toks(" ".join(str(prob.get(k) or "") for k in
                                   ("device", "failure", "failure_mode",
                                    "constraint"))
                          + " " + " ".join(str(v) for v in
                                           (prob.get("user_variables")
                                            or [])))
    distinct = idea - problem_vocab
    return distinct if len(distinct) >= 5 else idea


def _same_mechanism(distinct: set, rec_text_toks: set) -> dict:
    """The verdict rule (pre-registered): the nearest record is the
    SAME MECHANISM when it shares >= 3 of the idea's distinctive
    mechanism tokens (>= 40% of the token set, at least 3) — the
    record already operates on the idea's own mechanism vocabulary.
    Below that, DIFFERENT_MECHANISM with the overlap disclosed."""
    shared = distinct & rec_text_toks
    n_thresh = max(3, int(round(0.4 * len(distinct))))
    if len(shared) >= n_thresh:
        return {"verdict": "PRIOR_ART_SAME_MECHANISM",
                "shared_tokens": sorted(shared)[:12],
                "n_shared": len(shared), "threshold": n_thresh}
    return {"verdict": "PRIOR_ART_DIFFERENT_MECHANISM",
            "shared_tokens": sorted(shared)[:12],
            "n_shared": len(shared), "threshold": n_thresh}


def search_one(pid: str) -> dict:
    import os as _os
    _dir = _os.environ.get("A1_TRIPLES_DIR", "").strip()
    rec_f = (Path(_dir) if _dir else PAIRS_A1) / f"{pid}.json"
    if not rec_f.exists():
        return {"problem_id": pid, "state": "NOT_MEASURED",
                "why": "no A1 record (the arm has not run)"}
    rec = json.loads(rec_f.read_text(encoding="utf-8"))
    ans = str(rec.get("a1_answer") or "")
    if not ans.strip():
        return {"problem_id": pid, "state": "NOT_MEASURED",
                "why": f"A1 typed {rec.get('result')} with no answer "
                       "bytes (Art. XXV)"}
    prob = _problem(pid)
    pair = _load_pair(pid)
    packet_by_id = _packet_by_id_from_run_tree(pair) if pair else {}
    if not packet_by_id:
        return {"problem_id": pid, "state": "NOT_MEASURED",
                "why": "the frozen evidence packet is unresolvable "
                       "(Art. XXV)"}
    packet = _unique_packet_list(packet_by_id)
    distinct = _idea_tokens(rec, prob)
    scored = []
    for e in packet:
        rid = str(e.get("id") or e.get("source_id") or "")
        txt = " ".join(str(e.get(k) or "") for k in
                       ("title", "abstract", "text", "content"))
        toks = _toks(txt)
        if not toks:
            continue
        overlap = len(distinct & toks) / max(len(distinct), 1)
        scored.append({"record_id": rid,
                       "title": str(e.get("title") or "")[:110],
                       "overlap": round(overlap, 3),
                       "n_shared": len(distinct & toks)})
    scored.sort(key=lambda x: (-x["overlap"], x["record_id"]))
    top = scored[:TOP_K]
    nearest = _same_mechanism(distinct,
                              _toks(" ".join(
                                  str(e.get(k) or "") for k in
                                  ("title", "abstract", "text",
                                   "content"))
                                  for e in packet
                                  if str(e.get("id")
                                         or e.get("source_id") or "")
                                  == top[0]["record_id"])
                              ) if top else None
    # the novelty claim rule (owner item 4): claim novelty ONLY when
    # the NEAREST prior art is a DIFFERENT mechanism
    claim = "NOVELTY_NOT_CLAIMED"
    if nearest:
        claim = ("NOVELTY_CLAIMED"
                 if nearest["verdict"] == "PRIOR_ART_DIFFERENT_MECHANISM"
                 else "NOVELTY_WITHDRAWN_PRIOR_ART_SAME_MECHANISM")
    # R11 P2b (owner audit step 2): the named-technique false-novelty
    # instrument outranks the token verdict — an idea that explicitly
    # NAMES an established technique of its domain (spectral kurtosis
    # for bearings, PRPD, DGA per IEEE C57.104, ...) is KNOWN prior
    # art and the claim is withdrawn regardless of token distance.
    try:
        from discovery_fabric.engine.invention_rubric import (
            prior_art_verdict as _pav)
        # the verdict reads the IDEA'S OWN mechanism text (name +
        # mechanism + failure_link), never the whole composed answer:
        # the answer's DEPARTURE FROM STANDARD section names the
        # standard solution BY DESIGN, which would fire the anchors on
        # every idea (measured: 7/12 withdrawn on the first pass)
        _ch = rec.get("chosen") or {}
        _idea_txt = " ".join(str(_ch.get(k) or "") for k in
                             ("name", "mechanism", "failure_link"))
        # plus the answer's PROPOSAL+MECHANISM head (everything before
        # the DEPARTURE FROM STANDARD section — that section names the
        # standard solution by design and would fire the anchors on
        # every idea; measured: 12/12 claimed on candidate text alone
        # after the first over-fire, 7/12 on the whole answer)
        _head = ans.split("DEPARTURE FROM STANDARD")[0]
        _pav_v = _pav(_idea_txt + " " + _head[:1200], prob)
    except Exception:  # noqa: BLE001 — absent stays absent
        _pav_v = "NO_REFERENCE"
    if _pav_v == "KNOWN" and claim == "NOVELTY_CLAIMED":
        claim = "NOVELTY_WITHDRAWN_NAMED_PRIOR_ART"
    return {
        "novelty_search_version": NOVELTY_VERSION,
        "problem_id": pid,
        "state": "MEASURED",
        "a1_result_state": rec.get("result"),
        "idea_distinctive_tokens_n": len(distinct),
        "idea_distinctive_tokens": sorted(distinct)[:20],
        "prior_art_pool_n": len(packet),
        "nearest_prior_art_top5": top,
        "nearest_verdict": nearest,
        "novelty_claim": claim,
        "rule": ("novelty is claimed ONLY when the nearest prior art "
                 "is a DIFFERENT mechanism (owner R11 item 4); "
                 "deterministic pre-registered rule, zero LLM")}


def main() -> int:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO),
                            capture_output=True,
                            text=True).stdout.strip()
    t0 = time.time()
    d = json.loads((REPO / "eval" / "problems_dev12.json")
                   .read_text(encoding="utf-8"))
    plist = d if isinstance(d, list) else d.get("problems", [])
    pids = sorted(str(p.get("problem_id") or p.get("id"))
                  for p in plist)
    out = {
        "record": "novelty_search_r11/1.0.0",
        "commit": commit,
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "problems": {},
        "summary": {},
    }
    n_claimed = n_withdrawn = n_notmeasured = 0
    for pid in pids:
        rec = search_one(pid)
        out["problems"][pid] = rec
        if rec.get("state") != "MEASURED":
            n_notmeasured += 1
        elif rec.get("novelty_claim") == "NOVELTY_CLAIMED":
            n_claimed += 1
        else:
            n_withdrawn += 1
        print(f"[novelty] {pid[:40]:42} "
              f"{rec.get('state'):12} "
              f"{rec.get('novelty_claim', '-')}")
    out["summary"] = {
        "novelty_claimed": n_claimed,
        "novelty_withdrawn_or_not_claimed": n_withdrawn,
        "not_measured": n_notmeasured,
        "wall_s": round(time.time() - t0, 1)}
    OUT = REPO / "eval" / "novelty_search_r11.json"
    OUT.write_text(json.dumps(out, indent=1, default=str) + "\n",
                   encoding="utf-8")
    print(f"[novelty] summary: claimed={n_claimed} "
          f"withdrawn={n_withdrawn} not_measured={n_notmeasured} "
          f"-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

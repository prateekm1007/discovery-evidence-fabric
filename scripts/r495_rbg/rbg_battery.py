#!/usr/bin/env python3
"""RBG certification battery — one repetition of the fixture corpus.

Fixture corpus discipline (Art. VIII: certification must attack itself; the
corpus is authored against provider reality + fixed mutation rules, never
from the verifier's own behavior; the verifier module never sees expected
verdicts). Every fixture that needs evidence resolves it LIVE from the
provider inside this repetition -- repetition-based measurement is the only
honest seal path, so nothing is cached across repetitions.

Fixtures:
  F1 positive byte verification        -> EVIDENCE_VERIFIED
  F2 hallucinated passage              -> EVIDENCE_REFUTED  (must fail)
  F3 metamorphic one-word mutation     -> EVIDENCE_REFUTED  (must fail)
  F4 wrong-source attribution          -> EVIDENCE_REFUTED  (must fail)
  F5 injected auth failure             -> RETRIEVAL_INCOMPLETE (never absence)
  F6 patent-blindness declaration      -> PATENT_BLIND declared per run
  F7 honest zero results               -> NO_COLLISION_FOUND + NOT-novelty annotation
  F8 positive collision adjudication   -> COLLISION_DETECTED

Run:  ELSEVIER_API_KEY=... python3 rbg_battery.py <repetition_id> <out_json>
Credentials via env injection only; never printed.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rbg_gate as g  # noqa: E402

# ---- fixed fixture constants (authored before any run; Art. VIII) ----
SEARCH_QUERY = 'TITLE("shunt valve")'
ANCHOR_TERMS = ["shunt", "valve", "hydrocephalus", "cerebrospinal"]
# F8 query correction (disclosed, Art. VII -- correcting the claim, never the
# verifier): the original 'TITLE("programmable shunt valve") AND
# TITLE("differential")' measured ZERO hits live (provider truth, recorded);
# a zero-hit query cannot demonstrate collision detection. Corrected to a
# query with measured nonzero coverage BEFORE any seal was claimed.
COLLISION_QUERY = 'TITLE("programmable shunt valve")'
ZERO_QUERY = 'TITLE("qqzzxxwbar9")'
HALLUCINATED_PASSAGE = ("In a 4,096-patient randomized trial the self-programming "
                        "valve eliminated obstruction entirely and restored normal "
                        "intracranial compliance in every subject.")
MUTATION_FROM = "valve"
MUTATION_TO = "valve (mutated)"


def custody(query, provider, state, extra=None):
    rec = {"query": query, "provider": provider, "transport_state": state,
           "at_utc": g._now()}
    if extra:
        rec.update(extra)
    return rec


def resolve_anchor_record(transport):
    """Shared step: fetch the top shunt-valve record (search path) and its
    text (independent abstract path). Returns (state, hit, text, custody)."""
    state, hits = transport.search(SEARCH_QUERY, count=3)
    if state != g.T_LIVE or not hits:
        return state, None, None, custody(SEARCH_QUERY, transport.name, state)
    hit = hits[0]
    fstate, text, meta = transport.fetch_record_text(hit["scopus_id"])
    return fstate, hit, text, custody(SEARCH_QUERY, transport.name, fstate, {
        "record_id": hit["scopus_id"], "fetch_response_sha256": meta.get("response_sha256"),
        "fetched_text_sha256": g.sha256(text) if text else None,
    })


def run_battery(repetition_id):
    rep = {"repetition_id": repetition_id,
           "started_utc": g._now(),
           "fixtures": [],
           "engine": "rbg_gate.py",
           "verdict_vocabulary": "no novelty verdict exists (Art. XLVI)"}
    t = g.ScopusTransport()

    def fixture(fid, description, expected, observed_verdict, passed, details):
        rep["fixtures"].append({
            "fixture_id": fid,
            "description": description,
            "expected_verdict": expected,
            "observed_verdict": observed_verdict,
            "pass": bool(passed),
            "details": details,
        })

    # ---- shared live evidence resolution ----
    astate, hit_a, text_a, cust_a = resolve_anchor_record(t)
    rep["anchor_record_custody"] = cust_a

    # F1 positive byte verification: claimant quotes the record's REAL title
    # (search-path field); the verifier binds it against the gate-fetched
    # text (abstract-path) -- a live cross-path byte consistency measurement.
    if astate == g.T_LIVE and hit_a and text_a:
        verdict, detail = g.verify_exact_passage(text_a, hit_a["title"])
        fixture("F1", "positive byte verification of the real record title",
                g.V_VERIFIED, verdict, verdict == g.V_VERIFIED,
                {"custody": cust_a, "verification": detail})
    else:
        fixture("F1", "positive byte verification of the real record title",
                g.V_VERIFIED, g.V_INCOMPLETE, False,
                {"reason": "anchor record unavailable", "custody": cust_a})

    # F2 hallucinated passage attributed to the same real record
    if astate == g.T_LIVE and text_a:
        verdict, detail = g.verify_exact_passage(text_a, HALLUCINATED_PASSAGE)
        fixture("F2", "hallucinated passage must fail byte verification",
                g.V_REFUTED, verdict, verdict == g.V_REFUTED,
                {"hallucinated_passage_sha256": g.sha256(HALLUCINATED_PASSAGE),
                 "verification": detail})
    else:
        fixture("F2", "hallucinated passage must fail byte verification",
                g.V_REFUTED, g.V_INCOMPLETE, False, {"reason": "anchor record unavailable"})

    # F3 metamorphic one-word mutation of the real title
    if astate == g.T_LIVE and hit_a and text_a:
        title = hit_a["title"]
        if MUTATION_FROM in title:
            mutated = title.replace(MUTATION_FROM, MUTATION_TO, 1)
            verdict, detail = g.verify_exact_passage(text_a, mutated)
            fixture("F3", "one-word metamorphic mutation must fail byte verification",
                    g.V_REFUTED, verdict, verdict == g.V_REFUTED,
                    {"mutation": {"from": MUTATION_FROM, "to": MUTATION_TO},
                     "mutated_sha256": g.sha256(mutated), "verification": detail})
        else:
            fixture("F3", "one-word metamorphic mutation must fail byte verification",
                    g.V_REFUTED, g.V_INDETERMINATE, False,
                    {"reason": "mutation anchor word absent from real title",
                     "title": title})
    else:
        fixture("F3", "one-word metamorphic mutation must fail byte verification",
                g.V_REFUTED, g.V_INCOMPLETE, False, {"reason": "anchor record unavailable"})

    # F4 wrong-source attribution: record A's title bound to record B's text
    if astate == g.T_LIVE and hit_a and text_a:
        state_b, hits_b = t.search(SEARCH_QUERY, count=3)
        hit_b = next((h for h in (hits_b or []) if h["scopus_id"] != hit_a["scopus_id"]), None)
        if state_b == g.T_LIVE and hit_b:
            fstate_b, text_b, meta_b = t.fetch_record_text(hit_b["scopus_id"])
            if fstate_b == g.T_LIVE and text_b:
                verdict, detail = g.verify_exact_passage(text_b, hit_a["title"])
                fixture("F4", "real passage attributed to a different real record must fail",
                        g.V_REFUTED, verdict, verdict == g.V_REFUTED,
                        {"claimed_record_id": hit_a["scopus_id"],
                         "verified_against_record_id": hit_b["scopus_id"],
                         "verification": detail})
            else:
                fixture("F4", "real passage attributed to a different real record must fail",
                        g.V_REFUTED, g.V_INCOMPLETE, False,
                        {"reason": "second record unavailable", "fetch_state": fstate_b})
        else:
            fixture("F4", "real passage attributed to a different real record must fail",
                    g.V_REFUTED, g.V_INCOMPLETE, False,
                    {"reason": "second hit unavailable", "search_state": state_b})
    else:
        fixture("F4", "real passage attributed to a different real record must fail",
                g.V_REFUTED, g.V_INCOMPLETE, False, {"reason": "anchor record unavailable"})

    # F5 injected auth failure -> typed INCOMPLETE, never absence (Art. IV/XXI.3)
    bad = g.ScopusTransport(api_key="RBG_INVALID_KEY_INJECTED_FOR_FIXTURE_F5")
    bad_state, _ = bad.search(SEARCH_QUERY, count=1)
    cv = g.collision_verdict(bad_state, any_relevant_hit=True, any_verified_hit=False)
    fixture("F5", "injected auth failure must yield typed INCOMPLETE, never absence",
            g.V_INCOMPLETE, cv,
            bad_state in (g.T_AUTH_FAILED, g.T_SEARCH_FAILED) and cv == g.V_INCOMPLETE,
            {"injected_transport_state": bad_state, "collision_verdict": cv})

    # F6 patent-blindness declaration per run (operator's stated alternative).
    # Both honest blindness states are accepted: RETRIEVAL_UNCONFIGURED (no
    # key injected) and TOKEN_OUT_OF_SCOPE (key present, measured 500/401 --
    # see R495_TRANSPORT_PROBE.json). Either way the run is patent-blind.
    lens = g.LensPatentTransport()
    decl = lens.blind_declaration()
    blind_ok = decl["status"] in ("TOKEN_OUT_OF_SCOPE", g.T_UNCONFIGURED)
    fixture("F6", "unscoped patent transport must declare PATENT_BLIND for the run",
            g.V_BLIND, decl["declaration"], blind_ok,
            {"declaration": decl})
    rep["patent_blindness_declaration"] = decl

    # F7 honest zero results: typed NO_RESULTS, verdict NO_COLLISION_FOUND,
    # with the explicit not-novelty annotation (Art. XXI.2 / XLVI / XXVIII)
    zstate, _ = t.search(ZERO_QUERY, count=1)
    zcv = g.collision_verdict(zstate, any_relevant_hit=False, any_verified_hit=False)
    fixture("F7", "verified zero results must be NO_COLLISION_FOUND with not-novelty annotation",
            g.V_NO_COLLISION, zcv,
            zstate in (g.T_NO_RESULTS, g.T_SEARCH_FAILED) and zcv == g.V_NO_COLLISION,
            {"query": ZERO_QUERY, "transport_state": zstate, "collision_verdict": zcv,
             "annotation": "NO_COLLISION_FOUND is not novelty; it states only that "
                           "this query matched zero records in this provider"})

    # F8 positive collision adjudication with byte-verified passage
    if astate == g.T_LIVE and hit_a and text_a:
        cstate, chits = t.search(COLLISION_QUERY, count=3)
        rel, verified = [], []
        per_hit = []
        if cstate == g.T_LIVE:
            for h in (chits or [])[:3]:
                relevance = g.adjudicate_relevance(h["title"], ANCHOR_TERMS)
                st, txt, meta = t.fetch_record_text(h["scopus_id"])
                v, d = g.verify_exact_passage(txt, h["title"]) if st == g.T_LIVE else (g.V_INCOMPLETE, {})
                entry = {"record_id": h["scopus_id"], "relevance": relevance,
                         "fetch_state": st, "byte_verdict": v,
                         "fetch_response_sha256": meta.get("response_sha256")}
                per_hit.append(entry)
                if relevance["relevant"]:
                    rel.append(h)
                if v == g.V_VERIFIED:
                    verified.append(h)
        cv = g.collision_verdict(cstate, bool(rel), bool(verified))
        fixture("F8", "real prior-art collision detected with byte-verified passage",
                g.V_COLLISION, cv, cv == g.V_COLLISION,
                {"query": COLLISION_QUERY, "transport_state": cstate,
                 "hits_adjudicated": per_hit})
    else:
        fixture("F8", "real prior-art collision detected with byte-verified passage",
                g.V_COLLISION, g.V_INCOMPLETE, False, {"reason": "anchor record unavailable"})

    rep["ended_utc"] = g._now()
    verdict_seq = [f["observed_verdict"] for f in rep["fixtures"]]
    rep["observed_verdict_sequence"] = verdict_seq
    rep["verdict_sequence_sha256"] = g.sha256("|".join(verdict_seq))
    rep["all_fixtures_pass"] = all(f["pass"] for f in rep["fixtures"])
    rep["reviewer_provenance"] = "AI_REVIEW"
    return rep


if __name__ == "__main__":
    rep_id = sys.argv[1] if len(sys.argv) > 1 else "R1"
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    record = run_battery(rep_id)
    blob = json.dumps(record, indent=2)
    if out_path:
        with open(out_path, "w") as fh:
            fh.write(blob)
    print(json.dumps({"repetition_id": rep_id,
                      "all_fixtures_pass": record["all_fixtures_pass"],
                      "verdict_sequence_sha256": record["verdict_sequence_sha256"],
                      "observed_verdicts": record["observed_verdict_sequence"]}))

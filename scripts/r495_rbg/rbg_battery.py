#!/usr/bin/env python3
"""RBG certification battery — one repetition of the fixture corpus.

Fixture corpus discipline (Art. VIII: certification must attack itself; the
corpus is authored against provider reality + fixed mutation rules, never
from the verifier's own behavior; the verifier module never sees expected
verdicts). Every fixture that needs evidence resolves it LIVE from the
provider inside this repetition -- repetition-based measurement is the only
honest seal path, so nothing is cached across repetitions.

Fixtures (v3 -- R497 disclosed fixture update, Art. VII: the provider
reality changed -- PatentBear measured LIVE -- and the corpus was
re-authored against the new reality, never silently; the v2 F6/F9
expectations are preserved in the R496 records and in git history):
  F1 positive byte verification        -> EVIDENCE_VERIFIED
  F2 hallucinated passage              -> EVIDENCE_REFUTED  (must fail)
  F3 metamorphic one-word mutation     -> EVIDENCE_REFUTED  (must fail)
  F4 wrong-source attribution          -> EVIDENCE_REFUTED  (must fail)
  F5 injected auth failure             -> RETRIEVAL_INCOMPLETE (never absence)
  F6 per-run coverage declaration      -> PATENT_COVERAGE_LIVE_THIS_RUN
       (v2 asserted PATENT_BLIND under the then-measured reality of no
        openable patent provider; v3 asserts the coverage statement now
        that a provider measures LIVE -- the same invariant, both sides
        of it: the declaration must always reflect measured reality)
  F7 honest zero results               -> NO_COLLISION_FOUND + NOT-novelty annotation
  F8 positive collision adjudication   -> COLLISION_DETECTED
  F9 present-but-unopenable credential -> BLINDNESS_RETAINED
       (v3 re-anchor: a GARBAGE pb_live_ key measured 401 at the tool
        layer must not unblind the run nor be reported live)
  F10 patent-leg positive adjudication -> COLLISION_DETECTED
       (patentbear search hit, relevance + record-level byte binding of
        the hit's title AND abstract against the independently fetched
        record text)
  F11 patent-leg hallucinated passage  -> EVIDENCE_REFUTED
       (a fabricated passage verified against the patent record text)
  F12 free-source substrate honesty    -> CORPUS_COVERAGE_LIVE_THIS_RUN
       (FULL-MODE ONLY, v4 R499: the keyless free-source layer self-
        measures live -- HF Hub catalog (a LISTING, count signal only),
        content-bearing HF datasets-server rows for the brief's flagship
        corpus, the Google patents-public-data GitHub substrate; the
        account-gated / unreachable / non-API free sources (EPO OPS,
        USPTO portal, PatentsView) must stay TYPED and never LIVE;
        coverage derives ONLY from the content-bearing measurement; the
        operator brief's 16.2M-row claim is recorded against the keyless
        served-view measurement as EXTERNAL_CLAIM_UNVERIFIED; the
        --patent-leg-only mode's contract is UNCHANGED -- it runs only
        F6/F9/F10/F11 as defined at R498)
  F13 corpus hallucination attack      -> CORPUS_ATTACK_REFUSED
       (FULL-MODE ONLY: a plausible-but-nonexistent dataset id must NOT
        type live and must not move the coverage statement -- Art. VIII
        attack, F11's discipline generalized to the corpus substrate)

QUOTA DISCIPLINE (R497, Art. LXXIII): the provider meters every
successful call (free plan 20/month). Per repetition the PatentBear leg
spends exactly 2 debits: the layer self-measurement search (payload
REUSED by F10 -- no second search) and ONE record fetch. F9's garbage-key
call is measured 401 and does not debit (measured). Every usage object
is ledgered in the repetition record.

Run:  ELSEVIER_API_KEY=... PATENTBEAR_API_KEY=... python3 rbg_battery.py <repetition_id> <out_json> [--patent-leg-only]
Credentials via env injection only; never printed.

MODE (v3.1, R498 -- disclosed instrument MODE extension, Art. VII: no
fixture is re-authored, no expectation is changed; only the run scope):
  --patent-leg-only  run ONLY the patent-leg fixtures (F6, F9, F10, F11)
    when the Scopus credential is absent from every LXXIII store. The
    Scopus fixtures are recorded as SKIPPED_UNCONFIGURED_THIS_RUN with
    pass=null -- a skip is never a pass and never a fail -- and are
    excluded from the verdict sequence. The record explicitly references
    the R495 full-battery seal for the Scopus side and never re-claims
    it. This mode exists because quota windows and credential
    availability are per-leg constraints (R497: the seal was typed
    SEAL_NOT_CLAIMED_QUOTA_INFEASIBLE while the Scopus side stood sealed
    3/3 from R495); a mode that cannot measure a leg must not silently
    fail it (Art. LXI) nor silently pass it (Art. IV).
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
# F11 patent-leg hallucination (fixed constant, authored before any run;
# Art. VIII): a fabricated claim about the shunt-valve patent record that
# must fail byte verification against the gate-fetched patent record text.
PB_HALLUCINATED_PASSAGE = ("The patented shunt assembly was validated in a "
                           "multicenter trial of 2,304 patients and reduced "
                           "occlusion events to zero across all sites.")
# F13 corpus hallucination (fixed constant, authored before any run;
# Art. VIII): a syntactically plausible but NONEXISTENT dataset id in the
# toscanini namespace. Measured reality (R499 smoke): datasets-server
# answers 403 (AUTH_FAILED) for nonexistent ids, not 404 -- the fixture
# accepts ANY typed non-live state, and the measured state is recorded.
HALLUCINATED_DATASET = "toscanini-rbg/nonexistent-patent-corpus-f13"
# The typed-state vocabulary of the free-source layer (F12 honesty set).
TYPED_STATE_VOCABULARY = frozenset({
    "LIVE_200", "AUTH_FAILED", "SEARCH_FAILED", "RETRIEVAL_UNCONFIGURED",
    "NO_RESULTS", "NOT_FOUND", "DNS_UNRESOLVED_THIS_ENVIRONMENT",
    "WEB_SHELL_NOT_JSON_API", "CREDENTIAL_REQUIRED"})


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


# Scopus-side fixture registry for the patent-leg-only mode (the SAME
# ids/descriptions/expected verdicts as the full battery -- a single
# source of truth; the mode records skips against this registry).
SCOPUS_FIXTURE_DEFS = [
    ("F1", "positive byte verification of the real record title", g.V_VERIFIED),
    ("F2", "hallucinated passage must fail byte verification", g.V_REFUTED),
    ("F3", "one-word metamorphic mutation must fail byte verification", g.V_REFUTED),
    ("F4", "real passage attributed to a different real record must fail", g.V_REFUTED),
    ("F5", "injected auth failure must yield typed INCOMPLETE, never absence", g.V_INCOMPLETE),
    ("F7", "verified zero results must be NO_COLLISION_FOUND with not-novelty annotation", g.V_NO_COLLISION),
    ("F8", "real prior-art collision detected with byte-verified passage", g.V_COLLISION),
]

# Patent-leg fixture registry for the corpus-leg-only mode (the SAME
# ids/descriptions/expected verdicts as the full battery -- a single
# source of truth; the mode records skips against this registry).
PATENT_LEG_FIXTURE_DEFS = [
    ("F6", "with a LIVE patent provider the per-run declaration must be a "
           "PATENT_COVERAGE_LIVE_THIS_RUN coverage statement, not blindness",
     g.T_COVERED),
    ("F9", "present-but-unopenable credential must not unblind the run",
     "BLINDNESS_RETAINED"),
    ("F10", "patent-leg collision adjudication with byte-verified passage",
     g.V_COLLISION),
    ("F11", "hallucinated patent passage must fail byte verification",
     g.V_REFUTED),
]


def run_battery(repetition_id, patent_leg_only=False, corpus_leg_only=False):
    rep = {"repetition_id": repetition_id,
           "started_utc": g._now(),
           "fixtures": [],
           "engine": "rbg_gate.py",
           "battery_version": ("4.1" if corpus_leg_only else "4"),
           "battery_mode": ("corpus_leg_only" if corpus_leg_only else
                            ("patent_leg_only" if patent_leg_only else "full")),
           "battery_version_note": "v4 (R499): operator directive 'use huggingface and "
                                   "other free sources' -> disclosed fixture update "
                                   "(Art. VII): FreePatentSourceLayer installed (keyless "
                                   "HF Hub catalog + content-bearing HF datasets-server "
                                   "rows + Google substrate + typed boundaries for EPO "
                                   "OPS / USPTO portal / PatentsView), F12/F13 added as "
                                   "FULL-MODE fixtures (keyless, zero debits); the "
                                   "--patent-leg-only mode contract is unchanged from "
                                   "v3.1. v4.1 (R502) = MODE extension only "
                                   "(--corpus-leg-only: F12/F13 ONLY, the Scopus + "
                                   "PatentBear legs recorded as "
                                   "SKIPPED_UNCONFIGURED_THIS_RUN out-of-scope "
                                   "skips, zero PatentBear debits spent, the "
                                   "standing R495/R498 leg seals referenced never "
                                   "re-claimed; the HF legs now attach the "
                                   "HF_TOKEN authenticated header when the "
                                   "environment holds it -- measured R504 both-modes-live "
                                   "on /splits, /rows and the Hub catalog). v3.1 (R498) = MODE extension only "
                                   "(--patent-leg-only, SKIPPED_UNCONFIGURED_THIS_RUN "
                                   "semantics, no fixture re-authored); v3 (R497) = "
                                   "PatentBear LIVE, F6 coverage assert + F9 measured-401 "
                                   "re-anchor + F10/F11 patent-leg fixtures; v2 (R496) = "
                                   "multi-provider layer + F9; v1 (R495) = single Lens "
                                   "class, 8 fixtures",
           "verdict_vocabulary": "no novelty verdict exists (Art. XLVI)",
           "patentbear_quota_ledger": [],
           "free_source_quota_note": "KEYLESS: the free-source layer spends zero "
                                     "metered debits (HF Hub + datasets-server are "
                                     "rate-limited but free; 429 handled by bounded "
                                     "backoff, transport robustness only)"}
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

    def skipped(fid, description, expected, reason=None, standing=None):
        rep["fixtures"].append({
            "fixture_id": fid,
            "description": description,
            "expected_verdict": expected,
            "observed_verdict": "SKIPPED_UNCONFIGURED_THIS_RUN",
            "pass": None,          # a skip is neither pass nor fail
            "skipped": True,
            "details": {
                "skip_reason": reason or (
                    "scopus transport unconfigured this run "
                    "(ELSEVIER_API_KEY absent from every LXXIII "
                    "store: session env, local vault, Space secret "
                    "surface names)"),
                "standing_seal_reference": standing or (
                    "R495/R495_RBG_SEAL_RECORD.json -- "
                    "the Scopus side stands sealed 3/3 from R495; "
                    "NOT re-measured this run and NEVER re-claimed "
                    "by a patent-leg-only record"),
            },
        })

    # ---- shared live evidence resolution (full mode only) ----
    if patent_leg_only or corpus_leg_only:
        _skip_reason = None if patent_leg_only else (
            "out of scope for --corpus-leg-only (mode scope: F12/F13 "
            "free-source corpus leg only)")
        _skip_standing = None if patent_leg_only else (
            "R498/R498_RBG_PATENT_LEG_SEAL_RECORD.json "
            "(patent leg 3/3, hash 2e0545a3...) + "
            "R495/R495_RBG_SEAL_RECORD.json (Scopus 3/3, hash db336e97...) "
            "-- both referenced, NEVER re-claimed by a corpus-leg record")
        for fid, desc, expected in SCOPUS_FIXTURE_DEFS:
            skipped(fid, desc, expected, reason=_skip_reason,
                    standing=_skip_standing)
        rep["anchor_record_custody"] = {
            "state": "SKIPPED_UNCONFIGURED_THIS_RUN",
            "note": (("corpus-leg-only mode: no Scopus call attempted; the "
                      "Scopus-side fixtures are skips, not failures (Art. LXI "
                      "-- a credential absence is never a scientific verdict)")
                     if corpus_leg_only else
                     ("patent-leg-only mode: no Scopus call attempted; the "
                      "Scopus-side fixtures are skips, not failures (Art. LXI "
                      "-- a credential absence is never a scientific verdict)")),
        }
        astate, hit_a, text_a, cust_a = None, None, None, None
    else:
        astate, hit_a, text_a, cust_a = resolve_anchor_record(t)
        rep["anchor_record_custody"] = cust_a

    if not patent_leg_only and not corpus_leg_only:
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

    if corpus_leg_only:
        # v4.1 --corpus-leg-only (R502, Art. VII disclosed MODE extension —
        # the v3.1 precedent: MODE only, no fixture re-authored, no
        # expectation changed): the Scopus + PatentBear legs are OUT OF
        # SCOPE this mode. No PatentBear transport is constructed and ZERO
        # metered debits are spent (the shared bucket stands 19/20, the
        # last debit preserved); the standing leg seals are referenced,
        # never re-claimed -- a scope the mode cannot measure is a skip,
        # never a pass and never a fail (Art. LXI).
        for _fid, _desc, _exp in PATENT_LEG_FIXTURE_DEFS:
            skipped(_fid, _desc, _exp,
                    reason="out of scope for --corpus-leg-only (mode scope: "
                           "F12/F13 free-source corpus leg only; zero "
                           "PatentBear debits spent)",
                    standing="R498/R498_RBG_PATENT_LEG_SEAL_RECORD.json "
                             "(patent leg 3/3, hash 2e0545a3...) + "
                             "R495/R495_RBG_SEAL_RECORD.json (Scopus 3/3, "
                             "hash db336e97...) -- both referenced, NEVER "
                             "re-claimed by a corpus-leg record")
        rep["patent_coverage_declaration"] = {
            "state": "OUT_OF_SCOPE_THIS_MODE",
            "note": "no provider transport constructed in corpus-leg mode; "
                    "no coverage statement exists in this mode's scope"}
    else:
        # F6 per-run coverage declaration (v3, Art. VII disclosed update): the
        # layer self-measures ALL registered providers; PatentBear now measures
        # LIVE, so the declaration MUST be None and the coverage statement MUST
        # read PATENT_COVERAGE_LIVE_THIS_RUN naming the live provider. The
        # invariant is unchanged from v2 -- the declaration reflects measured
        # reality, whichever way reality measures (v2 records preserve the
        # blindness side; v3 asserts the coverage side).
        layer = g.PatentTransportLayer()  # re-measures all providers live (1 PB debit)
        decl = layer.blind_declaration()
        pb_measurement = layer.measured.get("patentbear", {})
        if pb_measurement.get("usage"):
            rep["patentbear_quota_ledger"].append(
                {"call": "layer_self_measurement_search", "usage": pb_measurement["usage"]})
        covered_ok = (decl["declaration"] is None
                      and decl["coverage_statement"] == g.T_COVERED
                      and "patentbear" in decl["live_providers"]
                      and pb_measurement.get("status") == g.T_LIVE)
        fixture("F6", "with a LIVE patent provider the per-run declaration must be a "
                      "PATENT_COVERAGE_LIVE_THIS_RUN coverage statement, not blindness",
                g.T_COVERED, decl["coverage_statement"] or decl["declaration"], covered_ok,
                {"declaration": decl})
        rep["patent_coverage_declaration"] = decl
    
        # F9 adversarial (v3 re-anchor, same invariant): KEY PRESENCE IS NOT
        # TRANSPORT LIVENESS. A present-but-INVALID credential -- the garbage
        # pb_live_ key, measured HTTP 401 at the tool layer (R497 probe) -- must
        # NOT unblind the run and must NOT be reported as a live transport by
        # any surface. The injected layer holds ONLY the garbage key (other
        # providers unconfigured: no calls, no debits; the 401 itself debits
        # nothing -- measured).
        bad_layer = g.PatentTransportLayer(lens_key="", patsnap_key="",
                                           patentbear_key="pb_live_" + "0" * 43)
        bad_decl = bad_layer.blind_declaration()
        bad_pb = bad_layer.measured.get("patentbear", {})
        unblind_attempt = (bad_layer.status() != g.T_LIVE
                           and bad_layer.live_providers() == []
                           and bad_pb.get("status") == g.T_AUTH_FAILED
                           and bad_decl["declaration"] == "PATENT_BLIND_FOR_THIS_RUN")
        fixture("F9", "present-but-unopenable credential must not unblind the run",
                "BLINDNESS_RETAINED", "BLINDNESS_RETAINED" if unblind_attempt else "UNBLINDED_ILLEGITIMATELY",
                unblind_attempt,
                {"aggregate_status": bad_layer.status(),
                 "patentbear_measurement": bad_pb,
                 "attack_description": "coder treats key presence as transport liveness and "
                                       "silently drops the blindness declaration; v3 attack "
                                       "surface: the measured-401 garbage pb_live_ key"})
    
        if not patent_leg_only:
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
    
        # ---- patent-leg fixtures (v3, R497): the patent side is now LIVE, so
        # it carries the same standard of proof as the literature side: record-
        # level byte binding against gate-fetched provider text. QUOTA
        # DISCIPLINE: F10 reuses the layer self-measurement search payload (no
        # second search) and spends exactly ONE record fetch; F11 verifies
        # against the already-fetched text (zero extra calls).
    
        # F10 patent-leg positive adjudication: relevance + record-level byte
        # binding of the hit's title AND abstract (both cross-path, Art. II/III)
        pb_state = pb_measurement.get("status")
        pb_hits = pb_measurement.get("search_hits") or []
        pb_search_usage = pb_measurement.get("usage")
        text_p = None          # defined on every path (F11 guards on it)
        meta_p = {}
        if pb_state == g.T_LIVE and pb_hits:
            ranked = [(h, g.adjudicate_relevance(h["title"], ANCHOR_TERMS))
                      for h in pb_hits[:3]]
            chosen = next(((h, r) for h, r in ranked if r["relevant"]), None)
            if chosen is None:
                fixture("F10", "patent-leg collision adjudication with byte-verified passage",
                        g.V_COLLISION, g.V_INDETERMINATE, False,
                        {"reason": "no anchor-relevant hit in the measured top hits",
                         "hits_seen": [h["id"] for h in pb_hits[:3]],
                         "search_usage": pb_search_usage})
            else:
                hit_p, rel_p = chosen
                # QUOTA STEWARDSHIP GUARD (R497): the account's quota is shared
                # (concurrent operator usage measured between R497 probes and the
                # smoke run: 11 unaccounted debits) and the provider meters every
                # successful call. Never spend the account's last 2 debits: if
                # the measured remaining headroom is below 2, the record fetch is
                # refused as a TYPED INCOMPLETE (transport-availability guard,
                # Art. IV/LXI -- never a false pass, never a false absence; the
                # account owner keeps headroom). This guard cannot fabricate a
                # pass: it can only turn a would-be verdict into INCOMPLETE.
                usage = pb_search_usage if isinstance(pb_search_usage, dict) else {}
                remaining = usage.get("monthly_remaining")
                if isinstance(remaining, int) and remaining < 2:
                    fixture("F10", "patent-leg collision adjudication with byte-verified passage",
                            g.V_COLLISION, g.V_INCOMPLETE, False,
                            {"reason": "QUOTA_STEWARDSHIP_ABORT",
                             "measured_usage": usage,
                             "policy": "never spend the account's last 2 external-call "
                                       "debits; the record fetch is refused, typed "
                                       "INCOMPLETE, and the seal honestly fails",
                             "record_id_would_fetch": hit_p["id"]})
                else:
                    fstate_p, text_p, meta_p = g.PatentBearTransport().fetch_record_text(hit_p["id"])
                    if meta_p.get("usage"):
                        rep["patentbear_quota_ledger"].append(
                            {"call": "F10_record_fetch", "usage": meta_p["usage"]})
                    if fstate_p == g.T_LIVE and text_p:
                        v_title, d_title = g.verify_exact_passage(text_p, hit_p["title"])
                        v_abs, d_abs = g.verify_exact_passage(text_p, hit_p["abstract"])
                        verified_p = (v_title == g.V_VERIFIED and v_abs == g.V_VERIFIED)
                        cv_p = g.collision_verdict(pb_state, True, verified_p)
                        fixture("F10", "patent-leg collision adjudication with byte-verified passage",
                                g.V_COLLISION, cv_p, cv_p == g.V_COLLISION and verified_p,
                                {"provider": "patentbear", "query": g.PATENTBEAR_MEASURE_QUERY,
                                 "record_id": hit_p["id"], "relevance": rel_p,
                                 "byte_verdict_title": v_title, "byte_verdict_abstract": v_abs,
                                 "title_verification": d_title, "abstract_verification": d_abs,
                                 "fetch_meta": meta_p, "search_state": pb_state,
                                 "annotation": "the search count (num_hits) played NO role in "
                                               "this verdict (Art. XXI.1); the verdict rests on "
                                               "relevance + record-level byte binding"})
                    else:
                        fixture("F10", "patent-leg collision adjudication with byte-verified passage",
                                g.V_COLLISION, g.V_INCOMPLETE, False,
                                {"reason": "record fetch failed", "fetch_state": fstate_p,
                                 "fetch_meta": meta_p, "record_id": hit_p["id"]})
        else:
            fixture("F10", "patent-leg collision adjudication with byte-verified passage",
                    g.V_COLLISION, g.V_INCOMPLETE, False,
                    {"reason": "patentbear measurement not LIVE", "state": pb_state,
                     "search_usage": pb_search_usage})
    
        # F11 patent-leg hallucination: the fabricated patent claim must fail
        # byte verification against the same gate-fetched record text (zero
        # extra provider calls)
        if pb_state == g.T_LIVE and text_p:
            verdict_p, detail_p = g.verify_exact_passage(text_p, PB_HALLUCINATED_PASSAGE)
            fixture("F11", "hallucinated patent passage must fail byte verification",
                    g.V_REFUTED, verdict_p, verdict_p == g.V_REFUTED,
                    {"hallucinated_passage_sha256": g.sha256(PB_HALLUCINATED_PASSAGE),
                     "verified_against_record_id": meta_p.get("record_id"),
                     "verification": detail_p})
        else:
            fixture("F11", "hallucinated patent passage must fail byte verification",
                    g.V_REFUTED, g.V_INCOMPLETE, False,
                    {"reason": "patent record text unavailable for verification"})

    # ---- free-source substrate fixtures (v4, R499): the operator directive
    # "use huggingface and other free sources" installs the keyless free
    # sources as instrument surface. QUOTA DISCIPLINE: every call here is
    # keyless and spends ZERO PatentBear debits. FULL-MODE ONLY: the
    # --patent-leg-only mode contract (R498) is unchanged.
    if not patent_leg_only:
        # F12 free-source substrate honesty: the layer self-measures live; the
        # content-bearing HF rows measurement (real text, not a listing) must
        # be LIVE, the listing + substrate may corroborate, every state must be
        # TYPED, and the keyless boundaries must NEVER measure LIVE (F9's
        # invariant generalized: present-but-gated/unreachable/non-API stays
        # non-live on every surface).
        free_layer = g.FreePatentSourceLayer()
        free_m = free_layer.self_measure()
        free_decl = free_layer.coverage_declaration()
        rep["free_source_coverage_declaration"] = free_decl
        rep["free_source_measurements"] = free_m
        all_typed = all(v.get("state") in TYPED_STATE_VOCABULARY
                        for v in free_m.values())
        rows_m = free_m.get("hf_corpus_rows", {})
        catalog_m = free_m.get("hf_hub_catalog", {})
        substrate_m = free_m.get("google_github_substrate", {})
        content_live = (rows_m.get("state") == g.T_LIVE
                        and bool(rows_m.get("rows_returned"))
                        and rows_m.get("has_long_text_field") is True)
        catalog_live = (catalog_m.get("state") == g.T_LIVE
                        and (catalog_m.get("dataset_count_returned") or 0) >= 1)
        substrate_live = substrate_m.get("state") == g.T_LIVE
        keyless_never_live = all(
            v.get("state") != g.T_LIVE for k, v in free_m.items()
            if v.get("role") in ("KEYLESS_BOUNDARY_MEASUREMENT",
                                 "KEYLESS_SHAPE_MEASUREMENT",
                                 "ENVIRONMENT_REACHABILITY_MEASUREMENT"))
        f12_ok = (all_typed and content_live and catalog_live and substrate_live
                  and keyless_never_live
                  and free_decl["coverage_statement"] == g.CORPUS_COVERED)
        fixture("F12", "free-source substrate: content-bearing keyless coverage "
                      "measured LIVE, every state typed, gated sources never live",
                g.CORPUS_COVERED, free_decl["coverage_statement"], f12_ok,
                {"per_source_states": free_decl["per_source_states"],
                 "content_live": content_live, "catalog_live": catalog_live,
                 "substrate_live": substrate_live,
                 "keyless_never_live": keyless_never_live,
                 "all_typed": all_typed,
                 "coverage_rule": "coverage derives ONLY from the content-bearing "
                                  "row measurement; the catalog listing is a count "
                                  "signal, never coverage (Art. XXI.1 / LXXV.2)",
                 "brief_claim_verification": free_decl["brief_claim_verification"],
                 "measured_num_rows_served": free_decl["measured_num_rows_served"]})

        # F13 corpus hallucination attack: a plausible-but-nonexistent dataset
        # id must NOT type live and must NOT move the coverage statement (the
        # statement derives from the real measurement, never from the attack).
        h_state, _h_obj = free_layer.fetch_dataset_rows(
            HALLUCINATED_DATASET, "default", "train", length=1)
        decl_after = free_layer.coverage_declaration()
        attack_refused = (h_state != g.T_LIVE
                          and h_state in TYPED_STATE_VOCABULARY
                          and decl_after["coverage_statement"] == free_decl["coverage_statement"])
        fixture("F13", "hallucinated dataset id must not type live nor move the "
                      "coverage statement",
                "CORPUS_ATTACK_REFUSED",
                "CORPUS_ATTACK_REFUSED" if attack_refused else (
                    "HALLUCINATED_DATASET_MEASURED_LIVE" if h_state == g.T_LIVE
                    else "COVERAGE_STATEMENT_MOVED_BY_ATTACK"),
                attack_refused,
                {"hallucinated_dataset": HALLUCINATED_DATASET,
                 "measured_state": h_state,
                 "coverage_statement_before": free_decl["coverage_statement"],
                 "coverage_statement_after": decl_after["coverage_statement"],
                 "attack_description": "coder trusts a plausible dataset id because it "
                                       "looks well-formed; the layer must measure and "
                                       "type it, never assume (Art. LXXV.1: a patent "
                                       "match is evidence, never truth)"})

    rep["ended_utc"] = g._now()
    # The verdict sequence covers MEASURED fixtures only -- skipped
    # fixtures carry no verdict and contribute nothing to the sequence
    # hash (a skip is not a verdict; Art. XXV/LXI).
    measured = [f for f in rep["fixtures"] if not f.get("skipped")]
    verdict_seq = [f["observed_verdict"] for f in measured]
    rep["skipped_fixture_ids"] = [f["fixture_id"] for f in rep["fixtures"]
                                  if f.get("skipped")]
    rep["observed_verdict_sequence"] = verdict_seq
    rep["verdict_sequence_sha256"] = g.sha256("|".join(verdict_seq))
    rep["all_fixtures_pass"] = (bool(measured)
                                 and all(f["pass"] for f in measured))
    rep["reviewer_provenance"] = "AI_REVIEW"
    return rep


if __name__ == "__main__":
    rep_id = sys.argv[1] if len(sys.argv) > 1 else "R1"
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    patent_leg_only = "--patent-leg-only" in sys.argv
    corpus_leg_only = "--corpus-leg-only" in sys.argv
    if patent_leg_only and corpus_leg_only:
        print(json.dumps({"error": "--patent-leg-only and --corpus-leg-only "
                                    "are mutually exclusive modes"}))
        sys.exit(2)
    record = run_battery(rep_id, patent_leg_only=patent_leg_only,
                         corpus_leg_only=corpus_leg_only)
    blob = json.dumps(record, indent=2)
    if out_path:
        with open(out_path, "w") as fh:
            fh.write(blob)
    print(json.dumps({"repetition_id": rep_id,
                      "all_fixtures_pass": record["all_fixtures_pass"],
                      "verdict_sequence_sha256": record["verdict_sequence_sha256"],
                      "observed_verdicts": record["observed_verdict_sequence"]}))

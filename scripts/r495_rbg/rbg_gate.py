#!/usr/bin/env python3
"""RBG — the Retrieval-Backed Gate (R495 instrument package).

Closes the instrument gap named by the operator after the baseline-equivalence
miss: adjudication of novelty / prior-art-collision / baseline-equivalence
claims must be backed by live retrieval with byte-verified exact passages --
never by search counts, model opinion, or claimant-supplied source text.

Constitutional wiring (EPISTEMIC_CONSTITUTION.md v2.4.0, hash b54a1be9):
  Art. II   byte-exact evidence only; no fuzzy, no normalization, no "close
            enough". A claimed passage is verified only if it is an exact
            substring of the gate-fetched record text.
  Art. III  the verifier never trusts the claimant: the gate resolves record
            identity and fetches record text itself, from the provider.
  Art. IV   no fallback epistemology: transport failure, auth failure, or an
            unreachable byte-verifier produces typed INCOMPLETE states --
            never a PASS, never absence-as-evidence.
  Art. XXI  custody chain per result: query -> provider -> raw result sha256
            -> relevance decision (typed, string-level, conservative) ->
            record ID -> exact span -> hash. Provider failure is typed
            SEARCH_FAILED/AUTH_FAILED, never NO_RESULTS. Zero results is
            NO_RESULTS, never novelty.
  Art. XXV  unknown stays unknown: every unresolved state remains typed.
  Art. XLVI retrieval absence is not novelty proof: the verdict vocabulary
            contains NO "novel" verdict at all.
  Art. LXI  infrastructure failure states are distinct from scientific
            verdicts and are never converted into either.
  Art. LXX  English-only artifacts.

Reuses the canonical adjudication-state style (typed records, sha256
provenance, fail-closed defaults). This package creates no new registry,
state machine, or provenance system (operator constraints 39-41): its records
are intended to be ingested by the canonical gate machinery at the PRIOR-ART /
STATE-OF-THE-ART COLLISION stage of the canonical loop (Art. LV) and by the
external-audit #7 Novelty dimension. The patent side declares PATENT_BLIND
per run unless a scoped Lens (or equivalent patent) transport is configured:
the operator's stated alternative, "configure Lens or declare
patent-blindness per run", measured live in R495_TRANSPORT_PROBE.json.

Credentials arrive via environment injection only (ELSEVIER_API_KEY,
LENS_API_KEY); values are never printed, logged, or persisted.
"""

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

SCOPUS_SEARCH_URL = "https://api.elsevier.com/content/search/scopus"
SCOPUS_ABSTRACT_URL = "https://api.elsevier.com/content/abstract/scopus_id/"
LENS_PATENTS_URL = "https://api.lens.org/patents/search"
TIMEOUT_S = 45
RATE_LIMIT_HTTP = 429          # measured live at R495: burst calls hit 429
RATE_LIMIT_RETRIES = 2         # bounded; 429-only; transport robustness, never
RATE_LIMIT_BACKOFF_S = 3.0     # verdict semantics (Art. IV untouched)
POLITE_PACE_S = 1.1            # provider pacing between successive live calls

# Typed transport states (Art. XXI.3 / Art. LXI -- never silently collapsed)
T_LIVE = "LIVE_200"
T_AUTH_FAILED = "AUTH_FAILED"
T_SEARCH_FAILED = "SEARCH_FAILED"
T_UNCONFIGURED = "RETRIEVAL_UNCONFIGURED"
T_NO_RESULTS = "NO_RESULTS"

# Gate verdicts. There is deliberately NO "NOVEL" verdict (Art. XLVI):
# retrieval can detect collisions and verify passages; it can never prove
# novelty. NO_COLLISION_FOUND means exactly what it says -- no more.
V_VERIFIED = "EVIDENCE_VERIFIED"          # byte-exact passage bound to gate-fetched record
V_REFUTED = "EVIDENCE_REFUTED"            # claimed passage NOT present in gate-fetched record
V_COLLISION = "COLLISION_DETECTED"        # relevant hit + byte-verified passage overlap
V_NO_COLLISION = "NO_COLLISION_FOUND"     # verified coverage, zero relevant hits
V_INDETERMINATE = "INDETERMINATE"         # relevance not establishable by the deterministic instrument
V_INCOMPLETE = "RETRIEVAL_INCOMPLETE"     # transport failed -- unknown, NOT absence
V_BLIND = "PATENT_BLIND"                  # no scoped patent transport: declared per run


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _http_get(url, headers):
    """GET with bounded 429 backoff (transport robustness only: a rate-limit
    response is a provider state, never evidence; Art. XXI.3)."""
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            if e.code == RATE_LIMIT_HTTP and attempt < RATE_LIMIT_RETRIES:
                time.sleep(RATE_LIMIT_BACKOFF_S * (attempt + 1))
                continue
            return e.code, e.read()
        except Exception:  # noqa: BLE001 -- typed failure, never absence
            return None, b""
    return None, b""


def _http_post(url, body, headers):
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception:  # noqa: BLE001
        return None, b""


class ScopusTransport:
    """Live Elsevier Scopus literature retrieval (the verified-live channel)."""

    name = "scopus"

    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("ELSEVIER_API_KEY", "")

    def configured(self):
        return bool(self.api_key)

    def search(self, query, count=3):
        """Returns (state, hits). hits = [{scopus_id, title, doi}]."""
        if not self.configured():
            return T_UNCONFIGURED, []
        time.sleep(POLITE_PACE_S)
        url = (SCOPUS_SEARCH_URL + "?apiKey=" + urllib.parse.quote(self.api_key) +
               "&query=" + urllib.parse.quote(query) + "&count=%d" % count)
        code, raw = _http_get(url, {"Accept": "application/json",
                                    "User-Agent": "toscanini-rbg/1.0"})
        if code is None:
            return T_SEARCH_FAILED, []
        if code in (401, 403):
            return T_AUTH_FAILED, []
        if code != 200:
            return T_SEARCH_FAILED, []
        try:
            core = json.loads(raw).get("search-results", {})
            entries = core.get("entry", []) or []
            total = core.get("opensearch:totalResults", "0")
            embedded_errors = [e for e in entries
                               if isinstance(e, dict) and e.get("error")]
        except Exception:  # noqa: BLE001
            return T_SEARCH_FAILED, []
        # Provider zero semantics (measured live at R495): a successful query
        # with zero records returns total="0" AND entry=[{"error": "Result
        # set was empty"}]. That marker with total 0 is a TRUE ZERO (Art.
        # XXI.2), not a provider failure. A provider error with NONZERO or
        # absent total remains SEARCH_FAILED (Art. XXI.3).
        if str(total) == "0" and (not entries or
                                  len(embedded_errors) == len(entries)):
            return T_NO_RESULTS, []
        if embedded_errors:
            return T_SEARCH_FAILED, []
        hits = []
        for e in entries:
            if not isinstance(e, dict) or e.get("error"):
                continue
            ident = str(e.get("dc:identifier", ""))  # "SCOPUS_ID:XXXXXXXX"
            hits.append({
                "scopus_id": ident.split(":", 1)[-1] if ":" in ident else ident,
                "title": e.get("dc:title") or "",
                "doi": e.get("prism:doi") or "",
            })
        if not hits and str(total) == "0":
            return T_NO_RESULTS, []
        if not hits:
            return T_SEARCH_FAILED, []
        return T_LIVE, hits

    def fetch_record_text(self, scopus_id):
        """Independent record resolution (Art. III): the gate fetches the
        record itself by ID. Returns (state, text, meta)."""
        if not self.configured():
            return T_UNCONFIGURED, "", {}
        time.sleep(POLITE_PACE_S)
        url = (SCOPUS_ABSTRACT_URL + urllib.parse.quote(scopus_id) +
               "?apiKey=" + urllib.parse.quote(self.api_key) +
               "&field=title,abstract,dc:identifier,prism:doi")
        code, raw = _http_get(url, {"Accept": "application/json",
                                    "User-Agent": "toscanini-rbg/1.0"})
        meta = {"fetch_http": code,
                "response_sha256": sha256(raw.decode("utf-8", "replace")) if raw else None}
        if code is None:
            return T_SEARCH_FAILED, "", meta
        if code in (401, 403):
            return T_AUTH_FAILED, "", meta
        if code != 200:
            return T_SEARCH_FAILED, "", meta
        try:
            payload = json.loads(raw)
            rec = payload.get("abstracts-retrieval-response", {})
            core = rec.get("coredata", {})
            title = core.get("dc:title", "") or ""
            abstract = core.get("dc:description", "") or ""
            if isinstance(title, list):
                title = title[0] if title else ""
            if isinstance(abstract, list):
                abstract = abstract[0] if abstract else ""
        except Exception:  # noqa: BLE001
            return T_SEARCH_FAILED, "", meta
        if not (title or abstract):
            return T_SEARCH_FAILED, "", meta
        return T_LIVE, title + "\n" + abstract, meta


class LensPatentTransport:
    """Lens.org patent transport. Measured live at R495: the operator token
    carries no product scope (patents endpoint -> HTTP 500 'No product in
    scope'; scholarly endpoint -> HTTP 401). With no scoped patent transport,
    the patent side declares PATENT_BLIND per run -- the operator's stated
    alternative (configure Lens OR declare patent-blindness per run)."""

    name = "lens_patents"
    scoped = False  # measured 2026-09-18; see R495_TRANSPORT_PROBE.json attempt2/attempt3

    def configured(self):
        return bool(os.environ.get("LENS_API_KEY", ""))

    def status(self):
        if not self.configured():
            return T_UNCONFIGURED
        if not self.scoped:
            return "TOKEN_OUT_OF_SCOPE"
        return T_LIVE

    def blind_declaration(self):
        """The per-run patent-blindness declaration (Art. XXV: unknown stays
        unknown; Art. XLVI: blindness is never folded into a novelty claim)."""
        return {
            "transport": self.name,
            "status": self.status(),
            "declaration": "PATENT_BLIND_FOR_THIS_RUN",
            "consequence": "patent-side collision coverage for this run is UNKNOWN; "
                           "no novelty or collision verdict may rely on patent coverage",
            "measured_evidence": "R495_TRANSPORT_PROBE.json attempt2 lens 500 "
                                 "'No product in scope' / attempt3 scholarly 401",
            "probed_at_utc": _now(),
        }


def verify_exact_passage(gate_fetched_text, claimed_passage):
    """Art. II byte verification. Exact substring on the gate-fetched text.
    No normalization, no case folding, no whitespace collapsing, no fuzzy
    matching of any kind. Returns (verdict, detail)."""
    if not gate_fetched_text:
        return V_INCOMPLETE, {"reason": "no gate-fetched text to verify against"}
    if not claimed_passage:
        return V_REFUTED, {"reason": "empty claimed passage"}
    exact = claimed_passage in gate_fetched_text
    detail = {
        "claimed_passage_sha256": sha256(claimed_passage),
        "gate_fetched_text_sha256": sha256(gate_fetched_text),
        "claimed_passage_len": len(claimed_passage),
        "gate_fetched_text_len": len(gate_fetched_text),
        "byte_exact_substring": exact,
    }
    return (V_VERIFIED if exact else V_REFUTED), detail


def adjudicate_relevance(title, anchor_terms):
    """Deterministic, conservative, string-level relevance decision (Art.
    XXI.4). The decision is recorded AS STRING_LEVEL_RELEVANCE -- it never
    promotes itself beyond what it is (Art. XXVIII). A hit is relevant only
    if >= 1 anchor term occurs in the title."""
    t = title or ""
    matched = sorted({term for term in anchor_terms if term.lower() in t.lower()})
    return {"relevance_class": "STRING_LEVEL_RELEVANCE",
            "matched_anchor_terms": matched,
            "relevant": bool(matched)}


def collision_verdict(transport_state, any_relevant_hit, any_verified_hit):
    """Collision-layer verdict from transport + relevance + byte verification.
    Art. IV/LXI: transport failure -> INCOMPLETE (never NO_COLLISION).
    Art. XLVI: NO_COLLISION_FOUND is not novelty."""
    if transport_state in (T_SEARCH_FAILED, T_AUTH_FAILED, T_UNCONFIGURED):
        return V_INCOMPLETE
    if transport_state == T_NO_RESULTS:
        return V_NO_COLLISION  # verified-coverage zero: recorded as exactly this, nothing more
    if any_relevant_hit and any_verified_hit:
        return V_COLLISION
    if any_relevant_hit and not any_verified_hit:
        return V_INDETERMINATE
    return V_NO_COLLISION

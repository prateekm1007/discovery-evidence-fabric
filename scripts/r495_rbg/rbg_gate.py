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
external-audit #7 Novelty dimension. The patent side is SELF-MEASURING per
run across every registered provider (Lens, PatSnap, PatentBear): it
declares PATENT_BLIND unless at least one provider measures LIVE, and it
issues a PATENT_COVERAGE_LIVE_THIS_RUN coverage statement when one does.
Measured history: Lens out-of-scope (R495); PatSnap recognized-but-
unopenable (R496); PatentBear LIVE (R497 -- MCP JSON-RPC tools/call,
real-vs-garbage key boundary measured HTTP 401 at the tool layer on BOTH
search_patents and get_patent_record, cross-path byte verification of
search-hit title AND abstract inside the independently fetched record
text, and provider-documented quota metering: free plan 20 external
calls/month, usage object ledgered per call in R497_PATENTBEAR_PROBE3.json).

Credentials arrive via environment injection only (ELSEVIER_API_KEY,
LENS_API_KEY, PATSNAP_API_KEY, PATENTBEAR_API_KEY); values are never
printed, logged, or persisted.
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
# PatentBear MCP surface (measured live at R497; see R497_PATENTBEAR_PROBE*.json)
PATENTBEAR_MCP_URL = "https://www.patentbear.com/mcp"
PATENTBEAR_PROTOCOL_VERSION = "2025-06-18"
PATENTBEAR_PACE_S = 1.1
PATENTBEAR_MEASURE_QUERY = "shunt valve"   # anchor query family, fixed (Art. VIII)
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
# Per-run patent COVERAGE statement (R497). NOT a novelty verdict and not a
# relevance verdict (Art. XLVI/XXVIII): it states only that >= 1 patent
# provider measured LIVE this run, so record-level byte binding is available
# on the patent leg. Blindness and coverage are mutually exclusive.
T_COVERED = "PATENT_COVERAGE_LIVE_THIS_RUN"


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


class PatentBearTransport:
    """PatentBear MCP transport -- measured LIVE at R497.

    Surface (all measured, R497_PATENTBEAR_PROBE{,2,3}.json):
      - MCP JSON-RPC over POST at PATENTBEAR_MCP_URL; stateless (no
        Mcp-Session-Id observed); Bearer pb_live_ key.
      - initialize/tools/list are unauthenticated by design (33 tools were
        listed to a garbage key too) -- the credential boundary lives at
        tools/call: measured HTTP 401 for a garbage key on BOTH
        search_patents and get_patent_record, while the real key measures
        HTTP 200 with per-call usage accounting (the garbage-key attempts
        did not debit the real key's counter -- accounting is per key).
      - Every SUCCESSFUL call debits the account's monthly external-call
        quota (provider-documented: free 20 / Plus 500 / Pro & Team 5000);
        the usage object rides every response and is ledgered by the
        caller. Quota is a first-class custody field, not a side note.
      - search hits carry verbatim title+abstract; the R497 cross-path
        measurement verified BOTH byte-exact inside the independently
        fetched get_patent_record text (Art. II/III machinery on the
        patent leg).

    A LIVE search yields typed LIVE_200 with hits; num_hits is a COUNT
    SIGNAL ONLY (Art. XXI.1) -- relevance and collision verdicts are made
    only downstream, on record-level byte evidence.
    """

    name = "patentbear"

    def __init__(self, api_key=None):
        self.api_key = api_key if api_key is not None else \
            os.environ.get("PATENTBEAR_API_KEY", "")

    def configured(self):
        return bool(self.api_key)

    def _tools_call(self, tool, arguments):
        """One JSON-RPC tools/call. Returns (state, text, usage, http).
        401/403 -> AUTH_FAILED (the measured credential boundary); any other
        non-200 or unparseable payload -> SEARCH_FAILED (typed, never
        absence); an in-band isError -> SEARCH_FAILED with the error text
        preserved. The usage object is surfaced whenever present."""
        body = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        }).encode()
        headers = {"Content-Type": "application/json",
                   "Accept": "application/json, text/event-stream",
                   "User-Agent": "toscanini-rbg/1.0",
                   "Authorization": "Bearer " + self.api_key}
        time.sleep(PATENTBEAR_PACE_S)
        code, raw = _http_post(PATENTBEAR_MCP_URL, body, headers)
        usage = None
        if code in (401, 403):
            return T_AUTH_FAILED, "", usage, code
        if code is None or code != 200:
            return T_SEARCH_FAILED, "", usage, code
        try:
            payload = json.loads(raw.decode("utf-8", "replace"))
            items = (payload.get("result") or {}).get("content") or []
            text = "\n".join(c.get("text", "") for c in items
                             if isinstance(c, dict) and c.get("type") == "text")
            if (payload.get("result") or {}).get("isError"):
                return T_SEARCH_FAILED, text or "", usage, code
        except Exception:  # noqa: BLE001 -- typed failure, never absence
            return T_SEARCH_FAILED, "", usage, code
        try:
            usage = (json.loads(text) or {}).get("usage")
        except Exception:  # noqa: BLE001
            usage = None
        return T_LIVE, text or "", usage, code

    def search(self, query):
        """Returns (state, hits, usage). hits carry the provider's verbatim
        id/title/abstract fields -- no normalization (Art. II)."""
        if not self.configured():
            return T_UNCONFIGURED, [], None
        state, text, usage, http = self._tools_call("search_patents",
                                                    {"query": query})
        if state != T_LIVE:
            return state, [], usage
        try:
            payload = json.loads(text)
        except Exception:  # noqa: BLE001
            return T_SEARCH_FAILED, [], usage
        hits = payload.get("hits") or []
        if payload.get("num_hits", 0) == 0 and not hits:
            return T_NO_RESULTS, [], usage
        if not hits:
            return T_SEARCH_FAILED, [], usage
        clean = []
        for h in hits:
            if isinstance(h, dict) and h.get("id"):
                clean.append({"id": str(h["id"]),
                              "title": h.get("title") or "",
                              "abstract": h.get("abstract") or ""})
        if not clean:
            return T_SEARCH_FAILED, [], usage
        return T_LIVE, clean, usage

    def fetch_record_text(self, patentbear_id):
        """Independent record resolution (Art. III): the gate fetches the
        record itself by ID. Returns (state, text, meta)."""
        if not self.configured():
            return T_UNCONFIGURED, "", {}
        state, text, usage, http = self._tools_call(
            "get_patent_record", {"id": patentbear_id, "format": "text"})
        meta = {"record_id": patentbear_id, "fetch_http": http,
                "usage": usage,
                "fetched_text_sha256": sha256(text) if text else None,
                "fetched_text_len": len(text or "")}
        if state != T_LIVE:
            meta["state"] = state
            return state, "", meta
        if not text:
            return T_SEARCH_FAILED, "", meta
        # provider-side truncation markers are surfaced, never silently eaten
        meta["text_omitted_marker_present"] = ("text_omitted" in text)
        return T_LIVE, text, meta


PATSNAP_COUNT_URL = "https://connect.patsnap.com/search/patent/query-search-count"
LENS_PATENT_SEARCH_URL = "https://api.lens.org/patents/search"


class PatentTransportLayer:
    """Multi-provider patent transport (Lens + PatSnap), SELF-MEASURING at
    runtime -- provider statuses are never hardcoded claims, they are
    re-measured per run (repetition-based measurement discipline; Art. VI:
    no manufactured provenance).

    Measured history:
      Lens (R495): the operator token carries NO product scope -- patents
        endpoint HTTP 500 'No product in scope', scholarly 401.
      PatSnap (R496): the operator's sk- apikey is RECOGNIZED by the gateway
        (body error 67200202 'apikey auth error' vs 67200008 'apikey not
        Pass' for a garbage key) but completes NO auth exchange reachable
        from the session: /auth is gone (67200101 'Path Not Found'),
        /oauth/token rejects every standard grant (67200015 'Grant type
        error'), and the Space secret surface (names-only, Art. LXXIII)
        registers no companion app_id. KEY PRESENCE IS NOT TRANSPORT
        LIVENESS -- a present-but-unopenable credential must NOT unblind
        the run.
      PatentBear (R497): LIVE. The operator's pb_live_ key opens the MCP
        tools/call layer (search_patents, get_patent_record measured 200
        with usage accounting; a garbage key measures 401 on the same
        surface -- the boundary is measured, not assumed). The patent leg
        now carries record-level byte binding end to end.

    The operator's directive branch is 'configure Lens OR declare
    patent-blindness per run'; the layer declares PATENT_BLIND unless a
    provider measures LIVE. A LIVE PatSnap count endpoint yields a typed
    COUNT SIGNAL ONLY (Art. XXI.1: a count is not relevance and not
    novelty; record-level byte verification needs the record-list endpoint,
    which is not configured)."""

    name = "patent_layer"
    PATSNAP_RECOGNIZED = "KEY_RECOGNIZED_AUTH_NOT_OPENED"

    def __init__(self, lens_key=None, patsnap_key=None, patentbear_key=None,
                 measure=True):
        self.lens_key = lens_key if lens_key is not None else os.environ.get("LENS_API_KEY", "")
        self.patsnap_key = patsnap_key if patsnap_key is not None else os.environ.get("PATSNAP_API_KEY", "")
        self.patentbear_key = patentbear_key if patentbear_key is not None else \
            os.environ.get("PATENTBEAR_API_KEY", "")
        self.measured = {}
        if measure:
            self.measure()

    # ---- runtime measurement (re-measured every repetition; the
    #      PatentBear leg costs 1 quota debit by provider design) ----
    def measure(self):
        self.measured = {}
        self.measured["lens"] = self._measure_lens()
        self.measured["patsnap"] = self._measure_patsnap()
        self.measured["patentbear"] = self._measure_patentbear()
        return self.measured

    def _measure_patentbear(self):
        """Self-measurement of the PatentBear transport: ONE search_patents
        call (1 quota debit by provider design). The search payload is
        KEPT in the measurement entry so the battery's patent-side fixtures
        reuse it instead of spending additional quota (Art. LXXIII budget
        discipline; measured provider quota: free plan 20 calls/month)."""
        if not self.patentbear_key:
            return {"status": T_UNCONFIGURED, "evidence": "PATENTBEAR_API_KEY absent"}
        transport = PatentBearTransport(api_key=self.patentbear_key)
        state, hits, usage = transport.search(PATENTBEAR_MEASURE_QUERY)
        entry = {"status": state,
                 "evidence": "patentbear tools/call search_patents -> %s" % state,
                 "usage": usage}
        if state == T_LIVE:
            # verbatim provider fields; the count stays a COUNT SIGNAL (Art. XXI.1)
            entry["search_hits"] = hits
            entry["count_signal_only_note"] = \
                "num_hits is a count signal only; no verdict derives from it"
        elif state == T_AUTH_FAILED:
            entry["evidence"] = ("patentbear tools/call search_patents HTTP 401 -- "
                                 "key rejected at the measured tool-layer boundary")
        return entry

    def _measure_lens(self):
        if not self.lens_key:
            return {"status": T_UNCONFIGURED, "evidence": "LENS_API_KEY absent"}
        body = json.dumps({"query": {"match": "shunt valve"}, "size": 1, "from": 0}).encode()
        code, raw = _http_post(LENS_PATENT_SEARCH_URL, body,
                               {"Content-Type": "application/json",
                                "Authorization": "Bearer " + self.lens_key})
        if code == 200:
            return {"status": T_LIVE, "evidence": "lens patents/search HTTP 200"}
        detail = raw.decode(errors="replace")[:140] if raw else ""
        if "No product in scope" in detail:
            return {"status": "TOKEN_OUT_OF_SCOPE",
                    "evidence": "lens patents/search HTTP %d 'No product in scope'" % code}
        if code in (401, 403):
            return {"status": T_AUTH_FAILED, "evidence": "lens HTTP %d" % code}
        return {"status": T_SEARCH_FAILED, "evidence": "lens HTTP %s %s" % (code, detail)}

    def _measure_patsnap(self):
        if not self.patsnap_key:
            return {"status": T_UNCONFIGURED, "evidence": "PATSNAP_API_KEY absent"}
        time.sleep(POLITE_PACE_S)
        body = json.dumps({"collapse_order": "LATEST", "collapse_by": "PBD",
                           "collapse_type": "DOCDB",
                           "query_text": "TACD: shunt valve"}).encode()
        code, raw = _http_post(PATSNAP_COUNT_URL, body,
                               {"Authorization": "Bearer " + self.patsnap_key,
                                "Content-Type": "application/json"})
        try:
            payload = json.loads(raw) if raw else {}
        except Exception:  # noqa: BLE001
            payload = {}
        err = payload.get("error_code")
        if payload.get("status") is True and code == 200:
            count = (payload.get("data") or {}).get("count")
            return {"status": T_LIVE, "count_signal": count,
                    "evidence": "patsnap query-search-count HTTP 200 status=true count=%s" % count}
        if err == 67200202:
            return {"status": self.PATSNAP_RECOGNIZED,
                    "evidence": "patsnap HTTP %d 67200202 'apikey auth error' -- key "
                                "recognized, no reachable exchange (R496 probe)" % code}
        if err == 67200008:
            return {"status": T_AUTH_FAILED,
                    "evidence": "patsnap HTTP %d 67200008 'apikey not Pass'" % code}
        return {"status": T_SEARCH_FAILED,
                "evidence": "patsnap HTTP %s err=%s" % (code, err)}

    # ---- typed aggregate state (Art. XXV: unknowns stay typed) ----
    def status(self):
        if not self.measured:
            self.measure()
        states = [v["status"] for v in self.measured.values()]
        if T_LIVE in states:
            return T_LIVE
        if any(s in (T_UNCONFIGURED,) for s in states) and \
           all(s in (T_UNCONFIGURED,) for s in states):
            return T_UNCONFIGURED
        if any(s in (self.PATSNAP_RECOGNIZED, T_AUTH_FAILED, T_SEARCH_FAILED,
                     "TOKEN_OUT_OF_SCOPE") for s in states):
            return "AUTH_INCOMPLETE"
        return "AUTH_INCOMPLETE"

    def live_providers(self):
        if not self.measured:
            self.measure()
        return [k for k, v in self.measured.items() if v["status"] == T_LIVE]

    def blind_declaration(self):
        """The per-run patent-blindness/coverage declaration (Art. XXV/
        XXVIII/XLVI). FIRES whenever no provider measures LIVE -- including
        the adversarial case where credentials are present but no transport
        opens. When a provider DOES measure LIVE, the declaration is None
        and a PATENT_COVERAGE_LIVE_THIS_RUN coverage statement is issued in
        its place: the two states are mutually exclusive and neither is a
        novelty or relevance verdict."""
        live = self.live_providers()
        return {
            "transport": self.name,
            "status": self.status(),
            "live_providers": live,
            "provider_measurements": dict(self.measured),
            "declaration": "PATENT_BLIND_FOR_THIS_RUN" if not live else None,
            "coverage_statement": T_COVERED if live else None,
            "consequence": (None if live else
                            "patent-side collision coverage for this run is UNKNOWN; "
                            "no novelty or collision verdict may rely on patent coverage"),
            "measured_evidence": ("R495_TRANSPORT_PROBE.json lens 500 'No product in "
                                  "scope'/scholarly 401; R496_PATSNAP_PROBE.json patsnap "
                                  "67200202 recognized-but-unopenable, /auth 67200101, "
                                  "/oauth/token 67200015, Space secret surface names-only []; "
                                  "R497_PATENTBEAR_PROBE{,2,3}.json patentbear LIVE at "
                                  "tools/call, garbage key 401, cross-path byte check "
                                  "title+abstract verified, quota metered free 20/month"),
            "missing_for_unblinding": (None if live else
                                       "a scoped patent transport (Lens product scope, "
                                       "PatSnap companion app_id, or an openable "
                                       "PatentBear/patent credential)"),
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


# ---- free-source substrate states (R499) --------------------------------
# The operator directive "use huggingface and other free sources" installs
# the keyless free-source substrate as instrument surface. Its states obey
# the same law as every transport state: MEASURED, TYPED, never inferred.
T_NOT_FOUND = "NOT_FOUND"                       # 404: the requested object does not exist
T_DNS_UNRESOLVED = "DNS_UNRESOLVED_THIS_ENVIRONMENT"  # cannot even reach the host HERE
T_NON_JSON = "WEB_SHELL_NOT_JSON_API"           # 200 but HTML shell, not an API answer
T_CREDENTIAL_REQUIRED = "CREDENTIAL_REQUIRED"   # measured 401/403 credential wall

CORPUS_COVERED = "CORPUS_COVERAGE_LIVE_THIS_RUN"
CORPUS_BLIND = "PATENT_CORPUS_BLIND_FOR_THIS_RUN"

# R504 -- HF_TOKEN authenticated quota (attach-when-present). Measured
# BEFORE integration (R504/R504_HF_AUTH_PROBE.json, both modes per
# endpoint): /splits, /rows and the Hub catalog answer 200 in BOTH modes
# (the authenticated mode never degrades a measured endpoint), and the
# /search 500 warming transient is server-side index state, identical in
# both modes -- the credential is not a /search lever. The header is
# attached whenever the HF_TOKEN environment variable is present (the
# canonical Space carries it as a standing secret, so the DEPLOYED legs
# run authenticated), and the per-measurement provenance records the
# credential mode actually used (LXXV clause 1: provenance = which
# source, which endpoint, which query, when -- and under which
# credential mode). A missing token degrades to the measured keyless
# mode; it is never a failure.
HF_AUTH_ENV = "HF_TOKEN"


def _hf_auth_header():
    """(headers, credential_mode) for the HF surfaces -- attach-when-present."""
    tok = os.environ.get(HF_AUTH_ENV, "")
    if tok:
        return {"Authorization": "Bearer %s" % tok}, "AUTHENTICATED_HF_TOKEN"
    return {}, "ANONYMOUS"

# R499 probe-measured constants (Art. VIII: authored from provider reality,
# probe ledger R499/R499_FREE_SOURCES_PROBE.json):
HF_CATALOG_URL = ("https://huggingface.co/api/datasets?other=patents"
                  "&limit=100&full=false")
HF_CORPUS_DATASET = "common-pile/uspto"     # the operator brief's flagship corpus
HF_CORPUS_CONFIG = "default"                # measured via datasets-server /splits
HF_CORPUS_SPLIT = "train"                   # measured via datasets-server /splits
BRIEF_CLAIM_ROWS_COMMON_PILE = 16200000     # operator-brief external claim (~16.2M)
EPO_OPS_PROBE_URL = ("https://ops.epo.org/3.2/rest-services/published-data/"
                     "search?q=ti%3D%22shunt%20valve%22")
USPTO_PORTAL_PROBE_URL = "https://data.uspto.gov/api/1/datasets?q=patent"
GITHUB_SUBSTRATE_URL = ("https://raw.githubusercontent.com/google/"
                        "patents-public-data/master/README.md")


class FreePatentSourceLayer:
    """Keyless free patent-source substrate (R499): Hugging Face Hub catalog,
    Hugging Face datasets-server row access (content-bearing), the Google
    patents-public-data GitHub substrate, and TYPED boundary measurements of
    the account-gated free sources (EPO OPS, USPTO portal, PatentsView).

    Constitutional law for this layer:
      - every state is MEASURED, never inferred from presence or reputation;
      - a keyless boundary that answers 401/403 types CREDENTIAL_REQUIRED --
        the named missing piece is the free registration, never a verdict;
      - an unreachable host types DNS_UNRESOLVED_THIS_ENVIRONMENT (Art.
        XXIII: cannot-verify-here is said, not papered over);
      - a 200 that returns an HTML shell types WEB_SHELL_NOT_JSON_API --
        a marketing page is not an API (presentational success is not
        retrieval success);
      - coverage statements derive ONLY from content-bearing LIVE
        measurements (a row fetch with real text), never from catalog
        listings alone (a listing is a count signal, Art. XXI.1).
    """

    name = "free_sources"

    def __init__(self):
        self.measured = {}

    # -- generic dataset-server row fetch (also serves F13's attack path) --
    def fetch_dataset_rows(self, dataset, config, split, length=2):
        url = ("https://datasets-server.huggingface.co/rows?dataset=%s"
               "&config=%s&split=%s&offset=0&length=%d"
               % (urllib.parse.quote(dataset), urllib.parse.quote(config),
                  urllib.parse.quote(split), int(length)))
        auth_h, self.last_credential_mode = _hf_auth_header()
        code, raw = _http_get(url, {"Accept": "application/json",
                                    "User-Agent": "toscanini-rbg/1.0",
                                    **auth_h})
        if code is None:
            return T_SEARCH_FAILED, None
        if code == 404:
            return T_NOT_FOUND, None
        if code in (401, 403):
            return T_AUTH_FAILED, None
        if code != 200:
            return T_SEARCH_FAILED, None
        try:
            obj = json.loads(raw.decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001
            return T_SEARCH_FAILED, None
        return T_LIVE, obj

    def self_measure(self):
        """Measure every registered free source live. Returns the per-source
        map; every state is typed."""
        m = self.measured = {}

        # 1. HF Hub catalog (a LISTING -- count signal, never coverage)
        cat_auth, cat_mode = _hf_auth_header()
        code, raw = _http_get(HF_CATALOG_URL, {"Accept": "application/json",
                                               "User-Agent": "toscanini-rbg/1.0",
                                               **cat_auth})
        st, obj = T_SEARCH_FAILED, None
        if code == 200:
            try:
                obj = json.loads(raw.decode("utf-8", "replace"))
                st = T_LIVE if isinstance(obj, list) else T_SEARCH_FAILED
            except Exception:  # noqa: BLE001
                st = T_SEARCH_FAILED
        elif code == 404:
            st = T_NOT_FOUND
        elif code in (401, 403):
            st = T_AUTH_FAILED
        m["hf_hub_catalog"] = {
            "state": st, "http": code,
            "credential_mode": cat_mode,
            "dataset_count_returned": len(obj) if isinstance(obj, list) else None,
            "role": "DISCOVERY_LISTING_COUNT_SIGNAL_ONLY"}

        # 2. HF datasets-server rows for the flagship corpus (CONTENT-BEARING)
        st_r, obj_r = self.fetch_dataset_rows(HF_CORPUS_DATASET, HF_CORPUS_CONFIG,
                                              HF_CORPUS_SPLIT, length=2)
        rows = (obj_r or {}).get("rows") if isinstance(obj_r, dict) else None
        long_text = False
        longest = 0
        if isinstance(rows, list) and rows:
            r0 = rows[0].get("row") or {}
            textish = [v for v in r0.values() if isinstance(v, str) and len(v) > 80]
            long_text = bool(textish)
            longest = max((len(v) for v in textish), default=0)
        m["hf_corpus_rows"] = {
            "state": st_r, "dataset": HF_CORPUS_DATASET,
            "config": HF_CORPUS_CONFIG, "split": HF_CORPUS_SPLIT,
            "credential_mode": getattr(self, "last_credential_mode",
                                       "ANONYMOUS"),
            "rows_returned": len(rows) if isinstance(rows, list) else None,
            "has_long_text_field": long_text,
            "longest_text_field_len": longest,
            "role": "CONTENT_BEARING_COVERAGE_SOURCE"}

        # 3. HF datasets-server size (served-view row count; claim check)
        st_s, obj_s = self.fetch_dataset_size()
        m["hf_corpus_size_served_view"] = {
            "state": st_s,
            "credential_mode": _hf_auth_header()[1],
            "measured_num_rows_served": obj_s,
            "brief_claim_num_rows": BRIEF_CLAIM_ROWS_COMMON_PILE,
            "claim_verification": (
                "EXTERNAL_CLAIM_UNVERIFIED_AT_SERVED_VIEW: the keyless "
                "datasets-server serves %s rows for the default config; the "
                "brief's full-dataset figure is neither confirmed nor "
                "refuted by this measurement" % obj_s
                if isinstance(obj_s, int) else "EXTERNAL_CLAIM_UNVERIFIED"),
            "role": "CLAIM_VERIFICATION_EVIDENCE"}

        # 4. Google patents-public-data GitHub substrate (tooling/docs)
        code4, raw4 = _http_get(GITHUB_SUBSTRATE_URL, {"Accept": "text/plain",
                                                       "User-Agent": "toscanini-rbg/1.0"})
        st4 = T_LIVE if (code4 == 200 and isinstance(raw4, bytes)
                         and b"patent" in raw4[:65536].lower()) else T_SEARCH_FAILED
        if code4 == 404:
            st4 = T_NOT_FOUND
        m["google_github_substrate"] = {
            "state": st4, "http": code4,
            "role": "TOOLING_DOCS_SUBSTRATE"}

        # 5. EPO OPS keyless boundary (account-gated free source)
        code5, _raw5 = _http_get(EPO_OPS_PROBE_URL, {"Accept": "application/json",
                                                     "User-Agent": "toscanini-rbg/1.0"})
        m["epo_ops_boundary"] = {
            "state": T_CREDENTIAL_REQUIRED if code5 in (401, 403) else
                     (T_SEARCH_FAILED if code5 is None else T_SEARCH_FAILED),
            "http": code5,
            "missing_piece": "free EPO OPS registration (auth key)",
            "role": "KEYLESS_BOUNDARY_MEASUREMENT"}

        # 6. USPTO Open Data Portal shape (keyless)
        code6, raw6 = _http_get(USPTO_PORTAL_PROBE_URL, {"Accept": "application/json",
                                                         "User-Agent": "toscanini-rbg/1.0"})
        if code6 == 200 and isinstance(raw6, bytes):
            head = raw6[:512].lstrip().lower()
            st6 = T_NON_JSON if head.startswith(b"<!doctype") or head.startswith(b"<html") \
                else T_LIVE
        elif code6 == 404:
            st6 = T_NOT_FOUND
        else:
            st6 = T_SEARCH_FAILED
        m["uspto_portal_shape"] = {
            "state": st6, "http": code6,
            "note": "the portal answers its SPA shell, not a JSON API, at "
                    "the probed path",
            "role": "KEYLESS_SHAPE_MEASUREMENT"}

        # 7. PatentsView reachability (MEASURED LIVE each repetition, not
        #    hard-typed from the R499 probe: the probe measured DNS
        #    unresolvable HERE (gaierror -2); if egress ever opens, the
        #    measured state must change with it, never stay pinned)
        import socket
        pv_state, pv_http, pv_missing = T_SEARCH_FAILED, None, None
        try:
            socket.gethostbyname("search.patentsview.org")
            pv_dns_ok = True
        except socket.gaierror:
            pv_dns_ok = False
        if not pv_dns_ok:
            pv_state = T_DNS_UNRESOLVED
            pv_missing = "egress route for search.patentsview.org"
        else:
            code7, _raw7 = _http_get(
                "https://search.patentsview.org/api/v1/patent/",
                {"Accept": "application/json", "User-Agent": "toscanini-rbg/1.0"})
            pv_http = code7
            if code7 in (401, 403):
                pv_state = T_CREDENTIAL_REQUIRED
                pv_missing = "free PatentsView API key (keyless registration)"
        m["patentsview_reachability"] = {
            "state": pv_state, "http": pv_http,
            "missing_piece": pv_missing,
            "probe_precedent": "R499 probe measured DNS unresolvable here",
            "role": "ENVIRONMENT_REACHABILITY_MEASUREMENT"}
        return m

    def fetch_dataset_size(self):
        url = ("https://datasets-server.huggingface.co/size?dataset="
               + urllib.parse.quote(HF_CORPUS_DATASET))
        auth_h, _mode = _hf_auth_header()
        code, raw = _http_get(url, {"Accept": "application/json",
                                    "User-Agent": "toscanini-rbg/1.0",
                                    **auth_h})
        if code != 200:
            return (T_NOT_FOUND if code == 404 else T_SEARCH_FAILED), None
        try:
            obj = json.loads(raw.decode("utf-8", "replace"))
            n = ((obj.get("size") or {}).get("dataset") or {}).get("num_rows")
            return T_LIVE, (n if isinstance(n, int) else None)
        except Exception:  # noqa: BLE001
            return T_SEARCH_FAILED, None

    def coverage_declaration(self):
        """Coverage derives ONLY from content-bearing LIVE measurements."""
        m = self.measured or self.self_measure()
        rows_m = m.get("hf_corpus_rows", {})
        live_content_sources = [k for k, v in m.items()
                                if v.get("state") == T_LIVE
                                and v.get("role") == "CONTENT_BEARING_COVERAGE_SOURCE"]
        covered = bool(rows_m.get("state") == T_LIVE
                       and rows_m.get("rows_returned")
                       and rows_m.get("has_long_text_field"))
        return {
            "coverage_statement": CORPUS_COVERED if covered else CORPUS_BLIND,
            "live_content_sources": live_content_sources,
            "per_source_states": {k: v.get("state") for k, v in m.items()},
            "measured_num_rows_served": m.get("hf_corpus_size_served_view", {}).get("measured_num_rows_served"),
            "brief_claim_verification": m.get("hf_corpus_size_served_view", {}).get("claim_verification"),
            "not_a_novelty_verdict": True,
        }

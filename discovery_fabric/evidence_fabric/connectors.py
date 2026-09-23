"""Federated HF-datasets-server connector — query-only retrieval over
REMOTE hosted data. NO bulk download, NO local warehouse, NO vector
index (the operator's explicit R449 constraint: "The job is to connect
evidence to invention, not to accumulate infrastructure").

Transport: the public datasets-server REST API
    /search?dataset=<id>&config=<c>&split=<s>&query=<q>&length=<n>
    /filter?dataset=...&where=<sql predicate>
    /rows?dataset=...&offset=<o>&length=<n>

State contract (the R394 connector-states discipline, reused verbatim
in vocabulary): SUCCESS / EMPTY_RESULT / TIMEOUT / RATE_LIMITED /
PROVIDER_ERROR / PARSE_ERROR / UNAVAILABLE / NOT_ATTEMPTED — plus
INDEX_LOADING for the datasets-server's lazy full-text index warmup.
INDEX_LOADING and every failure class map to UNKNOWN — NEVER absence
(Art. XXI.3 / XXV). Bounded retry with backoff for INDEX_LOADING only
(a warming index is a transient state, not a refusal); failure states
are recorded and surfaced, never retried into "empty".

Robustness notes measured live (2026-09-12, this round):
  - datasets-server is load-balanced; one node can answer /search while
    another reports the index still loading -> the retry is justified
    and bounded (2 retries, 8 s apart by default).
  - responses occasionally carry ONLY the features header with zero
    rows and no num_rows_total -> parsed as EMPTY_RESULT only when
    num_rows_total == 0, else RETRY/UNKNOWN (a header-only body is not
    a zero-match claim).
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

BASE = "https://datasets-server.huggingface.co"
HF_API = "https://huggingface.co/api"

DEFAULT_TIMEOUT_S = 60
DEFAULT_INDEX_RETRIES = 2
INDEX_RETRY_BACKOFF_S = 8.0

#: explicit UNKNOWN-class states (never absence — Art. XXI.3)
UNKNOWN_STATES = {"TIMEOUT", "RATE_LIMITED", "PROVIDER_ERROR",
                  "PARSE_ERROR", "UNAVAILABLE", "NOT_ATTEMPTED",
                  "INDEX_LOADING"}


def _get_json(url: str, timeout: int = DEFAULT_TIMEOUT_S
              ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """GET <url> -> (json, None) | (None, classified_error).

    The error string is a connector-state vocabulary token, optionally
    suffixed with detail — the classifier NEVER collapses into EMPTY.
    """
    try:
        req = urllib.request.Request(
            url, headers={"Accept": "application/json",
                          "User-Agent": "toscanini-evidence-fabric/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return None, "RATE_LIMITED"
        if e.code == 404:
            return None, "PROVIDER_ERROR:HTTP404"
        return None, f"PROVIDER_ERROR:HTTP{e.code}"
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if "timed out" in reason.lower() or "timeout" in reason.lower():
            return None, "TIMEOUT"
        return None, "UNAVAILABLE:" + reason[:120]
    except json.JSONDecodeError:
        return None, "PARSE_ERROR"
    except Exception as e:  # noqa: BLE001 — classified, never raised
        return None, f"UNAVAILABLE:{type(e).__name__}"


def _is_index_loading(err: Optional[str]) -> bool:
    return bool(err) and "INDEX_LOADING" in err


def _body_says_index_loading(body: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(body, dict):
        return False
    msg = str(body.get("error") or "")
    return "index is loading" in msg or \
        "still being processed" in msg


def dataset_splits(dataset_id: str
                   ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """Available configs/splits for a dataset (reachability probe)."""
    q = urllib.parse.quote(dataset_id, safe="")
    body, err = _get_json(f"{BASE}/splits?dataset={q}")
    if err:
        return None, err
    splits = body.get("splits") if isinstance(body, dict) else None
    if splits is None:
        return None, "PARSE_ERROR:splits-missing"
    return splits, None


def search_rows(dataset_id: str, config: str, split: str, query: str,
                length: int = 5, offset: int = 0,
                timeout: int = DEFAULT_TIMEOUT_S,
                index_retries: int = DEFAULT_INDEX_RETRIES,
                retry_backoff_s: float = INDEX_RETRY_BACKOFF_S
                ) -> Tuple[Optional[List[Dict[str, Any]]], Dict[str, Any]]:
    """Full-text search over REMOTE rows (federated; nothing downloaded).

    Returns (rows, meta). rows is None on UNKNOWN-class states (meta
    carries the state + reason); rows is [] ONLY on a genuine
    num_rows_total == 0 (a real absence claim for the queried index).
    meta carries num_rows_total (the matched-count — a query-string
    match count, NOT evidence of relevance; Art. XXI.1).
    """
    params = urllib.parse.urlencode({
        "dataset": dataset_id, "config": config, "split": split,
        "query": query, "length": length, "offset": offset})
    url = f"{BASE}/search?{params}"
    attempts = []
    for attempt in range(index_retries + 1):
        # R521 observability-only: per-attempt latency (no behavior
        # change — recorded, never acted upon).
        _att_t0 = time.perf_counter()
        body, err = _get_json(url, timeout=timeout)
        _att_lat = round(time.perf_counter() - _att_t0, 3)
        if err is None and not _body_says_index_loading(body):
            rows = body.get("rows") if isinstance(body, dict) else None
            if rows is None:
                # header-only body without rows and without a total:
                # not a zero-match claim — UNKNOWN, retried once
                total = body.get("num_rows_total") if isinstance(body, dict) else None
                if total == 0:
                    attempts.append({"attempt": attempt, "state": "SUCCESS",
                                     "latency_s": _att_lat})
                    return [], {"state": "EMPTY_RESULT",
                                "num_rows_total": 0,
                                "endpoint": "search",
                                "attempts": attempts}
                attempts.append({"attempt": attempt,
                                 "state": "PARSE_ERROR:rows-missing",
                                 "latency_s": _att_lat})
                continue
            total = body.get("num_rows_total")
            attempts.append({"attempt": attempt, "state": "SUCCESS",
                             "latency_s": _att_lat})
            state = "SUCCESS" if rows else "EMPTY_RESULT"
            return rows, {"state": state, "num_rows_total": total,
                          "endpoint": "search", "attempts": attempts,
                          "query": query}
        # error or index-loading body
        err_tok = err or "INDEX_LOADING"
        if _body_says_index_loading(body):
            err_tok = "INDEX_LOADING"
        attempts.append({"attempt": attempt, "state": err_tok,
                         "latency_s": _att_lat})
        if _is_index_loading(err_tok) and attempt < index_retries:
            time.sleep(retry_backoff_s)
            continue
        break
    return None, {"state": "UNKNOWN", "reason": attempts[-1]["state"],
                  "endpoint": "search", "attempts": attempts,
                  "query": query}


def filter_rows(dataset_id: str, config: str, split: str, where: str,
                length: int = 5, offset: int = 0,
                timeout: int = DEFAULT_TIMEOUT_S
                ) -> Tuple[Optional[List[Dict[str, Any]]], Dict[str, Any]]:
    """Structured (SQL-like WHERE) filter over REMOTE rows — the
    federated query path for property tables (materials/chemistry)."""
    params = urllib.parse.urlencode({
        "dataset": dataset_id, "config": config, "split": split,
        "where": where, "length": length, "offset": offset})
    body, err = _get_json(f"{BASE}/filter?{params}", timeout=timeout)
    if err:
        return None, {"state": "UNKNOWN", "reason": err,
                      "endpoint": "filter", "where": where}
    rows = body.get("rows") if isinstance(body, dict) else None
    if rows is None:
        return None, {"state": "UNKNOWN", "reason": "PARSE_ERROR:rows-missing",
                      "endpoint": "filter", "where": where}
    total = body.get("num_rows_total")
    return rows, {"state": "SUCCESS" if rows else "EMPTY_RESULT",
                  "num_rows_total": total, "endpoint": "filter",
                  "where": where}


def get_row(dataset_id: str, config: str, split: str, row_idx: int,
            timeout: int = DEFAULT_TIMEOUT_S
            ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Re-fetch ONE row at a pinned location — the custody verifier's
    primitive (Phase 7 backward trace). Returns (row, None) or
    (None, error-state)."""
    params = urllib.parse.urlencode({
        "dataset": dataset_id, "config": config, "split": split,
        "offset": row_idx, "length": 1})
    body, err = _get_json(f"{BASE}/rows?{params}", timeout=timeout)
    if err:
        return None, err
    rows = body.get("rows") if isinstance(body, dict) else None
    if not rows:
        return None, "PROVIDER_ERROR:row-absent"
    row = rows[0].get("row")
    if not isinstance(row, dict):
        return None, "PARSE_ERROR:row-malformed"
    return row, None


def dataset_info(dataset_id: str,
                 token: str = ""
                 ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """HF Hub dataset metadata: revision sha, card license, gating.
    The slash stays UNencoded (huggingface.co rejects encoded repo
    names — measured live this round)."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"{HF_API}/datasets/{dataset_id}", headers=headers or
        {"User-Agent": "toscanini-evidence-fabric/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT_S) as r:
            return json.loads(r.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        return None, f"PROVIDER_ERROR:HTTP{e.code}"
    except Exception as e:  # noqa: BLE001
        return None, f"UNAVAILABLE:{type(e).__name__}"


def raw_file(dataset_id: str, path: str = "README.md",
             timeout: int = 45) -> Tuple[Optional[str], Optional[str]]:
    """Raw file bytes from the dataset repo (license text reading).

    The slash in the dataset id must stay UNencoded (huggingface.co
    rejects url-encoded repo names with HTTP 400 — measured live this
    round); the path is encoded except its own slashes.
    """
    p = urllib.parse.quote(path, safe="/")
    url = f"https://huggingface.co/datasets/{dataset_id}/raw/main/{p}"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "toscanini-evidence-fabric/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace"), None
    except urllib.error.HTTPError as e:
        return None, f"PROVIDER_ERROR:HTTP{e.code}"
    except Exception as e:  # noqa: BLE001
        return None, f"UNAVAILABLE:{type(e).__name__}"


def repo_tree(dataset_id: str,
              timeout: int = 45) -> Tuple[Optional[List[Dict[str, Any]]],
                                          Optional[str]]:
    """The dataset repo's main-branch tree (LICENSE file discovery).
    The slash stays unencoded (same measured constraint as raw_file)."""
    body, err = _get_json(f"{HF_API}/datasets/{dataset_id}/tree/main",
                          timeout)
    if err:
        return None, err
    if not isinstance(body, list):
        return None, "PARSE_ERROR:tree-malformed"
    return body, None


def classify_unknown(state: str) -> bool:
    return state in UNKNOWN_STATES

"""
Google Patents BigQuery Adapter
================================

Google's patent corpus is available through BigQuery public datasets.
Free tier: 1 TiB/month of query processing + 10 GB storage (sandbox
without credit card).

PUBLIC DATASETS:
  - patents.publications  (90M+ publications from 17+ countries)
  - patents.publications_summary
  - patents.assignee_harmonized
  - patents.cpc  (CPC classifications)
  - patents.ipc  (IPC classifications)
  - patents.citations  (forward and backward citations)
  - patents.family  (INPADOC family)
  - patents.claims  (full claim text!)

This is our PRIMARY global discovery engine. Per CEO directive:
  - Do NOT depend on patents.google.com HTTP search (returns 503).
  - Use BigQuery SQL instead.

AUTH:
  Requires Google Cloud service account credentials.
  - Option 1: BIGQUERY_PROJECT env var + GOOGLE_APPLICATION_CREDENTIALS JSON file
  - Option 2: gcloud auth application-default login (user account)
  - Option 3: BigQuery sandbox (free, no credit card) at console.cloud.google.com

Sandbox setup:
  1. Sign in at console.cloud.google.com
  2. Create a project (free)
  3. Enable BigQuery API
  4. Create a service account + download JSON key
  5. Set GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
  6. Set BIGQUERY_PROJECT=your-project-id
"""
from __future__ import annotations
import os, sys, json, hashlib, time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


# ----------------------- CONSTANTS -----------------------
BIGQUERY_PATENTS_DATASET = "patents.publications"
BIGQUERY_CLAIMS_TABLE = "patents.publications"  # claims are in the publications table
BIGQUERY_CPC_TABLE = "patents.cpc"
BIGQUERY_CITATIONS_TABLE = "patents.citations"
BIGQUERY_FAMILY_TABLE = "patents.family"

# Maximum bytes to scan per query (to stay within free tier)
MAX_BYTES_BILLED = 100 * 1024 * 1024  # 100 MB per query


# ----------------------- DATA SCHEMAS -----------------------
@dataclass
class BigQueryPatentRecord:
    """Patent record from Google BigQuery."""
    patent_number: str
    publication_number: str
    title: str = ""
    abstract: str = ""
    assignee: str = ""
    inventor: str = ""
    publication_date: str = ""
    priority_date: str = ""
    filing_date: str = ""
    country_code: str = ""
    kind_code: str = ""
    cpc_codes: List[str] = field(default_factory=list)
    ipc_codes: List[str] = field(default_factory=list)
    family_id: str = ""
    source: str = "GOOGLE_BIGQUERY"
    retrieved_at_utc: str = ""
    content_hash: str = ""


@dataclass
class BigQueryClaimRecord:
    """Claims retrieved from BigQuery."""
    patent_number: str
    claims: List[str] = field(default_factory=list)
    claim_count: int = 0
    independent_claim_count: int = 0
    source: str = "GOOGLE_BIGQUERY"
    retrieved_at_utc: str = ""
    content_hash: str = ""


@dataclass
class BigQuerySearchAttempt:
    """One BigQuery search attempt."""
    query: str
    sql_query: str = ""
    attempted: bool = False
    api_status: bool = False
    api_error_msg: str = ""
    normalized_state: str = "SOURCE_UNAVAILABLE"
    failure_substate: str = "NONE"
    patents: List[BigQueryPatentRecord] = field(default_factory=list)
    patent_ids: List[str] = field(default_factory=list)
    total_count: int = 0
    bytes_billed: int = 0
    bytes_processed: int = 0
    retrieved_at_utc: str = ""


# ----------------------- CLIENT -----------------------
_client = None
_project_id = None


def _get_client():
    """Get the BigQuery client (lazy init)."""
    global _client, _project_id

    if _client is not None:
        return _client

    try:
        # Ensure google-cloud-bigquery is importable
        sys.path.insert(0, "/home/z/.local/lib/python3.13/site-packages")
        from google.cloud import bigquery
        from google.oauth2 import service_account
    except ImportError:
        return None

    # Try to load credentials
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    project_id = os.environ.get("BIGQUERY_PROJECT", "")

    # Also check .env.keys
    keys_file = Path("/home/z/my-project/discovery-evidence-fabric/.env.keys")
    if keys_file.exists():
        for line in keys_file.read_text().splitlines():
            if line.startswith("BIGQUERY_PROJECT="):
                project_id = project_id or line.split("=", 1)[1].strip()
            elif line.startswith("GOOGLE_APPLICATION_CREDENTIALS="):
                creds_path = creds_path or line.split("=", 1)[1].strip()

    if not project_id or not creds_path or not Path(creds_path).exists():
        return None

    try:
        credentials = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/bigquery"],
        )
        _client = bigquery.Client(project=project_id, credentials=credentials)
        _project_id = project_id
        return _client
    except Exception:
        return None


def is_bigquery_available() -> bool:
    """Check if BigQuery is available (credentials present)."""
    return _get_client() is not None


# ----------------------- QUERIES -----------------------
def _run_query(sql: str, params: List = None) -> Tuple[List[Dict], str, int, int]:
    """Run a BigQuery query. Returns (rows, error, bytes_billed, bytes_processed)."""
    client = _get_client()
    if client is None:
        return [], "AUTH_FAILURE: no BigQuery credentials. Set BIGQUERY_PROJECT + GOOGLE_APPLICATION_CREDENTIALS", 0, 0

    try:
        job_config = None
        from google.cloud import bigquery
        if params:
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter(None, None, p) if not isinstance(p, dict)
                    else bigquery.ScalarQueryParameter(
                        p.get("name"), p.get("type", "STRING"), p.get("value")
                    ) if p.get("name")
                    else bigquery.ArrayQueryParameter(
                        p.get("name"), p.get("type", "STRING"), p.get("value", [])
                    )
                    for p in params
                ]
            )

        job = client.query(
            sql,
            job_config=job_config,
            timeout=30,
        )
        result = job.result()
        rows = [dict(row) for row in result]
        bytes_billed = int(job.total_bytes_billed or 0)
        bytes_processed = int(job.total_bytes_processed or 0)
        return rows, "", bytes_billed, bytes_processed
    except Exception as e:
        return [], f"EXCEPTION: {type(e).__name__}: {str(e)[:300]}", 0, 0


def bigquery_search_concepts(query: str, limit: int = 10) -> BigQuerySearchAttempt:
    """Search patents by concept (title + abstract text match).

    Uses BigQuery's patents.publications table.
    """
    attempt = BigQuerySearchAttempt(
        query=query[:500],
        attempted=True,
        retrieved_at_utc=_now_utc(),
    )

    if not is_bigquery_available():
        attempt.failure_substate = "AUTH_FAILURE"
        attempt.api_error_msg = "No BigQuery credentials. Set BIGQUERY_PROJECT + GOOGLE_APPLICATION_CREDENTIALS"
        attempt.normalized_state = "SOURCE_UNAVAILABLE"
        return attempt

    # Build SQL — search title and abstract
    # Use parameterized query to avoid SQL injection
    sql = f"""
    SELECT
      publication_number,
      title,
      abstract,
      assignee,
      inventor,
      publication_date,
      priority_date,
      filing_date,
      country_code,
      kind_code,
      family_id
    FROM `{BIGQUERY_PATENTS_DATASET}`
    WHERE LOWER(title) LIKE @query OR LOWER(abstract) LIKE @query
    LIMIT @limit
    """

    params = [
        {"name": "query", "type": "STRING", "value": f"%{query.lower()}%"},
        {"name": "limit", "type": "INT64", "value": limit},
    ]

    rows, err, billed, processed = _run_query(sql, params)
    attempt.bytes_billed = billed
    attempt.bytes_processed = processed
    attempt.sql_query = sql[:500]

    if err:
        attempt.api_status = False
        attempt.api_error_msg = err
        attempt.failure_substate = "EXCEPTION"
        attempt.normalized_state = "SOURCE_UNAVAILABLE"
        return attempt

    attempt.api_status = True

    for row in rows:
        pub_num = row.get("publication_number", "")
        if pub_num:
            attempt.patent_ids.append(pub_num)
            attempt.patents.append(BigQueryPatentRecord(
                patent_number=pub_num,
                publication_number=pub_num,
                title=row.get("title", "") or "",
                abstract=row.get("abstract", "") or "",
                assignee=row.get("assignee", "") or "",
                inventor=row.get("inventor", "") or "",
                publication_date=str(row.get("publication_date", "") or ""),
                priority_date=str(row.get("priority_date", "") or ""),
                filing_date=str(row.get("filing_date", "") or ""),
                country_code=row.get("country_code", "") or "",
                kind_code=row.get("kind_code", "") or "",
                family_id=str(row.get("family_id", "") or ""),
                retrieved_at_utc=_now_utc(),
                content_hash=_sha256(json.dumps(row, sort_keys=True, default=str)),
            ))

    attempt.total_count = len(attempt.patents)
    if attempt.total_count > 0:
        attempt.normalized_state = "SEARCH_RETURNED_PATENTS"
        attempt.failure_substate = "NONE"
    else:
        attempt.normalized_state = "SEARCH_RETURNED_NO_RESULTS"
        attempt.failure_substate = "NO_RESULTS"

    return attempt


def bigquery_get_claims(patent_number: str) -> Optional[BigQueryClaimRecord]:
    """Retrieve claims for a specific patent from BigQuery."""
    if not is_bigquery_available():
        return None

    sql = f"""
    SELECT
      publication_number,
      claims_localized
    FROM `{BIGQUERY_PATENTS_DATASET}`
    WHERE publication_number = @patent_number
    LIMIT 1
    """

    params = [{"name": "patent_number", "type": "STRING", "value": patent_number}]

    rows, err, _, _ = _run_query(sql, params)
    if err or not rows:
        return None

    row = rows[0]
    claims_data = row.get("claims_localized", [])
    claims = []

    if isinstance(claims_data, list):
        for c in claims_data:
            if isinstance(c, dict):
                text = c.get("text", "")
                if text:
                    claims.append(text[:3000])
            elif isinstance(c, str):
                claims.append(c[:3000])

    return BigQueryClaimRecord(
        patent_number=patent_number,
        claims=claims,
        claim_count=len(claims),
        independent_claim_count=sum(1 for c in claims if "comprising" in c.lower() or "consisting" in c.lower()),
        retrieved_at_utc=_now_utc(),
        content_hash=_sha256(json.dumps(claims, sort_keys=True)),
    )


def bigquery_search_cpc(cpc_code: str, limit: int = 10) -> BigQuerySearchAttempt:
    """Search patents by CPC classification code."""
    attempt = BigQuerySearchAttempt(
        query=f"CPC:{cpc_code}",
        attempted=True,
        retrieved_at_utc=_now_utc(),
    )

    if not is_bigquery_available():
        attempt.failure_substate = "AUTH_FAILURE"
        attempt.normalized_state = "SOURCE_UNAVAILABLE"
        return attempt

    sql = f"""
    SELECT
      p.publication_number,
      p.title,
      p.abstract,
      p.publication_date,
      p.priority_date,
      p.country_code,
      p.kind_code,
      p.family_id
    FROM `{BIGQUERY_PATENTS_DATASET}` p
    JOIN UNNEST(p.cpc) AS c
    WHERE c.code LIKE @cpc_prefix
    LIMIT @limit
    """

    params = [
        {"name": "cpc_prefix", "type": "STRING", "value": f"{cpc_code}%"},
        {"name": "limit", "type": "INT64", "value": limit},
    ]

    rows, err, billed, processed = _run_query(sql, params)
    attempt.bytes_billed = billed
    attempt.bytes_processed = processed

    if err:
        attempt.api_error_msg = err
        attempt.failure_substate = "EXCEPTION"
        attempt.normalized_state = "SOURCE_UNAVAILABLE"
        return attempt

    attempt.api_status = True
    for row in rows:
        pub_num = row.get("publication_number", "")
        if pub_num:
            attempt.patent_ids.append(pub_num)
            attempt.patents.append(BigQueryPatentRecord(
                patent_number=pub_num,
                publication_number=pub_num,
                title=row.get("title", "") or "",
                abstract=row.get("abstract", "") or "",
                publication_date=str(row.get("publication_date", "") or ""),
                priority_date=str(row.get("priority_date", "") or ""),
                country_code=row.get("country_code", "") or "",
                kind_code=row.get("kind_code", "") or "",
                family_id=str(row.get("family_id", "") or ""),
                retrieved_at_utc=_now_utc(),
            ))

    attempt.total_count = len(attempt.patents)
    attempt.normalized_state = "SEARCH_RETURNED_PATENTS" if attempt.total_count > 0 else "SEARCH_RETURNED_NO_RESULTS"
    return attempt


def bigquery_get_citations(patent_number: str) -> List[Dict[str, str]]:
    """Retrieve citations for a patent (backward + forward)."""
    if not is_bigquery_available():
        return []

    sql = f"""
    SELECT
      citing_publication_number,
      cited_publication_number,
      category
    FROM `{BIGQUERY_CITATIONS_TABLE}`
    WHERE citing_publication_number = @patent_number
       OR cited_publication_number = @patent_number
    LIMIT 100
    """

    params = [{"name": "patent_number", "type": "STRING", "value": patent_number}]

    rows, err, _, _ = _run_query(sql, params)
    if err:
        return []

    return [
        {
            "citing": r.get("citing_publication_number", ""),
            "cited": r.get("cited_publication_number", ""),
            "category": r.get("category", ""),
        }
        for r in rows
    ]


def bigquery_get_family(patent_number: str) -> List[str]:
    """Retrieve INPADOC family members for a patent."""
    if not is_bigquery_available():
        return []

    sql = f"""
    SELECT
      family_id,
      publication_number
    FROM `{BIGQUERY_PATENTS_DATASET}`
    WHERE family_id = (
      SELECT family_id FROM `{BIGQUERY_PATENTS_DATASET}`
      WHERE publication_number = @patent_number LIMIT 1
    )
    LIMIT 100
    """

    params = [{"name": "patent_number", "type": "STRING", "value": patent_number}]

    rows, err, _, _ = _run_query(sql, params)
    if err:
        return []

    return [r.get("publication_number", "") for r in rows if r.get("publication_number")]

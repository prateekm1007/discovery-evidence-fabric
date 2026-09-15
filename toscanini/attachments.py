"""toscanini/attachments.py — R459: server-side attachment ingestion.

External product audit P0-3 (measured live at 181a22f): the `+ Attach`
affordance existed in the UI while the engine had no ingestion path, so
the first real file a user selected hit an error wall. This module
implements the engine side of the R458 attachment contract:

    upload -> typed extraction -> content hash (provenance from the
    first byte) -> owner-scoped storage -> binding to a run -> the
    worker merges the extracted text into the Problem Understanding
    INPUT record as typed USER_EVIDENCE.

Design invariants (constitutional):
  * Art. XXI — an attachment enters the investigation's record with
    provenance custody (sha256, size, media type, extraction status);
    it is never silently dropped and never silently trusted: extracted
    text is typed USER_EVIDENCE (the user's own claimed material),
    distinct from retrieved evidence (which keeps its own custody
    chain in the Evidence Fabric).
  * Art. X — one canonical store: attachments live under ENGINE_RUNS
    (the durable-state snapshot covers them; a restart cannot lose an
    uploaded document without the loss surfacing in the ledger).
  * Directive R458 §3 — the conversation references the attachment;
    the problem string does not become the database. Text is extracted
    SERVER-SIDE and bounded; the client never pastes file contents.

Ownership: an attachment is bound to its uploader's owner key at
creation; binding it to a run requires the same owner. Listing and
reading are owner-scoped by the server layer (the same capability
model as sessions).
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from toscanini.sessions import ENGINE_RUNS

ATTACHMENTS_DIR = ENGINE_RUNS / "attachments"

# per-attachment extracted-text bound: the Problem Understanding INPUT
# is a decision record, not a corpus — the full bytes stay on disk and
# the bounded extract is what the investigation reads (disclosed in the
# payload as text_chars_total + text_excerpt_chars).
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_TEXT_EXTRACT_CHARS = 20000
MAX_TEXT_EXTRACT_CHARS_PDF = 40000

# R471 (external audit P0-6): the URL/reference leg of the input model.
# A web reference is fetched SERVER-SIDE under the same custody chain
# as an upload (sha256, media type, typed extraction) with a hard SSRF
# guard: http/https only, every resolved address must be public, every
# redirect hop re-validated, response size and time bounded.
URL_FETCH_TIMEOUT_S = 10
URL_MAX_REDIRECTS = 3
URL_USER_AGENT = "ToscaniniDiscovery/1.0 (reference fetcher; bounded, SSRF-guarded)"

_TEXT_LIKE = re.compile(
    r"\.(txt|md|markdown|csv|tsv|json|log|xml|yaml|yml|html|htm|tex|bib)$",
    re.IGNORECASE,
)

# the typed extraction capability table — every status is honest and
# machine-readable; nothing pretends extraction happened
INGESTION_STATUSES = {
    "TEXT_EXTRACTED": "text extracted server-side and bound to the run",
    "STORED_TEXT_UNREADABLE": ("stored with content hash; no text could "
                               "be extracted (scanned image PDF or "
                               "binary) — the bytes are on record"),
    "STORED": "stored with content hash (no text extraction attempted)",
    "REJECTED_TOO_LARGE": "rejected: over the size limit",
    "REJECTED_EMPTY": "rejected: empty upload",
}


def _attachments_root() -> Path:
    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    return ATTACHMENTS_DIR


def _owner_dir(owner_key: str) -> Path:
    # R459 (isolation is a security property): the directory derives
    # from the SHA-256 of the owner capability — collision-free across
    # arbitrary keys, and the key itself is never recoverable from the
    # filesystem layout. (The first draft's hex-only sanitizer collapsed
    # distinct keys onto one directory — caught by the isolation test.)
    digest = hashlib.sha256((owner_key or "anonymous").encode()).hexdigest()[:32]
    d = _attachments_root() / digest
    d.mkdir(parents=True, exist_ok=True)
    return d


def _extract_text(filename: str, data: bytes) -> tuple[str, str]:
    """Returns (status, extracted_text). Bounded, fail-honest: an
    extraction failure is a typed status, never a fabricated text."""
    name = filename.lower()
    try:
        if _TEXT_LIKE.search(name):
            text = data.decode("utf-8", errors="replace")
            return "TEXT_EXTRACTED", text[:MAX_TEXT_EXTRACT_CHARS]
        if name.endswith(".pdf"):
            import io

            import pypdf  # the production PDF reader (pinned)
            reader = pypdf.PdfReader(io.BytesIO(data))
            pages: List[str] = []
            total = 0
            for page in reader.pages:
                try:
                    t = page.extract_text() or ""
                except Exception:  # noqa: BLE001 — one bad page stays honest
                    t = ""
                pages.append(t)
                total += len(t)
                if total > MAX_TEXT_EXTRACT_CHARS_PDF:
                    break
            text = "\n".join(pages).strip()
            if text:
                return "TEXT_EXTRACTED", text[:MAX_TEXT_EXTRACT_CHARS_PDF]
            return "STORED_TEXT_UNREADABLE", ""
    except Exception:  # noqa: BLE001 — extraction must never 500 the upload
        return "STORED_TEXT_UNREADABLE", ""
    return "STORED", ""


def _media_type(filename: str) -> str:
    """A coarse, honest media type from the extension — enough for the
    product surface to label the chip; the bytes carry the truth."""
    name = filename.lower()
    if _TEXT_LIKE.search(name):
        return "text/plain"
    for ext, mt in {
        ".pdf": "application/pdf",
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".webp": "image/webp",
        ".step": "application/step", ".stp": "application/step",
        ".stl": "model/stl", ".glb": "model/gltf-binary",
        ".zip": "application/zip", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }.items():
        if name.endswith(ext):
            return mt
    return "application/octet-stream"


def save_attachment(owner_key: str, filename: str,
                    data: bytes, role: str = "evidence") -> Dict[str, Any]:
    """Store one upload with provenance custody. Never raises for
    content reasons — rejection reasons are typed payloads."""
    attachment_id = f"att_{uuid.uuid4().hex[:16]}"
    size = len(data or b"")
    if size == 0:
        return {"attachment_id": attachment_id, "name": filename,
                "ingestion": {"status": "REJECTED_EMPTY"}, "rejected": True}
    if size > MAX_UPLOAD_BYTES:
        return {"attachment_id": attachment_id, "name": filename,
                "bytes": size,
                "ingestion": {"status": "REJECTED_TOO_LARGE",
                              "limit_bytes": MAX_UPLOAD_BYTES},
                "rejected": True}

    sha256 = hashlib.sha256(data).hexdigest()
    status, text = _extract_text(filename, data)

    odir = _owner_dir(owner_key)
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename)[:120] or "upload.bin"
    blob_path = odir / f"{attachment_id}__{safe_name}"
    blob_path.write_bytes(data)
    meta_path = odir / f"{attachment_id}.json"
    record = {
        "attachment_id": attachment_id,
        "owner_key": owner_key,
        "name": filename[:200],
        "stored_as": blob_path.name,
        "media_type": _media_type(filename),
        "bytes": size,
        "sha256": sha256,
        "role": role if role in ("evidence", "specification", "context") else "evidence",
        "ingestion": {
            "status": status,
            "text_chars_total": len(text),
            "text_excerpt_chars": min(len(text), MAX_TEXT_EXTRACT_CHARS),
            "note": INGESTION_STATUSES.get(status, status),
        },
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    meta_path.write_text(json.dumps(record, indent=1))
    # the bounded extract rides its own file so the worker reads one
    # artifact per attachment without re-parsing the blob
    if text:
        (odir / f"{attachment_id}.txt").write_text(text)
    return record


def get_attachment(attachment_id: str, owner_key: str) -> Optional[Dict[str, Any]]:
    p = _owner_dir(owner_key) / f"{attachment_id}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001 — a corrupt record stays absent, not wrong
        return None


def get_attachment_text(attachment_id: str, owner_key: str) -> str:
    p = _owner_dir(owner_key) / f"{attachment_id}.txt"
    if not p.exists():
        return ""
    try:
        return p.read_text(errors="replace")
    except Exception:  # noqa: BLE001
        return ""


def list_attachments(owner_key: str) -> List[Dict[str, Any]]:
    odir = _owner_dir(owner_key)
    out: List[Dict[str, Any]] = []
    for p in sorted(odir.glob("att_*.json")):
        try:
            rec = json.loads(p.read_text())
            rec.pop("owner_key", None)  # never echo the capability
            out.append(rec)
        except Exception:  # noqa: BLE001
            continue
    return out


def resolve_bindings(session: Dict[str, Any], owner_key: str) -> List[Dict[str, Any]]:
    """Resolve a session's bound attachments to their records (owner
    verified). Used by the worker — a binding whose record is missing
    or owner-mismatched surfaces as an honest gap, never as content.

    R471 (audit P0-6, parallel-line union): a URL fetched via
    save_url_attachment lands here as a REGULAR attachment (blob +
    bounded extract + provenance); the record-only url_reference
    branch was dropped as dead under the fetch path."""
    out: List[Dict[str, Any]] = []
    for aid in (session.get("attachment_ids") or []):
        rec = get_attachment(str(aid), owner_key)
        if rec and rec.get("ingestion", {}).get("status") == "TEXT_EXTRACTED":
            out.append({
                "attachment_id": rec["attachment_id"],
                "name": rec["name"],
                "sha256": rec["sha256"],
                "bytes": rec["bytes"],
                "text": get_attachment_text(str(aid), owner_key),
            })
        elif rec:
            out.append({
                "attachment_id": rec["attachment_id"],
                "name": rec["name"],
                "sha256": rec["sha256"],
                "bytes": rec["bytes"],
                "text": "",
                "note": rec["ingestion"].get("note"),
            })
    return out


# ---------------------------------------------------------------------------
# R471 (external audit P0-6): URL/reference ingestion. The product brief
# promises a problem + URL + attachments input model; the URL leg was
# absent (measured: "no URL field or URL payload in the audited
# composer"). This is the engine side: a web reference is fetched
# SERVER-SIDE, SSRF-guarded, and lands in the SAME custody chain as an
# upload — one canonical attachment record, one typed ingestion verdict,
# the bounded extract merged as USER_EVIDENCE by the existing worker
# path. Failure states are typed and distinct: blocked URL (scheme or
# non-public host), fetch failure, empty content — never a fabricated
# success.
# ---------------------------------------------------------------------------

def _html_to_text(html: str) -> str:
    """Bounded HTML→text: script/style dropped, tags dropped, entities
    unescaped, whitespace collapsed. Deliberately crude — the extract is
    a decision-record input, not a scraper."""
    import html as _html
    txt = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    txt = re.sub(r"(?s)<[^>]+>", " ", txt)
    txt = _html.unescape(txt)
    return re.sub(r"\s+", " ", txt).strip()


def _ssrf_guard(url: str) -> tuple[Optional[str], Optional[Dict[str, str]]]:
    """Validate scheme + host BEFORE any request. Returns
    (normalized_url, None) or (None, {"status", "reason"}). Every
    address the hostname resolves to must be PUBLIC — loopback, private,
    link-local (cloud metadata), and reserved ranges are refused, so a
    URL can never turn the engine into a proxy into its own network."""
    from urllib.parse import urlparse
    import ipaddress
    import socket
    # R471 CTO correction (this line's never-raise battery): the caller
    # may hand anything through the module boundary; coerce before use
    raw = str(url or "").strip()
    if not raw:
        return None, {"status": "REJECTED_BLOCKED_URL",
                      "reason": "no URL was provided"}
    try:
        parsed = urlparse(raw)
    except Exception:  # noqa: BLE001 — a hostile URL is a typed refusal
        return None, {"status": "REJECTED_BLOCKED_URL",
                      "reason": "the URL could not be parsed"}
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        return None, {"status": "REJECTED_BLOCKED_URL",
                      "reason": f"scheme {scheme or 'missing'!r} is not "
                                "allowed — only http/https references "
                                "can be fetched"}
    host = parsed.hostname or ""
    if not host:
        return None, {"status": "REJECTED_BLOCKED_URL",
                      "reason": "the URL has no hostname"}
    default_port = 443 if scheme == "https" else 80
    try:
        infos = socket.getaddrinfo(host, parsed.port or default_port,
                                   proto=socket.IPPROTO_TCP)
    except Exception as exc:  # noqa: BLE001 — resolution failure is typed
        return None, {"status": "REJECTED_FETCH_FAILED",
                      "reason": f"the host could not be resolved ({exc})"}
    if not infos:
        return None, {"status": "REJECTED_FETCH_FAILED",
                      "reason": "the host resolved to no address"}
    for info in infos:
        ip_raw = info[4][0]
        try:
            addr = ipaddress.ip_address(str(ip_raw).split("%")[0])
        except ValueError:
            return None, {"status": "REJECTED_BLOCKED_URL",
                          "reason": f"unparseable resolved address "
                                    f"({ip_raw}) — blocked"}
        if not addr.is_global:
            return None, {"status": "REJECTED_BLOCKED_URL",
                          "reason": f"the host resolves to a "
                                    f"non-public address ({addr}) — "
                                    "blocked for safety"}
    return raw, None


def _build_opener():
    """urllib opener whose redirect handler validates every hop."""
    import urllib.error
    import urllib.request

    class _GuardedRedirect(urllib.request.HTTPRedirectHandler):
        max_repeats = URL_MAX_REDIRECTS
        max_redirections = URL_MAX_REDIRECTS

        def redirect_request(self, req, fp, code, msg, hdrs, newurl):
            guarded, err = _ssrf_guard(str(newurl))
            if err is not None:
                raise urllib.error.URLError(
                    f"redirect blocked: {err['reason']}")
            return super().redirect_request(
                req, fp, code, msg, hdrs, guarded)

    opener = urllib.request.build_opener(_GuardedRedirect)
    opener.addheaders = [("User-Agent", URL_USER_AGENT),
                         ("Accept", "text/html,text/*;q=0.9,*/*;q=0.5")]
    return opener


def _default_fetcher(url: str):
    """The production fetch: opener with guarded redirects, bounded
    time. Returns (body_bytes, content_type, final_url)."""
    import urllib.error
    import urllib.request
    req = urllib.request.Request(url, method="GET")
    try:
        with _build_opener().open(req, timeout=URL_FETCH_TIMEOUT_S) as resp:
            body = resp.read(MAX_UPLOAD_BYTES + 1)
            ctype = str(resp.headers.get("Content-Type") or "")
            final = resp.geturl()
    except urllib.error.HTTPError as exc:
        raise OSError(f"the server answered HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise OSError(f"the request failed ({exc.reason})") from exc
    return body, ctype, final


def _extract_from_content(ctype: str, data: bytes,
                          name: str) -> tuple[str, str]:
    """Typed extraction from fetched bytes — the same honest vocabulary
    as the upload path (TEXT_EXTRACTED / STORED / STORED_TEXT_UNREADABLE)."""
    base = ctype.split(";")[0].strip().lower()
    try:
        if base == "application/pdf" or name.lower().endswith(".pdf"):
            import io

            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(data))
            pages: List[str] = []
            total = 0
            for page in reader.pages:
                try:
                    t = page.extract_text() or ""
                except Exception:  # noqa: BLE001 — one bad page stays honest
                    t = ""
                pages.append(t)
                total += len(t)
                if total > MAX_TEXT_EXTRACT_CHARS_PDF:
                    break
            text = "\n".join(pages).strip()
            if text:
                return "TEXT_EXTRACTED", text[:MAX_TEXT_EXTRACT_CHARS_PDF]
            return "STORED_TEXT_UNREADABLE", ""
        if base.startswith("text/") or base in (
                "application/json", "application/xml",
                "application/xhtml+xml", "application/javascript"):
            decoded = data.decode("utf-8", errors="replace")
            if base in ("text/html", "application/xhtml+xml") \
                    or name.lower().endswith((".html", ".htm")):
                decoded = _html_to_text(decoded)
            text = decoded[:MAX_TEXT_EXTRACT_CHARS]
            if text.strip():
                return "TEXT_EXTRACTED", text
            return "STORED_TEXT_UNREADABLE", ""
    except Exception:  # noqa: BLE001 — extraction must never fabricate
        return "STORED_TEXT_UNREADABLE", ""
    return "STORED", ""


def save_url_attachment(owner_key: str, url: str,
                        role: str = "evidence",
                        _fetcher=None) -> Dict[str, Any]:
    """Fetch one web reference with provenance custody. Never raises
    for content reasons — every outcome is a typed record. The
    ``_fetcher`` seam exists for tests (the SSRF guard refuses
    loopback hosts, so a live success path cannot be exercised
    in-process)."""
    attachment_id = f"att_{uuid.uuid4().hex[:16]}"
    guarded, err = _ssrf_guard(url)
    if err is not None:
        return {"attachment_id": attachment_id, "name": str(url or "")[:200],
                "source_url": str(url or "")[:2000],
                "ingestion": {"status": err["status"],
                              "note": err["reason"]},
                "rejected": True}
    fetch = _fetcher or _default_fetcher
    try:
        data, ctype, final_url = fetch(guarded)
    except Exception as exc:  # noqa: BLE001 — typed failure, never a 500
        return {"attachment_id": attachment_id, "name": guarded[:200],
                "source_url": guarded[:2000],
                "ingestion": {"status": "REJECTED_FETCH_FAILED",
                              "note": str(exc)[:300]},
                "rejected": True}
    size = len(data or b"")
    if size == 0:
        return {"attachment_id": attachment_id, "name": guarded[:200],
                "source_url": guarded[:2000],
                "ingestion": {"status": "REJECTED_EMPTY_CONTENT",
                              "note": "the URL served no content"},
                "rejected": True}
    if size > MAX_UPLOAD_BYTES:
        return {"attachment_id": attachment_id, "name": guarded[:200],
                "source_url": guarded[:2000],
                "ingestion": {"status": "REJECTED_TOO_LARGE",
                              "note": f"the response exceeded "
                                      f"{MAX_UPLOAD_BYTES} bytes",
                              "limit_bytes": MAX_UPLOAD_BYTES},
                "rejected": True}
    from urllib.parse import urlparse
    host = urlparse(guarded).hostname or "reference"
    path = (urlparse(guarded).path or "").strip("/")
    name = (host + ("/" + path if path else ""))[:120] or host
    sha256 = hashlib.sha256(data).hexdigest()
    status, text = _extract_from_content(ctype, data, name)

    odir = _owner_dir(owner_key)
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", name)[:120] or "reference"
    blob_path = odir / f"{attachment_id}__{safe_name}"
    blob_path.write_bytes(data)
    meta_path = odir / f"{attachment_id}.json"
    record = {
        "attachment_id": attachment_id,
        "owner_key": owner_key,
        "name": name,
        "source_url": guarded[:2000],
        "final_url": (final_url or guarded)[:2000],
        "stored_as": blob_path.name,
        "media_type": (ctype.split(";")[0].strip().lower()
                       or "application/octet-stream"),
        "bytes": size,
        "sha256": sha256,
        "role": role if role in ("evidence", "specification", "context") else "evidence",
        "ingestion": {
            "status": status,
            "text_chars_total": len(text),
            "text_excerpt_chars": min(len(text), MAX_TEXT_EXTRACT_CHARS),
            "note": INGESTION_STATUSES.get(status, status),
        },
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    meta_path.write_text(json.dumps(record, indent=1))
    if text:
        (odir / f"{attachment_id}.txt").write_text(text)
    return record

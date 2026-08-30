"""Chemistry & biology connectors: PubChem, UniProt, ChEMBL, RCSB PDB."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List

from discovery_fabric.source_registry.base import (
    ConnectorBase, SourceRecord, SourceQueryResult, SSL_CONTEXT, USER_AGENT,
    STATUS_OK, STATUS_SEARCH_FAILED, utc_now, sha256_bytes,
)


class PubChemConnector(ConnectorBase):
    SOURCE_ID = "pubchem"
    ROLES = ("CHEMISTRY",)
    HEALTH_QUERY = "aspirin"
    LIMIT = 5

    def definitive_empty(self, http_status, body) -> bool:
        """PubChem PUG REST signals 'name not found' as HTTP 404 with a
        Fault body {'Fault': {'Code': 'PUGREST.NotFound', ...}} — the
        provider DEFINITIVELY answering 'no compound by that name'."""
        if http_status != 404 or not body:
            return False
        try:
            fault = json.loads(body.decode("utf-8")).get("Fault") or {}
            return fault.get("Code") == "PUGREST.NotFound"
        except Exception:  # noqa: BLE001
            return False

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(query)
        return (f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{q}"
                "/property/MolecularFormula,MolecularWeight,CanonicalSMILES,Title/JSON")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        return json.loads(raw.decode("utf-8"))

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        props = (payload or {}).get("PropertyTable", {}).get("Properties")
        if not isinstance(props, list):
            raise ValueError("pubchem payload missing PropertyTable.Properties")
        out = []
        for p in props:
            cid = p.get("CID")
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="CHEMISTRY",
                record_id=f"cid:{cid}",
                title=p.get("Title") or f"PubChem CID {cid}",
                uri=f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "cid": cid,
                    "title": p.get("Title"),
                    "molecular_formula": p.get("MolecularFormula"),
                    "molecular_weight": p.get("MolecularWeight"),
                    "canonical_smiles": p.get("CanonicalSMILES"),
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "pubchem.ncbi.nlm.nih.gov/rest/pug",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=["Name lookup resolves the first matching compound only"],
            ))
        return out


class UniProtConnector(ConnectorBase):
    SOURCE_ID = "uniprot"
    ROLES = ("BIOLOGY",)
    HEALTH_QUERY = "insulin"
    LIMIT = 5

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(query)
        return (f"https://rest.uniprot.org/uniprotkb/search?query={q}"
                f"&size={self.LIMIT}&fields=accession,protein_name,organism_name,reviewed")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        return json.loads(raw.decode("utf-8"))

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        results = (payload or {}).get("results")
        if not isinstance(results, list):
            raise ValueError("uniprot payload missing results list")
        out = []
        for r in results:
            acc = r.get("primaryAccession") or ""
            names = r.get("proteinDescription") or {}
            name = ((names.get("recommendedName") or {}).get("fullName") or {}).get("value")
            if not name:
                alt = names.get("submissionNames") or []
                name = ((alt[0] or {}).get("fullName") or {}).get("value") if alt else None
            organism = ((r.get("organism") or {}).get("scientificName")) or None
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="BIOLOGY",
                record_id=f"uniprot:{acc}",
                title=name or f"UniProt {acc}",
                uri=f"https://www.uniprot.org/uniprotkb/{acc}",
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "accession": acc,
                    "protein_name": name,
                    "organism": organism,
                    "reviewed": r.get("entryType", "").startswith("UniProtKB reviewed"),
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "rest.uniprot.org",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=[
                    "Reviewed (Swiss-Prot) vs unreviewed (TrEMBL) confidence differs",
                ],
            ))
        return out


class ChEMBLConnector(ConnectorBase):
    SOURCE_ID = "chembl"
    ROLES = ("BIOLOGY",)
    HEALTH_QUERY = "aspirin"
    LIMIT = 5

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(query)
        return (f"https://www.ebi.ac.uk/chembl/api/data/molecule.json?molecule_structures__"
                f"canonical_smiles__isnull=false&pref_name__iexact={q}&limit={self.LIMIT}")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        return json.loads(raw.decode("utf-8"))

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        molecules = (payload or {}).get("molecules")
        if not isinstance(molecules, list):
            raise ValueError("chembl payload missing molecules list")
        out = []
        for m in molecules:
            mid = m.get("molecule_chembl_id") or ""
            props = m.get("molecule_properties") or {}
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="BIOLOGY",
                record_id=f"chembl:{mid}",
                title=m.get("pref_name") or mid,
                uri=f"https://www.ebi.ac.uk/chembl/compound_report_card/{mid}/",
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "molecule_chembl_id": mid,
                    "pref_name": m.get("pref_name"),
                    "max_phase": m.get("max_phase"),
                    "molecular_weight": props.get("full_mwt"),
                    "alogp": props.get("alogp"),
                    "molecular_species": props.get("molecular_species"),
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "www.ebi.ac.uk/chembl/api/data",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=["Small-molecule focus; no device linkage"],
            ))
        return out


class RcsbPdbConnector(ConnectorBase):
    SOURCE_ID = "rcsb_pdb"
    ROLES = ("BIOLOGY",)
    HEALTH_QUERY = "insulin"
    LIMIT = 5

    def build_url(self, query: str) -> str:
        # RCSB search API is POST-only (search.rcsb.org); build_url returns
        # the endpoint and search() overrides to POST the query body.
        return "https://search.rcsb.org/rcsbsearch/v2/query"

    def search(self, query: str, timeout: int = 25) -> SourceQueryResult:
        url = self.build_url(query)
        body = json.dumps({
            "query": {
                "type": "terminal",
                "service": "full_text",
                "parameters": {"value": query},
            },
            "return_type": "entry",
            "request_options": {"paginate": {"start": 0, "rows": self.LIMIT}},
        }).encode("utf-8")
        t0 = time.time()
        try:
            req = urllib.request.Request(
                url, data=body,
                headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
            )
            resp = urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT)
            raw = resp.read()
        except urllib.error.HTTPError as e:
            try:
                detail = e.read()[:200].decode("utf-8", "replace")
            except Exception:
                detail = ""
            status = "UNAVAILABLE" if e.code >= 500 else STATUS_SEARCH_FAILED
            return self._finish(
                SourceQueryResult(
                    source_id=self.SOURCE_ID, status=status, ok=False,
                    http_status=e.code,
                    latency_ms=int((time.time() - t0) * 1000),
                    error=f"HTTP {e.code}: {detail}", query=query,
                    retrieved_at=utc_now(),
                ),
                query, url, None,
            )
        except Exception as e:  # noqa: BLE001
            return self._finish(
                SourceQueryResult(
                    source_id=self.SOURCE_ID, status=STATUS_SEARCH_FAILED, ok=False,
                    latency_ms=int((time.time() - t0) * 1000),
                    error=f"{type(e).__name__}: {e}", query=query,
                    retrieved_at=utc_now(),
                ),
                query, url, None,
            )
        raw_sha = sha256_bytes(raw)
        try:
            payload = json.loads(raw.decode("utf-8"))
            records = self.normalize_payload(payload, query, raw_sha)
            status = STATUS_OK if records else "EMPTY"
            return self._finish(
                SourceQueryResult(
                    source_id=self.SOURCE_ID, status=status, ok=True,
                    http_status=200,
                    latency_ms=int((time.time() - t0) * 1000),
                    records=records, query=query, retrieved_at=utc_now(),
                ),
                query, url, raw_sha,
            )
        except Exception as e:  # noqa: BLE001
            return self._finish(
                SourceQueryResult(
                    source_id=self.SOURCE_ID, status="PARSE_FAILED", ok=False,
                    http_status=200,
                    latency_ms=int((time.time() - t0) * 1000),
                    error=f"parse: {type(e).__name__}: {e}", query=query,
                    retrieved_at=utc_now(),
                ),
                query, url, raw_sha,
            )

    def parse_payload(self, raw: bytes, query: str) -> Any:
        return json.loads(raw.decode("utf-8"))

    def fetch_entry_summaries(self, ids):
        """data.rcsb.org pass: structure titles for the id list.

        DEFECT FIXED 2026-08-30 (found live by the QUERY_RELEVANCE
        battery): records previously shipped as stubs titled 'PDB entry
        1BOM (score 1.0)' — identifiers with scores, no structure names;
        unusable as evidence downstream and unadjudicable for relevance
        (0/10 on 'insulin' although the entries ARE insulin structures).
        The search API returns ids+scores only; titles require one
        data.rcsb.org call per entry (free; LIMIT=5 keeps this at 5
        requests). Failure degrades to the stub AND is disclosed on the
        record — never swallowed.
        """
        out = {}
        for ident in ids:
            try:
                url = f"https://data.rcsb.org/rest/v1/core/entry/{ident}"
                req = urllib.request.Request(
                    url, headers={"User-Agent": USER_AGENT,
                                  "Accept": "application/json"})
                resp = urllib.request.urlopen(req, timeout=15,
                                              context=SSL_CONTEXT)
                data = json.loads(resp.read().decode("utf-8"))
                out[ident] = {
                    "title": ((data.get("struct") or {}).get("title")),
                    "deposition_date": (data.get("rcsb_accession_info") or {}).get(
                        "deposit_date"),
                    "experimental_method": ((data.get("exptl") or [{}])[0] or {}).get(
                        "method"),
                }
            except Exception:  # noqa: BLE001 — per-entry degradation, disclosed
                continue
        return out

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        result_set = (payload or {}).get("result_set")
        if not isinstance(result_set, list):
            raise ValueError("rcsb payload missing result_set list")
        idents = [r.get("identifier") or "" for r in result_set]
        summaries = self.fetch_entry_summaries(idents)
        out = []
        for r in result_set:
            ident = r.get("identifier") or ""
            score = r.get("score")
            s = summaries.get(ident) or {}
            title = (s.get("title") or "").strip()
            if not title:
                title = f"PDB entry {ident} (score {score})"
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="BIOLOGY",
                record_id=f"pdb:{ident}",
                title=title,
                uri=f"https://www.rcsb.org/structure/{ident}",
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "pdb_id": ident,
                    "search_score": score,
                    "structure_title": s.get("title"),
                    "deposition_date": s.get("deposition_date"),
                    "experimental_method": s.get("experimental_method"),
                    "summary_fetched": bool(s),
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "search.rcsb.org/rcsbsearch/v2",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=[
                    "Only structures that have been solved experimentally",
                ],
            ))
        return out

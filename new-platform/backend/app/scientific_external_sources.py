"""Bounded read-only bibliography and FDA application-record lookups.

Explicit IDs only. Sources are research leads, not verified efficacy,
regulatory endorsement, or FDA approval likelihood. No candidate-score writes,
no free-form URL fetching, and no background crawler.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

NCT_PATTERN = re.compile(r"NCT[0-9]{8}\Z")
PMID_PATTERN = re.compile(r"[1-9][0-9]{0,11}\Z")
APPLICATION_PATTERN = re.compile(r"(?:NDA|BLA)[0-9]{6}\Z")
MAX_RESPONSE_BYTES = 2_000_000
PUBMED_LIMIT = 5
TIMEOUT_SECONDS = 12

_NCBI_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
_FDA_URL = "https://api.fda.gov/drug/drugsfda.json"


class SourceLookupError(RuntimeError):
    """A source failed; do not convert a failed lookup into negative evidence."""


def _read_json(url: str) -> Mapping[str, Any]:
    """Fetch JSON from the only two hard-coded API origins."""
    if not (url.startswith(_NCBI_URL) or url.startswith(_FDA_URL + "?")):
        raise ValueError("Unapproved scientific-source URL")
    request = Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "PDUFA-Scientific-Research/1.0 (source-reference lookup)",
    })
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        if exc.code == 404 and url.startswith(_FDA_URL + "?"):
            return {"results": []}
        raise SourceLookupError("Scientific source HTTP error " + str(exc.code)) from None
    except (URLError, OSError, TimeoutError):
        raise SourceLookupError("Scientific source unavailable") from None
    if len(body) > MAX_RESPONSE_BYTES:
        raise SourceLookupError("Scientific source response exceeds size limit")
    try:
        obj = json.loads(body)
    except (UnicodeDecodeError, ValueError):
        raise SourceLookupError("Scientific source returned invalid JSON") from None
    if not isinstance(obj, dict):
        raise SourceLookupError("Scientific source returned invalid response shape")
    return obj


def lookup_pubmed_nct(nct_id: str) -> dict[str, Any]:
    """Find up to five indexed citations mentioning an exact NCT ID.

    ESearch returns identifiers, ESummary returns bibliographic metadata.
    It does not establish that publications report this trial's results.
    """
    if not isinstance(nct_id, str) or not NCT_PATTERN.fullmatch(nct_id):
        raise ValueError("Exact NCT identifier required")
    search_params = urlencode({
        "db": "pubmed", "term": f'"{nct_id}"[All Fields]',
        "retmode": "json", "retmax": str(PUBMED_LIMIT),
    })
    search = _read_json(_NCBI_URL + "esearch.fcgi?" + search_params)
    esearch = search.get("esearchresult")
    if not isinstance(esearch, dict) or not isinstance(esearch.get("idlist"), list):
        raise SourceLookupError("PubMed search returned invalid identifiers")
    pmids = list(dict.fromkeys(esearch["idlist"]))
    if len(pmids) > PUBMED_LIMIT or not all(
        isinstance(pmid, str) and PMID_PATTERN.fullmatch(pmid) for pmid in pmids
    ):
        raise SourceLookupError("PubMed search returned invalid identifier values")
    references = []
    if pmids:
        summary_params = urlencode({
            "db": "pubmed", "id": ",".join(pmids), "retmode": "json",
        })
        summary = _read_json(_NCBI_URL + "esummary.fcgi?" + summary_params)
        result = summary.get("result")
        if not isinstance(result, dict) or not isinstance(result.get("uids"), list):
            raise SourceLookupError("PubMed summary returned invalid response")
        supplied_ids = result["uids"]
        if len(supplied_ids) > PUBMED_LIMIT or any(
            not isinstance(uid, str) or uid not in pmids for uid in supplied_ids
        ):
            raise SourceLookupError("PubMed summary identity mismatch")
        if len(set(supplied_ids)) != len(supplied_ids):
            raise SourceLookupError("PubMed summary repeated an identifier")
        for pmid in pmids:
            if pmid not in supplied_ids:
                continue
            record = result.get(pmid)
            if not isinstance(record, dict) or str(record.get("uid")) != pmid:
                raise SourceLookupError("PubMed article identity mismatch")
            title = record.get("title")
            if not isinstance(title, str) or not title.strip():
                raise SourceLookupError("PubMed citation missing title")
            references.append({
                "kind": "pubmed_citation",
                "pmid": pmid,
                "title": title[:1500],
                "journal": str(record.get("fulljournalname") or "")[:300],
                "publication_date": str(record.get("pubdate") or "")[:100],
                "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "nct_search_id": nct_id,
                "verification_status": "bibliographic_match_only",
                "scientifically_verified": False,
                "trial_result_confirmed": False,
            })
    return {
        "source": "pubmed",
        "requested_nct_id": nct_id,
        "status": "indexed_references_found" if references else "no_indexed_references_found",
        "references": references,
        "truncated": len(references) >= PUBMED_LIMIT,
        "note": "Indexed NCT mention is a research lead, not proof of trial association or scientific findings.",
    }


def lookup_fda_application(application_number: str) -> dict[str, Any]:
    """Retrieve an exact NDA/BLA application record (not a trial-to-FDA match)."""
    if not isinstance(application_number, str) or not APPLICATION_PATTERN.fullmatch(application_number):
        raise ValueError("Exact NDA/BLA application number required")
    params = urlencode({
        "search": f'application_number:"{application_number}"',
        "limit": "1",
    })
    url = _FDA_URL + "?" + params
    result = _read_json(url)
    records = result.get("results")
    if not isinstance(records, list) or len(records) > 1:
        raise SourceLookupError("FDA application search returned invalid response")
    references = []
    for record in records:
        if not isinstance(record, dict) or record.get("application_number") != application_number:
            raise SourceLookupError("FDA application number mismatch")
        products = record.get("products") or []
        if not isinstance(products, list):
            raise SourceLookupError("FDA products response is invalid")
        names = []
        for product in products[:20]:
            if isinstance(product, dict):
                name = product.get("brand_name") or product.get("generic_name")
                if isinstance(name, str) and name.strip():
                    names.append(name[:200])
        references.append({
            "kind": "drugs_at_fda_application",
            "application_number": application_number,
            "sponsor_name": str(record.get("sponsor_name") or "")[:300],
            "product_names": list(dict.fromkeys(names)),
            "source_url": url,
            "verification_status": "application_record_only",
            "scientifically_verified": False,
            "trial_association_verified": False,
        })
    return {
        "source": "openfda_drugsfda",
        "requested_application_number": application_number,
        "status": "application_found" if references else "application_not_found",
        "references": references,
        "note": "Application record is not independently linked to this NCT trial or evidence of future approval.",
    }


def attach_research_references(
    dossier: Mapping[str, Any],
    pubmed: Mapping[str, Any] | None = None,
    fda: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach source-only leads without changing scientific conclusions."""
    if not isinstance(dossier, Mapping):
        raise ValueError("Dossier must be a mapping")
    output = deepcopy(dict(dossier))
    nct_id = output.get("nct_id")
    domains = output.get("domains")
    if not isinstance(domains, dict):
        raise ValueError("Dossier domains are missing")
    if pubmed is not None:
        if not isinstance(pubmed, Mapping) or pubmed.get("requested_nct_id") != nct_id:
            raise ValueError("PubMed source NCT identity mismatch")
        references = pubmed.get("references")
        if not isinstance(references, list) or len(references) > PUBMED_LIMIT:
            raise ValueError("PubMed references are invalid")
        domains["clinical_results"]["research_leads"] = deepcopy(references)
    if fda is not None:
        if not isinstance(fda, Mapping) or not isinstance(fda.get("references"), list):
            raise ValueError("FDA references are invalid")
        domains["regulatory_analysis"]["research_leads"] = deepcopy(fda["references"])
    # No literature index or FDA record may automatically become a scored finding.
    for item in domains.values():
        if item.get("score") is not None:
            raise ValueError("External source lookup cannot alter scientific scores")
    if output.get("overall_score") is not None or output.get("fda_approval_probability") is not None:
        raise ValueError("External source lookup cannot assert approval probability")
    output["external_research_status"] = "references_only"
    return output

#!/usr/bin/env python3
"""Unreviewed exact-NCT PubMed discovery for the entire POOL, all phases/statuses.

No scores, trial findings, FDA prediction, accepted review or roster mutation.
The separate whole-POOL ClinicalTrials.gov collector remains authoritative for
registry capture. This companion job only harvests potential publication leads.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

NCT = re.compile(r"NCT[0-9]{8}")
VERSION = "pool-pubmed-unreviewed-leads-v1"
ESearch = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
MAX_BYTES = 500000
RETMAX = 25


def extract_pool(snapshot):
    pipeline = snapshot.get("pipeline") if isinstance(snapshot, dict) else None
    if not isinstance(pipeline, list) or not 0 < len(pipeline) <= 25000:
        raise ValueError("Invalid/empty POOL pipeline")
    ncts, observed, nontrials = [], set(), 0
    for row in pipeline:
        identity = row.get("id") if isinstance(row, dict) else None
        if not isinstance(identity, str):
            raise ValueError("Invalid POOL program identity")
        if not identity.startswith("TRIAL|"):
            nontrials += 1  # RESULT aliases and FDA application events are not trials.
            continue
        nct = identity[6:]
        if not NCT.fullmatch(nct) or nct in observed:
            raise ValueError("Duplicate/malformed exact-NCT POOL trial")
        observed.add(nct)
        ncts.append(nct)
    if not ncts:
        raise ValueError("No exact-NCT trial rows in POOL")
    return ncts, nontrials


def search_pubmed(nct, opener=urlopen):
    if not isinstance(nct, str) or not NCT.fullmatch(nct):
        raise ValueError("Exact NCT is required")
    url = ESearch + "?" + urlencode({
        "db": "pubmed", "term": '"' + nct + '"[All Fields]',
        "retmode": "json", "retmax": RETMAX, "sort": "pub date",
        "tool": "pdufa-pool-source-research",
    })
    with opener(Request(url, headers={"User-Agent": "PDUFAPoolSourceResearch/1.0",
                                      "Accept": "application/json"}), timeout=20) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("NCBI response too large")
    body = json.loads(raw).get("esearchresult")
    if not isinstance(body, dict):
        raise ValueError("Invalid NCBI response")
    ids, count = body.get("idlist"), body.get("count")
    valid_int = lambda p: isinstance(p, str) and p.isascii() and p.isdecimal() and 1 <= len(p) <= 16
    if (not isinstance(ids, list) or len(ids) > RETMAX or
            not isinstance(count, str) or not count.isascii() or
            not count.isdecimal() or len(count) > 9 or
            any(not valid_int(p) for p in ids) or
            len(set(ids)) != len(ids) or int(count) < len(ids)):
        raise ValueError("Malformed or inconsistent PubMed IDs")
    return {
        "nct": nct,
        "status": "QUERY_SUCCEEDED_UNREVIEWED",
        "searchUrl": url,
        "queriedAtUtc": datetime.now(timezone.utc).isoformat(),
        "reportedTotalHits": int(count),
        "truncated": int(count) > len(ids),
        "publicationLeads": [
            {"pmid": p, "url": "https://pubmed.ncbi.nlm.nih.gov/" + p + "/",
             "status": "UNREVIEWED_LEAD", "clinicalFinding": None,
             "exactTrialLinkVerified": False}
            for p in ids
        ],
    }


def validate_checkpoint(checkpoint, digest, ncts):
    if (not isinstance(checkpoint, dict) or
            checkpoint.get("schemaVersion") != VERSION or
            checkpoint.get("rosterSha256") != digest or
            checkpoint.get("nctOrder") != ncts or
            not isinstance(checkpoint.get("rows"), list) or
            len(checkpoint["rows"]) != len(ncts)):
        raise ValueError("Checkpoint does not match exact POOL snapshot")
    for nct, row in zip(ncts, checkpoint["rows"]):
        if not isinstance(row, dict) or row.get("nct") != nct or row.get("status") not in {
                "NOT_QUERIED", "RETRY_REQUIRED", "QUERY_SUCCEEDED_UNREVIEWED"}:
            raise ValueError("Checkpoint trial/status mismatch")
        leads = row.get("publicationLeads")
        if not isinstance(leads, list) or len(leads) > RETMAX:
            raise ValueError("Malformed checkpoint leads")
        if row["status"] == "QUERY_SUCCEEDED_UNREVIEWED":
            if not isinstance(row.get("reportedTotalHits"), int) or row["reportedTotalHits"] < len(leads):
                raise ValueError("Invalid saved search count")
            ids = set()
            for lead in leads:
                if (not isinstance(lead, dict) or
                        lead.get("status") != "UNREVIEWED_LEAD" or
                        lead.get("clinicalFinding") is not None or
                        lead.get("exactTrialLinkVerified") is not False or
                        not isinstance(lead.get("pmid"), str) or
                        not lead["pmid"].isascii() or not lead["pmid"].isdecimal() or
                        lead["pmid"] in ids or
                        lead.get("url") != "https://pubmed.ncbi.nlm.nih.gov/" + lead["pmid"] + "/"):
                    raise ValueError("Untrusted accepted evidence in saved leads")
                ids.add(lead["pmid"])


def report(snapshot, digest, ncts, nontrials, rows):
    success = sum(row["status"] == "QUERY_SUCCEEDED_UNREVIEWED" for row in rows)
    failed = sum(row["status"] == "RETRY_REQUIRED" for row in rows)
    return {
        "schemaVersion": VERSION,
        "scope": "ALL_EXACT_POOL_TRIAL_NCTS_ALL_PHASES_ALL_STATUSES",
        "status": ("UNREVIEWED_SEARCHES_COMPLETE" if success == len(ncts)
                   else "PARTIAL_RETRY_OR_UNQUERIED"),
        "rosterSha256": digest,
        "rosterAsOf": snapshot.get("asOf"),
        "nctOrder": ncts,
        "totalPoolTrials": len(ncts),
        "nonTrialRowsExcluded": nontrials,
        "queriesSucceeded": success, "queriesFailed": failed,
        "queriesUnattempted": len(ncts) - success - failed,
        "publicationLeadsUnreviewed": sum(len(row["publicationLeads"]) for row in rows),
        "sourceReviewsCompleted": 0,
        "scientificAssessmentsCompleted": 0,
        "fdaPredictionsComputed": 0,
        "clinicalFindingsVerified": False,
        "limitations": [
            "Exact-NCT query matches are unreviewed candidates, not verified trial-publication links.",
            "Zero matches is not proof of no research or negative clinical evidence.",
            "This artifact never writes into POOL/FOCUS, assessments, history or production.",
        ],
        "rows": rows,
    }


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    try:
        with temp.open("w", encoding="utf8") as fh:
            json.dump(value, fh, indent=2, ensure_ascii=False, allow_nan=False)
            fh.write("\n")
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def run(roster, output, *, resume=False, limit=None, searcher=search_pubmed, pause=time.sleep):
    roster, output = Path(roster), Path(output)
    if roster.resolve() == output.resolve():
        raise ValueError("Cannot replace source POOL roster")
    raw = roster.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    snapshot = json.loads(raw)
    ncts, nontrials = extract_pool(snapshot)
    if limit is not None and (type(limit) is not int or limit < 1):
        raise ValueError("Limit must be positive; omit for entire POOL")
    if output.exists() and not resume:
        raise ValueError("Output exists; use --resume")
    if resume and output.exists():
        previous = json.loads(output.read_text(encoding="utf8"))
        validate_checkpoint(previous, digest, ncts)
        rows = previous["rows"]
    else:
        rows = [{"nct": nct, "status": "NOT_QUERIED", "publicationLeads": []}
                for nct in ncts]
    attempted = 0
    for i, entry in enumerate(rows):
        if entry["status"] == "QUERY_SUCCEEDED_UNREVIEWED":
            continue
        if limit is not None and attempted >= limit:
            break
        if attempted:
            pause(0.36)  # Respect NCBI unauthenticated 3 requests/s.
        attempted += 1
        try:
            candidate = searcher(ncts[i])
            if (not isinstance(candidate, dict) or candidate.get("nct") != ncts[i]
                    or candidate.get("status") != "QUERY_SUCCEEDED_UNREVIEWED"):
                raise ValueError("PubMed exact-NCT query response mismatch")
            test_rows = list(rows)
            test_rows[i] = candidate
            validate_checkpoint({
                "schemaVersion": VERSION, "rosterSha256": digest,
                "nctOrder": ncts, "rows": test_rows}, digest, ncts)
            rows[i] = candidate
        except (OSError, TimeoutError, ValueError, json.JSONDecodeError,
                HTTPError, URLError) as exc:
            rows[i] = {"nct": ncts[i], "status": "RETRY_REQUIRED",
                       "errorType": type(exc).__name__, "publicationLeads": []}
        save(output, report(snapshot, digest, ncts, nontrials, rows))
    value = report(snapshot, digest, ncts, nontrials, rows)
    save(output, value)
    return value


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--roster", type=Path,
                   default=Path("new-platform/frontend/data/tools-pool-snapshot.json"))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--limit", type=int, default=None,
                   help="Optional partial development sample; default searches entire POOL")
    a = p.parse_args(argv)
    value = run(a.roster, a.output, resume=a.resume, limit=a.limit)
    print(json.dumps({k: value[k] for k in ("status", "totalPoolTrials",
        "queriesSucceeded", "queriesFailed", "queriesUnattempted",
        "publicationLeadsUnreviewed")}))
    return 0 if value["status"] == "UNREVIEWED_SEARCHES_COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())

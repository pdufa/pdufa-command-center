#!/usr/bin/env python3
"""Discover PubMed records mentioning exact FOCUS NCT IDs.

These are unreviewed publication leads, NOT evidence of efficacy or FDA outcomes.
"""
import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

NCT = re.compile(r"^NCT[0-9]{8}$")
BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

def search(nct, opener=urllib.request.urlopen):
    if not NCT.fullmatch(nct):
        raise ValueError("Invalid NCT")
    params = urllib.parse.urlencode({"db": "pubmed", "term": f'"{nct}"[All Fields]',
                                     "retmode": "json", "retmax": "25", "sort": "pub date",
                                     "tool": "pdufa-focus-evidence"})
    url = BASE + "?" + params
    with opener(urllib.request.Request(url, headers={"User-Agent": "PDUFAFocusEvidence/1.0"}), timeout=20) as response:
        data = json.load(response)
    result = data.get("esearchresult", {})
    pmids = result.get("idlist", [])
    if not isinstance(pmids, list) or any(not isinstance(p, str) or not p.isdigit() for p in pmids):
        raise ValueError("Invalid PubMed response")
    count = int(result.get("count", 0))
    if count < len(pmids) or len(set(pmids)) != len(pmids):
        raise ValueError("Inconsistent PubMed response")
    return {"nct": nct, "searchUrl": url, "totalHits": count,
            "resultsTruncated": int(result.get("count", 0)) > len(pmids),
            "publicationLeads": [{"pmid": str(p), "sourceUrl": f"https://pubmed.ncbi.nlm.nih.gov/{p}/",
                                  "reviewStatus": "UNREVIEWED", "clinicalFinding": None}
                                 for p in pmids]}

def build(roster, searcher=search, sleep=time.sleep):
    ncts = list(dict.fromkeys(r["nct"] for r in roster.get("records", [])))
    if len(roster.get("records", [])) != 29 or len(ncts) != 29 or any(not NCT.fullmatch(n) for n in ncts):
        raise ValueError("Expected exact 29 FOCUS NCTs")
    rows = []
    for index, nct in enumerate(ncts):
        if index:
            sleep(0.36)  # Stay below NCBI's unauthenticated 3 requests/second limit.
        try:
            rows.append(searcher(nct))
        except (OSError, ValueError, TimeoutError) as exc:
            rows.append({"nct": nct, "status": "RETRY_REQUIRED", "publicationLeads": [],
                         "errorType": type(exc).__name__})
    failed = sum(r.get("status") == "RETRY_REQUIRED" for r in rows)
    return {"schemaVersion": 1, "status": "PARTIAL_RETRY_REQUIRED" if failed else "UNREVIEWED_PUBLICATION_DISCOVERY",
            "queriesSucceeded": len(rows) - failed, "queriesFailed": failed,
            "trialCount": 29, "publicationLeadsFound": sum(len(r["publicationLeads"]) for r in rows),
            "scientificAssessmentsCompleted": 0, "rows": rows}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--roster", type=Path, default=Path("new-platform/frontend/data/p3PostDataActive.json"))
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    report = build(json.loads(a.roster.read_text()))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"trialCount": 29, "publicationLeadsFound": report["publicationLeadsFound"],
                      "queriesSucceeded": report["queriesSucceeded"], "queriesFailed": report["queriesFailed"]}))
    if report["queriesFailed"]:
        raise SystemExit("PubMed discovery incomplete; retry required. Partial artifact preserved.")

if __name__ == "__main__":
    main()

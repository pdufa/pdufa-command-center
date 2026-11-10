#!/usr/bin/env python3
"""Exact-NCT, no-credentials source-gap acquisition and SAFETY source reconciliation.

Read-only receipt of *what upstream sources actually contained*. No SAP is
deemed authenticated by title alone; no full document or patient data stored.
No clinical method scores, reviewer events, FDA outcomes, DB writes or deploys.
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

NCT = "NCT06081894"
SCHEMA = "MAIN_ACACIA_ORIGINAL_SOURCE_GAP_AUDIT_V1"
SOURCES = {
    "REGISTRY": "https://clinicaltrials.gov/api/v2/studies/NCT06081894",
    "SPONSOR_HF_OCT12": ("https://ir.cytokinetics.com/press-releases/press-release-details/"
        "2026/Cytokinetics-Announces-Additional-Data-from-ACACIA-HCM-Presented-at-the-HFSA-"
        "Annual-Scientific-Meeting-2026/default.aspx"),
    "NEJM_PROTOCOL_SUPPLEMENT": ("https://www.nejm.org/doi/suppl/10.1056/"
        "NEJMoa2603021/suppl_file/nejmoa2603021_protocol.pdf"),
    "NEJM_APPENDIX_SUPPLEMENT": ("https://www.nejm.org/doi/suppl/10.1056/"
        "NEJMoa2603021/suppl_file/nejmoa2603021_appendix.pdf"),
}
LIMIT = {k: 7_500_000 if k.startswith("NEJM_") else 1_000_000 for k in SOURCES}


class RedirectBlocked(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("REDIRECT_BLOCKED")


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def observe(source_id):
    """Allowlisted external GET; return bytes only to memory, never store source."""
    if source_id not in SOURCES:
        raise ValueError("SOURCE_NOT_ALLOWLISTED")
    url = SOURCES[source_id]
    req = Request(url, headers={
        "Accept": "application/json" if source_id == "REGISTRY"
        else "application/pdf" if source_id.startswith("NEJM_")
        else "text/html",
        "User-Agent": "MAIN-ACACIA-Source-Gap-Audit/1.0",
    })
    try:
        with build_opener(RedirectBlocked()).open(req, timeout=17) as response:
            if response.status != 200 or response.geturl() != url:
                raise ValueError("UNEXPECTED_ORIGIN_OR_HTTP")
            content_type = response.headers.get("Content-Type", "").lower()
            body = response.read(LIMIT[source_id] + 1)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
        return None, "HTTP_OR_NETWORK_UNAVAILABLE", type(error).__name__
    if len(body) > LIMIT[source_id]:
        return None, "BODY_TOO_LARGE", "SIZE_LIMIT"
    expected = ("json" if source_id == "REGISTRY" else
                "pdf" if source_id.startswith("NEJM_") else "html")
    if expected not in content_type:
        return None, "UNEXPECTED_CONTENT_TYPE", "CONTENT_TYPE"
    if expected == "pdf" and not body.startswith(b"%PDF-"):
        return None, "NOT_A_PDF", "PDF_SIGNATURE"
    return body, "RETRIEVED", None


def check_registry(data):
    if not isinstance(data, dict):
        return {"identity": "UNVERIFIED", "sapDocumentListed": "UNVERIFIED",
                "largeDocuments": None, "resultsPosted": "UNVERIFIED"}
    pm = data.get("protocolSection", {})
    if not isinstance(pm, dict) or pm.get("identificationModule", {}).get("nctId") != NCT:
        return {"identity": "MISMATCH", "sapDocumentListed": "UNVERIFIED",
                "largeDocuments": None, "resultsPosted": "UNVERIFIED"}
    design = pm.get("designModule", {})
    phases = design.get("phases", []) if isinstance(design, dict) else []
    if not isinstance(phases, list) or "PHASE3" not in phases:
        return {"identity": "MISMATCH", "sapDocumentListed": "UNVERIFIED",
                "largeDocuments": None, "resultsPosted": "UNVERIFIED"}
    documents = data.get("documentSection", {})
    module = documents.get("largeDocumentModule", {}) if isinstance(documents, dict) else {}
    large = module.get("largeDocs", []) if isinstance(module, dict) else []
    if not isinstance(large, list):
        large = []
    sap = any(isinstance(item, dict) and
              re.search(r"\bSAP\b|statistical analysis plan", " ".join(
                  str(item.get(k) or "") for k in ("title", "type", "filename", "fileName")), re.I)
              for item in large)
    return {
        "identity": "MATCH_PHASE3",
        "sapDocumentListed": "CANDIDATE_TITLE_ONLY" if sap else "NOT_LISTED_IN_THIS_RESPONSE",
        "largeDocuments": len(large),
        "resultsPosted": isinstance(data.get("resultsSection"), dict),
    }


def check_sponsor(html_bytes):
    parser = VisibleText()
    parser.feed(html_bytes.decode("utf-8", "replace"))
    text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    # Verify the narrow October 12 sponsor statement, not a generically
    # matched 12/3 number in promotional or label text elsewhere.
    correct_document = (
        "Cytokinetics Announces Additional Data from ACACIA-HCM" in text
        and "October 12, 2026" in text
        and "non-obstructive" in text.lower()
    )
    if not correct_document:
        return {"documentIdentity": "UNVERIFIED",
                "hfBreakdown": "NOT_VERIFIED", "lvefAssociatedTreated": None,
                "otherTreated": None, "treatedReportedTotal": None,
                "placeboReportedTotal": None}
    fragment = re.search(
        r"two participants.{0,220}?heart failure.{0,170}?LVEF.{0,160}?"
        r"Ten additional patients.{0,160}?heart failure.{0,170}?LVEF"
        r".{0,120}?total of 12 patients.{0,100}?three patients",
        text, re.I
    )
    if not fragment:
        return {"documentIdentity": "MATCH", "hfBreakdown": "NOT_VERIFIED",
                "lvefAssociatedTreated": None, "otherTreated": None,
                "treatedReportedTotal": None, "placeboReportedTotal": None}
    return {
        "documentIdentity": "MATCH",
        "hfBreakdown": "PUBLIC_SPONSOR_COMPONENTS_MATCH_2_PLUS_10_EQUALS_12_VS_3",
        "lvefAssociatedTreated": 2,
        "otherTreated": 10,
        "treatedReportedTotal": 12,
        "placeboReportedTotal": 3,
    }


def receipt_sha(item):
    return hashlib.sha256(json.dumps({k: v for k, v in item.items()
                                      if k != "receiptSha256"},
                                     sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def audit(*, fetcher=observe, timestamp=None, commit=None, run=None):
    timestamp = timestamp or datetime.now(timezone.utc)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("Timezone-aware time required")
    now = timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    entries = []
    registry = None
    sponsor = None
    for name, url in SOURCES.items():
        data, status, error = fetcher(name)
        entry = {"sourceId": name, "sourceUrl": url, "checkedAt": now,
                 "status": status, "errorCategory": error,
                 "sha256": hashlib.sha256(data).hexdigest() if data is not None else None,
                 "bytes": len(data) if data is not None else None}
        if data is not None and name == "REGISTRY":
            try:
                registry = check_registry(json.loads(data))
            except (ValueError, UnicodeDecodeError, TypeError):
                registry = None
                entry["status"] = "INVALID_JSON"
        if data is not None and name == "SPONSOR_HF_OCT12":
            sponsor = check_sponsor(data)
        entries.append(entry)
    report = {
        "schema": SCHEMA,
        "nct": NCT,
        "checkedAt": now,
        "gitCommit": str(commit)[:64] if commit else None,
        "workflowRun": str(run)[:64] if run else None,
        "mode": "PUBLIC_RESEARCH_SOURCE_DISCOVERY_ONLY",
        "sources": entries,
        "registry": registry or {
            "identity": "UNVERIFIED", "sapDocumentListed": "UNVERIFIED",
            "largeDocuments": None, "resultsPosted": "UNVERIFIED"
        },
        "sponsor": sponsor or {
            "documentIdentity": "UNVERIFIED", "hfBreakdown": "NOT_VERIFIED",
            "lvefAssociatedTreated": None, "otherTreated": None,
            "treatedReportedTotal": None, "placeboReportedTotal": None
        },
        "finalLockedSapAuthenticated": False,
        "originalPrimarySensitivityReviewed": False,
        "hfSeriousEvent11vs1Versus12vs3Reconciled": False,
        "safetyLineListingAdjudicated": False,
        "independentPhaseReviewerSigned": False,
        "independentClinicalGradesWritten": 0,
        "fdaPrediction": "ABSTAIN",
        "calibratedAccuracy": None,
        "interpretation": (
            "NEJM supplement availability and sponsor text are only public research leads. "
            "The sponsor's 2+10=12 vs 3 breakdown does NOT reconcile published 11 vs 1 "
            "without original event definitions, follow-up dates and analysis populations. "
            "A public protocol supplement is not a final locked SAP. No clinical scoring."
        )
    }
    report["receiptSha256"] = receipt_sha(report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="acacia-public-gap-audit/receipt.json")
    args = parser.parse_args()
    import os
    report = audit(commit=os.environ.get("GITHUB_SHA"),
                   run=os.environ.get("GITHUB_RUN_ID"))
    output = Path(args.output)
    output.parent.mkdir(exist_ok=True, parents=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "stage": "ACACIA_PUBLIC_SOURCE_GAP_RECONCILIATION",
        "status": "PASS_RESEARCH_AUDIT",
        "sourceStatuses": {r["sourceId"]: r["status"] for r in report["sources"]},
        "sapListed": report["registry"]["sapDocumentListed"],
        "sponsorBreakdown": report["sponsor"]["hfBreakdown"],
        "hfDifferenceIndependentlyReconciled": False,
        "signedGrades": 0, "fdaPrediction": "ABSTAIN",
        "receiptSha256": report["receiptSha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

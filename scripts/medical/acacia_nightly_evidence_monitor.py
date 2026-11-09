#!/usr/bin/env python3
"""One-trial, public-only ACACIA source checkpoint for isolated MAIN research.

This standalone runner creates dated, hash-linked *research source receipts*.
It does not run clinical grades, acquire reviewer credentials, change trial
rosters, update production, or assign FDA outcomes/probabilities.

Run with Python 3.12 stdlib:
  python scripts/medical/acacia_nightly_evidence_monitor.py --output evidence-receipts/receipt.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

SCHEMA = "MAIN_ACACIA_PUBLIC_EVIDENCE_CHECKPOINT_V1"
NCT = "NCT06081894"
SOURCES = {
    "REGISTRY": "https://clinicaltrials.gov/api/v2/studies/NCT06081894",
    "NEJM_PIVOTAL_INDEX": "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID%3A42663312&format=json&pageSize=5",
}
BASELINE_POSTED = "2026-09-22"
MAX_SOURCE_BYTES = 350_000
RESEARCH_CARDS = (("5.1", 3), ("4.2", 3), ("5.3", 2))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("REDIRECT_NOT_ALLOWED")


class SourceUnavailable(Exception):
    """An upstream HTTP, response-size, JSON or timeout failure."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def get(data, *path):
    for key in path:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def is_registry(data) -> bool:
    ident = get(data, "protocolSection", "identificationModule")
    phases = get(data, "protocolSection", "designModule", "phases")
    if not isinstance(ident, dict) or ident.get("nctId") != NCT or not isinstance(phases, list):
        return False
    title = str(ident.get("briefTitle") or "") + " " + str(ident.get("officialTitle") or "")
    return "PHASE3" in phases and bool(re.search(r"ACACIA|non[\s-]?obstructive", title, re.I))


def is_publication(data) -> bool:
    results = get(data, "resultList", "result")
    if not isinstance(results, list):
        return False
    for result in results:
        if not isinstance(result, dict):
            continue
        title = str(result.get("title") or "")
        if (str(result.get("pmid") or result.get("id") or "") == "42663312"
                and re.search("aficamten", title, re.I)
                and re.search("hypertrophic cardiomyopathy", title, re.I)):
            return True
    return False


def registry_candidates(data) -> list[str]:
    if not is_registry(data):
        return []
    candidates = []
    posted = get(data, "protocolSection", "statusModule",
                 "studyLastUpdatePostDateStruct", "date")
    if (isinstance(posted, str) and re.fullmatch(r"20\d{2}-\d{2}-\d{2}", posted)
            and posted > BASELINE_POSTED):
        candidates.append("REGISTRY_RECORD_UPDATED_SINCE_BASELINE")
    results = get(data, "resultsSection")
    if isinstance(results, dict) and results:
        candidates.append("NEW_REGISTRY_RESULTS_CANDIDATE")
    docs = get(data, "documentSection", "largeDocumentModule", "largeDocs")
    if isinstance(docs, list) and any(
            isinstance(row, dict)
            and re.search(r"\bSAP\b|statistical analysis plan",
                          str(row.get("title") or ""), re.I)
            for row in docs):
        candidates.append("PUBLIC_SAP_TITLE_CANDIDATE_UNREVIEWED")
    return candidates


def fetch_public(source_id: str) -> tuple[dict, bytes]:
    if source_id not in SOURCES:
        raise ValueError("Source not allowlisted")
    url = SOURCES[source_id]
    req = Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "PDUFA-MAIN-Public-Source-Audit/1.0",
    })
    opener = build_opener(NoRedirect())
    try:
        with opener.open(req, timeout=15) as response:
            if response.geturl() != url:
                raise SourceUnavailable("UNEXPECTED_ORIGIN")
            if response.status != 200:
                raise SourceUnavailable("UNEXPECTED_HTTP_STATUS")
            if "json" not in response.headers.get("Content-Type", "").lower():
                raise SourceUnavailable("NON_JSON_RESPONSE")
            blob = response.read(MAX_SOURCE_BYTES + 1)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise SourceUnavailable("UPSTREAM_UNAVAILABLE") from exc
    if len(blob) > MAX_SOURCE_BYTES:
        raise SourceUnavailable("BODY_TOO_LARGE")
    try:
        doc = json.loads(blob)
    except (UnicodeError, ValueError) as exc:
        raise SourceUnavailable("INVALID_JSON") from exc
    if not isinstance(doc, dict):
        raise SourceUnavailable("INVALID_SHAPE")
    return doc, blob


def receipt_hash(receipt: dict) -> str:
    return sha(canonical({k: v for k, v in receipt.items()
                          if k != "receiptSha256"}).encode("utf-8"))


def previous_index(previous: dict | None):
    if previous is None:
        return None, None, "NONE_PROVIDED"
    if (not isinstance(previous, dict) or previous.get("schema") != SCHEMA
            or previous.get("nct") != NCT
            or previous.get("receiptSha256") != receipt_hash(previous)):
        return None, None, "PREVIOUS_INVALID"
    sources = previous.get("sources")
    if (not isinstance(sources, list) or len(sources) != len(SOURCES)
            or {row.get("sourceId") for row in sources
                if isinstance(row, dict)} != set(SOURCES)):
        return None, None, "PREVIOUS_INVALID"
    return {x["sourceId"]: x for x in sources}, previous["receiptSha256"], "PREVIOUS_VALID"


def make_checkpoint(*, fetcher=fetch_public, prior=None, now=None, git_sha=None, run_id=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Timezone-aware observation time required")
    date = now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    previous, previous_digest, history = previous_index(prior)
    captures = []
    changes = []
    candidates = []
    for source_id, url in SOURCES.items():
        entry = {"sourceId": source_id, "sourceUrl": url,
                 "observedAt": date, "status": "UNAVAILABLE",
                 "responseSha256": None, "responseBytes": None,
                 "changedSincePrevious": None, "researchCandidates": [],
                 "errorCategory": None}
        try:
            doc, blob = fetcher(source_id)
            if not isinstance(doc, dict) or not isinstance(blob, bytes):
                raise SourceUnavailable("INVALID_FETCHED_CONTENT")
            if len(blob) > MAX_SOURCE_BYTES:
                raise SourceUnavailable("BODY_TOO_LARGE")
            ok = is_registry(doc) if source_id == "REGISTRY" else is_publication(doc)
            entry["status"] = "MATCH" if ok else "CHANGED"
            entry["responseSha256"] = sha(blob)
            entry["responseBytes"] = len(blob)
            if previous is not None:
                prior_hash = previous[source_id].get("responseSha256")
                if isinstance(prior_hash, str) and re.fullmatch(r"[a-f0-9]{64}", prior_hash):
                    entry["changedSincePrevious"] = prior_hash != entry["responseSha256"]
                    if entry["changedSincePrevious"]:
                        changes.append(source_id)
            if ok and source_id == "REGISTRY":
                entry["researchCandidates"] = registry_candidates(doc)
                candidates.extend(entry["researchCandidates"])
        except SourceUnavailable as exc:
            entry["errorCategory"] = str(exc)
        captures.append(entry)

    statuses = [c["status"] for c in captures]
    if "CHANGED" in statuses or changes or candidates:
        status = "REVIEW_REQUIRED"
    elif "UNAVAILABLE" in statuses:
        status = "PARTIAL_UNAVAILABLE"
    else:
        status = "SOURCE_IDENTITIES_MATCH"
    result = {
        "schema": SCHEMA,
        "nct": NCT,
        "observedAt": date,
        "runId": str(run_id)[:64] if run_id else None,
        "sourceCommit": str(git_sha)[:64] if git_sha else None,
        "checkpointKind": "PUBLIC_RESEARCH_EVIDENCE_ONLY",
        "historyStatus": history,
        "previousReceiptSha256": previous_digest,
        "status": status,
        "sources": captures,
        "sourceChangesSincePrevious": changes,
        "newResearchCandidates": sorted(set(candidates)),
        "provisionalDocumentaryScores": [
            {"assessmentId": name, "methodIndex": 1,
             "points": value, "outOf": 5,
             "meaning": "DOCUMENT_AVAILABILITY_NOT_CLINICAL_GRADE"}
            for name, value in RESEARCH_CARDS
        ],
        "evidenceSnapshotAsOf": "2026-11-08",
        "scoresRecheckedAgainstOriginalSnapshot": True,
        "newDocumentsAutomaticallyGraded": False,
        "officialClinicalGradeEventsWritten": 0,
        "independentPhaseSignoffsWritten": 0,
        "fdaPrediction": "ABSTAIN",
        "accuracy": "NOT_CALIBRATED",
        "rosterMutations": 0,
        "productionWrites": 0,
        "notes": ("This artifact records an unattended-capable public-source check. "
                  "No finding, SAP candidate or changed document has been clinically adjudicated.")
    }
    result["receiptSha256"] = receipt_hash(result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="acacia-evidence-monitor/receipt.json")
    parser.add_argument("--previous", help="Optional prior hash-verified JSON artifact")
    args = parser.parse_args()
    prior = None
    if args.previous:
        try:
            prior = json.loads(Path(args.previous).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            prior = {"schema": "INVALID_PREVIOUS"}
    checkpoint = make_checkpoint(
        prior=prior,
        git_sha=__import__("os").environ.get("GITHUB_SHA"),
        run_id=__import__("os").environ.get("GITHUB_RUN_ID"),
    )
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(checkpoint, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": checkpoint["status"],
        "nct": checkpoint["nct"],
        "sourceStatuses": {x["sourceId"]: x["status"] for x in checkpoint["sources"]},
        "prior": checkpoint["historyStatus"],
        "changes": checkpoint["sourceChangesSincePrevious"],
        "candidates": checkpoint["newResearchCandidates"],
        "clinicalGradesWritten": 0,
        "fdaPrediction": "ABSTAIN",
        "receiptSha256": checkpoint["receiptSha256"]
    }, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "CHECKPOINT_FAILED",
                          "errorKind": type(exc).__name__,
                          "clinicalGradesWritten": 0}), file=sys.stderr)
        raise SystemExit(1)

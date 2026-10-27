"""Read-only FDA source retrieval and SHA-256 inventory.

Fetches only allowlisted HTTPS FDA PDF URLs from staged candidates. This is
source-byte collection, NOT independent adjudication or model promotion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def permitted_fda_pdf(url):
    if not isinstance(url, str):
        return False
    try:
        p = urlsplit(url)
        return (p.scheme == "https" and p.hostname in
                {"www.accessdata.fda.gov", "www.fda.gov"} and
                p.path.lower().endswith(".pdf") and
                not p.username and not p.password and not p.port)
    except ValueError:
        return False


class NoRedirects(__import__("urllib.request", fromlist=["HTTPRedirectHandler"]).HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def collect(rows, opener=None):
    from urllib.request import build_opener
    opener = opener or build_opener(NoRedirects)
    report = []
    for row in rows:
        url = row.get("official_source_url") if isinstance(row, dict) else None
        item = {"application_id": row.get("application_id") if isinstance(row, dict) else None,
                "official_source_url": url, "status": "NOT_FETCHED",
                "sha256": None, "independently_verified": False, "model_eligible": False}
        if not permitted_fda_pdf(url):
            item["status"] = "BLOCKED_NOT_ALLOWLISTED_FDA_PDF"
        else:
            try:
                req = Request(url, headers={"User-Agent": "PDUFA-Research-Evidence-Collector/1.0"})
                with opener.open(req, timeout=12) as resp:
                    if resp.status != 200:
                        raise ValueError("non-200 response")
                    payload = resp.read(10_000_001)
                    if len(payload) > 10_000_000 or not payload.startswith(b"%PDF-"):
                        raise ValueError("not a valid size-limited PDF")
                    item["sha256"] = hashlib.sha256(payload).hexdigest()
                    item["status"] = "BYTES_HASHED_NOT_ADJUDICATED"
            except Exception as exc:
                item["status"] = "FETCH_FAILED"
                item["error_type"] = type(exc).__name__
        report.append(item)
    return {"records": report, "independently_verified": 0, "model_eligible": 0,
            "warning": "PDF hash establishes byte identity only, not FDA decision adjudication."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-dir", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in
            sorted(args.candidate_dir.glob("fda_candidate_*.json"))]
    print(json.dumps(collect(rows), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

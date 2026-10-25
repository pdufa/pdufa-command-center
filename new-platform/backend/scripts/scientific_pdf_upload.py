#!/usr/bin/env python3
"""Curator-operated scientific PDF capture. Never marks evidence verified.

Usage:
  PDUFA_INTERNAL_API_KEY=... PDUFA_SCIENTIFIC_REVIEW_WRITE_KEY=... \
  python scientific_pdf_upload.py --pdf /path/to/source.pdf \
    --nct NCT02142738 --gate protocol_sap --source-url https://... \
    --source-type protocol_sap --curator "Reviewer name"

Requires PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED=1 and
PDUFA_SCIENTIFIC_DOCUMENT_CAPTURE_ENABLED=1 on the isolated Render service.
Never pass credentials as CLI flags or URLs.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MAX_BYTES = 4 * 1024 * 1024
API = "https://pdufa-scientific-assessment-review.onrender.com"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pdf", required=True, type=Path)
    p.add_argument("--nct", required=True)
    p.add_argument("--gate", required=True, choices=["protocol_sap", "published_results", "independent_replication", "official_regulatory"])
    p.add_argument("--source-url", required=True)
    p.add_argument("--source-type", required=True, choices=["peer_reviewed_publication", "official_agency_document", "protocol_sap", "clinical_study_report", "institutional_summary", "other"])
    p.add_argument("--curator", required=True)
    p.add_argument("--dry-run", action="store_true", help="Validate local PDF and print digest without transmitting")
    a = p.parse_args()
    if not a.nct.startswith("NCT") or len(a.nct) != 11 or not a.nct[3:].isdigit():
        p.error("Exact NCT identifier required")
    if not a.source_url.startswith("https://"):
        p.error("HTTPS source URL required")
    if not 2 <= len(a.curator) <= 80:
        p.error("Curator label must be 2–80 characters")
    if not a.pdf.is_file() or a.pdf.stat().st_size > MAX_BYTES:
        p.error("Local PDF missing or larger than 4 MiB")
    raw = a.pdf.read_bytes()
    if not 32 <= len(raw) <= MAX_BYTES or not raw.startswith(b"%PDF-") or b"%%EOF" not in raw[-1024:]:
        p.error("PDF signature, EOF, or length invalid")
    digest = hashlib.sha256(raw).hexdigest()
    print(json.dumps({"nctId": a.nct, "sha256": digest, "bytes": len(raw), "dryRun": a.dry_run}))
    if a.dry_run:
        return
    internal = os.environ.get("PDUFA_INTERNAL_API_KEY")
    review = os.environ.get("PDUFA_SCIENTIFIC_REVIEW_WRITE_KEY")
    if not internal or not review or internal == review:
        p.error("Two distinct credentials must be supplied via environment variables")
    body = json.dumps({
        "gateId": a.gate, "sourceUrl": a.source_url,
        "sourceType": a.source_type, "sha256": digest,
        "contentBase64": base64.b64encode(raw).decode("ascii"),
        "capturedBy": a.curator,
    }).encode()
    req = Request(API + "/api/scientific-assessment/source-documents/" + a.nct,
                  data=body, headers={"Content-Type": "application/json",
                  "X-PDUFA-Scientific-Review-Key": review,
                  "X-PDUFA-Internal-Key": internal}, method="POST")
    try:
        with urlopen(req, timeout=30) as response:
            print(response.read().decode())
    except HTTPError as e:
        raise SystemExit("Capture rejected (HTTP " + str(e.code) + "); check permissions and source identity") from None
    except URLError:
        raise SystemExit("Capture unavailable; no successful upload confirmed") from None


if __name__ == "__main__":
    main()

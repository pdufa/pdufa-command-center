"""Compare the pinned real Drugs@FDA original-submission tables to FDA CRLs.

Download ONLY FDA's public manifest and quarantined CRL source. Use the
already collected private Drugs@FDA tables in the isolated research workflow.
No app database writes, source-letter publication, model scoring, or trading.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from app.hop_drugsfda_submission_spine import audit_original_submissions
from app.hop_fda_original_letter_bridge import (
    crosswalk_original_submissions_to_published_letters,
)
from app.hop_openfda_snapshot import build_crl_snapshot
from app.hop_fda_unmatched_letter_triage import build_letter_identity_gap_triage
from app.hop_fda_gap_research_packets import build_source_search_packets

MANIFEST_URL = "https://api.fda.gov/download.json"
SOURCE_DIR = Path(__file__).resolve().parents[1] / "app" / "research_sources"
PINNED_CRLS = SOURCE_DIR / "hop_fda_page_review_worksheet_audit_index.json"
PINNED_DRUGSFDA = SOURCE_DIR / "hop_drugsfda_original_submissions_20261025.json"


def fetch_pinned_official_bytes(
    url: str, *, hostname: str, prefix: str, max_bytes: int,
) -> bytes:
    parsed = urlparse(url)
    if (parsed.scheme != "https" or parsed.hostname != hostname
            or not parsed.path.startswith(prefix) or parsed.username
            or parsed.password or parsed.port or parsed.fragment):
        raise ValueError("Unexpected official FDA source URL")
    request = urllib.request.Request(
        url, headers={"User-Agent": "PDUFA-fda-letter-submission-identity-audit/1.0"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        redirected = urlparse(response.geturl())
        if (redirected.scheme != "https" or redirected.hostname != hostname
                or not redirected.path.startswith(prefix) or redirected.username
                or redirected.password or redirected.port or redirected.fragment):
            raise ValueError("Source left the pinned FDA domain")
        payload = response.read(max_bytes + 1)
    if not payload or len(payload) > max_bytes:
        raise ValueError("Unexpected FDA source size")
    return payload


def collect_real_crosswalk(
    applications: Path, submissions: Path, *, as_of: date,
    private_gap_worklist: Path | None = None,
    private_grouped_packets: Path | None = None,
) -> dict:
    pinned_crl = json.loads(PINNED_CRLS.read_text(encoding="utf-8"))
    pinned_drug = json.loads(PINNED_DRUGSFDA.read_text(encoding="utf-8"))
    original = audit_original_submissions(applications, submissions, as_of=as_of)
    if (original["source_application_tsv_sha256"] !=
            pinned_drug["applications_tsv_sha256"]
            or original["source_submission_tsv_sha256"] !=
            pinned_drug["submissions_tsv_sha256"]):
        raise ValueError("Drugs@FDA source bytes have changed since pinned audit")

    manifest = json.loads(fetch_pinned_official_bytes(
        MANIFEST_URL, hostname="api.fda.gov", prefix="/download.json",
        max_bytes=8_000_000,
    ))
    try:
        parts = manifest["results"]["transparency"]["crl"]["partitions"]
    except (KeyError, TypeError):
        raise ValueError("Missing official CRL partitions in FDA manifest") from None
    if not isinstance(parts, list) or len(parts) != 1:
        raise ValueError("CRL source partition set differs from pinned single archive")
    part = parts[0]
    if not isinstance(part, dict) or not isinstance(part.get("file"), str):
        raise ValueError("Invalid official CRL partition metadata")
    url = part["file"]
    downloaded = fetch_pinned_official_bytes(
        url, hostname="download.open.fda.gov",
        prefix="/transparency/crl/", max_bytes=12_000_000,
    )
    observed_crl_digest = hashlib.sha256(downloaded).hexdigest()
    if observed_crl_digest != pinned_crl.get("source_archive_sha256"):
        raise ValueError("Published FDA CRL archive changed from pinned audit snapshot")
    snapshot, source_audit = build_crl_snapshot(
        manifest, {url: downloaded}, as_of=as_of,
    )
    result = crosswalk_original_submissions_to_published_letters(
        original, snapshot, as_of=as_of,
    )
    # Official source identity-gap queue is private/local ONLY. A published
    # letter absent from the approved-centric table is not an FDA nonapproval.
    review_queue, gap_audit = build_letter_identity_gap_triage(
        original, snapshot, applications_tsv=applications, as_of=as_of,
    )
    if private_gap_worklist is not None:
        private_gap_worklist.parent.mkdir(parents=True, exist_ok=True)
        private_gap_worklist.write_text(
            json.dumps(review_queue, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    result["letter_identity_gap_triage_audit"] = gap_audit
    result["private_letter_level_queue_not_exported"] = True
    packets, packet_aggregate = build_source_search_packets(
        review_queue, as_of=as_of, pinned_audit=gap_audit,
    )
    if private_grouped_packets is not None:
        private_grouped_packets.parent.mkdir(parents=True, exist_ok=True)
        private_grouped_packets.write_text(
            json.dumps(packets, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    result["application_source_research_packet_audit"] = packet_aggregate
    result["private_grouped_packet_rows_not_exported"] = True
    if (result["published_letter_references"] != pinned_drug.get(
            "published_letter_references", result["published_letter_references"])
            or result["published_letter_references"] != 458):
        raise ValueError("Published CRL snapshot no longer matches audited corpus")
    result["source_crl_archive_sha256"] = observed_crl_digest
    result["source_crl_snapshot_status"] = source_audit["status"]
    result["pinned_original_submissions_audit_url"] = (
        "https://github.com/pdufa/pdufa-command-center/actions/runs/40246351051"
    )
    result["no_raw_applications_or_letters_exported"] = True
    result["no_live_scanner_or_model_action"] = True
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Source-identity-only original NDA/BLA vs FDA CRL bridge"
    )
    parser.add_argument("--applications", type=Path, required=True)
    parser.add_argument("--submissions", type=Path, required=True)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--private-gap-worklist", type=Path,
                        help="Optional private-only unpublished letter review queue")
    parser.add_argument("--private-grouped-packets", type=Path,
                        help="Optional private-only grouped FDA application research packets")
    args = parser.parse_args()
    result = collect_real_crosswalk(
        args.applications, args.submissions, as_of=args.as_of,
        private_gap_worklist=args.private_gap_worklist,
        private_grouped_packets=args.private_grouped_packets,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    # Shell success indicates only an internally consistent source-ID audit.
    # Regulatory outcomes / denominator / model confidence remain unverified.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

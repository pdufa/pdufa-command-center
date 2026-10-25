"""Download the official Drugs@FDA table ZIP to audit ORIGINAL NDA/BLA submissions.

Research-only collection: reports source table counts/hashes, never FDA review
cycles, scientific outcome labels, model probabilities, or any live DB change.
Only two expected official table files are read from the ZIP, with size/path/CRC
safeguards. Raw downloaded tables are not retained in GitHub build artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import urllib.request
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from app.hop_drugsfda_submission_spine import audit_original_submissions

OFFICIAL_DOWNLOAD = "https://www.fda.gov/media/89850/download?attachment="
OFFICIAL_DOWNLOAD_HOSTS = frozenset({"www.fda.gov", "fda.gov", "accessdata.fda.gov"})
MAX_ZIP_BYTES = 100 * 1024 * 1024
MAX_TABLE_BYTES = 150 * 1024 * 1024
EXPECTED_FILENAMES = {"applications.txt", "submissions.txt"}
PUBLIC_COUNTS = (
    "application_rows_in_extract",
    "application_type_counts",
    "submission_rows_in_extract",
    "original_nda_bla_submission_rows",
    "distinct_nda_bla_applications_in_original_submission_inventory",
    "excluded_submission_row_reason_counts",
    "source_data_quality_flag_counts",
    "independently_verified_fda_review_cycles",
    "complete_original_nda_bla_application_denominator_verified",
    "unapproved_applications_absent_from_export_possible",
    "submission_number_is_not_review_cycle",
    "raw_status_not_a_verified_decision_label",
    "model_eligible_records",
    "approval_rate", "prediction_probability", "readiness",
)


def _official_final_url(url: str) -> bool:
    try:
        parts = urlparse(url)
        return (
            parts.scheme == "https"
            and parts.hostname in OFFICIAL_DOWNLOAD_HOSTS
            and parts.username is None and parts.password is None
            and parts.port is None
        )
    except (ValueError, TypeError):
        return False


def extract_two_official_tables(
    data: bytes, destination: Path,
) -> dict[str, Path]:
    """In-memory archive inspection; do not extract arbitrary ZIP members."""
    if not isinstance(data, bytes) or len(data) < 50 or len(data) > MAX_ZIP_BYTES:
        raise ValueError("Unexpected FDA ZIP byte size")
    by_name: dict[str, zipfile.ZipInfo] = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.infolist()
        if not members or len(members) > 40:
            raise ValueError("Unexpected FDA table archive file count")
        for member in members:
            filename = member.filename.replace("\\", "/")
            if (filename.startswith("/") or ".." in filename.split("/")
                    or re.match(r"^[A-Za-z]:", filename)
                    or member.flag_bits & 0x1):
                raise ValueError("Unsafe encrypted or traversal ZIP member")
            # Only explicitly requested table basenames are used.
            basename = filename.split("/")[-1].lower()
            if basename in EXPECTED_FILENAMES:
                if basename in by_name or member.is_dir():
                    raise ValueError("Duplicate or directory-only required FDA table")
                if member.file_size <= 0 or member.file_size > MAX_TABLE_BYTES:
                    raise ValueError("Required FDA table exceeds size bounds")
                by_name[basename] = member
        if set(by_name) != EXPECTED_FILENAMES:
            raise ValueError("Official ZIP missing Applications or Submissions table")
        destination.mkdir(parents=True, exist_ok=True)
        files = {}
        for key, member in by_name.items():
            content = archive.read(member)  # CRC verified by zipfile.
            if len(content) != member.file_size or b"\x00" in content[:1024]:
                raise ValueError("Invalid/unsupported FDA TSV bytes")
            name = "Applications.txt" if key == "applications.txt" else "Submissions.txt"
            path = destination / name
            path.write_bytes(content)
            files[key] = path
    return files


def download_official_source_bytes(url: str = OFFICIAL_DOWNLOAD) -> tuple[bytes, str]:
    if url != OFFICIAL_DOWNLOAD:
        raise ValueError("Only the pinned official FDA download URL is allowed")
    request = urllib.request.Request(
        url, headers={"User-Agent": "PDUFA-offline-source-research/1.0",
                      "Accept": "application/zip,application/octet-stream,*/*"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        final_url = response.geturl()
        if not _official_final_url(final_url):
            raise ValueError("FDA source redirected to an unauthorized host")
        chunks = []
        size = 0
        while True:
            piece = response.read(1024 * 1024)
            if not piece:
                break
            size += len(piece)
            if size > MAX_ZIP_BYTES:
                raise ValueError("FDA ZIP exceeds maximum accepted size")
            chunks.append(piece)
    return b"".join(chunks), final_url


def collect_aggregate_audit(
    downloaded_zip: bytes, official_final_url: str, working_dir: Path,
    *, as_of: date,
) -> dict:
    if not _official_final_url(official_final_url):
        raise ValueError("Unapproved FDA file redirect")
    files = extract_two_official_tables(downloaded_zip, working_dir)
    result = audit_original_submissions(
        files["applications.txt"], files["submissions.txt"], as_of=as_of,
    )
    # Never put per-submission source data into a public research artifact.
    summary = {
        "status": "OFFICIAL_FDA_TABLE_ORIGINAL_SUBMISSIONS_QUARANTINED",
        "fda_download_url": OFFICIAL_DOWNLOAD,
        "fda_final_download_url": official_final_url,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "cutoff_as_of": as_of.isoformat(),
        "source_zip_sha256": hashlib.sha256(downloaded_zip).hexdigest(),
        "applications_tsv_sha256": result["source_application_tsv_sha256"],
        "submissions_tsv_sha256": result["source_submission_tsv_sha256"],
    }
    for key in PUBLIC_COUNTS:
        summary[key] = result[key]
    summary["original_action_dates_independently_verified"] = 0
    summary["complete_nda_bla_review_cycle_population"] = None
    summary["predictive_accuracy"] = None
    summary["no_training_or_production_import"] = True
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect FDA's raw Drugs@FDA tables, output summary only"
    )
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Private temp directory, not a repository path")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    zip_bytes, redirect = download_official_source_bytes()
    summary = collect_aggregate_audit(
        zip_bytes, redirect, args.output_dir / "private_original_tables",
        as_of=args.as_of,
    )
    public_dir = args.output_dir / "public_aggregate_only"
    public_dir.mkdir(parents=True, exist_ok=True)
    (public_dir / "fda_original_submissions_coverage_audit.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True, indent=2))
    # This exit status deliberately does NOT mean independent FDA validation.
    # A successful shell exit is allowed solely to save a read-only report in
    # an isolated research workflow with no production/model authorization.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

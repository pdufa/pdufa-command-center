"""Read-only join of two official FDA bulk archives; never generates model labels."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
from urllib.request import Request, urlopen

from app.hop_openfda_snapshot import build_crl_snapshot
from app.hop_drugsfda_snapshot import stage_drugsfda_manifest
from app.hop_fda_application_crosswalk import crosswalk_public_fda_sources
from app.hop_fda_review_cycle_triage import triage_published_letter_cycles
from app.hop_fda_identity_review_queue import create_fda_identity_review_queue
from app.hop_fda_document_probe import probe_fda_review_documents

MANIFEST_URL = "https://api.fda.gov/download.json"


def fetch(url: str, max_bytes: int) -> bytes:
    with urlopen(Request(url, headers={"User-Agent": "PDUFA-HOP-identity-reconciliation/1.0"}),
                 timeout=60) as response:
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("FDA bulk archive download exceeds limit")
    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--pdf-probe-offset", type=int, default=0)
    parser.add_argument("--pdf-probe-limit", type=int, default=20)
    args = parser.parse_args()
    manifest = json.loads(fetch(MANIFEST_URL, 8_000_000))
    crl_parts = manifest["results"]["transparency"]["crl"]["partitions"]
    drug_parts = manifest["results"]["drug"]["drugsfda"]["partitions"]
    letters, letter_audit = build_crl_snapshot(
        manifest,
        {p["file"]: fetch(p["file"], 12_000_000) for p in crl_parts},
        date.today(),
    )
    registry, registry_audit = stage_drugsfda_manifest(
        manifest,
        {p["file"]: fetch(p["file"], 22_000_000) for p in drug_parts},
        date.today(),
    )
    crosswalk, audit = crosswalk_public_fda_sources(letters, registry)
    triage_cases, triage_audit = triage_published_letter_cycles(crosswalk, date.today())
    identity_queue, identity_audit = create_fda_identity_review_queue(crosswalk, letters)
    pdf_sources, pdf_audit = probe_fda_review_documents(
        identity_queue, offset=args.pdf_probe_offset, limit=args.pdf_probe_limit)
    audit["source_letter_archive_sha256"] = letter_audit["archive_sha256_by_url"]
    audit["source_registry_archive_sha256"] = registry_audit["source_archive_sha256"]
    dest = Path(args.output_dir)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "fda_crl_registry_identity_crosswalk.json").write_text(
        json.dumps(crosswalk, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (dest / "fda_crl_registry_identity_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (dest / "fda_repeat_letter_review_candidates.json").write_text(
        json.dumps(triage_cases, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (dest / "fda_repeat_letter_triage_audit.json").write_text(
        json.dumps(triage_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (dest / "fda_identity_review_queue.json").write_text(
        json.dumps(identity_queue, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (dest / "fda_identity_review_queue_audit.json").write_text(
        json.dumps(identity_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (dest / "fda_identity_review_official_pdf_checks.json").write_text(
        json.dumps(pdf_sources, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (dest / "fda_identity_review_official_pdf_checks_audit.json").write_text(
        json.dumps(pdf_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": audit["status"],
        "published_letter_records": audit["published_letter_records"],
        "approved_registry_source_application_records": audit["approved_registry_source_application_records"],
        "identity_link_status_counts": audit["identity_link_status_counts"],
        "model_eligible_records": audit["model_eligible_records"],
        "repeated_letter_application_groups": triage_audit["repeated_letter_application_groups"],
        "potential_same_day_type_duplicate_groups": triage_audit["potential_same_day_type_duplicate_groups"],
        "verified_review_cycle_outcomes": triage_audit["independently_verified_review_cycles"],
        "identity_review_queue_records": identity_audit["review_queue_records"],
        "identity_review_reason_counts": identity_audit["review_reason_counts"],
        "official_pdf_probe_counts": pdf_audit["document_fetch_status_counts"],
        "official_pdf_bytes_confirmed": pdf_audit["official_pdf_bytes_confirmed"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

"""Acquire a complete *published-letter* FDA action worklist (not a cohort).

The workflow fetches official openFDA source archives, cross-checks application
identities, flags non-binary regulatory document types, and probes each official
PDF in bounded batches. The archive is publication-selected and remains
ineligible for clinical prediction training.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
from urllib.request import Request, urlopen

from app.hop_openfda_snapshot import build_crl_snapshot
from app.hop_drugsfda_snapshot import stage_drugsfda_manifest
from app.hop_fda_application_crosswalk import crosswalk_public_fda_sources
from app.hop_fda_action_review import build_fda_action_review_worklist
from app.hop_fda_document_probe import probe_all_fda_review_documents


def fetch(url: str, max_bytes: int) -> bytes:
    if not url.startswith("https://"):
        raise ValueError("official FDA acquisition requires HTTPS")
    with urlopen(Request(
            url, headers={"User-Agent": "PDUFA-HOP-regulatory-source-audit/1.0"}),
            timeout=60) as response:
        blob = response.read(max_bytes + 1)
    if len(blob) > max_bytes:
        raise ValueError("official FDA source download is above safety limit")
    return blob


def output_json(directory: Path, filename: str, value: dict) -> None:
    (directory / filename).write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--pdf-batch-size", type=int, default=20)
    args = parser.parse_args()

    official_manifest = json.loads(fetch("https://api.fda.gov/download.json", 8_000_000))
    letters_meta = official_manifest["results"]["transparency"]["crl"]["partitions"]
    drugs_meta = official_manifest["results"]["drug"]["drugsfda"]["partitions"]
    letters, letters_audit = build_crl_snapshot(
        official_manifest,
        {p["file"]: fetch(p["file"], 12_000_000) for p in letters_meta},
        date.today(),
    )
    drugs, drugs_audit = stage_drugsfda_manifest(
        official_manifest,
        {p["file"]: fetch(p["file"], 22_000_000) for p in drugs_meta},
        date.today(),
    )
    crosswalk, crosswalk_audit = crosswalk_public_fda_sources(letters, drugs)
    cases, case_audit = build_fda_action_review_worklist(
        crosswalk, letters, date.today()
    )
    pdfs, pdf_audit = probe_all_fda_review_documents(
        cases, batch_size=args.pdf_batch_size
    )
    if (len(cases["records"]) != len(pdfs["records"])
            or case_audit["published_letter_records"] != crosswalk_audit["published_letter_records"]
            or case_audit["published_letter_records"] != letters_audit["published_letter_records"]
            or case_audit["independently_adjudicated_review_cycle_outcomes"] != 0
            or pdf_audit["model_eligible_records"] != 0):
        raise ValueError("FDA source evidence counts do not reconcile")
    case_audit["official_source_archive_sha256"] = {
        **letters_audit["archive_sha256_by_url"],
        **drugs_audit["source_archive_sha256"],
    }
    pdf_audit["source_letter_archive_sha256"] = letters_audit["archive_sha256_by_url"]

    dest = Path(args.output_dir)
    dest.mkdir(parents=True, exist_ok=True)
    output_json(dest, "fda_all_published_action_review_worklist.json", cases)
    output_json(dest, "fda_all_published_action_review_audit.json", case_audit)
    output_json(dest, "fda_all_published_action_pdf_checks.json", pdfs)
    output_json(dest, "fda_all_published_action_pdf_checks_audit.json", pdf_audit)
    print(json.dumps({
        "publication_only": True,
        "published_letter_records": case_audit["published_letter_records"],
        "letter_type_counts": case_audit["published_letter_type_counts"],
        "pdf_check_counts": pdf_audit["document_fetch_status_counts"],
        "effective_action_dates_verified":
            case_audit["effective_fda_action_dates_independently_verified"],
        "verified_review_cycle_outcomes":
            case_audit["independently_adjudicated_review_cycle_outcomes"],
        "model_eligible_records": case_audit["model_eligible_records"],
        "prediction_probability": case_audit["prediction_probability"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

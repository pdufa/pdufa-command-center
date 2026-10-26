#!/usr/bin/env python3
"""Validate each research-only MAIN Phase 3 output before GitHub artifact upload.

A successful scheduled workflow must have all expected source files, 741 exact
NCT IDs, 130 SEC issuer research pointers, 6669 gate checks and 4446 rights
review slots. SHA256 values detect altered/missing artifact bytes; they do not
authenticate external FDA, legal, scientific or commercial-rights facts.
No live Pipeline/GEM/FS/FA write is performed.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

EXPECTED_TRIALS = 741
EXPECTED_ISSUERS = 130
GATE_SLOTS = EXPECTED_TRIALS * 9
RIGHTS_SLOTS = EXPECTED_TRIALS * 6
MAX_FILE_BYTES = 30_000_000
NCT = re.compile(r"^NCT[0-9]{8}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
GITHUB_SHA = re.compile(r"^[a-f0-9]{40}$")
EXPECTED_FILES = (
    "main_phase3_registry.json",
    "main_phase3_qualification_ledger.json",
    "main_phase3_sponsor_rights_queue.json",
    "main_phase3_rights_gaps.json",
    "main_phase3_rights_casebook.json",
    "main_phase3_program_identity.json",
    "main_phase3_sec_rights_leads.json",
    "main_phase3_sec_primary_documents_pilot.json",
    "main_phase3_sec_trial_rights_join.json",
    "main_phase3_rights_review_worklist.json",
    "main_phase3_rights_review_worklist.csv",
    "main_phase3_rights_review_submissions_coverage.json",
    "main_phase3_qualification_scorecard.json",
    "main_phase3_qualification_summary.md",
)
JSON_FILES = tuple(x for x in EXPECTED_FILES if x.endswith(".json"))
MANIFEST_NAME = "main_phase3_run_integrity_manifest.json"


def no_duplicate_json_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key in saved source report")
        result[key] = value
    return result


def load_json(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"),
                          object_pairs_hook=no_duplicate_json_pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Malformed source report: {path.name}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Source report must be an object: {path.name}")
    return data


def trial_ids(data, key, label):
    rows = data.get(key)
    if not isinstance(rows, list) or len(rows) != EXPECTED_TRIALS:
        raise ValueError(f"Incomplete 741-NCT scope: {label}")
    ids = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"Malformed source row: {label}")
        nct = row.get("nct_id")
        if not isinstance(nct, str) or not NCT.fullmatch(nct) or nct in ids:
            raise ValueError(f"Duplicate/unknown NCT identity in {label}")
        ids.add(nct)
    return ids


def check_report_numbers(reports, csv_path, markdown_path):
    registry = reports["main_phase3_registry.json"]
    ledger = reports["main_phase3_qualification_ledger.json"]
    casebook = reports["main_phase3_rights_casebook.json"]
    program = reports["main_phase3_program_identity.json"]
    sec = reports["main_phase3_sec_rights_leads.json"]
    pilot = reports["main_phase3_sec_primary_documents_pilot.json"]
    joined = reports["main_phase3_sec_trial_rights_join.json"]
    worklist = reports["main_phase3_rights_review_worklist.json"]
    reviewed = reports["main_phase3_rights_review_submissions_coverage.json"]
    score = reports["main_phase3_qualification_scorecard.json"]

    if (registry.get("report_type") != "MAIN_ORIGINAL_PHASE3_FULL_CENSUS_RESEARCH_ONLY"
        or registry.get("census_total") != EXPECTED_TRIALS
        or registry.get("source_identity_verified") != EXPECTED_TRIALS
        or registry.get("source_errors") != []
        or ledger.get("report_type") != "MAIN_PHASE3_QUALIFICATION_EVIDENCE_LEDGER_RESEARCH_ONLY"
        or ledger.get("total") != EXPECTED_TRIALS
        or casebook.get("report_type") != "MAIN_PHASE3_RIGHTS_CASEBOOK_RESEARCH_ONLY"
        or casebook.get("total_trials") != EXPECTED_TRIALS
        or casebook.get("saved_issuer_pointers") != EXPECTED_ISSUERS
        or program.get("report_type") != "MAIN_PHASE3_ORIGINAL_DRUG_INDICATION_TERMS_RESEARCH_ONLY"
        or program.get("total_trials") != EXPECTED_TRIALS
        or sec.get("report_type") != "MAIN_PHASE3_SEC_RIGHTS_FILING_LEADS_RESEARCH_ONLY"
        or sec.get("total_issuers") != EXPECTED_ISSUERS or sec.get("total_trials") != EXPECTED_TRIALS
        or pilot.get("report_type") != "MAIN_PHASE3_SEC_PRIMARY_RIGHTS_DOCUMENT_PILOT_RESEARCH_ONLY"
        or pilot.get("total_issuers") != EXPECTED_ISSUERS or pilot.get("total_trials") != EXPECTED_TRIALS
        or joined.get("report_type") != "MAIN_PHASE3_TRIAL_DRUG_SEC_RIGHTS_JOIN_RESEARCH_ONLY"
        or joined.get("total_issuers") != EXPECTED_ISSUERS or joined.get("total_trials") != EXPECTED_TRIALS
        or worklist.get("report_type") != "MAIN_PHASE3_COMMERCIAL_RIGHTS_REVIEW_WORKLIST_RESEARCH_ONLY"
        or worklist.get("total_trials") != EXPECTED_TRIALS
        or worklist.get("total_issuer_research_pointers") != EXPECTED_ISSUERS
        or reviewed.get("report_type") != "MAIN_PHASE3_RIGHTS_REVIEW_SUBMISSIONS_COVERAGE_RESEARCH_ONLY"
        or reviewed.get("trial_denominator") != EXPECTED_TRIALS
        or reviewed.get("checklist_slot_denominator") != RIGHTS_SLOTS
        or score.get("report_type") != "MAIN_PHASE3_QUALIFICATION_PROGRESS_SCORECARD_RESEARCH_ONLY"
        or score.get("historical_trial_count") != EXPECTED_TRIALS
        or score.get("issuer_research_pointer_count") != EXPECTED_ISSUERS
        or score.get("gate_checks_denominator") != GATE_SLOTS
        or score.get("rights_review_checklist_slots") != RIGHTS_SLOTS):
        raise ValueError("One or more saved reports have an invalid source identity or denominator")

    sources = (
        (registry, "original_source_records", "registry"),
        (ledger, "records", "qualification ledger"),
        (casebook, "items", "rights casebook"),
        (program, "items", "drug program"),
        (sec, "trials", "SEC pointers"),
        (joined, "items", "SEC trial join"),
        (worklist, "items", "rights worklist"),
        (reviewed, "items", "review submissions"),
    )
    canonical = trial_ids(registry, "original_source_records", "registry")
    for report, key, label in sources[1:]:
        if trial_ids(report, key, label) != canonical:
            raise ValueError(f"NCT set differs from verified original registry in {label}")

    if (not isinstance(sec.get("issuers"), list) or len(sec["issuers"]) != EXPECTED_ISSUERS
        or not isinstance(pilot.get("issuers"), list)
        or len(pilot["issuers"]) != EXPECTED_ISSUERS):
        raise ValueError("SEC issuer source lists are incomplete")

    if (score.get("gate_checks_pass") != EXPECTED_TRIALS
        or score.get("gate_checks_review") != GATE_SLOTS - EXPECTED_TRIALS
        or score.get("gate_checks_fail") != 0
        or score.get("rights_slots_with_submissions") != reviewed.get("distinct_review_slots_with_submissions")
        or score.get("rights_slots_without_submissions") != reviewed.get("review_slots_without_submissions")
        or score.get("sec_issuer_indexes_fetched") != sec.get("issuer_metadata_fetched")
        or score.get("sec_primary_documents_attempted") != pilot.get("documents_attempted")
        or score.get("sec_primary_documents_fetched") != pilot.get("documents_retrieved")
        or score.get("independently_verified_current_rights_trials") != 0
        or reviewed.get("independently_verified_commercial_rights") != 0
        or casebook.get("rights_verified_trials") != 0
        or pilot.get("independently_verified_current_rights") != 0
        or program.get("independently_verified_commercial_rights") != 0
        or joined.get("verified_current_commercial_rights") != 0
        or worklist.get("independently_verified_current_rights") != 0):
        raise ValueError("Published source coverage does not reconcile or improperly asserts rights")

    if (type(score.get("rights_slots_with_submissions")) is not int
        or type(score.get("rights_slots_without_submissions")) is not int
        or score["rights_slots_with_submissions"] < 0
        or score["rights_slots_without_submissions"] < 0
        or score["rights_slots_with_submissions"] + score["rights_slots_without_submissions"] != RIGHTS_SLOTS):
        raise ValueError("4,446 rights review slot totals do not reconcile")

    for report in (registry, ledger, casebook, program, sec, pilot, joined,
                   worklist, reviewed):
        if report.get("qualified_pipeline_total") is not None:
            raise ValueError("Historical research source cannot claim a qualified Pipeline count")
    if score.get("qualified_trial_count") is not None or score.get("qualifying_pipeline_count") is not None:
        raise ValueError("Qualifying Pipeline count must remain unknown in this research report")

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Malformed rights review CSV header")
        if not {"nct_id", "review_position", "qualified_pipeline", "commercial_rights_verified"}.issubset(reader.fieldnames):
            raise ValueError("Rights review CSV lacks required audit columns")
        lines = list(reader)
    if len(lines) != EXPECTED_TRIALS:
        raise ValueError("Rights CSV must contain exactly 741 trial rows")
    seen = set()
    for i, row in enumerate(lines, start=1):
        nct = row.get("nct_id")
        if (not isinstance(nct, str) or nct not in canonical or nct in seen
            or row.get("review_position") != str(i)
            or row.get("qualified_pipeline") != ""
            or row.get("commercial_rights_verified") != "False"):
            raise ValueError("Rights CSV duplicate, unknown, misordered or improperly promoted trial")
        seen.add(nct)

    summary = markdown_path.read_text(encoding="utf-8")
    if (len(summary) > 500_000
        or "**Qualified Pipeline total:** **UNKNOWN** (not zero)" not in summary
        or "<details><summary>All nine mandatory gates" not in summary
        or f"{score['gate_checks_pass']}/{GATE_SLOTS}" not in summary):
        raise ValueError("Human-readable scorecard missing nonqualification or complete denominators")

    return {
        "historical_trial_count": EXPECTED_TRIALS,
        "issuer_research_pointer_count": EXPECTED_ISSUERS,
        "verified_registry_identity_checks": EXPECTED_TRIALS,
        "mandatory_gate_checks": GATE_SLOTS,
        "unresolved_mandatory_gate_checks": GATE_SLOTS - EXPECTED_TRIALS,
        "commercial_rights_review_slots": RIGHTS_SLOTS,
        "rights_slots_with_submissions": score["rights_slots_with_submissions"],
        "sec_issuer_indexes_fetched": score["sec_issuer_indexes_fetched"],
        "sec_primary_documents_attempted": score["sec_primary_documents_attempted"],
        "sec_primary_documents_fetched": score["sec_primary_documents_fetched"],
        "independently_verified_commercial_rights": 0,
        "qualified_pipeline_total": None,
    }


def check_file(directory, filename):
    path = directory / filename
    if path.is_symlink() or not path.is_file() or path.parent.resolve() != directory.resolve():
        raise ValueError(f"Required source artifact is missing, unsafe or not a regular file: {filename}")
    length = path.stat().st_size
    if not 0 < length <= MAX_FILE_BYTES:
        raise ValueError(f"Source artifact missing, empty or oversized: {filename}")
    content = path.read_bytes()
    return {"name": filename, "bytes": length,
            "sha256": hashlib.sha256(content).hexdigest()}


def make_manifest(directory, event, pacific_day, run_id, commit):
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError("Missing GitHub runner source directory")
    if event not in ("schedule", "workflow_dispatch", "pull_request"):
        raise ValueError("Only original authorized read-only source runs are accepted")
    if not isinstance(pacific_day, str) or not re.fullmatch(r"\d{4}-\d\d-\d\d", pacific_day):
        raise ValueError("Missing or invalid Pacific source day")
    date.fromisoformat(pacific_day)
    if not isinstance(run_id, str) or not run_id.isdigit() or int(run_id) < 1:
        raise ValueError("Missing source run ID")
    if not isinstance(commit, str) or not GITHUB_SHA.fullmatch(commit):
        raise ValueError("Missing exact source commit")
    files = [check_file(directory, name) for name in EXPECTED_FILES]
    reports = {name: load_json(directory / name) for name in JSON_FILES}
    numbers = check_report_numbers(
        reports,
        directory / "main_phase3_rights_review_worklist.csv",
        directory / "main_phase3_qualification_summary.md",
    )
    return {
        "schema_version": 1,
        "report_type": "MAIN_PHASE3_RESEARCH_ARTIFACT_INTEGRITY_MANIFEST",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "github_run_id": int(run_id),
        "github_sha": commit,
        "github_event": event,
        "pacific_research_date": pacific_day,
        "artifact_name": "main-phase3-evidence-qualification-research-only",
        "verified_file_count": len(files),
        "file_count_expected": len(EXPECTED_FILES),
        "files": files,
        "reconciled_scope": numbers,
        "verification_meaning": (
            "Locally verifies output presence, integrity and expected research-only "
            "NCT/issuer denominators before upload. No independent external source "
            "authentication, FDA result, legal rights determination, Pipeline/GEM "
            "qualification or trade authorization."
        ),
    }


def verify_manifest(directory, manifest):
    if (not isinstance(manifest, dict)
        or manifest.get("report_type") != "MAIN_PHASE3_RESEARCH_ARTIFACT_INTEGRITY_MANIFEST"
        or manifest.get("verified_file_count") != len(EXPECTED_FILES)
        or manifest.get("file_count_expected") != len(EXPECTED_FILES)
        or not isinstance(manifest.get("files"), list)
        or [x.get("name") for x in manifest["files"] if isinstance(x, dict)] != list(EXPECTED_FILES)):
        raise ValueError("Incomplete or forged nightly source artifact manifest")
    for expected in manifest["files"]:
        if not isinstance(expected, dict) or check_file(Path(directory), expected["name"]) != expected:
            raise ValueError("Source file changed or deleted since manifest generation")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runner_temp", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--event-name", default=os.environ.get("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--pacific-date", default=os.environ.get("PACIFIC_RESEARCH_DATE", ""))
    parser.add_argument("--github-run-id", default=os.environ.get("GITHUB_RUN_ID", ""))
    parser.add_argument("--github-sha", default=os.environ.get("GITHUB_SHA", ""))
    args = parser.parse_args()
    output = args.output
    if output.resolve() != (args.runner_temp.resolve() / MANIFEST_NAME):
        sys.exit("Integrity manifest must be in source artifact directory under its fixed name")
    manifest = make_manifest(args.runner_temp, args.event_name, args.pacific_date,
                             args.github_run_id, args.github_sha)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    verify_manifest(args.runner_temp, manifest)
    print(
        f"MAIN research artifact integrity: {manifest['verified_file_count']}/"
        f"{manifest['file_count_expected']} files source-hashed and reconciled; "
        f"{manifest['reconciled_scope']['historical_trial_count']}/741 NCTs; "
        f"{manifest['reconciled_scope']['issuer_research_pointer_count']}/130 issuer pointers; "
        "qualified Pipeline UNKNOWN"
    )


if __name__ == "__main__":
    main()

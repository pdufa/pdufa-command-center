#!/usr/bin/env python3
"""Reconcile the FDA source snapshots without certifying a PDUFA denominator.

Run against archived Drugs@FDA and openFDA CRL exports in outcome quarantine.
Only the aggregate report is written outside that directory.
"""

import argparse
import csv
from collections import Counter
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import zipfile

BEGIN = date(2026, 1, 1)
END = date(2026, 11, 18)


def read_drugsfda(path):
    with zipfile.ZipFile(path) as archive:
        members = [member for member in archive.infolist() if not member.is_dir()]
        if len(members) != 1 or not members[0].filename.endswith(".json"):
            raise ValueError("Expected one JSON member in the Drugs@FDA archive")
        if members[0].file_size > 300_000_000:
            raise ValueError("Drugs@FDA archive exceeds the staging size limit")
        return json.loads(archive.read(members[0]))


def approval_candidates(applications):
    inventory = {}
    source_classes = Counter()
    duplicate_keys = 0
    for application in applications:
        number = application["application_number"]
        if not number.startswith(("NDA", "BLA")):
            continue
        for submission in application.get("submissions", []):
            status_date = submission.get("submission_status_date")
            if not status_date:
                continue
            action_date = datetime.strptime(status_date, "%Y%m%d").date()
            if not BEGIN <= action_date <= END:
                continue
            kind = submission.get("submission_type")
            category = submission.get("submission_class_code")
            status = submission.get("submission_status")
            source_classes[(number[:3], status, kind, category)] += 1
            if status != "AP" or (
                kind != "ORIG" and (kind, category) != ("SUPPL", "EFFICACY")
            ):
                continue
            submission_number = submission["submission_number"]
            key = (number, kind, submission_number, action_date.isoformat())
            if key in inventory:
                duplicate_keys += 1
                continue
            brands = sorted(
                {p["brand_name"] for p in application.get("products", []) if p.get("brand_name")}
            )
            documents = [
                d["application_docs_url"]
                for d in submission.get("application_docs", [])
                if d.get("application_docs_url")
                and d.get("application_docs_type") in ("Letter", "Approval Letter")
            ]
            inventory[key] = {
                "application_number": number,
                "submission_type": kind,
                "submission_number": submission_number,
                "submission_class": category,
                "actual_action_date": action_date.isoformat(),
                "actual_outcome": "APPROVE",
                "sponsor_as_published": application.get("sponsor_name"),
                "drugs_as_published": brands,
                "fda_source_urls": documents or [
                    "https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm"
                    f"?event=overview.process&ApplNo={number[3:]}"
                ],
                "indication": None,
                "pdufa_goal_date": None,
                "eligibility_status": "FDA_ACTION_CANDIDATE",
            }
    return list(inventory.values()), source_classes, duplicate_keys


def letter_candidates(payload):
    records = payload["results"]
    expected = payload["meta"]["results"]["total"]
    if payload["meta"]["results"]["skip"] != 0 or expected != len(records):
        raise ValueError("CRL query results must include all pages")
    inventory = {}
    unresolved = []
    duplicate_keys = 0
    for letter in records:
        action_date = datetime.strptime(letter["letter_date"], "%m/%d/%Y").date()
        if not BEGIN <= action_date <= END:
            raise ValueError("Letter date outside the expected backtest window")
        filename = letter.get("file_name")
        applications = letter.get("application_number")
        if letter.get("letter_type") != "COMPLETE RESPONSE" or not applications or (
            not filename or not filename.endswith(".pdf")
        ):
            unresolved.append(
                {
                    "source_filename": filename,
                    "actual_action_date": action_date.isoformat(),
                    "sponsor_as_published": letter.get("company_name"),
                    "reason": "Missing published letter, application ID or structured letter type",
                }
            )
            continue
        # Multiple printed application strings can describe one FDA letter.
        # Keep the letter as one record until its application cycles are read.
        if filename in inventory:
            duplicate_keys += 1
            continue
        inventory[filename] = {
            "application_numbers_as_published": applications,
            "actual_action_date": action_date.isoformat(),
            "actual_outcome": "CRL",
            "sponsor_as_published": letter.get("company_name"),
            "fda_source_url": f"https://download.open.fda.gov/crl/{filename}",
            "eligibility_status": "FDA_LETTER_CANDIDATE",
        }
    return list(inventory.values()), unresolved, duplicate_keys


def audit(drugs_path, crl_path, timing_path, quarantine, target):
    drugs = read_drugsfda(drugs_path)
    approvals, source_classes, approval_duplicates = approval_candidates(drugs["results"])
    crls = json.loads(crl_path.read_text())
    letters, unresolved, letter_duplicates = letter_candidates(crls)
    with timing_path.open(newline="", encoding="utf-8-sig") as stream:
        timing_rows = list(csv.DictReader(stream))
    if not timing_rows or not {"goal_date", "fda_action_date", "ticker", "drug"} <= timing_rows[0].keys():
        raise ValueError("Expected versioned FDA timing discovery CSV")
    timing_ids = {
        (row["ticker"], row["drug"], row["fda_action_date"], row["goal_date"])
        for row in timing_rows
        if BEGIN <= date.fromisoformat(row["fda_action_date"]) <= END
    }
    approval_counts = Counter((a["application_number"][:3], a["submission_type"]) for a in approvals)
    quarantine.mkdir(mode=0o700, parents=True, exist_ok=True)
    ledger = quarantine / "fda-action-candidates.private.json"
    descriptor = os.open(ledger, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(
            {"approval_candidates": approvals, "crl_letter_candidates": letters, "incomplete_letters": unresolved},
            stream,
            indent=2,
        )
        stream.write("\n")
    return {
        "window_start": BEGIN.isoformat(),
        "window_end": END.isoformat(),
        "requested_cases": target,
        "case_count_verified": False,
        "eligible_denominator": None,
        "drugsfda_approval_candidates": len(approvals),
        "drugsfda_candidate_breakdown": {
            f"{app} {kind}": count for (app, kind), count in sorted(approval_counts.items())
        },
        "drugsfda_duplicate_candidate_keys": approval_duplicates,
        "drugsfda_all_nda_bla_submission_status_rows": sum(source_classes.values()),
        "openfda_crl_export_date": crls["meta"]["last_updated"],
        "openfda_crl_query_rows": len(crls["results"]),
        "openfda_crl_letter_candidates": len(letters),
        "openfda_crl_incomplete_rows": len(unresolved),
        "openfda_crl_duplicate_filenames": letter_duplicates,
        "timing_discovery_distinct_rows": len(timing_ids),
        "snapshot_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (drugs_path, crl_path, timing_path)
        },
        "limitations": [
            "Drugs@FDA is an approved-product registry. Its submission codes do not establish PDUFA goal dates, indications or review cycles.",
            "Original approvals and efficacy-class supplements are candidate screening classes only. Labeling supplements require separate review when tied to clinical data and a PDUFA goal.",
            "The Drugs@FDA export omits some CBER actions and may lag newly published FDA action letters.",
            "openFDA letter keys are not review-cycle keys and the publication index has unresolved entries.",
            "The timing sample is a discovery subset. Its goal dates and FDA actions require checks against the linked sources.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drugsfda", required=True, type=Path)
    parser.add_argument("--crls", required=True, type=Path)
    parser.add_argument("--timing", required=True, type=Path)
    parser.add_argument("--quarantine", required=True, type=Path)
    parser.add_argument("--target", type=int, default=196)
    args = parser.parse_args()
    report = audit(args.drugsfda, args.crls, args.timing, args.quarantine, args.target)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

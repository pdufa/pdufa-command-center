#!/usr/bin/env python3
"""Generate a read-only Level 2 evidence-gap queue for the saved FOCUS cohort.

The saved FOCUS source contains research URL leads, NOT independently
adjudicated mechanism hypotheses. This script never opens those URLs,
assigns scientific scores, guesses trial phases, changes enrollment,
populates approval predictions, or writes into the Git repository.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit

from level2_scientific_hypothesis_intake import prepare_hypothesis_review

ROOT = Path(__file__).resolve().parents[1]
FOCUS = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
REPORTS = Path.home() / "PDUFA-Agent-Reports"
MAX_FOCUS = 2000
NCT = re.compile(r"NCT[0-9]{8}\Z")
# These are source *leads*, not retrieved evidence receipts.
URL_LEAD_FIELDS = ("resultsUrl", "regulatoryUrl")


def _valid_lead(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("https://"):
        return False
    if any(c.isspace() for c in value):
        return False
    try:
        parsed = urlsplit(value)
        return bool(
            parsed.scheme == "https" and parsed.hostname
            and "." in parsed.hostname and not parsed.username
            and not parsed.password and not parsed.fragment
            and parsed.port in (None, 443)
        )
    except ValueError:
        return False


def build_review_queue(snapshot: dict) -> dict:
    if not isinstance(snapshot, dict) or snapshot.get("schemaVersion") != 1:
        raise ValueError("Invalid FOCUS snapshot schema")
    cutoff = snapshot.get("asOf")
    if not isinstance(cutoff, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", cutoff):
        raise ValueError("FOCUS snapshot date missing")
    try:
        if date.fromisoformat(cutoff).isoformat() != cutoff:
            raise ValueError("Invalid FOCUS as-of date")
    except ValueError as exc:
        raise ValueError("Invalid FOCUS as-of date") from exc
    rows = snapshot.get("records")
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_FOCUS:
        raise ValueError("Unexpected FOCUS record count")
    seen = set()
    entries = []
    for raw in rows:
        if not isinstance(raw, dict):
            raise ValueError("Invalid FOCUS record")
        nct = raw.get("nct")
        if not isinstance(nct, str) or not NCT.fullmatch(nct):
            raise ValueError("FOCUS trial identity is invalid")
        if nct in seen:
            raise ValueError("Duplicate FOCUS trial identity")
        seen.add(nct)
        ticker = raw.get("ticker")
        if not isinstance(ticker, str) or not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,11}", ticker):
            raise ValueError("Ticker is not a valid snapshot identifier")
        company = raw.get("company")
        if not isinstance(company, str) or not 1 <= len(company.strip()) <= 200:
            raise ValueError("Company name missing from snapshot")
        lead_items = []
        for key in URL_LEAD_FIELDS:
            value = raw.get(key)
            if value is None or value == "":
                continue
            if not _valid_lead(value):
                raise ValueError("Invalid saved source lead for " + nct)
            lead_items.append({
                "role": key,
                "url": value,
                "status": "UNOPENED_SNAPSHOT_SOURCE_LEAD_NOT_VERIFIED",
            })

        # No scientific hypothesis is synthesized from ticker, trial title,
        # sponsor release link, or regulatory marketing material. The intake
        # must show what has not been researched or independently reviewed.
        review = prepare_hypothesis_review(
            {"nct": nct, "sources": []},
            as_of=cutoff,
        )
        if review["assessment_complete"] or review["scientifically_verified"]:
            raise ValueError("Unsafe scientific readiness promotion")
        entries.append({
            "nct": nct,
            "ticker": ticker,
            "company": company,
            "source_leads": lead_items,
            "hypothesis_review": review,
            "status": "SOURCE_COLLECTION_AND_HYPOTHESIS_REVIEW_REQUIRED",
            "phase_verified_by_this_queue": False,
            "approval_probability": None,
        })

    return {
        "schema_version": 1,
        "workflow": "LEVEL_2_FOCUS_RESEARCH_GAPS",
        "snapshot_as_of": cutoff,
        "trial_count": len(entries),
        "level2_assessments_completed": 0,
        "level2_assessments_in_review": 0,
        "outcome_predictions_generated": 0,
        "readiness": "SOURCE_COLLECTION_REQUIRED",
        "source_leads_are_unverified": True,
        "current_live_focus_membership_confirmed": False,
        "original_source_fetched": False,
        "repository_modified": False,
        "production_modified": False,
        "records": entries,
    }


def main() -> int:
    try:
        audit = subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts/audit_raas_retirement.py"), "--check"],
            cwd=ROOT, capture_output=True, text=True, errors="replace", timeout=240,
        )
        if audit.returncode != 0:
            print("STOP: Retired-systems safety audit failed")
            return 2
        if FOCUS.is_symlink() or not FOCUS.is_file() or not FOCUS.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError("Trusted FOCUS snapshot file missing or unsafe")
        raw_bytes = FOCUS.read_bytes()
        snapshot = json.loads(raw_bytes.decode("utf-8"))
        report = build_review_queue(snapshot)
        report["snapshot_sha256"] = hashlib.sha256(raw_bytes).hexdigest()
        report["built_at_utc"] = datetime.now(timezone.utc).isoformat()
        REPORTS.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = REPORTS / f"level2-focus-evidence-queue-{stamp}.json"
        with output.open("x", encoding="utf-8", newline="\n") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print("PASS: Mandatory PDUFA retirement audit")
        print("PASS: Saved FOCUS entries evaluated:", report["trial_count"])
        print("Level 2 scientifically verified:", report["level2_assessments_completed"])
        print("FDA predictions generated:", report["outcome_predictions_generated"])
        print("Saved cohort as of:", report["snapshot_as_of"])
        print("Review-only evidence-gap report:", output)
        print("No new source retrieval or scoring; live FOCUS membership not checked")
        return 0
    except (OSError, UnicodeError, ValueError, subprocess.TimeoutExpired) as exc:
        print("STOP: FOCUS Level 2 snapshot processing failed:", type(exc).__name__, str(exc)[:120])
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

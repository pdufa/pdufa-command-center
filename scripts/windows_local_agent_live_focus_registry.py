#!/usr/bin/env python3
"""Capture live ClinicalTrials.gov records for saved FOCUS NCTs, locally only.

Source-only retrieval: never adjudicates mechanisms, clinical efficacy, FDA
outcomes, or trial-level readiness. Reuses the repository's bounded primary
registry fetcher. Never sends saved records to GitHub, changes the roster,
or writes into the repository. Default is at most five network requests.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta, date
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

from fetch_focus_registry_evidence import retrieve

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
REPORTS = Path.home() / "PDUFA-Agent-Reports"
CAPTURES = REPORTS / "level2-live-registry-captures"
NCT = re.compile(r"NCT[0-9]{8}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
TTL = timedelta(hours=24)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def parse_stamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Timestamp absent")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Timestamp without timezone")
    return dt.astimezone(timezone.utc)


def verified_roster(snapshot: object) -> list[str]:
    if not isinstance(snapshot, dict) or snapshot.get("schemaVersion") != 1:
        raise ValueError("FOCUS schema not recognized")
    stamp = snapshot.get("asOf")
    if not isinstance(stamp, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", stamp):
        raise ValueError("FOCUS as-of date missing")
    if date.fromisoformat(stamp).isoformat() != stamp:
        raise ValueError("FOCUS as-of date invalid")
    rows = snapshot.get("records")
    if not isinstance(rows, list) or len(rows) != 29:
        raise ValueError("This bounded capture expects the saved 29-trial FOCUS roster")
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid FOCUS entry")
        nct = row.get("nct")
        if not isinstance(nct, str) or not NCT.fullmatch(nct) or nct in seen:
            raise ValueError("FOCUS NCT missing, duplicated or invalid")
        seen.add(nct)
    return [row["nct"] for row in rows]


def make_envelope(nct: str, cohort_digest: str, record: dict, metadata: dict) -> dict:
    if not isinstance(record, dict) or not isinstance(metadata, dict):
        raise ValueError("Registry retrieval returned a nonobject")
    if record.get("protocolSection", {}).get("identificationModule", {}).get("nctId") != nct:
        raise ValueError("Registry response has an unrelated NCT")
    if (metadata.get("nct") != nct
            or metadata.get("source_url") != "https://clinicaltrials.gov/api/v2/studies/" + nct
            or metadata.get("source_type") != "PRIMARY_REGISTRY"
            or metadata.get("scientific_adjudication") != "NOT_ADJUDICATED"
            or metadata.get("fda_probability") is not None
            or not isinstance(metadata.get("sha256"), str)
            or not DIGEST.fullmatch(metadata["sha256"])):
        raise ValueError("Registry source metadata does not meet safety contract")
    when = parse_stamp(metadata.get("retrieved_at_utc"))
    return {
        "schema_version": 1,
        "nct": nct,
        "cohort_sha256": cohort_digest,
        "retrieved_at_utc": when.isoformat(),
        "source_url": metadata["source_url"],
        "source_type": "PRIMARY_REGISTRY",
        "raw_source_sha256_from_fetch": metadata["sha256"],
        "normalized_record_sha256": hashlib.sha256(canonical_bytes(record)).hexdigest(),
        "source_status": "PRIMARY_REGISTRY_RETRIEVED_NOT_INDEPENDENTLY_REVIEWED",
        "scientific_assessment_completed": False,
        "fda_prediction": None,
        "approval_probability": None,
        "record": record,
    }


def valid_cache(path: Path, nct: str, cohort_digest: str, now: datetime) -> bool:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 13_000_000:
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return False
        when = parse_stamp(data.get("retrieved_at_utc"))
        age = now - when
        return (
            data.get("schema_version") == 1
            and data.get("nct") == nct
            and data.get("cohort_sha256") == cohort_digest
            and data.get("source_url") == "https://clinicaltrials.gov/api/v2/studies/" + nct
            and data.get("source_type") == "PRIMARY_REGISTRY"
            and data.get("source_status") == "PRIMARY_REGISTRY_RETRIEVED_NOT_INDEPENDENTLY_REVIEWED"
            and data.get("scientific_assessment_completed") is False
            and data.get("fda_prediction") is None
            and data.get("approval_probability") is None
            and isinstance(data.get("raw_source_sha256_from_fetch"), str)
            and DIGEST.fullmatch(data["raw_source_sha256_from_fetch"]) is not None
            and isinstance(data.get("normalized_record_sha256"), str)
            and DIGEST.fullmatch(data["normalized_record_sha256"]) is not None
            and isinstance(data.get("record"), dict)
            and data["record"].get("protocolSection", {}).get("identificationModule", {}).get("nctId") == nct
            and hashlib.sha256(canonical_bytes(data["record"])).hexdigest() == data["normalized_record_sha256"]
            and timedelta(0) <= age < TTL
        )
    except (ValueError, OSError, TypeError, OverflowError, KeyError, AttributeError):
        return False


def atomic_json(path: Path, value: dict) -> None:
    if path.is_symlink():
        raise ValueError("Refusing to overwrite a symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent,
            prefix="capture-", suffix=".tmp", delete=False,
        ) as handle:
            temp_name = handle.name
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if temp_name is not None and os.path.exists(temp_name):
            os.unlink(temp_name)


def capture_batch(ncts: list[str], cohort_digest: str, directory: Path, limit: int,
                  fetcher=retrieve, now: datetime | None = None) -> dict:
    """Bounded network capture; fetcher injection enables purely offline tests."""
    if (not isinstance(limit, int) or not 1 <= limit <= 29
            or len(ncts) != 29 or len(set(ncts)) != 29
            or any(not isinstance(n, str) or not NCT.fullmatch(n) for n in ncts)
            or not isinstance(cohort_digest, str) or not DIGEST.fullmatch(cohort_digest)):
        raise ValueError("Unsafe capture request")
    if (directory.is_symlink() or directory.parent.is_symlink()
            or directory.resolve().is_relative_to(ROOT.resolve())):
        raise ValueError("Unsafe output directory")
    directory.mkdir(parents=True, exist_ok=True)
    fixed_clock = now is not None
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Capture date must be timezone-aware")
    fresh = [nct for nct in ncts if valid_cache(directory / f"{nct}.json", nct, cohort_digest, now)]
    remaining = [nct for nct in ncts if nct not in set(fresh)]
    attempt = remaining[:limit]
    failures = 0
    completed = 0
    for index, nct in enumerate(attempt):
        try:
            record, metadata = fetcher(nct, timeout=20)
            envelope = make_envelope(nct, cohort_digest, record, metadata)
            fetched_time = parse_stamp(envelope["retrieved_at_utc"])
            # The live response necessarily arrives *after* the batch begins.
            validation_clock = now if fixed_clock else datetime.now(timezone.utc)
            if not timedelta(0) <= validation_clock - fetched_time < TTL:
                raise ValueError("Source capture timestamp is not current")
            atomic_json(directory / f"{nct}.json", envelope)
            if not valid_cache(directory / f"{nct}.json", nct, cohort_digest, validation_clock):
                raise ValueError("Saved source capture did not pass checksum validation")
            completed += 1
        except (OSError, ValueError, TimeoutError, TypeError, KeyError, json.JSONDecodeError) as exc:
            failures += 1
            print("Registry capture failed for a saved NCT:", nct, type(exc).__name__)
        if index + 1 < len(attempt) and fetcher is retrieve:
            time.sleep(1)
    # Compare against the time AFTER the last download, not the batch start.
    # Newly fetched records naturally have timestamps later than the start.
    final_clock = now if fixed_clock else datetime.now(timezone.utc)
    fresh_after = sum(
        valid_cache(directory / f"{n}.json", n, cohort_digest, final_clock)
        for n in ncts
    )
    return {
        "schema_version": 1,
        "workflow": "LEVEL2_FOCUS_LIVE_REGISTRY_CAPTURE",
        "saved_roster_size": len(ncts),
        "fresh_exact_registry_captures": fresh_after,
        "network_attempts_this_run": len(attempt),
        "newly_captured_this_run": completed,
        "failed_attempts_this_run": failures,
        "remaining_without_fresh_capture": len(ncts) - fresh_after,
        "source_state": "ALL_FRESH_SOURCE_ONLY" if fresh_after == len(ncts) else "PARTIAL_SOURCE_CAPTURE",
        "source_adjudication": "NOT_COMPLETED",
        "clinical_prediction": None,
        "fda_approval_probability": None,
        "scientific_levels_completed": 0,
        "production_modified": False,
        "repository_modified": False,
        "roster_live_membership_verified": False,
        "cohort_sha256": cohort_digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=5, choices=range(1, 30),
                        metavar="1..29", help="Max HTTPS requests this run; default 5")
    parser.add_argument("--all", action="store_true", help="Attempt all remaining NCTs (up to 29)")
    args = parser.parse_args()
    try:
        audit = subprocess.run(
            [sys.executable, "-B", "scripts/audit_raas_retirement.py", "--check"],
            cwd=ROOT, capture_output=True, text=True, errors="replace", timeout=240,
        )
        if audit.returncode != 0:
            print("STOP: Historical RAAS retirement audit failed")
            return 2
        if (REPORTS.is_symlink() or REPORTS.resolve().is_relative_to(ROOT.resolve())):
            raise ValueError("Reports location must be outside the repository")
        if ROSTER.is_symlink() or not ROSTER.is_file() or not ROSTER.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError("Trusted saved FOCUS roster missing")
        raw = ROSTER.read_bytes()
        ncts = verified_roster(json.loads(raw.decode("utf-8")))
        digest = hashlib.sha256(raw).hexdigest()
        result = capture_batch(ncts, digest, CAPTURES, 29 if args.all else args.batch_size)
        REPORTS.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ%f")
        report = REPORTS / f"level2-registry-live-status-{stamp}.json"
        atomic_json(report, result)
        print("PASS: Historical retirement guard")
        print("Fresh exact-NCT registry captures:", result["fresh_exact_registry_captures"], "of", result["saved_roster_size"])
        print("Newly retrieved in this run:", result["newly_captured_this_run"])
        print("Failed retrieval attempts:", result["failed_attempts_this_run"])
        print("Source state:", result["source_state"])
        print("Local capture summary:", report)
        print("No scientific assessments, FDA probabilities, repository edits or production changes")
        return 0 if result["failed_attempts_this_run"] == 0 else 1
    except (OSError, ValueError, TypeError, TimeoutError, json.JSONDecodeError) as exc:
        print("STOP: Live registry capture unavailable:", type(exc).__name__)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""One bounded, fail-closed Levels 4-7 PDUFA research run for dated FOCUS NCTs.

Automates source acquisition, original-source inventory, phase-first assessment
readiness, level-7 model validation gap checks and status report generation.
NEVER replaces expert review, autonomous coding, FDA-approval prediction
validation, deployment approval, trading, or live FOCUS reconciliation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, date
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import level4_scientific_evidence as L4
import level5_contradictory_evidence as L5
import level6_cross_disciplinary_inventory as L6
import level7_source_readiness_inventory as L7
import pdufa_cumulative_level_assessments as SCORE

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "automation/focus-assessment-roster-snapshot-20261112.json"
MANIFEST = ROOT / "automation/scientific-level-completion-queue.json"
STOP = Path.home() / "PDUFA-Agent-Continuous" / "STOP"
REGISTRY = "https://clinicaltrials.gov/api/v2/studies/"
MAX_SOURCE_BYTES = 12_000_000


def fetch_registry(nct: str, *, timeout: int = 15, retries: int = 2) -> tuple[dict, dict, bytes]:
    if not L4.NCT.fullmatch(nct):
        raise ValueError("Invalid exact NCT identifier")
    url = REGISTRY + nct
    for attempt in range(retries + 1):
        try:
            request = Request(url, headers={
                "Accept": "application/json", "User-Agent": "PDUFA-ReviewableFocusSources/1.0"
            })
            with urlopen(request, timeout=timeout) as response:
                raw = response.read(MAX_SOURCE_BYTES + 1)
            if len(raw) > MAX_SOURCE_BYTES:
                raise ValueError("Source record exceeds maximum bytes")
            record = json.loads(raw)
            actual = record.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
            if actual != nct:
                raise ValueError("Downloaded source trial identity mismatch")
            stamp = datetime.now(timezone.utc).isoformat()
            return record, {
                "nct": nct, "source_url": url,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "retrieved_at_utc": stamp, "source_type": "PRIMARY_REGISTRY",
                "independent_review": "NOT_COMPLETED",
            }, raw
        except HTTPError as exc:
            if exc.code != 429 and not 500 <= exc.code <= 599:
                raise
            if attempt == retries:
                raise
        except (URLError, TimeoutError):
            if attempt == retries:
                raise
        time.sleep(min(2 ** attempt, 4))
    raise RuntimeError("Source retry budget exhausted")


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def source_posted_date(record: dict, retrieved_at: str) -> str | None:
    value = (record.get("protocolSection", {}).get("statusModule", {})
             .get("lastUpdatePostDateStruct", {}).get("date"))
    try:
        published = SCORE.utc_date(value)
        retrieved = SCORE.datetime_utc(retrieved_at)
        if published > retrieved.date():
            return None
        return published.isoformat()
    except (TypeError, ValueError):
        return None


def phase_evidence(nct: str, record: dict, provenance: dict) -> dict:
    """Registry phase, not an independently adjudicated FDA application status."""
    stage = L6.phase_from_registry(record)["phase_bucket"]
    published = source_posted_date(record, provenance["retrieved_at_utc"])
    result = {
        "nct": nct, "phase": stage, "application_stage": "UNKNOWN",
        "evidence": {},
    }
    if published is not None:
        result["phase_source"] = {
            "url": provenance["source_url"], "sha256": provenance["sha256"],
            "published_on": published, "retrieved_at_utc": provenance["retrieved_at_utc"],
        }
    else:
        result["phase"] = "UNKNOWN_OR_NOT_APPLICABLE"
    return result


def atomic_bytes(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("Unsafe output path")
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".pdufa-source-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def failure(level: int, nct: str, exc: BaseException) -> dict:
    return {
        "level": level, "nct": nct,
        "status": "SOURCE_OR_INVENTORY_BLOCKED",
        "blocker_class": type(exc).__name__,
        "scientific_stage_complete": False,
        "fda_prediction": None, "review_required": True,
    }


def restore_curated(result: dict, curated: dict | None, nct: str) -> dict:
    if curated is None:
        return result
    rows = curated.get("trials")
    if (curated.get("schema_version") != 1 or not isinstance(rows, list)):
        raise ValueError("Invalid curated evidence input")
    matched = [x for x in rows if x.get("nct") == nct]
    if len(matched) > 1:
        raise ValueError("Duplicate curated trial record")
    if not matched:
        return result
    x = matched[0]
    if x.get("phase") != result["phase"]:
        raise ValueError("Curated phase conflicts with exact registry phase")
    if not isinstance(x.get("evidence"), dict):
        raise ValueError("Missing curated criterion ratings")
    for forbidden in SCORE.FORBIDDEN_OUTCOME_INPUTS:
        if forbidden in x:
            raise ValueError("Known FDA outcome cannot enter blinded scoring")
    result = {**result, "evidence": x["evidence"]}
    if x.get("application_stage") is not None:
        result["application_stage"] = x["application_stage"]
    if x.get("application_source") is not None:
        result["application_source"] = x["application_source"]
    return result


def execute(*, roster: dict, manifest: dict, output: Path, fetcher=fetch_registry,
            curated: dict | None = None, stop_file: Path = STOP,
            now: datetime | None = None) -> dict:
    """Perform one serial scan, returning status without scientific signoff."""
    names = SCORE.validated_roster(roster)
    SCORE.validated_manifest(manifest)
    at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    as_of = at.date().isoformat()
    output = output.resolve()
    if stop_file.exists():
        raise RuntimeError("OWNER_STOP_ACTIVE")
    if curated is not None and curated.get("as_of") != as_of:
        raise ValueError("Curated source cutoff must equal scan UTC date")
    inventory = {level: [] for level in (4, 5, 6)}
    scores = []
    receipts = []
    observed_ncts = []
    fetched = 0
    for item in names:
        if stop_file.exists():
            raise RuntimeError("OWNER_STOP_ACTIVE")
        nct = item["nct"]
        observed_ncts.append(nct)
        try:
            record, provenance, raw = fetcher(nct)
            if (not isinstance(raw, bytes) or
                    hashlib.sha256(raw).hexdigest() != provenance["sha256"] or
                    json.loads(raw) != record or
                    provenance.get("nct") != nct or
                    provenance.get("source_url") != REGISTRY + nct):
                raise ValueError("Original source bytes, digest and trial ID inconsistent")
            if SCORE.datetime_utc(provenance.get("retrieved_at_utc")) > at:
                # No later source is allowed to sneak into an earlier audit cutoff.
                # Provide actual current time after retrieval in production.
                if now is not None:
                    raise ValueError("Synthetic scan cutoff predates source retrieval")
                at = datetime.now(timezone.utc)
                as_of = at.date().isoformat()
            atomic_bytes(output / "registry" / (nct + ".json"), raw)
            atomic_bytes(output / "registry" / (nct + ".receipt.json"),
                         (json.dumps(provenance, indent=2, sort_keys=True) + "\n").encode())
            fetched += 1
            receipts.append({"nct": nct, "sha256": provenance["sha256"],
                             "retrieved_at_utc": provenance["retrieved_at_utc"],
                             "status": "CURRENT_REGISTRY_SOURCE_RETRIEVED_NOT_SCIENCE_REVIEWED"})
            for level, fn in ((4, L4.summarize), (5, L5.collect), (6, L6.collect)):
                try:
                    inventory[level].append(fn(record, provenance))
                except (ValueError, TypeError, KeyError, RuntimeError) as exc:
                    inventory[level].append(failure(level, nct, exc))
            try:
                scores.append(restore_curated(phase_evidence(nct, record, provenance), curated, nct))
            except (ValueError, KeyError, TypeError) as exc:
                # Never discard the trial from coverage, and never score it on
                # an inconsistent or after-cutoff source.
                scores.append({"nct": nct, "phase": "UNKNOWN_OR_NOT_APPLICABLE",
                               "application_stage": "UNKNOWN", "evidence": {}})
                receipts[-1]["assessment_blocker"] = type(exc).__name__
        except (OSError, HTTPError, URLError, TimeoutError, ValueError,
                TypeError, KeyError, json.JSONDecodeError) as exc:
            for level in (4, 5, 6):
                inventory[level].append(failure(level, nct, exc))
            receipts.append({"nct": nct, "status": "SOURCE_BLOCKED",
                             "blocker_class": type(exc).__name__})
            # Missing source -> no phase proof and no numerical assessment.
    batches = {}
    for level in (4, 5, 6):
        report = {
            "level": level, "total": len(names),
            "retrieved": sum(x.get("status") not in
                             ("SOURCE_OR_INVENTORY_BLOCKED",) for x in inventory[level]),
            "reports": inventory[level], "scientific_level_complete": False,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "type": "PHASE_FIRST_REVIEWABLE_SOURCE_INVENTORY_NOT_PDUFA_SCORE",
        }
        batches[level] = report
        SCORE.safe_write(output / f"level{level}-evidence.json", report)
    if batches[6]["retrieved"] == 32 and fetched == 32:
        try:
            level7 = L7.inventory(
                batches[6], ncts=observed_ncts,
                freeze_as_of=roster["source"]["snapshot_date"],
                source_roster_blob_sha1=git_blob_sha(
                    checked_roster_file(roster).read_bytes()),
            )
        except (ValueError, KeyError, TypeError) as exc:
            level7 = {"level": 7, "status": "LEVEL7_SOURCE_AUDIT_BLOCKED",
                      "blocker_class": type(exc).__name__,
                      "scientific_level_complete": False, "predictive_model_trained": False}
    else:
        level7 = {
            "level": 7, "status": "BLOCKED_INCOMPLETE_LEVEL6_ORIGINAL_REGISTRY_RECEIPTS",
            "level6_original_registry_receipts": batches[6]["retrieved"],
            "total": 32, "scientific_level_complete": False,
            "predictive_model_trained": False, "approval_probabilities_generated": False,
        }
    SCORE.safe_write(output / "level7-model-readiness.json", level7)
    if curated is not None:
        # Match each curated entry to a live-source NCT, fail on unknown IDs.
        extras = {x.get("nct") for x in curated["trials"]} - set(observed_ncts)
        if extras:
            raise ValueError("Curated input contains NCT not in FOCUS")
    assessment = SCORE.build(manifest, roster, {
        "schema_version": 1, "as_of": as_of, "trials": scores,
    })
    SCORE.safe_write(output / "levels4-20-assessment-readiness.json", assessment)
    status = {
        "run_started_utc": at.isoformat(), "as_of": as_of,
        "automated_through": 7, "target_levels": [4, 5, 6, 7],
        "roster_count": len(names),
        "dated_roster_not_live_focus_reconciliation": True,
        "original_registry_sources_retrieved": fetched,
        "levels": {
            str(level): {
                "inventory_reports": len(batches[level]["reports"]),
                "original_sources_retrieved": batches[level]["retrieved"],
                "full_scientific_assessments": 0,
                "scientifically_signed_off": False,
            } for level in (4, 5, 6)
        },
        "level7_model": level7["status"],
        "level7_model_trained": False,
        "trial_assessment_records": assessment["assessment_records"],
        "scores_generated": sum(x["provisional_numeric_scores"]
                                for x in assessment["per_level"] if x["level"] <= 7),
        "independently_reviewed_scientific_levels": 0,
        "release_status": "NOT_MERGED_NOT_DEPLOYED",
        "source_issues": [r for r in receipts if r["status"] == "SOURCE_BLOCKED"],
        "next_gates": [
            "VERIFY_CURRENT_CANONICAL_FOCUS_AND_APPLICATION_IDENTITIES",
            "INDEPENDENTLY_ADJUDICATE_SOURCE_DOCUMENTS_AND_CRITERION_SCORES",
            "VALIDATE_LEVEL7_OUTCOME_BLIND_MODEL_AND_CALIBRATION",
            "REVIEW_DRAFT_CODE_AND_APPROVE_PROTECTED_RELEASE",
        ],
    }
    SCORE.safe_write(output / "level4-7-automation-status.json", status)
    return status


def checked_roster_file(roster: dict) -> Path:
    """Legacy source roster checksum must be exact Git blob for the dated file."""
    # The fixed, checked-in dated roster is the only allowed source in v1.
    with ROSTER.open("r", encoding="utf-8") as f:
        if json.load(f) != roster:
            raise ValueError("Supplied roster cannot be silently substituted")
    return ROSTER


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--roster", type=Path, default=ROSTER)
    p.add_argument("--manifest", type=Path, default=MANIFEST)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--curated", type=Path,
                   help="Expert-annotated criterion evidence, no automated grade invention")
    p.add_argument("--stop-file", type=Path, default=STOP)
    args = p.parse_args()
    try:
        roster = json.loads(args.roster.read_text(encoding="utf-8"))
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        curated = json.loads(args.curated.read_text(encoding="utf-8")) if args.curated else None
        status = execute(roster=roster, manifest=manifest, output=args.out_dir,
                         curated=curated, stop_file=args.stop_file)
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(json.dumps({"status": "LEVEL4_7_AUTOMATION_BLOCKED",
                          "blocker": type(exc).__name__, "detail": str(exc)[:150]}))
        return 2
    print(json.dumps(status, indent=2, sort_keys=True))
    # Source gaps are declared in status but do not fabricate success;
    # operational workflow is successful if it audibly recorded all 32 cases.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Read-only registry evidence-change triage for FOCUS scientific Levels 1–6.

Compares two independently collected, explicitly UNREVIEWED current-source
research snapshots. It never authenticates originals, invalidates a production
review, schedules work, publishes a prediction, or rewrites history. Every
trigger needs an authorized source and clinical reviewer before adjudication.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROSTER = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
APPLICATIONS = ROOT / "new-platform/backend/app/data/focus_application_snapshot.json"
FIELDS = (
    "phasesUnreviewed", "studyStatusUnreviewed", "indicationsUnreviewed",
    "primaryEndpointsUnreviewed", "registryResultsContentPresent",
    "primaryResultsUnreviewed", "designUnreviewed", "populationUnreviewed",
    "sourceLeads", "contradictionLeads", "registryPostedVersionDateUnreviewed",
)
EFFECTS = {
    "phasesUnreviewed": (1, 2, 3, 4, 5, 6),
    "studyStatusUnreviewed": (2, 3, 4),
    "indicationsUnreviewed": (2, 3, 6),
    "primaryEndpointsUnreviewed": (3, 4, 5, 6),
    "registryResultsContentPresent": (3, 5, 6),
    "primaryResultsUnreviewed": (3, 5, 6),
    "designUnreviewed": (4, 5),
    "populationUnreviewed": (2, 3, 4, 6),
    "sourceLeads": (1, 3, 4, 5),
    "contradictionLeads": (1, 2, 3, 4, 5, 6),
    "registryPostedVersionDateUnreviewed": (1, 2),
}
NCT_COUNT = 32


def _loaded(name):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _utc_timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Original receipt retrieval time missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid source receipt timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("Original receipt timestamp must have timezone")
    return parsed.astimezone(timezone.utc)


def _original(record, nct):
    receipt = record.get("registrySource")
    if not isinstance(receipt, dict) or receipt.get("nct") != nct:
        raise ValueError("Complete, exact-NCT source receipt required")
    # Receipt integrity and evidence cutoff are also checked by the existing
    # source preparation module. A hash string does NOT prove source provenance.
    return receipt


def _snapshot(report, ncts, preparation):
    records = preparation.validate_snapshot(report, ncts)
    if report.get("focusTrialCount") != NCT_COUNT or len(records) != NCT_COUNT:
        raise ValueError("Exact full FOCUS roster required")
    if report.get("trialsWithRetrievedRegistry") != NCT_COUNT:
        raise ValueError("All current FOCUS registry packets required for comparison")
    if any(row.get("registrySource") is None for row in records.values()):
        raise ValueError("Uncollected original source must not appear as a comparison")
    return records


def compare(baseline, candidate, roster, application_crosswalk):
    """Return an advisory reassessment queue, not live review state changes."""
    prep = _loaded("level16_research_preparation")
    records = prep.load("phase_first_levels_1_6")._records(roster, "FOCUS roster")
    apps = prep.load("phase_first_levels_1_6")._records(
        application_crosswalk, "FOCUS application crosswalk")
    if (len(records) != NCT_COUNT or len(apps) != 29
            or not set(apps).issubset(records)):
        raise ValueError("Frozen FOCUS cohort or provisional identity mismatch")
    app_cycles = set()
    for nct, mapped in apps.items():
        candidates = mapped.get("candidateApplications")
        if not isinstance(candidates, list):
            raise ValueError("Invalid application candidates")
        for item in candidates:
            if (not isinstance(item, dict) or item.get("ticker") != records[nct]["ticker"]
                    or not isinstance(item.get("cycleId"), str)
                    or not item["cycleId"].strip()):
                raise ValueError("Provisional application cycle identity mismatch")
            app_cycles.add(item["cycleId"])
    if len(app_cycles) != 23 or sorted(set(records) - set(apps)) != sorted(
            ("NCT05031780", "NCT06747468", "NCT06553768")):
        raise ValueError("Unmapped FOCUS exceptions or cycle count changed")
    old = _snapshot(baseline, list(records), prep)
    new = _snapshot(candidate, list(records), prep)
    if date.fromisoformat(candidate["evidenceCutoffDate"]) < date.fromisoformat(
            baseline["evidenceCutoffDate"]):
        raise ValueError("Candidate research cutoff precedes baseline")
    rows = []
    for nct in records:
        old_trial, new_trial = old[nct], new[nct]
        if (old_trial.get("ticker") != records[nct]["ticker"]
                or new_trial.get("ticker") != records[nct]["ticker"]
                or old_trial.get("mappingStatus") != new_trial.get("mappingStatus")
                or old_trial.get("candidateApplicationCycleIdsUnverified")
                != new_trial.get("candidateApplicationCycleIdsUnverified")):
            raise ValueError("Cross-trial or application mapping changed")
        before, after = _original(old_trial, nct), _original(new_trial, nct)
        previous, next_time = _utc_timestamp(before["retrievedAt"]), _utc_timestamp(after["retrievedAt"])
        if next_time < previous:
            raise ValueError("Candidate source receipt predates baseline source capture")
        digest_changed = before["documentSha256"] != after["documentSha256"]
        changed_fields = [key for key in FIELDS if before.get(key) != after.get(key)]
        captured_changed = before["capturedRegistry"]["fields"] != after["capturedRegistry"]["fields"]
        if not digest_changed and (changed_fields or captured_changed):
            raise ValueError("Same original-source digest cannot have changed extracted field metadata")
        if digest_changed and next_time <= previous:
            raise ValueError("Changed registry bytes require a newer recorded retrieval")
        old_version = before.get("registryPostedVersionDateUnreviewed")
        new_version = after.get("registryPostedVersionDateUnreviewed")
        rollback = bool(old_version and new_version and
                        date.fromisoformat(new_version) < date.fromisoformat(old_version))
        # Even a byte change with no selected-field differences changes the
        # original evidence version; conservatively trigger all six levels.
        trigger = digest_changed or bool(changed_fields) or rollback
        affected = set()
        for key in changed_fields:
            affected.update(EFFECTS[key])
        if digest_changed:
            affected.update(range(1, 7))
        if rollback:
            affected.update(range(1, 7))
        reasons = (["SOURCE_ORIGINAL_BYTES_DIFFER_RECEIPT_REVIEW_REQUIRED"]
                   if digest_changed else [])
        if rollback:
            reasons.append("REGISTRY_POSTED_VERSION_ROLLBACK_REQUIRES_RECONCILIATION")
        reasons += ["CAPTURED_" + key.upper() + "_DIFF" for key in changed_fields]
        rows.append({
            "nct": nct, "ticker": records[nct]["ticker"],
            "provisionalMappingStatus": old_trial.get("mappingStatus"),
            "baselineSourceSha256Unverified": before["documentSha256"],
            "candidateSourceSha256Unverified": after["documentSha256"],
            "baselineRegistryPostedDateUnreviewed": old_version,
            "candidateRegistryPostedDateUnreviewed": new_version,
            "reassessmentTrigger": trigger,
            "triggerReasons": reasons,
            "fieldCategoriesChanged": changed_fields,
            "affectedLevels": sorted(affected),
            "currentSourceReviewStatus": "NOT_INDEPENDENTLY_AUTHENTICATED",
            "scientificReassessmentStatus": (
                "BLOCKED_PENDING_INDEPENDENT_SOURCE_AND_DOMAIN_REVIEW"
                if trigger else "NO_NEW_REGISTRY_SOURCE_CHANGE_DETECTED"
            ),
            "mayCarryOverPriorScientificSignoffAutomatically": False,
            "approvalProbability": None,
            "fdaOutcomeJudgment": None,
        })
    return {
        "kind": "FOCUS_LEVEL16_REGISTRY_CHANGE_TRIAGE_RESEARCH_ONLY",
        "baselineEvidenceCutoff": baseline["evidenceCutoffDate"],
        "candidateEvidenceCutoff": candidate["evidenceCutoffDate"],
        "focusTrialCount": len(rows),
        "provisionalApplicationCycleCount": len(app_cycles),
        "changedTrialCount": sum(row["reassessmentTrigger"] for row in rows),
        "unchangedTrialCount": sum(not row["reassessmentTrigger"] for row in rows),
        "independentlyAuthenticatedSources": 0,
        "independentlyAdjudicatedLevels": 0,
        "publishedFdaForecasts": 0,
        "historicalBlindPredictionPermitted": False,
        "doesNotModifyLiveReviewState": True,
        "trials": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--roster", type=Path, default=ROSTER)
    parser.add_argument("--applications", type=Path, default=APPLICATIONS)
    args = parser.parse_args()
    def read(path):
        return json.loads(path.read_text(encoding="utf-8"))
    report = compare(read(args.baseline), read(args.candidate),
                     read(args.roster), read(args.applications))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

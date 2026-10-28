"""Published, research-only source-candidate replay summary with no FDA model labels.

The summary pins a completed GitHub Actions source replay, but runtime cannot
reopen expired artifacts. A valid summary is a research report, not proof
that all FDA review cycles are known, and cannot authorize model training.
"""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import re

from .hop_fda_filing_benchmarks import audit_fda_filing_benchmarks

_ROOT = Path(__file__).parent / "research_sources"
_INDEX = _ROOT / "hop_fda_action_candidate_2024_2025_audit_index.json"
_BENCHMARK = _ROOT / "hop_fda_pdufa_filing_benchmarks.json"
_SCHEMA = "hop-fda-fy2024-fy2025-action-candidate-summary-v1"
_HASH = re.compile(r"[a-f0-9]{64}\Z")
_PINS = {
    "drugsfda": "adb24d7921d56bc3824b57e785164a32287efc69a9d3fe9b940da97f6c65f5b2",
    "crl": "d3d284e1ec0aa62b6dfb7523bd7bbfc7324c3b218a412fd6ee357a35f5c39898",
}
_CATEGORIES = (
    "original_ap_registry_action_candidates",
    "tentative_approval_nonbinary_candidates",
    "selected_crl_parent_only",
    "selected_crl_explicit_original",
    "selected_crl_supplement_excluded",
    "selected_crl_legacy_unresolved",
    "selected_crl_multiple_missing",
)
_RESEARCH_FALSE_FLAGS = (
    "verified_original_filing_denominator",
    "all_original_filing_application_ids_known",
    "every_review_cycle_decision_verified",
    "every_predecision_feature_snapshot_verified",
    "training_authorized",
    "trade_authorized",
)


def _unique_json(pairs):
    d = {}
    for key, value in pairs:
        if key in d:
            raise ValueError("Duplicate research source JSON property")
        d[key] = value
    return d


def audit_fda_action_candidate_replay_summary(
    manifest: dict, filing_benchmarks: dict, *, as_of: date,
) -> dict:
    """Quarantined FY action-source results. No sample-based probability."""
    if type(as_of) is not date:
        raise ValueError("Exact research as-of date required")
    if not isinstance(manifest, dict) or manifest.get("schema_version") != _SCHEMA:
        raise ValueError("Unknown FDA action-source research summary schema")
    captured = manifest.get("compiled_on")
    if captured != "2026-10-28":
        raise ValueError("Pinned source-replay capture date missing")
    if as_of < date.fromisoformat(captured):
        return {
            "status": "ACTION_SOURCE_REPLAY_NOT_YET_OBSERVED_AS_OF",
            "asOf": as_of.isoformat(),
            "researchCandidateRows": 0,
            "sourceFiscalActionSummaries": [],
            "independentlyVerifiedModelCycles": 0,
            "independentRealBacktests": 0,
            "approvalProbability": None,
            "trainingAuthorized": False,
        }
    if manifest.get("status") != "SOURCE_SELECTED_CANDIDATES_NOT_VERIFIED_DECISION_COHORT":
        raise ValueError("Invalid source-selected historical research classification")
    for key in _RESEARCH_FALSE_FLAGS:
        if manifest.get(key) is not False:
            raise ValueError("Historical research source cannot self-certify " + key)
    if (any(type(manifest.get(key)) is not int or manifest[key] != 0 for key in (
            "model_eligible_cycles", "independent_real_backtests"))
            or manifest.get("approval_probability") is not None
            or manifest.get("measured_accuracy") is not None):
        raise ValueError("Unreviewed candidate sources are not validated model labels")
    replay = manifest.get("replay")
    if not isinstance(replay, dict) or any(type(replay.get(key)) is not int for key in (
            "run_id", "artifact_id", "github_artifact_retention_days")):
        raise ValueError("Source replay run identity missing")
    if (replay.get("run_id") != 40723526247
            or replay.get("artifact_id") != 12831901791
            or replay.get("source_replay_commit") !=
            "f5c0fe7fbe66e6dcbc7e5a7c64f2e97ce6433bb3"
            or replay.get("github_artifact_retention_days") != 14
            or replay.get("queue_durable_archived") is not False
            or replay.get("artifact_url") !=
            "https://github.com/pdufa/pdufa-command-center/actions/runs/40723526247/artifacts/12831901791"
            or not isinstance(replay.get("queue_sha256"), str)
            or not _HASH.fullmatch(replay["queue_sha256"])):
        raise ValueError("Untrusted FDA source replay provenance")
    sources = manifest.get("sources")
    if not isinstance(sources, dict) or set(sources) != set(_PINS):
        raise ValueError("Both pinned FDA source archive audits required")
    for kind, expected in _PINS.items():
        row = sources[kind]
        if (not isinstance(row, dict) or row.get("sha256") != expected
                or row.get("retrieved_on") != "2026-10-25"
                or row.get("exported_on") !=
                ("2026-10-23" if kind == "drugsfda" else "2026-10-21")
                or type(row.get("records")) is not int
                or row["records"] != (29416 if kind == "drugsfda" else 458)
                or row.get("selection") !=
                ("APPROVED_PRODUCT_REGISTRY_NOT_COMPLETE"
                 if kind == "drugsfda" else
                 "SELECTIVELY_PUBLISHED_FDA_LETTERS_NOT_COMPLETE")):
            raise ValueError("FDA source manifest pins or selection status changed")
    reference = audit_fda_filing_benchmarks(filing_benchmarks)
    filings = reference["latest_original_applications_filed_by_fy"]
    years = manifest.get("fiscal_action_years")
    if not isinstance(years, list) or len(years) != 2:
        raise ValueError("The two pinned fiscal action-year summaries are required")
    by_year = {}
    for row in years:
        if not isinstance(row, dict) or type(row.get("year")) is not int:
            raise ValueError("Invalid fiscal source action year")
        fy = row["year"]
        if fy not in (2024, 2025) or fy in by_year:
            raise ValueError("Duplicate or unexpected fiscal source action year")
        if (type(row.get("original_filing_year_reported_count")) is not int
                or row["original_filing_year_reported_count"] != filings[str(fy)]):
            raise ValueError("FDA original filing-year totals must match audited report versions")
        for key in _CATEGORIES + (
            "distinct_apps_original_ap", "distinct_parent_apps_crl",
            "source_overlap_same_action_fy",
        ):
            if type(row.get(key)) is not int or row[key] < 0:
                raise ValueError("Source candidate count must be nonnegative integer")
        if (row["distinct_apps_original_ap"] >
                row["original_ap_registry_action_candidates"]
                or row["source_overlap_same_action_fy"] >
                min(row["distinct_apps_original_ap"], row["distinct_parent_apps_crl"])):
            raise ValueError("Source selected application identity counts conflict")
        by_year[fy] = row
    total = sum(row[key] for row in by_year.values() for key in _CATEGORIES)
    if (type(manifest.get("source_candidate_rows")) is not int
            or total != manifest["source_candidate_rows"]
            or total != 412):
        raise ValueError("FDA candidate queue count differs from action-source classes")
    if not isinstance(manifest.get("caution"), str) or not manifest["caution"].strip():
        raise ValueError("Historical filing/action year mismatch warning missing")
    return {
        "status": "SOURCE_SELECTED_FDA_ACTION_CANDIDATES_RESEARCH_ONLY",
        "asOf": as_of.isoformat(),
        "capturedAt": captured,
        "sourceRecordsInspected": {
            "drugsfdaApprovedRegistry": sources["drugsfda"]["records"],
            "selectivelyPublishedLetterRecords": sources["crl"]["records"],
        },
        "researchCandidateRows": total,
        "sourceFiscalActionSummaries": [
            {
                "fiscalActionYear": fy,
                "originalApplicationsFiledInFiscalYearReferenceOnly":
                    by_year[fy]["original_filing_year_reported_count"],
                "originalApprovalActionCandidatesFromApprovedRegistry":
                    by_year[fy]["original_ap_registry_action_candidates"],
                "uniqueApplicationsInApprovedActionCandidates":
                    by_year[fy]["distinct_apps_original_ap"],
                "nonbinaryTentativeApprovalCandidates":
                    by_year[fy]["tentative_approval_nonbinary_candidates"],
                "selectedPublishedCrlParentOnly":
                    by_year[fy]["selected_crl_parent_only"],
                "selectedPublishedCrlExplicitOriginal":
                    by_year[fy]["selected_crl_explicit_original"],
                "selectedPublishedCrlSupplementsExcluded":
                    by_year[fy]["selected_crl_supplement_excluded"],
                "selectedPublishedCrlLegacyUnresolved":
                    by_year[fy]["selected_crl_legacy_unresolved"],
                "selectedPublishedCrlMultipleMissing":
                    by_year[fy]["selected_crl_multiple_missing"],
                "overlappingParentApplicationsSameFiscalActionYear":
                    by_year[fy]["source_overlap_same_action_fy"],
                "filingDenominatorCoverage": None,
                "approvalRate": None,
                "independentModelEligibleCycles": 0,
            } for fy in sorted(by_year)
        ],
        "replayArtifactUrl": replay["artifact_url"],
        "queueSha256": replay["queue_sha256"],
        "sourceArchivesCapturedAndFingerprintPinned": True,
        "exactReviewCycleIndependentVerification": False,
        "completeFilingCohortVerified": False,
        "historicalIndependentBacktests": 0,
        "fdaApprovalProbability": None,
        "independentlyMeasuredAccuracy": None,
        "trainingAuthorized": False,
        "tradeAuthorized": False,
        "criticalLimitation": manifest["caution"],
    }


def load_fda_action_candidate_replay_summary(*, as_of: date) -> dict:
    return audit_fda_action_candidate_replay_summary(
        json.loads(_INDEX.read_text(encoding="utf-8"),
                   object_pairs_hook=_unique_json),
        json.loads(_BENCHMARK.read_text(encoding="utf-8"),
                   object_pairs_hook=_unique_json),
        as_of=as_of,
    )

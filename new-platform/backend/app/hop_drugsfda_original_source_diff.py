"""Compare TWO actual quarantined FDA source families at submission-key level.

The official tabular Drugs@FDA file and a pinned openFDA-approved-registry
artifact are different snapshots/representations; neither is a complete
NDA/BLA historical FDA review-cycle decision denominator. Comparison only
reports source membership and raw metadata discrepancies, never labels.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime

HEX = re.compile(r"[0-9a-f]{64}\Z")
APPL = re.compile(r"(?:NDA|BLA)[0-9]{6}\Z")


def _read_archived_originals(data: dict) -> tuple[dict, dict]:
    if (not isinstance(data, dict)
            or data.get("schema_version") != 1
            or data.get("status") != "APPROVED_REGISTRY_NOT_COMPLETE_DECISION_COHORT"
            or not isinstance(data.get("records"), list)):
        raise ValueError("Archived FDA registry is not a quarantined source snapshot")
    originals = {}
    by_application = Counter()
    seen_apps = set()
    for row in data["records"]:
        if (not isinstance(row, dict)
                or row.get("model_eligible") is not False
                or row.get("complete_application_denominator_verified") is not False
                or row.get("review_cycles_independently_adjudicated") is not False
                or row.get("point_in_time_features_verified") is not False):
            raise ValueError("Original registry source was promoted or malformed")
        app = row.get("application_number_as_published")
        if not isinstance(app, str) or not re.fullmatch(
            r"(?:NDA|BLA|ANDA)[0-9]{5,6}", app
        ) or app in seen_apps:
            raise ValueError("Invalid or duplicate archived application identity")
        seen_apps.add(app)
        submissions = row.get("submissions_as_published")
        if not isinstance(submissions, list):
            raise ValueError("Archived FDA submission list unavailable")
        if app[:3] not in ("NDA", "BLA"):
            continue
        for sub in submissions:
            if not isinstance(sub, dict):
                raise ValueError("Bad archived FDA submission entry")
            if sub.get("submission_type_as_published") != "ORIG":
                continue
            number = sub.get("submission_number_as_published")
            if not isinstance(number, str) or not re.fullmatch(r"[0-9]{1,5}", number):
                raise ValueError("Invalid archived original submission number")
            key = (app, int(number))
            if key in originals:
                raise ValueError("Duplicate archived original application/submission key")
            if not APPL.fullmatch(app):
                raise ValueError("Nonstandard archived application has an original entry")
            raw_status = sub.get("submission_status_as_published")
            raw_date = sub.get("submission_status_date_as_published")
            if raw_status is not None and not isinstance(raw_status, str):
                raise ValueError("Malformed archived raw FDA status")
            if raw_date is not None and not isinstance(raw_date, str):
                raise ValueError("Malformed archived raw FDA date")
            if raw_date:
                if not re.fullmatch(r"[0-9]{8}", raw_date):
                    raise ValueError("Malformed archived FDA date")
                try:
                    parsed = datetime.strptime(raw_date, "%Y%m%d").date()
                except ValueError as e:
                    raise ValueError("Invalid archived FDA date") from e
                normalized_date = parsed.isoformat()
            else:
                normalized_date = None
            originals[key] = (raw_status or "", normalized_date)
            by_application[app] += 1
    return originals, {
        "_archived_application_ids": seen_apps,
        "archived_application_record_count": len(data["records"]),
        "archived_original_application_count": len(by_application),
        "archived_original_submission_count": len(originals),
    }


def reconcile_original_submission_sources(
    tabular: dict, archive: dict, *,
    tabular_index: dict, archive_index: dict,
    as_of: date,
    max_examples: int = 25,
) -> dict:
    """Cross-compare source keys and status metadata without adjudication.

    Requires both frozen upstream SHA fingerprints from separately collected
    source audits. A different source version must be pinned before comparing.
    """
    if not isinstance(as_of, date) or type(max_examples) is not int or not 1 <= max_examples <= 100:
        raise ValueError("Invalid source comparison cutoff/sample limit")
    if (not isinstance(tabular, dict)
            or tabular.get("status") != "DRUGSFDA_ORIGINAL_SUBMISSION_SPINE_RESEARCH_ONLY"
            or tabular.get("independently_verified_fda_review_cycles") != 0
            or tabular.get("model_eligible_records") != 0
            or tabular.get("prediction_probability") is not None
            or tabular.get("complete_original_nda_bla_application_denominator_verified") is not False
            or not isinstance(tabular.get("candidate_original_submissions"), list)
            or not isinstance(tabular_index, dict)
            or tabular_index.get("status") != "OFFICIAL_FDA_TABLE_ORIGINAL_SUBMISSIONS_QUARANTINED"
            or not isinstance(archive_index, dict)
            or archive_index.get("status") != "ACTUAL_FDA_APPROVED_REGISTRY_ORIGINAL_SPINE_QUARANTINED"
            or tabular_index.get("model_eligible_records") != 0
            or archive_index.get("model_eligible_records") != 0
            or tabular_index.get("prediction_probability") is not None
            or archive_index.get("prediction_probability") is not None
            or archive_index.get("complete_original_nda_bla_denominator_verified") is not False):
        raise ValueError("Source comparison requires two independent quarantined inventories")
    if (tabular.get("research_cutoff") != as_of.isoformat()
            or archive_index.get("research_cutoff") != as_of.isoformat()
            or tabular.get("source_application_tsv_sha256") != tabular_index.get("applications_tsv_sha256")
            or tabular.get("source_submission_tsv_sha256") != tabular_index.get("submissions_tsv_sha256")
            or any(not isinstance(d, str) or not HEX.fullmatch(d) for d in (
                archive_index.get("github_artifact_json_sha256"),
                tabular.get("source_application_tsv_sha256"),
                tabular.get("source_submission_tsv_sha256"),
            ))
            or len(tabular["candidate_original_submissions"]) != tabular_index.get("original_nda_bla_submission_rows")
            or tabular.get("distinct_nda_bla_applications_in_original_submission_inventory")
               != tabular_index.get("distinct_nda_bla_applications_in_original_submission_inventory")):
        raise ValueError("Pinned FDA source bytes/counts do not reconcile")
    archived, arch_counts = _read_archived_originals(archive)
    if (arch_counts["archived_application_record_count"] != archive_index.get("approved_registry_application_records")
            or arch_counts["archived_original_submission_count"] != archive_index.get("original_nda_bla_submission_entries")
            or arch_counts["archived_original_application_count"] != archive_index.get("distinct_nda_bla_applications_with_original_submission")):
        raise ValueError("Archived source key counts are not identical to pinned audit")
    tab = {}
    for item in tabular["candidate_original_submissions"]:
        if (not isinstance(item, dict)
                or item.get("independently_verified") is not False
                or item.get("model_eligible") is not False
                or item.get("review_cycle") is not None
                or item.get("fda_action_outcome") is not None
                or item.get("submission_kind") != "ORIG"):
            raise ValueError("Tabular source row is not an unverified original")
        app = item.get("application_id")
        number = item.get("original_submission_number")
        if not isinstance(app, str) or not APPL.fullmatch(app) or type(number) is not int or number < 1:
            raise ValueError("Invalid tabular NDA/BLA original submission key")
        key = (app, number)
        if key in tab:
            raise ValueError("Duplicate original key in tabular source")
        code = item.get("raw_submission_status_code")
        raw_day = item.get("raw_submission_status_date")
        if not isinstance(code, str) or raw_day is not None and not isinstance(raw_day, str):
            raise ValueError("Invalid tabular raw source data")
        tab[key] = (code, raw_day)
    keys_tab, keys_arch = set(tab), set(archived)
    missing_from_arch = sorted(keys_tab - keys_arch)
    missing_from_tab = sorted(keys_arch - keys_tab)
    overlap = keys_tab & keys_arch
    different_status = sorted(k for k in overlap if tab[k][0] != archived[k][0])
    different_date = sorted(k for k in overlap if tab[k][1] != archived[k][1])
    app_diff_tab = {app for app, _ in missing_from_arch}
    app_diff_arch = {app for app, _ in missing_from_tab}
    absent_archived_app_keys = sorted(
        key for key in missing_from_arch
        if key[0] not in arch_counts["_archived_application_ids"]
    )
    if len(tab) != tabular_index["original_nda_bla_submission_rows"]:
        raise ValueError("Tabular source inventory had unstable key count")

    def examples(keys: list[tuple[str, int]]) -> list[dict]:
        return [{"application_id": app, "original_submission_number": n}
                for app, n in keys[:max_examples]]

    return {
        "status": "ORIGINAL_SUBMISSION_SOURCE_MEMBERSHIP_RECONCILED_NOT_FDA_DECISIONS",
        "research_cutoff": as_of.isoformat(),
        "source_versions": {
            "tabular_applications_tsv_sha256": tabular["source_application_tsv_sha256"],
            "tabular_submissions_tsv_sha256": tabular["source_submission_tsv_sha256"],
            "openfda_approved_registry_artifact_json_sha256":
                archive_index["github_artifact_json_sha256"],
        },
        "tabular_original_submission_keys": len(keys_tab),
        "openfda_archived_original_submission_keys": len(keys_arch),
        "net_tabular_minus_openfda_original_keys": len(keys_tab) - len(keys_arch),
        "shared_original_submission_keys": len(overlap),
        "tabular_keys_absent_from_openfda": len(missing_from_arch),
        "openfda_keys_absent_from_tabular": len(missing_from_tab),
        "distinct_applications_with_tabular_only_keys": len(app_diff_tab),
        "distinct_applications_with_openfda_only_keys": len(app_diff_arch),
        "tabular_only_keys_with_entire_application_absent_from_openfda":
            len(absent_archived_app_keys),
        "tabular_only_keys_in_openfda_application_but_missing_original":
            len(missing_from_arch) - len(absent_archived_app_keys),
        "shared_keys_with_raw_status_mismatch": len(different_status),
        "shared_keys_with_raw_status_date_mismatch": len(different_date),
        "tabular_only_key_examples": examples(missing_from_arch),
        "openfda_only_key_examples": examples(missing_from_tab),
        "status_mismatch_key_examples": examples(different_status),
        "date_mismatch_key_examples": examples(different_date),
        "examples_truncated": any(len(keys) > max_examples for keys in (
            missing_from_arch, missing_from_tab, different_status, different_date
        )),
        "original_fda_action_dates_independently_verified": 0,
        "review_cycles_independently_verified": 0,
        "complete_fda_decision_denominator_verified": False,
        "model_eligible_records": 0,
        "approval_rate": None,
        "prediction_probability": None,
        "predictive_accuracy": None,
        "readiness": "REVIEW_REQUIRED",
        "note": (
            "Different source representations and collection dates may explain "
            "some membership/status discrepancies. A shared application+ORIG "
            "number is not an adjudicated FDA review cycle or outcome."
        ),
    }

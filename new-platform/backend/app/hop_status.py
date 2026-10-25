"""Read-only HOP readiness status from committed research sources.

No database writes, model fitting, scanner scheduling, or probability output.
"""
from __future__ import annotations
import json
from pathlib import Path

STAGING_PATH = Path(__file__).parent / "research_sources" / "hop_fda_outcome_staging.json"
SOURCE_AUDIT_PATH = Path(__file__).parent / "research_sources" / "hop_openfda_crl_audit_index.json"
DRUGS_SOURCE_AUDIT_PATH = Path(__file__).parent / "research_sources" / "hop_drugsfda_audit_index.json"
CROSSWALK_AUDIT_PATH = Path(__file__).parent / "research_sources" / "hop_fda_crosswalk_audit_index.json"
REPEAT_LETTER_AUDIT_PATH = Path(__file__).parent / "research_sources" / "hop_fda_repeat_letter_triage_index.json"
IDENTITY_REVIEW_AUDIT_PATH = Path(__file__).parent / "research_sources" / "hop_fda_identity_review_queue_index.json"


def _published_letter_source_audit(path: Path) -> dict | None:
    """Summarize a quarantined published-letter archive, never an outcome cohort."""
    try:
        audit = json.loads(path.read_text(encoding="utf-8"))
        published = audit["published_letter_records"]
        quarantined = audit["quarantined_letter_records"]
        counts = audit["letter_type_counts"]
        if (audit.get("status") != "QUARANTINED_NOT_A_COMPLETE_APPLICATION_COHORT"
                or type(published) is not int or published < 1
                or type(quarantined) is not int or quarantined != published
                or not isinstance(counts, dict)
                or any(type(n) is not int or n < 0 for n in counts.values())
                or sum(counts.values()) != published
                or audit.get("verified_complete_application_denominator") is not False
                or audit.get("model_eligible_records") != 0
                or audit.get("verified_application_review_cycles") != 0):
            raise ValueError("Invalid or unverified FDA publication-source audit")
        return {
            "published_letter_records": published,
            "quarantined_letter_records": quarantined,
            "fda_export_date": audit["source_export_date"],
            "collection_run_url": audit["collection_run_url"],
            "verified_application_review_cycles": 0,
            "model_eligible_records": 0,
            "complete_denominator_verified": False,
            "status": "PUBLICATION_ONLY_NOT_MODEL_ELIGIBLE",
        }
    except (OSError, ValueError, TypeError, KeyError):
        return None



def _quarantined_approved_registry(path: Path) -> dict | None:
    try:
        index = json.loads(path.read_text(encoding="utf-8"))
        total = index["source_application_records"]
        quarantined = index["quarantined_application_records"]
        prefixes = index["application_number_prefixes"]
        if (index.get("status") != "QUARANTINED_APPROVED_REGISTRY_NOT_COMPLETE_DECISION_COHORT"
                or type(total) is not int or total < 1
                or type(quarantined) is not int or quarantined != total
                or not isinstance(prefixes, dict)
                or any(type(n) is not int or n < 0 for n in prefixes.values())
                or sum(prefixes.values()) != total
                or index.get("complete_application_denominator_verified") is not False
                or type(index.get("model_eligible_records")) is not int
                or index["model_eligible_records"] != 0
                or type(index.get("independently_verified_review_cycle_outcomes")) is not int
                or index["independently_verified_review_cycle_outcomes"] != 0):
            raise ValueError("FDA approved registry is not a validated cohort")
        return {"status": "APPROVED_REGISTRY_ONLY", "application_records": total,
                "quarantined_records": total, "application_types": prefixes,
                "source_export_date": index["source_export_date"],
                "collection_run_url": index["collection_run_url"],
                "model_eligible_records": 0, "complete_denominator_verified": False}
    except (OSError, ValueError, TypeError, KeyError):
        return None


def _quarantined_identity_crosswalk(path: Path) -> dict | None:
    try:
        index = json.loads(path.read_text(encoding="utf-8"))
        counts = index["identity_link_status_counts"]
        letters = index["published_letter_records"]
        registry = index["approved_registry_source_application_records"]
        qualified = index["qualified_reference_letter_records"]
        legacy = index["unresolved_legacy_bl_letter_records"]
        missing = index["letters_without_application_identifiers"]
        allowed_statuses = {
            "APPLICATION_ID_UNRESOLVED",
            "MULTIPLE_OR_AMBIGUOUS_APPLICATION_LINKS",
            "NOT_FOUND_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT",
            "PRESENT_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT",
        }
        if (index.get("status") != "QUARANTINED_IDENTITY_LINKAGE_ONLY_NOT_OUTCOME_COHORT"
                or type(letters) is not int or letters < 1
                or type(registry) is not int or registry < 1
                or not isinstance(counts, dict)
                or set(counts) != allowed_statuses
                or any(type(n) is not int or n < 0 for n in counts.values())
                or sum(counts.values()) != letters
                or type(qualified) is not int or not 0 <= qualified <= letters
                or type(legacy) is not int or not 0 <= legacy <= counts["APPLICATION_ID_UNRESOLVED"]
                or type(missing) is not int or not 0 <= missing <= counts["APPLICATION_ID_UNRESOLVED"]
                or legacy + missing > counts["APPLICATION_ID_UNRESOLVED"]
                or index.get("complete_application_denominator_verified") is not False
                or type(index.get("model_eligible_records")) is not int
                or index["model_eligible_records"] != 0
                or type(index.get("verified_review_cycle_outcomes")) is not int
                or index["verified_review_cycle_outcomes"] != 0):
            raise ValueError("FDA source linkage cannot be a validated outcome cohort")
        return {"status": "IDENTITY_MATCH_ONLY", "published_letter_records": letters,
                "approved_registry_source_application_records": registry,
                "identity_link_status_counts": counts,
                "qualified_reference_letter_records": qualified,
                "unresolved_legacy_bl_letter_records": legacy,
                "letters_without_application_identifiers": missing,
                "application_identity_normalization": index["application_identity_normalization"],
                "collection_run_url": index["collection_run_url"],
                "collection_artifact_url": index["collection_artifact_url"],
                "model_eligible_records": 0, "verified_review_cycle_outcomes": 0}
    except (OSError, ValueError, TypeError, KeyError):
        return None


def _quarantined_repeat_letter_triage(path: Path) -> dict | None:
    """Source-level repeat groups are NOT independently verified review cycles."""
    try:
        source = json.loads(path.read_text(encoding="utf-8"))
        total = source["published_letter_records"]
        grouped = source["grouped_letter_records"]
        excluded = source["excluded_letter_records"]
        single = source["single_letter_application_groups"]
        repeated_groups = source["repeated_letter_application_groups"]
        repeated_letters = source["letter_records_in_repeated_groups"]
        collisions = source["potential_same_day_type_duplicate_groups"]
        counts = (total, grouped, single, repeated_groups, repeated_letters, collisions)
        if (source.get("status") != "REVIEW_CYCLE_TRIAGE_ONLY_NO_INDEPENDENT_OUTCOME_LABELS"
                or any(type(x) is not int or x < 0 for x in counts)
                or total < 1 or not isinstance(excluded, dict)
                or set(excluded) != {"unresolved_or_ambiguous_identity"}
                or type(excluded["unresolved_or_ambiguous_identity"]) is not int
                or excluded["unresolved_or_ambiguous_identity"] < 0
                or grouped + excluded["unresolved_or_ambiguous_identity"] != total
                or single + repeated_letters != grouped
                or repeated_groups > repeated_letters
                or collisions > repeated_groups
                or source.get("complete_application_denominator_verified") is not False
                or type(source.get("independently_verified_review_cycles")) is not int
                or source["independently_verified_review_cycles"] != 0
                or type(source.get("model_eligible_records")) is not int
                or source["model_eligible_records"] != 0
                or source.get("prediction_probability") is not None):
            raise ValueError("source triage counts cannot establish verified review cycles")
        return {
            "status": "REPEATED_LETTER_RESEARCH_ONLY",
            "published_letter_records": total,
            "grouped_letter_records": grouped,
            "excluded_letter_records": excluded,
            "single_letter_application_groups": single,
            "repeated_letter_application_groups": repeated_groups,
            "letter_records_in_repeated_groups": repeated_letters,
            "potential_same_day_type_duplicate_groups": collisions,
            "collection_run_url": source["collection_run_url"],
            "collection_artifact_url": source["collection_artifact_url"],
            "independently_verified_review_cycles": 0,
            "model_eligible_records": 0,
        }
    except (OSError, KeyError, ValueError, TypeError):
        return None



def _quarantined_identity_review_queue(path: Path) -> dict | None:
    """Counts from actual published source review queue, not regulatory outcomes."""
    reasons = {
        "APPLICATION_ID_UNRESOLVED",
        "MULTIPLE_OR_AMBIGUOUS_APPLICATION_LINKS",
        "NOT_FOUND_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT",
    }
    try:
        src = json.loads(path.read_text(encoding="utf-8"))
        total = src["published_letter_records"]
        queued = src["review_queue_records"]
        linked = src["already_identity_linked_records"]
        counts = src["review_reason_counts"]
        repeated = src["repeated_letter_application_groups"]
        duplicate_groups = src["potential_same_day_type_duplicate_groups"]
        if (src.get("status") != "IDENTITY_REVIEW_QUEUE_NOT_OUTCOME_COHORT"
                or any(type(x) is not int or x < 0
                       for x in (total, queued, linked, repeated, duplicate_groups))
                or total < 1 or linked + queued != total
                or not isinstance(counts, dict) or set(counts) != reasons
                or any(type(v) is not int or v < 0 for v in counts.values())
                or sum(counts.values()) != queued
                or duplicate_groups > repeated
                or src.get("complete_application_denominator_verified") is not False
                or type(src.get("independently_verified_review_cycles")) is not int
                or src["independently_verified_review_cycles"] != 0
                or type(src.get("model_eligible_records")) is not int
                or src["model_eligible_records"] != 0
                or src.get("prediction_probability") is not None):
            raise ValueError("review queue failed source reconciliation or model abstention")
        return {
            "status": "IDENTITY_REVIEW_REQUIRED_NOT_OUTCOME_COHORT",
            "published_letter_records": total,
            "identity_linked_records": linked,
            "identity_review_queue_records": queued,
            "review_reason_counts": counts,
            "source_export_date": src["source_export_date"],
            "collection_run_url": src["source_collection_run_url"],
            "collection_artifact_url": src["collection_artifact_url"],
            "independently_verified_review_cycles": 0,
            "model_eligible_records": 0,
            "complete_denominator_verified": False,
        }
    except (OSError, KeyError, ValueError, TypeError):
        return None

def hop_readiness_status(path: Path = STAGING_PATH, source_audit_path: Path = SOURCE_AUDIT_PATH,
                         drugs_audit_path: Path = DRUGS_SOURCE_AUDIT_PATH,
                         crosswalk_audit_path: Path = CROSSWALK_AUDIT_PATH,
                         repeat_letter_audit_path: Path = REPEAT_LETTER_AUDIT_PATH,
                         identity_review_audit_path: Path = IDENTITY_REVIEW_AUDIT_PATH) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        records = raw["records"]
        if not isinstance(records, list):
            raise ValueError("records must be a list")
        staged = len(records)
        # Every staging record is quarantined regardless of a caller-supplied
        # eligibility flag; staging cannot promote observations into training.
        quarantined = staged
        # Staging is *never* a model-eligible source, even if a flag changes.
        letter_source = _published_letter_source_audit(source_audit_path)
        drug_source = _quarantined_approved_registry(drugs_audit_path)
        identity_links = _quarantined_identity_crosswalk(crosswalk_audit_path)
        if identity_links and (not letter_source or not drug_source
                or identity_links["published_letter_records"] != letter_source["published_letter_records"]
                or identity_links["approved_registry_source_application_records"] != drug_source["application_records"]):
            identity_links = None
        repeat_letters = _quarantined_repeat_letter_triage(repeat_letter_audit_path)
        if repeat_letters and (not identity_links
                or repeat_letters["published_letter_records"] != identity_links["published_letter_records"]
                or repeat_letters["excluded_letter_records"]["unresolved_or_ambiguous_identity"] != (
                    identity_links["identity_link_status_counts"]["APPLICATION_ID_UNRESOLVED"]
                    + identity_links["identity_link_status_counts"]["MULTIPLE_OR_AMBIGUOUS_APPLICATION_LINKS"])):
            repeat_letters = None
        identity_review = _quarantined_identity_review_queue(identity_review_audit_path)
        if identity_review and (not identity_links
                or identity_review["published_letter_records"] != identity_links["published_letter_records"]
                or identity_review["identity_linked_records"] != identity_links["identity_link_status_counts"][
                    "PRESENT_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT"]
                or any(identity_review["review_reason_counts"].get(reason) != count
                       for reason, count in identity_links["identity_link_status_counts"].items()
                       if reason != "PRESENT_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT")):
            identity_review = None
        return {
            "status": "RESEARCH_ONLY",
            "historical_staged": staged,
            "published_crl_source": letter_source,
            "approved_registry_source": drug_source,
            "fda_identity_crosswalk": identity_links,
            "fda_repeat_letter_triage": repeat_letters,
            "fda_identity_review_queue": identity_review,
            "historical_quarantined": quarantined,
            "historical_model_eligible": 0,
            "historical_training_data_connected": False,
            "model_validated": False,
            "prediction_probability": None,
            "prediction_available": False,
            "message": "Staged evidence is not validated training data.",
        }
    except (OSError, ValueError, KeyError, TypeError):
        return {
            "status": "SOURCE_UNAVAILABLE",
            "historical_staged": None,
            "published_crl_source": None,
            "approved_registry_source": None,
            "fda_identity_crosswalk": None,
            "fda_repeat_letter_triage": None,
            "fda_identity_review_queue": None,
            "historical_quarantined": None,
            "historical_model_eligible": 0,
            "historical_training_data_connected": False,
            "model_validated": False,
            "prediction_probability": None,
            "prediction_available": False,
            "message": "HOP source status unavailable; no prediction can be issued.",
        }

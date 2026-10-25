"""Read-only HOP readiness status from committed research sources.

No database writes, model fitting, scanner scheduling, or probability output.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from .hop_fda_filing_benchmarks import audit_fda_filing_benchmarks

STAGING_PATH = Path(__file__).parent / "research_sources" / "hop_fda_outcome_staging.json"
SOURCE_AUDIT_PATH = Path(__file__).parent / "research_sources" / "hop_openfda_crl_audit_index.json"
DRUGS_SOURCE_AUDIT_PATH = Path(__file__).parent / "research_sources" / "hop_drugsfda_audit_index.json"
CROSSWALK_AUDIT_PATH = Path(__file__).parent / "research_sources" / "hop_fda_crosswalk_audit_index.json"
REPEAT_LETTER_AUDIT_PATH = Path(__file__).parent / "research_sources" / "hop_fda_repeat_letter_triage_index.json"
IDENTITY_REVIEW_AUDIT_PATH = Path(__file__).parent / "research_sources" / "hop_fda_identity_review_queue_index.json"
OFFICIAL_PDF_AUDIT_PATH = Path(__file__).parent / "research_sources" / "hop_fda_pdf_document_verification_index.json"
FILING_BENCHMARK_PATH = Path(__file__).parent / "research_sources" / "hop_fda_pdufa_filing_benchmarks.json"
ALL_ACTION_PDF_AUDIT_PATH = Path(__file__).parent / "research_sources" / "hop_fda_full_action_pdf_audit_index.json"
SHARED_PDF_AUDIT_PATH = Path(__file__).parent / "research_sources" / "hop_fda_shared_pdf_reconciliation_index.json"
PAGE_CANDIDATE_AUDIT_PATH = Path(__file__).parent / "research_sources" / "hop_fda_shared_pdf_page_candidate_index.json"


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


def _quarantined_official_pdf_document_audit(path: Path) -> dict | None:
    """HTTP-confirmed FDA PDF bytes are NOT verified regulatory action dates."""
    try:
        src = json.loads(path.read_text(encoding="utf-8"))
        total = src["total_identity_review_cases"]
        confirmed = src["official_pdf_bytes_confirmed"]
        unreleased = src["no_safe_filename_to_check"]
        checks = (
            total, confirmed, unreleased,
            src["document_identity_adjudicated"],
            src["effective_action_dates_independently_verified"],
            src["review_cycle_outcomes_independently_verified"],
            src["model_eligible_records"],
        )
        if (src.get("status") != "OFFICIAL_PDF_BYTES_CONFIRMED_NOT_ACTION_DATES_VERIFIED"
                or any(type(n) is not int or n < 0 for n in checks)
                or total < 1 or confirmed + unreleased != total
                or src["document_identity_adjudicated"] != 0
                or src["effective_action_dates_independently_verified"] != 0
                or src["review_cycle_outcomes_independently_verified"] != 0
                or src["model_eligible_records"] != 0
                or src.get("complete_application_denominator_verified") is not False
                or src.get("prediction_probability") is not None
                or not re.fullmatch(r"[0-9a-f]{64}",
                                    src["no_safe_filename_source_record_sha256"])
                or src["no_safe_filename_as_published"] != "Under Review for Release"):
            raise ValueError("FDA PDF availability audit cannot validate model outcomes")
        return {
            "status": "SOURCE_PDFS_CHECKED_NOT_REGULATORY_OUTCOMES_VERIFIED",
            "source_export_date": src["fda_letter_export_date"],
            "identity_review_cases_checked": total,
            "official_pdf_bytes_confirmed": confirmed,
            "source_records_without_pdf_filename": unreleased,
            "source_record_unreleased": src["no_safe_filename_source_record_sha256"],
            "collection_run_url": src["collection_workflow_run"],
            "source_artifact_url": src["source_artifact_url"],
            "document_identity_adjudicated": 0,
            "effective_action_dates_independently_verified": 0,
            "review_cycle_outcomes_independently_verified": 0,
            "model_eligible_records": 0,
        }
    except (OSError, KeyError, ValueError, TypeError):
        return None


def _fda_annual_filing_reference(path: Path) -> dict | None:
    try:
        return audit_fda_filing_benchmarks(
            json.loads(path.read_text(encoding="utf-8"))
        )
    except (OSError, KeyError, ValueError, TypeError):
        return None



def _quarantined_all_fda_action_pdf_audit(path: Path) -> dict | None:
    """All public FDA letters: source PDF bytes are not FDA action labels."""
    allowed_types = {
        "COMPLETE RESPONSE", "CORRECTED PROVISIONAL DETERMINATION",
        "PROVISIONAL DETERMINATION", "REFUSAL TO FILE",
        "RESCIND COMPLETE RESPONSE", "TENTATIVE APPROVAL", "UNCLASSIFIED",
    }
    try:
        src = json.loads(path.read_text(encoding="utf-8"))
        total = src["published_letter_records"]
        verified = src["full_official_pdf_bytes_confirmed"]
        unreleased = src["source_records_without_safe_pdf_filename"]
        types = src["published_letter_type_counts"]
        if (src.get("status") != "ALL_PUBLISHED_FDA_ACTION_PDFS_QUARANTINED_NOT_VALIDATED_OUTCOMES"
                or any(type(n) is not int or n < 0 for n in (total, verified, unreleased))
                or total < 1 or verified + unreleased != total
                or not isinstance(types, dict) or set(types) != allowed_types
                or any(type(n) is not int or n < 0 for n in types.values())
                or sum(types.values()) != total
                or type(src.get("special_document_actions_requiring_prior_action_review")) is not int
                or src["special_document_actions_requiring_prior_action_review"] != (
                    types["RESCIND COMPLETE RESPONSE"]
                    + types["CORRECTED PROVISIONAL DETERMINATION"])
                or any(type(src.get(field)) is not int or src[field] != 0
                       for field in (
                           "effective_fda_action_dates_independently_verified",
                           "adjudicated_review_cycle_outcomes",
                           "clinical_predecision_evidence_verified",
                           "model_eligible_records",
                       ))
                or src.get("complete_application_denominator_verified") is not False
                or src.get("prediction_probability") is not None
                or not re.fullmatch(r"[0-9a-f]{64}",
                        src["source_record_without_released_pdf"])
                or not re.fullmatch(r"[0-9a-f]{64}",
                        src["original_fda_archive_sha256"])
                or src["source_status_without_pdf"] != "Under Review for Release"):
            raise ValueError("published FDA document audit cannot establish review-cycle outcomes")
        return {
            "status": "OFFICIAL_SOURCE_DOCUMENTS_CHECKED_ONLY",
            "fda_source_export_date": src["official_fda_crl_export_date"],
            "published_letter_records": total,
            "official_pdf_bytes_confirmed": verified,
            "source_records_without_pdf": unreleased,
            "published_letter_type_counts": types,
            "special_actions_requiring_prior_review":
                src["special_document_actions_requiring_prior_action_review"],
            "source_collection_run_url": src["source_collection_run_url"],
            "source_collection_artifact_url": src["source_collection_artifact_url"],
            "independently_verified_effective_action_dates": 0,
            "independently_adjudicated_review_cycle_outcomes": 0,
            "model_eligible_records": 0,
            "complete_denominator_verified": False,
        }
    except (OSError, KeyError, ValueError, TypeError):
        return None


def _quarantined_shared_fda_pdf_audit(path: Path) -> dict | None:
    """PDF equality is source evidence, not independently adjudicated actions."""
    try:
        src = json.loads(path.read_text(encoding="utf-8"))
        total = src["published_letter_source_records"]
        linked = src["official_pdf_confirmed_letter_references"]
        unique = src["unique_confirmed_pdf_documents"]
        groups = src["distinct_shared_pdf_groups"]
        affected = src["letter_records_in_shared_pdf_groups"]
        extra = src["additional_letter_links_beyond_unique_pdfs"]
        cross_apps = src["shared_documents_containing_multiple_applications"]
        same_day = src["same_date_and_letter_type_collision_groups"]
        unconfirmed = src["source_records_without_confirmed_pdf"]
        missing = src["source_records_without_confirmed_pdf_sha256"]
        numbers = (total, linked, unique, groups, affected,
                   extra, cross_apps, same_day, unconfirmed)
        if (src.get("status") != "FDA_PDF_SHARED_DOCUMENT_RECONCILIATION_NOT_OUTCOME_ADJUDICATION"
                or any(type(x) is not int or x < 0 for x in numbers)
                or total < 1 or unique > linked
                or linked + unconfirmed != total
                or linked - unique != extra
                or not 0 <= groups <= unique
                or not 2 * groups <= affected <= linked
                or not 0 <= cross_apps <= groups
                or not 0 <= same_day <= groups
                or not isinstance(missing, list) or len(missing) != unconfirmed
                or any(not isinstance(digest, str)
                       or not re.fullmatch(r"[0-9a-f]{64}", digest) for digest in missing)
                or not isinstance(src.get("original_fda_archive_sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", src["original_fda_archive_sha256"])
                or any(type(src.get(k)) is not int or src[k] != 0
                       for k in ("individual_letter_page_ranges_verified",
                                 "independently_verified_fda_action_dates",
                                 "independently_verified_review_cycle_outcomes",
                                 "model_eligible_records"))
                or src.get("complete_application_denominator_verified") is not False
                or src.get("prediction_probability") is not None):
            raise ValueError("FDA shared PDF source audit does not reconcile")
        return {
            "status": "SHARED_PDF_PAGE_MAPPING_REQUIRED",
            "published_letter_records": total,
            "confirmed_pdf_references": linked,
            "distinct_verified_pdf_documents": unique,
            "shared_pdf_groups_needing_page_mapping": groups,
            "published_letter_records_in_shared_pdf_groups": affected,
            "duplicate_document_links": extra,
            "cross_application_shared_pdf_groups": cross_apps,
            "same_date_type_collision_groups": same_day,
            "source_records_without_confirmed_pdf": unconfirmed,
            "source_collection_run_url": src["source_collection_run_url"],
            "source_collection_artifact_url": src["source_collection_artifact_url"],
            "independently_verified_review_cycle_outcomes": 0,
            "model_eligible_records": 0,
            "complete_denominator_verified": False,
        }
    except (OSError, KeyError, ValueError, TypeError):
        return None


def _quarantined_fda_page_candidate_audit(path: Path) -> dict | None:
    """Automated page TEXT matches are provisional, never reviewed FDA outcomes."""
    allowed_pdf_statuses = {"PDF_TEXT_EXTRACTED"}
    allowed_letter_statuses = {
        "DATE_AND_ID_PAGE_CANDIDATES", "ID_ONLY_PAGE_CANDIDATES",
        "NO_APPLICATION_TOKEN_ON_EXTRACTED_PAGES",
        "TOO_MANY_PAGES_REQUIRE_MANUAL_REVIEW",
    }
    try:
        src = json.loads(path.read_text(encoding="utf-8"))
        groups = src["shared_pdf_groups_examined"]
        letters = src["source_letter_records_examined"]
        pdf_statuses = src["pdf_text_extraction_status_counts"]
        status = src["letter_candidate_status_counts"]
        one = src["letter_date_id_one_candidate_page_records"]
        many = src["letter_date_id_multiple_candidate_pages_records"]
        weak = src["id_only_multiple_candidate_pages_records"]
        if (src.get("status") != "FDA_SHARED_PDF_PAGE_CANDIDATES_REQUIRE_HUMAN_ADJUDICATION"
                or type(groups) is not int or groups < 1
                or type(letters) is not int or letters < 2
                or not isinstance(pdf_statuses, dict)
                or set(pdf_statuses) != allowed_pdf_statuses
                or any(type(n) is not int or n < 0 for n in pdf_statuses.values())
                or sum(pdf_statuses.values()) != groups
                or not isinstance(status, dict) or set(status) != allowed_letter_statuses
                or any(type(n) is not int or n < 0 for n in status.values())
                or sum(status.values()) != letters
                or any(type(x) is not int or x < 0 for x in (one, many, weak))
                or one + many != status["DATE_AND_ID_PAGE_CANDIDATES"]
                or weak > status["ID_ONLY_PAGE_CANDIDATES"]
                or any(type(src.get(field)) is not int or src[field] != 0
                       for field in (
                           "uniquely_independently_verified_letter_page_ranges",
                           "effective_fda_action_dates_independently_verified",
                           "independently_verified_review_cycle_outcomes",
                           "model_eligible_records",
                       ))
                or src.get("complete_application_denominator_verified") is not False
                or src.get("prediction_probability") is not None
                or not isinstance(src.get("source_archive_sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", src["source_archive_sha256"])):
            raise ValueError("FDA PDF page matches are not verified regulatory outcomes")
        return {
            "status": "PROVISIONAL_PDF_PAGE_MATCHES_NEED_INDEPENDENT_REVIEW",
            "shared_pdf_documents_text_indexed": groups,
            "published_letter_records_page_searched": letters,
            "strong_same_page_id_and_date_candidates": status["DATE_AND_ID_PAGE_CANDIDATES"],
            "strong_cases_with_only_one_candidate_page": one,
            "strong_cases_with_multiple_candidate_pages": many,
            "id_only_page_candidates": status["ID_ONLY_PAGE_CANDIDATES"],
            "no_application_token_found": status["NO_APPLICATION_TOKEN_ON_EXTRACTED_PAGES"],
            "too_many_matching_pages_to_narrow": status["TOO_MANY_PAGES_REQUIRE_MANUAL_REVIEW"],
            "source_collection_run_url": src["source_collection_run_url"],
            "source_collection_artifact_url": src["source_collection_artifact_url"],
            "independently_verified_page_ranges": 0,
            "independently_verified_regulatory_outcomes": 0,
            "model_eligible_records": 0,
            "complete_denominator_verified": False,
        }
    except (OSError, KeyError, ValueError, TypeError):
        return None

def hop_readiness_status(path: Path = STAGING_PATH, source_audit_path: Path = SOURCE_AUDIT_PATH,
                         drugs_audit_path: Path = DRUGS_SOURCE_AUDIT_PATH,
                         crosswalk_audit_path: Path = CROSSWALK_AUDIT_PATH,
                         repeat_letter_audit_path: Path = REPEAT_LETTER_AUDIT_PATH,
                         identity_review_audit_path: Path = IDENTITY_REVIEW_AUDIT_PATH,
                         official_pdf_audit_path: Path = OFFICIAL_PDF_AUDIT_PATH,
                         filing_benchmark_path: Path = FILING_BENCHMARK_PATH,
                         all_action_pdf_audit_path: Path = ALL_ACTION_PDF_AUDIT_PATH,
                         shared_pdf_audit_path: Path = SHARED_PDF_AUDIT_PATH,
                         page_candidate_audit_path: Path = PAGE_CANDIDATE_AUDIT_PATH) -> dict:
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
        source_pdfs = _quarantined_official_pdf_document_audit(official_pdf_audit_path)
        if source_pdfs and (not identity_review
                or source_pdfs["identity_review_cases_checked"] != identity_review[
                    "identity_review_queue_records"]):
            source_pdfs = None
        all_published_pdfs = _quarantined_all_fda_action_pdf_audit(all_action_pdf_audit_path)
        if all_published_pdfs and (not letter_source
                or all_published_pdfs["published_letter_records"] != letter_source["published_letter_records"]):
            all_published_pdfs = None
        shared_pdfs = _quarantined_shared_fda_pdf_audit(shared_pdf_audit_path)
        if shared_pdfs and (not all_published_pdfs
                or shared_pdfs["published_letter_records"] != all_published_pdfs["published_letter_records"]
                or shared_pdfs["confirmed_pdf_references"] != all_published_pdfs["official_pdf_bytes_confirmed"]):
            shared_pdfs = None
        page_candidates = _quarantined_fda_page_candidate_audit(page_candidate_audit_path)
        if page_candidates and (not shared_pdfs
                or page_candidates["shared_pdf_documents_text_indexed"] != shared_pdfs[
                    "shared_pdf_groups_needing_page_mapping"]
                or page_candidates["published_letter_records_page_searched"] != shared_pdfs[
                    "published_letter_records_in_shared_pdf_groups"]):
            page_candidates = None
        return {
            "status": "RESEARCH_ONLY",
            "historical_staged": staged,
            "published_crl_source": letter_source,
            "approved_registry_source": drug_source,
            "fda_identity_crosswalk": identity_links,
            "fda_repeat_letter_triage": repeat_letters,
            "fda_identity_review_queue": identity_review,
            "fda_official_pdf_checks": source_pdfs,
            "fda_annual_filing_reference": _fda_annual_filing_reference(filing_benchmark_path),
            "fda_all_published_action_documents": all_published_pdfs,
            "fda_shared_pdf_source_reconciliation": shared_pdfs,
            "fda_provisional_pdf_page_candidates": page_candidates,
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
            "fda_official_pdf_checks": None,
            "fda_annual_filing_reference": None,
            "fda_all_published_action_documents": None,
            "fda_shared_pdf_source_reconciliation": None,
            "fda_provisional_pdf_page_candidates": None,
            "historical_quarantined": None,
            "historical_model_eligible": 0,
            "historical_training_data_connected": False,
            "model_validated": False,
            "prediction_probability": None,
            "prediction_available": False,
            "message": "HOP source status unavailable; no prediction can be issued.",
        }

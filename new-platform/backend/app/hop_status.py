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
        if (index.get("status") != "QUARANTINED_IDENTITY_LINKAGE_ONLY_NOT_OUTCOME_COHORT"
                or type(letters) is not int or letters < 1
                or type(registry) is not int or registry < 1
                or not isinstance(counts, dict)
                or any(type(n) is not int or n < 0 for n in counts.values())
                or sum(counts.values()) != letters
                or index.get("complete_application_denominator_verified") is not False
                or type(index.get("model_eligible_records")) is not int
                or index["model_eligible_records"] != 0
                or type(index.get("verified_review_cycle_outcomes")) is not int
                or index["verified_review_cycle_outcomes"] != 0):
            raise ValueError("FDA source linkage cannot be a validated outcome cohort")
        return {"status": "IDENTITY_MATCH_ONLY", "published_letter_records": letters,
                "approved_registry_source_application_records": registry,
                "identity_link_status_counts": counts,
                "collection_run_url": index["collection_run_url"],
                "model_eligible_records": 0, "verified_review_cycle_outcomes": 0}
    except (OSError, ValueError, TypeError, KeyError):
        return None

def hop_readiness_status(path: Path = STAGING_PATH, source_audit_path: Path = SOURCE_AUDIT_PATH,
                         drugs_audit_path: Path = DRUGS_SOURCE_AUDIT_PATH,
                         crosswalk_audit_path: Path = CROSSWALK_AUDIT_PATH) -> dict:
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
        return {
            "status": "RESEARCH_ONLY",
            "historical_staged": staged,
            "published_crl_source": letter_source,
            "approved_registry_source": drug_source,
            "fda_identity_crosswalk": identity_links,
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
            "historical_quarantined": None,
            "historical_model_eligible": 0,
            "historical_training_data_connected": False,
            "model_validated": False,
            "prediction_probability": None,
            "prediction_available": False,
            "message": "HOP source status unavailable; no prediction can be issued.",
        }

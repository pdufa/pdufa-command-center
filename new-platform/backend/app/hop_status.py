"""Read-only HOP readiness status from committed research sources.

No database writes, model fitting, scanner scheduling, or probability output.
"""
from __future__ import annotations
import json
from pathlib import Path

STAGING_PATH = Path(__file__).parent / "research_sources" / "hop_fda_outcome_staging.json"
SOURCE_AUDIT_PATH = Path(__file__).parent / "research_sources" / "hop_openfda_crl_audit_index.json"


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


def hop_readiness_status(path: Path = STAGING_PATH, source_audit_path: Path = SOURCE_AUDIT_PATH) -> dict:
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
        return {
            "status": "RESEARCH_ONLY",
            "historical_staged": staged,
            "published_crl_source": _published_letter_source_audit(source_audit_path),
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
            "historical_quarantined": None,
            "historical_model_eligible": 0,
            "historical_training_data_connected": False,
            "model_validated": False,
            "prediction_probability": None,
            "prediction_available": False,
            "message": "HOP source status unavailable; no prediction can be issued.",
        }

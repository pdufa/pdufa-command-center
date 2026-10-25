"""Read-only HOP readiness status from committed research sources.

No database writes, model fitting, scanner scheduling, or probability output.
"""
from __future__ import annotations
import json
from pathlib import Path

STAGING_PATH = Path(__file__).parent / "research_sources" / "hop_fda_outcome_staging.json"

def hop_readiness_status(path: Path = STAGING_PATH) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        records = raw["records"]
        if not isinstance(records, list):
            raise ValueError("records must be a list")
        staged = len(records)
        # Every staging record is quarantined regardless of a caller-supplied\n        # eligibility flag; staging cannot promote observations into training.\n        quarantined = staged
        # Staging is *never* a model-eligible source, even if a flag changes.
        return {
            "status": "RESEARCH_ONLY",
            "historical_staged": staged,
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
            "historical_quarantined": None,
            "historical_model_eligible": 0,
            "historical_training_data_connected": False,
            "model_validated": False,
            "prediction_probability": None,
            "prediction_available": False,
            "message": "HOP source status unavailable; no prediction can be issued.",
        }

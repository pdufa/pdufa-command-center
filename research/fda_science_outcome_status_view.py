"""Read-only SCIENCE/OUTCOME provenance status for a research dashboard.

No predictions, probabilities, data mutations or production deployment.
"""
import json
from pathlib import Path
from research.fda_outcome_provenance_gate import build_outcome_provenance_status

ROOT = Path(__file__).resolve().parents[1]
RECONSTRUCTION = ROOT / "research/evidence/2025_holdout_predecision_reconstruction.json"


def build_research_status(reconstruction):
    cases = reconstruction["cases"]
    dossiers = [{"event_key": case["event_key"],
                 "research_only": True,
                 "original_prediction_cutoff": None,
                 "schema_version": "fda-science-research-dossier-v1"} for case in cases]
    result = build_outcome_provenance_status(reconstruction, dossiers)
    return {
        "schemaVersion": "fda-science-outcome-research-status-v1",
        "researchOnly": True,
        "tradingAuthorized": False,
        "validatedPredictions": result["validated_predictions"],
        "cases": [{"eventKey": row["event_key"],
                   "scienceStatus": "NOT_INDEPENDENTLY_VERIFIED",
                   "outcomeDecision": row["outcome_decision"],
                   "approvalProbability": row["approval_probability"],
                   "readyForAnalysis": row["ready_for_analysis_grade"],
                   "reluctantGrade": row["reluctant_grade"],
                   "blockers": row["science_provenance_blockers"]}
                  for row in result["cases"]],
    }


if __name__ == "__main__":
    print(json.dumps(build_research_status(json.loads(RECONSTRUCTION.read_text())), indent=2))

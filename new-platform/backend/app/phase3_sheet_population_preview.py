"""Read-only, source-safe preview for eventual PDUFA sheet population.

Only verified eligible trials may appear as analysis-ready. This does not
write to Google Sheets or generate unvalidated model results.
"""
from __future__ import annotations

def build_sheet_population_preview(batch: dict) -> dict:
    if not isinstance(batch, dict) or not isinstance(batch.get("rows"), list):
        raise ValueError("Validated batch output required")
    preview = []
    for item in batch["rows"]:
        gate = (item.get("analysis") or {}).get("gate") or {}
        if not item.get("deepAnalysisEligible") or not gate.get("deepAnalysisEligible"):
            continue
        science = item["analysis"].get("science")
        if not isinstance(science, dict):
            continue
        preview.append({
            "trialExactKey": item["exactKey"],
            "asOf": item["asOf"],
            "pdufaTargetDate": gate["pdufaTargetDate"],
            "phase3ResultsVerified": gate["phase3ResultsVerified"],
            "pdufaDateVerified": gate["pdufaDateVerified"],
            "scienceReviewedItems": science["reviewed"],
            "scienceRequiredItems": science["required"],
            "scienceEvidenceCoveragePercent": science["evidenceCoveragePercent"],
            "readinessGrade": "NOT ASSESSED",
            "approvalProbability": None,
            "independentConclusion": None,
        })
    return {"schemaVersion":"pdufa-sheet-preview-v1","mode":"PREVIEW_ONLY",
            "requiresManualSourceReview":True,"rows":preview,"writtenToSheet":False}

"""Read-only batch bridge from existing Pipeline exports into research triage.

Never modifies Pipeline, GEM JR, GEM, WT, FS/FA presets, or source records.
The export is caller-supplied and cannot establish authenticity by itself.
"""
from research.preliminary_candidate_scope import preliminary_candidate_scope


def triage_pipeline_export(rows):
    if not isinstance(rows, list):
        raise ValueError("pipeline export must be a list")
    if len(rows) > 10000:
        raise ValueError("pipeline export exceeds 10000 rows")
    output = []
    seen = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError("each pipeline record must be an object")
        key = row.get("program_id")
        if not isinstance(key, str) or not key.strip() or key != key.strip():
            raise ValueError("each record needs a stable program_id")
        if key in seen:
            raise ValueError("duplicate program_id in pipeline export")
        seen.add(key)
        result = preliminary_candidate_scope(row)
        output.append({"program_id": key, **result})
    return {
        "records": output,
        "total": len(output),
        "candidate_for_evidence_review": sum(
            r["scope"] == "CANDIDATE_FOR_EVIDENCE_REVIEW" for r in output),
        "blocked": sum(r["scope"] != "CANDIDATE_FOR_EVIDENCE_REVIEW" for r in output),
        "prediction_status": "ABSTAIN",
        "research_only": True,
        "data_authenticity_verified": False,
    }

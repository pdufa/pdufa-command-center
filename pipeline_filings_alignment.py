"""Keep SEC/FDA baseline counts tied to the Pipeline chart's exact record IDs.

The Pipeline contains registered NCT trials, published results, and regulatory
application events. A filing or claim is not another trial. Only an exact
APPLICATION|event_key may inherit the existing candidate-specific evidence.
"""
from __future__ import annotations

from pipeline_display import DATE_BANDS, filter_pipeline, prepare_pipeline
from pipeline_universe import STAGES


def pipeline_scope(universe, session, today):
    """Use the exact stage/date/search predicates used by the Pipeline charts."""
    stage_filters = list(session.get("pipeline_stages_v9") or [])
    date_filters = list(session.get("pipeline_dates_v9") or [])
    query = str(session.get("pipeline_query_v9") or "").strip()
    chosen = filter_pipeline(
        prepare_pipeline(universe, today),
        stage_filters or list(STAGES),
        date_filters or list(DATE_BANDS),
        query,
    )
    signature = (
        tuple(stage_filters), tuple(date_filters), query,
        session.get("pipeline_sort_v9"),
    )
    displayed = bool(stage_filters and date_filters
                     and session.get("pipeline_applied_v9") == signature)
    # The Pipeline chart counts reflect filters even before the user presses SHOW.
    return chosen, {
        "universe_total": len(universe),
        "chart_total": len(chosen),
        "display_total": len(chosen) if displayed else 0,
        "table_applied": displayed,
    }


def align_baseline(pipeline_records, candidate_baseline):
    """Exactly one baseline row per Pipeline record; never join on ticker alone.

    Registered trials, results and application events can legitimately share
    the same ticker. Candidate SEC/FDA verification is associated only with
    APPLICATION|event_key, never a TRIAL|NCT... or RESULT|... row.
    """
    candidates = {
        str(row.get("Trial / event") or "").strip(): row
        for row in candidate_baseline
        if str(row.get("Trial / event") or "").strip()
    }
    seen = set()
    aligned = []
    for item in pipeline_records:
        record_id = str(item.get("record_id") or "").strip()
        if not record_id or record_id in seen:
            raise ValueError("Pipeline records must have distinct nonempty record_id values")
        seen.add(record_id)
        key = record_id[len("APPLICATION|"):] if record_id.startswith("APPLICATION|") else ""
        source = candidates.get(key) if key else None
        row = {
            "Pipeline ID": record_id,
            "Record Type": item.get("record_type", ""),
            "Pipeline stage": item.get("current_stage", ""),
            "Ticker": item.get("ticker", ""),
            "Trial / event": key or record_id,
            "Drug": item.get("drug", ""),
            "Trial NCT": item.get("nct_id", ""),
            "Pipeline source": item.get("source_url", ""),
            "Agency verification": "NOT_CHECKED",
            "Agency claim": "NOT_ASSESSED_FOR_THIS_PIPELINE_RECORD",
            "Agency source": "",
            "Research gaps": "SOURCE_CLAIM_NOT_ASSESSED_IN_CANDIDATE_SCAN",
            "GEM eligibility": "NOT CERTIFIED",
            "Reconciliation": "PIPELINE_ONLY — NO EXACT APPLICATION MATCH",
        }
        if source is not None:
            # Only the matched application inherits candidate-specific evidence.
            row.update(source)
            row["Pipeline ID"] = record_id
            row["Record Type"] = item.get("record_type", "")
            row["Pipeline stage"] = item.get("current_stage", "")
            row["Pipeline source"] = item.get("source_url", "")
            row["Reconciliation"] = "EXACT APPLICATION EVENT MATCH"
            row["Trial NCT"] = source.get("Trial NCT") or item.get("nct_id", "")
        aligned.append(row)
    if len(aligned) != len(pipeline_records):
        raise ValueError("Pipeline baseline row count diverged from source records")
    return aligned


def reconciliation_counts(records):
    return {
        "matched": sum(row["Reconciliation"] == "EXACT APPLICATION EVENT MATCH" for row in records),
        "unassessed": sum(row["Reconciliation"] != "EXACT APPLICATION EVENT MATCH" for row in records),
    }

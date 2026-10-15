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
        ticker_matches = (
            source is not None and
            str(source.get("Ticker") or "").strip().upper() ==
            str(item.get("ticker") or "").strip().upper()
        )
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
        if ticker_matches:
            # Only exact ID + ticker matches inherit candidate-specific evidence.
            row.update(source)
            row["Pipeline ID"] = record_id
            row["Record Type"] = item.get("record_type", "")
            row["Pipeline stage"] = item.get("current_stage", "")
            row["Pipeline source"] = item.get("source_url", "")
            row["Ticker"] = item.get("ticker", "")
            row["Drug"] = item.get("drug", "")
            row["Reconciliation"] = "EXACT APPLICATION EVENT MATCH"
            row["Trial NCT"] = source.get("Trial NCT") or item.get("nct_id", "")
        elif source is not None:
            row["Reconciliation"] = "TICKER CONFLICT — SOURCE EVIDENCE WITHHELD"
        aligned.append(row)
    if len(aligned) != len(pipeline_records):
        raise ValueError("Pipeline baseline row count diverged from source records")
    return aligned


def reconciliation_counts(records):
    return {
        "matched": sum(row["Reconciliation"] == "EXACT APPLICATION EVENT MATCH" for row in records),
        "unassessed": sum(row["Reconciliation"] != "EXACT APPLICATION EVENT MATCH" for row in records),
    }



def candidate_events_outside_pipeline(pipeline_records, candidate_baseline):
    """Report orphan candidate events; filters must not manufacture 'orphans'."""
    by_pipeline_id = {
        str(row.get("record_id") or "").strip(): row
        for row in pipeline_records
    }
    orphaned = []
    seen = set()
    for item in candidate_baseline:
        key = str(item.get("Trial / event") or "").strip()
        if not key or key in seen:
            continue
        identifier = "APPLICATION|" + key
        # A key exists but the issuer may disagree. Report the conflict.
        identity_row = by_pipeline_id.get(identifier)
        present = identity_row is not None
        ticker_matches = (
            identity_row is not None and
            str(identity_row.get("ticker") or "").strip().upper() ==
            str(item.get("Ticker") or "").strip().upper()
        )
        if present and ticker_matches:
            continue
        seen.add(key)
        orphaned.append({
            "Ticker": item.get("Ticker", ""),
            "Candidate event": key,
            "Agency claim": item.get("Agency claim", ""),
            "Agency verification": item.get("Agency verification", ""),
            "Agency source": item.get("Agency source", ""),
            "Reconciliation": (
                "TICKER CONFLICT — EXACT PIPELINE ID" if present else
                "CANDIDATE NOT IN CURRENT PIPELINE UNIVERSE"
            ),
        })
    return orphaned


def scope_evidence_tables(tables, pipeline_records):
    """Show issuer filings or application claims only within the Pipeline view.

    SEC forms are issuer-level and may relate to multiple trial programs;
    filtering by ticker must never count them as trial-specific verification.
    FDA claims/extensions instead require exact APPLICATION|event keys.
    """
    ids = {str(row.get("record_id") or "").strip() for row in pipeline_records}
    tickers = {str(row.get("ticker") or "").strip().upper()
               for row in pipeline_records if str(row.get("ticker") or "").strip()}
    scoped = {}
    for name, items in tables.items():
        output = []
        for row in items:
            if name.startswith("SEC"):
                if str(row.get("Ticker") or "").strip().upper() not in tickers:
                    continue
                output.append({**row, "Scope": "Pipeline issuer — filing, not trial proof"})
            else:
                event = str(row.get("Trial / event") or "").strip()
                pipeline_id = "APPLICATION|" + event
                if pipeline_id not in ids:
                    continue
                output.append({**row, "Pipeline ID": pipeline_id})
        scoped[name] = output
    return scoped


def scope_research_queue(queue, pipeline_records):
    """No independent source-review event outside the current Pipeline view."""
    ids = {str(row.get("record_id") or "").strip() for row in pipeline_records}
    tickers = {str(row.get("ticker") or "").strip().upper()
               for row in pipeline_records if str(row.get("ticker") or "").strip()}
    result = []
    for row in queue:
        event = str(row.get("event_key") or "").strip()
        ticker = str(row.get("ticker") or "").strip().upper()
        linked = (
            ("APPLICATION|" + event in ids)
            or (event.startswith("REGISTRY:") and ticker in tickers)
            or (event in ids)
        )
        if linked:
            result.append(row)
    return result

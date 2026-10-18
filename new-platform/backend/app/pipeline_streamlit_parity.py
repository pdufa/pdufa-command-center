"""Exact Pipeline *universe and current stage* parity with Streamlit/main.

Mirrors pipeline_universe.py build_universe() using only Python stdlib.
In particular: two published clinical files are complementary evidence about
the SAME NCT, not competing duplicate keys to quarantine. Announcements without
NCT identifiers remain separate RESULT|SHA keys. Streamlit data and its
identities are read-only; existing Neon Program IDs are never recycled.

Keep stage/date counts based on a unique source record ID, never one count per
source CSV row, one per ticker, or one per historic stage tag.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date

STAGES = (
    "Early Phase 1", "Phase 1", "Phase 1/2", "Phase 2", "Phase 2/3",
    "Phase 3", "Phase 3 Results", "NDA/BLA Submission", "FDA Acceptance",
    "PDUFA Decision", "Post-Decision", "Phase 4", "Not Applicable", "Unknown",
)
_NCT = re.compile(r"^NCT\d{8}$")
_COLUMNS = (
    "record_id", "record_type", "ticker", "company", "drug", "indication", "nct_id",
    "intervention_type", "route", "drug_modality", "drug_class",
    "mechanism_target", "use_status", "classification_status",
    "classification_source_url", "classification_note", "registered_phase",
    "current_stage", "stage_tags", "status", "start_date",
    "primary_completion", "study_completion", "results_posted",
    "nda_submission_date", "fda_acceptance_date", "pdufa_date",
    "decision_date", "outcome", "source_updated", "checked_at",
    "evidence_status", "evidence_note", "source_url",
)


def clean(v) -> str:
    x = str(v or "").strip()
    return "" if x.lower() in ("nan", "nat", "<na>", "none") else x


def dated(v):
    try:
        return date.fromisoformat(clean(v)[:10])
    except ValueError:
        return None


def posted(v, today: date) -> bool:
    day = dated(v)
    return day is not None and day <= today


def linked(v) -> bool:
    return clean(v).startswith(("https://", "http://"))


def phase_label(value: str) -> str:
    raw = clean(value).upper().replace(" ", "")
    tokens = set(filter(None, re.split(r"[|,/]", raw)))
    if tokens == {"PHASE1", "PHASE2"}:
        return "Phase 1/2"
    if tokens == {"PHASE2", "PHASE3"}:
        return "Phase 2/3"
    return {
        "EARLY_PHASE1": "Early Phase 1", "PHASE1": "Phase 1",
        "PHASE2": "Phase 2", "PHASE3": "Phase 3", "PHASE4": "Phase 4",
        "NA": "Not Applicable",
    }.get(raw, "Unknown")


def _trial_raw(source: dict) -> dict:
    row = {key: "" for key in _COLUMNS}
    row.update({key: clean(source.get(key)) for key in _COLUMNS if key in source})
    row["record_id"] = "TRIAL|" + clean(source.get("nct_id")).upper()
    row["record_type"] = "Registered trial"
    row["nct_id"] = clean(source.get("nct_id")).upper()
    row["registered_phase"] = phase_label(source.get("phase") or source.get("phases"))
    row["status"] = clean(source.get("status") or source.get("trial_status"))
    row["results_posted"] = clean(source.get("results_posted") or source.get("results_first_posted"))
    row["evidence_status"] = "SOURCE RECORDED"
    row["evidence_note"] = clean(source.get("program_identity_status"))
    return row


def _merge_original_rows(first: dict, second: dict) -> dict:
    """Identical preferential overwrite to pipeline_universe.build_universe."""
    newer, older = second, first
    if clean(newer.get("checked_at")) < clean(older.get("checked_at")):
        older, newer = newer, older
    return {key: clean(newer.get(key)) or clean(older.get(key)) for key in _COLUMNS}


def _result_key(source: dict) -> str:
    nct = clean(source.get("nct_id")).upper()
    if _NCT.fullmatch(nct):
        return "TRIAL|" + nct
    digest = hashlib.sha256("|".join(
        clean(source.get(k)) for k in (
            "ticker", "drug", "phase3_results_posted_at", "phase3_results_source"
        )
    ).encode("utf-8")).hexdigest()[:24]
    return "RESULT|" + digest


def _regulatory_id(source: dict) -> str:
    event_key = clean(source.get("event_key"))
    if event_key:
        return "APPLICATION|" + event_key
    basis = "|".join(clean(source.get(key)) for key in
                     ("ticker", "drug", "indication", "pdufa_date"))
    return "APPLICATION|" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:24]


def _regulatory_tags(row: dict, today: date) -> set[str]:
    """Mirrors Streamlit's evidence-only milestone and actual-outcome tagging."""
    tags = set()
    source = next((clean(row.get(key)) for key in (
        "pdufa_evidence_url", "fda_source_note", "trial_evidence_url"
    ) if linked(row.get(key))), "")
    notes = " ".join(clean(row.get(key)) for key in
                     ("regulatory_summary", "evidence_summary"))
    accepted = posted(row.get("fda_acceptance_date"), today) or (
        linked(source) and bool(re.search(
            r"\bFDA\s+(?:has\s+)?accepted\b[^.!?]{0,180}\b(?:s?NDA|s?BLA|application)\b",
            notes, re.I,
        )))
    submitted = posted(row.get("nda_submission_date"), today) or (
        linked(source) and bool(re.search(
            r"\b(?:s?NDA|s?BLA|new drug application|biologics license application)"
            r"\s+(?:(?:has been|was|is)\s+)?(?:re)?submitted\b",
            notes, re.I,
        )))
    if accepted:
        tags.update(("FDA Acceptance", "NDA/BLA Submission"))
    elif submitted:
        tags.add("NDA/BLA Submission")
    if linked(row.get("trial_evidence_url")) and posted(row.get("phase3_date"), today):
        tags.add("Phase 3 Results")
    outcome = clean(row.get("outcome") or row.get("actual_outcome")
                    or row.get("actual_fda_decision")).upper()
    decision = dated(row.get("decision_date"))
    if outcome in {"APPROVED", "CRL", "REJECTED", "WITHDRAWN"} and (
            decision is None or decision <= today):
        tags.add("Post-Decision")
    elif dated(row.get("pdufa_date")):
        tags.add("PDUFA Decision")
    if not tags:
        tags.add("Unknown")
    return tags


def original_pipeline_universe(rows: dict[str, list[dict]], today: date) -> dict[str, dict]:
    """Return precisely one record per original Streamlit record_id.

    Payload's source_data holds the richest source fields for research panels,
    and stage/source evidence are from the original Streamlit merge policy.
    """
    result: dict[str, dict] = {}
    metadata: dict[str, dict] = {}
    for source in rows.get("phase_pipeline.csv", []) + rows.get("all_phase_trials.csv", []):
        nct = clean(source.get("nct_id")).upper()
        if not _NCT.fullmatch(nct):
            continue
        row = _trial_raw(source)
        key = row["record_id"]
        if key in result:
            result[key] = _merge_original_rows(result[key], row)
            previous = metadata.get(key, {})
            newer, older = source, previous
            if clean(newer.get("checked_at")) < clean(older.get("checked_at")):
                newer, older = older, newer
            metadata[key] = {**older, **{k: v for k, v in newer.items() if clean(v)}}
        else:
            result[key] = row
            metadata[key] = dict(source)
    for key, row in result.items():
        tags = {row["registered_phase"]}
        if ("3" in row["registered_phase"] and posted(row.get("results_posted"), today)
                and linked(row.get("source_url"))):
            tags.add("Phase 3 Results")
        row["stage_tags"] = tuple(s for s in STAGES if s in tags)
        row["current_stage"] = "Phase 3 Results" if "Phase 3 Results" in tags else row["registered_phase"]

    # Streamlit accepts a published announcement as another source for the
    # SAME exact trial, never a duplicate counted program.
    for announcement in rows.get("phase3_announcements.csv", []):
        stamp = announcement.get("phase3_results_posted_at")
        url = announcement.get("phase3_results_source")
        if not posted(stamp, today) or not linked(url):
            continue
        nct = clean(announcement.get("nct_id")).upper()
        key = _result_key(announcement)
        row = result.get(key)
        if row is not None and clean(row.get("ticker")) != clean(announcement.get("ticker")):
            key += "|" + clean(announcement.get("ticker"))
            row = result.get(key)
        if row is None:
            row = {k: "" for k in _COLUMNS}
            for k in ("ticker", "company", "drug", "indication"):
                row[k] = clean(announcement.get(k))
            row.update(record_id=key,
                       record_type="Registered result" if _NCT.fullmatch(nct) else "Result announcement",
                       nct_id=nct, source_url=url, stage_tags=())
            metadata[key] = dict(announcement)
        tags = set(row["stage_tags"]) - {"Unknown"}
        tags.add("Phase 3 Results")
        row.update(
            current_stage="Phase 3 Results",
            stage_tags=tuple(s for s in STAGES if s in tags),
            results_posted=clean(stamp),
            evidence_status=clean(announcement.get("verification_status")) or "REVIEW",
            evidence_note=clean(announcement.get("source_list_note")),
            checked_at=clean(announcement.get("last_checked_at")) or clean(row.get("checked_at")),
        )
        result[key] = row

    # Historical first, then FDA review, then PDUFA candidates exactly as
    # Streamlit's historical + regulatory event enrichment does.
    events: dict[str, dict] = {}
    for source in (
        rows.get("prediction_engine_history.csv", []) +
        rows.get("fda_review_engine.csv", []) +
        rows.get("pdufa_candidates.csv", [])
    ):
        key = _regulatory_id(source)
        old = events.get(key, {})
        events[key] = {**old, **{k: clean(v) for k, v in source.items() if clean(v)}}
    for key, source in events.items():
        row = {column: clean(source.get(column)) for column in _COLUMNS}
        tags = _regulatory_tags(source, today)
        src = next((clean(source.get(k)) for k in (
            "pdufa_evidence_url", "fda_source_note", "trial_evidence_url"
        ) if linked(source.get(k))), "")
        outcome = clean(source.get("outcome") or source.get("actual_outcome")
                        or source.get("actual_fda_decision")).upper()
        row.update(
            record_id=key, record_type="Regulatory program / event",
            stage_tags=tuple(s for s in STAGES if s in tags),
            source_url=src, outcome=outcome,
            evidence_status="REVIEW / RECORDED",
            evidence_note=clean(source.get("evidence_summary") or source.get("regulatory_summary")),
            checked_at=clean(source.get("last_checked") or source.get("fda_last_evaluated_at")),
            current_stage=next((s for s in (
                "Post-Decision", "PDUFA Decision", "FDA Acceptance",
                "NDA/BLA Submission", "Phase 3 Results"
            ) if s in tags), "Unknown"),
        )
        if not row["drug"]:
            parts = clean(source.get("event_key")).split("|")
            if len(parts) >= 3 and dated(parts[1]):
                row["drug"] = "|".join(parts[2:])
        result[key] = row
        metadata[key] = dict(source)

    return {
        key: {**metadata.get(key, {}), **record,
              "id": key, "recordType": record["record_type"],
              "registeredPhase": record["registered_phase"],
              "stage": record["current_stage"],
              "stageTags": list(record.get("stage_tags") or []),
              "pdufa_date": record["pdufa_date"],
              "nct_id": record["nct_id"],
              "results_posted": record["results_posted"],
              "status": record["status"],
              "source_url": record["source_url"],
              "evidenceStatus": record["evidence_status"],
              "evidenceNote": record["evidence_note"]}
        for key, record in result.items()
    }

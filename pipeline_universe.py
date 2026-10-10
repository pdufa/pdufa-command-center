"""Source-preserving clinical and regulatory records for the Pipeline view."""
import csv
import hashlib
import re
from datetime import date
from pathlib import Path
import pandas as pd

STAGES = (
    "Early Phase 1", "Phase 1", "Phase 1/2", "Phase 2", "Phase 2/3",
    "Phase 3", "Phase 3 Results", "NDA/BLA Submission", "FDA Acceptance",
    "PDUFA Decision", "Post-Decision", "Phase 4", "Not Applicable", "Unknown",
)
SOURCE_FILES = (
    "all_phase_trials.csv", "phase_pipeline.csv", "phase3_announcements.csv",
    "pdufa_candidates.csv", "prediction_engine_history.csv", "fda_review_engine.csv",
    "drug_metadata.csv",
)
COLUMNS = (
    "record_id", "record_type", "ticker", "company", "drug", "indication", "nct_id",
    "intervention_type", "route", "drug_modality", "drug_class", "mechanism_target",
    "use_status", "classification_status", "classification_source_url", "classification_note",
    "registered_phase", "current_stage", "stage_tags", "status", "start_date",
    "primary_completion", "study_completion", "results_posted", "nda_submission_date",
    "fda_acceptance_date", "pdufa_date", "decision_date", "outcome", "source_updated",
    "checked_at", "evidence_status", "evidence_note", "source_url",
)

def clean(value):
    if value is None:
        return ""
    value = str(value).strip()
    return "" if value.lower() in {"nan", "nat", "<na>", "none"} else value

def dated(value):
    try:
        return date.fromisoformat(clean(value)[:10])
    except ValueError:
        return None

def posted(value, today):
    parsed = dated(value)
    return parsed is not None and parsed <= today

def linked(value):
    return clean(value).startswith(("https://", "http://"))

def phase_label(value):
    raw = clean(value).upper().replace(" ", "")
    tokens = set(filter(None, re.split(r"[|,/]", raw)))
    if tokens == {"PHASE1", "PHASE2"}:
        return "Phase 1/2"
    if tokens == {"PHASE2", "PHASE3"}:
        return "Phase 2/3"
    labels = {"EARLY_PHASE1": "Early Phase 1", "PHASE1": "Phase 1",
              "PHASE2": "Phase 2", "PHASE3": "Phase 3", "PHASE4": "Phase 4",
              "NA": "Not Applicable"}
    return labels.get(raw, "Unknown")

def read_rows(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [{key: clean(value) for key, value in row.items()}
                for row in csv.DictReader(handle)]

REGISTRY_MODALITY = {
    "DRUG": "Drug (registry; molecular modality not specified)",
    "BIOLOGICAL": "Biologic / biological (registry)",
    "DEVICE": "Device",
    "DIETARY_SUPPLEMENT": "Dietary supplement",
    "BEHAVIORAL": "Behavioral intervention",
    "RADIATION": "Radiation",
    "GENETIC": "Genetic intervention",
    "OTHER": "Other intervention",
}

CLASSIFICATION_COLUMNS = (
    "drug_modality", "drug_class", "mechanism_target", "route", "use_status",
    "classification_source_url", "classification_note",
)

def normalized(value):
    return re.sub(r"[^a-z0-9]+", " ", clean(value).lower()).strip()

def metadata_aliases(value):
    return [normalized(alias) for alias in clean(value).split("|") if normalized(alias)]

def apply_drug_metadata(records, metadata=()):
    prepared = []
    for item in metadata or ():
        aliases = metadata_aliases(item.get("drug_alias"))
        if not aliases:
            continue
        prepared.append((item, aliases))
    for row in records:
        ticker = normalized(row.get("ticker"))
        drug = normalized(row.get("drug"))
        matches = [
            (item, aliases)
            for item, aliases in prepared
            if normalized(item.get("ticker")) == ticker
            and any(alias and alias in drug for alias in aliases)
        ]
        match = max(
            matches,
            key=lambda pair: max(len(alias) for alias in pair[1]),
            default=None,
        )
        if match is not None:
            item, _ = match
            for column in CLASSIFICATION_COLUMNS:
                value = clean(item.get(column))
                if value and (column != "route" or not clean(row.get("route"))):
                    row[column] = value
            row["classification_status"] = clean(
                item.get("classification_status")
            ) or "SOURCE CLASSIFIED"
        else:
            intervention_types = [
                clean(value).upper()
                for value in clean(row.get("intervention_type")).split("|")
                if clean(value)
            ]
            if not clean(row.get("drug_modality")) and intervention_types:
                row["drug_modality"] = " / ".join(
                    REGISTRY_MODALITY.get(value, value.title())
                    for value in intervention_types
                )
            row["classification_status"] = (
                "REGISTRY PARTIAL" if intervention_types else "NOT CLASSIFIED"
            )
    return records

def base():
    return {column: "" for column in COLUMNS}

def event_id(row):
    if clean(row.get("event_key")):
        return "APPLICATION|" + clean(row["event_key"])
    parts = [clean(row.get(key)) for key in ("ticker", "drug", "indication", "pdufa_date")]
    return "APPLICATION|" + hashlib.sha256("|".join(parts).encode()).hexdigest()[:24]

def regulatory_tags(row, today):
    """Use recorded milestones/outcomes; predictions and elapsed targets are not outcomes."""
    tags = set()
    source = next((clean(row.get(key)) for key in
                   ("pdufa_evidence_url", "fda_source_note", "trial_evidence_url")
                   if linked(row.get(key))), "")
    notes = " ".join(clean(row.get(key)) for key in ("regulatory_summary", "evidence_summary"))
    accepted = posted(row.get("fda_acceptance_date"), today) or (
        linked(source) and bool(re.search(
            r"\bFDA\s+(?:has\s+)?accepted\b[^.!?]{0,180}\b(?:s?NDA|s?BLA|application)\b",
            notes, re.I)))
    submitted = posted(row.get("nda_submission_date"), today) or (
        linked(source) and bool(re.search(
            r"\b(?:s?NDA|s?BLA|new drug application|biologics license application)"
            r"\s+(?:(?:has been|was|is)\s+)?(?:re)?submitted\b", notes, re.I)))
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
    return tags, source, outcome

def build_universe(clinical=(), announcements=(), regulatory=(), historical=(),
                   metadata=(), today=None):
    today = today or date.today()
    records = {}
    for source in clinical:
        nct = clean(source.get("nct_id")).upper()
        if not re.fullmatch(r"NCT\d{8}", nct):
            continue
        row = base()
        row.update({key: clean(source.get(key)) for key in COLUMNS if key in source})
        row["record_id"] = "TRIAL|" + nct
        row["record_type"] = "Registered trial"
        row["nct_id"] = nct
        row["registered_phase"] = phase_label(source.get("phase") or source.get("phases"))
        row["status"] = clean(source.get("status") or source.get("trial_status"))
        row["results_posted"] = clean(source.get("results_posted") or source.get("results_first_posted"))
        row["evidence_status"] = "SOURCE RECORDED"
        row["evidence_note"] = clean(source.get("program_identity_status"))
        old = records.get(row["record_id"])
        if old is not None:
            # Prefer the latest source check; keep older nonblank fields for continuity.
            if row["checked_at"] < old["checked_at"]:
                old, row = row, old
            row = {key: row.get(key) or old.get(key, "") for key in COLUMNS}
        records[row["record_id"]] = row
    for row in records.values():
        tags = {row["registered_phase"]}
        if "3" in row["registered_phase"] and posted(row["results_posted"], today) and linked(row["source_url"]):
            tags.add("Phase 3 Results")
        row["stage_tags"] = tuple(stage for stage in STAGES if stage in tags)
        row["current_stage"] = "Phase 3 Results" if "Phase 3 Results" in tags else row["registered_phase"]
    for source in announcements:
        stamp = source.get("phase3_results_posted_at", "")
        url = source.get("phase3_results_source", "")
        if not posted(stamp, today) or not linked(url):
            continue
        nct = clean(source.get("nct_id")).upper()
        key = "TRIAL|" + nct if re.fullmatch(r"NCT\d{8}", nct) else (
            "RESULT|" + hashlib.sha256("|".join(clean(source.get(k)) for k in
                ("ticker", "drug", "phase3_results_posted_at", "phase3_results_source")).encode()).hexdigest()[:24])
        row = records.get(key)
        if row is not None and clean(row["ticker"]) != clean(source.get("ticker")):
            key += "|" + clean(source.get("ticker"))
            row = records.get(key)
        if row is None:
            row = base()
            row.update({key: clean(source.get(key)) for key in ("ticker", "company", "drug", "indication")})
            row.update(record_id=key, record_type="Registered result" if nct else "Result announcement",
                       nct_id=nct, source_url=url, stage_tags=())
        tags = set(row["stage_tags"]) - {"Unknown"}
        tags.add("Phase 3 Results")
        row.update(current_stage="Phase 3 Results", stage_tags=tuple(s for s in STAGES if s in tags),
                   results_posted=stamp, evidence_status=clean(source.get("verification_status")) or "REVIEW",
                   evidence_note=clean(source.get("source_list_note")), checked_at=clean(source.get("last_checked_at")) or row["checked_at"])
        records[key] = row
    # Exact event keys only; never attach an application to a trial by ticker alone.
    applications = {}
    for source in list(historical) + list(regulatory):
        key = event_id(source)
        old = applications.get(key, {})
        applications[key] = {**old, **{k: clean(v) for k, v in source.items() if clean(v)}}
    for key, source in applications.items():
        row = base()
        row.update({column: clean(source.get(column)) for column in COLUMNS if column in source})
        tags, url, outcome = regulatory_tags(source, today)
        row.update(record_id=key, record_type="Regulatory program / event",
                   stage_tags=tuple(s for s in STAGES if s in tags), source_url=url,
                   outcome=outcome, evidence_status="REVIEW / RECORDED",
                   evidence_note=clean(source.get("evidence_summary") or source.get("regulatory_summary")),
                   checked_at=clean(source.get("last_checked") or source.get("fda_last_evaluated_at")))
        if not row["drug"]:
            event = clean(source.get("event_key"))
            parts = event.split("|")
            if len(parts) >= 3 and dated(parts[1]):
                row["drug"] = "|".join(parts[2:])
        row["current_stage"] = next((s for s in (
            "Post-Decision", "PDUFA Decision", "FDA Acceptance",
            "NDA/BLA Submission", "Phase 3 Results") if s in tags), "Unknown")
        records[key] = row
    apply_drug_metadata(records.values(), metadata)
    frame = pd.DataFrame(records.values(), columns=COLUMNS).fillna("")
    return frame

def load_universe(data_root, today=None):
    root = Path(data_root)
    clinical = read_rows(root / "phase_pipeline.csv") + read_rows(root / "all_phase_trials.csv")
    return build_universe(
        clinical=clinical, announcements=read_rows(root / "phase3_announcements.csv"),
        regulatory=read_rows(root / "fda_review_engine.csv") + read_rows(root / "pdufa_candidates.csv"),
        historical=read_rows(root / "prediction_engine_history.csv"),
        metadata=read_rows(root / "drug_metadata.csv"), today=today)

def select_records(frame, stages, query=""):
    if frame.empty or not stages:
        return frame.iloc[:0].copy()
    # Pipeline STAGES represents the CURRENT stage, not all historical
    # milestones in stage_tags. Using tags here over-included FDA decision
    # rows while the stage counts used current_stage.
    wanted = set(stages)
    result = frame[frame["current_stage"].fillna("").isin(wanted)].copy()
    if clean(query) and not result.empty:
        text = result[["ticker", "company", "drug", "indication", "nct_id"]].astype(str).agg(" ".join, axis=1)
        result = result[text.str.contains(clean(query), case=False, regex=False)]
    return result.drop_duplicates("record_id")

def stage_counts(frame):
    return pd.DataFrame([{"Stage": stage, "Count": len(select_records(frame, [stage]))}
                         for stage in STAGES])

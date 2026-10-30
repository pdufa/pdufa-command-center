"""Source-bound historical FDA registry; source leads are not validated labels.

The six-case importer preserves curated source text and unknown values. It never
turns a dated outcome narrative into a timestamped/hashed decision document, nor
extracts scientific comparison features from prose without scientific review.
Program scoping here is data isolation; callers still need an authenticated,
server-authorized principal before exposing this research registry over an API.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from research.fda_verification_queue import _bind_action_metadata
from research.prediction_v1_1_historical_label_gate import historical_label_receipt

ROOT = Path(__file__).resolve().parents[1]
ACTION_MANIFEST = ROOT / "research/evidence/2025_holdout_fda_action_evidence.json"
RECONSTRUCTION_MANIFEST = ROOT / "research/evidence/2025_holdout_predecision_reconstruction.json"
TNXP_TRIAL_MANIFEST = ROOT / "research/evidence/tnxp_three_trial_comparison.json"
SCHEMA_VERSION = "historical-fda-decision-registry-v1"
DEFAULT_PROGRAM = "FDA_HISTORICAL_RESEARCH"
SCIENTIFIC_FIELDS = (
    "therapeutic_category", "drug_modality", "mechanism_of_action",
    "clinical_trial_identifiers", "phase3_trial_characteristics",
    "primary_endpoints", "secondary_endpoints", "efficacy_findings",
    "statistical_evidence", "safety_findings", "regulatory_pathway",
    "fda_special_designations", "advisory_committee_information",
    "manufacturing_findings", "inspection_findings", "previous_fda_decisions",
    "documented_decision_reasons",
)
ACTION_FIELDS = frozenset({"reported_outcome", "action_date", "decision_at",
    "source_published_at", "source_url", "source_document_sha256",
    "decision_document_id", "document_status", "classification_basis",
    "curated_outcome_claim", "source_context"})
FEATURE_FIELDS = frozenset({"value", "source_observation_ids", "assessment_ids",
    "uncertainty", "conflicting_observation_ids", "independently_reviewed"})
RECORD_FIELDS = frozenset({"record_id", "program_id", "program_family", "company",
    "ticker", "drug", "indication", "application_id", "review_cycle_id",
    "review_cycle_independently_adjudicated", "pdufa_target_date", "evidence_cutoff",
    "cutoff_basis", "original_prediction_cutoff", "scientific_fields",
    "observations", "reported_action", "missing_documents", "source_artifacts",
    "linked_trial_metadata"})
OBSERVATION_FIELDS = frozenset({"observation_id", "program_id", "source_url",
    "available_on", "availability_basis", "availability_source_url", "source_role",
    "finding", "assessment_ids", "source_location", "content_observed_on",
    "original_document_sha256", "source_bytes_retained", "independently_reviewed"})
TRIAL_FIELDS = frozenset({"trial_id", "trial_name", "registry_id", "reported_primary_endpoint",
    "reported_primary_analysis_method", "source_id", "source_url", "source_document_date",
    "public_availability_verified", "original_document_sha256", "independently_reviewed",
    "eligible_as_prediction_feature", "status"})
OUTCOME_CLAIMS = {"APPROVED": "PASS", "approval": "PASS", "CRL": "CRL",
                  "complete_response_letter": "CRL", "EXTENSION": "EXTENSION"}
FDA_ACTION_HOSTS = frozenset({"fda.gov", "www.fda.gov", "accessdata.fda.gov",
                             "www.accessdata.fda.gov", "download.open.fda.gov"})


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _program(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}", value):
        raise ValueError("exact research program identifier required")
    return value


def _day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("canonical date required; do not invent a timestamp")
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("canonical date required") from exc
    return result


def _url(value):
    if not isinstance(value, str) or any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError("attributable HTTPS source required")
    try:
        parts = urlsplit(value)
        valid = (parts.scheme == "https" and parts.hostname and "." in parts.hostname
                 and parts.username is None and parts.password is None
                 and parts.port in (None, 443) and parts.path not in ("", "/")
                 and not parts.fragment)
    except ValueError as exc:
        raise ValueError("attributable HTTPS source required") from exc
    if not valid:
        raise ValueError("attributable HTTPS source required")


def _digest(value):
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def _read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate historical registry JSON key")
            result[key] = value
        return result
    raw = Path(path).read_bytes()
    return json.loads(raw, object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite historical registry JSON")))


def _artifact(path):
    return {"path": str(Path(path).relative_to(ROOT)),
            "local_manifest_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            "hash_scope": "LOCAL_CURATED_MANIFEST_NOT_ORIGINAL_FDA_SOURCE_BYTES"}


def action_label_review(record):
    """Use the installed historical label gate without upgrading source claims.

    Date-only documents are intentionally kept date-only. Missing original bytes
    or publication clocks therefore remain explicit gate failures.
    """
    action = record["reported_action"]
    label = {"program_id": record["program_id"], "outcome": action["reported_outcome"],
        **{key: action[key] for key in ("decision_at", "source_published_at", "source_url",
                                      "source_document_sha256", "decision_document_id")}}
    # No date->midnight conversion: the recovered research cutoff has day precision.
    result = historical_label_receipt(label)
    result["point_in_time_validation_status"] = "BLOCKED_PENDING_ORIGINAL_TIMESTAMPS_AND_CUTOFF"
    result["eligible_for_predictive_training"] = False
    result["eligible_for_validated_accuracy"] = False
    return result


def validate_registry(registry, *, program_id):
    """Validate structure and exact program scope, never scientific truth."""
    _program(program_id)
    if (not isinstance(registry, dict) or set(registry) != {"schema_version", "records"}
            or registry["schema_version"] != SCHEMA_VERSION or not isinstance(registry["records"], list)):
        raise ValueError("versioned historical decision registry required")
    seen_ids, seen_cycles, seen_actions = set(), set(), set()
    for record in registry["records"]:
        if not isinstance(record, dict) or set(record) != RECORD_FIELDS:
            raise ValueError("exact historical case schema required")
        if record["program_id"] != program_id:
            raise ValueError("cross-program historical registry access denied")
        for field in ("record_id", "program_family", "ticker", "drug", "indication", "cutoff_basis"):
            if not _text(record[field]):
                raise ValueError("explicit case identity and cutoff provenance required")
        if record["record_id"] in seen_ids:
            raise ValueError("duplicate historical record identity")
        seen_ids.add(record["record_id"])
        if not isinstance(record["application_id"], str) or not re.fullmatch(r"(?:NDA|BLA)\d{6}", record["application_id"]):
            raise ValueError("exact FDA application identity required")
        if record["company"] is not None and not _text(record["company"]):
            raise ValueError("unknown company must be null")
        cycle = record["review_cycle_id"]
        if cycle is not None and not _text(cycle):
            raise ValueError("unknown review cycle must be null")
        if record["review_cycle_independently_adjudicated"] is not False:
            raise ValueError("registry imports cannot self-certify review cycles")
        if cycle is not None:
            key = (record["application_id"], cycle.casefold())
            if key in seen_cycles:
                raise ValueError("duplicate application/review cycle, including goal-date aliases")
            seen_cycles.add(key)
        target, cutoff = (_day(record[key]) for key in ("pdufa_target_date", "evidence_cutoff"))
        if cutoff >= target:
            raise ValueError("research cutoff must precede PDUFA target")
        if record["original_prediction_cutoff"] is not None:
            raise ValueError("recovered original prediction cutoffs need independent archive review")
        if not isinstance(record["scientific_fields"], dict) or set(record["scientific_fields"]) != set(SCIENTIFIC_FIELDS):
            raise ValueError("all scientific registry fields, including unknown values, required")
        action = record["reported_action"]
        if not isinstance(action, dict) or set(action) != ACTION_FIELDS:
            raise ValueError("source-bound reported action required")
        if not isinstance(action["reported_outcome"], str) or action["reported_outcome"] not in {"PASS", "CRL", "EXTENSION", "UNRESOLVED"}:
            raise ValueError("unknown outcome; missed targets do not establish FDA action")
        if action["action_date"] is None and action["reported_outcome"] == "UNRESOLVED":
            action_day = None
        else:
            action_day = _day(action["action_date"])
        if action_day is not None:
            action_key = (record["application_id"], action_day)
            if action_key in seen_actions:
                raise ValueError("duplicate application/action date requires cycle adjudication")
            seen_actions.add(action_key)
            if cutoff >= action_day:
                raise ValueError("reconstruction cutoff must precede actual FDA action")
        if action["source_url"] is not None or action["reported_outcome"] != "UNRESOLVED":
            _url(action["source_url"])
        if action["reported_outcome"] != "UNRESOLVED" and urlsplit(action["source_url"]).hostname not in FDA_ACTION_HOSTS:
            raise ValueError("formal FDA action source claims require an official FDA host")
        for field in ("decision_at", "source_published_at", "source_document_sha256"):
            if action[field] is not None:
                raise ValueError("this source-lead importer cannot supply unreviewed timestamps or original hashes")
        if action["decision_document_id"] is not None and not _text(action["decision_document_id"]):
            raise ValueError("unknown document identity must be null")
        if any(not _text(action[key]) for key in ("document_status", "classification_basis", "source_context")):
            raise ValueError("action uncertainty and classification provenance required")
        if not _text(action["curated_outcome_claim"]) or OUTCOME_CLAIMS.get(action["curated_outcome_claim"], "UNRESOLVED") != action["reported_outcome"]:
            raise ValueError("reported outcome must preserve the attributable curated claim")
        if not isinstance(record["observations"], list):
            raise ValueError("source-bound observation list required")
        seen_observations = set()
        for item in record["observations"]:
            if not isinstance(item, dict) or set(item) != OBSERVATION_FIELDS:
                raise ValueError("exact evidence observation schema required")
            if item["program_id"] != program_id:
                raise ValueError("cross-program evidence observation denied")
            if not _text(item["observation_id"]) or item["observation_id"] in seen_observations:
                raise ValueError("unique evidence observation identity required")
            seen_observations.add(item["observation_id"])
            if item["source_role"] not in {"PREDECISION_RESEARCH", "OUTCOME_ONLY"}:
                raise ValueError("explicit source role required")
            _url(item["source_url"])
            if item["availability_source_url"] is not None:
                _url(item["availability_source_url"])
            if item["available_on"] is not None:
                _day(item["available_on"])
            _day(item["content_observed_on"])
            if not _text(item["finding"]) or not _text(item["availability_basis"]):
                raise ValueError("source narrative and public availability basis required")
            ids = item["assessment_ids"]
            if (not isinstance(ids, list) or not ids or any(not isinstance(value, str)
                    or not re.fullmatch(r"S(?:0[1-9]|[1-3][0-9]|40)", value) for value in ids)
                    or len(set(ids)) != len(ids)):
                raise ValueError("canonical scientific assessment mapping required")
            if item["source_bytes_retained"] is not False or item["independently_reviewed"] is not False or item["original_document_sha256"] is not None:
                raise ValueError("source leads cannot self-certify original bytes or scientific review")
        for feature in record["scientific_fields"].values():
            if feature is None:
                continue
            if not isinstance(feature, dict) or set(feature) != FEATURE_FIELDS:
                raise ValueError("structured findings require source-bound feature records")
            value = feature["value"]
            if not (_text(value) or isinstance(value, list) and value and all(_text(item) for item in value)):
                raise ValueError("reported scientific feature values must be descriptive, not fabricated scores")
            for key in ("source_observation_ids", "conflicting_observation_ids"):
                ids = feature[key]
                if (not isinstance(ids, list) or any(not isinstance(item, str) or item not in seen_observations for item in ids)
                        or len(set(ids)) != len(ids)):
                    raise ValueError("scientific feature sources must belong to the same case and program")
            if not feature["source_observation_ids"] or not _text(feature["uncertainty"]):
                raise ValueError("feature provenance and uncertainty required")
            ids = feature["assessment_ids"]
            if (not isinstance(ids, list) or not ids or any(not isinstance(item, str)
                    or not re.fullmatch(r"S(?:0[1-9]|[1-3][0-9]|40)", item) for item in ids)
                    or len(set(ids)) != len(ids)):
                raise ValueError("feature canonical assessment mapping required")
            if feature["independently_reviewed"] is not False:
                raise ValueError("source-bound structured features cannot self-certify scientific review")
        if not isinstance(record["linked_trial_metadata"], list):
            raise ValueError("explicit linked trial metadata list required")
        seen_trials = set()
        for trial in record["linked_trial_metadata"]:
            if not isinstance(trial, dict) or set(trial) != TRIAL_FIELDS:
                raise ValueError("exact source-bound trial metadata schema required")
            if any(not _text(trial[key]) for key in ("trial_id", "trial_name", "reported_primary_endpoint", "reported_primary_analysis_method", "source_id")):
                raise ValueError("reported trial identity and endpoint provenance required")
            if trial["trial_id"] in seen_trials:
                raise ValueError("duplicate linked clinical trial")
            seen_trials.add(trial["trial_id"])
            if trial["registry_id"] is not None and (not isinstance(trial["registry_id"], str) or not re.fullmatch(r"NCT\d{8}", trial["registry_id"])):
                raise ValueError("unknown trial registry identifiers must remain null")
            _url(trial["source_url"])
            if trial["source_document_date"] is not None:
                _day(trial["source_document_date"])
            if (trial["public_availability_verified"] is not False or trial["independently_reviewed"] is not False
                    or trial["eligible_as_prediction_feature"] is not False or trial["original_document_sha256"] is not None
                    or trial["status"] != "SOURCE_LEAD_PUBLIC_AVAILABILITY_NOT_INDEPENDENTLY_VERIFIED"):
                raise ValueError("linked trial source leads cannot become prediction features or verified assessments")
        if not isinstance(record["missing_documents"], list) or not all(_text(x) for x in record["missing_documents"]):
            raise ValueError("outstanding evidence requirements required")
        if not isinstance(record["source_artifacts"], list) or not record["source_artifacts"]:
            raise ValueError("local import provenance required")
        for artifact in record["source_artifacts"]:
            if (not isinstance(artifact, dict) or set(artifact) != {"path", "local_manifest_sha256", "hash_scope"}
                    or not _text(artifact["path"]) or not _digest(artifact["local_manifest_sha256"])
                    or artifact["hash_scope"] != "LOCAL_CURATED_MANIFEST_NOT_ORIGINAL_FDA_SOURCE_BYTES"):
                raise ValueError("local artifact checksum scope must not impersonate FDA source bytes")
    return deepcopy(registry)


def build_historical_registry(*, program_id=DEFAULT_PROGRAM):
    """Import existing six curated cases without altering the 146-row history."""
    _program(program_id)
    action_manifest, reconstruction = _read(ACTION_MANIFEST), _read(RECONSTRUCTION_MANIFEST)
    trial_manifest = _read(TNXP_TRIAL_MANIFEST)
    trial_sources = {row["source_id"]: row for row in trial_manifest["sources"]}
    evidence_by_event = {}
    for action in action_manifest["records"]:
        if action["event_key"] in evidence_by_event:
            raise ValueError("duplicate curated FDA action event")
        evidence_by_event[action["event_key"]] = action
    _bind_action_metadata(reconstruction, evidence_by_event)
    records = []
    for case in reconstruction["cases"]:
        action = evidence_by_event[case["event_key"]]
        cycle = action.get("review_cycle_id")
        if cycle is None or "unverified" in cycle.lower():
            cycle = None
        observations = [{"observation_id": row["id"], "program_id": program_id,
            "source_url": row["source_url"], "available_on": row["available_on"],
            "availability_basis": row["availability_basis"],
            "availability_source_url": row["availability_source_url"], "source_role": row["source_role"],
            "finding": row["finding"], "assessment_ids": deepcopy(row["science_question_ids"]),
            "source_location": row["source_location"], "content_observed_on": row["content_observed_on"],
            "original_document_sha256": row["original_document_sha256"],
            "source_bytes_retained": row["source_bytes_retained"],
            "independently_reviewed": row["independently_reviewed"]} for row in case["observations"]]
        claim = action.get("action", action.get("legacy_recorded_outcome"))
        trial_metadata = []
        if case["event_key"] == trial_manifest["event_key"]:
            if case["application_id"] != trial_manifest["application_id"]:
                raise ValueError("linked trial dossier application does not match historical case")
            for trial in trial_manifest["trials"]:
                source = trial_sources[trial["primary_analysis"]["source_id"]]
                trial_metadata.append({"trial_id": trial["trial_id"], "trial_name": trial["name"],
                    "registry_id": trial["registry_id"],
                    "reported_primary_endpoint": trial["primary_analysis"]["endpoint"],
                    "reported_primary_analysis_method": trial["primary_analysis"]["method"],
                    "source_id": source["source_id"], "source_url": source["source_url"],
                    "source_document_date": source["document_date"],
                    "public_availability_verified": source["public_availability_verified"],
                    "original_document_sha256": source["original_document_sha256"],
                    "independently_reviewed": source["independently_reviewed"],
                    "eligible_as_prediction_feature": False,
                    "status": "SOURCE_LEAD_PUBLIC_AVAILABILITY_NOT_INDEPENDENTLY_VERIFIED"})
        # This is an explicitly attributed curated classification, not a new FDA label.
        # The original manifest's contextual narrative remains part of import provenance.
        records.append({"record_id": case["event_key"], "program_id": program_id,
            "program_family": case["program_family"], "company": None, "ticker": case["ticker"],
            "drug": action["product"], "indication": case["indication"],
            "application_id": case["application_id"], "review_cycle_id": cycle,
            "review_cycle_independently_adjudicated": False,
            "pdufa_target_date": case["legacy_goal_date"], "evidence_cutoff": case["reconstruction_cutoff"],
            "cutoff_basis": case["cutoff_basis"], "original_prediction_cutoff": case["original_prediction_cutoff"],
            "scientific_fields": {field: None for field in SCIENTIFIC_FIELDS},
            "observations": observations, "missing_documents": deepcopy(case["missing_documents"]),
            "linked_trial_metadata": trial_metadata,
            "source_artifacts": [_artifact(ACTION_MANIFEST), _artifact(RECONSTRUCTION_MANIFEST)] +
                ([_artifact(TNXP_TRIAL_MANIFEST)] if trial_metadata else []),
            "reported_action": {"reported_outcome": OUTCOME_CLAIMS.get(claim, "UNRESOLVED"),
                "action_date": case["action_date"], "decision_at": None, "source_published_at": None,
                "source_url": action.get("original_2025_document_url") or action.get("fda_document_url") or action.get("fda_approval_letter_url"),
                "source_document_sha256": None,
                "decision_document_id": action.get("original_document_reference_id") or action.get("document_reference_id") or action.get("fda_primary_document_reference_id"),
                "document_status": action.get("original_action_document_status", "CURATED_ACTION_CONTENT_NOT_INDEPENDENTLY_ADJUDICATED"),
                "classification_basis": "CURATED_ACTION_MANIFEST_CLAIM_NOT_INDEPENDENT_DECISION_LABEL",
                "curated_outcome_claim": claim,
                "source_context": action.get("original_document_evidence") or action.get("document_evidence") or action.get("evidence_summary")}})
    records.sort(key=lambda row: row["record_id"])
    return validate_registry({"schema_version": SCHEMA_VERSION, "records": records}, program_id=program_id)


def registry_summary(registry, *, program_id):
    checked = validate_registry(registry, program_id=program_id)
    return {"schema_version": SCHEMA_VERSION, "historical_records_collected": len(checked["records"]),
        "source_observations_retained": sum(len(row["observations"]) for row in checked["records"]),
        "linked_trial_metadata_leads": sum(len(row["linked_trial_metadata"]) for row in checked["records"]),
        "independently_verified_decision_cycles": 0, "historically_backtested_cases": 0,
        "scientific_comparison_features_adjudicated": 0, "prediction_readiness": "NOT_READY",
        "prediction_action": "ABSTAIN", "prediction_probabilities": None,
        "records": [{"record_id": row["record_id"], "application_id": row["application_id"],
            "reported_action_date": row["reported_action"]["action_date"],
            "reported_outcome": row["reported_action"]["reported_outcome"],
            "label_review": action_label_review(row)} for row in checked["records"]]}


def predecision_view(registry, *, program_id, record_id):
    """Return only narratives eligible for that case's conservative research day.

    Printed dates, post-cutoff text and all outcome-only text are excluded; their
    finding text is withheld from the view. SEC index availability remains a
    reported source clock, not an independent scientific assessment.
    """
    checked = validate_registry(registry, program_id=program_id)
    matches = [row for row in checked["records"] if row["record_id"] == record_id]
    if len(matches) != 1:
        raise ValueError("historical case not available in authorized program")
    record = matches[0]
    cutoff = _day(record["evidence_cutoff"])
    admitted, excluded = [], []
    for observation in record["observations"]:
        if observation["source_role"] == "OUTCOME_ONLY":
            reason = "OUTCOME_ONLY"
        elif observation["available_on"] is None:
            reason = "PUBLIC_AVAILABILITY_UNKNOWN"
        elif _day(observation["available_on"]) > cutoff:
            reason = "AFTER_EVIDENCE_CUTOFF"
        elif observation["availability_basis"] != "SEC_FILING_INDEX" or observation["availability_source_url"] is None:
            reason = "PUBLIC_AVAILABILITY_NOT_INDEPENDENTLY_RECOVERED"
        else:
            reason = None
        if reason:
            excluded.append({"observation_id": observation["observation_id"], "reason": reason})
        else:
            admitted.append(observation)
    admitted_ids = {item["observation_id"] for item in admitted}
    visible_features = {}
    feature_statuses = {}
    for name, feature in record["scientific_fields"].items():
        if feature is None:
            status = "MISSING"
        elif not set(feature["source_observation_ids"]).issubset(admitted_ids):
            status = "SOURCE_NOT_AVAILABLE_AT_CUTOFF"
        elif set(feature["conflicting_observation_ids"]) & admitted_ids:
            status = "CONFLICTED_REQUIRES_SCIENTIFIC_REVIEW"
        else:
            status = "SOURCE_REPORTED_NOT_INDEPENDENTLY_REVIEWED"
        if status == "SOURCE_REPORTED_NOT_INDEPENDENTLY_REVIEWED":
            visible_features[name] = deepcopy(feature)
            visible_features[name]["conflicting_observation_ids"] = []
        else:
            visible_features[name] = None
        feature_statuses[name] = status
    return {"record_id": record_id, "program_id": program_id,
        "application_id": record["application_id"], "evidence_cutoff": record["evidence_cutoff"],
        "cutoff_basis": record["cutoff_basis"], "source_reported_research_observations": admitted,
        "excluded_observations": excluded, "scientific_fields": visible_features,
        "scientific_field_statuses": feature_statuses,
        "linked_trial_metadata_status": "SOURCE_LEADS_EXCLUDED_ORIGINAL_PUBLIC_AVAILABILITY_UNVERIFIED" if record["linked_trial_metadata"] else "NO_LINKED_TRIAL_METADATA",
        "outcome_labels_included": False, "independently_reviewed_assessments": 0,
        "prediction_readiness": "NOT_READY", "prediction_action": "ABSTAIN"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program-id", default=DEFAULT_PROGRAM)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    result = build_historical_registry(program_id=args.program_id)
    data = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output is not None:
        if args.check:
            if not args.output.is_file() or args.output.read_text(encoding="utf-8") != data:
                parser.exit(1, "Historical registry differs from its source manifests.\n")
        else:
            args.output.write_text(data, encoding="utf-8")
    print(json.dumps(registry_summary(result, program_id=args.program_id), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

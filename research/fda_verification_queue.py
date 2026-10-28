"""Prioritize legacy historical events for independent FDA verification.

This is a triage queue, not a validation cohort or outcome predictor.
"""
import csv
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from research.fda_predecision_reconstruction import audit_reconstructions

PRIORITY = {
    "2025_EXTERNAL_BLIND": 0,
    "2024_FROZEN_PREDECISION_TUNE": 1,
    "2026_AUDIT_REPAIR_FROZEN_MODEL": 2,
}


def _read_json(path):
    def unique_object(pairs):
        result = {}
        for key,value in pairs:
            if key in result:
                raise ValueError("duplicate JSON field in research source packet")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8"),object_pairs_hook=unique_object)


def _bind_action_metadata(packet, evidence_by_event):
    """Cross-check curated sources; this does not independently adjudicate them."""
    fields = ("action_date", "fda_original_action_date", "fda_original_approval_date", "fda_action_date")
    for case in packet.get("cases", []):
        evidence = evidence_by_event.get(case.get("event_key"))
        if evidence is None:
            raise ValueError("reconstruction requires matching FDA action evidence")
        application = evidence.get("application_id")
        if not isinstance(application,str):
            raise ValueError("invalid FDA action evidence application identity")
        identity = re.fullmatch(r"(NDA|BLA)[ -]?([0-9]{6})(?:/0)?",application.strip().upper())
        if identity is None or "".join(identity.groups()) != case.get("application_id"):
            raise ValueError("reconstruction application conflicts with FDA action evidence")
        dates = []
        for field in fields:
            value = evidence.get(field)
            if value is not None:
                if not isinstance(value,str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}",value):
                    raise ValueError("invalid FDA action evidence date")
                dates.append(date.fromisoformat(value).isoformat())
        if len(set(dates)) != 1 or case.get("action_date") != dates[0]:
            raise ValueError("reconstruction action date conflicts with FDA action evidence")


def _attach_science_framework(reconstruction):
    catalog_path = Path(__file__).resolve().parents[1]/"new-platform/backend/app/science_40_question_catalog.json"
    catalog = _read_json(catalog_path)
    questions = catalog["questions"]
    by_id = {row["id"]:row for row in questions}
    if (len(questions)!=40 or len(by_id)!=40 or catalog["layerCount"]!=8
            or catalog["maximumInvestigationDepth"]!=20):
        raise ValueError("existing SCIENCE catalog contract changed; explicit review required")
    reconstruction["science_framework"] = {
        "catalog_schema_version":catalog["schemaVersion"],"layer_count":8,"question_count":40,
        "depth_count":20,"independently_certified_assessments":0,"certified_depth_levels":0}
    for case in reconstruction["case_reports"]:
        for row in case["science_worklist"]:
            definition = by_id[row["question_id"]]
            row.update(layer=definition["layer"],layer_name=definition["layerName"],question=definition["question"])
        case["action_metadata_binding"] = "MATCHED_CURATED_ACTION_MANIFEST_NOT_INDEPENDENT_ADJUDICATION"
        case["main"].update({
            "supporting_factors":case["supporting_factors"],"opposing_factors":case["opposing_factors"],
            "evidence_completeness":{"status":"INCOMPLETE","missing_documents":case["missing_documents"]},
            "historical_precedent_strength":"UNADJUDICATED_RESEARCH_CONTEXT",
            "critical_unresolved_concerns":case["blockers"],"prediction_model_version":None,
            "prediction_version":None,"research_packet_version":1,"research_as_of":reconstruction["as_of"]})


def build_verification_queue(path, evidence_manifest=None, *, reconstruction_manifest=None, as_of=None):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    evidence_by_event = {}
    if evidence_manifest is not None:
        manifest = _read_json(evidence_manifest)
        for item in manifest.get("records", []):
            key = item["event_key"]
            if key in evidence_by_event:
                raise ValueError("duplicate FDA action evidence event key")
            evidence_by_event[key] = item
    reconstruction = None
    reconstructions_by_event = {}
    if reconstruction_manifest is not None:
        if evidence_manifest is None:
            raise ValueError("reconstruction requires the linked FDA action manifest")
        packet = _read_json(reconstruction_manifest)
        _bind_action_metadata(packet,evidence_by_event)
        reconstruction = audit_reconstructions(packet, rows, as_of=date.today() if as_of is None else as_of)
        _attach_science_framework(reconstruction)
        reconstructions_by_event = {case["event_key"]: case for case in reconstruction["case_reports"]}
    queue = []
    for row in rows:
        evidence = evidence_by_event.get(row.get("event_key", ""), {})
        queue.append({
            "fda_evidence_status": evidence.get("verification_status", "ACTION_CONTENT_RECORDED_CYCLE_UNVERIFIED" if evidence else "NOT_YET_RECONCILED"),
            "legacy_action_date_mismatch": evidence.get("verification_status") == "LEGACY_GOAL_DATE_NOT_ACTION_DATE",
            "event_key": row.get("event_key", ""),
            "ticker": row.get("ticker", ""),
            "pdufa_date": row.get("pdufa_date", ""),
            "validation_period": row.get("validation_period", ""),
            "independence_status": row.get("independence_status", ""),
            "verification_status": "REQUIRES_INDEPENDENT_FDA_ACTION_EVIDENCE",
            "legacy_notes_quarantined": True,
            "prediction_input_eligibility": "BLOCKED_PENDING_PREDECISION_EVIDENCE_AUDIT",
            "requirements": [
                "FDA original action document and application identifier",
                "FDA review cycle and actual action date",
                "evidence availability before prediction cutoff",
                "program-family independence and sampling denominator",
            ],
            "trading_authorized": False,
        })
        if row.get("event_key") in reconstructions_by_event:
            queue[-1]["predecision_reconstruction"] = reconstructions_by_event[row["event_key"]]
    queue.sort(key=lambda r: (PRIORITY.get(r["validation_period"], 9), r["pdufa_date"], r["event_key"]))
    result = {
        "total_records": len(queue),
        "priority_period_counts": dict(sorted(Counter(x["validation_period"] for x in queue).items())),
        "queue": queue,
        "research_only": True,
        "validated_training_cohort": False,
    }
    if reconstruction is not None:
        result["predecision_reconstruction_summary"] = {
            key:value for key,value in reconstruction.items() if key != "case_reports"
        }
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Read-only FDA source and predecision reconstruction queue")
    parser.add_argument("history_csv")
    parser.add_argument("evidence_manifest", nargs="?")
    parser.add_argument("reconstruction_manifest", nargs="?")
    parser.add_argument("--as-of", type=date.fromisoformat,
                        help="Fixed reconstruction audit snapshot, YYYY-MM-DD")
    args = parser.parse_args()
    if args.reconstruction_manifest and args.as_of is None:
        parser.error("--as-of is required for reproducible reconstruction auditing")
    print(json.dumps(build_verification_queue(args.history_csv,args.evidence_manifest,
        reconstruction_manifest=args.reconstruction_manifest,as_of=args.as_of),indent=2))

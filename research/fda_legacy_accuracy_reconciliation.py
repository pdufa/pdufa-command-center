"""Read-only reconciliation of legacy accuracy claims with research chronology.

Legacy YES labels are retained verbatim; they are not promoted to verified
prospective accuracy when contemporaneous prediction evidence is unavailable.
"""
import csv
import json
from pathlib import Path
from research.fda_archive_chronology_gate import audit_archive_chronology


def reconcile_legacy_accuracy(audit_rows, archive, reconstruction):
    chronology = audit_archive_chronology(archive, reconstruction)
    by_event = {row["event_key"]: row for row in chronology["cases"]}
    selected = {}
    for row in audit_rows:
        key = row.get("event_key")
        if key in by_event:
            if key in selected:
                raise ValueError("duplicate legacy audit event")
            selected[key] = row
    if set(selected) != set(by_event):
        raise ValueError("missing priority events in legacy accuracy audit")
    cases = []
    for key, check in by_event.items():
        legacy = selected[key]
        cases.append({
            "event_key": key,
            "legacy_audit_status": legacy.get("audit_status"),
            "legacy_count_in_audited_accuracy": legacy.get("count_in_audited_accuracy"),
            "legacy_action": legacy.get("audit_action"),
            "verified_prospective_accuracy_eligible": False,
            "chronology_blocker": check["reason"],
            "resolution": "PRESERVE_LEGACY_ROW_QUARANTINE_FROM_VERIFIED_PROSPECTIVE_METRICS",
        })
    return {"research_only": True, "legacy_rows_reconciled": len(cases),
            "verified_prospective_accuracy_cases": 0,
            "production_audit_modified": False, "cases": cases}


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        raise SystemExit("usage: python -m research.fda_legacy_accuracy_reconciliation audit.csv archive.json reconstruction.json")
    with Path(sys.argv[1]).open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    archive = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    reconstruction = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
    print(json.dumps(reconcile_legacy_accuracy(rows, archive, reconstruction), indent=2))

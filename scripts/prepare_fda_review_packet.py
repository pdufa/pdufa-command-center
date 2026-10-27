"""Generate a review-only checklist from reconciled FDA source evidence."""
import argparse
import json
from pathlib import Path


def prepare(ledger, reconciliation):
    candidates = ledger.get("candidate_review_cycles", [])
    records = reconciliation.get("records", [])
    if len(candidates) != len(records):
        raise ValueError("FDA evidence count mismatch")
    packet = []
    seen = set()
    seen_cycles = set()
    for candidate, record in zip(candidates, records):
        identity = ("application_id", "submission_id", "review_cycle", "official_source_url")
        if any(candidate.get(k) != record.get(k) for k in identity):
            raise ValueError("FDA evidence identity mismatch")
        key = tuple(candidate.get(k) for k in identity)
        if key in seen:
            raise ValueError("duplicate FDA decision identity in review packet")
        seen.add(key)
        cycle_key = tuple(candidate.get(k) for k in ("application_id", "submission_id", "review_cycle"))
        if cycle_key in seen_cycles:
            raise ValueError("same FDA review cycle has multiple source identities")
        seen_cycles.add(cycle_key)
        packet.append({
            **{k: candidate.get(k) for k in identity},
            "claimed_action": candidate.get("action_type"),
            "claimed_date": candidate.get("action_date"),
            "source_sha256": record.get("source_sha256"),
            "source_status": record.get("status"),
            "candidate_status": candidate.get("status"),
            "candidate_issues": candidate.get("issues", []),
            "review_priority": ("SOURCE_EVIDENCE_BLOCKED" if record.get("status") != "SOURCE_HASH_AVAILABLE_ADJUDICATION_PENDING"
                                else "METADATA_REVIEW_REQUIRED" if candidate.get("status") == "QUARANTINED"
                                else "INDEPENDENT_ADJUDICATION_REQUIRED"),
            "review_required": [
                "Confirm PDF contents and source hash",
                "Confirm application, submission and review cycle",
                "Confirm action and date, including corrections",
                "Confirm evidence cutoff and independent reviewer",
            ],
            "independently_verified": False,
            "model_eligible": False,
        })
    priority_order = {"SOURCE_EVIDENCE_BLOCKED": 0,
                      "METADATA_REVIEW_REQUIRED": 1,
                      "INDEPENDENT_ADJUDICATION_REQUIRED": 2}
    packet.sort(key=lambda r: (priority_order[r["review_priority"]],
                               str(r["application_id"]), str(r["submission_id"]),
                               str(r["review_cycle"])))
    counts = {priority: sum(r["review_priority"] == priority for r in packet)
              for priority in priority_order}
    return {"records": packet, "total_to_review": len(packet),
            "priority_counts": counts, "verified": 0, "model_eligible": 0,
            "cleared_for_independent_review": counts["INDEPENDENT_ADJUDICATION_REQUIRED"],
            "blocked_before_independent_review": counts["SOURCE_EVIDENCE_BLOCKED"] + counts["METADATA_REVIEW_REQUIRED"],
            "remaining_to_verify": len(packet),
            "warning": "Cleared for review does not mean independently verified or model eligible."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--reconciliation", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(
        json.loads(args.ledger.read_text(encoding="utf-8")),
        json.loads(args.reconciliation.read_text(encoding="utf-8"))),
        indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

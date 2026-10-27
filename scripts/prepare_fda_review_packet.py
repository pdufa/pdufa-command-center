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
    for candidate, record in zip(candidates, records):
        identity = ("application_id", "submission_id", "review_cycle", "official_source_url")
        if any(candidate.get(k) != record.get(k) for k in identity):
            raise ValueError("FDA evidence identity mismatch")
        packet.append({
            **{k: candidate.get(k) for k in identity},
            "claimed_action": candidate.get("action_type"),
            "claimed_date": candidate.get("action_date"),
            "source_sha256": record.get("source_sha256"),
            "source_status": record.get("status"),
            "review_required": [
                "Confirm PDF contents and source hash",
                "Confirm application, submission and review cycle",
                "Confirm action and date, including corrections",
                "Confirm evidence cutoff and independent reviewer",
            ],
            "independently_verified": False,
            "model_eligible": False,
        })
    return {"records": packet, "verified": 0, "model_eligible": 0}


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

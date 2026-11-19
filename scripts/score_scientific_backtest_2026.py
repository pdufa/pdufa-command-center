#!/usr/bin/env python3
"""Score an independently locked scientific backtest in outcome quarantine."""

import argparse
from datetime import date
from urllib.parse import urlparse

from blind_six_levels_2026 import load_csv
from report_blind_six_levels_2026 import score


IDENTITY_FIELDS = ("application_number", "review_cycle", "decision_date")


def validate_ledger(rows, predictions):
    """Reject unresolved outcomes and anything joined to a different review cycle."""
    identities = {}
    for prediction in predictions:
        event_id = prediction["event_id"]
        identity = tuple(prediction[field] for field in IDENTITY_FIELDS)
        if any(not isinstance(value, str) or not value.strip() for value in identity):
            raise ValueError(f"{event_id}: missing locked application, cycle or action date")
        if identities.setdefault(event_id, identity) != identity:
            raise ValueError(f"{event_id}: inconsistent locked review-cycle identity")
    for row in rows:
        event_id = row.get("event_id")
        identity = tuple(row.get(field) for field in IDENTITY_FIELDS)
        if identities.get(event_id) != identity:
            raise ValueError(f"{event_id}: FDA ledger does not match the locked application cycle")
        if row.get("identity_status") != "VERIFIED_ELIGIBLE":
            raise ValueError(f"{event_id}: FDA ledger action is not verified eligible")
        try:
            action_date = date.fromisoformat(row["decision_date"])
            source = urlparse(row.get("fda_source_url", ""))
            host = source.hostname or ""
        except ValueError as exc:
            raise ValueError(f"{event_id}: invalid action date or FDA source") from exc
        if (
            action_date.isoformat() != row["decision_date"]
            or source.scheme != "https"
            or source.username is not None
            or (host != "fda.gov" and not host.endswith(".fda.gov"))
        ):
            raise ValueError(f"{event_id}: an exact action date and official FDA source are required")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locked", required=True)
    parser.add_argument("--outcomes", required=True)
    parser.add_argument("--expected-lock-sha256", required=True)
    parser.add_argument("--summary-csv")
    parser.add_argument("--results-csv")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    from blind_scientific_2026 import verify_canonical_lock

    score(args, verify_canonical_lock, load_csv, validate_ledger)


if __name__ == "__main__":
    main()

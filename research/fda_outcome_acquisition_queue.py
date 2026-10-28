"""Generate an auditable acquisition queue from historical FDA outcome observations.

This is a *source acquisition* inventory, not evidence verification.
Later-cycle and corrected documents must not stand in for the original action.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path


def build_fda_outcome_acquisition_queue(reconstruction: dict) -> dict:
    rows = []
    for case in reconstruction["cases"]:
        action = date.fromisoformat(case["action_date"])
        for obs in case.get("observations", []):
            if obs.get("source_role") != "OUTCOME_ONLY":
                continue
            available = obs.get("available_on")
            after_action = bool(available and date.fromisoformat(available) > action)
            marker = (obs.get("id") or "").upper()
            is_replacement = after_action or any(
                term in marker for term in ("LATER-CYCLE", "CORRECTED"))
            rows.append({
                "event_key": case["event_key"],
                "ticker": case["ticker"],
                "application": case["application_id"],
                "original_action_date": case["action_date"],
                "observation_id": obs["id"],
                "source_url": obs.get("source_url"),
                "reported_available_on": available,
                "source_is_later_or_corrected": is_replacement,
                "may_substitute_for_original_action": not is_replacement,
                "source_bytes_retained": bool(obs.get("source_bytes_retained")),
                "sha256_recorded": bool(obs.get("original_document_sha256")),
                "independently_reviewed": bool(obs.get("independently_reviewed")),
                "acquisition_status": "NEEDS_ORIGINAL_BYTES_AND_AUTHENTICATION",
                "eligible_for_predecision_science": False,
                "eligible_for_predictive_training": False,
            })
    return {"research_only": True, "trading_authorized": False,
            "source_count": len(rows), "sources": rows}


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconstruction", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    with args.reconstruction.open(encoding="utf-8") as handle:
        queue = build_fda_outcome_acquisition_queue(json.load(handle))
    if args.output.exists():
        parser.error("output already exists; do not overwrite acquisition audits")
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(queue, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

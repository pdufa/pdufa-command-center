#!/usr/bin/env python3
"""Build a conservative, deterministic FOCUS scientific adjudication workqueue.

Run: python scripts/build_focus_adjudication_queue.py
Read-only to roster, prediction history, and scoring. Writes JSON to stdout.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
RESEARCH = ROOT / "research/focus"
NCT_PATTERN = re.compile(r"NCT\d{8}", re.I)
DIMENSIONS = (
    "disease_and_mechanism",
    "trial_design_and_population",
    "endpoints_and_statistics",
    "clinical_benefit",
    "safety_and_tolerability",
    "subgroups_and_external_validity",
    "fda_regulatory_and_cmc",
    "independent_replication_and_challenge",
)
PENDING = "PENDING_INDEPENDENT_REVIEW"


def build_queue(roster: dict, research_dir: Path) -> dict:
    records = roster["records"]
    assert len(records) == 29, "FOCUS roster changed: review mapping before continuing"
    keys = [(r["ticker"], r["nct"]) for r in records]
    assert len(set(keys)) == len(keys), "Duplicate FOCUS ticker/NCT"
    notes = sorted(research_dir.glob("*preliminary-evidence*.md"))
    queue = []
    for r in records:
        ticker, nct = r["ticker"], r["nct"]
        # Ticker-level notes can cover multiple NCTs. They are leads only,
        # never proof that an individual study has been adjudicated.
        matches = []
        for note in notes:
            if not note.name.upper().startswith(ticker.upper() + "-"):
                continue
            body = note.read_text(encoding="utf-8")
            if nct.upper() in body.upper():
                matches.append(note.relative_to(ROOT).as_posix())
        queue.append({
            "ticker": ticker,
            "nct": nct,
            "preliminary_source_notes": matches,
            "source_review": PENDING,
            "independent_challenge": PENDING,
            "dimensions": {d: {
                "status": PENDING,
                "primary_source_uri": None,
                "reviewer": None,
                "reviewed_at": None,
                "evidence_excerpt_or_location": None,
                "finding": None,
                "contrary_evidence": None,
            } for d in DIMENSIONS},
            "adjudicated": False,
            "calibrated_fda_probability": None,
            "prediction_published": False,
        })
    return {
        "schema_version": 1,
        "roster_as_of": roster["asOf"],
        "scope": "FOCUS",
        "research_is_not_adjudication": True,
        "dimensions_per_trial": len(DIMENSIONS),
        "trial_count": len(queue),
        "adjudicated_count": 0,
        "prediction_count": 0,
        "trials": queue,
    }


def main() -> None:
    data = json.loads(ROSTER.read_text(encoding="utf-8"))
    queue = build_queue(data, RESEARCH)
    assert len(queue["trials"]) == 29
    assert all(not t["adjudicated"] and t["calibrated_fda_probability"] is None
               for t in queue["trials"])
    print(json.dumps(queue, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

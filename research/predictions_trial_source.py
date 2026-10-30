"""Normalize independently supplied trial feeds for the PREDICTIONS selector.

No fabricated trials. Source connectors supply real rows and provenance.
Existing filter presets are not modified.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping

from research.predictions_tab import eligible_trials

SOURCE_GROUPS = {
    "phase3_released": "PHASE3_DATA_RELEASED",
    "gem_jr": "GEM_JR",
    "gem": "GEM",
    "wt": "WT",
}


def build_prediction_candidates(
    *,
    phase3_released: Iterable[Mapping] = (),
    gem_jr: Iterable[Mapping] = (),
    gem: Iterable[Mapping] = (),
    wt: Iterable[Mapping] = (),
) -> list[dict]:
    """Require stable IDs and verifiable source references for every candidate."""
    sources = {
        "phase3_released": phase3_released,
        "gem_jr": gem_jr,
        "gem": gem,
        "wt": wt,
    }
    prepared: list[dict] = []
    for source_name, rows in sources.items():
        for row in rows:
            trial_id = str(row.get("trial_id") or "").strip()
            evidence_url = str(row.get("source_url") or "").strip()
            if not trial_id or not evidence_url.startswith(("https://", "http://")):
                continue
            if source_name == "phase3_released" and row.get("phase3_data_released") is not True:
                continue
            prepared.append({
                "trial_id": trial_id,
                "label": str(row.get("label") or trial_id),
                "groups": [SOURCE_GROUPS[source_name]],
                "source_url": evidence_url,
            })
    selected = eligible_trials(prepared)
    evidence_by_id: dict[str, set[str]] = {}
    for row in prepared:
        evidence_by_id.setdefault(row["trial_id"], set()).add(row["source_url"])
    return [
        {**row, "source_urls": sorted(evidence_by_id[row["trial_id"]])}
        for row in selected
    ]

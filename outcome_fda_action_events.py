"""Fail-closed FDA action-event normalization (not a training cohort)."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Optional

ACTION_TYPES = frozenset({"approval", "accelerated_approval", "complete_response", "other"})
NON_ACTION_TYPES = frozenset({"pdufa_goal", "meeting", "amendment", "incomplete_response", "review_recommendation"})

@dataclass(frozen=True)
class FDAEvent:
    application_key: str
    submission_key: str
    event_date: date
    event_type: str
    source_url: str
    final_agency_action: bool = False
    source_document_sha256: Optional[str] = None
    source_publication_date: Optional[date] = None

    def __post_init__(self):
        if not self.application_key or not self.submission_key or not self.source_url.startswith("https://"):
            raise ValueError("FDA event requires application, submission and HTTPS evidence")
        if self.event_type not in ACTION_TYPES | NON_ACTION_TYPES:
            raise ValueError("Unsupported event type")
        if self.final_agency_action and self.event_type not in ACTION_TYPES:
            raise ValueError("Non-actions cannot be final agency actions")
        if self.source_document_sha256 is not None and (
            len(self.source_document_sha256) != 64
            or any(ch not in "0123456789abcdef" for ch in self.source_document_sha256)
        ):
            raise ValueError("Expected lowercase SHA-256 digest")

    @property
    def action_key(self) -> Optional[tuple[str, str, date, str]]:
        if not self.final_agency_action:
            return None
        return (self.application_key, self.submission_key, self.event_date, self.event_type)


@dataclass(frozen=True)
class ModelGate:
    complete_denominator_verified: bool = False
    cycle_boundaries_verified: bool = False
    feature_asof_verified: bool = False
    action_sources_verified: bool = False
    model_independently_validated: bool = False

    @property
    def model_eligible(self) -> bool:
        return all((
            self.complete_denominator_verified,
            self.cycle_boundaries_verified,
            self.feature_asof_verified,
            self.action_sources_verified,
            self.model_independently_validated,
        ))

    @property
    def prediction_probability(self) -> None:
        # No trained model is provided by this module. Never synthesize a probability.
        return None


def unique_final_actions(events: list[FDAEvent]) -> dict[tuple[str, str, date, str], FDAEvent]:
    """Deduplicate identical action keys; reject contradictory evidence."""
    actions: dict[tuple[str, str, date, str], FDAEvent] = {}
    for event in events:
        key = event.action_key
        if key is None:
            continue
        existing = actions.get(key)
        if existing is not None and existing != event:
            raise ValueError(f"Conflicting action evidence for {key}")
        actions[key] = event
    return actions


def check_asof(event: FDAEvent, asof: date) -> bool:
    """Only use source documents available by the feature as-of date."""
    return event.source_publication_date is not None and event.source_publication_date <= asof

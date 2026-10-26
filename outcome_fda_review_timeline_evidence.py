"""FDA source-supported review timelines; NOT independent cohort certification.

A timeline is a proposed (receipt, FDA final-action) pair for one submission.
FDA source publication timestamps, unbiased cohort denominator, complete
amendment/clock inventory and pre-action feature availability remain unverified.
No probability or model eligibility is furnished here.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Optional

from outcome_fda_action_events import FDAEvent, unique_final_actions
from outcome_fda_research_action_fixtures import RESEARCH_ACTIONS

SUPPORTED_ACTIONS = frozenset({"complete_response", "approval", "accelerated_approval"})

@dataclass(frozen=True)
class SourceSupportedCycle:
    application_key: str
    submission_key: str
    received_date: date
    action_date: date
    action_type: str
    receipt_source_url: str
    final_action_source_url: str
    regulatory_history_source_url: str
    pdufa_goal_date: Optional[date] = None

    def __post_init__(self):
        if not self.application_key.startswith(("BLA:", "NDA:")):
            raise ValueError("Explicit regulatory application identifier required")
        if not self.submission_key.startswith(self.application_key + ":"):
            raise ValueError("Submission must belong to the application")
        if self.received_date > self.action_date:
            raise ValueError("Final action must not precede submission")
        if self.action_type not in SUPPORTED_ACTIONS:
            raise ValueError("Only signed FDA final actions can close these timelines")
        if any(not url.startswith("https://") for url in (
            self.receipt_source_url,
            self.final_action_source_url,
            self.regulatory_history_source_url,
        )):
            raise ValueError("Primary evidence URLs required")
        if self.pdufa_goal_date is not None and self.pdufa_goal_date < self.received_date:
            raise ValueError("Action goal cannot precede the submission receipt")

    @property
    def cycle_key(self) -> str:
        return self.submission_key

    @property
    def independently_certified(self) -> bool:
        # Evidence-linked timing is not certification of inventory completeness.
        return False

    @property
    def model_eligible(self) -> bool:
        return False

    @property
    def source_publication_asof_verified(self) -> bool:
        return False


FDA_ABEONA_SBRA = "https://www.fda.gov/media/186796/download"
FDA_ABEONA_CRL = "https://download.open.fda.gov/crl/CRL_BLA125807_20240416.pdf"
FDA_ABEONA_APPROVAL = "https://www.fda.gov/media/186513/download"

REVIEW_TIMELINES = (
    SourceSupportedCycle(
        application_key="BLA:125807",
        submission_key="BLA:125807:ORIGINAL",
        received_date=date(2023, 9, 25),
        action_date=date(2024, 4, 16),
        action_type="complete_response",
        receipt_source_url=FDA_ABEONA_CRL,
        final_action_source_url=FDA_ABEONA_CRL,
        regulatory_history_source_url=FDA_ABEONA_SBRA,
        pdufa_goal_date=None,
    ),
    SourceSupportedCycle(
        application_key="BLA:125807",
        submission_key="BLA:125807:RESUBMISSION-1",
        received_date=date(2024, 10, 28),
        action_date=date(2025, 4, 28),
        action_type="approval",
        receipt_source_url=FDA_ABEONA_SBRA,
        final_action_source_url=FDA_ABEONA_APPROVAL,
        regulatory_history_source_url=FDA_ABEONA_SBRA,
        pdufa_goal_date=date(2025, 4, 29),
    ),
)


FDA_MESOBLAST_SBRA = "https://www.fda.gov/media/185192/download"
FDA_MESOBLAST_2023_CRL = "https://download.open.fda.gov/crl/CRL_BLA125706_20230801.pdf"
FDA_MESOBLAST_APPROVAL = "https://www.fda.gov/media/184605/download"

# Printed contradiction verified on the original FDA PDF, pages 1 and 7.
# Do not construe the cover-page '127506/0' as an additional application.
MESOBLAST_SBRA_IDENTIFIER_CONFLICT = {
    "cover_page_1": "127506/0",
    "regulatory_history_page_7": "125706/0",
    "signed_fda_approval_letter": "125706/0",
    "resolution": "canonical_125706_with_source_conflict_preserved",
}

MESOBLAST_SOURCE_SUPPORTED_TIMELINES = (
    SourceSupportedCycle(
        application_key="BLA:125706",
        submission_key="BLA:125706:RESUBMISSION-1",
        received_date=date(2023, 1, 31),
        action_date=date(2023, 8, 1),
        action_type="complete_response",
        receipt_source_url=FDA_MESOBLAST_2023_CRL,
        final_action_source_url=FDA_MESOBLAST_2023_CRL,
        regulatory_history_source_url=FDA_MESOBLAST_SBRA,
        pdufa_goal_date=None,
    ),
    SourceSupportedCycle(
        application_key="BLA:125706",
        submission_key="BLA:125706:RESUBMISSION-2",
        received_date=date(2024, 7, 8),
        action_date=date(2024, 12, 18),
        action_type="approval",
        receipt_source_url=FDA_MESOBLAST_SBRA,
        final_action_source_url=FDA_MESOBLAST_APPROVAL,
        regulatory_history_source_url=FDA_MESOBLAST_SBRA,
        pdufa_goal_date=date(2025, 1, 7),
    ),
)

# Source-supported timelines only: the 2020 original Mesoblast CRL's primary
# letter could not be fetched in this pass and its cycle is deliberately excluded.
REVIEW_TIMELINES = REVIEW_TIMELINES + MESOBLAST_SOURCE_SUPPORTED_TIMELINES


FDA_ROCKET_SBRA = "https://www.fda.gov/media/191993/download"
FDA_ROCKET_CRL = "https://download.open.fda.gov/crl/CRL_BLA125806_20240614.pdf"
FDA_ROCKET_APPROVAL = "https://www.fda.gov/media/191723/download"

ROCKET_SOURCE_SUPPORTED_TIMELINES = (
    SourceSupportedCycle(
        application_key="BLA:125806",
        submission_key="BLA:125806:ORIGINAL",
        received_date=date(2023, 8, 1),
        action_date=date(2024, 6, 14),
        action_type="complete_response",
        receipt_source_url=FDA_ROCKET_SBRA,
        final_action_source_url=FDA_ROCKET_CRL,
        regulatory_history_source_url=FDA_ROCKET_SBRA,
        pdufa_goal_date=None,
    ),
    SourceSupportedCycle(
        application_key="BLA:125806",
        submission_key="BLA:125806:RESUBMISSION-1",
        received_date=date(2025, 9, 26),
        action_date=date(2026, 3, 26),
        action_type="accelerated_approval",
        receipt_source_url=FDA_ROCKET_SBRA,
        final_action_source_url=FDA_ROCKET_APPROVAL,
        regulatory_history_source_url=FDA_ROCKET_SBRA,
        pdufa_goal_date=date(2026, 3, 28),
    ),
)

FDA_ULTRAGENYX_SBRA = "https://www.fda.gov/media/195198/download"
FDA_ULTRAGENYX_CRL = "https://download.open.fda.gov/crl/CRL_BLA125845_20250707.pdf"
FDA_ULTRAGENYX_APPROVAL = "https://www.fda.gov/media/194921/download"
FDA_ULTRAGENYX_CLINICAL_REVIEW = "https://www.fda.gov/media/195731/download"

# FDA SBRA and clinical review print conflicting resubmission PDUFA dates.
# pdufa_goal_date below uses SBRA only with both sources preserved here.
ULTRAGENYX_PDUFA_GOAL_SOURCE_CONFLICT = {
    "sbra": {"source_url": FDA_ULTRAGENYX_SBRA, "goal_date": "2026-09-19"},
    "clinical_review": {"source_url": FDA_ULTRAGENYX_CLINICAL_REVIEW, "goal_date": "2026-09-18"},
    "resolution_status": "unresolved_preserve_both",
}

ULTRAGENYX_SOURCE_SUPPORTED_TIMELINES = (
    SourceSupportedCycle(
        application_key="BLA:125845",
        submission_key="BLA:125845:ORIGINAL",
        received_date=date(2024, 12, 18),
        action_date=date(2025, 7, 7),
        action_type="complete_response",
        receipt_source_url=FDA_ULTRAGENYX_SBRA,
        final_action_source_url=FDA_ULTRAGENYX_CRL,
        regulatory_history_source_url=FDA_ULTRAGENYX_SBRA,
        pdufa_goal_date=None,
    ),
    SourceSupportedCycle(
        application_key="BLA:125845",
        submission_key="BLA:125845:RESUBMISSION-1",
        received_date=date(2026, 3, 20),
        action_date=date(2026, 9, 17),
        action_type="approval",
        receipt_source_url=FDA_ULTRAGENYX_SBRA,
        final_action_source_url=FDA_ULTRAGENYX_APPROVAL,
        regulatory_history_source_url=FDA_ULTRAGENYX_SBRA,
        pdufa_goal_date=date(2026, 9, 19),
    ),
)

FDA_REPLIMUNE_FIRST_CRL = "https://download.open.fda.gov/crl/CRL_BLA125827_20250721.pdf"
FDA_REPLIMUNE_SECOND_CRL = "https://download.open.fda.gov/crl/CRL_BLA125827_20260410.pdf"
FDA_REPLIMUNE_APPROVAL = "https://www.fda.gov/media/194128/download"
FDA_REPLIMUNE_CLINICAL_REVIEW = "https://www.fda.gov/media/194468/download"

# Clinical review recommendation is NOT a signed final FDA action letter.
REPLIMUNE_FINAL_ACTION_VS_REVIEW_RECOMMENDATION = {
    "clinical_review_source_url": FDA_REPLIMUNE_CLINICAL_REVIEW,
    "reviewer_recommendation": "complete_response",
    "signed_action_source_url": FDA_REPLIMUNE_APPROVAL,
    "final_agency_action": "accelerated_approval",
    "review_pdufa_goal_date": "2026-08-02",
    "final_action_date": "2026-08-06",
    "pdufa_clock_explanation": "unverified",
}

REPLIMUNE_SOURCE_SUPPORTED_TIMELINES = (
    SourceSupportedCycle(
        application_key="BLA:125827",
        submission_key="BLA:125827:ORIGINAL",
        received_date=date(2024, 11, 21),
        action_date=date(2025, 7, 21),
        action_type="complete_response",
        receipt_source_url=FDA_REPLIMUNE_APPROVAL,
        final_action_source_url=FDA_REPLIMUNE_FIRST_CRL,
        regulatory_history_source_url=FDA_REPLIMUNE_APPROVAL,
        pdufa_goal_date=None,
    ),
    SourceSupportedCycle(
        application_key="BLA:125827",
        submission_key="BLA:125827:RESUBMISSION-1",
        received_date=date(2025, 10, 9),
        action_date=date(2026, 4, 10),
        action_type="complete_response",
        receipt_source_url=FDA_REPLIMUNE_SECOND_CRL,
        final_action_source_url=FDA_REPLIMUNE_SECOND_CRL,
        regulatory_history_source_url=FDA_REPLIMUNE_SECOND_CRL,
        pdufa_goal_date=None,
    ),
    SourceSupportedCycle(
        application_key="BLA:125827",
        submission_key="BLA:125827:RESUBMISSION-2",
        received_date=date(2026, 6, 2),
        action_date=date(2026, 8, 6),
        action_type="accelerated_approval",
        receipt_source_url=FDA_REPLIMUNE_APPROVAL,
        final_action_source_url=FDA_REPLIMUNE_APPROVAL,
        regulatory_history_source_url=FDA_REPLIMUNE_CLINICAL_REVIEW,
        pdufa_goal_date=date(2026, 8, 2),
    ),
)

# Sampled, source-supported timelines only; not certified complete cycles.
REVIEW_TIMELINES = (
    REVIEW_TIMELINES
    + ROCKET_SOURCE_SUPPORTED_TIMELINES
    + ULTRAGENYX_SOURCE_SUPPORTED_TIMELINES
    + REPLIMUNE_SOURCE_SUPPORTED_TIMELINES
)


def validate_review_timelines(
    cycles: tuple[SourceSupportedCycle, ...] = REVIEW_TIMELINES,
    action_fixtures: tuple[FDAEvent, ...] = RESEARCH_ACTIONS,
) -> None:
    """Require one-to-one matching FDA action and nonoverlapping cycle starts.

    Does not claim that all submissions/actions for an application are known.
    """
    observed = unique_final_actions(list(action_fixtures))
    seen: set[str] = set()
    grouped: dict[str, list[SourceSupportedCycle]] = {}
    for cycle in cycles:
        if cycle.cycle_key in seen:
            raise ValueError("Duplicate review-cycle key")
        seen.add(cycle.cycle_key)
        expected = (cycle.application_key, cycle.submission_key, cycle.action_date, cycle.action_type)
        fixture = observed.get(expected)
        if fixture is None:
            raise ValueError("Missing matching FDA final-action research fixture")
        if fixture.source_url != cycle.final_action_source_url:
            raise ValueError("FDA primary final-action source mismatch")
        grouped.setdefault(cycle.application_key, []).append(cycle)
    for records in grouped.values():
        ordered = sorted(records, key=lambda x: x.received_date)
        for prior, current in zip(ordered, ordered[1:]):
            if current.received_date <= prior.action_date:
                raise ValueError("Overlapping or reversed review timelines")


def review_timeline_summary() -> dict:
    validate_review_timelines()
    return {
        "research_only": True,
        "applications_with_source_supported_timelines": len({x.application_key for x in REVIEW_TIMELINES}),
        "source_supported_review_timelines": len(REVIEW_TIMELINES),
        "independently_certified_review_cycles": 0,
        "complete_application_denominator_verified": False,
        "source_publication_asof_verified": False,
        "model_eligible_records": 0,
        "prediction_probability": None,
    }

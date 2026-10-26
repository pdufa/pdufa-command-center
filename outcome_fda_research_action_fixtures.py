"""Research-only FDA action fixtures, deliberately not a cohort denominator.

Every event points to an FDA source. Records are hand-transcribed from the
committed primary-source reports; they do not establish complete cycle coverage.
"""
from datetime import date
from outcome_fda_action_events import FDAEvent, ModelGate, unique_final_actions

def event(application, submission, day, kind, url):
    return FDAEvent(
        application_key=f"BLA:{application}",
        submission_key=f"BLA:{application}:{submission}",
        event_date=date.fromisoformat(day),
        event_type=kind,
        source_url=url,
        final_agency_action=True,
        # Publication date intentionally UNKNOWN; must not be guessed from action date.
        source_publication_date=None,
    )

RESEARCH_ACTIONS = (
    event("125807", "ORIGINAL", "2024-04-16", "complete_response",
          "https://download.open.fda.gov/crl/CRL_BLA125807_20240416.pdf"),
    event("125807", "RESUBMISSION-1", "2025-04-28", "approval",
          "https://www.fda.gov/media/186513/download"),
    event("125706", "ORIGINAL", "2020-09-30", "complete_response",
          "https://download.open.fda.gov/crl/CRL_BLA125706_20200930.pdf"),
    event("125706", "RESUBMISSION-1", "2023-08-01", "complete_response",
          "https://download.open.fda.gov/crl/CRL_BLA125706_20230801.pdf"),
    event("125706", "RESUBMISSION-2", "2024-12-18", "approval",
          "https://www.fda.gov/media/184605/download"),
    event("125827", "ORIGINAL", "2025-07-21", "complete_response",
          "https://download.open.fda.gov/crl/CRL_BLA125827_20250721.pdf"),
    event("125827", "RESUBMISSION-1", "2026-04-10", "complete_response",
          "https://download.open.fda.gov/crl/CRL_BLA125827_20260410.pdf"),
    event("125827", "RESUBMISSION-2", "2026-08-06", "accelerated_approval",
          "https://www.fda.gov/media/194128/download"),
    event("125806", "ORIGINAL", "2024-06-14", "complete_response",
          "https://download.open.fda.gov/crl/CRL_BLA125806_20240614.pdf"),
    event("125806", "RESUBMISSION-1", "2026-03-26", "accelerated_approval",
          "https://www.fda.gov/media/191723/download"),
    # Independently rechecked original FDA PDF letters (2026-10-26).
    # CYCLE-UNVERIFIED avoids asserting an unsupported resubmission ordinal.
    event("125743", "CYCLE-UNVERIFIED-2022", "2022-02-25", "complete_response",
          "https://download.open.fda.gov/crl/CRL_BLA125743_20220225.pdf"),
    event("125743", "CYCLE-UNVERIFIED-2023", "2023-12-15", "approval",
          "https://www.fda.gov/media/174897/download"),
    event("125745", "CYCLE-UNVERIFIED-2025", "2025-01-15", "complete_response",
          "https://download.open.fda.gov/crl/CRL_BLA125745_20250115.pdf"),
    event("125745", "CYCLE-UNVERIFIED-2026", "2026-01-09", "complete_response",
          "https://download.open.fda.gov/crl/CRL_BLA125745_20260109.pdf"),
    event("125734", "CYCLE-UNVERIFIED-2023", "2023-06-28", "approval",
          "https://www.fda.gov/media/169921/download"),
    # Primary FDA CRL letters visually verified on 2026-10-26.
    # No assumption about application review-cycle boundaries or resubmission order.
    event("125842", "CYCLE-UNVERIFIED-2025", "2025-07-09", "complete_response",
          "https://download.open.fda.gov/crl/CRL_BLA125842_20250709.pdf"),
    event("125840", "CYCLE-UNVERIFIED-2026", "2026-02-07", "complete_response",
          "https://download.open.fda.gov/crl/CRL_BLA125840_20260207.pdf"),
    event("125845", "ORIGINAL", "2025-07-07", "complete_response",
          "https://download.open.fda.gov/crl/CRL_BLA125845_20250707.pdf"),
    event("125845", "RESUBMISSION-1", "2026-09-17", "approval",
          "https://www.fda.gov/media/194921/download"),
)

def research_summary():
    actions = unique_final_actions(list(RESEARCH_ACTIONS))
    return {
        "applications_with_sampled_actions": len({e.application_key for e in actions.values()}),
        "sampled_action_endpoints": len(actions),
        "independently_certified_review_cycles": 0,
        "model_eligible_records": 0,
        "prediction_probability": ModelGate().prediction_probability,
        "complete_application_denominator_verified": False,
    }

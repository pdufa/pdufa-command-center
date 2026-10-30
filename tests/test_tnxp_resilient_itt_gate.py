from dataclasses import replace

from research.tnxp_resilient_itt_gate import Adjudication, Evidence, adjudicate, prediction_gate


def complete_flags():
    return Evidence(
        final_signed_sap=True,
        version_history=True,
        database_lock_timing=True,
        csr_population_listing=True,
        deviation_record=True,
        adjudication_record=True,
        all_randomized_sensitivity=True,
        authenticated_sources=True,
        explicit_conformance_finding=True,
    )


def test_missing_evidence_never_certifies():
    assert adjudicate(Evidence()) is Adjudication.UNRESOLVED
    baseline = complete_flags()
    for name in (
        "final_signed_sap", "version_history", "database_lock_timing",
        "csr_population_listing", "deviation_record",
        "adjudication_record", "all_randomized_sensitivity",
        "authenticated_sources",
    ):
        assert adjudicate(replace(baseline, **{name: False})) is Adjudication.UNRESOLVED
    assert adjudicate(replace(baseline, explicit_conformance_finding=None)) is Adjudication.UNRESOLVED


def test_self_asserted_complete_flags_cannot_certify():
    # Even every flag set True is not independently authenticated evidence.
    assert adjudicate(complete_flags()) is Adjudication.UNRESOLVED
    assert adjudicate(replace(complete_flags(), explicit_conformance_finding=False)) is Adjudication.UNRESOLVED


def test_research_gate_never_claims_prediction():
    assert prediction_gate(Evidence()) == "ABSTAIN"
    assert prediction_gate(complete_flags()) == "ABSTAIN"

"""Checks for exact-NCT Alkermes protocol/safety/clinical-applicability audit.

This snapshot preserves source facts rather than guessing unpublished Phase 3
efficacy, safety, FDA decisions, or protocol PDFs.
"""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "new-platform/frontend/data"


def read(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def test_all_34_alkermes_trials_reconcile_exactly_to_scoring_and_registry():
    audit = read("alks34ProtocolSafetyApplicabilityAudit20261106.json")
    score = read("alks34ClinicalScorecard20261106.json")
    registry = read("alks34RegistryDeepResults20261106.json")
    rows = audit["records"]
    ids = [x["nctId"] for x in rows]
    assert len(ids) == len(set(ids)) == 34
    assert all(re.fullmatch(r"NCT\d{8}", x) for x in ids)
    assert set(ids) == {x["nctId"] for x in score["records"]}
    assert set(ids) == {x["nctId"] for x in registry["records"]}
    by_registry = {x["nctId"]: x for x in registry["records"]}
    for x in rows:
        raw = by_registry[x["nctId"]]
        assert x["primaryEndpoint"]["definition"] == raw["primaryOutcomes"]
        assert x["evidence"]["registryResultsPosted"] == raw["postedResults"]
        assert x["sourceDocuments"]["registryProtocolAttached"] == raw["hasPublicProtocol"]
        assert x["sourceDocuments"]["registrySapAttached"] == raw["hasPublicSAP"]
        assert x["safety"]["seriousAdverseEventsByArm"] == (raw["seriousAdverseEventsByArm"] or None)
        assert x["retention"]["participantFlowByArm"] == (raw["participantFlowGroups"] or None)


def test_document_and_safety_counts_are_not_imputed():
    audit = read("alks34ProtocolSafetyApplicabilityAudit20261106.json")
    s = audit["summary"]
    assert s["trials"] == 34
    assert s["registeredPrimaryEndpoints"] == 34
    assert s["registryResultsPosted"] == 27
    assert s["noRegistryResultsPosted"] == 7
    assert s["publicProtocolAndSAPInSnapshot"] == 11
    assert s["protocolAndSapNotAttachedInSnapshot"] == 23
    assert s["primaryOutcomeStatisticalAnalysesPosted"] == 14
    assert s["armLevelSeriousAERecords"] == 27
    assert s["armLevelOtherAERecords"] == 27
    assert s["participantFlowRecords"] == 27
    assert s["withdrawalReasonRecords"] == 18
    assert s["unscoredUniversalQuestionSlotsInSnapshot"] == 546
    for r in audit["records"]:
        assert r["primaryEndpoint"]["sourceUrl"] == "https://clinicaltrials.gov/study/" + r["nctId"]
        assert not r["evidence"]["registryResultsPosted"] or r["evidence"]["postedPrimaryResults"]
        if not r["evidence"]["registryResultsPosted"]:
            assert not r["evidence"]["reportedPrimaryStatistics"]


def test_structural_na_does_not_erase_co_primary_or_fabricate_efficacy():
    audit = read("alks34ProtocolSafetyApplicabilityAudit20261106.json")
    s = audit["summary"]
    assert s["safetyPrimaryTrials"] == 15
    assert s["efficacyOrComparativePrimaryTrials"] == 19
    assert s["clinicalFactorsNotApplicable"] == 55
    assert s["safetyPrimaryTrialsWithCoPrimaryClinicalMeasure"] == 1
    assert s["primaryObjectiveOnlyNaQuestionTriageCount"] == 42
    assert {x["nctId"] for x in audit["records"] if x["studyPurpose"] == "SAFETY_PRIMARY"}
    special = next(x for x in audit["records"] if x["nctId"] == "NCT03201757")
    assert "CGI-S" in special["primaryEndpoint"]["definition"]
    assert not special["reviewApplicability"]["universalThirtyQuestionPrimaryObjectiveOnlyNotApplicable"]
    for r in audit["records"]:
        proposed = r["reviewApplicability"]["universalThirtyQuestionPrimaryObjectiveOnlyNotApplicable"]
        if r["studyPurpose"] != "SAFETY_PRIMARY":
            assert not proposed
        for q in proposed:
            assert q["disposition"] == "NOT_APPLICABLE_TO_PRIMARY_SAFETY_OBJECTIVE"
        if r["registryStatus"] in ("RECRUITING", "ENROLLING_BY_INVITATION"):
            assert r["evidence"]["documentaryHistoricalResult"] is None


def test_dated_interim_extension_evidence_is_not_final_pivotal_readout():
    audit = read("alks34ProtocolSafetyApplicabilityAudit20261106.json")
    alks2680 = next(x for x in audit["records"] if x["nctId"] == "NCT06767683")
    assert not alks2680["evidence"]["registryResultsPosted"]
    report = alks2680["additionalSourceEvidence"]
    assert report["evidenceType"] == "ISSUER_INTERIM_NOT_FINAL"
    assert report["dataCutoff"] == "2026-05-12"
    assert "phase 2" in report["observations"].lower()
    assert "not randomized" in report["limitations"].lower()


def test_site_exposes_audit_per_exact_nct_and_distinguishes_outcomes():
    page = (ROOT / "new-platform/frontend/app/alkermes-scores/page.tsx").read_text(encoding="utf-8")
    assert 'import researchAudit from "../../data/alks34ProtocolSafetyApplicabilityAudit20261106.json"' in page
    assert "data-alks-protocol-safety-audit" in page
    assert "data-alks-evidence-trial" in page
    assert "data-alks-evidence-expand" in page
    assert "do not overwrite the separate 30-question production assessment" in page

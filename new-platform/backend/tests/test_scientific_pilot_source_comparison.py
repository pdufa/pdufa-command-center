"""Historical KEYNOTE-024 cross-source observations are never trial certification.

Offline tests use mocked manifests only; no FDA network, no live DB, no trade writes.
"""
from __future__ import annotations

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app import main
from app import scientific_pilot_source_comparison as comparison
from app.scientific_reconciliation_worklist import reconciliation_worklist

NCT = "NCT02142738"
GOOGLE = {"Authorization": "Bearer test-only-Google-token"}


def _metadata(source_id, nct=NCT):
    url = comparison.SOURCES[source_id]["url"]
    return {
        "documentId": "a"*32 if source_id == "protocol_2017" else "b"*32,
        "gateId": "protocol_sap" if source_id == "protocol_2017" else "official_regulatory",
        "sourceUrl": url, "sha256": "f"*64 if source_id == "protocol_2017" else "e"*64,
        "byteLength": 2652084 if source_id == "protocol_2017" else 128330,
        "byteIntegrityChecked": True,
        "documentContentScientificallyVerified": False,
    }


@pytest.fixture
def archive(monkeypatch):
    original = {"documents": [_metadata("protocol_2017"), _metadata("fda_2016")],
                "sourceDocumentCount": 2}
    state = {"manifest_reads": 0, "ledger_reads": 0}
    def read_manifest(trial):
        assert trial == NCT
        state["manifest_reads"] += 1
        return deepcopy(original)
    def read_ledger(trial):
        assert trial == NCT
        state["ledger_reads"] += 1
        return {"verifiedGateCount": 0}
    monkeypatch.setattr(comparison, "read_document_manifest", read_manifest)
    monkeypatch.setattr(comparison, "read_ledger", read_ledger)
    return state


def test_eight_preliminary_questions_match_real_worklist_and_never_certify(archive):
    brief = comparison.preliminary_pilot_evidence_comparison(NCT)
    ids = {v["id"] for v in reconciliation_worklist(NCT)["checks"]}
    assert {check["questionId"] for check in brief["checks"]} == ids
    assert brief["checkCount"] == 8
    assert brief["unresolvedCount"] == 8
    assert brief["independentlyResolvedCount"] == 0
    assert brief["verifiedIndependentGates"] == 0
    assert brief["archivedPdfCount"] == 2
    assert brief["documentByteIntegrityChecked"] is True
    assert brief["historicalRegulatoryOutcomeKnown"] is True
    assert brief["scientificallyVerified"] is False
    assert brief["independentReplicationEstablished"] is False
    assert brief["mayAssignScientificScore"] is False
    assert brief["fdaApprovalProbability"] is None
    assert brief["tradingEnabled"] is False
    assert all(not row["independentlyResolved"] and
               row["criteriaSatisfied"] == 0 and
               not row["evidenceGateApproved"] for row in brief["checks"])
    assert all(row["documentContentScientificallyVerified"] is False
               for row in brief["archivedPdfManifests"])
    assert archive["manifest_reads"] == 1
    assert archive["ledger_reads"] == 1


def test_source_scoped_claims_protect_2016_vs_2020_2021_2017_windows(archive):
    rows={x["questionId"]:x for x in comparison.preliminary_pilot_evidence_comparison(NCT)["checks"]}
    protocol=rows["protocol_amendment_chronology"]
    assert "Japan" in protocol["preliminaryObservation"]
    assert "2017" in protocol["preliminaryObservation"]
    assert protocol["analysisBoundary"] == "2016-05-09"
    assert "pre-unblinding" in protocol["stillMissing"]
    assert protocol["journalProtocolSupplement"]["filename"] == "nejmoa1606774_protocol.pdf"
    assert protocol["journalProtocolSupplement"]["pdfContentRetrievedAndInspected"] is False
    assert protocol["journalProtocolSupplement"]["effectiveDateConfirmedBeforeAnalysis"] is False
    assert protocol["documentedPreAnalysisAmendment"]["number"] == "P024-03"
    assert protocol["documentedPreAnalysisAmendment"]["scope"] == "global"
    assert protocol["documentedPreAnalysisAmendment"]["dateFinalized"] == "2016-01-28"
    assert protocol["documentedPreAnalysisAmendment"]["secondAuthorityDateCorroboration"] is True
    assert protocol["documentedPreAnalysisAmendment"]["actualSignedSapRetrieved"] is False
    assert protocol["documentedPreAnalysisAmendment"]["prospectiveLockIndependentlyVerified"] is False
    assert "P024-03" in protocol["stillMissing"]
    assert "P024-04" in protocol["preliminaryObservation"]
    assert "P024-05" in protocol["preliminaryObservation"]
    assert "May 9, 2016" in protocol["preliminaryObservation"]
    assert protocol["reportedDesignNotYetIndependentlyAudited"]["oneSidedFamilyAlpha"] == 0.025
    assert protocol["reportedDesignNotYetIndependentlyAudited"]["oneSidedPfsInterimAlpha"] == 0.02
    assert protocol["reportedDesignNotYetIndependentlyAudited"]["fdaReportedInterimOsThreshold"] == 0.0118
    efficacy=rows["pfs_initial_vs_followup"]
    assert efficacy["initialPfs"]["cutoff"] == "2016-05-09"
    assert efficacy["initialPfs"]["hazardRatio"] == 0.5
    assert efficacy["initialPfs"]["reportedP"] == "<0.001"
    assert efficacy["initialInterimOs"]["hazardRatio"] == 0.60
    assert efficacy["initialInterimOs"]["reportedP"] == "0.005"
    assert efficacy["initialInterimOs"]["fda2019RetrospectiveInterimThreshold"] == "0.0118"
    assert efficacy["initialInterimOs"]["alphaAndPValueAreDifferentMeasures"] is True
    assert efficacy["longTermOs"]["cutoff"] == "2020-06-01"
    assert efficacy["longTermOs"]["hazardRatio"] == 0.62
    crossover=rows["crossover_adjustment"]
    assert crossover["effectiveCrossover"]["patientsWithSubsequentAntiPd1Pdl1"] == 99
    assert crossover["effectiveCrossover"]["reportedPercent"] == 66.0
    assert "not automatically" in crossover["preliminaryObservation"]
    safety=rows["safety_endpoint_taxonomy"]
    assert safety["reportedGrade3To5TraePercent"]["pembrolizumab"] == 26.6
    assert safety["reportedGrade3To5TraePercent"]["chemotherapy"] == 53.3
    qol=rows["exploratory_qol_multiplicity"]
    assert qol["reportedWeek15Difference"]["nominalP"] == "0.0020"
    assert qol["reportedWeek15Difference"]["ci95"] == [2.9,12.8]
    fda=rows["2015_vs_2016_fda_actions"]
    assert fda["historicalAction"]["firstLineSupplement"] == "BLA 125514/S-12"
    assert fda["historicalAction"]["previouslyTreatedSupplement"] == "BLA 125514/S-8"
    assert fda["historicalAction"]["signedDate"] == "2016-10-24"


def test_source_urls_are_https_curated_and_no_conflicting_claims(archive):
    brief = comparison.preliminary_pilot_evidence_comparison(NCT)
    for item in brief["sources"].values():
        assert item["url"].startswith("https://")
        assert item["locator"] and item["label"]
        assert item["kind"]
    for row in brief["checks"]:
        assert row["sourceIds"]
        assert all(source_id in brief["sources"] for source_id in row["sourceIds"])
        assert row["stillMissing"]
        assert "preliminary" in row["reviewStatus"]
    corroboration = next(x for x in brief["checks"]
                         if x["questionId"] == "independent_corroboration")
    assert "KEYNOTE-042" in corroboration["preliminaryObservation"]
    assert "multiplicity" in corroboration["preliminaryObservation"]
    assert corroboration["independentTrialIdentified"] is True
    assert corroboration["distinctEnrollmentTrial"]["trialId"] == "NCT02220894"
    assert corroboration["distinctEnrollmentTrial"]["totalRandomized"] == 1274
    assert corroboration["distinctEnrollmentTrial"]["highPdL1SubgroupRandomized"] == 599
    assert corroboration["distinctEnrollmentTrial"]["highPdL1SubgroupOs"]["hazardRatio"] == 0.69
    assert corroboration["distinctEnrollmentTrial"]["highPdL1SubgroupPfs"]["hazardRatio"] == 0.81
    assert corroboration["distinctEnrollmentTrial"]["highPdL1SubgroupPfs"]["significantUnderTrialMultiplicityRules"] is False
    assert corroboration["distinctEnrollmentTrial"]["independentlyMethodologicallyAdjudicated"] is False
    brief["checks"][0]["sourceIds"].clear()
    assert comparison.OBSERVATIONS["protocol_amendment_chronology"]["sourceIds"]
    brief["sources"]["fda_2016"]["url"]="https://changed.example"
    assert comparison.SOURCES["fda_2016"]["url"] != "https://changed.example"


def test_fail_closed_when_source_manifest_or_review_policy_changes(monkeypatch, archive):
    monkeypatch.setattr(comparison, "read_document_manifest",
                        lambda _: (_ for _ in ()).throw(ValueError("PDF SHA-256 tampered")))
    with pytest.raises(ValueError,match="PDF SHA-256"):
        comparison.preliminary_pilot_evidence_comparison(NCT)
    monkeypatch.setattr(comparison, "read_document_manifest",
                        lambda _: {"documents": [], "sourceDocumentCount": 0})
    monkeypatch.setattr(comparison, "read_ledger",
                        lambda _: {"verifiedGateCount": 1})
    with pytest.raises(ValueError,match="review policy"):
        comparison.preliminary_pilot_evidence_comparison(NCT)


def test_nonpilot_trial_fails_without_ledger_or_manifest_access(archive):
    with pytest.raises(LookupError):
        comparison.preliminary_pilot_evidence_comparison("NCT99999999")
    assert archive["manifest_reads"] == 0


@pytest.fixture
def operator_api(monkeypatch, archive):
    from app import scientific_google_identity
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE","single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL","owner@example.org")
    monkeypatch.setenv("RENDER_SERVICE_ID","srv-dbehn9fb9u1s739ok5vg")
    monkeypatch.setattr(main, "DATABASE_URL",
                        "postgresql+psycopg://isolated.invalid/test")
    monkeypatch.setattr(main, "_DB_STATE",{"available":True,"reason":"READY"})
    monkeypatch.setattr(scientific_google_identity,"verified_google_identity",
                        lambda _: {"verifiedEmail":"owner@example.org"})
    return TestClient(main.app)


def test_google_operator_readonly_endpoint_never_exposes_credentials(operator_api):
    noauth=operator_api.get("/api/scientific-assessment/operator/source-comparison/"+NCT)
    assert noauth.status_code==401
    ok=operator_api.get("/api/scientific-assessment/operator/source-comparison/"+NCT,
                        headers=GOOGLE)
    assert ok.status_code==200,ok.text
    assert "no-store" in ok.headers["cache-control"]
    assert ok.json()["archivedPdfCount"]==2
    assert ok.json()["scientificallyVerified"] is False
    assert ok.json()["verifiedIndependentGates"]==0
    assert "contentBase64" not in ok.text
    assert "test-only-Google-token" not in ok.text
    assert "owner@example.org" not in ok.text


def test_wrong_google_operator_and_other_trial_rejected(operator_api,monkeypatch):
    from app import scientific_google_identity
    monkeypatch.setattr(scientific_google_identity,"verified_google_identity",
                        lambda _: {"verifiedEmail":"unauthorized@example.org"})
    assert operator_api.get(
        "/api/scientific-assessment/operator/source-comparison/"+NCT,
        headers=GOOGLE).status_code==403
    monkeypatch.setattr(scientific_google_identity,"verified_google_identity",
                        lambda _: {"verifiedEmail":"owner@example.org"})
    assert operator_api.get(
        "/api/scientific-assessment/operator/source-comparison/NCT99999999",
        headers=GOOGLE).status_code==404


def test_operator_endpoint_returns_conflict_on_untrusted_archive(operator_api,monkeypatch):
    monkeypatch.setattr(comparison,"read_document_manifest",
                        lambda _: (_ for _ in ()).throw(ValueError("Metadata tampered")))
    response=operator_api.get(
        "/api/scientific-assessment/operator/source-comparison/"+NCT,
        headers=GOOGLE)
    assert response.status_code==409
    assert "Metadata tampered" not in response.text



def test_protocol_lead_is_not_misrepresented_as_preunblinding_approval(archive):
    report = comparison.preliminary_pilot_evidence_comparison(NCT)
    protocol = next(row for row in report["checks"]
                    if row["questionId"] == "protocol_amendment_chronology")
    assert protocol["independentlyResolved"] is False
    assert protocol["criteriaSatisfied"] == 0
    assert protocol["evidenceGateApproved"] is False
    assert report["sources"]["nejm_2016_protocol_lead"]["kind"] == (
        "publisher_supplement_link_not_content_verified")
    assert report["sources"]["german_regulator_2022_csr"]["kind"] == (
        "official_regulator_hosted_sponsor_report_retrospective")
    assert report["sources"]["german_regulator_2022_csr"]["locator"].find("P024-03") >= 0
    assert report["sources"]["eu_trial_amendments"]["kind"] == (
        "official_eu_trial_registry_amendment_history")
    assert report["sources"]["fda_2019_review"]["kind"] == (
        "official_fda_multidisciplinary_review_retrospective")
    assert protocol["journalProtocolSupplement"]["publicationYear"] == 2016
    assert "2016 publication date does not prove earlier lock" in protocol["stillMissing"]


def test_distinct_trial_replicates_os_direction_but_not_pfs_significance(archive):
    report = comparison.preliminary_pilot_evidence_comparison(NCT)
    study = next(row for row in report["checks"]
                 if row["questionId"] == "independent_corroboration")
    cohort = study["distinctEnrollmentTrial"]
    assert cohort["trialId"] != NCT
    assert cohort["sameParticipantsAsKeynote024"] is False
    assert cohort["noOnStudyChemoToPembroCrossover"] is True
    assert cohort["highPdL1SubgroupOs"]["prespecifiedEndpoint"] is True
    assert cohort["highPdL1SubgroupPfs"]["significantUnderTrialMultiplicityRules"] is False
    assert "KEYNOTE-042" in study["preliminaryObservation"]
    assert "discordant PFS" in study["stillMissing"]
    assert report["independentReplicationEstablished"] is False
    assert report["verifiedIndependentGates"] == 0
    assert report["scientificallyVerified"] is False
    assert report["mayAssignScientificScore"] is False
    assert report["fdaApprovalProbability"] is None

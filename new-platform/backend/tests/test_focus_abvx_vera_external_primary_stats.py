"""Exact trial source statistics never mutate registry analyses or backfill FDA outcomes."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/"research/source-links/FOCUS-ABVX-VERA-external-primary-stats-2026-11-17.json"

def load():
    return json.loads(SOURCE.read_text(encoding="utf-8"))

def test_trial_identifiers_and_archived_original_registry_receipts_are_fixed():
    data=load()
    rows={r["nctId"]:r for r in data["trials"]}
    assert set(rows)=={"NCT05507203","NCT05507216","NCT04716231"}
    assert rows["NCT05507203"]["sponsorStudyId"]=="ABX464-105"
    assert rows["NCT05507216"]["sponsorStudyId"]=="ABX464-106"
    assert rows["NCT04716231"]["sponsorStudyId"]=="VT-001-0050"
    assert all(len(r["registryPacketSha256"])==64 for r in rows.values())
    assert all(r["registryPrimaryAnalysesPosted"]==0 for r in rows.values())

def test_external_arm_counts_match_dose_specific_primary_results():
    rows={r["trialName"]:r for r in load()["trials"]}
    a={x["dose"]:x for x in rows["ABTECT-1"]["endpointResults"]["arms"]}
    b={x["dose"]:x for x in rows["ABTECT-2"]["endpointResults"]["arms"]}
    assert (a["placebo"]["responders"],a["obefazimod 50 mg"]["responders"],a["obefazimod 25 mg"]["responders"])==(4,69,38)
    assert (b["placebo"]["responders"],b["obefazimod 50 mg"]["responders"],b["obefazimod 25 mg"]["responders"])==(10,63,18)
    assert [x["n"] for x in a.values()]==[158,160,318]
    assert [x["n"] for x in b.values()]==[159,159,318]
    for r in (rows["ABTECT-1"],rows["ABTECT-2"]):
        assert len(r["endpointResults"]["comparisonsVersusPlacebo"])==2
        for x in r["endpointResults"]["arms"]:
            assert abs(100*x["responders"]/x["n"]-x["percentReported"])<0.1

def test_abtect_25mg_non_significant_in_trial_two_cannot_be_silently_promoted():
    rows={r["trialName"]:r for r in load()["trials"]}
    c={x["dose"]:x for x in rows["ABTECT-2"]["endpointResults"]["comparisonsVersusPlacebo"]}
    assert c["obefazimod 25 mg"]["pValueReported"]=="0.1034"
    assert c["obefazimod 25 mg"]["sponsorReportedSignificant"] is False
    assert c["obefazimod 50 mg"]["pValueReported"]=="0.0001"
    assert c["obefazimod 50 mg"]["sponsorReportedSignificant"] is True

def test_vera_phase3_is_not_confused_with_origin_phase2b_or_future_decision():
    v=next(x for x in load()["trials"] if x["ticker"]=="VERA")
    assert v["phaseAtFrozenSnapshot"]=="PHASE3"
    assert v["registryPrimaryTimeFrame"]=="36 Weeks"
    assert v["externalSource"]["doi"]=="10.1056/NEJMoa2510198"
    assert v["endpointResults"]["peerReviewedAbstractGeometricMeanBetweenGroupDifferencePercentagePoints"]==41.8
    assert v["endpointResults"]["confidenceInterval95PercentagePoints"]==[28.9,52.3]
    fda=v["regulatoryOutcomeSeparateFromPrediction"]
    assert fda["actionDate"]=="2026-07-07"
    assert fda["applicationNumber"]=="761486"
    assert fda["approvalType"]=="ACCELERATED_APPROVAL"
    assert fda["mustNeverEnterFrozenHistoricalPredictorFeatures"] is True

def test_sources_are_not_scientific_signoff_or_blind_historical_prediction():
    d=load()
    assert d["counts"]["focusTrialsWithExternalStatisticalEvidence"]==3
    assert d["counts"]["trialDoseComparisons"]==5
    assert d["counts"]["knownFdaHistoricalOutcomesRecordedSeparately"]==1
    assert d["scientificReviewComplete"] is False
    assert d["productionWriteAllowed"] is False
    assert "STRICT_EVIDENCE_DATE" in d["historicalBlindBacktestPolicy"]
    for row in d["trials"]:
        assert row["clinicalScientificReviewComplete"] is False
        assert row["score"] is None and row["prediction"]=="ABSTAIN"
        assert row["registryStatisticalComparisonStillAbsent"] is True
        assert row["endpointResults"].get("independentStatisticalReplication",False) is False

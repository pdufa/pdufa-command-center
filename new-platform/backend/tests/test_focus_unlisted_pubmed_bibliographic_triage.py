"""Biblio NCT mentions must not be equated with trial efficacy or FDA prediction."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FILE = REPO / "research/source-links/focus-unlisted-pubmed-bibliographic-triage-2026-11-17.json"

def record():
    return json.loads(FILE.read_text(encoding="utf-8"))

def test_all_nine_unlisted_trial_pmid_associations_are_counted():
    r=record()
    rows=r["entries"]
    assert len(rows)==r["counts"]["trialPmidAssociations"]==9
    assert len({x["pmid"] for x in rows})==r["counts"]["uniquePmids"]==8
    assert len({x["nctId"] for x in rows})==r["counts"]["focusTrials"]==4
    assert {x["ticker"] for x in rows}=={"BLTE","APMD","AMLX"}
    assert sum(x["pmid"]=="41050845" for x in rows)==2
    assert len({(x["nctId"],x["pmid"]) for x in rows})==9

def test_bibliographic_titling_cannot_promote_background_to_trial_success():
    r=record()
    for x in r["entries"]:
        assert x["sourceUrl"]=="https://pubmed.ncbi.nlm.nih.gov/"+x["pmid"]+"/"
        assert x["hasExactNctPubmedSearchLead"] is True
        assert x["listedAsReferenceInCapturedRegistryPacket"] is False
        assert x["canServeAsDirectEfficacyEvidence"] is False
        assert x["independentClinicalAdjudicationComplete"] is False
        assert x["predictionEligibility"]=="ABSTAIN"
    assert r["verifiedTrialEfficacyAssociations"]==0
    assert r["clinicalScientificReviewComplete"] is False
    assert r["scientificScoresComputed"]==0
    assert r["fdaPredictionsComputed"]==0
    assert r["productionWritesAllowed"] is False

def test_same_nct_match_can_be_context_and_not_endpoint_effect():
    rows=record()["entries"]
    aml=[x for x in rows if x["ticker"]=="AMLX"]
    assert len(aml)==1 and aml[0]["sourceType"]=="DIFFERENT_INTERVENTION_AND_TRIAL"
    apmd=[x for x in rows if x["ticker"]=="APMD"]
    assert len(apmd)==3
    assert {x["sourceType"] for x in apmd}=={"TRIAL_DESIGN_BASELINE_SOURCE","OUTCOME_MEASURE_VALIDITY_CONTEXT"}

"""R69 archived literal PubMed leads are not verified exact-study outcomes."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import pytest

from scripts.build_focus_original_literature_leads_r69 import (
    build, read_file, R46_SHA, R66_SHA, SCHEMA
)
from scripts.refresh_focus_public_sources_r40 import (
    ROSTER, APPS, _read_json, build_manifest
)

def source():
    names=("R69_R46","R69_R66","R69_REGISTRY_DIR")
    if any(not os.environ.get(name) for name in names):
        pytest.skip("Original R46/R66 registry research artifacts are not mounted in this generic test environment")
    manifest=build_manifest(_read_json(ROSTER),_read_json(APPS))
    r46,h46=read_file(Path(os.environ["R69_R46"]))
    r66,h66=read_file(Path(os.environ["R69_R66"]))
    assert h46==R46_SHA and h66==R66_SHA
    return manifest,r46,r66,Path(os.environ["R69_REGISTRY_DIR"])

def research(originals=None):
    manifest,r46,r66,dir=source()
    return build(manifest,r46,r66,originals or dir,
                 hashes={"r46":R46_SHA,"r66":R66_SHA})

def test_17_missing_original_results_have_11_unreviewed_pubmed_leads_from_7_ncts():
    r=research()
    assert r["schema"]==SCHEMA
    assert r["canonicalUniqueNcts"]==29
    assert r["provisionalApplicationCycles"]==23
    assert r["originalRegistryNoCurrentPrimaryTrials"]==17
    assert r["missingPrimaryTrialsWithPubmedReferenceLeads"]==7
    assert r["missingPrimaryTrialsWithoutPubmedReferenceLeads"]==10
    assert r["registryListedUnverifiedPubmedReferences"]==11
    assert len(r["missingPrimaryLiteratureReviewQueue"])==17
    assert len(r["all29OriginalReferenceCensus"])==29
    assert len({x["nct"] for x in r["missingPrimaryLiteratureReviewQueue"]})==17
    assert r["independentlyVerifiedArticlesReportingExactTrialPrimary"]==0
    assert r["independentlyQualifiedReviewerAssessments"]==0
    assert r["validatedFutureFDAForecasts"]==0
    assert r["FDAOutcome"]=="ABSTAIN"
    assert r["measuredPredictionAccuracy"] is None
    assert r["registryReferenceCannotEstablishTrialEfficacy"] is True
    assert r["externalArticlesNotFetchedOrContentAdjudicated"] is True
    assert r["historicalBacktestDataInspected"] is False
    assert r["modelTrainingOrProductionWrites"] is False
    for trial in r["missingPrimaryLiteratureReviewQueue"]:
        assert trial["currentRegistryPrimaryTables"]==0
        assert trial["independentEfficacyAssessment"] is None
        assert trial["independentSafetyAssessment"] is None
        assert trial["scientificMethodGrade"] is None
        assert trial["officialFdaForecast"]=="ABSTAIN"
        assert trial["mustVerifyExactNctInFullPublication"] is True
        for item in trial["registryDerivedPubmedReferenceLeads"]:
            assert item["registryReferenceType"]=="DERIVED"
            assert item["pmid"].isdigit()
            assert item["pubmedUrl"]=="https://pubmed.ncbi.nlm.nih.gov/"+item["pmid"]+"/"
            assert item["articleContentIndependentlyInspected"] is False
            assert item["exactNctMentionInArticleVerified"] is False
            assert item["paperReportsPivotalPrimaryOutcomeVerified"] is False
            assert item["independentQualifiedPublicationReviewSigned"] is False

def test_selected_exact_pmid_crosswalk_is_the_registered_lead_not_trial_result():
    rows={x["nct"]:x for x in research()["missingPrimaryLiteratureReviewQueue"]}
    assert [x["pmid"] for x in rows["NCT02500381"]["registryDerivedPubmedReferenceLeads"]]==["40098309","34105177"]
    assert [x["pmid"] for x in rows["NCT04871282"]["registryDerivedPubmedReferenceLeads"]]==["42848980"]
    assert [x["pmid"] for x in rows["NCT05126758"]["registryDerivedPubmedReferenceLeads"]]==["42526472"]
    assert [x["pmid"] for x in rows["NCT05662241"]["registryDerivedPubmedReferenceLeads"]]==["42233621","41840328"]
    assert [x["pmid"] for x in rows["NCT06081894"]["registryDerivedPubmedReferenceLeads"]]==["42667274","42663312","42663111"]
    assert [x["pmid"] for x in rows["NCT06153693"]["registryDerivedPubmedReferenceLeads"]]==["40587141"]
    assert [x["pmid"] for x in rows["NCT06343779"]["registryDerivedPubmedReferenceLeads"]]==["42849489"]
    assert rows["NCT05059223"]["registryDerivedPubmedReferenceLeads"]==[]

def test_original_r46_or_r66_scientific_status_forgery_is_rejected():
    manifest,r46,r66,dir=source()
    mutators=[
      lambda a,b:a.update(registryRecordsFetched=1),
      lambda a,b:a.update(scientificGradesWritten=11),
      lambda a,b:a["records"][0].update(sourceResponseSha256="0"*64),
      lambda a,b:b.update(independentlyQualifiedPhaseReviews=29),
      lambda a,b:b.update(futureFDAOutcomePredictionsValidated=23),
      lambda a,b:b["originalRegistryPhaseEvidence"][0].update(independentPhaseReviewEventId="signed"),
      lambda a,b:b["originalRegistryPhaseEvidence"][0].update(applicationCycleIds=["forged"]),
    ]
    for change in mutators:
        a,b=copy.deepcopy(r46),copy.deepcopy(r66)
        change(a,b)
        with pytest.raises(ValueError):
            build(manifest,a,b,dir,hashes={"r46":R46_SHA,"r66":R66_SHA})

def test_modified_original_reference_bytes_fail_same_original_sha_receipt(tmp_path):
    manifest,r46,r66,dir=source()
    target=tmp_path/"registry"
    target.mkdir()
    for path in dir.glob("NCT*.json"):
        (target/path.name).write_bytes(path.read_bytes())
    n=target/"NCT06081894.json"
    raw=json.loads(n.read_text())
    raw["protocolSection"]["referencesModule"]["references"].pop()
    n.write_text(json.dumps(raw))
    with pytest.raises(ValueError,match="ORIGINAL_REGISTRY_HASH_OR_APPLICATION_EDGE_CHANGED"):
        build(manifest,r46,r66,target,hashes={"r46":R46_SHA,"r66":R66_SHA})

def test_shared_trial_does_not_become_two_independent_papers():
    row=next(x for x in research()["missingPrimaryLiteratureReviewQueue"]
             if x["nct"]=="NCT02500381")
    assert len(row["applicationCycleIds"])==2
    assert row["originalRegistryLiteratureLeadCount"]==2

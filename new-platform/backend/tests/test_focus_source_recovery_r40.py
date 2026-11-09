"""MAIN Rev40 public-source recovery: deterministic synthetic tests, no FDA grades."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path

import pytest
from scripts.refresh_focus_public_sources_r40 import (
    APPS,ROSTER,_valid_url,build_manifest,perform_capture,
)
# APP is an expected filename? No: only verify exact source files from ROOT.
from scripts.refresh_focus_public_sources_r40 import _read_json

def current():
    return _read_json(ROSTER),_read_json(APPS)

def simulated_fetch(url):
    if "/api/v2/studies/" in url:
        nct=url.split("?")[0].split("/")[-1]
        body=json.dumps({
            "protocolSection":{
                "identificationModule":{"nctId":nct},
                "statusModule":{"overallStatus":"COMPLETED",
                  "lastUpdatePostDateStruct":{"date":"2026-11-08"}},
                "designModule":{"phases":["PHASE3"]}
            },
            "resultsSection":{"outcomeMeasuresModule":{"outcomeMeasures":[]}}
        }).encode()
    else:
        body=b"<html><body>Example synthetic issuer source; not real medical data.</body></html>"
    return {"status":"FETCHED","url":url,"resolvedUrl":url,
            "contentType":"application/json" if body.startswith(b"{") else "text/html",
            "bytes":len(body),"sha256":"a"*64},body

def test_canonical_roster_is_exact_29_23_with_shared_trials_and_two_sarepta_supplements():
    manifest=build_manifest(*current())
    assert manifest["trialCount"]==29
    assert manifest["applicationCount"]==23
    assert len(manifest["trialRows"])==29
    assert len(manifest["applicationGroups"])==23
    assert len({x["nct"] for x in manifest["trialRows"]})==29
    apps={x["cycleId"]:x for x in manifest["applicationGroups"]}
    assert apps["srpt-casimersen"]["ncts"]==["NCT02500381"]
    assert apps["srpt-golodirsen"]["ncts"]==["NCT02500381"]
    assert apps["cytk-aficamten-ohcm"]["ncts"]==["NCT05767346"]
    assert apps["cytk-aficamten-nhcm"]["ncts"]==["NCT06081894"]
    assert manifest["qualifiedScientificReviews"]==0
    assert manifest["modelTrainingAuthorized"] is False

def test_synthetic_capture_produces_29_registry_and_complete_23_app_source_receipts_without_model_release():
    manifest=build_manifest(*current())
    result=perform_capture(manifest,fetcher=simulated_fetch)
    assert result["trialRoster"]==29
    assert result["provisionalApplicationGroups"]==23
    assert result["clinicalTrialsGovRecordsFetched"]==29
    assert result["applicationSourceUrlsFetched"]==result["uniqueApplicationSourceUrls"]
    assert result["canonicalApplicationSourceUrls"]==21
    assert result["additionalOfficialSecSourceUrls"]==1
    assert result["uniqueApplicationSourceUrls"]==22
    assert result["applicationGroupsWithAvailablePublicSource"]==23
    assert len(result["applicationGroups"])==23
    assert len(result["trialSources"])==29
    assert all(x["registryIdentityMatches"] is True for x in result["trialSources"])
    assert all(x["scientificPhaseIndependentlyVerified"] is False for x in result["trialSources"])
    assert all(x["originalRegulatorReviewCycleVerified"] is False for x in result["applicationGroups"])
    assert all(x["qualifiedReviewerSignoff"] is False for x in result["applicationGroups"])
    assert result["independentlyValidatedApplicationForecasts"]==0
    assert result["numericalApprovalProbability"] is None
    assert result["calibratedAccuracy"] is None
    assert result["modelTrainingAuthorized"] is False
    assert result["noClinicalOrProductionWrites"] is True
    assert sum(x["formalFdaActionPrediction"]=="NOT_APPLICABLE_ALREADY_OBSERVED"
               for x in result["applicationGroups"])==1
    assert sum(x["formalFdaActionPrediction"]=="ABSTAIN"
               for x in result["applicationGroups"])==22

def test_issuer_403_does_not_imply_trial_failure_or_regulatory_crl():
    manifest=build_manifest(*current())
    blocked=manifest["applicationGroups"][0]["sourceUrl"]
    def fetch(url):
        if url==blocked:return {"url":url,"status":"HTTP_UNAVAILABLE","httpStatus":403},None
        return simulated_fetch(url)
    result=perform_capture(manifest,fetcher=fetch)
    assert result["applicationSourceUrlsFetched"]==result["uniqueApplicationSourceUrls"]-1
    assert result["clinicalTrialsGovRecordsFetched"]==29
    assert all(x["formalFdaActionPrediction"] in
               ("ABSTAIN","NOT_APPLICABLE_ALREADY_OBSERVED") for x in result["applicationGroups"])
    assert result["qualifiedClinicalReviews"]==0

def test_clinicaltrials_registry_id_mismatch_blocks_fake_verification():
    manifest=build_manifest(*current())
    def fetch(url):
        if "/api/v2/studies/" in url:
            obs,body=simulated_fetch(url)
            bad=json.loads(body)
            bad["protocolSection"]["identificationModule"]["nctId"]="NCT00000000"
            return obs,json.dumps(bad).encode()
        return simulated_fetch(url)
    result=perform_capture(manifest,fetcher=fetch)
    assert result["clinicalTrialsGovRecordsFetched"]==0
    assert all(x["status"]=="REGISTRY_IDENTITY_MISMATCH" for x in result["trialSources"])
    assert result["independentlyValidatedApplicationForecasts"]==0

def test_source_url_allowlist_prevents_internal_and_untrusted_redirect_destinations():
    assert _valid_url("https://www.sec.gov/Archives/edgar/data/123/abc.htm")
    assert _valid_url("https://clinicaltrials.gov/api/v2/studies/NCT01234567?format=json")
    for url in [
        "http://www.sec.gov/a","https://127.0.0.1/a",
        "https://localhost/private","https://169.254.169.254/latest/meta-data",
        "https://www.sec.gov@bad.example/private",
        "https://www.sec.gov:444/a",
        "https://www.sec.gov/",
        "file:///etc/passwd","https://untrusted.example/a",
    ]:assert not _valid_url(url),url

@pytest.mark.parametrize("kind",["unexpected_nct","extra_nct","new_cycle","unsafe_link","changed_stage","future_source"])
def test_roster_or_application_drift_fails_closed(kind):
    roster,apps=current()
    if kind=="unexpected_nct":apps["records"][0]["nct"]="NCT00000000"
    elif kind=="extra_nct":roster["records"].append(deepcopy(roster["records"][0]))
    elif kind=="new_cycle":apps["records"][0]["candidateApplications"][0]["cycleId"]="different-cycle"
    elif kind=="unsafe_link":apps["records"][0]["candidateApplications"][0]["sourceUrl"]="http://localhost/"
    elif kind=="changed_stage":apps["records"][0]["candidateApplications"][0]["stage"]="FDA_APPROVED_CERTIFIED"
    elif kind=="future_source":apps["records"][0]["candidateApplications"][0]["sourceDate"]="2026-12-01"
    with pytest.raises(ValueError):build_manifest(roster,apps)


def test_achieve_recovered_using_official_sec_10q_if_issuer_redirects():
    manifest=build_manifest(*current())
    achieve=next(g for g in manifest["applicationGroups"] if g["cycleId"]=="achv-cytisinicline")
    assert achieve["sourceUrl"].startswith("https://ir.achievelifesciences.com/")
    def blocked_issuer(url):
        if url==achieve["sourceUrl"]:
            return {"url":url,"status":"HTTP_UNAVAILABLE","httpStatus":301},None
        return simulated_fetch(url)
    result=perform_capture(manifest,fetcher=blocked_issuer)
    achv=next(a for a in result["applicationGroups"] if a["cycleId"]=="achv-cytisinicline")
    assert achv["applicationSource"]["status"]=="HTTP_UNAVAILABLE"
    assert achv["alternateOfficialSecSource"]["status"]=="FETCHED"
    assert achv["alternateOfficialSecSource"]["url"]=="https://www.sec.gov/Archives/edgar/data/949858/000119312526344624/achv-20260630.htm"
    assert achv["atLeastOneApplicationSourceFetched"] is True
    assert result["applicationGroupsWithAvailablePublicSource"]==23
    assert result["qualifiedClinicalReviews"]==0

def test_issuer_and_alternate_both_blocked_leave_application_in_research_not_crl():
    manifest=build_manifest(*current())
    achieve=next(g for g in manifest["applicationGroups"] if g["cycleId"]=="achv-cytisinicline")
    def blocked_both(url):
        if url==achieve["sourceUrl"] or "949858/000119312526344624" in url:
            return {"url":url,"status":"HTTP_UNAVAILABLE","httpStatus":403},None
        return simulated_fetch(url)
    result=perform_capture(manifest,fetcher=blocked_both)
    a=next(x for x in result["applicationGroups"] if x["cycleId"]=="achv-cytisinicline")
    assert a["atLeastOneApplicationSourceFetched"] is False
    assert result["applicationGroupsWithAvailablePublicSource"]==22
    assert a["formalFdaActionPrediction"]=="ABSTAIN"
    assert result["independentlyValidatedApplicationForecasts"]==0


def test_raw_source_capture_is_exact_and_digest_mismatches_fail_closed(tmp_path):
    import hashlib
    manifest=build_manifest(*current())
    def actual_bytes(url):
        receipt,body=simulated_fetch(url)
        return {**receipt,"sha256":hashlib.sha256(body).hexdigest()},body
    raw=tmp_path/"raw";raw.mkdir()
    result=perform_capture(manifest,fetcher=actual_bytes,raw_dir=raw)
    assert len(list(raw.iterdir()))==51
    assert all(r["originalByteDigestVerified"] for r in result["trialSources"])
    with pytest.raises(ValueError,match="NEW_EMPTY"):perform_capture(manifest,fetcher=actual_bytes,raw_dir=raw)
    other=tmp_path/"other";other.mkdir()
    with pytest.raises(ValueError,match="DIGEST_MISMATCH"):perform_capture(manifest,fetcher=simulated_fetch,raw_dir=other)


def test_optional_original_fda_records_keep_prior_actions_separate_from_new_predictions():
    manifest=build_manifest(*current())
    result=perform_capture(manifest,fetcher=simulated_fetch,include_fda_addenda=True)
    assert result['additionalOriginalFdaSourceUrls']==2
    assert result['uniqueApplicationSourceUrls']==24
    groups={g['cycleId']:g for g in result['applicationGroups']}
    assert groups['capr-deramiocel']['additionalOfficialFdaSources'][0]['sourceRole']=='FDA_STAFF_PRE_AMENDMENT_NOT_FINAL_ACTION'
    assert groups['capr-deramiocel']['formalFdaActionPrediction']=='ABSTAIN'
    assert groups['cytk-aficamten-ohcm']['additionalOfficialFdaSources'][0]['sourceRole']=='PRIOR_OBSTRUCTIVE_APPROVAL_NOT_CURRENT_TRIAL_REVIEW_CYCLE'
    assert result['scientificMethodGradesWritten']==0 and result['calibratedAccuracy'] is None

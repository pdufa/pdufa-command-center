"""Synthetic Rev38 FDA source-recapture tests. Nothing here is historical model data."""
from copy import deepcopy
from datetime import date
import hashlib,json
from importlib.util import spec_from_file_location,module_from_spec
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=spec_from_file_location("rev38",ROOT/"scripts/refresh_hop_fda_action_candidates.py")
module=module_from_spec(spec)
spec.loader.exec_module(module)
BENCH=json.loads((ROOT/"app/research_sources/hop_fda_pdufa_filing_benchmarks.json").read_text())
CUTOFF=date(2026,11,9)

def snapshots():
    approved={"status":"APPROVED_REGISTRY_NOT_COMPLETE_DECISION_COHORT",
      "source_export_date":"2026-10-23","retrieved_on":"2026-10-25",
      "records":[{
        "application_number_as_published":"NDA123456",
        "submissions_as_published":[{
          "submission_type_as_published":"ORIG",
          "submission_number_as_published":"1",
          "submission_status_as_published":"AP",
          "submission_status_date_as_published":"20240420"
        }],
        "record_sha256":"a"*64,"model_eligible":False,
        "complete_application_denominator_verified":False,
        "review_cycles_independently_adjudicated":False,
        "point_in_time_features_verified":False
      }]}
    crl={"status":"QUARANTINED_NOT_A_COMPLETE_APPLICATION_COHORT",
      "source_export_date":"2026-10-21","retrieved_on":"2026-10-25",
      "records":[{
        "letter_date_as_published":"04/21/2024",
        "letter_type_as_published":"COMPLETE RESPONSE",
        "application_numbers":["BLA 761303/Original 1"],
        "source_record_sha256":"b"*64,
        "model_eligible":False,"independently_verified":False,
        "cohort_complete_verified":False
      }]}
    return approved,crl

def test_source_union_is_research_only_with_distinct_filing_denominator():
    approved,crl=snapshots()
    report,rows=module.research_refresh(approved,crl,BENCH,CUTOFF)
    assert len(rows)==report["researchCandidateRows"]==2
    assert [row["sourceAction"] for row in rows]==["AP","COMPLETE RESPONSE"]
    assert all(row["modelEligible"] is False for row in rows)
    assert report["modelEligibleHistoricalCases"]==0
    assert report["trainingAuthorized"] is False
    assert report["approvalProbability"] is None
    assert report["measuredAccuracy"] is None
    assert report["completeOriginalApplicationFilingRosterVerified"] is False
    assert all(y["filingDenominatorCoverage"] is None for y in report["fiscalActionYearSourceCandidates"])

def test_source_promotion_duplicate_or_bad_cutoff_refused():
    a,c=snapshots()
    a["records"][0]["model_eligible"]=True
    with pytest.raises(ValueError):
        module.research_refresh(a,c,BENCH,CUTOFF)
    a,c=snapshots()
    c["records"].append(deepcopy(c["records"][0]))
    with pytest.raises(ValueError):
        module.research_refresh(a,c,BENCH,CUTOFF)
    a,c=snapshots()
    with pytest.raises(ValueError):
        module.research_refresh(a,c,BENCH,date(2026,10,24))

def test_replay_source_bytes_sha_and_no_overwriting(tmp_path):
    a,c=snapshots()
    ap=tmp_path/module.APP
    cr=tmp_path/module.CRL
    out=tmp_path/"derived"
    out.mkdir()
    ap.write_text(json.dumps(a))
    cr.write_text(json.dumps(c))
    receipt=module.write_snapshot(ap,cr,out,CUTOFF)
    assert receipt["sourceProvenance"]["approvedRegistry"]["sha256"]==hashlib.sha256(ap.read_bytes()).hexdigest()
    assert receipt["sourceProvenance"]["selectedCrl"]["sha256"]==hashlib.sha256(cr.read_bytes()).hexdigest()
    assert hashlib.sha256((out/"r38_fda_source_candidates.json").read_bytes()).hexdigest()==receipt["candidateFileSha256"]
    assert receipt["retentionLimit"]=="GITHUB_ARTIFACT_90_DAYS_NOT_PERMANENT_BACKUP"
    assert receipt["modelEligibleHistoricalCases"]==0
    with pytest.raises(ValueError,match="OVERWRITE"):
        module.write_snapshot(ap,cr,out,CUTOFF)

def test_duplicate_json_properties_and_unapproved_source_paths_refused(tmp_path):
    a,c=snapshots()
    ap=tmp_path/module.APP
    cr=tmp_path/module.CRL
    out=tmp_path/"derived"
    out.mkdir()
    ap.write_text('{"records":[],"records":[]}')
    cr.write_text(json.dumps(c))
    with pytest.raises(ValueError,match="DUPLICATE_FDA_SOURCE_JSON_PROPERTY"):
        module.write_snapshot(ap,cr,out,CUTOFF)
    ap.write_text(json.dumps(a))
    fake=tmp_path/"fake.json"
    fake.write_text(json.dumps(c))
    with pytest.raises(ValueError,match="INVALID_FDA_SOURCE_PATH"):
        module.write_snapshot(ap,fake,out,CUTOFF)

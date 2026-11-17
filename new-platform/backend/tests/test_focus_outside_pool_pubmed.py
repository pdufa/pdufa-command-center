"""Three FOCUS-only exact-NCT source paths, no live search or clinical scoring."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "focus_only_pubmed_test", ROOT / "scripts/medical/focus_outside_pool_pubmed.py")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)
A,B,C = "NCT05126758","NCT06343779","NCT06669754"


def sources(tmp_path):
    focus = tmp_path / "focus.json"
    pool = tmp_path / "pool.json"
    focus.write_text(json.dumps({"asOf": "2026-11-17", "records": [
        {"nct": "NCT00000001"}, {"nct": A}, {"nct": B}, {"nct": C}
    ]}))
    pool.write_text(json.dumps({"pipeline": [
        {"id": "TRIAL|NCT00000001"}, {"id": "RESULT|DOES_NOT_COUNT"}
    ]}))
    return focus,pool


def hit(nct):
    return {"nct": nct, "status": "QUERY_SUCCEEDED_UNREVIEWED",
            "reportedTotalHits": 1, "publicationLeads": [
        {"pmid": "12345", "url": "https://pubmed.ncbi.nlm.nih.gov/12345/",
         "status": "UNREVIEWED_LEAD", "exactTrialLinkVerified": False,
         "clinicalFinding": None}]}


def test_all_three_focus_only_are_separate_unreviewed_leads(tmp_path):
    f,p=sources(tmp_path)
    all_focus, excluded = mod.exact_focus_outside_pool(
        json.loads(f.read_text()), json.loads(p.read_text()))
    assert len(all_focus)==4
    assert excluded==[A,B,C]
    seen=[]
    output=tmp_path/"unreviewed.json"
    result=mod.collect(f,p,output,searcher=lambda n: (seen.append(n),hit(n))[1],
                       pause=lambda _: None)
    assert seen==[A,B,C]
    assert result["focusOnlyCount"]==3
    assert result["queriesSucceeded"]==3
    assert result["publicationLeadsUnreviewed"]==3
    assert result["scientificReviewsCompleted"]==0
    assert result["fdaPredictionsComputed"]==0
    assert result["verifiedClinicalFindings"] is False
    assert json.loads(output.read_text())==result


def test_partial_failure_retry_only_failed_focus_nct(tmp_path):
    f,p=sources(tmp_path)
    output=tmp_path/"leads.json"
    def first(nct):
        if nct==B:
            raise TimeoutError("synthetic source outage")
        return hit(nct)
    r=mod.collect(f,p,output,searcher=first,pause=lambda _: None)
    assert r["queriesFailed"]==1 and r["queriesSucceeded"]==2
    calls=[]
    r2=mod.collect(f,p,output,resume=True,
                   searcher=lambda n:(calls.append(n),hit(n))[1],
                   pause=lambda _: None)
    assert calls==[B]
    assert r2["queriesSucceeded"]==3
    assert r2["scientificReviewsCompleted"]==0


def test_wrong_trial_response_and_source_roster_change_fail_closed(tmp_path):
    f,p=sources(tmp_path)
    output=tmp_path/"leads.json"
    r=mod.collect(f,p,output,searcher=lambda n:hit("NCT00000001"),
                  pause=lambda _: None)
    assert r["queriesFailed"]==3
    with pytest.raises(ValueError,match="research artifact exists"):
        mod.collect(f,p,output,searcher=hit,pause=lambda _: None)
    saved=json.loads(output.read_text())
    saved["rows"][0]["status"]="QUERY_SUCCEEDED_UNREVIEWED"
    output.write_text(json.dumps(saved))
    with pytest.raises(ValueError):
        mod.collect(f,p,output,resume=True,searcher=hit,pause=lambda _: None)
    output.write_text(json.dumps(r))
    f.write_text(f.read_text()+"\n")
    with pytest.raises(ValueError,match="scope"):
        mod.collect(f,p,output,resume=True,searcher=hit,pause=lambda _: None)


def test_duplicate_or_unrelated_nct_is_rejected(tmp_path):
    f,p=sources(tmp_path)
    focus=json.loads(f.read_text())
    focus["records"].append({"nct":A})
    with pytest.raises(ValueError,match="duplicate"):
        mod.exact_focus_outside_pool(focus,json.loads(p.read_text()))
    focus["records"][-1]={"nct":"https://example.com/"}
    with pytest.raises(ValueError,match="Malformed"):
        mod.exact_focus_outside_pool(focus,json.loads(p.read_text()))

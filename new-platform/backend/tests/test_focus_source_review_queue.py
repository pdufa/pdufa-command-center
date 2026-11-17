"""Synthetic source-only scientific queue; no live NCBI, FDA or trial data."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "scripts/medical/focus_source_review_queue.py"
spec = importlib.util.spec_from_file_location("focus_queue_synthetic_test", MODULE)
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)


def packet(nct, posted=False):
    raw = {"protocolSection": {
        "identificationModule": {"nctId": nct},
        "statusModule": {"overallStatus": "COMPLETED"},
        "outcomesModule": {"primaryOutcomes": [{"measure": "Primary", "timeFrame": "Day 28"}]}
    }}
    if posted:
        raw["resultsSection"] = {"outcomeMeasuresModule": {"outcomeMeasures": [
            {"type": "PRIMARY", "title": "Primary", "timeFrame": "Day 28"}]}}
    return raw


def setup(tmp_path):
    a, b = "NCT00000001", "NCT00000002"
    focus = tmp_path / "p3PostDataActive.json"
    pool = tmp_path / "tools-pool-snapshot.json"
    focus.write_text(json.dumps({"asOf": "2026-11-17", "records": [
        {"nct": a, "ticker": "AAA"}, {"nct": b, "ticker": "BBB"}]}))
    pool.write_text(json.dumps({"asOf": "2026-11-17", "pipeline": [{"id": "TRIAL|" + a}]}))
    fsha=hashlib.sha256(focus.read_bytes()).hexdigest()
    psha=hashlib.sha256(pool.read_bytes()).hexdigest()
    reg=tmp_path / "registry"
    cache=reg / "registry-cache"
    cache.mkdir(parents=True)
    state={"sources": {}}
    for nct,posted in [(a,True),(b,False)]:
        obj=packet(nct,posted)
        digest=hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
        path="registry-cache/"+nct+".json"
        (reg/path).write_text(json.dumps(obj))
        state["sources"][nct]={"versions":[{"fingerprint":digest,"cachePath":path}]}
    (reg/"ingestion-state.json").write_text(json.dumps(state))
    inventory={
        "asOf":"2026-11-17",
        "sourceFiles":[
          {"path":"new-platform/frontend/data/p3PostDataActive.json","sha256":fsha},
          {"path":"new-platform/frontend/data/tools-pool-snapshot.json","sha256":psha}
        ],
        "counts":{"focusTrials":2,"fullySourceReviewed":0},
        "records":[
          {"nctId":a,"drug":"Drug A","indication":"Disease A","phase":"PHASE3","membership":{"focus":True}},
          {"nctId":b,"drug":"Drug B","indication":"Disease B","phase":"PHASE3","membership":{"focus":True}}
        ]
    }
    (reg/"inventory.json").write_text(json.dumps(inventory))
    lead={"pmid":"12345","url":"https://pubmed.ncbi.nlm.nih.gov/12345/",
          "status":"UNREVIEWED_LEAD","clinicalFinding":None,
          "exactTrialLinkVerified":False}
    pool_pub={
      "schemaVersion":q.pubmed.VERSION,
      "rosterSha256":psha,
      "nctOrder":[a],"rows":[{"nct":a,"status":"QUERY_SUCCEEDED_UNREVIEWED",
        "reportedTotalHits":1,"publicationLeads":[lead]}],
      "status":"UNREVIEWED_SEARCHES_COMPLETE",
      "sourceReviewsCompleted":0,"fdaPredictionsComputed":0,
      "queriesSucceeded":1
    }
    ppub=tmp_path/"pool-pubmed.json"
    ppub.write_text(json.dumps(pool_pub))
    outonly=q.focus_pubmed.report(json.loads(focus.read_text()),fsha,psha,[a,b],[b],
      [{"nct":b,"status":"QUERY_SUCCEEDED_UNREVIEWED",
        "reportedTotalHits":0,"publicationLeads":[]}])
    o=tmp_path/"focus-only.json"
    o.write_text(json.dumps(outonly))
    coverage={
        "status":"SOURCE_CAPTURE_PRESENT_NOT_SCIENTIFICALLY_REVIEWED",
        "rosterSha256":psha,"poolTrials":1,
        "rawRegistryPacketsVerifiedLocally":1,"pubmedQueriesSucceeded":1,
        "pubmedQueriesFailed":0,"scientificReviewsCompleted":0,
        "fdaPredictionsComputed":0
    }
    cov=tmp_path/"coverage.json"
    cov.write_text(json.dumps(coverage))
    return [focus,pool,reg,ppub,o,cov]


def test_focus_review_queue_never_claims_clinical_success(tmp_path):
    paths=setup(tmp_path)
    out=q.build(*paths)
    assert out["counts"]["focusTrials"]==2
    assert out["counts"]["withPostedPrimaryResults"]==1
    assert out["counts"]["withoutPostedPrimaryResults"]==1
    assert out["counts"]["unreviewedPublicationLeads"]==1
    assert out["trials"][0]["candidatePubmedPmidsUnreviewed"]==["12345"]
    assert out["trials"][1]["candidatePubmedPmidsUnreviewed"]==[]
    assert out["counts"]["scientificReviewsCompleted"]==0
    assert out["counts"]["fdaPredictionsComputed"]==0
    assert all(x["scientificScores"] is None and
               x["fdaApprovalProbability"] is None and
               x["fdaPrediction"]=="ABSTAIN" and
               x["productionWritesAllowed"] is False
               for x in out["trials"])
    q.write_outputs(out,tmp_path/"readiness.json",tmp_path/"readiness.md")
    assert (tmp_path/"readiness.json").exists()


def test_wrong_registry_packet_digest_fails_closed(tmp_path):
    paths=setup(tmp_path)
    reg=paths[2]
    x=json.loads((reg/"ingestion-state.json").read_text())
    x["sources"]["NCT00000002"]["versions"][0]["fingerprint"]="0"*64
    (reg/"ingestion-state.json").write_text(json.dumps(x))
    with pytest.raises(ValueError,match="SHA-256 mismatch"):
        q.build(*paths)


def test_wrong_focus_source_hash_fails_closed(tmp_path):
    paths=setup(tmp_path)
    focus=paths[0]
    focus.write_text(focus.read_text()+"\n")
    with pytest.raises(ValueError):
        q.build(*paths)


def test_incomplete_pubmed_or_false_reviews_fail_closed(tmp_path):
    paths=setup(tmp_path)
    cov=paths[-1]
    a=json.loads(cov.read_text())
    a["pubmedQueriesSucceeded"]=0
    cov.write_text(json.dumps(a))
    with pytest.raises(ValueError,match="Whole-POOL"):
        q.build(*paths)
    a["pubmedQueriesSucceeded"]=1
    a["scientificReviewsCompleted"]=1
    cov.write_text(json.dumps(a))
    with pytest.raises(ValueError,match="Whole-POOL"):
        q.build(*paths)

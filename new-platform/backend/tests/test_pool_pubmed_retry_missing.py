"""Offline synthetic trials for immutable exact-NCT PubMed shard retries."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "pool_pubmed_shard_recovery_test", ROOT / "scripts/medical/pool_pubmed_retry_missing.py")
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)
shards = tool.shards


def nct(i):
    return "NCT" + str(i).zfill(8)


def fixtures(tmp_path):
    roster = tmp_path / "source-pool.json"
    roster.write_text(json.dumps({"asOf": "2026-11-17", "pipeline": [
        {"id": "TRIAL|" + nct(i)} for i in range(1, 9)
    ] + [{"id": "RESULT|NOT_STUDY"}]}))
    source = tmp_path / "original-shards"
    source.mkdir()
    for index in range(3):
        def search(n):
            if n == nct(4):
                raise TimeoutError("simulated source timeout")
            return hit(n)
        shards.collect(roster, source / ("shard-%02d.json" % index),
                       index=index, count=3, searcher=search,
                       pause=lambda _: None)
    return roster, source


def hit(n):
    return {"nct": n, "status": "QUERY_SUCCEEDED_UNREVIEWED",
            "reportedTotalHits": 1, "publicationLeads": [{
                "pmid": "12345",
                "url": "https://pubmed.ncbi.nlm.nih.gov/12345/",
                "status": "UNREVIEWED_LEAD",
                "exactTrialLinkVerified": False,
                "clinicalFinding": None,
            }]}


def test_only_failed_exact_nct_retried_and_original_receipts_untouched(tmp_path):
    roster, source = fixtures(tmp_path)
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in source.iterdir()}
    plan = tool.recovery_plan(roster, source, count=3)
    assert plan["poolTrials"] == 8
    assert plan["unresolvedNctCount"] == 1
    calls = []
    res = tool.retry(roster, source, tmp_path / "retry",
                     tmp_path / "merged.json", count=3,
                     searcher=lambda n: (calls.append(n), hit(n))[1],
                     pause=lambda _: None)
    assert calls == [nct(4)]
    assert res["queriesRecovered"] == 1
    assert res["queriesStillUnresolved"] == 0
    assert res["status"] == "UNREVIEWED_SEARCHES_COMPLETE"
    assert res["finalUnreviewedPublicationLeads"] == 8
    assert res["scientificReviewsCompleted"] == res["fdaPredictionsComputed"] == 0
    assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in source.iterdir()}
    merged = json.loads((tmp_path / "merged.json").read_text())
    assert merged["nctOrder"] == [nct(i) for i in range(1, 9)]


def test_persistent_source_failure_never_claims_completed_research(tmp_path):
    roster, source = fixtures(tmp_path)
    res = tool.retry(roster, source, tmp_path / "retry",
                     tmp_path / "merged.json", count=3,
                     searcher=lambda _: (_ for _ in ()).throw(TimeoutError()),
                     pause=lambda _: None)
    assert res["status"] == "PARTIAL_RETRY_OR_UNQUERIED"
    assert res["queriesStillUnresolved"] == 1
    assert res["scientificReviewsCompleted"] == 0
    assert json.loads((tmp_path / "merged.json").read_text())["queriesFailed"] == 1


def test_changed_roster_and_missing_shard_fail_before_any_network(tmp_path):
    roster, source = fixtures(tmp_path)
    (source / "shard-02.json").unlink()
    calls = []
    with pytest.raises(FileNotFoundError):
        tool.retry(roster, source, tmp_path / "retry",
                   tmp_path / "merged.json", count=3,
                   searcher=lambda n: calls.append(n))
    assert calls == []
    assert not (tmp_path / "retry").exists()
    roster, source = fixtures(tmp_path / "new-input")
    roster.write_text(roster.read_text().replace(nct(7), nct(9)))
    with pytest.raises(ValueError, match="Checkpoint does not match"):
        tool.recovery_plan(roster, source, count=3)


def test_tampered_source_shard_and_duplicate_destination_rejected(tmp_path):
    roster, source = fixtures(tmp_path)
    bad = source / "shard-01.json"
    data = json.loads(bad.read_text())
    data["rows"][0]["nct"] = nct(7)
    bad.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Checkpoint"):
        tool.recovery_plan(roster, source, count=3)
    assert not (tmp_path / "retry").exists()


def test_retry_limit_must_not_induce_unbounded_source_traffic(tmp_path):
    roster, source = fixtures(tmp_path)
    with pytest.raises(ValueError, match="recovery bound"):
        tool.retry(roster, source, tmp_path / "retry",
                   tmp_path / "merged.json", count=3, max_queries=0,
                   searcher=hit)

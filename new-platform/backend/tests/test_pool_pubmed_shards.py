"""Synthetic bounded shards; no public network and no scientific success claims."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "pool_pubmed_shards_test", ROOT / "scripts/medical/pool_pubmed_shards.py")
shards = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shards)


def trial(i):
    return "NCT" + str(i).zfill(8)


def snapshot(tmp_path, count=11):
    roster = tmp_path / "pool.json"
    roster.write_text(json.dumps({
        "asOf": "2026-11-17",
        "pipeline": [{"id": "TRIAL|" + trial(i)} for i in range(1, count+1)]
                    + [{"id": "RESULT|IGNORED"}, {"id": "APPLICATION|IGNORED"}],
    }))
    return roster


def hit(nct):
    return {"nct": nct, "status": "QUERY_SUCCEEDED_UNREVIEWED",
            "reportedTotalHits": 1,
            "publicationLeads": [{"pmid": "123456", "url": "https://pubmed.ncbi.nlm.nih.gov/123456/",
                                  "status": "UNREVIEWED_LEAD", "clinicalFinding": None,
                                  "exactTrialLinkVerified": False}]}


def test_all_shards_merge_exact_pool_order_and_safety_labels(tmp_path):
    roster = snapshot(tmp_path)
    folder = tmp_path / "shards"
    folder.mkdir()
    queried = []
    for idx in range(3):
        result = shards.collect(roster, folder / ("shard-%02d.json" % idx), index=idx,
                                count=3, pause=lambda _: None,
                                searcher=lambda nct: (queried.append(nct), hit(nct))[1])
        assert result["status"] == "SHARD_QUERIES_COMPLETE_UNREVIEWED"
        assert result["sourceReviewsCompleted"] == 0
        assert result["fullPoolTrialCount"] == 11
    assert sorted(queried) == sorted([trial(i) for i in range(1, 12)])
    output = tmp_path / "merged.json"
    final = shards.merge(roster, folder, output, count=3)
    assert final["status"] == "UNREVIEWED_SEARCHES_COMPLETE"
    assert final["totalPoolTrials"] == 11
    assert final["nctOrder"] == [trial(i) for i in range(1, 12)]
    assert final["publicationLeadsUnreviewed"] == 11
    assert final["sourceReviewsCompleted"] == 0
    assert final["scientificAssessmentsCompleted"] == 0
    assert final["fdaPredictionsComputed"] == 0
    assert json.loads(output.read_text())["shardCount"] == 3


def test_partial_shard_and_global_merge_never_claim_source_completion(tmp_path):
    roster = snapshot(tmp_path, count=5)
    folder = tmp_path / "parts"
    folder.mkdir()
    for idx in range(2):
        def failure(nct):
            if nct == trial(2):
                raise TimeoutError("source unavailable")
            return hit(nct)
        shards.collect(roster, folder / ("shard-%02d.json" % idx),
                       index=idx, count=2, pause=lambda _: None, searcher=failure)
    result = shards.merge(roster, folder, tmp_path / "merged.json", count=2)
    assert result["status"] == "PARTIAL_RETRY_OR_UNQUERIED"
    assert result["queriesFailed"] == 1
    assert result["sourceReviewsCompleted"] == 0
    assert result["fdaPredictionsComputed"] == 0


def test_resume_only_failed_original_nct_when_roster_unchanged(tmp_path):
    roster = snapshot(tmp_path, count=7)
    output = tmp_path / "shard.json"
    shards.collect(roster, output, index=0, count=2, searcher=lambda nct: (
        hit(nct) if nct != trial(3) else (_ for _ in ()).throw(TimeoutError())),
        pause=lambda _: None)
    calls = []
    result = shards.collect(roster, output, index=0, count=2, resume=True,
                            searcher=lambda nct: (calls.append(nct), hit(nct))[1],
                            pause=lambda _: None)
    assert calls == [trial(3)]
    assert result["queriesSucceeded"] == 4
    assert result["queriesFailed"] == 0


def test_wrong_shard_or_source_digest_refused(tmp_path):
    roster = snapshot(tmp_path, count=5)
    folder = tmp_path / "parts"
    folder.mkdir()
    for idx in range(2):
        shards.collect(roster, folder / ("shard-%02d.json" % idx), index=idx,
                       count=2, searcher=hit, pause=lambda _: None)
    path = folder / "shard-01.json"
    bad = json.loads(path.read_text())
    bad["shardIndex"] = 0
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="Shard metadata"):
        shards.merge(roster, folder, tmp_path / "merged.json", count=2)
    with pytest.raises(ValueError, match="Shard metadata"):
        shards.collect(roster, path, index=1, count=2, resume=True,
                       searcher=hit, pause=lambda _: None)


def test_newer_roster_cannot_be_merged_with_old_shards(tmp_path):
    roster = snapshot(tmp_path, count=5)
    folder = tmp_path / "parts"
    folder.mkdir()
    for idx in range(2):
        shards.collect(roster, folder / ("shard-%02d.json" % idx),
                       index=idx, count=2, searcher=hit, pause=lambda _: None)
    roster.write_text(roster.read_text().replace(trial(5), trial(6)))
    with pytest.raises(ValueError, match="Checkpoint does not match"):
        shards.merge(roster, folder, tmp_path / "merged.json", count=2)


def test_consecutive_network_failures_stop_shard_not_truthfully_complete(tmp_path):
    roster = snapshot(tmp_path, count=9)
    result = shards.collect(roster, tmp_path / "partial.json",
                            index=0, count=1, stop_after_failures=2,
                            searcher=lambda _: (_ for _ in ()).throw(TimeoutError()),
                            pause=lambda _: None)
    assert result["queriesFailed"] == 2
    assert result["queriesUnattempted"] == 7
    assert result["status"] == "SHARD_PARTIAL_RETRY_OR_UNQUERIED"


def test_unsafe_shard_count_rejected(tmp_path):
    roster = snapshot(tmp_path)
    with pytest.raises(ValueError):
        shards.collect(roster, tmp_path / "x.json", index=0, count=129,
                       searcher=hit)

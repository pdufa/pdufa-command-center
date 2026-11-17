"""Offline source-boundary regressions for whole-POOL PubMed harvesting."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
path = ROOT / "scripts/medical/pool_pubmed_discovery.py"
spec = importlib.util.spec_from_file_location("pool_pubmed_discovery", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
N1, N2 = "NCT00000001", "NCT00000002"


def roster(path, ids=(N1, N2)):
    value = {"asOf": "2026-11-16", "pipeline": [
        {"id": "TRIAL|" + nct} for nct in ids
    ] + [{"id": "RESULT|UNKNOWN"}, {"id": "APPLICATION|NDA-123456"}]}
    path.write_text(json.dumps(value))
    return value


def lead(nct, pmid="12345"):
    return {"nct": nct, "status": "QUERY_SUCCEEDED_UNREVIEWED",
            "reportedTotalHits": 1, "publicationLeads": [{
                "pmid": pmid, "url": "https://pubmed.ncbi.nlm.nih.gov/" + pmid + "/",
                "status": "UNREVIEWED_LEAD", "clinicalFinding": None,
                "exactTrialLinkVerified": False,
            }]}


def test_exact_pool_only_excludes_aliases():
    ncts, skipped = mod.extract_pool(roster_value())
    assert ncts == [N1, N2] and skipped == 2
    with pytest.raises(ValueError):
        mod.extract_pool({"pipeline": [{"id": "TRIAL|" + N1},
                                        {"id": "TRIAL|" + N1}]})
    with pytest.raises(ValueError):
        mod.extract_pool({"pipeline": [{"id": "TRIAL|NOT_NCT"}]})


def roster_value():
    return {"pipeline": [{"id": "TRIAL|" + N1}, {"id": "TRIAL|" + N2},
                         {"id": "RESULT|UNLINKED"}, {"id": "APPLICATION|NDA"}]}


def test_full_pool_and_unreviewed_coverage(tmp_path):
    a, b = tmp_path / "pool.json", tmp_path / "out.json"
    roster(a)
    calls, pauses = [], []
    def search(nct):
        calls.append(nct)
        return lead(nct)
    x = mod.run(a, b, searcher=search, pause=pauses.append)
    assert calls == [N1, N2] and pauses == [0.36]
    assert x["status"] == "UNREVIEWED_SEARCHES_COMPLETE"
    assert x["totalPoolTrials"] == 2 and x["nonTrialRowsExcluded"] == 2
    assert x["queriesSucceeded"] == 2
    assert x["sourceReviewsCompleted"] == 0
    assert x["scientificAssessmentsCompleted"] == 0
    assert x["fdaPredictionsComputed"] == 0
    assert json.loads(b.read_text())["rosterSha256"] == x["rosterSha256"]


def test_retry_resume_only_failed_trial(tmp_path):
    a, b = tmp_path / "pool.json", tmp_path / "out.json"
    roster(a)
    def fail(nct):
        if nct == N2:
            raise TimeoutError("simulated")
        return lead(nct)
    partial = mod.run(a, b, searcher=fail, pause=lambda _: None)
    assert partial["queriesSucceeded"] == partial["queriesFailed"] == 1
    calls = []
    def success(nct):
        calls.append(nct)
        return lead(nct, "67890")
    final = mod.run(a, b, resume=True, searcher=success, pause=lambda _: None)
    assert calls == [N2]
    assert final["queriesSucceeded"] == 2
    assert final["rows"][0]["publicationLeads"][0]["pmid"] == "12345"


def test_partial_limit_and_wrong_trial_fail_closed(tmp_path):
    a, b = tmp_path / "pool.json", tmp_path / "out.json"
    roster(a)
    value = mod.run(a, b, limit=1, searcher=lambda nct: lead(nct),
                    pause=lambda _: None)
    assert value["status"] == "PARTIAL_RETRY_OR_UNQUERIED"
    assert value["queriesUnattempted"] == 1
    b.unlink()
    value = mod.run(a, b, searcher=lambda nct: lead(N2 if nct == N1 else N1),
                    pause=lambda _: None)
    assert value["queriesFailed"] == 2


def test_changed_roster_and_tampered_pmids_refuse_resume(tmp_path):
    a, b = tmp_path / "pool.json", tmp_path / "out.json"
    roster(a)
    mod.run(a, b, searcher=lambda nct: lead(nct), pause=lambda _: None)
    raw = json.loads(b.read_text())
    raw["rows"][0]["publicationLeads"][0]["url"] = "https://evil.example/"
    b.write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        mod.run(a, b, resume=True, searcher=lambda nct: lead(nct))
    b.unlink()
    mod.run(a, b, searcher=lambda nct: lead(nct), pause=lambda _: None)
    roster(a, (N1, "NCT00000003"))
    with pytest.raises(ValueError):
        mod.run(a, b, resume=True, searcher=lambda nct: lead(nct))


def test_invalid_pubmed_responses_fail():
    class Response:
        def __init__(self, payload):
            self.payload = payload
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def read(self, _):
            return json.dumps(self.payload).encode()
    for payload in (
        {"esearchresult": {"idlist": ["12", "12"], "count": "2"}},
        {"esearchresult": {"idlist": ["12", "x"], "count": "2"}},
        {"esearchresult": {"idlist": ["12", "24"], "count": "1"}},
        {"esearchresult": {"idlist": ["12"], "count": "-1"}},
    ):
        with pytest.raises(ValueError):
            mod.search_pubmed(N1, opener=lambda *_a, **_kw: Response(payload))

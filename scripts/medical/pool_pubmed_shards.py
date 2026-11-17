#!/usr/bin/env python3
"""Bounded, exact-NCT PubMed POOL shards and strict artifact merge.

Never authenticates publications, clinical findings, predictions or FDA actions.
Original single-job collector remains available for small subsets and testing.
Shards protect GitHub job timeouts and retain individual query failures.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time
from urllib.request import urlopen

ORIGINAL = Path(__file__).with_name("pool_pubmed_discovery.py")
SPEC = importlib.util.spec_from_file_location("pool_pubmed_exact_source", ORIGINAL)
pubmed = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pubmed)

SHARD_SCOPE = "EXACT_POOL_NCT_SHARD_ONLY_NOT_REVIEWED"
DEFAULT_COUNT = 32


def _source(roster):
    raw = Path(roster).read_bytes()
    snapshot = json.loads(raw)
    ncts, excluded = pubmed.extract_pool(snapshot)
    return snapshot, hashlib.sha256(raw).hexdigest(), ncts, excluded


def _validate_index(index, count):
    if (type(index) is not int or type(count) is not int
            or not 1 <= count <= 128 or not 0 <= index < count):
        raise ValueError("Invalid stable shard index/count")


def _shard_report(snapshot, digest, ncts, excluded, rows, *, index, count, original_total):
    result = pubmed.report(snapshot, digest, ncts, excluded, rows)
    result.update({
        "scope": SHARD_SCOPE,
        "status": ("SHARD_QUERIES_COMPLETE_UNREVIEWED"
                   if result["queriesSucceeded"] == len(ncts)
                   else "SHARD_PARTIAL_RETRY_OR_UNQUERIED"),
        "shardIndex": index,
        "shardCount": count,
        "fullPoolTrialCount": original_total,
        "scientificAssessmentsCompleted": 0,
        "sourceReviewsCompleted": 0,
        "fdaPredictionsComputed": 0,
    })
    return result


def _check_shard(value, digest, expected, index, count, full_count):
    if (not isinstance(value, dict) or value.get("scope") != SHARD_SCOPE
            or value.get("shardIndex") != index
            or value.get("shardCount") != count
            or value.get("fullPoolTrialCount") != full_count
            or value.get("totalPoolTrials") != len(expected)
            or value.get("sourceReviewsCompleted") != 0
            or value.get("scientificAssessmentsCompleted") != 0
            or value.get("fdaPredictionsComputed") != 0
            or value.get("clinicalFindingsVerified") is not False):
        raise ValueError("Shard metadata, identities, or safety flags changed")
    pubmed.validate_checkpoint(value, digest, expected)
    successes = sum(row["status"] == "QUERY_SUCCEEDED_UNREVIEWED" for row in value["rows"])
    failed = sum(row["status"] == "RETRY_REQUIRED" for row in value["rows"])
    if (value.get("queriesSucceeded") != successes or
            value.get("queriesFailed") != failed or
            value.get("queriesUnattempted") != len(expected) - successes - failed or
            value.get("publicationLeadsUnreviewed") != sum(
                len(row["publicationLeads"]) for row in value["rows"])
            or value.get("status") != (
                "SHARD_QUERIES_COMPLETE_UNREVIEWED" if successes == len(expected)
                else "SHARD_PARTIAL_RETRY_OR_UNQUERIED")):
        raise ValueError("Shard counts or completion status contradicted row states")


def collect(roster, output, *, index, count=DEFAULT_COUNT, resume=False,
            searcher=None, pause=time.sleep, pace_seconds=0.8,
            stop_after_failures=6):
    _validate_index(index, count)
    if not isinstance(pace_seconds, (float, int)) or not 0.8 <= pace_seconds <= 10:
        raise ValueError("Shard calls must be paced for at most two concurrent workers")
    if type(stop_after_failures) is not int or not 1 <= stop_after_failures <= 100:
        raise ValueError("Invalid consecutive source failure threshold")
    if Path(roster).resolve() == Path(output).resolve():
        raise ValueError("Cannot overwrite source POOL roster")
    snapshot, digest, all_ncts, excluded = _source(roster)
    selected = all_ncts[index::count]
    path = Path(output)
    if path.exists() and not resume:
        raise ValueError("Prior shard exists; request explicit resume to retain evidence")
    if resume and path.exists():
        prior = json.loads(path.read_text(encoding="utf-8"))
        _check_shard(prior, digest, selected, index, count, len(all_ncts))
        rows = prior["rows"]
    else:
        rows = [{"nct": nct, "status": "NOT_QUERIED", "publicationLeads": []}
                for nct in selected]
    if searcher is None:
        # Keep individual stalled NCBI requests bounded; partial is not success.
        searcher = lambda nct: pubmed.search_pubmed(
            nct, opener=lambda request, timeout: urlopen(request, timeout=8))
    consecutive_failures, attempts = 0, 0
    for i, entry in enumerate(rows):
        if entry["status"] == "QUERY_SUCCEEDED_UNREVIEWED":
            continue
        if consecutive_failures >= stop_after_failures:
            break
        if attempts:
            pause(pace_seconds)
        attempts += 1
        try:
            candidate = searcher(selected[i])
            if (not isinstance(candidate, dict) or candidate.get("nct") != selected[i]
                    or candidate.get("status") != "QUERY_SUCCEEDED_UNREVIEWED"):
                raise ValueError("Wrong exact NCT or unverifiable candidate response")
            trial_rows = list(rows)
            trial_rows[i] = candidate
            check = _shard_report(snapshot, digest, selected, excluded,
                                  trial_rows, index=index, count=count,
                                  original_total=len(all_ncts))
            _check_shard(check, digest, selected, index, count, len(all_ncts))
            rows[i] = candidate
            consecutive_failures = 0
        except (OSError, TimeoutError, ValueError, json.JSONDecodeError) as e:
            rows[i] = {"nct": selected[i], "status": "RETRY_REQUIRED",
                       "errorType": type(e).__name__, "publicationLeads": []}
            consecutive_failures += 1
        value = _shard_report(snapshot, digest, selected, excluded,
                              rows, index=index, count=count, original_total=len(all_ncts))
        pubmed.save(path, value)
    result = _shard_report(snapshot, digest, selected, excluded, rows,
                           index=index, count=count, original_total=len(all_ncts))
    _check_shard(result, digest, selected, index, count, len(all_ncts))
    pubmed.save(path, result)
    return result


def merge(roster, shard_dir, output, *, count=DEFAULT_COUNT):
    _validate_index(0, count)
    snapshot, digest, full, excluded = _source(roster)
    dest = Path(output)
    if dest.resolve() == Path(roster).resolve():
        raise ValueError("Cannot overwrite original POOL roster")
    if dest.exists():
        raise ValueError("Merged source artifact exists; keep versioned results")
    root = Path(shard_dir)
    rows = {}
    for index in range(count):
        path = root / ("shard-%02d.json" % index)
        data = json.loads(path.read_text(encoding="utf-8"))
        expected = full[index::count]
        _check_shard(data, digest, expected, index, count, len(full))
        for row in data["rows"]:
            nct = row["nct"]
            if nct in rows:
                raise ValueError("Duplicated trial across PubMed source shards")
            rows[nct] = row
    if set(rows) != set(full) or len(rows) != len(full):
        raise ValueError("Missing exact-POOL trial in sharded source merge")
    result = pubmed.report(snapshot, digest, full, excluded, [rows[nct] for nct in full])
    result["collectionMethod"] = "VALIDATED_NCT_SHARDS_UNREVIEWED"
    result["shardCount"] = count
    pubmed.validate_checkpoint(result, digest, full)
    pubmed.save(dest, result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roster", type=Path, default=Path(
        "new-platform/frontend/data/tools-pool-snapshot.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--shard-count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--shard-index", type=int)
    parser.add_argument("--shard-dir", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    if (args.shard_index is None) == (args.shard_dir is None):
        parser.error("Supply exactly one of --shard-index or --shard-dir")
    if args.shard_dir is None:
        x = collect(args.roster, args.output, index=args.shard_index,
                    count=args.shard_count, resume=args.resume)
        result_ok = x["status"] == "SHARD_QUERIES_COMPLETE_UNREVIEWED"
        details = {k: x[k] for k in ("shardIndex", "shardCount", "fullPoolTrialCount",
                                   "queriesSucceeded", "queriesFailed", "queriesUnattempted")}
    else:
        x = merge(args.roster, args.shard_dir, args.output, count=args.shard_count)
        result_ok = x["status"] == "UNREVIEWED_SEARCHES_COMPLETE"
        details = {k: x[k] for k in ("totalPoolTrials", "queriesSucceeded",
                                   "queriesFailed", "queriesUnattempted",
                                   "publicationLeadsUnreviewed")}
    print(json.dumps({"status": x["status"], **details}))
    return 0 if result_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

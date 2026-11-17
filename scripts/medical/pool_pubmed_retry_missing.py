#!/usr/bin/env python3
"""Retry only unresolved exact-NCT PubMed queries from saved sharded research.

Input shard receipts are immutable. Output is a separate retry archive with
a whole-POOL exact-NCT reconciliation. A completed query is still UNREVIEWED,
not a clinical result, scientific score or FDA prediction.

A caller must first retrieve ALL original shard artifacts from the SAME
completed GitHub collection run. Missing or different-roster shards fail closed.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import time

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "pool_pubmed_shards_recovery_dependency", HERE / "pool_pubmed_shards.py")
shards = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(shards)


def recovery_plan(roster, source_dir, *, count=32):
    """Verify entire immutable shard set BEFORE any network or output mutation."""
    shards._validate_index(0, count)
    _snapshot, digest, all_ncts, _excluded = shards._source(roster)
    rows = []
    source_dir = Path(source_dir)
    missing = 0
    for index in range(count):
        original = source_dir / ("shard-%02d.json" % index)
        data = json.loads(original.read_text(encoding="utf-8"))
        expected = all_ncts[index::count]
        shards._check_shard(data, digest, expected, index, count, len(all_ncts))
        remaining = [row["nct"] for row in data["rows"]
                     if row["status"] != "QUERY_SUCCEEDED_UNREVIEWED"]
        missing += len(remaining)
        rows.append({
            "index": index, "path": original, "remaining": remaining,
            "queryCount": len(expected),
        })
    if sum(x["queryCount"] for x in rows) != len(all_ncts):
        raise ValueError("Not every exact-NCT source trial is present")
    return {
        "rosterSha256": digest,
        "poolTrials": len(all_ncts),
        "shards": rows,
        "unresolvedNctCount": missing,
    }


def retry(roster, source_dir, output_dir, merged_file, *, count=32,
          max_queries=512, searcher=None, pause=time.sleep):
    if type(max_queries) is not int or not 1 <= max_queries <= 1000:
        raise ValueError("Retry bound must be between 1 and 1000")
    plan = recovery_plan(roster, source_dir, count=count)
    if plan["unresolvedNctCount"] > max_queries:
        raise ValueError("Missing source queries exceed permitted recovery bound")
    source_dir = Path(source_dir).resolve()
    output_dir = Path(output_dir).resolve()
    merged_file = Path(merged_file).resolve()
    if (source_dir == output_dir or source_dir in output_dir.parents
            or output_dir in source_dir.parents
            or merged_file == Path(roster).resolve()
            or merged_file == Path(source_dir).resolve()
            or merged_file in source_dir.parents
            or merged_file == output_dir
            or merged_file in output_dir.parents):
        raise ValueError("Recovery outputs must be separate from original source artifacts")
    if output_dir.exists() or merged_file.exists():
        raise ValueError("Recovery outputs already exist; retain previous version")
    output_dir.mkdir(parents=True, exist_ok=False)
    total_recovered = 0
    total_unresolved = 0
    retries = 0
    for item in plan["shards"]:
        dest = output_dir / item["path"].name
        shutil.copy2(item["path"], dest)
        if item["remaining"]:
            if retries:
                pause(2.0)  # One worker; avoid another burst between shards.
            retries += len(item["remaining"])
            result = shards.collect(
                roster, dest, index=item["index"], count=count, resume=True,
                searcher=searcher, pause=pause, pace_seconds=2.0)
        else:
            result = json.loads(dest.read_text(encoding="utf-8"))
        shards._check_shard(
            result, plan["rosterSha256"],
            shards._source(roster)[2][item["index"]::count],
            item["index"], count, plan["poolTrials"])
        outstanding = result["queriesFailed"] + result["queriesUnattempted"]
        total_unresolved += outstanding
        total_recovered += len(item["remaining"]) - outstanding
    merged = shards.merge(roster, output_dir, merged_file, count=count)
    if merged["queriesFailed"] + merged["queriesUnattempted"] != total_unresolved:
        raise ValueError("Retry manifest is inconsistent with merged research")
    if merged["sourceReviewsCompleted"] != 0 or merged["fdaPredictionsComputed"] != 0:
        raise ValueError("Unreviewed source leads were incorrectly promoted")
    return {
        "status": merged["status"],
        "rosterSha256": plan["rosterSha256"],
        "fullPoolTrials": plan["poolTrials"],
        "previouslyUnresolved": plan["unresolvedNctCount"],
        "queriesRecovered": total_recovered,
        "queriesStillUnresolved": total_unresolved,
        "queriedNcts": retries,
        "finalUnreviewedPublicationLeads": merged["publicationLeadsUnreviewed"],
        "scientificReviewsCompleted": 0,
        "fdaPredictionsComputed": 0,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--roster", type=Path, default=Path(
        "new-platform/frontend/data/tools-pool-snapshot.json"))
    p.add_argument("--source-shards", type=Path, required=True)
    p.add_argument("--retry-shards", type=Path, required=True)
    p.add_argument("--merged-output", type=Path, required=True)
    p.add_argument("--shard-count", type=int, default=32)
    p.add_argument("--max-queries", type=int, default=512)
    args = p.parse_args(argv)
    result = retry(args.roster, args.source_shards, args.retry_shards,
                   args.merged_output, count=args.shard_count,
                   max_queries=args.max_queries)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "UNREVIEWED_SEARCHES_COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())

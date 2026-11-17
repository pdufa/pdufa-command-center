#!/usr/bin/env python3
"""Discover unreviewed PubMed leads for FOCUS NCTs excluded from the POOL.

Preserves the source-defined FOCUS roster. Never imports source leads into a
scientific score, FDA prediction, clinical trial outcome or production table.
The separate all-POOL sharded collector handles the other FOCUS NCTs.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import time

SCRIPT = Path(__file__).with_name("pool_pubmed_discovery.py")
SPEC = importlib.util.spec_from_file_location("pool_exact_nct_pubmed", SCRIPT)
pubmed = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pubmed)

NCT = re.compile(r"NCT[0-9]{8}")
VERSION = "focus-outside-pool-pubmed-unreviewed-v1"
SCOPE = "EXACT_FOCUS_NCTS_EXCLUDED_FROM_POOL_UNREVIEWED"


def _source(path):
    raw = Path(path).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def exact_focus_outside_pool(focus, pool):
    if not isinstance(focus, dict) or not isinstance(focus.get("records"), list):
        raise ValueError("FOCUS must be a snapshot with a records array")
    if not isinstance(pool, dict):
        raise ValueError("POOL snapshot must be a JSON object")
    all_focus = []
    for row in focus["records"]:
        nct = row.get("nct") if isinstance(row, dict) else None
        if not isinstance(nct, str) or not NCT.fullmatch(nct):
            raise ValueError("Malformed exact FOCUS NCT")
        all_focus.append(nct)
    if not all_focus or len(all_focus) > 500 or len(all_focus) != len(set(all_focus)):
        raise ValueError("FOCUS roster empty, unbounded, or has duplicate NCTs")
    pool_ncts, _ = pubmed.extract_pool(pool)
    pool_ids = set(pool_ncts)
    excluded = [nct for nct in all_focus if nct not in pool_ids]
    return all_focus, excluded


def report(focus, f_sha, p_sha, full_focus, excluded, rows):
    succeeded = sum(x["status"] == "QUERY_SUCCEEDED_UNREVIEWED" for x in rows)
    failed = sum(x["status"] == "RETRY_REQUIRED" for x in rows)
    return {
        "schemaVersion": VERSION,
        "scope": SCOPE,
        "focusSnapshotSha256": f_sha,
        "poolSnapshotSha256": p_sha,
        "focusRosterAsOf": focus.get("asOf"),
        "fullFocusNctOrder": full_focus,
        "fullFocusCount": len(full_focus),
        "focusOnlyNctOrder": excluded,
        "focusOnlyCount": len(excluded),
        "queriesSucceeded": succeeded,
        "queriesFailed": failed,
        "queriesUnattempted": len(excluded) - succeeded - failed,
        "publicationLeadsUnreviewed": sum(len(x["publicationLeads"]) for x in rows),
        "status": ("FOCUS_ONLY_PUBLICATION_LEADS_QUERIED_NOT_REVIEWED"
                   if succeeded == len(excluded) else
                   "PARTIAL_FOCUS_ONLY_PUBMED_DISCOVERY"),
        "scientificReviewsCompleted": 0,
        "fdaPredictionsComputed": 0,
        "verifiedClinicalFindings": False,
        "limitations": [
            "These FOCUS NCTs are absent from the current POOL study roster; FOCUS membership is never changed.",
            "Unreviewed PubMed search matches are not confirmed publications about this trial.",
            "No publication match does not prove absence of clinical data.",
            "These source leads are separate from the 32-trial scientific assessment engine.",
        ],
        "rows": rows,
    }


def validate(value, focus_sha, pool_sha, full_focus, excluded):
    if (not isinstance(value, dict) or value.get("schemaVersion") != VERSION
            or value.get("scope") != SCOPE
            or value.get("focusSnapshotSha256") != focus_sha
            or value.get("poolSnapshotSha256") != pool_sha
            or value.get("fullFocusNctOrder") != full_focus
            or value.get("fullFocusCount") != len(full_focus)
            or value.get("focusOnlyNctOrder") != excluded
            or value.get("focusOnlyCount") != len(excluded)
            or value.get("scientificReviewsCompleted") != 0
            or value.get("fdaPredictionsComputed") != 0
            or value.get("verifiedClinicalFindings") is not False):
        raise ValueError("FOCUS-only discovery scope, roster or source status mismatch")
    checkpoint = {
        "schemaVersion": pubmed.VERSION,
        "rosterSha256": focus_sha,
        "nctOrder": excluded,
        "rows": value.get("rows"),
    }
    pubmed.validate_checkpoint(checkpoint, focus_sha, excluded)
    rows = value["rows"]
    succeeded = sum(x["status"] == "QUERY_SUCCEEDED_UNREVIEWED" for x in rows)
    failed = sum(x["status"] == "RETRY_REQUIRED" for x in rows)
    if (value.get("queriesSucceeded") != succeeded
            or value.get("queriesFailed") != failed
            or value.get("queriesUnattempted") != len(rows) - succeeded - failed
            or value.get("publicationLeadsUnreviewed") != sum(
                len(x["publicationLeads"]) for x in rows)
            or value.get("status") != (
                "FOCUS_ONLY_PUBLICATION_LEADS_QUERIED_NOT_REVIEWED"
                if succeeded == len(rows) else "PARTIAL_FOCUS_ONLY_PUBMED_DISCOVERY")):
        raise ValueError("FOCUS-only published-lead coverage counts mismatch")


def collect(focus_path, pool_path, output, *, resume=False, searcher=None,
            pause=time.sleep):
    focus, f_sha = _source(focus_path)
    pool, p_sha = _source(pool_path)
    full_focus, excluded = exact_focus_outside_pool(focus, pool)
    output = Path(output)
    if output.resolve() in {Path(focus_path).resolve(), Path(pool_path).resolve()}:
        raise ValueError("Research artifact must not replace FOCUS or POOL roster")
    if output.exists():
        if not resume:
            raise ValueError("Source research artifact exists; resume required")
        saved = json.loads(output.read_text(encoding="utf-8"))
        validate(saved, f_sha, p_sha, full_focus, excluded)
        rows = saved["rows"]
    else:
        rows = [{"nct": nct, "status": "NOT_QUERIED", "publicationLeads": []}
                for nct in excluded]
    if searcher is None:
        searcher = pubmed.search_pubmed
    attempts = 0
    for i, row in enumerate(rows):
        if row["status"] == "QUERY_SUCCEEDED_UNREVIEWED":
            continue
        if attempts:
            # Other GitHub shards may already make 2.5 requests/s.
            # Adding <= 0.286 requests/s keeps overall pacing below 3/s.
            pause(3.5)
        attempts += 1
        try:
            found = searcher(excluded[i])
            if (not isinstance(found, dict)
                    or found.get("nct") != excluded[i]
                    or found.get("status") != "QUERY_SUCCEEDED_UNREVIEWED"):
                raise ValueError("Wrong exact NCT in PubMed candidate")
            test = list(rows)
            test[i] = found
            validate(report(focus, f_sha, p_sha, full_focus, excluded, test),
                     f_sha, p_sha, full_focus, excluded)
            rows[i] = found
        except (OSError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            rows[i] = {
                "nct": excluded[i], "status": "RETRY_REQUIRED",
                "errorType": type(exc).__name__,
                "publicationLeads": [],
            }
        pubmed.save(output, report(focus, f_sha, p_sha, full_focus, excluded, rows))
    result = report(focus, f_sha, p_sha, full_focus, excluded, rows)
    validate(result, f_sha, p_sha, full_focus, excluded)
    pubmed.save(output, result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--focus", type=Path, default=Path(
        "new-platform/frontend/data/p3PostDataActive.json"))
    parser.add_argument("--pool", type=Path, default=Path(
        "new-platform/frontend/data/tools-pool-snapshot.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    r = collect(args.focus, args.pool, args.output, resume=args.resume)
    print(json.dumps({k: r[k] for k in (
        "fullFocusCount", "focusOnlyCount", "queriesSucceeded",
        "queriesFailed", "publicationLeadsUnreviewed", "status")}))
    return 0 if r["status"] == "FOCUS_ONLY_PUBLICATION_LEADS_QUERIED_NOT_REVIEWED" else 2


if __name__ == "__main__":
    raise SystemExit(main())

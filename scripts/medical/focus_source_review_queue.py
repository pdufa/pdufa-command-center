#!/usr/bin/env python3
"""Exact-NCT FOCUS scientific review queue from source-complete research artifacts.

This is a research coverage queue, NOT any clinical assessment, success
classification, Level 1-20 score, approval prediction or FDA decision.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _module(filename, name):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pubmed = _module("pool_pubmed_discovery.py", "focus_review_queue_pubmed")
focus_pubmed = _module("focus_outside_pool_pubmed.py", "focus_review_queue_focus_only")
sources = _module("pool_source_coverage_manifest.py", "focus_review_queue_registry")


def _read_and_sha(path):
    raw = Path(path).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def _index_by_nct(rows, id_key):
    result = {}
    for row in rows:
        if not isinstance(row, dict) or row.get(id_key) in result:
            raise ValueError("Duplicate or malformed exact NCT source records")
        result[row[id_key]] = row
    return result


def build(focus_path, pool_path, registry_dir, pubmed_path, focus_only_path,
          coverage_path):
    focus, focus_sha = _read_and_sha(focus_path)
    pool, pool_sha = _read_and_sha(pool_path)
    if not isinstance(focus, dict) or not isinstance(focus.get("records"), list):
        raise ValueError("Missing FOCUS roster")
    full_focus, outside_pool = focus_pubmed.exact_focus_outside_pool(focus, pool)
    pool_ncts, _ = pubmed.extract_pool(pool)
    pool_ids = set(pool_ncts)
    registry_dir = Path(registry_dir)
    inventory = sources.read(registry_dir / "inventory.json")
    state = sources.read(registry_dir / "ingestion-state.json")
    literature = sources.read(pubmed_path)
    outside = sources.read(focus_only_path)
    coverage = sources.read(coverage_path)
    if not all(isinstance(x, dict) for x in
               (inventory, state, literature, outside, coverage)):
        raise ValueError("Incomplete source artifact")
    file_hashes = {row["path"]: row["sha256"]
                   for row in inventory["sourceFiles"]}
    if (file_hashes.get("new-platform/frontend/data/tools-pool-snapshot.json") != pool_sha
            or file_hashes.get("new-platform/frontend/data/p3PostDataActive.json") != focus_sha):
        raise ValueError("Source FOCUS or POOL roster SHA-256 mismatch")
    if (coverage.get("status") != "SOURCE_CAPTURE_PRESENT_NOT_SCIENTIFICALLY_REVIEWED"
            or coverage.get("rosterSha256") != pool_sha
            or coverage.get("poolTrials") != len(pool_ncts)
            or coverage.get("rawRegistryPacketsVerifiedLocally") != len(pool_ncts)
            or coverage.get("pubmedQueriesSucceeded") != len(pool_ncts)
            or coverage.get("pubmedQueriesFailed") != 0
            or coverage.get("scientificReviewsCompleted") != 0
            or coverage.get("fdaPredictionsComputed") != 0):
        raise ValueError("Whole-POOL source completion was not independently reconciled")
    pubmed.validate_checkpoint(literature, pool_sha, pool_ncts)
    if (literature.get("status") != "UNREVIEWED_SEARCHES_COMPLETE"
            or literature.get("queriesSucceeded") != len(pool_ncts)
            or literature.get("sourceReviewsCompleted") != 0
            or literature.get("fdaPredictionsComputed") != 0):
        raise ValueError("Incomplete/untrusted whole-POOL publication discovery")
    focus_pubmed.validate(outside, focus_sha, pool_sha, full_focus, outside_pool)
    if (outside.get("status") != "FOCUS_ONLY_PUBLICATION_LEADS_QUERIED_NOT_REVIEWED"
            or outside.get("queriesSucceeded") != len(outside_pool)):
        raise ValueError("FOCUS-only publication discovery not source-complete")
    if (inventory["counts"].get("focusTrials") != len(full_focus)
            or inventory["counts"].get("fullySourceReviewed") != 0):
        raise ValueError("Registry inventory FOCUS count or scientific review truth mismatch")
    registry_by_id = _index_by_nct(inventory["records"], "nctId")
    literature_by_id = _index_by_nct(literature["rows"], "nct")
    focus_only_by_id = _index_by_nct(outside["rows"], "nct")
    if (set(full_focus) != {n for n,r in registry_by_id.items()
                           if r.get("membership", {}).get("focus") is True}
            or set(focus_only_by_id) != set(outside_pool)
            or set(literature_by_id) != pool_ids):
        raise ValueError("Source membership differs from exact FOCUS/POOL roster")
    focus_roster = _index_by_nct(focus["records"], "nct")
    trials, counts = [], Counter()
    for nct in full_focus:
        source_record = registry_by_id[nct]
        if sources.packet_status(registry_dir, state, nct) != (
                "RAW_PACKET_DIGEST_MATCH_NOT_CLINICALLY_REVIEWED"):
            raise ValueError("FOCUS registry packet absent or digest invalid: " + nct)
        entry = state["sources"][nct]["versions"][-1]
        raw = sources.read(registry_dir / entry["cachePath"])
        if raw.get("protocolSection", {}).get("identificationModule", {}).get("nctId") != nct:
            raise ValueError("FOCUS raw registry identity mismatch")
        registered = raw.get("protocolSection", {}).get("outcomesModule", {}).get("primaryOutcomes", []) or []
        result_measures = raw.get("resultsSection", {}).get("outcomeMeasuresModule", {}).get("outcomeMeasures", []) or []
        if not isinstance(registered, list) or not isinstance(result_measures, list):
            raise ValueError("Malformed registered/posted primary outcomes")
        posted = [v for v in result_measures if v.get("type") == "PRIMARY"]
        candidates = (literature_by_id[nct] if nct in pool_ids else focus_only_by_id[nct])
        if candidates.get("status") != "QUERY_SUCCEEDED_UNREVIEWED":
            raise ValueError("PubMed query missing for exact FOCUS NCT: " + nct)
        pmids = [v["pmid"] for v in candidates["publicationLeads"]]
        if len(pmids) != len(set(pmids)):
            raise ValueError("Duplicate unreviewed PMID lead")
        has_primary = bool(posted)
        queue = ("REVIEW_POSTED_REGISTRY_PRIMARY_RESULTS_AND_SAFETY" if has_primary
                 else "FIND_AND_RECONCILE_ORIGINAL_EXTERNAL_PRIMARY_RESULTS")
        trial = {
            "nctId": nct,
            "ticker": focus_roster[nct].get("ticker"),
            "drug": source_record.get("drug"),
            "indication": source_record.get("indication"),
            "phase": source_record.get("phase"),
            "currentRegistryStatus": raw.get("protocolSection", {}).get("statusModule", {}).get("overallStatus"),
            "poolMember": nct in pool_ids,
            "registryPacketSha256": entry["fingerprint"],
            "rawRegistrySourceVerified": True,
            "registeredPrimaryOutcomeCount": len(registered),
            "registeredPrimaryOutcomeDescriptions": [
                {"measure": v.get("measure"), "timeFrame": v.get("timeFrame")}
                for v in registered
            ],
            "postedPrimaryOutcomeCount": len(posted),
            "postedPrimaryOutcomesPresent": has_primary,
            "registrySafetySectionPresent": isinstance(
                raw.get("resultsSection", {}).get("adverseEventsModule"), dict),
            "pubmedQuery": "QUERY_SUCCEEDED_UNREVIEWED",
            "candidatePubmedPmidsUnreviewed": pmids,
            "candidatePublicationCount": len(pmids),
            "sourceResearchPriority": queue,
            "requiredScientificReviews": [
                "Validate exact study and intervention, primary protocol and prespecified statistical analysis plan",
                "Reconcile original efficacy effect sizes, confidence intervals, populations, missing data and multiplicity",
                "Review adverse events, withdrawals and long-term safety with original sources",
                "Confirm regulatory application identity, correspondence, review cycle and FDA decision source",
                "Apply publication/evidence availability dates to every historical blind prediction cutoff",
            ],
            "sourceReviewStatus": "RAW_SOURCE_CAPTURED_NOT_SCIENTIFICALLY_ADJUDICATED",
            "scientificScores": None,
            "fdaApprovalProbability": None,
            "fdaPrediction": "ABSTAIN",
            "productionWritesAllowed": False,
        }
        trials.append(trial)
        counts["rawPacketsVerified"] += 1
        counts["pubmedQueriesSucceeded"] += 1
        counts["unreviewedPublicationLeads"] += len(pmids)
        counts["withPostedPrimaryResults" if has_primary else "withoutPostedPrimaryResults"] += 1
        counts["registeredPrimaryOutcomeMeasures"] += len(registered)
        counts["postedPrimaryOutcomeMeasures"] += len(posted)
        counts["sourceTask_" + queue] += 1
    return {
        "schemaVersion": 1,
        "kind": "FOCUS_32_EXACT_NCT_SOURCE_REVIEW_QUEUE_NOT_A_PREDICTION",
        "status": "ALL_SOURCE_QUERIES_CAPTURED_REVIEW_NOT_YET_COMPLETED",
        "source": {
            "focusRosterSha256": focus_sha,
            "poolRosterSha256": pool_sha,
            "registryInventoryAsOf": inventory.get("asOf"),
            "poolRegistryPacketCount": coverage["rawRegistryPacketsVerifiedLocally"],
            "poolPubmedQueriesCompleted": coverage["pubmedQueriesSucceeded"],
            "focusOnlyPubmedQueriesCompleted": outside["queriesSucceeded"],
            "originalSourceAuditStatus": coverage["status"],
        },
        "counts": {"focusTrials": len(trials),
                   "focusOutsidePool": len(outside_pool),
                   "scientificReviewsCompleted": 0,
                   "fdaPredictionsComputed": 0,
                   **dict(counts)},
        "limitations": [
            "Source capture and query completion do not authenticate matched paper relevance.",
            "Absence of posted registry primary outcomes does not prove absent public trial data.",
            "Posted registry results have not been independently statistically reanalyzed.",
            "Registry safety-section presence does not imply a completed safety review.",
            "All scoring and FDA decisions remain abstaining pending independent validation."
        ],
        "trials": trials
    }


def write_outputs(result, output_json, output_md):
    output_json = Path(output_json)
    output_md = Path(output_md)
    if output_json.resolve() == output_md.resolve():
        raise ValueError("Review queue outputs must be separate")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf8")
    counts = result["counts"]
    lines = [
        "# FOCUS original-source scientific review queue (no scores)",
        "",
        "All 32 exact NCTs have captured original registry packets and completed PubMed searches.",
        "Original source capture is complete; scientific and FDA assessment is NOT complete.",
        "",
        f"- FOCUS trials: {counts['focusTrials']}",
        f"- Posted primary registry results: {counts['withPostedPrimaryResults']}",
        f"- External primary readout reconciliation needed: {counts['withoutPostedPrimaryResults']}",
        f"- Unreviewed trial-PMID leads: {counts['unreviewedPublicationLeads']}",
        f"- Independently completed scientific reviews: {counts['scientificReviewsCompleted']}",
        "",
        "| Ticker | Exact NCT | Posted primary | PubMed candidates | Required source task |",
        "|---|---|---:|---:|---|",
    ]
    for x in result["trials"]:
        lines.append(f"| {x['ticker']} | {x['nctId']} | {x['postedPrimaryOutcomeCount']} | "
                     f"{x['candidatePublicationCount']} | {x['sourceResearchPriority']} |")
    lines += [
        "",
        "Source trust rule: all PMID matches are unreviewed leads, not verified trial efficacy.",
        "No scientific score, approval percentage, FDA outcome or production write is authorized.",
    ]
    output_md.write_text("\n".join(lines) + "\n", encoding="utf8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--focus", type=Path, required=True)
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--registry-dir", type=Path, required=True)
    parser.add_argument("--pool-pubmed", type=Path, required=True)
    parser.add_argument("--focus-only-pubmed", type=Path, required=True)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args(argv)
    result = build(args.focus, args.pool, args.registry_dir,
                   args.pool_pubmed, args.focus_only_pubmed, args.coverage)
    if result["counts"]["focusTrials"] != 32:
        raise ValueError("This run requires the unchanged, verified 32-NCT FOCUS roster")
    write_outputs(result, args.output_json, args.output_md)
    print(json.dumps({k: v for k,v in result["counts"].items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

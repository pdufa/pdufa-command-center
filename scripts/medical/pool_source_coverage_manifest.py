#!/usr/bin/env python3
"""Offline audit of separate whole-POOL registry and PubMed artifacts.

Source archive integrity and identity coverage are NOT scientific review,
efficacy findings, FDA approval probability, or owner verification.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re

NCT = re.compile(r"NCT[0-9]{8}")
SHA = re.compile(r"[0-9a-f]{64}")
VERSION = "pool-source-coverage-manifest-v1"


def read(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > 500_000_000:
        raise ValueError("Source artifact absent/oversized: " + path.name)
    return json.loads(path.read_text(encoding="utf-8"))


def exact(nct):
    return isinstance(nct, str) and NCT.fullmatch(nct) is not None


def packet_status(directory, state, nct):
    source = state.get("sources", {}).get(nct)
    versions = source.get("versions") if isinstance(source, dict) else None
    if not isinstance(versions, list) or not versions:
        return "RAW_PACKET_NOT_CAPTURED"
    version = versions[-1]
    if (not isinstance(version, dict) or not isinstance(version.get("fingerprint"), str)
            or SHA.fullmatch(version["fingerprint"]) is None
            or not isinstance(version.get("cachePath"), str)):
        raise ValueError("Malformed source receipt: " + nct)
    root = Path(directory).resolve()
    path = (root / version["cachePath"]).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Unsafe cache path: " + nct)
    obj = read(path)
    if not isinstance(obj, dict) or obj.get("protocolSection", {}).get("identificationModule", {}).get("nctId") != nct:
        raise ValueError("Wrong exact-NCT registry packet: " + nct)
    digest = hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    if digest != version["fingerprint"]:
        raise ValueError("Registry packet SHA-256 mismatch: " + nct)
    return "RAW_PACKET_DIGEST_MATCH_NOT_CLINICALLY_REVIEWED"


def build(registry_dir, pubmed_path):
    registry_dir = Path(registry_dir)
    inventory = read(registry_dir / "inventory.json")
    state = read(registry_dir / "ingestion-state.json")
    pubmed = read(pubmed_path)
    if not all(isinstance(x, dict) for x in (inventory, state, pubmed)):
        raise ValueError("All source artifacts must be JSON objects")
    if (pubmed.get("schemaVersion") != "pool-pubmed-unreviewed-leads-v1"
            or pubmed.get("scope") != "ALL_EXACT_POOL_TRIAL_NCTS_ALL_PHASES_ALL_STATUSES"):
        raise ValueError("Unexpected PubMed source schema or scope")
    source_files = inventory.get("sourceFiles")
    if not isinstance(source_files, list):
        raise ValueError("Registry inventory source file list missing")
    matching = [s for s in source_files if isinstance(s, dict)
                and s.get("path") == "new-platform/frontend/data/tools-pool-snapshot.json"]
    if (len(matching) != 1 or not isinstance(matching[0].get("sha256"), str)
            or SHA.fullmatch(matching[0]["sha256"]) is None
            or matching[0]["sha256"] != pubmed.get("rosterSha256")):
        raise ValueError("Registry and PubMed POOL snapshot SHA mismatch")
    records = inventory.get("records")
    if not isinstance(records, list) or not 0 < len(records) <= 25000:
        raise ValueError("Invalid full registry inventory")
    seen, pool = set(), {}
    for record in records:
        if not isinstance(record, dict) or not exact(record.get("nctId")):
            raise ValueError("Malformed registry trial identity")
        nct = record["nctId"]
        if nct in seen:
            raise ValueError("Duplicate registry NCT " + nct)
        seen.add(nct)
        membership = record.get("membership")
        if not isinstance(membership, dict) or type(membership.get("pool")) is not bool:
            raise ValueError("Invalid registry source membership")
        if membership["pool"]:
            pool[nct] = record
    if not pool or len(pool) != inventory.get("counts", {}).get("poolUniqueNcts"):
        raise ValueError("Full registry POOL subset mismatched")
    order, pubrows = pubmed.get("nctOrder"), pubmed.get("rows")
    if (not isinstance(order, list) or not isinstance(pubrows, list)
            or len(order) != len(pubrows) or len(order) != len(pool)
            or len(set(order)) != len(order) or set(order) != set(pool)
            or pubmed.get("totalPoolTrials") != len(pool)):
        raise ValueError("Collectors disagree on exact POOL NCT inventory")
    collected = {}
    for nct, record in zip(order, pubrows):
        if (not isinstance(record, dict) or record.get("nct") != nct
                or record.get("status") not in {"NOT_QUERIED", "RETRY_REQUIRED", "QUERY_SUCCEEDED_UNREVIEWED"}
                or not isinstance(record.get("publicationLeads"), list)
                or len(record["publicationLeads"]) > 25):
            raise ValueError("Invalid PubMed research row")
        ids = set()
        for lead in record["publicationLeads"]:
            pmid = lead.get("pmid") if isinstance(lead, dict) else None
            if (not isinstance(pmid, str) or not pmid.isascii() or not pmid.isdecimal()
                    or pmid in ids or not 0 < len(pmid) <= 16
                    or lead.get("url") != "https://pubmed.ncbi.nlm.nih.gov/" + pmid + "/"
                    or lead.get("status") != "UNREVIEWED_LEAD"
                    or lead.get("exactTrialLinkVerified") is not False
                    or lead.get("clinicalFinding") is not None):
                raise ValueError("Unreviewed PubMed lead identity or trust boundary violated")
            ids.add(pmid)
        if record["status"] != "QUERY_SUCCEEDED_UNREVIEWED" and record["publicationLeads"]:
            raise ValueError("Unqueried PubMed trial cannot contain review leads")
        collected[nct] = record
    rows, counts = [], Counter()
    for nct in sorted(pool):
        recorded = pool[nct].get("rawRegistryCaptured")
        if type(recorded) is not bool:
            raise ValueError("Registry raw capture state missing " + nct)
        archive = packet_status(registry_dir, state, nct)
        if recorded != (archive != "RAW_PACKET_NOT_CAPTURED"):
            raise ValueError("Registry packet and inventory state disagree " + nct)
        pub = collected[nct]
        counts["registryPackets"] += int(recorded)
        counts[pub["status"]] += 1
        counts["unreviewedLeads"] += len(pub["publicationLeads"])
        rows.append({
            "nctId": nct, "registry": archive,
            "pubmedQuery": pub["status"],
            "unreviewedPubmedLeads": len(pub["publicationLeads"]),
            "clinicalScientificReview": "NOT_ADJUDICATED",
            "fdaPrediction": "ABSTAIN", "scientificScore": None,
        })
    total = len(pool)
    return {
        "schemaVersion": VERSION,
        "scope": "WHOLE_POOL_EXACT_NCT_RAW_SOURCE_RECONCILIATION",
        "status": ("SOURCE_CAPTURE_PRESENT_NOT_SCIENTIFICALLY_REVIEWED"
                   if counts["registryPackets"] == counts["QUERY_SUCCEEDED_UNREVIEWED"] == total
                   else "PARTIAL_SOURCE_CAPTURE_REQUIRES_FOLLOWUP"),
        "rosterSha256": matching[0]["sha256"],
        "poolTrials": total,
        "rawRegistryPacketsVerifiedLocally": counts["registryPackets"],
        "pubmedQueriesSucceeded": counts["QUERY_SUCCEEDED_UNREVIEWED"],
        "pubmedQueriesFailed": counts["RETRY_REQUIRED"],
        "pubmedQueriesUnattempted": counts["NOT_QUERIED"],
        "pubmedLeadsUnreviewed": counts["unreviewedLeads"],
        "scientificReviewsCompleted": 0,
        "fdaPredictionsComputed": 0,
        "clinicalFindingsVerified": False,
        "assessmentValidation": "NOT_ESTABLISHED",
        "limitations": [
            "Exact-NCT and archive SHA integrity do not authenticate publication conclusions or FDA findings.",
            "A PubMed search result is an unreviewed potential study link; zero matches do not prove lack of evidence.",
            "There is no clinical effect scoring, owner review, validated forecast or production database update.",
        ],
        "rows": rows,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry-dir", type=Path, required=True)
    parser.add_argument("--pubmed", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if output in {(args.registry_dir / "inventory.json").resolve(),
                  (args.registry_dir / "ingestion-state.json").resolve(),
                  args.pubmed.resolve()}:
        raise ValueError("Output must not overwrite source evidence artifacts")
    result = build(args.registry_dir, args.pubmed)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_name(output.name + ".tmp")
    try:
        temp.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(temp, output)
    finally:
        if temp.exists():
            temp.unlink()
    print(json.dumps({k: v for k, v in result.items() if k in (
        "status", "poolTrials", "rawRegistryPacketsVerifiedLocally", "pubmedQueriesSucceeded",
        "pubmedQueriesFailed", "pubmedLeadsUnreviewed")}))
    return 0 if result["status"] == "SOURCE_CAPTURE_PRESENT_NOT_SCIENTIFICALLY_REVIEWED" else 2


if __name__ == "__main__":
    raise SystemExit(main())

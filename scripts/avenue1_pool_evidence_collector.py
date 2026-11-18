#!/usr/bin/env python3
"""Read-only Avenue #1 clinical evidence collector for the entire POOL.

Requires PDUFA_API_BASE_URL and PDUFA_INTERNAL_API_KEY. Does not alter POOL,
FOCUS, prediction scores, or production databases. Output is local JSONL.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

def fetch_json(url, headers=None, attempts=3):
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {
                "User-Agent": "PDUFA-Avenue1-Evidence-Collector/1.0"
            }), timeout=35) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, ValueError):
            if attempt + 1 == attempts:
                raise
            time.sleep(2 ** attempt)

def pool_records():
    base = os.environ.get("PDUFA_API_BASE_URL", "").rstrip("/")
    key = os.environ.get("PDUFA_INTERNAL_API_KEY", "")
    if not base.startswith("https://") or not key:
        raise RuntimeError("Authenticated POOL backend variables missing")
    data = fetch_json(base + "/api/workspace?require_fresh=true", {
        "x-pdufa-internal-key": key, "User-Agent": "PDUFA-Avenue1-Evidence-Collector/1.0"
    })
    # Preserve the complete original source structure for schema inspection.
    return data

def study_evidence(nct):
    study = fetch_json("https://clinicaltrials.gov/api/v2/studies/" + nct)
    protocol = study.get("protocolSection") or {}
    results = study.get("resultsSection") or {}
    outcomes = results.get("outcomeMeasuresModule") or {}
    measures = outcomes.get("outcomeMeasures") or []
    if not isinstance(measures, list) or any(not isinstance(m, dict) for m in measures):
        raise ValueError("Invalid ClinicalTrials.gov outcome measure schema")
    for measure in measures:
        analyses = measure.get("analyses") or []
        if not isinstance(analyses, list) or any(not isinstance(a, dict) for a in analyses):
            raise ValueError("Invalid ClinicalTrials.gov outcome analysis schema")
    arms = (protocol.get("armsInterventionsModule") or {}).get("armGroups") or []
    references = (protocol.get("referencesModule") or {}).get("references") or []
    baseline = (results.get("baselineCharacteristicsModule") or {})
    design_info = (protocol.get("designModule") or {}).get("designInfo") or {}
    # Null registry collections are treated as absent, not as clinical evidence.
    # Raw results are preserved for review; no efficacy claim is inferred.
    clinical_dimensions = {
        "primary_endpoint": (protocol.get("outcomesModule") or {}).get("primaryOutcomes", []),
        "effect_magnitude": measures,
        "statistical_reliability": [
            analysis for measure in measures
            for analysis in (measure.get("analyses") or [])
        ],
        "clinical_meaningfulness": "REQUIRES_CLINICAL_REVIEW",
        "standard_of_care_comparator": arms,
        "durability": "REQUIRES_TIMEFRAME_REVIEW",
        "subgroup_consistency": "REQUIRES_SUBGROUP_REVIEW",
        "replication": "REQUIRES_INDEPENDENT_TRIAL_REVIEW",
        "endpoint_relevance": "REQUIRES_INDICATION_REVIEW",
        "evidence_quality": {
            "allocation": design_info.get("allocation"),
            "masking": design_info.get("maskingInfo"),
            "baseline_characteristics_posted": bool(baseline),
            "references": references,
        },
    }
    return {
        "clinical_dimensions": clinical_dimensions,
        "source_provenance": {
            "registry": "ClinicalTrials.gov",
            "nct": nct,
            "posted_results_available": bool(results),
        },
        "nct": nct,
        "phase": (protocol.get("designModule") or {}).get("phases", []),
        "status": (protocol.get("statusModule") or {}).get("overallStatus"),
        "results_posted": bool(results),
        "primary_outcomes": measures,
        "protocol_outcomes": (protocol.get("outcomesModule") or {}).get("primaryOutcomes", []),
        "adverse_events": results.get("adverseEventsModule"),
        "source": "https://clinicaltrials.gov/study/" + nct,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "superiority_to_active_soc": "NOT_ESTABLISHED_WITHOUT_COMPARATOR_REVIEW",
        "ten_category_scoring": "PENDING_EVIDENCE_REVIEW"
    }

def find_ncts(snapshot):
    """Use ONLY exact TRIAL|NCT records from the unrestricted POOL pipeline."""
    import re
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("pipeline"), list):
        raise RuntimeError("Unexpected POOL schema: pipeline list missing")
    rows = snapshot["pipeline"]
    health = snapshot.get("sourceHealth") or {}
    parity = health.get("pipelineSourceParity") or health.get("streamlitPipelineParity") or {}
    if health.get("state") != "FRESH" or parity.get("exactPrograms") != len(rows):
        raise RuntimeError("POOL source freshness/parity not verified")
    if (health.get("clinicalRows", 0) + health.get("regulatoryRows", 0)) != len(rows):
        raise RuntimeError("POOL clinical/regulatory source counts do not match pipeline")
    ids = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise RuntimeError("Invalid POOL row identity")
        identity = row["id"]
        if re.fullmatch(r"TRIAL\|NCT\d{8}", identity):
            nct = identity.split("|", 1)[1]
            if nct in seen:
                raise RuntimeError("Duplicate POOL trial identity: " + nct)
            seen.add(nct)
            ids.append(nct)
    return sorted(ids)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default="artifacts/avenue1")
    p.add_argument("--limit", type=int, default=0, help="Optional test limit; 0 means all")
    args = p.parse_args()
    if args.limit < 0:
        p.error("--limit must be zero (all) or a positive integer")
    raw = pool_records()
    ids = find_ncts(raw)
    if not ids:
        raise RuntimeError("No exact NCT identifiers in authenticated POOL source; schema review required")
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "pool-source-inventory.json").write_text(json.dumps({
        "nct_count": len(ids), "ncts": ids, "source": "authenticated backend /api/workspace",
        "as_of": datetime.now(timezone.utc).isoformat()
    }, indent=2))
    trial_metadata = {row["id"].split("|", 1)[1]: row for row in raw["pipeline"]
                      if row["id"].startswith("TRIAL|NCT") and row["id"].split("|", 1)[1] in ids}
    errors = []
    done = 0
    dimension_counts = {name: 0 for name in (
        "primary_endpoint", "effect_magnitude", "statistical_reliability",
        "clinical_meaningfulness", "standard_of_care_comparator",
        "durability", "subgroup_consistency", "replication",
        "endpoint_relevance", "evidence_quality")}
    missing_by_trial = []
    with (out / "clinical-evidence.jsonl").open("w") as f:
        for nct in ids[:args.limit or None]:
            try:
                evidence = study_evidence(nct)
                evidence["pool_record"] = trial_metadata[nct]
                evidence["pool_source_as_of"] = raw.get("asOf")
                dimensions = evidence["clinical_dimensions"]
                missing = []
                for name, value in dimensions.items():
                    has_evidence = bool(value) and not (
                        isinstance(value, str) and value.startswith("REQUIRES_")
                    )
                    if name == "evidence_quality":
                        has_evidence = bool(value.get("allocation") or value.get("masking") or value.get("references"))
                    if has_evidence:
                        dimension_counts[name] += 1
                    else:
                        missing.append(name)
                missing_by_trial.append({"nct": nct, "missing_dimensions": missing})
                f.write(json.dumps(evidence) + "\n")
                done += 1
            except Exception as exc:
                errors.append({"nct": nct, "error_type": type(exc).__name__})
            time.sleep(0.15)
    attempted = min(len(ids), args.limit) if args.limit else len(ids)
    (out / "collection-status.json").write_text(json.dumps({
        "pool_nct_count": len(ids),
        "attempted": attempted,
        "collected": done,
        "error_count": len(errors),
        "coverage_percent": round(100 * done / attempted, 2),
        "full_pool_run": attempted == len(ids),
        "full_pool_collection_complete": attempted == len(ids) and done == len(ids) and not errors,
        "errors": errors,
        "dimension_evidence_counts": dimension_counts,
        "missing_dimensions_by_trial": missing_by_trial,
        "coverage_note": "Field presence is not proof of clinical sufficiency or efficacy.",
        "note": "Results posting is not proof of efficacy or superiority; no scores assigned."
    }, indent=2))
    print(f"POOL NCTs={len(ids)}; collected={done}; errors={len(errors)}")
    return 0 if not errors else 2

if __name__ == "__main__":
    sys.exit(main())

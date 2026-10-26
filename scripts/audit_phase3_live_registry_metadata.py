#!/usr/bin/env python3
"""Read-only live ClinicalTrials.gov metadata refresh for 741 historical NCTs.

Current registry sponsor, status, interventions and conditions are *research*
metadata; none alone establish a current issuer's legal development rights,
an FDA application or a PDUFA decision date.
"""
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
TRIALS = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
MAX_BYTES = 500_000


def extract(nct, payload):
    p = payload.get("protocolSection", {})
    identity = p.get("identificationModule", {})
    if identity.get("nctId") != nct:
        raise ValueError("Registry returned wrong NCT")
    sponsor = p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name")
    status = p.get("statusModule", {})
    design = p.get("designModule", {})
    arms = p.get("armsInterventionsModule", {})
    return {
        "nct_id": nct, "live_registry_lead_sponsor": sponsor,
        "live_registry_status": status.get("overallStatus"),
        "registry_last_update_posted": status.get("studyFirstPostDateStruct", {}).get("date"),
        "registry_last_update_submitted": status.get("studyFirstSubmitDate"),
        "registry_last_update_posted_date": status.get("lastUpdatePostDateStruct", {}).get("date"),
        "phases": design.get("phases", []),
        "interventions": [{"type": x.get("type"), "name": x.get("name")} for x in arms.get("interventions", [])][:40],
        "conditions": p.get("conditionsModule", {}).get("conditions", [])[:40],
    }


def retrieve(nct):
    if not re.fullmatch(r"NCT\d{8}", nct):
        raise ValueError("Malformed NCT")
    url = f"https://clinicaltrials.gov/api/v2/studies/{nct}"
    request = urllib.request.Request(url, headers={
        "User-Agent": "PDUFACommandCenterResearch/1.0 (read-only)",
        "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=16) as response:
        if response.status != 200:
            raise ValueError("Registry HTTP not 200")
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Registry response too large")
    return extract(nct, json.loads(data))


def run(fetcher=retrieve):
    saved = list(csv.DictReader(TRIALS.open(encoding="utf-8-sig", newline="")))
    if len(saved) != 741 or len({r["nct_id"] for r in saved}) != 741 or len({r["ticker"] for r in saved}) != 130:
        raise ValueError("Original research census identity mismatch")
    results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetcher, row["nct_id"]): row for row in saved}
        for future in as_completed(futures):
            row = futures[future]
            item = {"nct_id": row["nct_id"], "ticker": row["ticker"],
                    "saved_original_lead_sponsor": row["company"],
                    "saved_original_status": row["status"],
                    "registry_url": row["source_url"],
                    "live_retrieved_at_utc": None,
                    "current_registry_metadata": None,
                    "sponsor_name_equal": None, "error": None,
                    "current_legal_rights_verified": False,
                    "fda_pdufa_verified": False, "qualified_pipeline": None}
            try:
                data = future.result()
                item["current_registry_metadata"] = data
                item["live_retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
                item["sponsor_name_equal"] = data["live_registry_lead_sponsor"] == row["company"]
            except (urllib.error.URLError, OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                item["error"] = type(exc).__name__ + ": " + str(exc)[:160]
            results.append(item)
    results.sort(key=lambda x: x["nct_id"])
    retrieved = sum(r["current_registry_metadata"] is not None for r in results)
    same = sum(r["sponsor_name_equal"] is True for r in results)
    changed = sum(r["sponsor_name_equal"] is False for r in results)
    return {"scope": "LIVE_REGISTRY_METADATA_RESEARCH_ONLY",
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "historical_trial_count": 741, "historical_issuer_count": 130,
            "registry_metadata_retrieved": retrieved,
            "registry_metadata_unresolved": 741-retrieved,
            "saved_vs_current_lead_sponsor_equal": same,
            "saved_vs_current_lead_sponsor_changed": changed,
            "current_legal_rights_verified": 0, "fda_pdufa_verified": 0,
            "qualified_pipeline_count": None,
            "trials": results,
            "limitations": "Registry metadata is not legal rights, FDA NDA/BLA/IND status, or PDUFA evidence. Errors remain unresolved."}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: audit_phase3_live_registry_metadata.py <report.json>")
    result = run()
    path = Path(sys.argv[1])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Live ClinicalTrials.gov metadata:", result["registry_metadata_retrieved"], "/741")
    print("Unresolved registry fetches:", result["registry_metadata_unresolved"], "/741")
    print("Exact current sponsor-name matches:", result["saved_vs_current_lead_sponsor_equal"], "/741")
    print("Changed current sponsor names:", result["saved_vs_current_lead_sponsor_changed"], "/741")
    print("Current legal rights verified: 0/741; FDA/PDUFA verified: 0/741; qualified Pipeline: UNKNOWN.")

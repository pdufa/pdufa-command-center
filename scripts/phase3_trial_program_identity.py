#!/usr/bin/env python3
"""Read-only original trial drug and indication leads for all 741 Phase 3 studies.

Registry intervention names are NOT proven distinct products, regulatory
indications, current licenses, active development, or Pipeline qualification.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

EXPECTED = 741
ISSUERS = 130
NAME_STATES = {"PRESENT", "EMPTY", "SECTION_MISSING", "SECTION_INVALID",
               "FIELD_MISSING", "FIELD_INVALID", "OVER_LIMIT_REVIEW", "ITEM_INVALID"}
SOURCE = "https://clinicaltrials.gov/api/v2/studies/"
CONTROLS = re.compile(r"^(placebo|saline|vehicle|sham|observation|no intervention|standard of care|best supportive care|usual care)(?:\\b|$)", re.I)
NCT = re.compile(r"^NCT[0-9]{8}$")
SHA = re.compile(r"^[0-9a-fA-F]{64}$")


def exact_index(items, name):
    if not isinstance(items, list) or len(items) != EXPECTED:
        raise ValueError(f"Expected 741 complete {name} rows")
    index = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f"Invalid {name} row")
        nct = item.get("nct_id")
        if not isinstance(nct, str) or not NCT.fullmatch(nct) or nct in index:
            raise ValueError(f"Invalid or duplicate {name} NCT identity")
        index[nct] = item
    return index


def validate_names(value, state, count, typed=False):
    if state not in NAME_STATES or type(count) is not int or count < 0:
        raise ValueError("Invalid original registry program field status")
    if not isinstance(value, list) or len(value) > 100:
        raise ValueError("Invalid original registry program list")
    if state == "PRESENT" and (not value or len(value) != count):
        raise ValueError("Incomplete original program field")
    if state == "EMPTY" and (value or count != 0):
        raise ValueError("Invalid empty original program field")
    if state not in {"PRESENT", "EMPTY"} and value:
        raise ValueError("Invalid original field cannot provide trusted names")
    if state in {"SECTION_MISSING", "SECTION_INVALID", "FIELD_MISSING", "FIELD_INVALID"} and count:
        raise ValueError("Invalid field should not advertise source item counts")
    if state == "OVER_LIMIT_REVIEW" and count <= 100:
        raise ValueError("Source over-limit status inconsistent")
    for entry in value:
        if typed:
            if not isinstance(entry, dict) or set(entry) != {"name", "type"}:
                raise ValueError("Invalid registry intervention record")
            name, kind = entry["name"], entry["type"]
            if not isinstance(kind, str) or not kind or len(kind) > 80:
                raise ValueError("Invalid registry intervention type")
        else:
            name = entry
        if not isinstance(name, str) or not name.strip() or len(name) > 400:
            raise ValueError("Invalid registry program name")


def build_report(registry, casebook):
    if (registry.get("census_total") != EXPECTED
        or registry.get("source_identity_verified") != EXPECTED
        or registry.get("source_errors") != []
        or registry.get("qualified_pipeline_total") is not None
        or casebook.get("report_type") != "MAIN_PHASE3_RIGHTS_CASEBOOK_RESEARCH_ONLY"
        or casebook.get("total_trials") != EXPECTED
        or casebook.get("saved_issuer_pointers") != ISSUERS
        or casebook.get("rights_verified_trials") != 0
        or casebook.get("rights_unverified_trials") != EXPECTED
        or casebook.get("qualified_pipeline_total") is not None):
        raise ValueError("Incomplete original registry / rights casebook or unsafe scope")
    sources = exact_index(registry.get("original_source_records"), "registry")
    records = exact_index(casebook.get("items"), "rights casebook")
    if set(sources) != set(records):
        raise ValueError("Original registry NCT identities differ from rights casebook")
    rows = []
    condition_present = 0
    intervention_present = 0
    drug_name_present = 0
    missing_or_malformed = 0
    status_counts = Counter()
    ticker_set = set()
    for nct in sorted(records):
        source, record = sources[nct], records[nct]
        ticker = record.get("ticker")
        if (not isinstance(ticker, str) or not ticker
            or source.get("nct_id") != nct
            or source.get("census_ticker") != ticker
            or source.get("census_company") != record.get("saved_census_company")
            or source.get("source") != SOURCE + nct
            or record.get("original_registry_api_url") != SOURCE + nct
            or source.get("source_sha256") != record.get("original_registry_sha256")
            or not isinstance(source.get("source_sha256"), str)
            or not SHA.fullmatch(source["source_sha256"])
            or record.get("rights_verification_status") != "NOT_ESTABLISHED"
            or record.get("qualified_pipeline") is not None):
            raise ValueError(f"{nct}: mismatched source, issuer, or qualification boundary")
        condition_names = source.get("registry_condition_names")
        intervention_names = source.get("registry_interventions")
        condition_state = source.get("registry_conditions_field_status")
        intervention_state = source.get("registry_interventions_field_status")
        validate_names(condition_names, condition_state, source.get("registry_conditions_source_count"))
        validate_names(intervention_names, intervention_state, source.get("registry_interventions_source_count"), typed=True)
        title = source.get("registry_study_title")
        if not isinstance(title, str) or not title.strip() or len(title) > 1000:
            raise ValueError("Missing bounded original registry study title")
        candidates = []
        for item in intervention_names:
            if item["type"].upper() in {"DRUG", "BIOLOGICAL"} and not CONTROLS.match(item["name"]):
                if item["name"] not in candidates:
                    candidates.append(item["name"])
        ticker_set.add(ticker)
        condition_present += condition_state == "PRESENT"
        intervention_present += intervention_state == "PRESENT"
        drug_name_present += bool(candidates)
        missing_or_malformed += (condition_state not in {"PRESENT", "EMPTY"} or
                                 intervention_state not in {"PRESENT", "EMPTY"})
        status_counts[(condition_state, intervention_state)] += 1
        rows.append({
            "nct_id": nct, "ticker": ticker,
            "original_registry_source_url": SOURCE + nct,
            "original_registry_source_sha256": source["source_sha256"],
            "original_registry_study_title": title,
            "registry_conditions": condition_names,
            "conditions_field_status": condition_state,
            "registry_interventions": intervention_names,
            "interventions_field_status": intervention_state,
            "provisional_drug_or_biologic_names": candidates,
            "drug_indication_qualified": False,
            "commercial_rights_verified": False,
            "qualified_pipeline": None,
            "identity_review_status": "REGISTRY_TERMS_REQUIRE_INDEPENDENT_REVIEW",
        })
    if len(ticker_set) != ISSUERS:
        raise ValueError("Original 130-issuer scope is incomplete")
    return {
        "report_type": "MAIN_PHASE3_ORIGINAL_DRUG_INDICATION_TERMS_RESEARCH_ONLY",
        "total_trials": EXPECTED, "total_saved_issuer_pointers": ISSUERS,
        "trials_with_named_conditions": condition_present,
        "trials_with_named_interventions": intervention_present,
        "trials_with_provisional_drug_or_biologic_mentions": drug_name_present,
        "trials_without_provisional_drug_or_biologic_mentions": EXPECTED - drug_name_present,
        "trials_with_missing_or_invalid_original_program_fields": missing_or_malformed,
        "registry_field_status_counts": {
            f"{a}|{b}": count for (a, b), count in sorted(status_counts.items())
        }, "independently_verified_program_identities": 0,
        "independently_verified_commercial_rights": 0,
        "qualified_pipeline_total": None,
        "items": rows,
        "limitations": ("ClinicalTrials.gov registered intervention names and conditions are "
                        "source-linked research labels, not independently verified active drugs, "
                        "U.S. indications, licensing, development rights or FDA outcomes. "
                        "Placebo/control-name filtering does not establish molecular identity. "
                        "No Pipeline/GEM promotion."),
    }


def main():
    if len(sys.argv) != 4:
        sys.exit("Usage: phase3_trial_program_identity.py <registry.json> <rights-casebook.json> <output.json>")
    report = build_report(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")),
                          json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")))
    output = Path(sys.argv[3])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    print(f"Original drug/indication leads: {report['total_trials']}/741 source identities, "
          f"drug or biologic mentions {report['trials_with_provisional_drug_or_biologic_mentions']}/741; "
          "verified program rights 0/741")


if __name__ == "__main__":
    main()

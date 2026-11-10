#!/usr/bin/env python3
"""Attach registry evidence leads to specialty dossiers without clinical adjudication."""
import argparse
import json
from pathlib import Path

FIELD_DIMENSIONS = {
    "disease_subtype_and_diagnostic_criteria": ("conditions", "eligibility"),
    "current_standard_of_care_and_comparator": ("arms",),
    "endpoint_validity_and_clinical_meaning": ("primaryEndpoints", "secondaryEndpoints"),
    "population_generalizability": ("eligibility", "enrollment"),
    "magnitude_and_durability_of_benefit": ("primaryEndpoints", "secondaryEndpoints"),
    "specialty_specific_safety": (),
    "unmet_need_and_alternatives": (),
    "regulatory_precedent_and_uncertainties": (),
}

def enrich(dossier_report, checkpoint):
    records = checkpoint.get("results", {})
    dossiers = dossier_report.get("dossiers", [])
    if dossier_report.get("status") != "DOSSIER_SHELLS_ONLY" or len(dossiers) != 29:
        raise ValueError("Expected 29 unadjudicated dossier shells")
    if len({d["nct"] for d in dossiers}) != 29:
        raise ValueError("Duplicate dossier NCT")
    for dossier in dossiers:
        nct = dossier["nct"]
        result = records.get(nct, {})
        evidence = result.get("evidence", {}) if result.get("status") == "CAPTURED_UNREVIEWED" else {}
        if evidence and evidence.get("nct") != nct:
            raise ValueError("Cross-trial evidence rejected")
        fields = evidence.get("fields", {})
        source = evidence.get("source")
        sha = evidence.get("sha256")
        for name, field_names in FIELD_DIMENSIONS.items():
            leads = []
            for field_name in field_names:
                field = fields.get(field_name, {})
                if (field.get("status") == "CAPTURED_UNREVIEWED" and field.get("value") is not None
                        and source and sha and field.get("locator")):
                    leads.append({"sourceUrl": source, "sourceSha256": sha,
                                  "locator": field["locator"], "registryField": field_name,
                                  "evidenceStatus": "UNREVIEWED_REGISTRY_LEAD"})
            dossier["dimensions"][name]["registryEvidenceLeads"] = leads
            dossier["dimensions"][name]["status"] = "EVIDENCE_REQUIRED"
        dossier["dossierStatus"] = "NOT_SCIENTIFICALLY_ADJUDICATED"
    dossier_report["status"] = "UNREVIEWED_REGISTRY_EVIDENCE_LEADS"
    dossier_report["scientificallyAdjudicated"] = 0
    dossier_report["registryEvidenceLeadCount"] = sum(
        len(d["dimensions"][k]["registryEvidenceLeads"])
        for d in dossiers for k in FIELD_DIMENSIONS)
    return dossier_report

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dossiers", type=Path, required=True)
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    report = enrich(json.loads(a.dossiers.read_text()), json.loads(a.checkpoint.read_text()))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"trialCount": len(report["dossiers"]), "registryEvidenceLeadCount": report["registryEvidenceLeadCount"]}))

if __name__ == "__main__":
    main()

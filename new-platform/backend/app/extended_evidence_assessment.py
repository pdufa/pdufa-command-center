"""Level 7 provenance and Level 8 normalized identity for runtime snapshots."""

from datetime import date, datetime, timezone
import json
import re


def assess_evidence_level(request, source):
    """Use only the runtime's frozen input and its provenance receipt."""
    protocol = json.loads(source["document_json"])["protocolSection"]
    identity = protocol.get("identificationModule", {})
    study = protocol.get("designModule", {})
    conditions = protocol.get("conditionsModule", {}).get("conditions", [])
    phases = study.get("phases", [])
    nct = request.nct
    posted = protocol.get("statusModule", {}).get("lastUpdatePostDateStruct", {}).get("date")
    captured_at = datetime.fromisoformat(source["captured_at"])
    chronology_ok = bool(
        posted and posted == source["published_at"] and captured_at.tzinfo is not None
        and date.fromisoformat(posted) <= captured_at.astimezone(timezone.utc).date()
    )
    exact_identity = nct == source["nct_id"] == identity.get("nctId")

    def check(key, available, explanation, locator):
        return {"id": key, "state": "AVAILABLE" if available else "MISSING",
                "explanation": explanation, "locator": locator}

    if request.level == 7:
        name = "Evidence collection and provenance"
        checks = [
            check("exact_nct", exact_identity, "Registry payload must match the requested NCT.",
                  "protocolSection.identificationModule.nctId"),
            check("registry_origin", source["source_url"] == f"https://clinicaltrials.gov/api/v2/studies/{nct}",
                  "Require the exact official registry origin.", "evidence.source_url"),
            check("dated_revision", chronology_ok, "Record posted and captured dates in chronological order.",
                  "protocolSection.statusModule.lastUpdatePostDateStruct.date"),
            check("fingerprints", all(re.fullmatch("[a-f0-9]{64}", source.get(key) or "")
                                      for key in ("raw_sha256", "input_sha256")),
                  "Retain the source receipt and sanitized execution fingerprints.", "evidence"),
        ]
        observations = {"registryPostedOn": posted, "capturedAt": source["captured_at"]}
    elif request.level == 8:
        name = "Trial identity and normalized evidence readiness"
        normalized_conditions = list(dict.fromkeys(
            item.strip() for item in conditions if isinstance(item, str) and item.strip()
        ))
        sponsor = protocol.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name")
        checks = [
            check("exact_nct", exact_identity, "Require matching exact registry trial identity.",
                  "protocolSection.identificationModule.nctId"),
            check("trial_phase", bool(phases and "NA" not in phases), "Require a stated clinical phase.",
                  "protocolSection.designModule.phases"),
            check("condition", bool(normalized_conditions), "Require recorded study conditions.",
                  "protocolSection.conditionsModule.conditions"),
            check("lead_sponsor", bool(sponsor), "Require a registry lead sponsor.",
                  "protocolSection.sponsorCollaboratorsModule.leadSponsor.name"),
            check("study_type", bool(study.get("studyType")), "Require a stated study type.",
                  "protocolSection.designModule.studyType"),
            check("corroboration", False, "The frozen input does not carry corroborating exact-program source receipts.",
                  "evidence"),
        ]
        observations = {"registryConditions": normalized_conditions, "registryPhases": phases,
                        "leadSponsor": sponsor, "studyType": study.get("studyType")}
    else:
        raise ValueError("Expected Level 7 or Level 8")
    return {
        "name": name,
        "checks": checks,
        "observations": observations,
        "limitations": ["Registry metadata is sponsor-reported and does not establish application identity or clinical validity."],
        "scientificStatus": (
            "EVIDENCE_GAPS" if any(item["state"] == "MISSING" for item in checks)
            else "SOURCE_CHECKS_COMPLETE_NOT_CLINICAL_VALIDATION"
        ),
    }

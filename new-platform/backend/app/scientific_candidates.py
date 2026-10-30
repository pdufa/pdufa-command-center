"""Source-grounded scientific-candidate dossiers; no predictions or writes.

An archived field is not an independent source check. A fresh registry record
can establish what the registry currently reports, not the clinical validity of
the report. FDA, submission, designation and PDUFA facts remain unknown unless
separately supplied with exact-trial scoped primary-source provenance.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
import math
import re
from urllib.parse import urlsplit

VERSION = "scientific-candidate-readiness-v1"
NCT = re.compile(r"NCT[0-9]{8}\Z")
REGULATORY_ID = re.compile(r"\b(IND|NDA|BLA|ANDA)\s*(?:NO\.?|NUMBER|#|:|-)?\s*(\d{3,8})\b", re.I)
P_VALUE = re.compile(r"\s*(<=|>=|<|>|=|~)?\s*((?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*\Z")
CHECKLIST_FIELDS = (
    "nct_identifier", "sponsor", "drug_or_biological_product", "indication", "trial_phase",
    "primary_endpoint", "primary_endpoint_results", "statistical_significance", "clinical_effect_size",
    "safety_findings", "serious_adverse_events", "study_completion_status", "fda_regulatory_pathway",
    "special_designations", "regulatory_submission_evidence", "pdufa_date", "evidence_completeness",
    "conflicting_or_missing_information", "scientific_assessment_eligibility", "source_provenance",
)
FRAMEWORK_REFERENCE = {
    "source_url": "https://github.com/pdufa/pdufa-command-center/blob/main/new-platform/backend/app/science_40_question_catalog.json",
    "catalog_blob_sha": "85f068c52e5337ca09d8a1c9416377c8cca1ea8f",
    "framework": "science-40-question-catalog-v1",
    "layers": ["Clinical efficacy", "Statistical integrity", "Trial design", "Safety", "Reproducibility",
               "Regulatory pathway", "Manufacturing and quality", "External validity and comparators"],
    "investigation_depth_levels": list(range(1, 21)),
    "assessment_ids": [f"S{i:02d}" for i in range(1, 41)],
    "assessments_completed": 0, "investigation_depths_completed": 0,
    "status": "HANDOFF_ONLY_NOT_EXECUTED",
    "gate": "Existing SCIENCE40 public Phase3 results plus independently documented PDUFA date gate remains in force.",
}


def _obj(value):
    return value if isinstance(value, dict) else {}


def _rows(value):
    return [r for r in value if isinstance(r, dict)] if isinstance(value, list) else []


def _strings(value):
    return [v.strip() for v in value if isinstance(v, str) and v.strip()] if isinstance(value, list) else []


def _named(value):
    return isinstance(value, str) and value.strip().lower() not in {"", "unknown", "n/a", "not available", "not specified", "none", "tbd"}


def _numeric(value):
    if value is None or isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except (ValueError, TypeError):
        return False


def _time(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else None
    except ValueError:
        return None


def _url(value):
    if not isinstance(value, str) or any(c.isspace() for c in value):
        return False
    try:
        p = urlsplit(value)
        return p.scheme == "https" and bool(p.hostname) and "." in p.hostname and p.username is None and p.password is None and p.port in (None, 443)
    except ValueError:
        return False


def _actual_elapsed(value, cutoff):
    item = _obj(value)
    raw = item.get("date")
    if item.get("type") != "ACTUAL" or not isinstance(raw, str):
        return False
    try:
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", raw):
            last = date.fromisoformat(raw)
        elif re.fullmatch(r"[0-9]{4}-[0-9]{2}", raw):
            import calendar
            year, month = map(int, raw.split("-"))
            last = date(year, month, calendar.monthrange(year, month)[1])
        elif re.fullmatch(r"[0-9]{4}", raw):
            last = date(int(raw), 12, 31)
        else:
            return False
        return last <= cutoff
    except (ValueError, OverflowError):
        return False


def extract_regulatory_identifiers(study):
    """Return exact explicit secondary-ID candidates, not verified FDA claims."""
    ident = _obj(_obj(_obj(study).get("protocolSection")).get("identificationModule"))
    found = []
    for index, row in enumerate(_rows(ident.get("secondaryIdInfos"))):
        raw = " ".join(str(row.get(k, "")) for k in ("id", "type", "domain"))
        for match in REGULATORY_ID.finditer(raw):
            found.append({"nct_id": ident.get("nctId"), "identifier": match.group(0),
                          "identifier_type": match.group(1).upper(), "identifier_number": match.group(2),
                          "raw_secondary_id": dict(row), "source_field": f"protocolSection.identificationModule.secondaryIdInfos[{index}]",
                          "classification": "UNRESOLVED"})
    return found


def _analysis(analysis):
    fields = ("groupIds", "groupDescription", "testedNonInferiority", "nonInferiorityType", "nonInferiorityComment",
              "statisticalMethod", "statisticalComment", "pValue", "pValueComment", "paramType", "paramValue",
              "paramSpreadType", "paramSpreadValue", "ciPctValue", "ciNumSides", "ciLowerLimit", "ciUpperLimit", "estimateComment")
    result = {k: analysis[k] for k in fields if k in analysis}
    p = P_VALUE.fullmatch(str(analysis.get("pValue", "")))
    if p and 0 <= float(p.group(2)) <= 1:
        result["parsed_p_value"] = {"qualifier": p.group(1) or "=", "value": float(p.group(2))}
    result["significance_conclusion"] = "NOT_INFERRED: alpha, multiplicity, analysis population and prespecification require source review"
    return result


def _outcome(outcome):
    fields = ("type", "title", "description", "populationDescription", "reportingStatus", "timeFrame", "paramType",
              "dispersionType", "unitOfMeasure", "calculatePct", "denomUnitsSelected", "groups", "denoms", "classes")
    result = {k: outcome[k] for k in fields if k in outcome}
    result["analyses"] = [_analysis(a) for a in _rows(outcome.get("analyses"))]
    return result


def _has_measurements(outcome):
    return any(_numeric(m.get("value")) for c in _rows(outcome.get("classes"))
               for category in _rows(c.get("categories")) for m in _rows(category.get("measurements")))


def _ae_information(module):
    fields = ("frequencyThreshold", "timeFrame", "description", "eventGroups", "seriousEvents", "otherEvents")
    return {k: module[k] for k in fields if k in module}


def _sae_counts(module):
    groups = _rows(module.get("eventGroups"))
    # Explicit group totals, including zero, are preferable to summing event rows,
    # where a participant can appear more than once.
    totals = [{k: row[k] for k in ("id", "title", "description", "seriousNumAffected", "seriousNumAtRisk", "deathsNumAffected", "deathsNumAtRisk") if k in row}
              for row in groups if any(_numeric(row.get(k)) for k in ("seriousNumAffected", "seriousNumAtRisk"))]
    event_stats = [{"term": event.get("term"), "organ_system": event.get("organSystem"), "stats": event.get("stats", [])}
                   for event in _rows(module.get("seriousEvents"))
                   if any(_numeric(stat.get(k)) for stat in _rows(event.get("stats")) for k in ("numAffected", "numAtRisk", "numEvents"))]
    denominator = any(_numeric(row.get("seriousNumAtRisk")) and float(row["seriousNumAtRisk"]) > 0 for row in groups)
    denominator = denominator or any(_numeric(stat.get("numAtRisk")) and float(stat["numAtRisk"]) > 0
                                     for event in _rows(module.get("seriousEvents")) for stat in _rows(event.get("stats")))
    return {"reported": bool(totals or event_stats), "group_totals": totals, "event_statistics": event_stats,
            "positive_denominator_reported": denominator,
            "interpretation": "Source-reported counts; no causal attribution or benefit-risk conclusion inferred."}


def _external(field, evidence, nct, verified_at):
    row = _obj(evidence.get(field))
    checked = _time(row.get("verified_at"))
    cutoff = _time(verified_at)
    host = urlsplit(row.get("source_url", "")).hostname if _url(row.get("source_url")) else ""
    authoritative = ((row.get("source_type") == "FDA" and (host == "fda.gov" or host.endswith(".fda.gov")))
                     or (row.get("source_type") == "SPONSOR_REGULATORY_DISCLOSURE" and row.get("sponsor_domain_verified") is True))
    supported = (row.get("status") == "VERIFIED" and row.get("nct_id") == nct
                 and row.get("source_type") in ("FDA", "SPONSOR_REGULATORY_DISCLOSURE")
                 and authoritative and _url(row.get("source_url")) and bool(checked) and bool(cutoff) and checked <= cutoff
                 and bool(re.fullmatch(r"[a-f0-9]{64}", str(row.get("source_document_sha256", ""))))
                 and row.get("value") is not None)
    if supported and field == "pdufa_date":
        raw_date = _obj(row.get("value")).get("date") if isinstance(row.get("value"), dict) else row.get("value")
        try:
            supported = isinstance(raw_date, str) and len(raw_date) == 10 and date.fromisoformat(raw_date).isoformat() == raw_date
        except ValueError:
            supported = False
    return {"status": "VERIFIED" if supported else "UNRESOLVED", "value": row.get("value") if supported else None,
            "evidence": row if row else None,
            "limitation": "A source-scoped verification record is required; trial phase and FDA-regulation flags do not establish regulatory status."}


def build_dossier(archived_study, live_study=None, *, archived_sha256=None, verified_at=None,
                  source_status="FETCHED", external_evidence=None, live_sha256=None):
    """Produce a complete evidence dossier without performing an investigation.

    external_evidence fields: fda_regulatory_pathway, special_designations,
    regulatory_submission_evidence, pdufa_date. A supported entry needs VERIFIED,
    exact nct_id, FDA/SPONSOR_REGULATORY_DISCLOSURE source_type, HTTPS source_url,
    source_document_sha256, verified_at and value. Such metadata never certifies
    the separate 40 assessments or adjudication register.
    """
    stamp = verified_at or datetime.now(timezone.utc).isoformat()
    if _time(stamp) is None:
        raise ValueError("A timezone-aware verification timestamp is required")
    archive = _obj(archived_study)
    archive_nct = _obj(_obj(archive.get("protocolSection")).get("identificationModule")).get("nctId")
    live = _obj(live_study)
    live_nct = _obj(_obj(live.get("protocolSection")).get("identificationModule")).get("nctId")
    identity_ok = isinstance(archive_nct, str) and bool(NCT.fullmatch(archive_nct))
    checked = source_status == "FETCHED" and bool(live) and identity_ok and live_nct == archive_nct
    conflicts = []
    if live and live_nct != archive_nct:
        conflicts.append({"field": "nct_identifier", "archive": archive_nct, "live": live_nct,
                          "severity": "CRITICAL", "explanation": "Fresh registry identity does not match the archived trial."})
    current = live if checked else archive
    protocol, results = _obj(current.get("protocolSection")), _obj(current.get("resultsSection"))
    identification = _obj(protocol.get("identificationModule"))
    sponsor = _obj(_obj(protocol.get("sponsorCollaboratorsModule")).get("leadSponsor"))
    products = [{k: r[k] for k in ("type", "name", "description", "otherNames") if k in r}
                for r in _rows(_obj(protocol.get("armsInterventionsModule")).get("interventions"))
                if r.get("type") in ("DRUG", "BIOLOGICAL") and _named(r.get("name"))]
    indications = _strings(_obj(protocol.get("conditionsModule")).get("conditions"))
    phases = _strings(_obj(protocol.get("designModule")).get("phases"))
    registered = _rows(_obj(protocol.get("outcomesModule")).get("primaryOutcomes"))
    outcomes = [_outcome(o) for o in _rows(_obj(results.get("outcomeMeasuresModule")).get("outcomeMeasures")) if o.get("type") == "PRIMARY"]
    quantitative = [o for o in outcomes if _has_measurements(o)]
    analyses = [{"outcome_title": o.get("title"), **a} for o in outcomes for a in o["analyses"]]
    effect = [a for a in analyses if _numeric(a.get("paramValue"))]
    p_values = [a for a in analyses if "parsed_p_value" in a]
    ae = _obj(results.get("adverseEventsModule"))
    safety, serious = _ae_information(ae), _sae_counts(ae)
    status = _obj(protocol.get("statusModule"))
    completion = {k: status[k] for k in ("overallStatus", "lastKnownStatus", "whyStopped", "primaryCompletionDateStruct", "completionDateStruct", "resultsFirstPostDateStruct", "lastUpdatePostDateStruct") if k in status}
    elapsed_primary = _actual_elapsed(status.get("primaryCompletionDateStruct"), _time(stamp).date())
    elapsed_completion = _actual_elapsed(status.get("completionDateStruct"), _time(stamp).date())
    completion.update(primary_completion_actual_elapsed=elapsed_primary, study_completion_actual_elapsed=elapsed_completion)
    archived_sponsor = _obj(_obj(_obj(archive.get("protocolSection")).get("sponsorCollaboratorsModule"))).get("leadSponsor")
    if checked and _obj(archived_sponsor).get("name") != sponsor.get("name"):
        conflicts.append({"field": "sponsor", "archive": _obj(archived_sponsor).get("name"), "live": sponsor.get("name"),
                          "severity": "REVIEW", "explanation": "Sponsor changed between archive and live registry; acquisition or transfer is not assumed."})
    external = {field: _external(field, _obj(external_evidence), archive_nct, stamp)
                for field in ("fda_regulatory_pathway", "special_designations", "regulatory_submission_evidence", "pdufa_date")}
    product_lookup = _obj(_obj(external_evidence).get("fda_lookup"))
    critical = []
    for field, present in (("nct_identifier", identity_ok), ("sponsor", _named(sponsor.get("name"))),
                           ("drug_or_biological_product", bool(products)), ("indication", bool(indications)),
                           ("trial_phase", any(p in ("PHASE3", "PHASE4") for p in phases)),
                           ("primary_endpoint", bool(registered or outcomes)), ("primary_endpoint_results", bool(quantitative)),
                           ("serious_adverse_events", serious["reported"])):
        if not present:
            critical.append(field)
    uncertainty = []
    if not checked:
        uncertainty.append("A fresh independent ClinicalTrials.gov identity/content check was unavailable.")
    if not p_values:
        uncertainty.append("No valid primary-endpoint p-value was reported; secondary-endpoint statistics are not substituted.")
    if not effect:
        uncertainty.append("No comparative effect estimate was reported for a primary endpoint; descriptive arm values are not a clinical benefit claim.")
    if not serious["positive_denominator_reported"]:
        uncertainty.append("Serious adverse-event population denominator is missing or nonpositive.")
    if status.get("overallStatus") != "COMPLETED":
        uncertainty.append("Current registry study status is not COMPLETED; remaining, stopped or changed trial status requires review.")
    if not elapsed_primary or not elapsed_completion:
        uncertainty.append("An elapsed ACTUAL primary-completion date or study-completion date is missing; planned or future dates are not completion evidence.")
    uncertainty += [field.replace("_", " ") + " is not verified against exact-trial primary regulatory evidence."
                    for field, row in external.items() if row["status"] != "VERIFIED"]
    uncertainty += ["Reported p-values do not establish significance without prespecified alpha, multiplicity and analysis-population review.",
                    "Clinical meaningfulness, protocol/SAP compliance and causal benefit-risk have not been independently adjudicated."]
    gate = checked and "PHASE3" in phases and bool(quantitative) and external["pdufa_date"]["status"] == "VERIFIED"
    critical_conflict = any(row["severity"] == "CRITICAL" for row in conflicts)
    if critical or critical_conflict:
        readiness = "NOT READY"
        reasons = ["Critical evidence is absent or conflicting: " + ", ".join(critical or ["NCT identity mismatch"]) + "."]
    elif (checked and gate and p_values and effect and serious["positive_denominator_reported"]
          and status.get("overallStatus") == "COMPLETED" and not conflicts
          and elapsed_primary and elapsed_completion
          and all(v["status"] == "VERIFIED" for v in external.values())):
        readiness = "READY"
        reasons = ["Registry identity, primary quantitative results, analyses, effect estimate and safety denominator are available, with exact-trial regulatory context supplied for evidence review.",
                   "READY permits intake review only; the existing SCIENCE40 gate and independent adjudication requirements remain separate."]
    else:
        readiness = "RELUCTANT"
        reasons = ["Quantitative primary outcomes and core trial identity/evidence are present, but material external or scientific-context verification remains incomplete."]
    present_fields = {
        "nct_identifier": identity_ok, "sponsor": _named(sponsor.get("name")), "drug_or_biological_product": bool(products),
        "indication": bool(indications), "trial_phase": bool(phases), "primary_endpoint": bool(registered or outcomes),
        "primary_endpoint_results": bool(quantitative), "statistical_significance": bool(p_values), "clinical_effect_size": bool(effect),
        "safety_findings": bool(safety), "serious_adverse_events": serious["reported"], "study_completion_status": bool(status.get("overallStatus")),
        **{k: v["status"] == "VERIFIED" for k, v in external.items()},
        "evidence_completeness": not critical, "conflicting_or_missing_information": not conflicts and not critical,
        "scientific_assessment_eligibility": gate, "source_provenance": checked,
    }
    checklist = [{"field": field, "status": ("VERIFIED_SOURCE_REPORT" if checked else "ARCHIVE_ONLY") if present_fields[field] else "MISSING_OR_INSUFFICIENT",
                  "source_url": "https://clinicaltrials.gov/api/v2/studies/" + str(archive_nct) if checked else "https://clinicaltrials.gov/study/" + str(archive_nct),
                  "assessed_at": stamp,
                  "limitation": "Field presence is not scientific adjudication; see dossier evidence and uncertainty."} for field in CHECKLIST_FIELDS]
    for row in checklist:
        if row["field"] in ("statistical_significance", "clinical_effect_size") and present_fields[row["field"]]:
            row["status"] = "REPORTED_NOT_ADJUDICATED"
        if row["field"] in external:
            row["source_url"] = _obj(external[row["field"]].get("evidence")).get("source_url")
    provenance = [{"source_type": "ARCHIVED_CLINICALTRIALS_GOV", "source_url": "https://clinicaltrials.gov/study/" + str(archive_nct),
                   "stored_payload_sha256": archived_sha256, "status": "ARCHIVE_REVIEWED", "observed_at": stamp}]
    if checked:
        provenance.append({"source_type": "LIVE_CLINICALTRIALS_GOV", "source_url": "https://clinicaltrials.gov/api/v2/studies/" + archive_nct,
                           "status": "FETCHED_IDENTITY_MATCHED", "observed_at": stamp, "document_sha256": live_sha256,
                           "canonical_json_sha256": hashlib.sha256(json.dumps(live, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()})
    else:
        provenance.append({"source_type": "LIVE_CLINICALTRIALS_GOV", "source_url": "https://clinicaltrials.gov/api/v2/studies/" + str(archive_nct),
                           "status": source_status if source_status != "FETCHED" else "UNAVAILABLE", "observed_at": stamp})
    registry_proof = _obj(_obj(external_evidence).get("registry_sourceproof"))
    if registry_proof:
        provenance.append({"source_type": "REGISTRY_FETCH_PROOF", **registry_proof})
    if product_lookup:
        provenance.append({"source_type": "FDA_PRODUCT_LOOKUP", **product_lookup,
                           "limitation": "Product-level FDA records do not establish this trial's indication, pathway, submission, designation, or PDUFA date."})
    return {
        "version": VERSION, "nct_id": archive_nct, "title": identification.get("briefTitle"), "sponsor": sponsor,
        "products": products, "indication": indications, "phase": phases, "readiness": readiness, "reasons": reasons,
        "verified_at": stamp, "last_verified": stamp, "independently_checked": checked,
        "primary_endpoints": registered, "primary_endpoint_results": outcomes,
        "statistical_significance": {"reported_primary_analyses": analyses, "interpretation": "NOT_INFERRED", "valid_p_values_reported": len(p_values)},
        "clinical_effect_size": {"reported_comparative_estimates": effect, "clinical_meaningfulness": "NOT_ADJUDICATED"},
        "safety_findings": safety, "serious_adverse_events": serious, "study_completion_status": completion,
        **external, "regulatory_identifier_candidates": extract_regulatory_identifiers(current),
        "evidence_completeness": {"checklist_fields": len(CHECKLIST_FIELDS), "critical_missing": critical,
                                  "fields_present": sum(present_fields.values()), "fields_missing_or_insufficient": [k for k, v in present_fields.items() if not v]},
        "conflicts": conflicts, "critical_missing": critical, "uncertainty": uncertainty,
        "scientific_assessment_eligibility": {"evidence_review_available": checked and not critical_conflict,
            "existing_science40_gate_satisfied": gate, "science40_execution_authorized": False,
            "reason": "Preparation only; no framework assessments or adjudications are executed by this dossier builder."},
        "checklist": checklist, "provenance": provenance,
        "framework_handoff": {**FRAMEWORK_REFERENCE, "existing_gate_satisfied": gate, "candidate_readiness": readiness},
        "additional_external_evidence_required": bool(not checked or critical or conflicts or not p_values or not effect
                                                     or not serious["positive_denominator_reported"]
                                                     or any(v["status"] != "VERIFIED" for v in external.values())),
        "fda_product_lookup": product_lookup or {"status": "NOT_ATTEMPTED"},
        "full_scientific_investigations_completed": 0, "trade_authorized": False,
        "approval_probability": None, "regulatory_outcome_prediction": None,
    }

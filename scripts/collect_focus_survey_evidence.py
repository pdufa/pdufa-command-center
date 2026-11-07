#!/usr/bin/env python3
"""Collect exact-NCT public research leads for the live FOCUS survey universe.

No numeric survey grades, FDA approval claims or modelled financial forecasts.
'Processed' means that all 38 question slots were evaluated, NOT verified.
Each source capture is unreviewed until an independently reviewed research fact
is joined using exact NCT + issuer + drug + indication.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
CATALOG = ROOT / "data/phase3_benefit_survey_catalog.json"
REVIEWED = ROOT / "new-platform/frontend/data/benefit-assessment-research.json"
OUTPUT = ROOT / "reports/focus-survey"
PACKETS = OUTPUT / "source-packets"
NCT = re.compile(r"NCT[0-9]{8}\Z")
USER_AGENT = "PDUFA-Command-Center-source-research/1.0"
HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json"}
STATUSES = ("VERIFIED", "SOURCE_CAPTURED_NEEDS_REVIEW", "MODELED", "MISSING",
            "NOT_APPLICABLE", "SOURCE_UNAVAILABLE", "IDENTITY_REVIEW_REQUIRED")

# These are registry source pointers, not equivalence claims or survey grades.
# Each rule must have a concrete corresponding registry observation to be a lead.
SOURCE_RULES = {
    "bestSubgroup": "subgroupOutcomes",
    "clinicalBenefit": "reportedOutcomeMeasures",
    "magnitude": "reportedOutcomeMeasures",
    "meaningfulBenefit": "reportedOutcomeMeasures",
    "durability": "durabilityMeasures",
    "responseRemission": "responseMeasures",
    "timeToResponse": "timeToResponseMeasures",
    "survivalBenefit": "survivalMeasures",
    "qualityOfLife": "qualityOfLifeMeasures",
    "headToHead": "activeComparatorResults",
    "convenience": "treatmentArms",
    "treatmentSequence": "treatmentArms",
    "safetyAdvantage": "adverseEventGroups",
    "seriousAes": "seriousEventGroups",
    "discontinuation": "reportedWithdrawals",
}

def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_suffix(path.suffix + ".tmp")
    staged.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    staged.replace(path)

def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                      separators=(",", ":")).encode("utf-8")).hexdigest()

def text(value, limit=600):
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return ""
    return " ".join(str(value).split())[:limit]

def dict_of(value):
    return value if isinstance(value, dict) else {}

def array_of(value):
    return value if isinstance(value, list) else []

def validate_inputs(roster, catalog):
    if roster.get("schemaVersion") != 1 or catalog.get("schemaVersion") != 1:
        raise ValueError("INVALID_FOCUS_INPUT_SCHEMA")
    records = roster.get("records")
    groups = catalog.get("assessments")
    if not isinstance(records, list) or not records or len(records) > 1000:
        raise ValueError("FOCUS_ROSTER_UNAVAILABLE")
    if not isinstance(groups, list) or len(groups) != 20 or \
       [g.get("rank") for g in groups] != list(range(1, 21)):
        raise ValueError("CANONICAL_20_SURVEYS_CHANGED")
    all_ingredients = []
    for group in groups:
        for ingredient in group.get("ingredients", []):
            if not ingredient.get("id") or not ingredient.get("evidenceRequirement"):
                raise ValueError("INVALID_INGREDIENT_DEFINITION")
            all_ingredients.append(ingredient["id"])
    if len(all_ingredients) != 38 or len(set(all_ingredients)) != 38:
        raise ValueError("CANONICAL_38_INGREDIENTS_CHANGED")
    seen = set()
    for row in records:
        nct, ticker = row.get("nct"), row.get("ticker")
        if not isinstance(nct, str) or not NCT.fullmatch(nct) or nct in seen or \
           not isinstance(ticker, str) or not ticker.strip() or not row.get("company"):
            raise ValueError("DUPLICATE_OR_INVALID_FOCUS_NCT")
        seen.add(nct)
    return records, groups

def request_json(url, retries=3, maximum=4_000_000):
    last_error = None
    for attempt in range(retries):
        try:
            with urlopen(Request(url, headers=HEADERS), timeout=25) as resp:
                data = resp.read(maximum + 1)
                if len(data) > maximum:
                    raise ValueError("PUBLIC_SOURCE_TOO_LARGE")
                return json.loads(data)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            last_error = type(exc).__name__ + ": " + text(str(exc), 120)
            if isinstance(exc, HTTPError) and exc.code in (400, 401, 403, 404):
                break
            if attempt + 1 < retries:
                time.sleep(1.1 * (2 ** attempt))
    raise RuntimeError(last_error or "UNKNOWN_SOURCE_ERROR")

def extract_registry(raw, expected_nct):
    protocol = dict_of(dict_of(raw).get("protocolSection"))
    identity = dict_of(protocol.get("identificationModule"))
    if identity.get("nctId") != expected_nct:
        raise ValueError("REGISTRY_NCT_IDENTITY_MISMATCH")
    design = dict_of(protocol.get("designModule"))
    arms = dict_of(protocol.get("armsInterventionsModule"))
    outcomes = dict_of(protocol.get("outcomesModule"))
    status = dict_of(protocol.get("statusModule"))
    results = dict_of(dict_of(raw).get("resultsSection"))
    result_measures = array_of(dict_of(results.get("outcomeMeasuresModule")).get("outcomeMeasures"))
    event_module = dict_of(results.get("adverseEventsModule"))
    flow_module = dict_of(results.get("participantFlowModule"))
    interventions = []
    for item in array_of(arms.get("interventions")):
        intervention = dict_of(item)
        interventions.append({"name": text(intervention.get("name"), 120),
                              "type": text(intervention.get("type"), 60)})
    registered_arms = []
    for item in array_of(arms.get("armGroups")):
        arm = dict_of(item)
        registered_arms.append({
            "label": text(arm.get("label"), 100),
            "type": text(arm.get("type"), 60),
            "description": text(arm.get("description"), 500),
            "interventionNames": [text(x, 120) for x in array_of(arm.get("interventionNames"))]
        })
    reported = []
    for measure in result_measures[:60]:
        item = dict_of(measure)
        measurements = []
        for cls in array_of(item.get("classes")):
            for category in array_of(dict_of(cls).get("categories")):
                for measurement in array_of(dict_of(category).get("measurements")):
                    m = dict_of(measurement)
                    if text(m.get("value")):
                        measurements.append({
                            "groupId": text(m.get("groupId"), 80),
                            "value": text(m.get("value"), 90),
                            "spread": text(m.get("spread"), 90)
                        })
        if measurements:
            reported.append({"title": text(item.get("title"), 240),
                             "description": text(item.get("description"), 500),
                             "unit": text(item.get("unitOfMeasure"), 70),
                             "timeFrame": text(item.get("timeFrame"), 130),
                             "groups": [{"id": text(x.get("id")), "title": text(x.get("title"))}
                                        for x in array_of(item.get("groups")) if isinstance(x, dict)],
                             "measurements": measurements[:60]})
    ae_groups = []
    serious_groups = []
    for group in array_of(event_module.get("eventGroups")):
        g = dict_of(group)
        recorded = {"title": text(g.get("title"), 100),
                    "id": text(g.get("id"), 80),
                    "seriousAffected": g.get("seriousNumAffected"),
                    "seriousAtRisk": g.get("seriousNumAtRisk"),
                    "otherAffected": g.get("otherNumAffected"),
                    "otherAtRisk": g.get("otherNumAtRisk")}
        if recorded["title"] or recorded["id"]:
            ae_groups.append(recorded)
        if recorded["seriousAffected"] is not None and recorded["seriousAtRisk"] is not None:
            serious_groups.append(recorded)
    withdrawals = []
    for period in array_of(flow_module.get("periods")):
        for milestone in array_of(dict_of(period).get("milestones")):
            m = dict_of(milestone)
            for achievement in array_of(m.get("achievements")):
                a = dict_of(achievement)
                if re.search(r"withdraw|discontinu|drop.?out", text(m.get("title")), re.I):
                    withdrawals.append({"milestone": text(m.get("title"), 100),
                                        "groupId": text(a.get("groupId"), 70),
                                        "count": text(a.get("numSubjects"), 40)})
    titles = [text(x.get("measure"), 200) for x in array_of(outcomes.get("primaryOutcomes"))
              if isinstance(x, dict)]
    titles += [text(x.get("measure"), 200) for x in array_of(outcomes.get("secondaryOutcomes"))
               if isinstance(x, dict)]
    all_outcome_text = lambda pattern: [
        measure for measure in reported
        if re.search(pattern, measure["title"] + " " + measure["description"], re.I)
    ]
    active_comparator = any(re.search(r"ACTIVE_COMPARATOR", arm["type"]) for arm in registered_arms)
    eligibility = dict_of(protocol.get("eligibilityModule"))
    d = {
        "title": text(identity.get("officialTitle") or identity.get("briefTitle"), 400),
        "leadSponsor": text(dict_of(dict_of(protocol.get("sponsorCollaboratorsModule")).get("leadSponsor")).get("name"), 200),
        "indications": [text(x, 130) for x in array_of(dict_of(protocol.get("conditionsModule")).get("conditions"))][:15],
        "interventions": interventions[:25],
        "treatmentArms": registered_arms[:25],
        "enrollment": dict_of(design.get("enrollmentInfo")),
        "eligibilityCriteria": text(eligibility.get("eligibilityCriteria"), 1500),
        "outcomeDefinitions": titles[:30],
        "reportedOutcomeMeasures": reported[:40],
        "adverseEventGroups": ae_groups[:25],
        "seriousEventGroups": serious_groups[:25],
        "reportedWithdrawals": withdrawals[:40],
        "subgroupOutcomes": all_outcome_text(r"subgroup|stratif|biomarker")[:10],
        "durabilityMeasures": all_outcome_text(r"durabil|sustain|follow.?up|long.?term")[:10],
        "responseMeasures": all_outcome_text(r"response|remission|responder")[:12],
        "timeToResponseMeasures": all_outcome_text(r"time to response")[:10],
        "survivalMeasures": all_outcome_text(r"surviv|mortality|overall survival|progression.?free")[:12],
        "qualityOfLifeMeasures": all_outcome_text(r"quality.?of.?life|patient.?reported|PROMIS|SF-36|EQ-5D")[:12],
        "activeComparatorResults": reported[:12] if active_comparator else [],
        "milestones": {k: dict_of(status.get(k)) for k in
                       ("startDateStruct", "primaryCompletionDateStruct", "completionDateStruct",
                        "resultsFirstPostDateStruct")},
        "registryStatus": text(status.get("overallStatus"), 60),
        "whyStopped": text(status.get("whyStopped"), 300),
        "sourceUpdated": text(dict_of(status.get("studyFirstSubmitDateStruct")).get("date") or
                              dict_of(status.get("lastUpdatePostDateStruct")).get("date"), 40),
    }
    return d

def fetch_literature(nct):
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urlencode({
        "query": '"' + nct + '"', "format": "json", "resultType": "core", "pageSize": 25
    })
    raw = request_json(url, retries=2)
    entries = []
    for item in array_of(dict_of(raw.get("resultList")).get("result"))[:25]:
        d = dict_of(item)
        abstract = text(d.get("abstractText"), 1200)
        title = text(d.get("title"), 300)
        published = text(d.get("firstPublicationDate"), 30)
        source = text(d.get("source"), 20)
        item_id = text(d.get("id"), 90)
        entries.append({
            "title": title, "doi": text(d.get("doi"), 120), "publicationDate": published,
            "exactNctInAbstract": nct in abstract, "exactNctInTitle": nct in title,
            "isOpenAccess": d.get("isOpenAccess") == "Y",
            "url": "https://europepmc.org/article/" + quote(source) + "/" + quote(item_id)
                     if source and item_id else url
        })
    return entries

def packet_for_trial(row):
    nct = row["nct"]
    packet = {"nctId": nct, "ticker": row["ticker"], "company": row["company"],
              "retrievedAt": utcnow(), "registryUrl": "https://clinicaltrials.gov/study/" + nct,
              "regulatorySourceLead": row.get("regulatoryUrl"),
              "reportedFdaStatus": row.get("fdaStatus"), "registry": None,
              "literatureLeads": [], "sourceErrors": {}}
    try:
        raw = request_json("https://clinicaltrials.gov/api/v2/studies/" + nct)
        packet["registry"] = extract_registry(raw, nct)
        packet["registrySourceHash"] = fingerprint(raw)
    except Exception as exc:
        packet["sourceErrors"]["registry"] = text(str(exc), 150)
    try:
        packet["literatureLeads"] = fetch_literature(nct)
    except Exception as exc:
        packet["sourceErrors"]["literature"] = text(str(exc), 150)
    packet["packetHash"] = fingerprint({k: v for k, v in packet.items() if k not in ("retrievedAt", "packetHash")})
    return packet

def load_reviewed():
    try:
        feed = load(REVIEWED)
        if feed.get("schemaVersion") != 1 or not isinstance(feed.get("records"), list):
            return {}
        by_nct = {}
        for r in feed["records"]:
            if not isinstance(r, dict) or not NCT.fullmatch(str(r.get("nctId", ""))):
                continue
            by_nct.setdefault(r["nctId"], []).append(r)
        return by_nct
    except (OSError, ValueError, TypeError):
        return {}

def reviewed_fact(record, row, packet, ingredient):
    """Only explicit existing reviewed records may be VERIFIED or MODELED.
    Registry auto-capture never promotes itself into an accepted answer.
    """
    registry = dict_of(packet.get("registry"))
    interventions = [x["name"].lower() for x in registry.get("interventions", []) if x.get("name")]
    indications = [x.lower() for x in registry.get("indications", [])]
    if not registry or len(record) != 1:
        return None
    r = record[0]
    if str(r.get("ticker", "")).upper() != row["ticker"].upper():
        return None
    drug = str(r.get("drug", "")).strip().lower()
    indication = str(r.get("indication", "")).strip().lower()
    # Require exact registered drug identity; an anchored registered formulation
    # suffix can be omitted from the display name (Aficamten (CK-...) -> Aficamten).
    # Do not use substring/ticker-only matching.
    drug_match = any(drug == name or name.startswith(drug + " (") for name in interventions)
    if not drug or not indication or not drug_match or indication not in indications:
        return None
    candidate = dict_of(r.get("facts")).get(ingredient)
    if not isinstance(candidate, dict) or candidate.get("status") not in ("VERIFIED", "MODELED"):
        return None
    if not candidate.get("sourceUrl") or not candidate.get("sourceDate") or not candidate.get("method"):
        return None
    witness = candidate.get("sourceWitness")
    if witness is not None:
        if not isinstance(witness, dict) or not witness.get("registrySourceHash") or \
           witness.get("registrySourceHash") != packet.get("registrySourceHash"):
            return None
        # Source hash ties a human-reviewed comparison to the exact registry
        # snapshot. A subsequent source revision sends it back for review.
        if witness.get("endpointTitle") not in [o.get("title") for o in registry.get("reportedOutcomeMeasures", [])]:
            return None
    return candidate

def build_slots(records, groups, packets, reviewed):
    slots = []
    for row in records:
        nct = row["nct"]
        packet = packets[nct]
        registry = dict_of(packet.get("registry"))
        candidate_reviews = reviewed.get(nct, [])
        for group in groups:
            for ingredient in group["ingredients"]:
                fid = ingredient["id"]
                source = SOURCE_RULES.get(fid)
                value = registry.get(source) if source else None
                leads = []
                if isinstance(value, list) and value:
                    leads.append({
                        "kind": "REGISTRY_UNREVIEWED",
                        "url": packet["registryUrl"],
                        "pointer": "registry." + source,
                        "count": len(value),
                        "sourceHash": packet.get("registrySourceHash"),
                        "date": packet["retrievedAt"][:10]
                    })
                reviewed_value = reviewed_fact(candidate_reviews, row, packet, fid)
                status = (reviewed_value["status"] if reviewed_value else
                          "SOURCE_CAPTURED_NEEDS_REVIEW" if leads else
                          "SOURCE_UNAVAILABLE" if source and not registry else
                          "MISSING")
                slots.append({
                    "nctId": nct, "ticker": row["ticker"], "company": row["company"],
                    "surveyNumber": group["rank"], "surveyName": group["name"],
                    "ingredientId": fid, "ingredientName": ingredient["label"],
                    "evidenceRequirement": ingredient["evidenceRequirement"],
                    "status": status, "reviewedValue": reviewed_value["value"] if reviewed_value else None,
                    "reviewedSourceUrl": reviewed_value.get("sourceUrl") if reviewed_value else None,
                    "reviewedSourceDate": reviewed_value.get("sourceDate") if reviewed_value else None,
                    "registryLeads": leads,
                    "publicationLeads": len(packet["literatureLeads"]),
                    "reason": None if reviewed_value else
                              "Source lead needs clinical review" if leads else
                              "Registry source unavailable" if source and not registry else
                              "No source-validated ingredient answer",
                })
    expected = len(records) * 38
    if len(slots) != expected or len({(s["nctId"], s["ingredientId"]) for s in slots}) != expected:
        raise ValueError("FOCUS_SURVEY_SLOT_IDENTITY_FAILURE")
    return slots

def coverage(slots, records, packets):
    by_status = {s: sum(row["status"] == s for row in slots) for s in STATUSES}
    by_survey = []
    for number in range(1, 21):
        selected = [s for s in slots if s["surveyNumber"] == number]
        by_survey.append({
            "surveyNumber": number,
            "name": selected[0]["surveyName"],
            "slots": len(selected),
            "verified": sum(s["status"] == "VERIFIED" for s in selected),
            "capturedNeedsReview": sum(s["status"] == "SOURCE_CAPTURED_NEEDS_REVIEW" for s in selected),
            "missing": sum(s["status"] in ("MISSING", "SOURCE_UNAVAILABLE",
                                          "IDENTITY_REVIEW_REQUIRED") for s in selected),
        })
    by_trial = []
    for row in records:
        selected = [s for s in slots if s["nctId"] == row["nct"]]
        by_trial.append({
            "nctId": row["nct"], "ticker": row["ticker"],
            "verified": sum(s["status"] == "VERIFIED" for s in selected),
            "capturedNeedsReview": sum(s["status"] == "SOURCE_CAPTURED_NEEDS_REVIEW" for s in selected),
            "missing": sum(s["status"] in ("MISSING", "SOURCE_UNAVAILABLE",
                                          "IDENTITY_REVIEW_REQUIRED") for s in selected),
            "registryRetrieved": bool(packets[row["nct"]].get("registry")),
            "literatureLeads": len(packets[row["nct"]]["literatureLeads"]),
        })
    total = len(slots)
    return {
        "schemaVersion": 1, "generatedAt": utcnow(), "focusTrials": len(records),
        "surveyCategories": 20, "surveyIngredients": 38, "ingredientSlots": total,
        "sourceRegistryTrials": sum(bool(p.get("registry")) for p in packets.values()),
        "literatureLeads": sum(len(p["literatureLeads"]) for p in packets.values()),
        "statuses": by_status,
        "verifiedPercent": round(100 * by_status["VERIFIED"] / total, 2),
        "leadCapturePercent": round(100 * by_status["SOURCE_CAPTURED_NEEDS_REVIEW"] / total, 2),
        "bySurvey": by_survey, "byTrial": by_trial,
        "warning": "Registry and literature leads are not reviewed ingredient findings. "
                   "38 slots per trial does not mean 38 verified assessments.",
    }

def write_csv(path, headers, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

def save_reports(records, slots, packets, report):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for nct, packet in packets.items():
        atomic_json(PACKETS / (nct + ".json"), packet)
    atomic_json(OUTPUT / "evidence.json", {"schemaVersion": 1,
         "rosterSource": str(ROSTER.relative_to(ROOT)), "slots": slots})
    atomic_json(OUTPUT / "coverage.json", report)
    headers = ["nctId", "ticker", "company", "surveyNumber", "surveyName", "ingredientId",
               "ingredientName", "status", "reviewedValue", "reviewedSourceUrl",
               "reviewedSourceDate", "publicationLeads", "reason", "registryLeadUrl",
               "registryLeadPointer", "registryLeadCount"]
    flat = []
    for slot in slots:
        row = {key: slot.get(key) for key in headers}
        lead = slot["registryLeads"][0] if slot["registryLeads"] else {}
        row.update({"registryLeadUrl": lead.get("url"), "registryLeadPointer": lead.get("pointer"),
                    "registryLeadCount": lead.get("count", 0)})
        flat.append(row)
    write_csv(OUTPUT / "evidence.csv", headers, flat)
    write_csv(OUTPUT / "coverage.csv",
              ["surveyNumber", "name", "slots", "verified", "capturedNeedsReview", "missing"],
              report["bySurvey"])
    write_csv(OUTPUT / "missing-evidence.csv", headers,
              [r for r in flat if r["status"] not in ("VERIFIED", "NOT_APPLICABLE")])
    return flat

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--nct")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--write-sheets", action="store_true")
    args = parser.parse_args(argv)
    records, groups = validate_inputs(load(ROSTER), load(CATALOG))
    if args.nct:
        if not NCT.fullmatch(args.nct):
            parser.error("Invalid NCT ID")
        records = [r for r in records if r["nct"] == args.nct]
        if not records:
            parser.error("NCT not present in current FOCUS roster")
        if args.write_sheets:
            parser.error("Use --all before writing FOCUS survey research tabs")
    if args.report:
        output = OUTPUT / "coverage.json"
        print(output.read_text(encoding="utf-8") if output.exists() else
              json.dumps({"status": "NO_SAVED_REPORT"}))
        return 0
    if not args.all and not args.nct and not args.dry_run:
        parser.error("Specify --all, --nct, --dry-run or --report")
    if args.dry_run:
        print(json.dumps({"dryRun": True, "trials": len(records),
                          "surveys": len(groups), "ingredientSlots": len(records) * 38}))
        return 0
    PACKETS.mkdir(parents=True, exist_ok=True)
    packets = {}
    to_fetch = []
    for row in records:
        path = PACKETS / (row["nct"] + ".json")
        if args.resume and path.exists():
            try:
                previous = load(path)
                if previous.get("nctId") == row["nct"] and previous.get("ticker") == row["ticker"] \
                   and previous.get("packetHash"):
                    packets[row["nct"]] = previous
                    continue
            except (OSError, ValueError):
                pass
        to_fetch.append(row)
    with ThreadPoolExecutor(max_workers=3) as pool:
        future_map = {pool.submit(packet_for_trial, row): row for row in to_fetch}
        for future in as_completed(future_map):
            row = future_map[future]
            packet = future.result()
            packets[row["nct"]] = packet
            atomic_json(PACKETS / (row["nct"] + ".json"), packet)
            print("Captured", row["nct"], "registry=", bool(packet["registry"]),
                  "literature=", len(packet["literatureLeads"]), flush=True)
    slots = build_slots(records, groups, packets, load_reviewed())
    report = coverage(slots, records, packets)
    if args.nct:
        if args.write_sheets:
            parser.error("Single-trial pilot must not overwrite full FOCUS survey tabs")
        atomic_json(OUTPUT / "pilot" / (args.nct + ".json"),
                    {"packet": packets[args.nct], "slots": slots, "coverage": report})
        print(json.dumps({"pilot": args.nct, "slots": len(slots),
                          "registryFetched": bool(packets[args.nct]["registry"])}))
        return 0
    # History is append-only by content fingerprint, not by run timestamp.
    history_path = OUTPUT / "source-history.json"
    try:
        history = load(history_path) if history_path.exists() else {"schemaVersion": 1, "changes": []}
        if history.get("schemaVersion") != 1 or not isinstance(history.get("changes"), list):
            raise ValueError("SOURCE_HISTORY_INVALID")
        for nct, packet in packets.items():
            if not any(x.get("nctId") == nct and x.get("packetHash") == packet["packetHash"]
                       for x in history["changes"]):
                history["changes"].append({"nctId": nct, "ticker": packet["ticker"],
                  "packetHash": packet["packetHash"], "registrySourceHash": packet.get("registrySourceHash"),
                  "retrievedAt": packet["retrievedAt"], "registryCaptured": bool(packet["registry"]),
                  "literatureLeads": len(packet["literatureLeads"])})
        atomic_json(history_path, history)
    except (OSError, ValueError, TypeError) as exc:
        raise RuntimeError("Source history could not be safely reconciled: " + str(exc)) from exc
    flat = save_reports(records, slots, packets, report)
    if args.write_sheets:
        from sync_focus_survey_evidence_to_sheets import sync
        try:
            sync(flat, report)
            report["googleSheetsSync"] = "SUCCESS"
        except Exception as exc:
            report["googleSheetsSync"] = "BLOCKED"
            report["googleSheetsError"] = text(str(exc), 250)
        atomic_json(OUTPUT / "coverage.json", report)
    print(json.dumps({key: report[key] for key in
                      ("focusTrials", "ingredientSlots", "sourceRegistryTrials",
                       "literatureLeads", "statuses", "verifiedPercent", "leadCapturePercent")},
                     sort_keys=True))
    return 0

if __name__ == "__main__":
    sys.exit(main())

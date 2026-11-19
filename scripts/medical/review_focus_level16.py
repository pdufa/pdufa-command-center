#!/usr/bin/env python3
"""Run installed FOCUS evidence contracts against sourced current registry snapshots."""

import argparse
import csv
import gzip
import json
from io import StringIO
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "new-platform/backend"))
from app.assessment_runtime import sha
from app.phase_first_intake import phase_first_intake
from app.scientific_levels_two_to_six import assess_levels_two_to_six

DATA = ROOT / "new-platform/frontend/data"
REVIEWER = "Codex current-source evidence review"
VERSION = "focus-current-level16-v1"
PUBLICATIONS = {
    "NCT04576949": (
        "2023-07-11", "https://jamanetwork.com/journals/jama/fullarticle/2807079",
        "Continuous smoking abstinence: 25.3% vs 4.4% (six weeks), "
        "32.6% vs 7.0% (12 weeks).",
        "Reported odds ratios 8.0 (95% CI 3.9–16.3) and 6.3 (3.7–11.6).",
        "Sixteen cytisinicline recipients stopped treatment because of adverse events.",
        "No serious adverse events were attributed to cytisinicline by trial investigators.",
    ),
    "NCT05206370": (
        "2025-04-21", "https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/2832701",
        "Continuous smoking abstinence: 39/263 vs 16/265 (six weeks), "
        "80/264 vs 25/265 (12 weeks).",
        "Reported odds ratios 2.9 (95% CI 1.5–5.6) and 4.4 (2.6–7.3).",
        None,
        "Four deaths were reported. Investigators did not attribute serious adverse events to treatment.",
    ),
}


REGULATORY_LEADS = {
    "NCT05031780": (
        "2026-05-12",
        "https://investor.agios.com/news-releases/news-release-details/agios-submits-snda-fda-us-accelerated-approval-mitapivat-sickle",
        "Sponsor links RISE UP to a sickle-cell sNDA submission. Exact FDA submission number is unverified.",
    ),
    "NCT06553768": (
        "2026-10-12",
        "https://ir.mirumpharma.com/news/news-details/2026/Mirum-Pharmaceuticals-Announces-Primary-Endpoint-Met-in-Phase-3-EXPAND-Study-of-LIVMARLI-maralixibat-in-Ultra-Rare-Cholestatic-Liver-Diseases/default.aspx",
        "Sponsor plans an EXPAND sNDA in the first half of 2027. This is a filing plan.",
    ),
    "NCT06747468": (
        "2026-11-14",
        "https://investors.amylyx.com/news-releases/news-release-details/amylyx-pharmaceuticals-presents-results-phase-3-lucidity",
        "Sponsor describes a planned year-end NDA for LUCIDITY. Exact application and submission IDs remain unverified.",
    ),
}


def read(path):
    if path.suffix == ".gz":
        with gzip.open(path, mode="rt", encoding="utf-8") as file:
            return json.load(file)
    return json.loads(path.read_text(encoding="utf-8"))


def joined(values):
    return "; ".join(str(value) for value in values if value not in (None, ""))


def review_trial(trial, receipt):
    nct = trial["nct"]
    source_url = f"https://clinicaltrials.gov/api/v2/studies/{nct}"
    doc = json.loads(receipt["document_json"])
    p, results = doc["protocolSection"], doc["resultsSection"]
    status = p["statusModule"]
    captured = datetime.fromisoformat(receipt["captured_at"])
    checked = captured.date().isoformat()
    published = receipt["published_at"]
    if not (p["identificationModule"]["nctId"] == nct == receipt["nct_id"]
            and receipt["source_url"] == source_url
            and published == status["lastUpdatePostDateStruct"]["date"] <= checked
            and sha(doc) == receipt["input_sha256"]):
        raise ValueError(f"{nct}: registry identity, version or digest mismatch")
    design = p["designModule"]
    endpoints = p["outcomesModule"].get("primaryOutcomes", [])
    level_one = phase_first_intake({
        "nct_id": nct, "last_update_posted": {"date": published},
        "phases": design.get("phases"), "status": status["overallStatus"],
        "study_design": design, "primary_outcomes": endpoints,
    }, cutoff=checked, registry_checked=receipt["captured_at"])
    criteria = {}

    def add(level, key, observation, limit, *, url=source_url, day=published, document_type="REGISTRY_RECORD"):
        if observation:
            criteria[f"{level}.{key}"] = {
                "source": url, "documentType": document_type,
                "nctId": nct, "sourceDate": day, "sourceRetrievedAt": checked,
                "reviewedAt": checked, "sourceVerifiedAt": checked, "sourceVerifiedBy": REVIEWER,
                "sourceVerified": True, "reviewerId": REVIEWER,
                "sourceVerificationMethod": "REGISTRY_RECORD_REVIEW" if document_type == "REGISTRY_RECORD" else "DIRECT_DOCUMENT_REVIEW",
                "evidenceExcerpt": observation, "rationale": limit, "judgment": "INCONCLUSIVE",
            }

    design_info = design.get("designInfo", {})
    arms = p["armsInterventionsModule"].get("armGroups", [])
    control = joined(arm.get("type") for arm in arms)
    allocation = design_info.get("allocation")
    if allocation or control:
        add(2, "randomizationAndControl", f"Registered allocation {allocation or 'unreported'}. "
            f"Arm types {control or 'unreported'}.", "Verify allocation concealment and conduct against original protocol.")
    masking = design_info.get("maskingInfo", {}).get("masking")
    if masking:
        add(2, "blindingAndBias", f"Registered masking {masking}.",
            "Verify blinding implementation and endpoint ascertainment in the original study documents.")
    conditions = p["conditionsModule"].get("conditions", [])
    population = p["eligibilityModule"]
    details = joined(population.get(key) for key in ("minimumAge", "maximumAge", "sex"))
    if details and population.get("eligibilityCriteria"):
        add(2, "populationAndEligibility", f"Registered age and sex fields: {details}.",
            "Eligibility scope was checked in the registry. Verify amendments, analyzed population and enrollment deviations.")
    primary_results = [
        row for row in results.get("outcomeMeasuresModule", {}).get("outcomeMeasures", [])
        if row.get("type") == "PRIMARY"
    ]
    if primary_results:
        add(3, "primaryEndpointResults", joined(row.get("title") for row in primary_results),
            "The registry posts these primary results. Check group definitions, applicable analysis populations and adverse outcomes before interpreting them.")
    adverse = results.get("adverseEventsModule", {})
    groups = adverse.get("eventGroups", [])
    for key, prefix in (("adverseEvents", "other"), ("seriousAdverseEvents", "serious")):
        observations = [
            f"{group.get('title', group.get('id'))}: {group[prefix+'NumAffected']}/{group[prefix+'NumAtRisk']}"
            for group in groups if type(group.get(prefix+"NumAffected")) is int
            and type(group.get(prefix+"NumAtRisk")) is int
            and 0 <= group[prefix+"NumAffected"] <= group[prefix+"NumAtRisk"]
            and group[prefix+"NumAtRisk"] > 0
        ]
        if observations:
            add(4, key, joined(observations), (
                "Counts are descriptive. Check reporting threshold, attribution and exposure."
                if prefix == "other" else
                "Counts are descriptive. Check attribution, events of special interest and exposure."
            ))
    if groups and adverse.get("timeFrame"):
        add(4, "exposureAndFollowup", f"Safety reporting window: {adverse['timeFrame']}",
            "This is the registry reporting period. Verify realized exposure, attrition and censoring.")
    if conditions:
        add(5, "indicationDefinition", f"Registered conditions: {joined(conditions)}.",
            "Check the exact intended label population, relevant comparator and clinically meaningful thresholds.")
    if nct in PUBLICATIONS:
        day, url, primary, effect, discontinuations, serious = PUBLICATIONS[nct]
        for level, key, fact, limit in (
            (3, "primaryEndpointResults", primary, "Article primary results; reconcile the exact estimand and missing-data populations with the SAP."),
            (3, "effectSizeAndPrecision", effect, "Article contrasts; do not pool across ORCA studies or infer FDA direction."),
            (4, "discontinuations", discontinuations, "Check between-arm attrition and reasons using the complete safety dataset."),
            (4, "seriousAdverseEvents", serious, "Article-reported attribution does not establish comparative benefit-risk."),
        ):
            add(level, key, fact, limit, url=url, day=day, document_type="JOURNAL_ARTICLE")

    if nct == "NCT06747468":
        day, url, _ = REGULATORY_LEADS[nct]
        add(3, "primaryEndpointResults",
            "Sponsor-reported prespecified primary composite rate 0.55 vs 1.24 per week (p=0.0000034).",
            "Verify analysis populations, estimand, multiplicity and details in the full report and SAP.",
            url=url, day=day, document_type="SPONSOR_RELEASE")
        add(4, "seriousAdverseEvents",
            "Sponsor reports no deaths or treatment-related serious adverse events over 16 randomized weeks.",
            "Comparative AE counts and exposure details are still needed.",
            url=url, day=day, document_type="SPONSOR_RELEASE")

    reviews = assess_levels_two_to_six(level_one, trial_id=nct, evidence=criteria)
    if any(section["rejectedCriteria"] for section in reviews.values()):
        raise ValueError(f"{nct}: an emitted source review failed the installed contract")
    cycle_ids = trial["provisionalApplicationCycleIds"]
    contradictions = [
        {"field": name, "retained": old, "current": new, "status": "REGISTRY_VERSION_DRIFT"}
        for name, old, new in (
            ("phase", trial["phases"], design.get("phases")),
            ("status", trial["registryStatus"], status["overallStatus"]),
            ("postedVersion", trial["registryVersionDate"], published),
        ) if old != new
    ]
    chronology = {
        "registryUrl": source_url, "registryPostedAt": published, "registryCapturedAt": receipt["captured_at"],
        "registryRawSha256": receipt["raw_sha256"], "registryFilteredSha256": receipt["input_sha256"],
        "retainedRegistrySha256": trial["registryDigest"],
    }
    regulatory_lead = REGULATORY_LEADS.get(nct)
    assessment = {
        "nct": nct, "ticker": trial["ticker"], "company": trial["company"],
        "version": VERSION, "ownerReviewStatus": "OWNER_NOT_REVIEWED",
        "registry": chronology, "registryVersionDifferences": contradictions,
        "retainedApplicationLeads": cycle_ids, "exactFdaCycleVerified": False,
        "regulatoryGap": "Exact trial–indication–application–cycle binding and regulatory/CMC originals need review.",
        "regulatoryLead": dict(zip(
            ("publicationDate", "sourceUrl", "observation"), regulatory_lead
        )) if regulatory_lead else None,
        "findings": [level_one, *reviews.values()],
        "retainedPreliminaryFindings": [{
            "level": level["level"], "contradictions": level["contradictions"],
        } for level in trial["levels"]],
    }
    assessment["assessmentSha256"] = sha(assessment)
    return assessment


def export(receipts, destination):
    package = read(DATA / "level16AssessmentEvidence.json")
    roster = read(DATA / "p3PostDataActive.json")
    trials = {trial["nct"]: trial for trial in package["trials"]}
    roster_ids = [trial["nct"] for trial in roster["records"]]
    if len(roster_ids) != 32 or set(roster_ids) != set(trials) or set(trials) != set(receipts):
        raise ValueError("FOCUS roster, retained artifact and registry snapshots must bind to the same exact 32 trials")
    if len(set(roster_ids)) != 32 or any([row["level"] for row in t["levels"]] != list(range(1, 7)) for t in trials.values()):
        raise ValueError("Expected six retained preliminary records per distinct trial")
    capture_days = {datetime.fromisoformat(row["captured_at"]).date() for row in receipts.values()}
    if len(capture_days) != 1:
        raise ValueError("Expected one UTC capture day per versioned export")
    stamp = capture_days.pop().strftime("%Y%m%d")
    data = [review_trial(trials[nct], receipts[nct]) for nct in roster_ids]
    output = {
        "version": VERSION, "evidenceMode": "CURRENT_SOURCE", "historicalPredictionInputPermitted": False,
        "rosterAsOf": roster["asOf"], "retainedPackageSha256": sha(package), "trials": data,
    }
    stream = StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["nct", "ticker", "level", "status", "scientific_validation", "owner_review",
                     "fda_direction", "finding", "outstanding", "source_urls", "captured_at", "version", "assessment_sha256"])
    for item in data:
        for finding in item["findings"]:
            registry = item["registry"]
            accepted = finding.get("acceptedEvidence", {})
            observation = joined(row["evidenceExcerpt"] for row in accepted.values())
            outstanding = joined(finding.get("reviewReadiness", {}).get("outstanding", []))
            if finding["level"] == 1:
                observation = joined((finding["phase"], finding["trialStatus"],
                                      *(e["measure"] for e in finding["endpointDefinitions"])))
                outstanding = "Registry intake only. Verify original documents and adjudicate endpoint quality."
            regulatory_lead = item["regulatoryLead"] if finding["level"] == 6 else None
            if finding["level"] == 6:
                outstanding = joined((outstanding, item["regulatoryGap"]))
            if regulatory_lead:
                observation = joined((regulatory_lead["publicationDate"], regulatory_lead["observation"]))
            source_urls = {registry["registryUrl"], *(e["source"] for e in accepted.values())}
            if regulatory_lead:
                source_urls.add(regulatory_lead["sourceUrl"])
            writer.writerow([item["nct"], item["ticker"], finding["level"],
                             finding.get("executionStatus") or finding["status"], finding["scientificValidation"],
                             item["ownerReviewStatus"], finding["fdaPrediction"], observation, outstanding,
                             joined(sorted(source_urls)), registry["registryCapturedAt"], VERSION, item["assessmentSha256"]])
    files = {
        destination / f"focus-level16-current-evidence-{stamp}.json":
            json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        destination / f"focus-level16-current-evidence-{stamp}.csv": stream.getvalue(),
    }
    for path, body in files.items():
        if path.exists() and path.read_bytes() != body.encode("utf-8"):
            raise ValueError(f"Refusing to replace prior assessment version: {path}")
    destination.mkdir(parents=True, exist_ok=True)
    for path, body in files.items():
        if not path.exists():
            with path.open("x", encoding="utf-8", newline="") as file:
                file.write(body)
    return output


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--receipts", type=Path, required=True, help="Exact-NCT collect_registry outputs")
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    export(read(args.receipts), args.output)

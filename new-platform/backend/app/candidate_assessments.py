"""Evidence-accountable research scores; missing is never zero or normalized.
Registry statistics are observations, not adjudications of clinical success.
"""
from __future__ import annotations
from datetime import date
import hashlib
import json
import math
import re
from urllib.parse import urlparse

MODEL = "candidate-assessments-v1"
NCT = re.compile(r"^NCT\d{8}$")
DOMAINS = {
    "PIPELINE": [("P1", "Clinical efficacy / effect size", 25), ("P2", "Trial design / endpoint quality", 20),
                 ("P3", "Statistical reliability", 15), ("P4", "Safety / tolerability", 15),
                 ("P5", "Reproducibility / consistency", 10), ("P6", "Regulatory / development feasibility", 10),
                 ("P7", "Competitive clinical differentiation", 5)],
    "GEM_JR": [("J1", "Clinical strength", 20), ("J2", "Next-milestone success", 15),
               ("J3", "Catalyst importance / timing", 20), ("J4", "Cash runway / financing risk", 15),
               ("J5", "Valuation / upside", 15), ("J6", "Competitive / commercial potential", 10),
               ("J7", "Market recognition / liquidity", 5)],
    "GEM": [("G1", "Clinical strength", 25), ("G2", "Next-milestone success", 20),
            ("G3", "Safety / regulatory readiness", 15), ("G4", "Catalyst importance / timing", 15),
            ("G5", "Cash runway / dilution", 10), ("G6", "Valuation / risk-adjusted upside", 10),
            ("G7", "Competitive / commercial potential", 5)],
}

def packed(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)

def day(value):
    try: return date.fromisoformat(str(value or "")[:10])
    except ValueError: return None

def source_url(value):
    try:
        url = urlparse(str(value or ""))
        return bool(url.scheme == "https" and url.hostname and not url.username)
    except ValueError: return False

def nct_id(row):
    explicit = str(row.get("nctId") or "")
    if NCT.fullmatch(explicit): return explicit
    matches = re.findall(r"\bNCT\d{8}\b", str(row.get("id") or ""))
    return matches[0] if len(matches) == 1 else ""

def measure(key, name, maximum, value=None, *, fraction=None, rule="", source="", checked="", source_date="", state=None, note=""):
    available = fraction is not None and source_url(source) and bool(day(checked))
    if available and (not math.isfinite(fraction) or not 0 <= fraction <= 1): raise ValueError("Invalid scoring fraction")
    status = state or ("OBSERVED" if available else "MISSING")
    scored = available and status == "OBSERVED"
    return {"id": key, "label": name, "maximum": maximum, "value": value,
            "points": round(maximum * fraction, 4) if scored else None, "coverage": maximum if scored else 0,
            "status": status, "rule": rule, "source": source, "checkedAt": checked, "sourceDate": source_date, "note": note}

def grade(key, name, maximum, reviews, today, *, max_age=90):
    entry = reviews.get(key, {})
    value = entry.get("grade")
    valid = (isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
             and value in (0, 1, 2, 3, 4) and source_url(entry.get("source"))
             and bool(str(entry.get("rationale") or "").strip()) and entry.get("measurements") is not None)
    checked, evidence_date = day(entry.get("reviewedAt")), day(entry.get("sourceDate"))
    state = "MISSING"
    if entry.get("conflict") is True: state = "CONFLICTING"
    elif valid and checked and evidence_date and evidence_date <= checked <= today:
        state = "STALE" if (today - checked).days > max_age else "OBSERVED"
    return measure(key, name, maximum, {"reviewGrade": value if valid else None, "measurements": entry.get("measurements")}, fraction=value / 4 if state == "OBSERVED" else None,
                   rule="Source-reviewed research grade: 0 adverse/unsupported; 1 weak; 2 mixed; 3 supportive; 4 strong. Points = weight × grade / 4. Exact-program dated measurements and rationale required; review valid " + str(max_age) + " days.",
                   source=entry.get("source", ""), checked=entry.get("reviewedAt", ""), source_date=entry.get("sourceDate", ""), state=state,
                   note=entry.get("rationale", "Source-backed interpretation has not been recorded."))

def domain(identity, name, maximum, metrics):
    if abs(sum(m["maximum"] for m in metrics) - maximum) > .001: raise ValueError("Weights do not reconcile: " + identity)
    observed, coverage = round(sum(m["points"] or 0 for m in metrics), 4), round(sum(m["coverage"] for m in metrics), 4)
    complete = abs(coverage - maximum) < .001
    return {"id": identity, "label": name, "maximum": maximum, "metrics": metrics,
            "score": round(observed, 2) if complete else None, "observedPoints": observed, "coverage": coverage,
            "status": "COMPLETE" if complete else "PARTIAL" if coverage else "MISSING"}

def inherited(categories, maximum, key):
    total = sum(c["maximum"] for c in categories)
    return [{"id": key + "." + c["id"], "label": c["id"] + " · " + c["label"],
             "maximum": maximum * c["maximum"] / total,
             "value": {"observedPoints": c["observedPoints"], "coverage": c["coverage"], "maximum": c["maximum"]},
             "points": maximum * c["observedPoints"] / total if c["coverage"] else None,
             "coverage": maximum * c["coverage"] / total,
             "status": "OBSERVED" if c["status"] == "COMPLETE" else c["status"],
             "rule": "Inherited from " + c["id"] + "; missing clinical points remain missing. No rescaling to an observed denominator.",
             "source": "", "checkedAt": "", "sourceDate": "", "note": "See Pipeline clinical measurements below."} for c in categories]

def score_candidate(row, registry=None, analyses=None, reviews=None, *, today=None, registry_checked=""):
    today = today or date.today()
    registry, analyses, reviews = registry or {}, analyses or [], reviews or {}
    nct = nct_id(row)
    if registry and (not nct or registry.get("nct_id") != nct): raise ValueError("Registry identity mismatch")
    facts, tech = row.get("trialFilters") or {}, row.get("technical") or {}
    checked = registry_checked[:10]
    source = "https://clinicaltrials.gov/study/" + nct if nct and registry and day(checked) and day(checked) <= today else ""
    design = registry.get("study_design") or {}
    info = design.get("designInfo") or {}
    masking, allocation = (info.get("maskingInfo") or {}).get("masking"), info.get("allocation")
    arms, endpoints = registry.get("treatment_groups") or [], registry.get("primary_outcomes") or []
    control = len(arms) >= 2 and any(a.get("type") in {"ACTIVE_COMPARATOR", "PLACEBO_COMPARATOR", "SHAM_COMPARATOR", "NO_INTERVENTION"} for a in arms)
    defined = bool(endpoints and all(e.get("measure") and e.get("timeFrame") for e in endpoints))
    registry_day = (registry.get("last_update_posted") or {}).get("date", "")
    def reg(key, name, maximum, value, fraction, rule):
        return measure(key, name, maximum, value, fraction=fraction, rule=rule, source=source, checked=checked, source_date=registry_day)
    def reviewed(key, name, weight, age=90): return grade(key, name, weight, reviews, today, max_age=age)
    outcome = facts.get("primaryOutcome")
    clinical_date, clinical_check = facts.get("resultsDate", ""), row.get("lastChecked", "")
    fresh = bool(day(clinical_check) and 0 <= (today - day(clinical_check)).days <= 90 and day(clinical_date)
                 and day(clinical_date) <= today and "CONFLICTING" not in facts.get("evidence", []))
    primary = measure("primaryOutcome", "Adjudicated primary endpoint", 10, outcome,
                      fraction=(1 if outcome == "SUCCESS" else 0) if outcome in {"SUCCESS", "FAILED"} and fresh else None,
                      source=row.get("phase3Source", ""), checked=clinical_check, source_date=clinical_date,
                      rule="Exact-trial verified primary outcome: success 10; failure 0. Posted results or a small p-value alone awards no points.")
    status = registry.get("status")
    status_points = 0 if status in {"TERMINATED", "WITHDRAWN", "SUSPENDED"} else 1 if status in {"RECRUITING", "NOT_YET_RECRUITING", "ACTIVE_NOT_RECRUITING", "COMPLETED", "ENROLLING_BY_INVITATION"} else None
    metrics = [
        [primary, reviewed("effectSize", "Effect size versus clinical threshold", 10), reviewed("clinicalRelevance", "Clinical relevance and interval", 5)],
        [reg("randomization", "Random allocation", 6, allocation, 1 if allocation == "RANDOMIZED" else 0 if allocation == "NON_RANDOMIZED" else None,
             "Registry RANDOMIZED: 6; NON_RANDOMIZED: 0; absent/NA: missing. Design heuristic, not a validity finding."),
         reg("control", "Concurrent comparator arm", 5, arms, (1 if control else 0) if arms else None,
             "≥2 arms including registered active/placebo/sham/no-intervention comparator: 5; reported uncontrolled design: 0; absent: missing."),
         reg("masking", "Masking", 4, masking, {"QUADRUPLE": 1, "TRIPLE": 1, "DOUBLE": 1, "SINGLE": .5, "NONE": 0}.get(masking),
             "Double/triple/quadruple: 4; single: 2; none: 0; absent: missing. Clinical suitability requires review."),
         reg("endpointDefinition", "Primary endpoint definition", 5, endpoints, (1 if defined else 0) if endpoints else None,
             "Every registered primary endpoint has a measure and time frame: 5; incomplete definitions: 0; absent: missing. Not proof of prespecification or relevance.")],
        [reviewed("statisticalPlan", "Prespecified analysis / multiplicity", 5), reviewed("precision", "Effect precision / confidence interval", 5), reviewed("missingData", "Power / missing data / sensitivity", 5)],
        [reviewed("seriousSafety", "Comparative serious adverse events", 5), reviewed("tolerability", "Discontinuation / tolerability", 5), reviewed("safetyExposure", "Exposure / safety follow-up", 5)],
        [reviewed("replication", "Independent replication", 6), reviewed("consistency", "Across-study / subgroup consistency", 4)],
        [reg("developmentStatus", "Registered development status", 3, status, status_points,
             "Active/recruiting/completed: 3; terminated/withdrawn/suspended: 0; unknown: missing. Completion does not establish efficacy."), reviewed("regulatoryFeasibility", "Regulatory path / manufacturing feasibility", 7)],
        [reviewed("clinicalDifferentiation", "Comparator differentiation", 3), reviewed("unmetNeed", "Unmet clinical need", 2)],
    ]
    primary_statistics = [{k: a.get(k) for k in ("endpoint", "endpoint_type", "comparison_groups", "p_value", "parameter", "estimate", "confidence_level", "confidence_lower", "confidence_upper", "method")} for a in analyses if a.get("endpoint_type") == "PRIMARY"]
    for item in metrics[0][1:] + metrics[2]:
        item["value"] = {"review": item["value"], "reportedPrimaryStatistics": primary_statistics,
                         "note": "Reported statistics remain observations; clinical interpretation, prespecification, multiplicity and clinical thresholds are not inferred."}
    pipeline = [domain(*spec, points) for spec, points in zip(DOMAINS["PIPELINE"], metrics)]
    def runway(maximum):
        months, gate = tech.get("runwayMonths"), str(tech.get("runwayGate") or "")
        stamp, link = tech.get("runwayAsOf", ""), tech.get("runwaySource", "")
        valid = (isinstance(months, (int, float)) and not isinstance(months, bool) and math.isfinite(months) and months >= 0
                 and day(stamp) and 0 <= (today - day(stamp)).days <= 120
                 and urlparse(link).hostname in {"www.sec.gov", "sec.gov"} and (gate.startswith("PASS") or gate.startswith("FAIL")))
        fraction = (1 if months >= 24 else .75 if months >= 18 else .5 if months >= 12 else .25 if months >= 6 else 0) if valid else None
        return measure("cashRunway", "SEC cash-only runway", maximum, months, fraction=fraction, source=link, checked=stamp, source_date=stamp,
                       rule="Reconciled SEC cash-only runway: ≥24 months full weight; ≥18 75%; ≥12 50%; ≥6 25%; <6 0. Unknown/stale missing. Review ≤120 days.", note=tech.get("runwayReason", "SEC cash and operating burn not reconciled."))
    def liquidity(maximum):
        value, stamp = tech.get("avgDollarVolume20"), tech.get("marketDate", "")
        valid = (tech.get("eodFresh") is True and isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
                 and value >= 0 and day(stamp) and 0 <= (today - day(stamp)).days <= 7)
        return measure("liquidity", "20-session average dollar volume", maximum, value,
                       fraction=(1 if value >= 5e6 else .5 if value >= 1e6 else 0) if valid else None,
                       rule="Fresh 20-session dollar volume: ≥$5M full; ≥$1M half; <$1M zero. Spread/execution capacity require separate review.",
                       source=tech.get("marketSource", ""), checked=stamp, source_date=stamp)
    def catalyst(maximum):
        timing = reviewed("catalystTiming", "Verified catalyst and timing", maximum * .6, 7)
        timing["value"] = {"reviewedMeasurements": timing["value"], "reportedPdufa": row.get("pdufaDate"), "registryPrimaryCompletion": registry.get("primary_completion_date"), "note": "Primary completion is not a public readout date; reported PDUFA dates require verification."}
        return [timing, reviewed("catalystImportance", "Catalyst importance", maximum * .4)]
    def cash(maximum): return [runway(maximum * 2 / 3), reviewed("dilutionRisk", "Financing / dilution risk", maximum / 3, 7)]
    def valuation(maximum):
        item = reviewed("riskAdjustedUpside", "Risk-adjusted upside and downside", maximum, 7)
        item["value"] = {"reviewedMeasurements": item["value"], "marketCap": row.get("marketCap"), "note": "Market cap alone does not establish undervaluation."}
        return [item]
    def commercial(maximum): return [reviewed("commercialPotential", "Addressable opportunity / competition / execution", maximum)]
    junior = [inherited(pipeline, 20, "clinical"), [reviewed("milestoneSuccess", "Next milestone: evidence strength", 15)], catalyst(20), cash(15), valuation(15), commercial(10), [liquidity(2), reviewed("marketRecognition", "Market recognition / sponsorship", 3, 30)]]
    gem = [inherited(pipeline, 25, "clinical"), [reviewed("milestoneSuccess", "Next milestone: evidence strength", 20)], inherited([pipeline[3]], 10, "safety") + inherited([pipeline[5]], 5, "regulatory"), catalyst(15), cash(10), valuation(10), commercial(5)]
    models = {}
    for name, groups in (("PIPELINE", pipeline), ("GEM_JR", [domain(*spec, items) for spec, items in zip(DOMAINS["GEM_JR"], junior)]), ("GEM", [domain(*spec, items) for spec, items in zip(DOMAINS["GEM"], gem)])):
        points, coverage = round(sum(c["observedPoints"] for c in groups), 2), round(sum(c["coverage"] for c in groups), 2)
        models[name] = {"score": points if coverage >= 99.999 else None, "observedPoints": points, "coverage": coverage, "status": "COMPLETE" if coverage >= 99.999 else "PARTIAL" if coverage else "MISSING", "categories": groups}
    flags = []
    if outcome == "FAILED": flags.append("Verified primary endpoint failure")
    if facts.get("safety") == "FLAGGED": flags.append("Unresolved safety flag")
    if facts.get("dilution") == "FLAGGED": flags.append("New dilution flag")
    if "CONFLICTING" in facts.get("evidence", []): flags.append("Conflicting source evidence")
    return {"modelVersion": MODEL, "id": row["id"], "programId": row.get("programId"), "nctId": nct, "asOf": today.isoformat(), "models": models, "riskFlags": flags,
            "qualification": {"savedLists": facts.get("lists", ["PIPELINE"]), "primaryOutcome": outcome, "firstFinancingClosed": facts.get("firstFinancingClosed"), "secondFinancingClosed": facts.get("secondFinancingClosed"), "note": "Scores do not alter screening, saved membership or trade entry. Only complete evidence is ranked. Uncalibrated research scores, not success probabilities."},
            "registryFetchedAt": registry_checked, "registrySourceDate": registry_day, "reportedStatistics": analyses,
            "data": {"candidate": row, "registry": registry},
            "missingEvidence": [c["id"] + ": " + m["label"] for model in models.values() for c in model["categories"] for m in c["metrics"] if m["coverage"] < m["maximum"]]}

def compact(result):
    return {"modelVersion": result["modelVersion"], "models": {name: {**{k: model[k] for k in ("score", "observedPoints", "coverage", "status")}, "categories": [{k: c[k] for k in ("id", "maximum", "score", "observedPoints", "coverage", "status")} for c in model["categories"]]} for name, model in result["models"].items()}, "riskFlags": result["riskFlags"]}

def fingerprint(result):
    stable = {key: result[key] for key in ("modelVersion", "models", "reportedStatistics", "qualification", "registryFetchedAt", "riskFlags")}
    return hashlib.sha256(packed(stable).encode()).hexdigest()

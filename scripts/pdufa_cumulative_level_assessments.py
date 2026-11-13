#!/usr/bin/env python3
"""Phase-first, cumulative PDUFA research scoring across scientific levels 4-20.

No score is manufactured from a FOCUS row, trial-status label, or Level 3
CLINICAL_FIVE comparator. Every numeric rubric score requires a date-bounded
primary-source receipt and criterion-specific, explained human evidence rating.

This is research infrastructure, NOT a validated FDA probability, clinical
advice, scientific acceptance, or publication/deployment authorization.
"""
from __future__ import annotations

import argparse
from datetime import datetime, date, timezone
import json
import math
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "automation/scientific-level-completion-queue.json"
DEFAULT_ROSTER = ROOT / "automation/focus-assessment-roster-snapshot-20261112.json"
NCT = re.compile(r"NCT\d{8}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
PHASES = {"EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4",
          "UNKNOWN_OR_NOT_APPLICABLE"}
APPLICATION_STAGES = {"UNKNOWN", "PRE_APPLICATION", "FILED", "UNDER_REVIEW",
                      "POST_APPROVAL"}
NONPUBLIC_PENDING = {"UNKNOWN", "MISSING", "UNPUBLISHED"}
EVIDENCE_STATES = {"VERIFIED", "NOT_YET_EXPECTED", "NOT_APPLICABLE",
                   "UNKNOWN", "MISSING", "UNPUBLISHED"}
# Level 6 demands genuine application-level assessment dimensions, not just
# pointers to an unreviewed clinical-registry record.
L6_ADDITIONAL_RUBRIC = ("efficacy", "safety", "trial_quality",
                       "benefit_risk", "manufacturing_cmc")
FORBIDDEN_OUTCOME_INPUTS = ("fda_outcome", "actual_outcome", "approval_decision",
                            "final_outcome", "known_pdufa_result")
# Do not demand nonpublic NDA/CMC files from trial-only, early-phase candidates.
EARLY_PHASE_NOT_YET_EXPECTED = {"regulatory_sources", "manufacturing_cmc"}
NONFILED_APPLICATION_NOT_YET_EXPECTED = {"manufacturing_cmc"}
REVIEW_REQUIRED = "INDEPENDENT_SCIENTIFIC_AND_CODE_REVIEW_REQUIRED"


def utc_date(value: object) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Expected ISO UTC date YYYY-MM-DD")
    return date.fromisoformat(value)


def datetime_utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Missing source timestamp")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid source timestamp") from exc
    if result.tzinfo is None or result.utcoffset() != timezone.utc.utcoffset(result):
        raise ValueError("Source timestamp must be UTC with explicit offset")
    return result.astimezone(timezone.utc)


def checked_url(value: object) -> str:
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError("Source URL must be an absolute HTTPS URL")
    parsed = urlparse(value)
    if (parsed.scheme != "https" or not parsed.netloc or parsed.username is not None
            or parsed.password is not None or parsed.fragment):
        raise ValueError("Source URL must be an HTTPS provenance URL without credentials")
    return value


def receipt(value: object, cutoff: date) -> dict:
    """A claimed source receipt is necessary, but never substitutes for review."""
    if not isinstance(value, dict):
        raise ValueError("Missing source receipt")
    url = checked_url(value.get("url"))
    digest = value.get("sha256")
    if not isinstance(digest, str) or SHA.fullmatch(digest) is None:
        raise ValueError("Missing original-source SHA-256 receipt")
    published = utc_date(value.get("published_on"))
    retrieved = datetime_utc(value.get("retrieved_at_utc"))
    if published > cutoff or retrieved.date() > cutoff:
        raise ValueError("Future source/after-cutoff leakage forbidden")
    if published > retrieved.date():
        raise ValueError("Publication cannot postdate source retrieval")
    return {"url": url, "sha256": digest, "published_on": published.isoformat(),
            "retrieved_at_utc": retrieved.isoformat()}


def validated_manifest(manifest: dict) -> list[dict]:
    rows = manifest.get("levels")
    if (not isinstance(rows, list) or len(rows) != 17 or
            [x.get("level") for x in rows] != list(range(4, 21)) or
            any(x.get("completed_scientific_level") is not False for x in rows)):
        raise ValueError("Invalid 4-20 review-gated manifest")
    seen: set[str] = set()
    for row in rows:
        fields = row.get("required_evidence_fields")
        if (not isinstance(fields, list) or not fields or
                any(not isinstance(v, str) or not re.fullmatch(r"[a-z][a-z0-9_]+", v)
                    for v in fields) or len(fields) != len(set(fields))):
            raise ValueError("Invalid assessment evidence criteria")
        for field in fields:
            if field in seen:
                raise ValueError("Criterion repeated at different scientific level")
            seen.add(field)
    return rows


def validated_roster(roster: dict) -> list[dict]:
    items = roster.get("trials")
    if (roster.get("schema_version") != 1 or not isinstance(items, list)
            or not items or len(items) > 250 or
            roster.get("trial_count") != len(items)):
        raise ValueError("Invalid dated FOCUS roster")
    ids = [x.get("nct") for x in items]
    if any(not isinstance(n, str) or not NCT.fullmatch(n) for n in ids):
        raise ValueError("Invalid exact NCT trial identity")
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate NCT trial in FOCUS")
    return items


def criteria_for_level(rows: list[dict], level: int) -> tuple[str, ...]:
    fields: list[str] = []
    for row in rows:
        if row["level"] > level:
            break
        fields.extend(row["required_evidence_fields"])
        if row["level"] == 6:
            fields.extend(L6_ADDITIONAL_RUBRIC)
    return tuple(fields)


def phase_policy(phase: str, application: str, criterion: str) -> str:
    """Only strictly pre-application clinical phases allow 'not yet expected'.

    Unknown status NEVER authorizes not-applicable, not-expected or a low score.
    """
    if (criterion in EARLY_PHASE_NOT_YET_EXPECTED and
            phase in {"EARLY_PHASE1", "PHASE1", "PHASE2"} and
            application == "PRE_APPLICATION"):
        return "NOT_YET_EXPECTED_ALLOWED"
    if (criterion in NONFILED_APPLICATION_NOT_YET_EXPECTED and
            phase in {"PHASE3", "PHASE4"} and
            application == "PRE_APPLICATION"):
        return "NOT_YET_EXPECTED_ALLOWED"
    return "EVIDENCE_REQUIRED_OR_UNKNOWN"


def assessment_for_trial(trial: dict, manifest: list[dict], cutoff: date) -> list[dict]:
    nct = trial.get("nct")
    if not isinstance(nct, str) or NCT.fullmatch(nct) is None:
        raise ValueError("Invalid NCT")
    if any(k in trial for k in FORBIDDEN_OUTCOME_INPUTS):
        raise ValueError("Known final FDA outcome cannot enter blinded research input")
    phase = trial.get("phase")
    application = trial.get("application_stage")
    if phase not in PHASES or application not in APPLICATION_STAGES:
        raise ValueError("Explicit source-derived phase and application stage required")
    phase_source = trial.get("phase_source")
    phase_ready = phase != "UNKNOWN_OR_NOT_APPLICABLE" and phase_source is not None
    if phase_source is not None:
        phase_receipt = receipt(phase_source, cutoff)
        if nct not in phase_receipt["url"] or "clinicaltrials.gov" not in urlparse(
                phase_receipt["url"]).hostname.lower():
            raise ValueError("Trial phase receipt must identify exact NCT in ClinicalTrials.gov")
    # Registry phase alone never proves NDA, BLA, or sNDA filing.
    application_source = trial.get("application_source")
    if application in {"FILED", "UNDER_REVIEW", "POST_APPROVAL"}:
        if application_source is None:
            raise ValueError("Filed/review-stage claim needs an original-source receipt")
        receipt(application_source, cutoff)
    elif application_source is not None:
        receipt(application_source, cutoff)
    evidence = trial.get("evidence", {})
    if not isinstance(evidence, dict):
        raise ValueError("Criterion evidence must be keyed by rubric criterion")
    all_fields = set(criteria_for_level(manifest, 20))
    if set(evidence) - all_fields:
        raise ValueError("Unrecognized criterion: do not mix other levels/outcomes")
    for item in evidence.values():
        if not isinstance(item, dict) or item.get("status") not in EVIDENCE_STATES:
            raise ValueError("Evidence item requires explicit status")
    result: list[dict] = []
    for row in manifest:
        level = row["level"]
        required = criteria_for_level(manifest, level)
        included: list[dict] = []
        gaps: list[dict] = []
        score_inputs: list[float] = []
        for name in required:
            item = evidence.get(name, {"status": "UNKNOWN",
                                      "reason": "No criterion-specific evidence provided"})
            status = item["status"]
            if status == "VERIFIED":
                score = item.get("rubric_score")
                explanation = item.get("reason")
                if (isinstance(score, bool) or not isinstance(score, (int, float))
                        or not math.isfinite(score) or not 0 <= score <= 100
                        or not isinstance(explanation, str) or len(explanation.strip()) < 15):
                    raise ValueError("Verified score needs finite 0-100 score and explanation")
                source = receipt(item.get("source"), cutoff)
                if not phase_ready:
                    gaps.append({"criterion": name, "status": "PHASE_NOT_VERIFIED"})
                    continue
                score_inputs.append(float(score))
                included.append({"criterion": name, "rubric_score": score,
                                 "reason": explanation.strip(), "source": source,
                                 "source_independently_adjudicated": False})
            elif status == "NOT_YET_EXPECTED":
                if phase_policy(phase, application, name) != "NOT_YET_EXPECTED_ALLOWED":
                    raise ValueError("Cannot exempt phase-applicable scientific criterion: "+name)
                gaps.append({"criterion": name, "status": status,
                             "reason": "Exempted only under explicit pre-filing phase policy"})
            elif status == "NOT_APPLICABLE":
                # Human/methodologically supported applicability exceptions must
                # be separately reviewed; none can bypass this version's strict gate.
                raise ValueError("NOT_APPLICABLE needs separate reviewed policy update")
            else:
                reason = item.get("reason")
                if not isinstance(reason, str) or not reason.strip():
                    reason = ("Primary source not yet adjudicated" if status == "UNKNOWN"
                              else "Missing or unpublished source; not scored as failure")
                gaps.append({"criterion": name, "status": status, "reason": reason})
        blockers = [g for g in gaps if g["status"] != "NOT_YET_EXPECTED"]
        score = (round(sum(score_inputs) / len(score_inputs), 1)
                 if phase_ready and not blockers and score_inputs else None)
        status = ("UNVERIFIED_PHASE" if not phase_ready else
                  "PROVISIONAL_RESEARCH_SCORE_REVIEW_REQUIRED" if score is not None else
                  "UNSCORED_PHASE_APPROPRIATE_EVIDENCE_INCOMPLETE")
        result.append({
            "level": level, "name": row["name"], "nct": nct, "phase": phase,
            "application_stage": application, "as_of": cutoff.isoformat(),
            "score_out_of_100": score,
            "score_type": "UNVALIDATED_EQUAL_WEIGHT_CUMULATIVE_RESEARCH_RUBRIC",
            "fda_approval_probability": None,
            "score_not_fda_probability": True,
            "scientific_confidence": "NOT_VALIDATED",
            "review_status": REVIEW_REQUIRED,
            "assessment_status": status, "phase_first": True,
            "cumulative_scoring_criteria": len(required),
            "scored_criteria": len(included),
            "phase_not_yet_expected_criteria": sum(
                g["status"] == "NOT_YET_EXPECTED" for g in gaps),
            "verified_source_ratings": included,
            "evidence_gaps": gaps,
            "score_reasons": [x["reason"] for x in included],
            "science_complete": False,
            "prediction_engine_calibrated": False,
            "assessment_version": "LEVEL4_20_CUMULATIVE_PILOT_V1",
        })
    return result


def build(manifest: dict, roster: dict, evidence: dict | None) -> dict:
    levels = validated_manifest(manifest)
    names = validated_roster(roster)
    as_of = utc_date(evidence.get("as_of") if evidence else roster["source"]["snapshot_date"])
    if evidence is None:
        evidence = {"schema_version": 1, "as_of": as_of.isoformat(), "trials": []}
    if evidence.get("schema_version") != 1 or not isinstance(evidence.get("trials"), list):
        raise ValueError("Bad evidence input")
    by_id: dict[str, dict] = {}
    for row in evidence["trials"]:
        if not isinstance(row, dict) or row.get("nct") in by_id:
            raise ValueError("Duplicate/malformed evidence trial")
        by_id[row["nct"]] = row
    allowed = {r["nct"] for r in names}
    if set(by_id) - allowed:
        raise ValueError("Evidence includes trial not in dated FOCUS roster")
    results = []
    for name in names:
        nct = name["nct"]
        if nct in by_id:
            rows = assessment_for_trial(by_id[nct], levels, as_of)
        else:
            rows = [{"level": l["level"], "name": l["name"], "nct": nct,
                     "score_out_of_100": None,
                     "assessment_status": "UNSCORED_TRIAL_PHASE_AND_SOURCES_NOT_VERIFIED",
                     "evidence_gaps": [{"criterion": "phase_and_source_receipts",
                                         "status": "UNKNOWN",
                                         "reason": "FOCUS metadata is a lead, not original-source evidence"}],
                     "score_not_fda_probability": True,
                     "fda_approval_probability": None,
                     "science_complete": False,
                     "review_status": REVIEW_REQUIRED}
                    for l in levels]
        results.extend(rows)
    per_level = []
    for level in range(4, 21):
        group = [r for r in results if r["level"] == level]
        count = sum(r["score_out_of_100"] is not None for r in group)
        per_level.append({"level": level, "trials": len(group),
                          "provisional_numeric_scores": count,
                          "unscored": len(group)-count,
                          "complete_scientific_assessments": 0,
                          "review_required": True,
                          "all_focus_trials_scored": count == len(group),
                          "scientifically_accepted": False})
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "roster": "DATED_FOCUS_SNAPSHOT_NOT_VERIFIED_CURRENT_CANONICAL",
        "source_spreadsheet_id": roster["source"]["spreadsheet_id"],
        "as_of": as_of.isoformat(),
        "focus_trials": len(names), "scientific_levels": 17,
        "assessment_records": len(results),
        "scientific_acceptance_automated": False, "production_publication": False,
        "validated_pdufa_probability_available": False,
        "rubric_warning": ("Equal-weight 0-100 research score is an unvalidated rubric. "
                          "No FDA probability, calibration, or independent scientific signoff."),
        "per_level": per_level, "assessments": results,
    }


def safe_write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("Refuse symlink output")
    fd, tmp = tempfile.mkstemp(prefix=".assess-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--roster", type=Path, default=DEFAULT_ROSTER)
    parser.add_argument("--evidence", type=Path, help="Curated per-criterion evidence JSON")
    parser.add_argument("--output", type=Path, help="Write audit-only results JSON")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print("PASS: PDUFA Level4-20 cumulative assessment module importable")
        return 0
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    roster = json.loads(args.roster.read_text(encoding="utf-8"))
    evidence = json.loads(args.evidence.read_text(encoding="utf-8")) if args.evidence else None
    result = build(manifest, roster, evidence)
    if args.output:
        safe_write(args.output, result)
    print(json.dumps({k: v for k, v in result.items() if k != "assessments"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

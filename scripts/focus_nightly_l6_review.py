#!/usr/bin/env python3
"""Privacy-minimizing, read-only nightly FOCUS Level 6 assessment readiness monitor.

Uses the existing FOCUS Google Sheet and existing ClinicalTrials.gov monitor.
This does NOT write scores, generate FDA forecasts, sign scientific reviews,
post to the site, edit FOCUS membership or enable retired scoring workflows.

Full trial-level queue remains ephemeral on the CI runner, not copied into
public GitHub commits, Actions artifacts or log summaries.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
from urllib.parse import quote

from pdufa_scoring_replay_guard import score_trials

SPREADSHEET_ID = "1erY_z62b4mHhx5s_3HgJxXoJEslbLngMuQNfhcuSviU"
SOURCE_RANGE = "FOCUS!A3:AE207"
FOCUS_SHEET_LINK = (
    f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit#gid=202611061"
)
WORKBENCH_LINK = (
    f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit#gid=2026111260"
)
REQUIRED_HEADERS = {
    0: "Ticker",
    1: "NCT ID",
    2: "Company",
    6: "Registry Status",
    7: "Phase 3 Results Public?",
    10: "Snapshot Date",
    15: "Provisional Component Scores (Not Overall)",
    22: "Active Review Status",
    26: "Market Cap USD",
    28: "PDUFA / FDA Filing",
}
COMPONENT = re.compile(r"post-1-(\d):([^;]+)")
EXACT_NCT = re.compile(r"NCT\d{8}\Z")
ALLOWED_SCORES = {"0", "25", "50", "75", "100"}
ISODATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def live_worksheet() -> list[list]:
    """Read with the same GitHub Actions service account as existing FOCUS sync."""
    import google.auth.transport.requests
    from google.oauth2 import service_account
    import requests

    key = os.environ.get("GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON")
    if not key:
        raise RuntimeError("FOCUS_SHEETS_SERVICE_ACCOUNT_UNAVAILABLE")
    creds = service_account.Credentials.from_service_account_info(
        json.loads(key), scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    uri = (f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}"
           f"/values/{quote(SOURCE_RANGE, safe='!:')}")
    response = requests.get(
        uri, headers={"Authorization": "Bearer " + creds.token},
        params={"valueRenderOption": "UNFORMATTED_VALUE"}, timeout=45,
    )
    response.raise_for_status()
    data = response.json().get("values")
    if not isinstance(data, list):
        raise ValueError("FOCUS_SHEET_RESPONSE_NOT_ROWS")
    return data


def clinical_components(value) -> list[int | None]:
    result = {i: None for i in range(1, 6)}
    value = value if isinstance(value, str) else ""
    if value and not value.startswith("CLINICAL_FIVE: "):
        raise ValueError("UNKNOWN_COMPONENT_SCHEMA")
    for match in COMPONENT.finditer(value):
        idx = int(match.group(1))
        raw = match.group(2).strip()
        if idx not in result or (raw not in ALLOWED_SCORES and raw not in {
            "MISSING_EVIDENCE", "NOT_REPORTED", "PENDING"
        }):
            raise ValueError("UNRECOGNIZED_COMPONENT_OR_STATE")
        if raw in ALLOWED_SCORES:
            result[idx] = int(raw)
    # Reject duplicated factor identifiers, including conflicting grades.
    indices = [int(match.group(1)) for match in COMPONENT.finditer(value)]
    if len(set(indices)) != len(indices):
        raise ValueError("DUPLICATE_CLINICAL_COMPONENT")
    if value and set(indices) != set(range(1, 6)):
        raise ValueError("INCOMPLETE_CLINICAL_FIVE_COMPONENT_SCHEMA")
    return [result[i] for i in range(1, 6)]


def build_assessment_readiness(
    sheet_values: list[list], roster: dict, registry: dict, today: date,
) -> dict:
    if not isinstance(sheet_values, list) or len(sheet_values) < 2:
        raise ValueError("FOCUS_LIVE_SHEET_MISSING_OR_EMPTY")
    header, values = sheet_values[0], sheet_values[1:]
    for index, label in REQUIRED_HEADERS.items():
        if len(header) <= index or header[index] != label:
            raise ValueError("FOCUS_HEADER_SCHEMA_DRIFT")
    if roster.get("schemaVersion") != 1 or not isinstance(roster.get("records"), list):
        raise ValueError("UNCERTAIN_GITHUB_ROSTER")
    if registry.get("schemaVersion") != 1 or not isinstance(registry.get("trials"), list):
        raise ValueError("UNCERTAIN_NIGHTLY_REGISTRY_SNAPSHOT")

    by_nct = {}
    for record in roster["records"]:
        nct = record.get("nct")
        if not isinstance(nct, str) or not EXACT_NCT.fullmatch(nct) or nct in by_nct:
            raise ValueError("DUPLICATED_OR_INVALID_GITHUB_NCT")
        by_nct[nct] = record
    source_by_nct = {}
    for record in registry["trials"]:
        nct = record.get("nct")
        if not isinstance(nct, str) or not EXACT_NCT.fullmatch(nct) or nct in source_by_nct:
            raise ValueError("DUPLICATED_OR_INVALID_REGISTRY_NCT")
        source_by_nct[nct] = record

    prepared, context, seen = [], [], set()
    for row in values:
        if len(row) <= 1 or not str(row[1]).strip():
            continue
        if len(row) < 31:
            raise ValueError("INCOMPLETE_FOCUS_31_COLUMN_ROW")
        ticker, nct = str(row[0]).strip(), str(row[1]).strip()
        if not EXACT_NCT.fullmatch(nct) or nct in seen or not re.fullmatch(r"[A-Z][A-Z0-9.]{0,9}", ticker):
            raise ValueError("INVALID_OR_DUPLICATE_LIVE_FOCUS_IDENTITY")
        seen.add(nct)
        result_state = str(row[7]).strip()
        if not result_state.upper().startswith("YES"):
            raise ValueError("FOCUS_ROW_DOES_NOT_HAVE_PUBLIC_PHASE3_EVIDENCE")
        snap = str(row[10]).strip()
        if not ISODATE.fullmatch(snap):
            raise ValueError("SOURCE_SNAPSHOT_DATE_MISSING")
        date.fromisoformat(snap)
        source_url = str(row[9]).strip()
        if source_url != f"https://clinicaltrials.gov/study/{nct}":
            raise ValueError("EXACT_NCT_REGISTRY_SOURCE_MISMATCH")
        scores = clinical_components(row[15])
        reg = source_by_nct.get(nct)
        phase_checked = (
            isinstance(reg, dict) and reg.get("sourceStatus") == "OFFICIAL_REGISTRY_RETRIEVED"
            and "PHASE3" in (reg.get("phase") or [])
        )
        if nct in by_nct and by_nct[nct].get("ticker") != ticker:
            raise ValueError("GITHUB_ROSTER_TICKER_MISMATCH")
        if reg is not None and reg.get("ticker") != ticker:
            raise ValueError("REGISTRY_SOURCE_TICKER_MISMATCH")
        context.append({
            "nct": nct, "ticker": ticker,
            "roster_present": nct in by_nct,
            "source_phase3_verified_from_run": bool(phase_checked),
            "source_status": reg.get("sourceStatus") if reg else "NOT_IN_MONITORED_ROSTER",
            "registry_delta": reg.get("delta") if reg else "NOT_MONITORED",
            "application_cycles": reg.get("applicationCycles") if reg else [],
            "source_snapshot": snap,
            "listed_fda_date": row[28] if isinstance(row[28], str) else "",
            "application_stage_from_sheet": str(row[22]),
        })
        prepared.append({
            "ticker": ticker, "nct": nct,
            "registry_status": str(row[6]),
            "phase_evidence": (
                "LIVE_REGISTRY_PHASE3" if phase_checked
                else "FOCUS_REPORTS_PUBLIC_PHASE3_NEEDS_REGISTRY_VERIFICATION"
            ),
            "snapshot_date": snap,
            "source_url": source_url,
            "clinical_components": scores,
        })
    if not prepared:
        raise ValueError("NO_FOCUS_TRIALS_FOR_ASSESSMENT")

    score_report = score_trials(prepared)
    entries = []
    for item, src in zip(score_report["trials"], context):
        count = int(item["component_coverage"].split("/")[0])
        recorded_date = src["listed_fda_date"]
        due = (date.fromisoformat(recorded_date) if
               isinstance(recorded_date, str) and ISODATE.fullmatch(recorded_date) else None)
        imminent = bool(due and today <= due <= today + timedelta(days=30))
        missing_registry = not src["roster_present"] or not src["source_phase3_verified_from_run"]
        priority = (0 if imminent or missing_registry else 1 if count < 5 else 2)
        if "planned" in src["application_stage_from_sheet"].lower():
            regulatory = "FUTURE_FDA_REVIEW_FINDINGS_NOT_YET_EXPECTED"
        else:
            regulatory = "FDA_CMC_AND_INSPECTION_FINDINGS_NOT_INDEPENDENTLY_VERIFIED"
        entries.append({
            **item,
            "application_cycles": src["application_cycles"],
            "source_registry_delta": src["registry_delta"],
            "source_status": src["source_status"],
            "source_phase3_verified_from_run": src["source_phase3_verified_from_run"],
            "application_stage_from_sheet": src["application_stage_from_sheet"],
            "missing_regulatory_conclusion_class": regulatory,
            "recorded_fda_date_unverified": recorded_date,
            "priority": priority,
            "requires_review": True,
            "scientific_score_100": None,
            "regulatory_score_100": None,
            "manufacturing_score_100": None,
            "confidence_rating": None,
            "fda_probability": None,
            "genuine_blind_prediction": False,
        })
    entries.sort(key=lambda x: (x["priority"], -int(x["component_coverage"].split("/")[0]) if x["priority"] == 0 else int(x["component_coverage"].split("/")[0]), x["nct"]))
    for rank, entry in enumerate(entries, 1):
        entry["review_order"] = rank

    extra_from_github = sorted(set(by_nct) - seen)
    new_in_live_sheet = sorted(seen - set(by_nct))
    unmatched_registry = sorted(seen - set(source_by_nct))
    return {
        "schemaVersion": 1,
        "kind": "FOCUS_LEVEL6_RESEARCH_READINESS_ONLY_NO_AUTOMATED_FDA_SCORING",
        "asOf": today.isoformat(),
        "source": FOCUS_SHEET_LINK,
        "workbench": WORKBENCH_LINK,
        "mode": "EXISTING_CLINICAL_SCORES_ONLY_WITH_PHASE_FIRST_REASSESSMENT",
        "reviewRequired": True,
        "validatedLevel6OverallScores": 0,
        "validatedFdaProbabilities": 0,
        "blindProspectivePredictionsProduced": 0,
        "summary": {
            "liveFocusNcts": len(entries),
            "savedGithubRosterNcts": len(by_nct),
            "fiveClinicalFactors": score_report["five_of_five"],
            "partialClinicalFactors": score_report["partial"],
            "noClinicalFactors": score_report["not_scoreable"],
            "nearFdaDateUnverifiedCount": sum(
                1 for e in entries
                if isinstance(e["recorded_fda_date_unverified"], str)
                and ISODATE.fullmatch(e["recorded_fda_date_unverified"]) is not None
                and today <= date.fromisoformat(e["recorded_fda_date_unverified"])
                <= today + timedelta(days=30)
            ),
            "liveSheetOnlyNcts": len(new_in_live_sheet),
            "githubOnlyNcts": len(extra_from_github),
            "notVerifiedInCurrentRegistryScan": len(unmatched_registry),
            "registryPhase3UnverifiedNcts": sum(not e["source_phase3_verified_from_run"] for e in entries),
            "evidenceChangedNcts": sum(e["source_registry_delta"] == "REGISTRY_EVIDENCE_CHANGED" for e in entries),
            "independentScientificSignoffs": 0,
            "automatedAssessmentDecisions": 0,
        },
        "rosterMismatchReview": {
            "newInLiveSheet": new_in_live_sheet,
            "missingFromLiveSheet": extra_from_github,
            "absentFromRegistryMonitor": unmatched_registry,
            "automaticRosterChanges": False,
        },
        "assessments": entries,
        "safety": {
            "noScoredMedicalJudgementsFabricated": True,
            "noAutomaticFDAProbabilities": True,
            "noPublicPredictionPublication": True,
            "noPrivateTrialScoresPublishedToGitHub": True,
            "noGoogleSheetWrites": True,
            "historicalOutcomeBlindAccuracyClaimed": False,
        },
    }


def write_step_summary(report: dict) -> None:
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_file:
        return
    s = report["summary"]
    with open(summary_file, "a", encoding="utf-8") as f:
        f.write("## Existing FOCUS scan: Level 6 research-readiness review\n\n")
        f.write("Private per-trial score details remain in the Google Sheet and ephemeral runner memory.\n\n")
        for k in ("liveFocusNcts", "savedGithubRosterNcts", "fiveClinicalFactors",
                  "partialClinicalFactors", "noClinicalFactors",
                  "nearFdaDateUnverifiedCount", "liveSheetOnlyNcts",
                  "githubOnlyNcts", "registryPhase3UnverifiedNcts",
                  "evidenceChangedNcts", "validatedLevel6OverallScores",
                  "automatedAssessmentDecisions"):
            value = report.get(k, s.get(k))
            f.write(f"- {k}: {value}\n")
        f.write(f"\n[Open owner scoring workbench]({WORKBENCH_LINK})\n\n")
        f.write("**Not a completed Level 6 scientific assessment, FDA probability or blind prediction.**\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roster", type=Path, required=True)
    parser.add_argument("--registry-current", type=Path, required=True)
    parser.add_argument("--sheet-fixture", type=Path, default=None)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--as-of", default=None)
    args = parser.parse_args()

    today = date.fromisoformat(args.as_of) if args.as_of else datetime.now(timezone.utc).date()
    sheet = read_json(args.sheet_fixture) if args.sheet_fixture else live_worksheet()
    report = build_assessment_readiness(
        sheet, read_json(args.roster), read_json(args.registry_current), today,
    )
    args.private_output.parent.mkdir(parents=True, exist_ok=True)
    if args.private_output.exists():
        raise SystemExit("REFUSE_OVERWRITE_PRIOR_PRIVATE_REVIEW_QUEUE")
    # GitHub-hosted runner temp path only. CI workflow never uploads this file.
    args.private_output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_step_summary(report)
    # Aggregate status only; no per-trial private clinical grades in public logs.
    print(json.dumps(report["summary"], sort_keys=True))
    if report["summary"]["liveSheetOnlyNcts"] or report["summary"]["githubOnlyNcts"]:
        print("::warning::Source roster differs from live FOCUS. Reconcile existing nightly FOCUS sync.")
    if report["summary"]["registryPhase3UnverifiedNcts"]:
        print("::warning::Some FOCUS trial phases require fresh original-registry verification.")
    print("All scientific assessments remain review-gated. No automated FDA predictions.")


if __name__ == "__main__":
    main()

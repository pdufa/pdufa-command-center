#!/usr/bin/env python3
"""Daily FDA public application-history watch for November 2026 research leads.

This is a public-data identity *signal*, NOT a prediction, decision, regulatory
clearance, independently certified application cycle or trading instruction.
In particular, the 2026-02-05 NDA 219083/S-001 REMS approval is NEVER the
pending MAPLE-HCM efficacy supplement. Drugs@FDA may lag and omits most
pending application identifiers; missing rows cannot disprove an application.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "new-platform/frontend/data/raas-v2-nov14-review-cycle-triangulation.json"
SCOPE = "RAAS_V2_OPENFDA_NOV14_APPLICATION_IDENTITY_WATCH_NOT_VALIDATED"
SEARCH = 'application_number:"NDA219083"'
URL = "https://api.fda.gov/drug/drugsfda.json?" + urllib.parse.urlencode(
    {"search": SEARCH, "limit": "1"}
)
# A second public search finds approved/publicly indexed ingredient matches.
# It does NOT index confidential pending BLA submissions or identify a cycle.
SMMT_SEARCH = 'products.active_ingredients.name:"IVONESCIMAB"'
SMMT_URL = "https://api.fda.gov/drug/drugsfda.json?" + urllib.parse.urlencode(
    {"search": SMMT_SEARCH, "limit": "25"}
)
MAX_BYTES = 2_000_000


def require(ok: bool, code: str) -> None:
    if not ok:
        raise ValueError("OPENFDA_APPLICATION_WATCH_" + code)


def observed_date(utc: str) -> dt.date:
    require(isinstance(utc, str) and utc.endswith("Z"), "TIME_FORMAT")
    try:
        return dt.datetime.strptime(utc, "%Y-%m-%dT%H:%M:%SZ").date()
    except ValueError as exc:
        raise ValueError("OPENFDA_APPLICATION_WATCH_TIME_INVALID") from exc


def check_dossier(d: dict) -> dict:
    require(d.get("scope") ==
            "RAAS_V2_NOV14_2026_ISSUER_FDA_AND_REGISTRY_TRIANGULATION_RESEARCH_ONLY"
            and d.get("casesCrossChecked") == 2
            and d.get("independentlyVerifiedCurrentApplicationCycleCount") == 0
            and d.get("independentlyVerifiedFrozenThreeWayForecastCount") == 0
            and d.get("approvedMetricCalibrations") == 0,
            "WRONG_DOSSIER_OR_APPROVAL")
    items = {x["researchCaseKey"]: x for x in d.get("records", [])}
    require(len(items) == 2 and set(items) == {
        "CYTK|MYQORZO_HCM_20261114", "SMMT|IVONESCIMAB_20261114"
    }, "WRONG_REVIEW_CYCLES")
    cy = items["CYTK|MYQORZO_HCM_20261114"]
    sm = items["SMMT|IVONESCIMAB_20261114"]
    require(cy.get("usFDAParentOriginalNdaNumber") == "219083"
            and cy.get("fdaPreviouslyApprovedUnrelatedSupplementNumber") == "S-001"
            and cy.get("fdaPreviouslyApprovedUnrelatedSupplementPurpose") ==
                "REMS_MODIFICATION_NOT_MAPLE_HCM"
            and cy.get("fdaPreviouslyApprovedS001EstablishesNov14FDAOutcome") is False
            and cy.get("currentSupplementSequenceNumber") is None
            and cy.get("specificPendingMAPLESupplementNumberIndependentlyVerified") is False
            and sm.get("currentBlaNumber") is None
            and sm.get("currentBlaNumberIndependentlyVerified") is False
            and all(x.get("exactCurrentFDAReviewCycleIndependentlyCertified") is False
                    and x.get("independentlyVerifiedThreeWayForecast") is False
                    for x in (cy, sm)),
            "RESEARCH_LEAD_MISLABELED_AS_APPROVED")
    return items


def date_string(raw: object) -> str | None:
    if not isinstance(raw, str) or len(raw) != 8 or not raw.isdigit():
        return None
    try:
        return dt.datetime.strptime(raw, "%Y%m%d").date().isoformat()
    except ValueError:
        return None



def inspect_smmt_public_ingredient(payload: dict | None, as_of: dt.date,
                                   source_status: str, detail: str | None) -> dict:
    """Source candidates only. An absent/returned BLA never proves pending status."""
    require(source_status in {
        "AVAILABLE", "HTTP_404_NO_PUBLIC_RECORD", "SOURCE_UNAVAILABLE",
        "MALFORMED_RESPONSE", "NOT_QUERIED"}, "SMMT_SOURCE_STATUS_INVALID")
    require(source_status == "AVAILABLE" or payload is None,
            "SMMT_SOURCE_STATUS_PAYLOAD_MISMATCH")
    candidates = []
    total = None
    last_updated = None
    result_count = 0
    if source_status == "AVAILABLE":
        require(isinstance(payload, dict) and
                isinstance(payload.get("results"), list) and
                len(payload["results"]) <= 25,
                "SMMT_INGREDIENT_RESPONSE_SCHEMA_INVALID")
        meta = payload.get("meta")
        if isinstance(meta, dict):
            last_updated = str(meta.get("last_updated") or "")[:100] or None
            rs = meta.get("results")
            if isinstance(rs, dict) and type(rs.get("total")) is int:
                total = rs["total"]
        rows = payload["results"]
        result_count = len(rows)
        for row in rows:
            require(isinstance(row, dict), "SMMT_INGREDIENT_ROW_NOT_OBJECT")
            products = row.get("products")
            require(isinstance(products, list), "SMMT_INGREDIENT_PRODUCTS_MISSING")
            ingredient_match = False
            for product in products:
                require(isinstance(product, dict), "SMMT_INGREDIENT_PRODUCT_NOT_OBJECT")
                active = product.get("active_ingredients", [])
                require(isinstance(active, list), "SMMT_ACTIVE_INGREDIENTS_NOT_LIST")
                for ingredient in active:
                    require(isinstance(ingredient, dict), "SMMT_INGREDIENT_NOT_OBJECT")
                    name = ingredient.get("name")
                    if isinstance(name, str) and name.strip().upper() == "IVONESCIMAB":
                        ingredient_match = True
            if not ingredient_match:
                # Fuzzy/aggregated source search is not a license identifier.
                continue
            application_number = row.get("application_number")
            # Only a syntactically plausible *published* BLA is shown as
            # research evidence; it still needs original FDA documents.
            if not isinstance(application_number, str) or not re.fullmatch(
                    r"BLA[0-9]{6}", application_number):
                continue
            submissions = row.get("submissions", [])
            require(isinstance(submissions, list),
                    "SMMT_INGREDIENT_SUBMISSIONS_NOT_LIST")
            dates = []
            for x in submissions:
                require(isinstance(x, dict),
                        "SMMT_INGREDIENT_SUBMISSION_NOT_OBJECT")
                dated = date_string(x.get("submission_status_date"))
                if dated is not None and dated <= as_of.isoformat():
                    dates.append(dated)
            candidates.append({
                "applicationNumberPubliclyIndexed": application_number,
                "fdaIndexedSponsorName": str(row.get("sponsor_name") or "")[:120],
                "matchedActiveIngredient": "IVONESCIMAB",
                "latestPublicSubmissionStatusDateNotIndependentlyAdjudicated":
                    max(dates) if dates else None,
                "pendingSMMTBlaNumberIndependentlyVerified": False,
                "sameEGFRmNSCLCHarmonIReviewCycleVerified": False,
                "fdaOutcomeFromPublicProductIndexVerified": False,
            })
    candidates.sort(key=lambda x:x["applicationNumberPubliclyIndexed"])
    require(len(candidates) <= 25, "SMMT_CANDIDATE_OVERFLOW")
    return {
        "ingredientQueryUrl": SMMT_URL,
        "publicSourceStatus": source_status,
        "publicSourceDetail": (detail or "")[:250],
        "publicDatasetLastUpdatedAsReported": last_updated,
        "resultsReturnedByFDA": result_count,
        "fdaReportedTotalMatches": total,
        "fdaResultPageMayBeTruncated": total is not None and total > result_count,
        "matchingPublishedBlaCandidatesNeedIndependentReview": candidates,
        "fdaPendingBlaAbsentFromPublicIndexProvesNoSubmission": False,
        "fdaPublicIndexedCandidateIndependentlyMatchesSummitHARMONi": False,
        "fdaOriginalBlaCycleAndGoalVerified": False,
        "fdaApprovalCrlOrExtensionVerifiedFromIngredientSearch": False,
        "warning": "Publicly indexed licensed-product ingredient searches may lag, "
                   "omit pending BLA numbers or return unrelated companies/cycles. "
                   "Even a matching drug name and BLA number is an unverified "
                   "document lead, not evidence of this Summit HARMONi review "
                   "or a prospective FDA prediction.",
    }


def inspect_response(payload: dict | None, checked_at: str,
                     source_status: str = "AVAILABLE",
                     source_detail: str | None = None,
                     dossier: dict | None = None,
                     smmt_payload: dict | None = None,
                     smmt_status: str = "NOT_QUERIED",
                     smmt_detail: str | None = None) -> dict:
    """Fail closed on malformed FDA responses and never auto-identify MAPLE."""
    now = observed_date(checked_at)
    d = dossier or json.loads(DOSSIER.read_text("utf-8"))
    items = check_dossier(d)
    require(source_status in {"AVAILABLE", "HTTP_404_NO_PUBLIC_RECORD",
                "SOURCE_UNAVAILABLE", "MALFORMED_RESPONSE"},
            "INVALID_SOURCE_STATUS")
    require(not (source_status != "AVAILABLE" and payload is not None),
            "FAIL_CLOSED_RESPONSE_STATUS")

    state = source_status
    meta = {}
    submissions = []
    if source_status == "AVAILABLE":
        require(isinstance(payload, dict) and
                isinstance(payload.get("results"), list) and
                len(payload["results"]) == 1 and
                isinstance(payload["results"][0], dict),
                "FDA_SCHEMA_INVALID")
        row = payload["results"][0]
        require(row.get("application_number") == "NDA219083" and
                isinstance(row.get("submissions"), list),
                "FDA_APPLICATION_IDENTITY_OR_SUBMISSIONS_MISMATCH")
        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
        for x in row["submissions"]:
            require(isinstance(x, dict), "FDA_SUBMISSION_NOT_OBJECT")
            # Some FDA submission records have incomplete dates; keep them
            # visible as unclassified, never as a confirmed regulatory event.
            typ = str(x.get("submission_type") or "").upper().strip()
            number = str(x.get("submission_number") or "").strip()
            status = str(x.get("submission_status") or "").upper().strip()
            dated = date_string(x.get("submission_status_date"))
            if dated is not None and dated > now.isoformat():
                # Prevent a future-dated database row from contaminating
                # an as-of report (or a retrospective test).
                continue
            if typ not in {"SUPPL", "ORIG"}:
                continue
            code = str(x.get("submission_class_code") or "").upper().strip()
            description = str(x.get("submission_class_code_description") or "")[:240]
            submissions.append({
                "submissionType": typ,
                "submissionNumber": number,
                "submissionStatus": status,
                "statusDate": dated,
                "submissionClassCode": code,
                "classDescription": description,
                "isPreviouslyApprovedUnrelatedRemsS001": (
                    typ == "SUPPL" and re.fullmatch(r"(?:S-?)?0*1", number.upper()) is not None
                ),
                "isMapleHcmPendingSupplementIndependentlyIdentified": False,
                "isApprovedMapleHcmOutcomeIndependentlyAdjudicated": False,
            })
    supplements = [x for x in submissions if x["submissionType"] == "SUPPL"]
    not_s001 = [x for x in supplements
                if not x["isPreviouslyApprovedUnrelatedRemsS001"]]
    sm = items["SMMT|IVONESCIMAB_20261114"]
    cy = items["CYTK|MYQORZO_HCM_20261114"]
    smmt_public = inspect_smmt_public_ingredient(
        smmt_payload, now, smmt_status, smmt_detail)
    return {
        "schemaVersion": 1,
        "scope": SCOPE,
        "status": "PUBLIC_DATABASE_MONITOR_ONLY_NOT_AN_FDA_CYCLE_OR_PREDICTION",
        "checkedAtUTC": checked_at,
        "issuerReportedGoalDate": "2026-11-14",
        "openFdaQueryUrl": URL,
        "smmtPublicIngredientQueryUrl": SMMT_URL,
        "smmtOpenFdaSourceStatus": smmt_status,
        "smmtPublicIndexedBlaCandidateCount": len(
            smmt_public["matchingPublishedBlaCandidatesNeedIndependentReview"]),
        "openFdaSourceStatus": state,
        "openFdaErrorOrDetail": (source_detail or "")[:400],
        "openFdaLastUpdatedAsReported": str(meta.get("last_updated") or "")[:100] or None,
        "cytk": {
            "researchCaseKey": cy["researchCaseKey"],
            "issuerReportedOriginalGoalDate": cy["issuerReportedFirstGoalDate"],
            "fdaKnownParentNda": "NDA219083",
            "fdaParentRecordReturned": state == "AVAILABLE",
            "observedSupplementSubmissionRows": supplements,
            "nonS001SupplementRowsRequireSeparateDocumentCycleMatching": not_s001,
            "fdaApprovedFebruaryRemsS001IsNovemberMapleHcm": False,
            "mapleHcmCurrentSupplementNumberIndependentlyVerified": False,
            "newFdaMapleHcmApprovalIndependentlyAdjudicated": False,
            "sourceForKnownRemsS001": cy["fdaPreviouslyApprovedUnrelatedSupplementSourceUrl"],
            "sourceForNov14IssuerGoal": cy["issuerGoalSourceUrl"],
        },
        "smmt": {
            "researchCaseKey": sm["researchCaseKey"],
            "issuerReportedOriginalGoalDate": sm["issuerReportedFirstGoalDate"],
            "fdaCurrentBlaNumberIndependentlyVerified": False,
            "fdaPublicOpenFdaNoMatchingApprovedBlaProvesNoPendingBla": False,
            "independentFdaOriginalCycleOrExtensionHistoryVerified": False,
            "sourceForNov14IssuerGoal": sm["issuerGoalSourceUrl"],
            "approvedProductIngredientSearch": smmt_public,
            "note": "Without an independently published numbered pending BLA, the "
                    "approved-product index cannot certify Summit's current "
                    "original review cycle; absence is not negative evidence.",
        },
        "independentlyCertifiedCurrentFdaReviewCycles": 0,
        "independentlyAdjudicatedNov14FdaActions": 0,
        "newImmutableThreeWayPredictions": 0,
        "approvedMetricCalibrations": 0,
        "canPromoteToFdaPredictionAccuracy": False,
        "warning": "openFDA/Drugs@FDA can lag and generally documents publicly "
                   "released actions, not confidential pending BLA/sNDA identities. "
                   "A supplement row, even an EFFICACY code, is not proof it concerns "
                   "MAPLE-HCM without a matching dated FDA approval letter or label. "
                   "No absence or retrieval failure proves no application, approval, "
                   "CRL or extension. S-001 is explicitly the unrelated REMS approval.",
    }


def fetch_public_parent(url: str = URL) -> tuple[dict | None, str, str | None]:
    require(url in {URL, SMMT_URL}, "FDA_URL_NOT_IN_ALLOWLIST")
    request = urllib.request.Request(url, headers={
        "User-Agent": "RAAS-source-readiness/1.0 (research-only; GitHub Actions)",
        "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read(MAX_BYTES + 1)
            require(len(raw) <= MAX_BYTES, "FDA_BODY_TOO_LARGE")
        try:
            return json.loads(raw.decode("utf-8")), "AVAILABLE", None
        except (UnicodeError, ValueError):
            return None, "MALFORMED_RESPONSE", "openFDA body not parseable JSON"
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None, "HTTP_404_NO_PUBLIC_RECORD", "Public API returned 404; not proof of no application"
        return None, "SOURCE_UNAVAILABLE", "FDA API HTTP " + str(exc.code)
    except (OSError, TimeoutError) as exc:
        return None, "SOURCE_UNAVAILABLE", type(exc).__name__


def main() -> None:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload, status, detail = fetch_public_parent()
    smmt_payload, smmt_status, smmt_detail = fetch_public_parent(SMMT_URL)
    result = inspect_response(
        payload, now, status, detail,
        smmt_payload=smmt_payload, smmt_status=smmt_status,
        smmt_detail=smmt_detail)
    path = Path(os.environ.get("RAAS_OPENFDA_APPLICATION_WATCH_JSON",
        "raas-v2-openfda-application-identity-watch.json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    print(json.dumps({k: result[k] for k in
        ("status", "checkedAtUTC", "openFdaSourceStatus",
         "smmtOpenFdaSourceStatus",
         "smmtPublicIndexedBlaCandidateCount",
         "independentlyCertifiedCurrentFdaReviewCycles",
         "independentlyAdjudicatedNov14FdaActions",
         "newImmutableThreeWayPredictions")}, sort_keys=True))


if __name__ == "__main__":
    main()

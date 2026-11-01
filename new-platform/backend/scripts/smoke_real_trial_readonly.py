#!/usr/bin/env python3
"""Read-only Phase 3 batch API smoke test with source-dated PEAK case.

Requires PDUFA_INTERNAL_API_KEY in environment; never prints or stores the key.
No scanner scheduling, spreadsheet writes, or trading operations.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from datetime import datetime
from zoneinfo import ZoneInfo

DEFAULT_BASE = "https://pdufa-hop-readonly-review.onrender.com"
FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "peak_real_trial_20261027.json"
PEAK_KEY = "APPLICATION|COGT|BEZUCLASTINIB_GIST_20261130"
MAX_RESPONSE_BYTES = 1_000_000


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError("Redirect refused; no credential forwarded")


def validated_base(value: str) -> str:
    allowed = {DEFAULT_BASE, "https://pdufa-new-api-staging.onrender.com"}
    base = value.rstrip("/")
    if base not in allowed or urlsplit(base).scheme != "https":
        raise ValueError("Use an existing authorized PDUFA HTTPS API origin")
    return base


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Repeated response field")
        result[key] = value
    return result


def get_json(req: Request) -> dict:
    try:
        with build_opener(NoRedirect()).open(req, timeout=30) as res:
            if res.status != 200:
                raise RuntimeError(f"Unexpected HTTP status {res.status}")
            data = res.read(MAX_RESPONSE_BYTES + 1)
            if len(data) > MAX_RESPONSE_BYTES:
                raise RuntimeError("API response exceeds smoke-check limit")
            payload = json.loads(data, object_pairs_hook=_unique_object,
                                 parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Invalid JSON number")))
    except HTTPError as exc:
        # Do not echo submitted headers or confidential response bodies.
        raise RuntimeError(f"API returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError("Service unreachable; verify public hostname and network") from exc
    except (ValueError, UnicodeError) as exc:
        raise RuntimeError("Invalid API JSON response") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected non-object API response")
    return payload


def verify_published_chain(payload: dict, *, expected_as_of: str) -> dict:
    """Verify the actual server-maintained research read, not a posted fixture.

    Passing this probe proves response consistency, never scientific validation.
    """
    if (payload.get("schemaVersion") != "peak-research-view-v1"
            or payload.get("exactKey") != PEAK_KEY or payload.get("asOf") != expected_as_of
            or any(payload.get(k) is not False for k in
                   ("tradeAuthorized", "sheetWritesEnabled", "productionSchedulingEnabled"))):
        raise RuntimeError("Published research identity, date or read-only boundary mismatch")
    science, outcome, main = (payload.get(k) for k in ("science40", "outcome", "main"))
    if not all(isinstance(x, dict) and x.get("exactKey") == PEAK_KEY
               and x.get("asOf") == expected_as_of and x.get("tradeAuthorized") is False
               for x in (science, outcome, main)):
        raise RuntimeError("SCIENCE, OUTCOME and MAIN identities/cutoffs do not reconcile")
    register = payload.get("researchRegister")
    if (not isinstance(register, dict) or register.get("exactKey") != PEAK_KEY
            or register.get("nctId") != "NCT05208047"
            or main.get("researchRegister") != register
            or science.get("totalAssessments") != 40
            or science.get("independentlyReviewedAssessments") != 0
            or science.get("readinessGrade") != "RELUCTANT"
            or main.get("researchReadinessGrade") != science["readinessGrade"]):
        raise RuntimeError("Published scientific register or MAIN evidence link mismatch")
    questions = register.get("questions")
    if (not isinstance(questions, list) or len(questions) != 40
            or any(not isinstance(q, dict) or q.get("id") != f"S{i:02}"
                   or q.get("exactKey") != PEAK_KEY or q.get("independentlyReviewed") is not False
                   for i, q in enumerate(questions, 1))):
        raise RuntimeError("Published question inventory did not reconcile")
    if (outcome.get("decision") != "ABSTAIN" or outcome.get("modelValidated") is not False
            or outcome.get("decisionReadinessGrade") != "ABSTAIN"
            or outcome.get("confidence") is not None or outcome.get("nonapprovalProbability") is not None
            or outcome.get("predictionClasses") != ["PASS", "CRL", "EXTENSION"]
            or outcome.get("probabilities") != {"PASS": None, "CRL": None, "EXTENSION": None}
            or outcome.get("extensionIsNonapproval") is not False
            or main.get("prediction") != "INSUFFICIENT_EVIDENCE"
            or main.get("schemaVersion") != "phase3-main-readiness-v1"
            or main.get("decisionReadinessGrade") != "ABSTAIN" or main.get("confidence") is not None
            or main.get("modelValidated") is not False
            or main.get("modelVersion") is not None or main.get("predictionTimestamp") is not None
            or any(section.get("approvalProbability") is not None for section in (science, outcome, main))):
        raise RuntimeError("Unsupported forecast or prediction-validation claim")
    return {"status": "SMOKE_CHECK_PASSED", "mode": "SERVER_PUBLISHED_RESEARCH",
            "asOf": expected_as_of, "scienceAssessments": 40,
            "independentlyCertified": 0, "outcomeDecision": "ABSTAIN",
            "mainPrediction": "INSUFFICIENT_EVIDENCE", "modelValidated": False,
            "productionDataFlowVerified": False, "tradeAuthorized": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("PDUFA_HOP_URL", DEFAULT_BASE))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--empty", action="store_true", help="Test only an empty authenticated batch")
    mode.add_argument("--published", action="store_true", help="GET server-maintained SCIENCE/OUTCOME/MAIN; submit no fixture")
    args = parser.parse_args()

    base = validated_base(args.base_url)
    key = (os.getenv("PDUFA_HOP_INTERNAL_API_KEY", os.getenv("PDUFA_INTERNAL_API_KEY"))
           if base == DEFAULT_BASE else os.getenv("PDUFA_INTERNAL_API_KEY"))
    if not key:
        print("Missing existing API key binding for selected service", file=sys.stderr)
        return 2
    health = get_json(Request(base + "/health", headers={"Accept": "application/json"}))
    if (health.get("storage_ready") is not True or health.get("storage_kind") != "postgresql"
            or health.get("status") != "ok" or health.get("service") != "pdufa-new-backend"):
        raise RuntimeError("PostgreSQL storage is not ready; no batch submitted")

    if args.published:
        response = get_json(Request(base + "/api/internal/phase3-research/peak-register",
            headers={"Accept": "application/json", "x-pdufa-internal-key": key}))
        summary = verify_published_chain(response,
            expected_as_of=datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat())
        print(json.dumps(summary, indent=2))
        return 0

    case = json.loads(FIXTURE.read_text(encoding="utf-8"))
    candidates = [] if args.empty else [case["candidate"]]
    body = json.dumps({"candidates": candidates}).encode("utf-8")
    req = Request(
        base + "/api/internal/phase3-research/evaluate-batch",
        data=body, method="POST",
        headers={"Content-Type": "application/json", "x-pdufa-internal-key": key},
    )
    response = get_json(req)
    expected = len(candidates)
    preview = response.get("sheetPreview")
    if (
        response.get("totalDiscovered") != expected
        or response.get("eligibleForResearch") != expected
        or response.get("tradeAuthorized") is not False
        or response.get("sheetPopulationStatus") != "NOT_WRITTEN"
        or not isinstance(preview, dict)
        or preview.get("writtenToSheet") is not False
        or preview.get("mode") != "PREVIEW_ONLY"
    ):
        raise RuntimeError("Batch API violated expected read-only response contract")
    rows = preview.get("rows")
    if not isinstance(rows, list) or len(rows) != expected:
        raise RuntimeError("Unexpected sheet preview rows")
    for row in rows:
        if row.get("approvalProbability") is not None or row.get("independentConclusion") is not None:
            raise RuntimeError("An unsupported prediction/conclusion was returned")
    if candidates and rows[0].get("trialExactKey") != candidates[0]["exact_key"]:
        raise RuntimeError("Exact trial identity changed")
    print(json.dumps({
        "status": "PASS",
        "mode": "EMPTY_BATCH_CONTRACT" if args.empty else "FIXTURE_BATCH_CONTRACT_NOT_PRODUCTION_EVIDENCE",
        "storageReady": True,
        "totalDiscovered": response["totalDiscovered"],
        "eligibleForResearch": response["eligibleForResearch"],
        "sheetPreviewRows": len(rows),
        "writtenToSheet": False,
        "tradeAuthorized": False,
        "approvalProbability": None,
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)

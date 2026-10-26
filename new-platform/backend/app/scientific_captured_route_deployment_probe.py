"""Credential-free public deployment-parity probe for ONE frozen pilot route.

A 401 is only evidence that *some* route-level authorization rejects an
anonymous request. It does not prove backend version, authorized source read
success, document authorship, reviewer identity, or scientific validity.
A 404 is a release blocker, but not evidence that zero PDFs were archived.
No request body, token, read key, login, redirect, or database write is used.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

PILOT_NCT = "NCT02142738"
ROUTE = (
    "https://pdufa-scientific-assessment-review.onrender.com"
    "/api/scientific-assessment/captured-source-manifest/" + PILOT_NCT
)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def anonymous_http_status() -> int | None:
    """Probe the literal fixed public route without credentials or redirects."""
    request = Request(ROUTE, headers={"Accept": "application/json"},
                      method="GET")
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(request, timeout=35) as response:
            return int(response.status)
    except HTTPError as error:
        status = int(error.code)
        error.close()
        return status
    except (OSError, URLError, TimeoutError):
        return None


def classify(status: int | None) -> dict:
    if status is not None and (type(status) is not int or not 100 <= status <= 599):
        raise ValueError("Unrecognized HTTP status")
    if status == 401:
        classification = "ANONYMOUS_AUTH_GUARD_PRESENT"
    elif status == 404:
        classification = "CAPTURED_ROUTE_NOT_DEPLOYED"
    elif status in (403, 407):
        classification = "ACCESS_OR_PROXY_GUARD_UNVERIFIED"
    elif status is None or status >= 500:
        classification = "RENDER_BACKEND_UNAVAILABLE"
    elif 200 <= status <= 299:
        classification = "SECURITY_FAILURE_ANONYMOUS_READ_ACCEPTED"
    else:
        classification = "UNEXPECTED_ROUTE_RESPONSE"
    return {
        "nctId": PILOT_NCT,
        "check": "unauthenticated_live_deployment_route_presence_only",
        "anonymousHttpStatus": status,
        "classification": classification,
        "anonymousAccessSafelyDenied": classification == "ANONYMOUS_AUTH_GUARD_PRESENT",
        "capturedManifestReadWithCredential": False,
        "archivedPdfCountKnown": False,
        "originalSourceAuthenticated": False,
        "reviewerIdentityVerified": False,
        "scientificAdjudicationCompleted": False,
        "fdaApprovalProbability": None,
        "promotionAllowed": False,
        "note": (
            "401 indicates an anonymous auth guard, NOT successful authenticated "
            "manifest access. 404 indicates an undeployed/missing route, NOT an "
            "empty archive. No source authorship, scientific grade, reviewer "
            "qualification, or FDA outcome is verified by this probe."
        ),
    }


def main() -> int:
    report = classify(anonymous_http_status())
    text = json.dumps(report, sort_keys=True)
    print("Captured source backend deployment-parity check:", text, flush=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        output_path = Path(summary)
        with output_path.open("a", encoding="utf-8") as handle:
            handle.write(
                "\n### Captured PDF archive backend deployment parity\n\n"
                f"- Exact pilot: **{PILOT_NCT}**\n"
                f"- Anonymous HTTP code: **{report['anonymousHttpStatus']}**\n"
                f"- Classification: **{report['classification']}**\n"
                "- This is a credential-free route check only. It cannot verify "
                "an authorized archive read, document contents, independent "
                "reviewers or an FDA prediction.\n"
            )
    # Never certify readiness on any code other than 401. 404/unavailable are
    # visible unresolved release blockers, NOT CI test failures. 2xx is a
    # critical security regression and must fail the workflow immediately.
    return 1 if report["classification"] == "SECURITY_FAILURE_ANONYMOUS_READ_ACCEPTED" else 0


if __name__ == "__main__":
    raise SystemExit(main())

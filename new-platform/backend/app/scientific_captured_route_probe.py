"""Passive anonymous HTTP probe of the isolated scientific PDF manifest route.

This script only requests one hard-coded GET URL without credentials and
discards all response content. Anonymous HTTP behavior CANNOT authenticate
the scientific deployment commit, rehashed PDF bytes or reviewer evidence.

GitHub CI receives a separate status: 401 = access denied (route version still
unknown), 404 = route not found, 5xx = unavailable, 2xx/redirect = security
failure because the captured metadata endpoint must reject anonymous access.
Not-found/network states are warnings, never evidence of an installed route.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

PILOT_URL = (
    "https://pdufa-scientific-assessment-review.onrender.com"
    "/api/scientific-assessment/captured-source-manifest/NCT02142738"
)


@dataclass(frozen=True)
class RouteObservation:
    http_status: int | None
    status: str
    evidence_of_deployed_contract: bool = False
    independent_clinical_verification: bool = False


class NoRedirect(HTTPRedirectHandler):
    """Do not follow unexpected redirects to sign-in pages or other hosts."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def classify(status: int | None) -> RouteObservation:
    """Never interpret 401 as proof that the *new* route is installed."""
    if status is None:
        state = "NETWORK_OR_SERVICE_UNAVAILABLE"
    elif status == 401:
        state = "ANONYMOUS_ACCESS_DENIED_VERSION_UNCONFIRMED"
    elif status == 404:
        state = "ROUTE_NOT_FOUND_POSSIBLY_NOT_DEPLOYED"
    elif 200 <= status < 400:
        state = "ANONYMOUS_ACCESS_OR_REDIRECT_SECURITY_FAILURE"
    elif status == 403:
        state = "FORBIDDEN_ROUTE_DEPLOYMENT_UNCONFIRMED"
    elif status in (429, 500, 502, 503, 504):
        state = "NETWORK_OR_SERVICE_UNAVAILABLE"
    else:
        state = "UNEXPECTED_HTTP_STATUS_VERSION_UNCONFIRMED"
    return RouteObservation(status, state)


def probe(opener=None) -> RouteObservation:
    """One unauthenticated GET only; don't send a token or read any PDF bytes."""
    client = opener if opener is not None else build_opener(NoRedirect)
    request = Request(PILOT_URL, method="GET")
    try:
        with client.open(request, timeout=90) as response:
            status = response.status
    except HTTPError as error:
        status = error.code
        error.close()
    except (URLError, TimeoutError, OSError):
        return classify(None)
    return classify(status)


def render_report(result: RouteObservation) -> dict:
    """No secrets, response bodies, cloud workspace IDs or signed claims."""
    return {
        "probe": "isolated_science_anonymous_captured_manifest",
        "httpStatus": result.http_status,
        "routeObservation": result.status,
        "authenticatedContractAndDeploymentVerified": False,
        "clinicalSourceAuthenticated": False,
        "scientificScore": None,
        "fdaApprovalProbability": None,
        "notice": (
            "Anonymous HTTP does not establish backend commit/version or "
            "captured PDF authenticity. An authenticated exact-trial manifest "
            "check in the protected preview remains necessary."
        ),
    }


def main() -> int:
    result = probe()
    output = render_report(result)
    print(json.dumps(output, sort_keys=True), flush=True)

    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        # Text is from fixed internal status enums only (no user or HTTP body).
        with Path(summary).open("a", encoding="utf-8") as stream:
            stream.write(
                "\n### Isolated scientific captured-source route (anonymous)\n"
                f"- HTTP: {result.http_status if result.http_status is not None else 'unavailable'}\n"
                f"- Observation: \`{result.status}\`\n"
                "- Authenticated backend contract/commit verified: **NO**\n"
                "- Scientific evidence/grades verified: **NO**\n"
            )
    if result.status == "ANONYMOUS_ACCESS_OR_REDIRECT_SECURITY_FAILURE":
        print(
            "::error::The protected captured-source endpoint returned a 2xx or redirect "
            "without credentials; deny preview release pending a security review.",
            flush=True,
        )
        return 1
    if result.status != "ANONYMOUS_ACCESS_DENIED_VERSION_UNCONFIRMED":
        print(
            f"::warning::Isolated Render archive route cannot be confirmed: {result.status}. "
            "Do not count this as a deployed source manifest or scientific verification.",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

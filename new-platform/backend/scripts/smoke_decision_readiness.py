"""Read-only smoke assertions for the isolated investment research endpoint.

Usage (only against the isolated service):
 PDUFA_REVIEW_BASE_URL=https://... PDUFA_INTERNAL_API_KEY=... python -m scripts.smoke_decision_readiness
"""
from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen
from urllib.parse import urlencode


def main():
    base = os.environ["PDUFA_REVIEW_BASE_URL"].rstrip("/")
    if base != "https://pdufa-alpaca-enrichment-review.onrender.com":
        raise SystemExit("Refusing non-isolated service")
    key = os.environ["PDUFA_INTERNAL_API_KEY"]
    for stage in ("GEM_JR", "GEM"):
        path = "/api/review/program-decision-readiness/PDUFA-000001?" + urlencode({"stage": stage})
        request = Request(base + path, headers={"x-pdufa-internal-key": key})
        with urlopen(request, timeout=60) as response:
            payload = json.load(response)
        assert payload["programId"] == "PDUFA-000001"
        assert payload["stage"] == stage
        assert payload["decisionReadiness"]["status"] == "NOT_READY"
        assert payload["decisionReadiness"]["tradeCall"] is None
        assert payload["decisionReadiness"]["ordersEnabled"] is False
        assert payload["ordersEnabled"] is False
        assert payload["fsFaChanges"] is False
        assert payload["marketEvidenceReview"]["programId"] == payload["programId"]
        assert payload["marketEvidenceReview"]["exactKey"] == payload["exactKey"]
        assert "verified catalyst" in payload["decisionReadiness"]["missingRequirements"]
        assert "financing and dilution risk review" in payload["decisionReadiness"]["missingRequirements"]
        print(stage + " isolated research readiness: PASS (no trade)")
if __name__ == "__main__":
    main()

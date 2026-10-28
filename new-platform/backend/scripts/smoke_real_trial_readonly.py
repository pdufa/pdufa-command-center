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
from urllib.request import Request, urlopen

DEFAULT_BASE = "https://pdufa-hop-readonly-review.onrender.com"
FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "peak_real_trial_20261027.json"


def get_json(req: Request) -> dict:
    try:
        with urlopen(req, timeout=30) as res:
            if res.status != 200:
                raise RuntimeError(f"Unexpected HTTP status {res.status}")
            payload = json.load(res)
    except HTTPError as exc:
        # Do not echo submitted headers or confidential response bodies.
        raise RuntimeError(f"API returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError("Service unreachable; verify public hostname and network") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected non-object API response")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("PDUFA_HOP_URL", DEFAULT_BASE))
    parser.add_argument("--empty", action="store_true", help="Test only an empty authenticated batch")
    args = parser.parse_args()

    key = os.getenv("PDUFA_INTERNAL_API_KEY")
    if not key:
        print("Missing PDUFA_INTERNAL_API_KEY environment variable", file=sys.stderr)
        return 2
    base = args.base_url.rstrip("/")
    health = get_json(Request(base + "/health", headers={"Accept": "application/json"}))
    if health.get("storage_ready") is not True or health.get("storage_kind") != "postgresql":
        raise RuntimeError("PostgreSQL storage is not ready; no batch submitted")

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

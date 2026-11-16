#!/usr/bin/env python3
"""Read-only isolated scientific L04-L06 staging preflight.

Never starts an assessment, mutates any database or prints credentials.
Requires a separately configured staging HTTPS backend and credentials.
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def normalized_base(value: str) -> str:
    parsed = urlparse(value.rstrip("/"))
    if (
        parsed.scheme != "https" or not parsed.hostname or parsed.username
        or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}
    ):
        raise ValueError("Staging backend must be a plain HTTPS origin")
    return value.rstrip("/")


def main() -> int:
    base = os.getenv("PDUFA_LEVEL456_API_BASE_URL", "").strip()
    key = os.getenv("PDUFA_LEVEL456_INTERNAL_API_KEY", "")
    report = {
        "kind": "SCIENTIFIC_456_STAGING_READ_ONLY_PREFLIGHT",
        "configured": bool(base and key),
        "verified": False,
        "safeToRunResearch": False,
    }
    if not base or not key:
        report["reason"] = "Isolated backend URL or key is not configured"
        print(json.dumps(report, indent=2))
        return 2
    try:
        base = normalized_base(base)
        existing_bases = [
            value.rstrip("/") for value in (
                os.getenv("PDUFA_LEVEL123_API_BASE_URL", ""),
                os.getenv("PDUFA_API_BASE_URL", ""),
            ) if value
        ]
        existing_keys = [
            value for value in (
                os.getenv("PDUFA_LEVEL123_INTERNAL_API_KEY", ""),
                os.getenv("PDUFA_INTERNAL_API_KEY", ""),
            ) if value
        ]
        if base in existing_bases or key in existing_keys:
            raise ValueError("Isolated 456 origin/credential overlaps existing 123 backend")
        version_request = Request(base + "/api/assessment-runtime/version",
                                  headers={"Accept": "application/json"},
                                  method="GET")
        with urlopen(version_request, timeout=20) as response:
            if response.geturl() != version_request.full_url:
                raise ValueError("Unexpected redirect in staging version probe")
            if "application/json" not in response.headers.get("Content-Type", ""):
                raise ValueError("Staging version response is not JSON")
            version = json.loads(response.read(32768))
        if version.get("scientificContracts", {}).get("SCIENTIFIC_1_6") != [4, 5, 6]:
            raise ValueError("Backend does not advertise isolated 456 scientific contract")
        if version.get("scientificContracts", {}).get("SCIENTIFIC_1_3") != [1, 2, 3]:
            raise ValueError("Backend does not preserve original 123 contract")
        if version.get("fdaModel") != "ABSTAIN":
            raise ValueError("Backend does not advertise unvalidated FDA model abstention")
        # A fictitious exact-NCT read checks storage/auth availability without
        # consulting a real trial or creating an assessment.
        probe = Request(base + "/api/assessment-runtime/history/NCT00000000",
                        headers={"Accept": "application/json", "X-Pdufa-Internal-Key": key},
                        method="GET")
        with urlopen(probe, timeout=20) as response:
            if response.geturl() != probe.full_url:
                raise ValueError("Unexpected redirect in staging history probe")
            if "application/json" not in response.headers.get("Content-Type", ""):
                raise ValueError("Staging history response is not JSON")
            history = json.loads(response.read(32768))
        if history.get("nct") != "NCT00000000" or not isinstance(history.get("runs"), list):
            raise ValueError("Staging history identity or storage response is invalid")
        if history["runs"]:
            raise ValueError("Synthetic test identifier unexpectedly has saved records")
        report.update(verified=True, reason="Backend contract, authentication and empty historical read verified",
                      safeToRunResearch=False, nextStep="Opt-in exact-NCT persistence test requires separate authorization")
        print(json.dumps(report, indent=2))
        return 0
    except (ValueError, HTTPError, URLError, OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        # Never include URL/path, response bodies or credentials in errors.
        report["reason"] = type(exc).__name__ + ": staging unavailable or contract not verified"
        print(json.dumps(report, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

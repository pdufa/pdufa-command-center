"""One-shot, read-only loopback HTTP verification against the running staging API.

Runs only when explicitly enabled. Never logs secrets or source identity keys.
"""
import json
import logging
import os
import time
from urllib.request import Request, urlopen
from sqlalchemy import select
from sqlalchemy.orm import Session

LOG = logging.getLogger(__name__)

def verify_live_reconciliation(engine, identity_model):
    key = os.getenv("PDUFA_INTERNAL_API_KEY")
    if not key:
        LOG.warning("PDUFA_RECONCILIATION_SELFTEST status=SKIPPED reason=NO_INTERNAL_KEY")
        return
    try:
        with Session(engine) as session:
            source_key = session.scalars(select(identity_model.source_key).limit(1)).first()
        if not source_key:
            LOG.warning("PDUFA_RECONCILIATION_SELFTEST status=SKIPPED reason=EMPTY_REGISTRY")
            return
        payload = {
            "schemaVersion": 1,
            "kind": "pdufa-reconciliation-review-export",
            "records": [
                {"programKey": "selftest-known", "exactSourceKey": source_key,
                 "status": "confirmed", "evidenceUrl": "https://clinicaltrials.gov/",
                 "reviewedOn": "2026-10-22"},
                {"programKey": "selftest-unmapped",
                 "exactSourceKey": "__PDUFA_SELFTEST_NONEXISTENT_SOURCE_KEY__",
                 "status": "separate", "evidenceUrl": "https://clinicaltrials.gov/",
                 "reviewedOn": "2026-10-22"},
                {"programKey": "selftest-invalid", "exactSourceKey": source_key,
                 "status": "confirmed", "evidenceUrl": "https://[malformed",
                 "reviewedOn": "2026-10-22"}
            ]
        }
        request = Request(
            "http://127.0.0.1:8000/api/reconciliation/validate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json",
                     "X-Pdufa-Internal-Key": key},
            method="POST")
        last_error = None
        for _ in range(8):
            try:
                with urlopen(request, timeout=5) as response:
                    result = json.load(response)
                ok = (result.get("mode") == "READ_ONLY_NO_QUALIFICATION_CHANGES"
                      and result.get("total") == 3
                      and result.get("exactMatches") == 1
                      and result.get("unmapped") == 1
                      and result.get("invalid") == 1)
                LOG.warning(
                    "PDUFA_RECONCILIATION_SELFTEST status=%s http=200 exact=%s unmapped=%s invalid=%s",
                    "PASS" if ok else "FAIL", result.get("exactMatches"),
                    result.get("unmapped"), result.get("invalid"))
                return
            except Exception as exc:
                last_error = type(exc).__name__
                time.sleep(2)
        LOG.error("PDUFA_RECONCILIATION_SELFTEST status=FAIL error_type=%s", last_error)
    except Exception as exc:
        LOG.exception("PDUFA_RECONCILIATION_SELFTEST status=FAIL error_type=%s", type(exc).__name__)

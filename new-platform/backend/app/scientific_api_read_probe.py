"""Read-only loopback acceptance check for the isolated scientific service.

Uses the existing environment-held key without exporting it. No new HTTP
endpoint, imports, batch submissions, scientific grades, or database writes.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

LOG = logging.getLogger(__name__)
SERVICE_ID = "srv-dbehn9fb9u1s739ok5vg"
NCT_ID = "NCT02142738"
BASE_URL = "http://127.0.0.1:8000"
TRIAL_PATH = "/api/scientific-assessment?exact_id=TRIAL%7C" + NCT_ID
MAX_BYTES = 2_100_000


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A credential must never follow even a loopback redirect.
        return None


def _request_json(path: str, key: str | None) -> tuple[int, dict]:
    if not path.startswith("/api/scientific-assessment"):
        raise ValueError("Unexpected probe path")
    headers = {"Accept": "application/json"}
    if key is not None:
        headers["x-pdufa-internal-key"] = key
    request = Request(BASE_URL + path, headers=headers, method="GET")
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(request, timeout=12) as response:
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError("Probe response too large")
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("Unexpected probe response")
            return response.status, payload
    except HTTPError as error:
        # Never parse/log an error response, URL, credential or exception body.
        status = error.code
        error.close()
        return status, {}


def check_api(key: str, request_json=_request_json) -> dict:
    """Require actual 401/200 HTTP responses plus exact archive/packet identity."""
    from .scientific_review_packet import check_packet_integrity

    if request_json(TRIAL_PATH, None)[0] != 401:
        raise ValueError("Missing credential accepted")
    # Deliberately differs even if the configured key equals a test string.
    if request_json(TRIAL_PATH, key + "-invalid")[0] != 401:
        raise ValueError("Wrong credential accepted")
    status, storage = request_json("/api/scientific-assessment/storage-status", key)
    if (status != 200 or storage.get("storageReady") is not True
            or storage.get("trialTablePresent") is not True
            or type(storage.get("storedTrialCount")) is not int
            or storage["storedTrialCount"] < 1):
        raise ValueError("Persistent archive unavailable")
    status, batches = request_json("/api/scientific-assessment/batches", key)
    if status != 200 or not isinstance(batches.get("jobs"), list):
        raise ValueError("Batch history unavailable")
    status, trial = request_json(TRIAL_PATH, key)
    grades = trial.get("readinessGrades") or {}
    assessment = trial.get("assessment") or {}
    if (status != 200 or trial.get("exactId") != "TRIAL|" + NCT_ID
            or trial.get("registryEvidenceStatus") != "source_record_loaded"
            or assessment.get("status") != "insufficient_evidence"
            or assessment.get("overall_score") is not None
            or grades.get("analysisReadiness", {}).get("readyForFullScientificConclusion") is not False
            or grades.get("analysisReadiness", {}).get("verdict") != "NOT_READY"
            or grades.get("scientificReluctance", {}).get("grade") != "F"
            or "scientificScore" not in grades or grades["scientificScore"] is not None
            or "fdaApprovalProbability" not in grades or grades["fdaApprovalProbability"] is not None):
        raise ValueError("Archived assessment or evidence boundary invalid")
    status, pilot = request_json("/api/scientific-assessment/pilot/keynote024", key)
    dossier = pilot.get("dossier") or {}
    domains = dossier.get("domains") or {}
    if (status != 200 or dossier.get("nct_id") != NCT_ID or len(domains) != 8
            or dossier.get("assessment_status") != "incomplete"
            or dossier.get("overall_score") is not None
            or any(domain.get("score") is not None for domain in domains.values())
            or pilot.get("researchOnly") is not True
            or pilot.get("scoringModified") is not False
            or pilot.get("qualificationPresetsModified") is not False):
        raise ValueError("Pilot identity or research boundary invalid")
    status, packet = request_json(
        "/api/scientific-assessment/review-packet/" + NCT_ID, key,
    )
    if (status != 200 or packet.get("nctId") != NCT_ID
            or not check_packet_integrity(packet)
            or "scientificConclusion" not in packet or packet["scientificConclusion"] is not None
            or "fdaApprovalProbability" not in packet or packet["fdaApprovalProbability"] is not None):
        raise ValueError("Review packet identity or integrity invalid")
    return {"checks": 7, "stored_trials": storage["storedTrialCount"],
            "batch_jobs": len(batches["jobs"]), "domains": len(domains)}


def run_probe(*, startup_attempts: int = 20, startup_interval: float = 0.5) -> bool:
    """Wait only for listener startup; all actual checks run exactly once."""
    key = os.getenv("PDUFA_INTERNAL_API_KEY", "")
    try:
        for attempt in range(startup_attempts):
            try:
                # Read-only unauthenticated request waits for the listener.
                _request_json(TRIAL_PATH, None)
                break
            except URLError:
                if attempt == startup_attempts - 1:
                    raise
                time.sleep(startup_interval)
        else:
            raise ValueError("No startup attempts configured")
        result = check_api(key)
        LOG.warning(
            "SCIENTIFIC_API_READ_PROBE status=PASS checks=%d stored_trials=%d "
            "batch_jobs=%d domains=%d read_only=True scores_assigned=False",
            result["checks"], result["stored_trials"], result["batch_jobs"], result["domains"],
        )
        return True
    except Exception as error:
        LOG.error("SCIENTIFIC_API_READ_PROBE status=FAIL error_type=%s read_only=True",
                  type(error).__name__)
        return False


def launch_if_isolated_review() -> None:
    from . import main
    if (os.getenv("RENDER_SERVICE_ID") == SERVICE_ID
            and os.getenv("PDUFA_MIGRATION_READ_ONLY", "").lower() in {"1", "true", "yes"}
            and os.getenv("PDUFA_INTERNAL_API_KEY")
            and main.DATABASE_URL.startswith("postgresql+psycopg://")
            and main._DB_STATE.get("available")
            and "PYTEST_CURRENT_TEST" not in os.environ):
        threading.Thread(target=run_probe, name="scientific-api-read-probe", daemon=True).start()

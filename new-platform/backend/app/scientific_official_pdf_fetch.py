"""Bounded, pinned-source document acquisition for the historical KEYNOTE-024 pilot.

Unlike arbitrary URL fetchers, the endpoint caller cannot supply a URL or host.
It retrieves at most one official public PDF per operator action, over TLS with
redirects forbidden and a strict byte budget. No scientific conclusions,
reviewer-role promotion, or score calculation are performed.
"""
from __future__ import annotations

import base64
import hashlib
from typing import Literal

import requests

from .scientific_reconciliation_worklist import (
    FDA_2016_APPROVAL, PROTOCOL_SAP, GERMAN_REGULATOR_CSR,
)
from .scientific_source_documents import (
    MAX_PDF_BYTES, capture_document, read_document_manifest,
)

PILOT_NCT = "NCT02142738"
OFFICIAL_SOURCES = {
    "protocol": {
        "gateId": "protocol_sap",
        "sourceType": "protocol_sap",
        "sourceUrl": PROTOCOL_SAP,
        "documentDateNote": (
            "This posted protocol is dated December 20, 2017, after the 2016 "
            "interim analysis. It is not proof of the prospectively locked 2016 SAP."
        ),
    },
    "fda": {
        "gateId": "official_regulatory",
        "sourceType": "official_agency_document",
        "sourceUrl": FDA_2016_APPROVAL,
        "documentDateNote": (
            "The FDA action letter documents both supplements S-8 and S-12. "
            "The first-line high PD-L1 indication corresponds to S-12."
        ),
    },
    "csr": {
        "gateId": "protocol_sap",
        "sourceType": "clinical_study_report",
        "sourceUrl": GERMAN_REGULATOR_CSR,
        "documentDateNote": (
            "The regulator-hosted retrospective clinical study report lists "
            "P024-03 as finalized 28 Jan 2016 and P024-06 on 29 Jul 2016. "
            "This is not a signed contemporaneous 2016 SAP."
        ),
    },
}


class OfficialSourceUnavailable(Exception):
    """No document was archived. Safe diagnostic (does not reveal URLs/tokens)."""


def fetch_official_pdf(source: Literal["protocol", "fda", "csr"]) -> bytes:
    """Fetch only a hard-coded original HTTPS PDF, not an arbitrary caller URL."""
    selected = OFFICIAL_SOURCES.get(source)
    if selected is None:
        raise ValueError("Unknown official source")
    # The source dict above is static, reviewed source code, not client input.
    url = selected["sourceUrl"]
    if not url.startswith("https://"):
        raise OfficialSourceUnavailable("Pinned original source requires HTTPS")
    response = None
    try:
        response = requests.get(
            url,
            headers={
                "Accept": "application/pdf",
                "User-Agent": "PDUFA-Scientific-Review/1.0 (source archival)",
            },
            timeout=(5, 15),
            allow_redirects=False,
            stream=True,
        )
        if response.status_code != 200:
            raise OfficialSourceUnavailable("Official PDF host did not return HTTP 200")
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type not in ("application/pdf", "application/octet-stream"):
            raise OfficialSourceUnavailable("Official host did not return PDF content")
        declared_length = response.headers.get("Content-Length")
        if declared_length is not None:
            try:
                length = int(declared_length)
            except ValueError:
                raise OfficialSourceUnavailable("Unusable official response length") from None
            if not 32 <= length <= MAX_PDF_BYTES:
                raise OfficialSourceUnavailable("Official source PDF exceeds archival limit")

        pieces = []
        count = 0
        for chunk in response.iter_content(chunk_size=65536):
            if not chunk:
                continue
            count += len(chunk)
            if count > MAX_PDF_BYTES:
                raise OfficialSourceUnavailable("Official source PDF exceeds archival limit")
            pieces.append(chunk)
        raw = b"".join(pieces)
        if len(raw) < 32:
            raise OfficialSourceUnavailable("Official source PDF was empty or truncated")
        if declared_length is not None and len(raw) != length:
            raise OfficialSourceUnavailable("Official PDF byte length does not match response")
        if not raw.startswith(b"%PDF-") or b"%%EOF" not in raw[-1024:]:
            raise OfficialSourceUnavailable("Official source returned invalid PDF boundaries")
        return raw
    except requests.exceptions.RequestException:
        raise OfficialSourceUnavailable("Original PDF host connection was unavailable") from None
    finally:
        if response is not None:
            response.close()


def archive_official_pdf(
    nct_id: str, source: Literal["protocol", "fda", "csr"]
) -> dict:
    """Store a pinned-source PDF as unreviewed bytes; repeat import is idempotent."""
    if nct_id != PILOT_NCT:
        raise ValueError("Pinned PDF acquisition is restricted to the archived pilot")
    selected = OFFICIAL_SOURCES.get(source)
    if selected is None:
        raise ValueError("Unknown official source")
    manifest = read_document_manifest(PILOT_NCT)
    for row in manifest["documents"]:
        if (row["gateId"] == selected["gateId"]
                and row["sourceUrl"] == selected["sourceUrl"]):
            return {
                **row, "alreadyArchived": True,
                "documentDateNote": selected["documentDateNote"],
                "scientificallyVerified": False,
                "independentReviewRequired": True,
            }

    raw = fetch_official_pdf(source)
    meta = capture_document(PILOT_NCT, {
        "gateId": selected["gateId"],
        "sourceType": selected["sourceType"],
        "sourceUrl": selected["sourceUrl"],
        "sha256": hashlib.sha256(raw).hexdigest(),
        "contentBase64": base64.b64encode(raw).decode("ascii"),
        "capturedBy": "Verified Google operator: pinned source",
    })
    if meta["documentContentScientificallyVerified"] is not False:
        raise RuntimeError("Scientific PDF archive unexpectedly promoted source verification")
    return {
        **meta, "alreadyArchived": False,
        "documentDateNote": selected["documentDateNote"],
        "scientificallyVerified": False,
        "independentReviewRequired": True,
    }



def bootstrap_pinned_pilot_sources() -> None:
    """One deployment opt-in: capture each pinned original once without blocking health.

    This function is called only from the isolated service's startup thread.
    Repeat deployments are idempotent; failures preserve the existing archive.
    """
    import logging

    logger = logging.getLogger(__name__)
    for source in ("protocol", "fda", "csr"):
        try:
            receipt = archive_official_pdf(PILOT_NCT, source)
            if (receipt["scientificallyVerified"] is not False
                    or receipt["independentReviewRequired"] is not True):
                raise RuntimeError("Unsafe scientific review flag in PDF receipt")
            logger.warning(
                "SCIENTIFIC_PINNED_SOURCE_CAPTURE source=%s status=%s "
                "bytes=%d scientific_verification=False",
                source,
                "ALREADY_ARCHIVED" if receipt["alreadyArchived"] else "CAPTURED",
                receipt["byteLength"],
            )
        except Exception as exc:
            # Original source could be unavailable, oversized, or already
            # concurrently captured. Never write a false source or score.
            logger.warning(
                "SCIENTIFIC_PINNED_SOURCE_CAPTURE source=%s status=UNAVAILABLE "
                "error_type=%s scientific_verification=False",
                source, type(exc).__name__,
            )

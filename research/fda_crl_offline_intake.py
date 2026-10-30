"""Offline FDA CRL PDF intake. Research-only; never certifies source authenticity.

Requires caller-provided original PDF bytes and an independently documented
public-availability date. Hashing proves byte identity, not FDA provenance.
"""
from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path


def inspect_fda_pdf(path: str | Path, *, application: str, action_date: str,
                    public_available_on: str | None = None,
                    source_url: str | None = None) -> dict:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".pdf":
        raise ValueError("Expected PDF file")
    if not application.startswith(("NDA", "BLA")) or not application[3:].isdigit():
        raise ValueError("Application must be NDA/BLA followed by digits")
    action = date.fromisoformat(action_date)
    public = date.fromisoformat(public_available_on) if public_available_on else None
    if public is not None and public < action:
        raise ValueError("Public availability cannot precede FDA action")
    data = path.read_bytes()
    if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:]:
        raise ValueError("PDF header or EOF missing; reject partial/corrupt file")
    if len(data) > 100_000_000:
        raise ValueError("PDF exceeds intake limit")
    return {
        "schema_version": "fda-crl-offline-intake-v1",
        "application": application,
        "action_date": action.isoformat(),
        "public_available_on_claimed": public.isoformat() if public else None,
        "source_url_claimed": source_url,
        "file_name": path.name,
        "file_size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "original_bytes_retained_at_input_path": True,
        "fda_authenticity_verified": False,
        "public_availability_independently_verified": False,
        "independently_reviewed": False,
        "eligible_for_predecision_science": False,
        "eligible_for_predictive_training": False,
        "trading_authorized": False,
        "status": "HASHED_UNVERIFIED_SOURCE",
    }

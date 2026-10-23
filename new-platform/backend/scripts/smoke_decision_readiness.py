"""Read-only smoke assertions for the isolated investment research endpoint.

Usage (only against the isolated service):
 PDUFA_REVIEW_BASE_URL=https://... PDUFA_INTERNAL_API_KEY=... python -m scripts.smoke_decision_readiness
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.readiness_smoke import REVIEW_URL, check_program


def main():
    base = os.environ["PDUFA_REVIEW_BASE_URL"].rstrip("/")
    if base != REVIEW_URL:
        raise SystemExit("Refusing non-isolated service")
    key = os.environ["PDUFA_INTERNAL_API_KEY"]
    logging.basicConfig(level=logging.WARNING)
    check_program(base, key, "PDUFA-000001")
if __name__ == "__main__":
    main()

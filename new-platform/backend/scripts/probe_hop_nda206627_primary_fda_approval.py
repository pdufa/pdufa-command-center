"""Fetch ONE fixed official FDA original approval PDF and preserve provenance.

This is a research-only PDF/source inspection for the known original
NDA206627 discrepancy, never automatic review-cycle outcome adjudication.
"""
from __future__ import annotations

import argparse
import json
import ssl
from pathlib import Path
from urllib.request import Request, urlopen

from app.hop_fda_nda206627_primary_source import (
    MAX_PDF_BYTES, PAGES_TO_OBSERVE, URL, inspect_nda206627_original_pdf,
)


def retrieve_exact_official_pdf() -> bytes:
    req = Request(
        URL,
        headers={"User-Agent": "PDUFA-Source-Research/1.0 (FDA public PDF evidence)"},
        method="GET",
    )
    with urlopen(req, timeout=35, context=ssl.create_default_context()) as response:
        if response.geturl() != URL:
            raise ValueError("Unexpected FDA PDF redirect; refuse alternate source")
        content_type = response.headers.get("Content-Type", "")
        if not content_type.lower().startswith("application/pdf"):
            raise ValueError("FDA primary source did not return application/pdf")
        length = response.headers.get("Content-Length")
        if length and int(length) > MAX_PDF_BYTES:
            raise ValueError("FDA source PDF exceeds research resource cap")
        content = response.read(MAX_PDF_BYTES + 1)
    if len(content) > MAX_PDF_BYTES:
        raise ValueError("Source PDF exceeds size cap")
    return content


def main() -> int:
    p = argparse.ArgumentParser(
        description="Observe ONE actual original NDA FDA approval PDF, not decide outcomes"
    )
    p.add_argument("--output-json", type=Path, required=True)
    args = p.parse_args()
    from io import BytesIO
    from pypdf import PdfReader

    body = retrieve_exact_official_pdf()
    reader = PdfReader(BytesIO(body), strict=True)
    if len(reader.pages) < 4 or len(reader.pages) > 100:
        raise ValueError("Unexpected official FDA package page count")
    page_text = {i: reader.pages[i].extract_text() or ""
                 for i in PAGES_TO_OBSERVE}
    result = inspect_nda206627_original_pdf(
        body, page_text, page_count=len(reader.pages)
    )
    if not result["all_target_source_text_checks_passed"]:
        raise ValueError(
            "Official PDF retrieved but original NDA approval text did not reconcile"
        )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0  # PDF evidence consistency only; scientific release remains BLOCKED.


if __name__ == "__main__":
    raise SystemExit(main())

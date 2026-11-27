"""Bounded actual FDA source PDF page-token sampling, research-only.

Selects a bounded hash-sorted page *batch* from the pinned private
identity-gap packet collection, re-fetches official PDFs, verifies exact
historical SHA-256 bytes and extracts at most 40 pages per source. Detailed
page-location hints stay PRIVATE. Only aggregate counts are uploaded.

This has no regulatory outcome adjudication, no model labels, and no trade.
"""
from __future__ import annotations

import argparse
import json
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.hop_fda_pdf_page_candidate_sampling import (
    MAX_PDF_BYTES, aggregate_sample, inspect_candidate_pages,
    select_pinned_pdf_sample,
)
from app.hop_fda_visual_page_review import (
    render_private_nontext_pages, render_counts_only,
)


class _RejectRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("FDA source PDF redirect not accepted")


def retrieve_exact_fda_crl_pdf(url: str) -> bytes:
    opener = build_opener(_RejectRedirect())
    request = Request(
        url, headers={"Accept": "application/pdf",
                      "User-Agent": "PDUFA-official-FDA-page-research/1.0"},
        method="GET",
    )
    with opener.open(request, timeout=25) as response:
        if response.geturl() != url or response.status != 200:
            raise OSError("Official FDA source URL did not return exact HTTP 200")
        kind = response.headers.get_content_type()
        if kind not in ("application/pdf", "application/octet-stream"):
            raise OSError("Official FDA source returned non-PDF content type")
        value = response.read(MAX_PDF_BYTES + 1)
    if len(value) > MAX_PDF_BYTES:
        raise OSError("Official source exceeds bounded PDF size")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sample previous official FDA PDF hashes for unverified page navigation hints"
    )
    parser.add_argument("--private-enriched-packets-json", type=Path, required=True)
    parser.add_argument("--private-pdf-page-hints-json", type=Path, required=True)
    parser.add_argument("--public-aggregate-json", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--offset", type=int, default=0,
                        help="Zero-based offset in sorted pinned PDF hashes")
    parser.add_argument("--private-visual-image-dir", type=Path,
                        help="Private PNG images for pages with no extractable text")
    parser.add_argument("--private-visual-manifest-json", type=Path,
                        help="Private-only page mapping and rendered PNG fingerprints")
    args = parser.parse_args()
    if bool(args.private_visual_image_dir) != bool(args.private_visual_manifest_json):
        raise ValueError("Both private visual output paths must be supplied together")
    if args.private_visual_image_dir:
        image_dir = args.private_visual_image_dir.resolve()
        private_manifest = args.private_visual_manifest_json.resolve()
        public_dir = args.public_aggregate_json.resolve().parent
        if (image_dir == public_dir or public_dir in image_dir.parents
                or image_dir in public_dir.parents or private_manifest == args.public_aggregate_json.resolve()
                or public_dir in private_manifest.parents
                or private_manifest == args.private_enriched_packets_json.resolve()
                or private_manifest == args.private_pdf_page_hints_json.resolve()):
            raise ValueError("Private FDA page bitmaps cannot overlap public artifact paths")
    destinations = [
        args.private_enriched_packets_json.resolve(),
        args.private_pdf_page_hints_json.resolve(),
        args.public_aggregate_json.resolve(),
    ]
    if len(set(destinations)) != len(destinations):
        raise ValueError("Private FDA source mapping and public audit destinations must differ")
    from pypdf import PdfReader

    source = json.loads(args.private_enriched_packets_json.read_text(encoding="utf-8"))
    selected, plan = select_pinned_pdf_sample(
        source, limit=args.limit, offset=args.offset
    )
    observed = []
    unavailable = 0
    rendered_page_records = []
    for item in selected:
        try:
            pdf = retrieve_exact_fda_crl_pdf(item["official_fda_pdf_url"])
        except (HTTPError, URLError, TimeoutError, OSError, ValueError):
            unavailable += 1
            continue
        # HASH MISMATCH is a hard error; do not permit substituted source
        # bytes or a network content change to be counted as the FDA baseline.
        import hashlib
        if hashlib.sha256(pdf).hexdigest() != item["historical_pdf_sha256"]:
            raise ValueError("FDA original full-PDF SHA256 does not match pinned source")
        try:
            reader = PdfReader(BytesIO(pdf), strict=False)
            page_observation = inspect_candidate_pages(
                item, pdf, page_count=len(reader.pages),
                extract_text=lambda idx: reader.pages[idx].extract_text() or "",
            )
            observed.append(page_observation)
        except (ValueError, TypeError, IndexError, OSError) as exc:
            # Page parsing failures are not verified pages and must be visible
            # as incompletes rather than model-released decisions.
            if isinstance(exc, ValueError) and "SHA256" in str(exc):
                raise
            unavailable += 1
            continue
        # Rendering errors must FAIL the audit, not be interpreted as a blank
        # PDF or counted as regulatory negatives.
        if args.private_visual_image_dir:
            rendered_page_records.extend(render_private_nontext_pages(
                pdf, page_observation,
                private_image_dir=args.private_visual_image_dir,
            ))
    summary = aggregate_sample(plan, observed, fetch_failures=unavailable)
    if args.private_visual_image_dir:
        summary["private_visual_render_count_audit"] = render_counts_only(
            observed, rendered_page_records,
            requested_documents=plan["selected_unique_pdf_documents"],
        )
        args.private_visual_manifest_json.parent.mkdir(parents=True, exist_ok=True)
        args.private_visual_manifest_json.write_text(
            json.dumps(rendered_page_records, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    args.private_pdf_page_hints_json.parent.mkdir(parents=True, exist_ok=True)
    args.public_aggregate_json.parent.mkdir(parents=True, exist_ok=True)
    args.private_pdf_page_hints_json.write_text(
        json.dumps(observed, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    args.public_aggregate_json.write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True, indent=2))
    return 0  # Page navigation evidence, NOT FDA action review-cycle clearance.


if __name__ == "__main__":
    raise SystemExit(main())

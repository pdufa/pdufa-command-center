"""Source-faithful SEC filing index rows; an index entry is NOT a financing closing."""
from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path

FIELDS = (
    "ticker", "cik10", "filing_type", "category", "filed_at",
    "accession_number", "filing_url", "source_index_url",
    "source_index_sha256", "evidence_scope",
)
FORMS = {
    "8-K", "8-K/A", "6-K", "6-K/A", "10-Q", "10-Q/A",
    "10-K", "10-K/A", "S-1", "S-1/A", "S-3", "S-3/A",
    "F-1", "F-1/A", "F-3", "F-3/A", "424B5", "424B2",
    "424B3", "POS AM",
}
SOURCE_SCOPE = "SEC_INDEX_METADATA_ONLY_NOT_FINANCING_CLOSURE"


def rows_from_submissions(*, ticker, cik10, recent, index_sha256, as_of=None, limit=15):
    """Use only the matching SEC CIK's schema-validated submissions JSON.

    SEC form names determine Base versus Amendment. A 424B5 prospectus
    supplement is not automatically an /A form or a funded transaction.
    """
    if not (re.fullmatch(r"\\d{10}", cik10 or "") and
            re.fullmatch(r"[A-Z][A-Z0-9.\\-]{0,14}", ticker or "") and
            re.fullmatch(r"[a-f0-9]{64}", index_sha256 or "")):
        raise ValueError("A verified issuer index identity/hash is required")
    if not isinstance(limit, int) or limit < 1:
        raise ValueError("Invalid index review limit")
    limit = min(limit, 50)
    cutoff = (as_of or date.today()).isoformat()
    output = []
    for form, filed, accession, document in zip(
            recent["form"], recent["filingDate"], recent["accessionNumber"],
            recent["primaryDocument"]):
        if form not in FORMS or filed > cutoff:
            continue
        if not re.fullmatch(r"\\d{10}-\\d{2}-\\d{6}", accession):
            continue
        base = ("https://www.sec.gov/Archives/edgar/data/" + str(int(cik10))
                + "/" + accession.replace("-", "") + "/")
        if re.fullmatch(r"[A-Za-z0-9_.-]+", document or "") and document not in {".", ".."}:
            link = base + document
        else:
            # The accession is verified SEC metadata even if its primary
            # document is absent. Do not fabricate a file URL.
            link = base
        output.append({
            "ticker": ticker, "cik10": cik10, "filing_type": form,
            "category": "AMENDMENT" if form.endswith("/A") or form == "POS AM" else "BASE",
            "filed_at": filed, "accession_number": accession,
            "filing_url": link,
            "source_index_url": "https://data.sec.gov/submissions/CIK" + cik10 + ".json",
            "source_index_sha256": index_sha256,
            "evidence_scope": SOURCE_SCOPE,
        })
        if len(output) >= limit:
            break
    return output


def write_rows(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

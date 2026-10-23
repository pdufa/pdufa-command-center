"""Offline integrity checks for curated approved-drug sales ledger.

This does not verify the underlying SEC/issuer disclosure amounts.
"""
import csv
import datetime
import math
import re
from pathlib import Path
from urllib.parse import urlparse

PATH = Path("data/approved_drug_sales_verified.csv")
COLUMNS = [
    "company", "ticker", "approved_product", "indication", "period",
    "individual_sales", "currency", "company_net_sales", "partner_sales",
    "royalties", "combined_total", "source_url", "verified_on",
    "disclosure_status",
]
ALLOWED_DOMAINS = {"www.sec.gov", "sec.gov", "investors.vrtx.com", "ir.biocryst.com"}


def validate(path=PATH):
    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != COLUMNS:
            raise ValueError("Financial ledger schema mismatch")
        seen = set()
        count = 0
        known_company_by_ticker = {}
        for line, row in enumerate(reader, start=2):
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"Line {line}: invalid number of fields")
            key = tuple(row[k].strip().upper() for k in ("ticker", "approved_product", "period"))
            if not all(key) or key in seen:
                raise ValueError(f"Line {line}: missing or duplicate ticker/product/period")
            seen.add(key)
            company = row["company"].strip().casefold()
            ticker = key[0]
            if ticker in known_company_by_ticker and known_company_by_ticker[ticker] != company:
                raise ValueError(f"Line {line}: ticker maps to multiple company names")
            known_company_by_ticker[ticker] = company
            if any(not row[k].strip() for k in ("company", "indication", "disclosure_status")):
                raise ValueError(f"Line {line}: missing required metadata")
            # Require a precise reporting window; do not mix fiscal-year
            # totals with partial-year periods under ambiguous labels.
            period = row["period"].strip().upper()
            if not re.fullmatch(r"(?:FY|H1|H2|Q[1-4]|9M)20[0-9]{2}", period):
                raise ValueError(f"Line {line}: unsupported reporting period")
            if row["currency"] != "USD millions":
                raise ValueError(f"Line {line}: unsupported units")
            source = urlparse(row["source_url"])
            if source.scheme != "https" or source.hostname not in ALLOWED_DOMAINS:
                raise ValueError(f"Line {line}: unapproved disclosure source")
            datetime.date.fromisoformat(row["verified_on"])
            if not row["individual_sales"].strip():
                raise ValueError(f"Line {line}: missing individual sales")
            for field in ("individual_sales", "company_net_sales", "partner_sales", "royalties", "combined_total"):
                if row[field].strip():
                    value = float(row[field])
                    if not math.isfinite(value) or value < 0 or value >= 1e9:
                        raise ValueError(f"Line {line}: invalid {field}")
            count += 1
    print(f"Financial ledger integrity PASS: {count} distinct rows (source amounts not independently verified)")
    return count


if __name__ == "__main__":
    validate()

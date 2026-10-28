"""Read-only acquisition of an FDA CRL bulk source snapshot as a CI artifact."""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

from app.hop_openfda_snapshot import build_crl_snapshot
from app.hop_source_receipts import SourceReceipts

MANIFEST_URL = "https://api.fda.gov/download.json"
MAX_MANIFEST_BYTES = 8_000_000
MAX_PARTITION_BYTES = 12_000_000


def download(url: str, limit: int) -> bytes:
    with urlopen(Request(url, headers={"User-Agent": "PDUFA-HOP-research-audit/1.0"}),
                 timeout=45) as response:
        content = response.read(limit + 1)
    if len(content) > limit:
        raise ValueError("FDA source download exceeds configured byte limit")
    return content


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--retain-originals-dir", help="Opt-in new directory for exact FDA manifest/archive bytes")
    args = parser.parse_args()
    receipts = SourceReceipts(args.retain_originals_dir, "CRL") if args.retain_originals_dir else None
    fetch_source = receipts.fetch if receipts is not None else download
    manifest = json.loads(fetch_source(MANIFEST_URL, MAX_MANIFEST_BYTES))
    parts = manifest["results"]["transparency"]["crl"]["partitions"]
    archives = {part["file"]: fetch_source(part["file"], MAX_PARTITION_BYTES) for part in parts}
    snapshot, audit = build_crl_snapshot(manifest, archives, date.today())
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "fda_crl_published_quarantined.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "fda_crl_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if receipts is not None:
        receipts.retain(audit["archive_sha256_by_url"])
    print(json.dumps({
        "status": audit["status"],
        "export_date": audit["source_export_date"],
        "published_letter_records": audit["published_letter_records"],
        "quarantined_records": audit["quarantined_records"],
        "model_eligible": audit["model_eligible"],
        "letter_types": audit["letter_types"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

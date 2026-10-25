"""Download approved-product Drugs@FDA source as a quarantined research artifact."""
from __future__ import annotations
import argparse
from datetime import date
import json
from pathlib import Path
from urllib.request import Request, urlopen
from app.hop_drugsfda_snapshot import stage_drugsfda_manifest

MANIFEST = "https://api.fda.gov/download.json"


def fetch(url: str, max_bytes: int) -> bytes:
    with urlopen(Request(url, headers={"User-Agent": "PDUFA-HOP-source-research/1.0"}), timeout=60) as response:
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("source archive exceeds download size limit")
    return data


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", required=True)
    args = p.parse_args()
    manifest = json.loads(fetch(MANIFEST, 8_000_000))
    parts = manifest["results"]["drug"]["drugsfda"]["partitions"]
    archives = {item["file"]: fetch(item["file"], 22_000_000) for item in parts}
    snapshot, audit = stage_drugsfda_manifest(manifest, archives, date.today())
    directory = Path(args.output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "drugsfda_approved_registry_quarantined.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (directory / "drugsfda_approved_registry_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "export_date": audit["source_export_date"],
        "source_application_records": audit["source_application_records"],
        "quarantined_application_records": audit["quarantined_application_records"],
        "application_number_prefixes": audit["application_number_prefixes"],
        "model_eligible_records": audit["model_eligible_records"],
        "status": audit["status"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

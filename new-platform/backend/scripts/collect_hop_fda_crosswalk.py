"""Read-only join of two official FDA bulk archives; never generates model labels."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
from urllib.request import Request, urlopen

from app.hop_openfda_snapshot import build_crl_snapshot
from app.hop_drugsfda_snapshot import stage_drugsfda_manifest
from app.hop_fda_application_crosswalk import crosswalk_public_fda_sources

MANIFEST_URL = "https://api.fda.gov/download.json"


def fetch(url: str, max_bytes: int) -> bytes:
    with urlopen(Request(url, headers={"User-Agent": "PDUFA-HOP-identity-reconciliation/1.0"}),
                 timeout=60) as response:
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("FDA bulk archive download exceeds limit")
    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    manifest = json.loads(fetch(MANIFEST_URL, 8_000_000))
    crl_parts = manifest["results"]["transparency"]["crl"]["partitions"]
    drug_parts = manifest["results"]["drug"]["drugsfda"]["partitions"]
    letters, letter_audit = build_crl_snapshot(
        manifest,
        {p["file"]: fetch(p["file"], 12_000_000) for p in crl_parts},
        date.today(),
    )
    registry, registry_audit = stage_drugsfda_manifest(
        manifest,
        {p["file"]: fetch(p["file"], 22_000_000) for p in drug_parts},
        date.today(),
    )
    crosswalk, audit = crosswalk_public_fda_sources(letters, registry)
    audit["source_letter_archive_sha256"] = letter_audit["archive_sha256_by_url"]
    audit["source_registry_archive_sha256"] = registry_audit["source_archive_sha256"]
    dest = Path(args.output_dir)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "fda_crl_registry_identity_crosswalk.json").write_text(
        json.dumps(crosswalk, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (dest / "fda_crl_registry_identity_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": audit["status"],
        "published_letter_records": audit["published_letter_records"],
        "approved_registry_source_application_records": audit["approved_registry_source_application_records"],
        "identity_link_status_counts": audit["identity_link_status_counts"],
        "model_eligible_records": audit["model_eligible_records"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

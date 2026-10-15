"""Run one SEC/FDA section; publish separate research snapshots for its tables."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in ("", None):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.source_verification import (
    FIELDS, STATES, VERSION, digest, read_rows, scope_hash, summary, verify_source,
)

SECTIONS = {
    "SEC_BASE": ("SEC", "FULL"),
    "SEC_AMENDMENTS": ("SEC", "DELTA"),
    "FDA_BASE": ("FDA", "FULL"),
    "FDA_AMENDMENTS": ("FDA", "DELTA"),
}
SNAPSHOTS = "filings_section_scans"
EXTENSION_FIELDS = ("event_key", "ticker", "extension_sequence",
                    "prior_pdufa_date", "current_pdufa_date", "extension_detected_at")


def section_config(section):
    if section not in SECTIONS:
        raise ValueError("Unsupported filings section")
    return SECTIONS[section]


def timestamp(value):
    when = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if when.tzinfo is None:
        raise ValueError("Scan timestamp needs a timezone")
    return when


def overlay_findings(saved, fresh):
    """Replace only the same claim when the new observation is newer."""
    indexed = {(r.get("event_key"), r.get("category"), r.get("claim")): r for r in saved}
    for row in fresh:
        key = (row.get("event_key"), row.get("category"), row.get("claim"))
        old = indexed.get(key)
        if not old or not old.get("checked_at") or timestamp(row["checked_at"]) >= timestamp(old["checked_at"]):
            indexed[key] = row
    return list(indexed.values())


def extension_observations(findings, history, detected_at):
    """Preserve first detection, including extensions found by earlier manual scans."""
    indexed = {}
    for row in history:
        key = (row.get("event_key"), row.get("prior_pdufa_date"), row.get("current_pdufa_date"))
        if not all(key):
            continue
        previous = indexed.get(key)
        if previous is None or (row.get("extension_detected_at") and
                row["extension_detected_at"] < previous.get("extension_detected_at", "~")):
            indexed[key] = {k: row.get(k, "") for k in EXTENSION_FIELDS}
    for row in findings:
        found = re.fullmatch(r"Explicit dated FDA PDUFA extension supersedes (\d{4}-\d{2}-\d{2})",
                             row.get("reason", ""))
        if row.get("claim") != "PDUFA_TARGET" or row.get("verification_status") != "VERIFIED" or not found:
            continue
        key = (row["event_key"], found[1], row.get("observed", ""))
        if key in indexed or not key[2] or key[1] == key[2]:
            continue
        indexed[key] = dict(zip(EXTENSION_FIELDS, (
            key[0], row["ticker"], "1", key[1], key[2], detected_at)))
    return list(indexed.values())


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_snapshot(folder, data_dir, section):
    """Reject stale scope, missing evidence, altered hashes and incomplete ledgers."""
    source, mode = section_config(section)
    report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
    events = read_rows(data_dir / "pdufa_candidates.csv")
    companies = read_rows(data_dir / "company_registry.csv")
    if (report.get("schema_version") != 1 or report.get("verification_version") != VERSION
            or report.get("section") != section or report.get("source") != source
            or report.get("scan_mode") != mode
            or report.get("verification_scope_sha256") != scope_hash(events, companies)):
        raise ValueError("Section snapshot does not match the current candidate scope")
    timestamp(report["finished_at"])
    names = {source.lower() + "_verification.csv"}
    names.add("sec_filing_watch.csv" if source == "SEC" else "fda_extensions.csv")
    hashes = report.get("artifact_sha256", {})
    if set(hashes) != names or any(digest((folder / name).read_bytes()) != hashes[name] for name in names):
        raise ValueError("Section evidence checksum mismatch")
    rows = read_rows(folder / (source.lower() + "_verification.csv"))
    expected = {(r["event_key"], r["ticker"]) for r in events}
    if source == "SEC":
        expected |= {("REGISTRY:" + r["ticker"], r["ticker"]) for r in companies}
    identities = {(r.get("event_key"), r.get("ticker")) for r in rows}
    if len(rows) != len(expected) or identities != expected:
        raise ValueError("Section ledger omits or duplicates a current event")
    for row in rows:
        claims = ({"FILINGS_INVENTORY"} if row["event_key"].startswith("REGISTRY:") else
                  {"FINANCING_CLOSURE"} if source == "SEC" else {"PDUFA_TARGET", "FDA_DECISION"})
        if (set(row) != set(FIELDS) or row.get("category") != source
                or row.get("claim") not in claims or row.get("verification_status") not in STATES):
            raise ValueError("Invalid section evidence schema or claim")
        timestamp(row["checked_at"])
        if row["verification_status"] in {"VERIFIED", "NOT_APPLICABLE"} and (
                not row.get("source_url", "").startswith("https://")
                or not re.fullmatch(r"[a-f0-9]{64}", row.get("source_sha256", ""))):
            raise ValueError("Verified section claim lacks source evidence")
    if any(report.get(k) != v for k, v in summary(rows).items()):
        raise ValueError("Section result counts disagree with the evidence")
    return {"report": report, "findings": rows, "folder": folder}


def collect(section, data_dir, out):
    source, mode = section_config(section)
    out.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    # DELTA can seed from the newest previously published exact-claim evidence.
    # Canonical source ledgers and all other agencies remain unchanged.
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as temporary:
        working = Path(temporary)
        for path in data_dir.glob("*.csv"):
            shutil.copyfile(path, working / path.name)
        saved = read_rows(data_dir / "pdufa_source_verification.csv")
        for name, (agency, _) in SECTIONS.items():
            if agency != source:
                continue
            folder = data_dir / SNAPSHOTS / name.lower()
            if (folder / "report.json").is_file():
                try:
                    saved = overlay_findings(saved, load_snapshot(folder, data_dir, name)["findings"])
                except (OSError, ValueError, KeyError, TypeError):
                    pass  # A stale snapshot never seeds a verification.
        write_csv(working / "pdufa_source_verification.csv", saved, FIELDS)
        result = verify_source(source, working, out, mode=mode)
    finished = datetime.now(timezone.utc).isoformat()
    files = [source.lower() + "_verification.csv"]
    if source == "FDA":
        path = data_dir / "fda_pdufa_extension_ledger.csv"
        history = read_rows(path) if path.is_file() else []
        for name in ("FDA_BASE", "FDA_AMENDMENTS"):
            folder = data_dir / SNAPSHOTS / name.lower()
            if (folder / "report.json").is_file():
                try:
                    load_snapshot(folder, data_dir, name)
                    history += read_rows(folder / "fda_extensions.csv")
                except (OSError, ValueError, KeyError, TypeError):
                    pass
        write_csv(out / "fda_extensions.csv", extension_observations(
            read_rows(out / "fda_verification.csv"), history, finished), EXTENSION_FIELDS)
        files.append("fda_extensions.csv")
    else:
        files.append("sec_filing_watch.csv")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    report = {**result, "schema_version": 1, "section": section, "source": source,
              "started_at": started, "finished_at": finished,
              "execution_status": "FINISHED",
              "evidence_status": "VERIFIED" if result["scope_coverage_verified"] else "PARTIAL",
              "run_url": ("https://github.com/pdufa/pdufa-command-center/actions/runs/" + run_id
                          if run_id.isdigit() else ""),
              "artifact_sha256": {name: digest((out / name).read_bytes()) for name in files}}
    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    load_snapshot(out, data_dir, section)
    return report


def publish(section, data_dir, artifacts):
    snapshot = load_snapshot(artifacts, data_dir, section)
    target = data_dir / SNAPSHOTS / section.lower()
    target.mkdir(parents=True, exist_ok=True)
    for name in snapshot["report"]["artifact_sha256"]:
        shutil.copyfile(artifacts / name, target / name)
    shutil.copyfile(artifacts / "report.json", target / "report.json")
    return snapshot["report"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["scan", "publish"])
    parser.add_argument("--section", required=True, choices=SECTIONS)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--artifacts-dir", required=True, type=Path)
    args = parser.parse_args()
    report = (collect(args.section, args.data_dir, args.artifacts_dir) if args.operation == "scan"
              else publish(args.section, args.data_dir, args.artifacts_dir))
    print(json.dumps({k: report[k] for k in (
        "section", "scan_mode", "execution_status", "evidence_status", "required_findings_unresolved")}))


if __name__ == "__main__":
    main()

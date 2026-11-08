#!/usr/bin/env python3
"""Deterministically build the packaged backend FDA application lead snapshot.

Source-of-truth stays in frontend FOCUS and application-cycle records. This
script does not query FDA, promote trials or write to POOL/FOCUS Google Sheets.
Use --check in CI; --write only to update the reviewed dated Docker snapshot.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FOCUS = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
CYCLES = ROOT / "new-platform/frontend/lib/medical-intelligence-applications.ts"
DEST = ROOT / "new-platform/backend/app/data/focus_application_snapshot.json"


def parse_cycles(source: str):
    try:
        raw = source.split("export const APPLICATION_CYCLES:", 1)[1].split("=[", 1)[1]
        raw = raw.split("] as const;", 1)[0]
        result = json.loads("[" + raw + "]")
    except (IndexError, ValueError) as exc:
        raise ValueError("Source-linked FDA application array could not be read") from exc
    if not isinstance(result, list) or not result:
        raise ValueError("No application cycles in canonical source")
    if len({item["id"] for item in result}) != len(result):
        raise ValueError("Duplicate application-cycle IDs")
    return result


def build():
    focus = json.loads(FOCUS.read_text(encoding="utf-8"))
    source = CYCLES.read_text(encoding="utf-8")
    cycles = parse_cycles(source)
    originals = focus.get("records", [])
    if not originals or len({r["nct"] for r in originals}) != len(originals):
        raise ValueError("FOCUS exact NCT records missing or duplicated")
    roster = {r["nct"] for r in originals}
    foreign = {nct for cycle in cycles for nct in cycle["ncts"]} - roster
    if foreign:
        raise ValueError("Application cycle contains NCT outside current FOCUS; review before packaging")
    records = []
    for trial in originals:
        nct = trial["nct"]
        if not isinstance(nct, str) or not nct.startswith("NCT") or len(nct) != 11 or not nct[3:].isdigit():
            raise ValueError("Invalid FOCUS registry identity")
        apps = [a for a in cycles if nct in a["ncts"]]
        if not apps:
            raise ValueError("FOCUS NCT has no independently reconstructed application identity: " + nct)
        if any(a["sourceDate"] > focus["asOf"] or not a["sourceUrl"].startswith("https://") for a in apps):
            raise ValueError("Application source is invalid or later than dated snapshot")
        drug = list(dict.fromkeys(a["drug"] for a in apps))
        indication = list(dict.fromkeys(a["indication"] for a in apps))
        records.append({
            "nct": nct,
            "drug": drug[0] if len(drug) == 1 else "",
            "indication": indication[0] if len(indication) == 1 else "",
            "designations": [],
            "candidateApplications": [{
                "cycleId": a["id"],
                "ticker": a["ticker"],
                "drug": a["drug"],
                "indication": a["indication"],
                "applicationType": a["applicationType"],
                "stage": a["stage"],
                "reportedGoal": a["reportedGoal"],
                "sourceDate": a["sourceDate"],
                "sourceUrl": a["sourceUrl"],
            } for a in apps],
            "attribution": "SOURCE_LINKED_CYCLE_RECONSTRUCTION_NOT_FDA_CONFIRMED",
        })
    return {
        "schemaVersion": 1,
        "asOf": focus["asOf"],
        "upstreamPath": "new-platform/frontend/lib/medical-intelligence-applications.ts",
        "sourceRosters": ["new-platform/frontend/data/p3PostDataActive.json"],
        "intendedUse": "PREVIEW_RESEARCH_IDENTITY_LEADS_ONLY",
        "clinicalSignoff": False,
        "sourceVerifiedByFda": False,
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true",
                      help="CI: fail when the packaged immutable source snapshot is stale")
    mode.add_argument("--write", action="store_true",
                      help="Explicitly refresh only the backend packaged identity file")
    args = parser.parse_args()
    expected = build()
    if args.check:
        if not DEST.exists() or json.loads(DEST.read_text(encoding="utf-8")) != expected:
            parser.exit(1, "Backend FDA application snapshot differs from reviewed FOCUS source. Use --write and inspect the diff.\n")
        print("Application snapshot parity VERIFIED: %s FOCUS NCTs" % len(expected["records"]))
    elif args.write:
        DEST.write_text(json.dumps(expected, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Updated backend application snapshot; review before merging.")


if __name__ == "__main__":
    main()

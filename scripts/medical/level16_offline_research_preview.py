#!/usr/bin/env python3
"""Build the existing FOCUS Level 1–6 offline preview from collected registry research.

The collected 32-trial snapshot is used to populate *unreviewed* phase/status
and source readiness. This command does not fetch evidence, verify publishers,
approve human reviewers, make FDA predictions, alter rosters or deploy a site.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports/scientific-levels1-6"
RESEARCH = REPORTS / "focus-source-research-20261114.json"
COVERAGE = REPORTS / "scientific-coverage-20261114.json"
ORCA2 = REPORTS / "orca2-statistical-chronology-20261114.json"
ROSTER = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
APPLICATIONS = ROOT / "new-platform/backend/app/data/focus_application_snapshot.json"
DEFINITIONS = ROOT / "new-platform/frontend/data/deepMedicalTwentyLevelExpansion.json"
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def _load(name):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build(research, coverage, roster, applications, definitions, orca_case, owner_dossier=None):
    """Return combined offline HTML plus a verifiable research-only coverage receipt."""
    preparation = _load("level16_research_preparation")
    handoff = _load("level16_review_handoff")
    orca = _load("level16_orca2_statistical_timeline")
    renderer = _load("render_level16_focus_preview")

    ncts = [row["nct"] for row in roster["records"]]
    prepared = preparation.validate_snapshot(research, ncts)
    if (research.get("evidenceCutoffDate") != "2026-11-14"
            or research.get("focusTrialCount") != 32
            or research.get("trialsWithRetrievedRegistry") != 32
            or len(prepared) != 32):
        raise ValueError("Research snapshot does not contain all 32 in-cutoff registry records")
    if (coverage.get("evidenceCutoffDate") != research["evidenceCutoffDate"]
            or coverage.get("focusTrialCount") != 32
            or coverage.get("trialCoverageCounts", {}).get("registry") != 32):
        raise ValueError("Coverage snapshot differs from collected source cohort")
    coverage_records = {row["nct"]: row for row in coverage["trials"]}
    if set(coverage_records) != set(prepared):
        raise ValueError("Coverage and original source NCT identities differ")
    for nct, item in prepared.items():
        original = item.get("registrySource")
        if not isinstance(original, dict):
            raise ValueError("Missing collected registry record for " + nct)
        digest = original.get("documentSha256")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise ValueError("Invalid submitted registry digest")
        if original.get("capturedRegistry", {}).get("sha256") != digest:
            raise ValueError("Collected source and extracted-field digest differ")
        published = coverage_records[nct]
        if (published.get("ticker") != item.get("ticker")
                or published.get("phaseUnreviewed") != original.get("phasesUnreviewed")
                or published.get("registry") is not True
                or published.get("mappingStatus") != item.get("mappingStatus")
                or original.get("provenanceIndependentlyAuthenticated") is not False
                or original.get("independentlyScientificallyReviewed") is not False):
            raise ValueError("Research and coverage differ on trial, phase, or unreviewed status")

    readiness = preparation.readiness_report(research, roster, applications, definitions)
    if (readiness.get("focusTrialCount") != 32
            or readiness.get("scientificallyAdjudicatedLevels") != 0
            or readiness.get("originalSourcesIndependentlyAuthenticated") != 0
            or readiness.get("calibratedFdaPredictions") != 0
            or any(trial.get("registryCaptureStatus") != "CAPTURED_UNREVIEWED"
                   for trial in readiness["trials"])):
        raise ValueError("Collected source cannot be promoted to scientific authentication")
    for trial in readiness["trials"]:
        original = prepared[trial["nct"]]["registrySource"]
        if (trial.get("capturedRegistryPhasesUnreviewed") != original.get("phasesUnreviewed")
                or trial.get("registrySource", {}).get("sha256") != original["documentSha256"]
                or any(level.get("assessmentCompleted") is not False
                       for level in trial["levels"])):
            raise ValueError("Rendered phase/source fields differ from collected originals")
    handoff_packet = handoff.build(coverage, roster, applications, orca.assess(orca_case))
    html = renderer.render(readiness, preliminary_research=research,
                           review_handoff=handoff_packet, owner_dossier=owner_dossier)
    return html, {
        "status": "OFFLINE_FOCUS_RESEARCH_PREVIEW_ONLY",
        "evidenceCutoffDate": research["evidenceCutoffDate"],
        "focusTrialCount": 32,
        "originalRegistryFieldsCapturedUnreviewed": 32,
        "independentSourceAuthentications": 0,
        "scientificallyAdjudicatedLevels": 0,
        "fdaForecasts": 0,
        "stagingActivated": False,
        "humanReviewApproved": False,
        "noOriginalDocumentBytesShipped": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="New local offline HTML output; will not overwrite")
    parser.add_argument("--research", type=Path, default=RESEARCH)
    parser.add_argument("--coverage", type=Path, default=COVERAGE)
    parser.add_argument("--roster", type=Path, default=ROSTER)
    parser.add_argument("--applications", type=Path, default=APPLICATIONS)
    parser.add_argument("--definitions", type=Path, default=DEFINITIONS)
    parser.add_argument("--orca2", type=Path, default=ORCA2)
    parser.add_argument("--owner-dossier", type=Path,
                        help="Optional source-linked owner-only ORCA-2 dossier; no external review gate")
    args = parser.parse_args()

    html, receipt = build(
        _read(args.research), _read(args.coverage), _read(args.roster),
        _read(args.applications), _read(args.definitions), _read(args.orca2),
        owner_dossier=_read(args.owner_dossier) if args.owner_dossier else None,
    )
    target = args.output.absolute()
    if target.is_relative_to(ROOT):
        parser.error("Preview output must remain outside the source repository")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as output:
        output.write(html)
    print(json.dumps({**receipt, "output": str(target)}))


if __name__ == "__main__":
    main()

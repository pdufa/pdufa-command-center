#!/usr/bin/env python3
"""Prepare OFFLINE Level 1–6 review tasks when current registry evidence changes.

This tool only recomputes evidence-change triage against a frozen, unsigned
research handoff. It cannot append review events, authenticate reviewers,
invalidate protected database assessments, publish predictions or deploy.
The candidate is untrusted research metadata, NEVER a review authorization.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "reports/scientific-levels1-6/focus-source-research-20261114.json"
ROSTER = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
APPLICATIONS = ROOT / "new-platform/backend/app/data/focus_application_snapshot.json"


def _load(name):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build(candidate, *, baseline=None, root=ROOT):
    """Calculate a source-triggered review WORKLIST, not live review status.

    Baseline and provisional mappings come from the actual checked-out
    source snapshot, not from caller-supplied review-approval claims.
    Candidate is validated by existing exact-NCT/cutoff/receipt logic.
    """
    root = Path(root)
    bundle_mod = _load("level16_research_handoff_bundle")
    triage_mod = _load("level16_registry_change_triage")
    current = bundle_mod.build_bundle(root)
    bundle_mod.verify_bundle(current, root)
    handoff = current["packet"]
    if (handoff.get("focusTrialCount") != 32
            or handoff.get("reviewPacketsPrepared") != 32
            or handoff.get("genuineQualifiedReviewersActivated") != 0
            or handoff.get("independentlyAuthenticatedSources") != 0
            or handoff.get("independentlyAdjudicatedLevels") != 0
            or handoff.get("actualApprovalProbabilities") != 0
            or handoff.get("stagingActivated") is not False):
        raise ValueError("Unreviewed handoff cannot become trusted review state")

    reference = _read(root / "reports/scientific-levels1-6/focus-source-research-20261114.json")
    if baseline is not None and baseline != reference:
        raise ValueError("Reassessment baseline must match the frozen source snapshot")
    delta = triage_mod.compare(
        reference, candidate,
        _read(root / "new-platform/frontend/data/p3PostDataActive.json"),
        _read(root / "new-platform/backend/app/data/focus_application_snapshot.json"),
    )
    if (delta.get("focusTrialCount") != 32
            or delta.get("independentlyAuthenticatedSources") != 0
            or delta.get("independentlyAdjudicatedLevels") != 0
            or delta.get("publishedFdaForecasts") != 0
            or delta.get("historicalBlindPredictionPermitted") is not False
            or delta.get("doesNotModifyLiveReviewState") is not True):
        raise ValueError("Triage cannot approve or rewrite clinical research")

    by_nct = {t["nct"]: t for t in handoff["trials"]}
    changes = {t["nct"]: t for t in delta["trials"]}
    if len(by_nct) != 32 or set(by_nct) != set(changes):
        raise ValueError("Review handoff and delta have different NCT membership")
    rows = []
    for nct, trial in by_nct.items():
        change = changes[nct]
        if (trial["ticker"] != change["ticker"]
                or trial["applicationMappingStatus"] != change["provisionalMappingStatus"]
                or trial.get("actualAuthenticatedSources") != 0
                or trial.get("actualIndependentScientificReviews") != 0
                or trial.get("actualCompletedLevels") != 0
                or trial.get("readyForIndependentFinalAdjudication") is not False):
            raise ValueError("Mismatched identity, mapping, or research status")
        affected = set(change["affectedLevels"])
        if affected - set(range(1, 7)):
            raise ValueError("Evidence change references unknown assessment level")
        level_rows = []
        for level in trial["levels"]:
            number = level["level"]
            if (level.get("sourceAuthenticationStatus") != "NOT_INDEPENDENTLY_AUTHENTICATED"
                    or level.get("independentScientificReviewStatus") != "NOT_ADJUDICATED"
                    or level.get("completionPermitted") is not False
                    or level.get("score") is not None
                    or level.get("approvalProbability") is not None):
                raise ValueError("Unsigned handoff level was promoted to adjudication")
            level_rows.append({
                "level": number,
                "name": level["name"],
                "phaseApplicabilityFromBaselineUnreviewed": level["applicability"],
                "registryEvidenceChangeDetected": number in affected,
                "reviewDisposition": (
                    "NEW_SOURCE_REVIEW_REQUIRED_NOT_AUTOMATICALLY_INVALIDATED"
                    if number in affected
                    else "NO_NEW_REGISTRY_CHANGE_NOT_A_REVIEW_COMPLETION"
                ),
                "originalEvidenceReverificationNeeded": number in affected,
                "sourceReviewStatus": "NOT_INDEPENDENTLY_AUTHENTICATED",
                "scientificReviewStatus": "NOT_ADJUDICATED",
                "independentChallengeStatus": "NOT_COMPLETED",
                "adjudicationStatus": "NOT_COMPLETED",
                "reviewerIdentityApproved": False,
                "unresolvedBaselineReviewQuestions": level["openReviewQuestions"],
                "score": None,
                "approvalProbability": None,
                "fdaOutcomeJudgment": None,
            })
        rows.append({
            "nct": nct,
            "ticker": trial["ticker"],
            "applicationMappingStatus": trial["applicationMappingStatus"],
            "candidateSourceSha256Unverified": change["candidateSourceSha256Unverified"],
            "previousSourceSha256Unverified": change["baselineSourceSha256Unverified"],
            "changedRegistryEvidence": change["reassessmentTrigger"],
            "triggerReasons": change["triggerReasons"],
            "affectedLevels": change["affectedLevels"],
            "requiresManualCurrentEvidenceReview": change["reassessmentTrigger"],
            "worklistStatus": (
                "NEW_UNREVIEWED_EVIDENCE_BLOCKED_PENDING_AUTHORIZATION"
                if change["reassessmentTrigger"]
                else "NO_NEW_CHANGE_DETECTED_EXISTING_REVIEWS_NOT_VERIFIED"
            ),
            "levels": level_rows,
        })

    rows.sort(key=lambda r: (not r["changedRegistryEvidence"],
                             r["nct"] != "NCT04576949", r["nct"]))
    return {
        "kind": "FOCUS_LEVEL16_SOURCE_CHANGE_REVIEW_WORKLIST_OFFLINE_ONLY",
        "status": "ADVISORY_ONLY_NO_LIVE_REVIEW_STATE_MUTATION",
        "baselineCutoff": delta["baselineEvidenceCutoff"],
        "candidateCutoff": delta["candidateEvidenceCutoff"],
        "frozenResearchPacketSha256": current["packetSha256"],
        "focusTrialCount": 32,
        "reviewLevelsPerTrial": 6,
        "changedTrialsRequiringReview": delta["changedTrialCount"],
        "changedLevelsRequiringReview": sum(len(x["affectedLevels"]) for x in rows),
        "independentSourceAuthentications": 0,
        "independentlyAdjudicatedLevels": 0,
        "authorizedReviewerCount": 0,
        "fdaPredictionsProduced": 0,
        "liveReassessmentScheduled": False,
        "protectedReviewEventsWritten": False,
        "stagingActivated": False,
        "trials": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True,
                        help="New immutable unreviewed source research snapshot")
    args = parser.parse_args()
    print(json.dumps(build(_read(args.candidate)), indent=2))


if __name__ == "__main__":
    main()

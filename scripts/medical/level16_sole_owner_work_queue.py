#!/usr/bin/env python3
"""Create an OWNER-ONLY Levels 1–6 research work queue, NOT clinical signoff.

Read-only and offline. Exactly one owner may operate the separate future
research workspace, subject to real account/MFA proof. No fake independent
reviewers, no scoring/final FDA predictions, no new account/role grants, no
production, billing, database or reviewer-policy modifications.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
INTENT = ROOT / "infra/level16-staging/sole-owner-intent.json"
KIND = "LEVEL16_OWNER_ONLY_PREPARATION_NOT_INDEPENDENT_REVIEW"
EXPECTED_KEYS = frozenset({
    "schemaVersion", "kind", "recordedLocalDate", "ownerPreferenceConfirmedByConversation",
    "soleHumanOperator", "siteOwnership", "authorizedOperatorSlots",
    "allowExternalEditorAccounts", "allowOutsideReviewerAccounts", "allowSharedAdminCredentials",
    "requiredMfaForSoleOwner", "ownerPrincipalId", "ownerIssuer",
    "ownerIdentityVerificationStatus", "researchMode", "researchReviewLabel",
    "existingIndependentWorkflow", "sourceAuthenticity",
    "independentScientificAdjudications", "ownerLevelReviewsEntered", "publishedPredictions",
    "noPurchaseOrBillingAuthorization", "noLiveReleaseAuthorization", "allowedNow",
    "requiresFurtherConcreteConfiguration", "protectedActionsStillDisabled", "notes",
})
NCT_RE = re.compile(r"NCT[0-9]{8}\Z")
BLOCKED = {
    "CREATE_PAID_RESOURCES", "ACTIVATE_STAGING", "MERGE", "DEPLOY",
    "MIGRATE_PRODUCTION", "MINT_IDENTITY", "CREATE_REVIEWER",
    "SIGN_INDEPENDENT_ATTESTATION", "PUBLISH_UNCALIBRATED_FDA_PROBABILITY",
}
ALLOWED = {
    "READ_ONLY_RESEARCH_PROCESSING", "PRIVATE_OWNER_PREPARATION",
    "DRAFT_PR_ENGINEERING_AND_TESTS",
}


def _module(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_intent(intent):
    if not isinstance(intent, dict) or set(intent) != EXPECTED_KEYS:
        raise ValueError("Expected exact sole-owner intention schema")
    expected = {
        "schemaVersion": 1,
        "kind": "LEVEL16_SOLE_OWNER_RESEARCH_INTENT_NOT_RUNTIME_AUTHORIZATION",
        "recordedLocalDate": "2026-11-13",
        "ownerPreferenceConfirmedByConversation": True,
        "soleHumanOperator": True,
        "siteOwnership": "SOLE_OWNER_CONTROLS_RESEARCH_ADMINISTRATION_AND_PUBLICATION_DECISIONS",
        "authorizedOperatorSlots": 1,
        "allowExternalEditorAccounts": False,
        "allowOutsideReviewerAccounts": False,
        "allowSharedAdminCredentials": False,
        "requiredMfaForSoleOwner": True,
        "ownerPrincipalId": None,
        "ownerIssuer": None,
        "ownerIdentityVerificationStatus": "NOT_CONFIGURED_OR_VERIFIED",
        "researchMode": "OWNER_DIRECTED_PUBLIC_SOURCE_RESEARCH",
        "researchReviewLabel": "OWNER_SELF_RESEARCH_NOT_INDEPENDENT",
        "existingIndependentWorkflow": "UNCHANGED_OPTIONAL_SEPARATE_CERTIFICATION_PATH",
        "sourceAuthenticity": "NOT_INDEPENDENTLY_ATTESTED",
        "independentScientificAdjudications": 0,
        "ownerLevelReviewsEntered": 0,
        "publishedPredictions": 0,
        "noPurchaseOrBillingAuthorization": True,
        "noLiveReleaseAuthorization": True,
    }
    for key, value in expected.items():
        if type(intent[key]) is not type(value) or intent[key] != value:
            raise ValueError(f"Sole-owner intent may not claim identity, independence, or activation: {key}")
    for field, values in (("allowedNow", ALLOWED), ("protectedActionsStillDisabled", BLOCKED)):
        got = intent[field]
        if not isinstance(got, list) or len(got) != len(values) or set(got) != values:
            raise ValueError("No extra authority or missing security restriction permitted")
    requirements = intent["requiresFurtherConcreteConfiguration"]
    if not isinstance(requirements, list) or len(requirements) < 6:
        raise ValueError("Concrete owner identity, hosting and scientific steps must remain explicit")
    if any(not isinstance(x, str) or not 20 <= len(x) <= 500 for x in requirements):
        raise ValueError("Invalid owner configuration requirement")
    if not isinstance(intent["notes"], str) or len(intent["notes"]) < 50:
        raise ValueError("Limits of sole ownership must be documented")
    return True


def build(intent, unsigned_bundle):
    validate_intent(intent)
    if not isinstance(unsigned_bundle, dict):
        raise ValueError("Source-metadata bundle required")
    bundle_kind = "FOCUS_LEVEL16_UNSIGNED_RESEARCH_REVIEW_BUNDLE"
    if (unsigned_bundle.get("kind") != bundle_kind
            or unsigned_bundle.get("status") != "BYTE_CONSISTENCY_ONLY_NOT_EVIDENCE_AUTHENTICATION"):
        raise ValueError("Cannot use verified or prediction-published packet in sole-owner research mode")
    packet = unsigned_bundle.get("packet")
    if (not isinstance(packet, dict)
            or packet.get("focusTrialCount") != 32
            or packet.get("reviewPacketsPrepared") != 32
            or packet.get("independentlyAuthenticatedSources") != 0
            or packet.get("independentlyAdjudicatedLevels") != 0
            or packet.get("genuineQualifiedReviewersActivated") != 0
            or packet.get("actualApprovalProbabilities") != 0
            or packet.get("stagingActivated") is not False):
        raise ValueError("Sole-owner work queue may not claim independently reviewed science")
    rows = packet.get("trials")
    if not isinstance(rows, list) or len(rows) != 32:
        raise ValueError("Exact 32-FOCUS-trial research cohort required")
    ncts = set()
    queue = []
    for trial in rows:
        nct = trial.get("nct")
        if not isinstance(nct, str) or not NCT_RE.fullmatch(nct) or nct in ncts:
            raise ValueError("Exact unique trial identity required")
        ncts.add(nct)
        levels = trial.get("levels")
        if (not isinstance(levels, list) or [x.get("level") for x in levels] != [1, 2, 3, 4, 5, 6]
                or trial.get("actualCompletedLevels") != 0
                or trial.get("actualAuthenticatedSources") != 0
                or trial.get("readyForIndependentFinalAdjudication") is not False
                or trial.get("fdaOutcomeJudgment") is not None
                or trial.get("approvalProbability") is not None):
            raise ValueError("Trial research and independent assessment must remain separate")
        tasks = []
        for level in levels:
            if (level.get("completionPermitted") is not False
                    or level.get("independentScientificReviewStatus") != "NOT_ADJUDICATED"
                    or level.get("sourceAuthenticationStatus") != "NOT_INDEPENDENTLY_AUTHENTICATED"
                    or level.get("score") is not None
                    or level.get("approvalProbability") is not None
                    or level.get("fdaOutcomeJudgment") is not None):
                raise ValueError("Cannot transfer independent conclusions into owner's research draft")
            questions = level.get("openReviewQuestions")
            if (not isinstance(questions, list) or not questions
                    or any(not isinstance(q, str) or len(q) > 4000 for q in questions)):
                raise ValueError("Owner task missing phase-specific evidence questions")
            tasks.append({
                "level": level["level"],
                "name": level["name"],
                "phaseAppropriate": level["applicability"],
                "originalEvidenceCollection": level["evidenceCollectionStatus"],
                "ownerResearchQuestions": list(questions),
                "ownerObservationStatus": "NOT_ENTERED",
                "ownerSourceChecksStatus": "NOT_ENTERED",
                "ownerAssessmentStatus": "NOT_ENTERED",
                "independentlyAuthenticated": False,
                "independentlyAdjudicated": False,
                "validatedFdaProbability": None,
            })
        queue.append({
            "nct": nct,
            "ticker": trial["ticker"],
            "company": trial["company"],
            "phaseUnreviewed": trial["phaseUnreviewed"],
            "indicationUnreviewed": trial["indicationUnreviewed"],
            "provisionalApplicationMapping": trial["applicationMappingStatus"],
            "ownerOnlyTasks": tasks,
            "ownerResearchProgress": "NOT_STARTED_OWNER_REVIEW",
            "outsidePeopleRequiredForOwnerResearch": False,
            "verifiedScientificOutcome": None,
        })
    return {
        "kind": KIND,
        "status": "PREPARED_OFFLINE_OWNER_RESEARCH_QUEUE_NOT_DEPLOYED",
        "ownerOnly": True,
        "authorizedOperatorSlotsRequested": 1,
        "authenticatedOwnerAccountsVerified": 0,
        "sourceMetadataSha256": dict(unsigned_bundle["sourceSha256"]),
        "researchPacketSha256": unsigned_bundle["packetSha256"],
        "trialCount": len(queue),
        "levelCount": sum(len(t["ownerOnlyTasks"]) for t in queue),
        "ownerReviewsCompleted": 0,
        "independentReviewsCompleted": 0,
        "siteLive": False,
        "sourceIndependentlyAuthenticated": False,
        "fdaForecastPublished": False,
        "independentlyReviewedWorkflowLeftIntact": True,
        "blockedOn": intent["requiresFurtherConcreteConfiguration"][:],
        "trials": queue,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nct", help="Show only a trial in the full validated owner-only 32-NCT queue")
    args = parser.parse_args()
    intent = json.loads(INTENT.read_text(encoding="utf-8"))
    packet = _module("level16_research_handoff_bundle").build_bundle(ROOT)
    queue = build(intent, packet)
    if args.nct:
        if not NCT_RE.fullmatch(args.nct) or args.nct not in {x["nct"] for x in queue["trials"]}:
            parser.error("Unknown trial outside the exact 32-FOCUS cohort")
        queue["trials"] = [t for t in queue["trials"] if t["nct"] == args.nct]
        queue["selectedNctOnly"] = args.nct
    print(json.dumps(queue, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

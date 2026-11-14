#!/usr/bin/env python3
"""Render an offline, read-only FOCUS Levels 1–6 review-queue preview.

The generated file does not connect to the application, submit reviews,
publish scores, or prove that medical evidence is independently verified.
"""
from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

NCT_RE = re.compile(r"NCT[0-9]{8}\Z")


def _text(value):
    return escape(str(value) if value is not None else "Unknown", quote=True)


def _source_link(url):
    if not isinstance(url, str) or any(c.isspace() for c in url):
        return "<span>Source locator withheld</span>"
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return "<span>Source locator withheld</span>"
    safe_url = escape(url, quote=True)
    return f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer">View submitted source</a>'


def render(report, trusted_review_reader=None, preliminary_research=None, review_handoff=None):
    if not isinstance(report, dict) or report.get("status") != "PHASE_FIRST_EVIDENCE_TRIAGE_ONLY":
        raise ValueError("Refusing non-readiness or scientific-prediction report")
    trials = report.get("trials")
    if (not isinstance(trials, list) or not trials
            or len(trials) != report.get("focusTrialCount")):
        raise ValueError("Preview requires the complete exact-NCT FOCUS report")
    handoff_by_nct = {}
    if review_handoff is not None:
        if (not isinstance(review_handoff, dict)
                or review_handoff.get("kind") != "FOCUS_LEVELS1_6_INDEPENDENT_REVIEW_HANDOFF_RESEARCH_ONLY"
                or review_handoff.get("focusTrialCount") != 32
                or review_handoff.get("reviewPacketsPrepared") != 32
                or review_handoff.get("independentlyAuthenticatedSources") != 0
                or review_handoff.get("independentlyAdjudicatedLevels") != 0
                or review_handoff.get("genuineQualifiedReviewersActivated") != 0
                or review_handoff.get("actualApprovalProbabilities") != 0
                or review_handoff.get("stagingActivated") is not False
                or review_handoff.get("researchIsOutcomeExposed") is not True
                or review_handoff.get("evidenceCutoffDate") != "2026-11-14"
                or review_handoff.get("reviewReleaseStatus")
                != "OWNER_RESEARCH_PREPARED_NO_EXTERNAL_SIGNOFF_REQUIRED"
                or review_handoff.get("ownerOnlyAssessmentMode") is not True
                or review_handoff.get("externalReviewerGateCount") != 0
                or review_handoff.get("externalSignoffsRequiredForScoring") != 0
                or review_handoff.get("ownerReviewNotYetEntered") is not True):
            raise ValueError("Review handoff must remain current-source research only")
        handoff_trials = review_handoff.get("trials")
        if not isinstance(handoff_trials, list) or len(handoff_trials) != 32:
            raise ValueError("Handoff requires all 32 exact FOCUS NCTs")
        for handoff_trial in handoff_trials:
            if not isinstance(handoff_trial, dict):
                raise ValueError("Invalid handoff record")
            nct = handoff_trial.get("nct")
            handoff_levels = handoff_trial.get("levels")
            if (not isinstance(nct, str) or not NCT_RE.fullmatch(nct) or nct in handoff_by_nct
                    or not isinstance(handoff_levels, list)
                    or [x.get("level") for x in handoff_levels] != list(range(1, 7))
                    or handoff_trial.get("actualCompletedLevels") != 0
                    or handoff_trial.get("actualIndependentScientificReviews") != 0
                    or handoff_trial.get("actualAuthenticatedSources") != 0
                    or handoff_trial.get("readyForIndependentFinalAdjudication") is not False
                    or handoff_trial.get("independentReviewerAccess") != "NOT_APPROVED_OR_ACTIVATED"
                    or handoff_trial.get("approvalProbability") is not None
                    or handoff_trial.get("fdaOutcomeJudgment") is not None
                    or handoff_trial.get("ownerOnlyAssessmentMode") is not True
                    or handoff_trial.get("outsideReviewerCountRequired") != 0
                    or handoff_trial.get("ownerAssessmentNotBlockedByExternalSignoff") is not True):
                raise ValueError("Handoff trial identity or clinical review was promoted")
            for entry in handoff_levels:
                if (entry.get("sourceAuthenticationStatus") != "NOT_INDEPENDENTLY_AUTHENTICATED"
                        or entry.get("independentScientificReviewStatus") != "NOT_ADJUDICATED"
                        or entry.get("ownerReviewStatus") != "OWNER_NOT_REVIEWED"
                        or entry.get("externalReviewerRequired") is not False
                        or entry.get("ownerCanReviewWithoutExternalVerification") is not True
                        or entry.get("independentChallengeStatus") != "NOT_COMPLETED"
                        or entry.get("finalAdjudicationStatus") != "NOT_COMPLETED"
                        or entry.get("completionPermitted") is not False
                        or entry.get("score") is not None
                        or entry.get("approvalProbability") is not None
                        or entry.get("fdaOutcomeJudgment") is not None
                        or not isinstance(entry.get("openReviewQuestions"), list)):
                    raise ValueError("Preview rejects untrusted handoff signoff or prediction")
            handoff_by_nct[nct] = handoff_trial
        if {x.get("nct") for x in trials} != set(handoff_by_nct):
            raise ValueError("Handoff and readiness NCT roster mismatch")
    research_by_nct = {}
    if preliminary_research is not None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("level16_research_preparation", Path(__file__).with_name("level16_research_preparation.py"))
        research = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(research)
        research_by_nct = research.validate_snapshot(preliminary_research,[t.get("nct") for t in trials])
    byte_summary = report.get("localByteConsistency")
    if byte_summary is not None and (
        not isinstance(byte_summary, dict)
        or byte_summary.get("status") != "LOCAL_BYTE_CONSISTENCY_ONLY_NOT_SOURCE_AUTHENTICATION"
        or byte_summary.get("originalSourceAuthenticated") != 0
        or byte_summary.get("independentScientificReviews") != 0
    ):
        raise ValueError("Preview refuses source-authentication or review promotion")
    seen = set()
    rows = []
    for trial in trials:
        nct = trial.get("nct")
        levels = trial.get("levels")
        if (not isinstance(nct, str) or not NCT_RE.fullmatch(nct)
                or nct in seen or not isinstance(levels, list)
                or [x.get("level") for x in levels] != list(range(1, 7))):
            raise ValueError("Malformed FOCUS trial identity or six-level report")
        seen.add(nct)
        if nct in handoff_by_nct:
            handoff_trial = handoff_by_nct[nct]
            mapping = (
                "NOT_MAPPED_APPLICATION_CYCLE"
                if trial.get("applicationCycleVerification") == "NOT_MAPPED_APPLICATION_CYCLE"
                else "PROVISIONAL_NOT_VERIFIED"
            )
            if (trial.get("applicationCycleVerification") not in (
                    "NOT_MAPPED_APPLICATION_CYCLE", "PROVISIONAL_NOT_FDA_VERIFIED")
                    or handoff_trial.get("applicationMappingStatus") != mapping
                    or handoff_trial.get("ticker") != trial.get("ticker")):
                raise ValueError("Handoff trial/application mapping differs from readiness report")
        if trial.get("fdaOutcomeJudgment") is not None or trial.get("fdaTimingJudgment") is not None:
            raise ValueError("Preview cannot display uncertified FDA predictions")
        for level in levels:
            workflow = level.get("reviewWorkflow", {})
            authorized = workflow.get("status") == "AUTHORIZED_DATABASE_READBACK"
            blocked_readback = workflow.get("status") == "TRUSTED_REVIEW_READBACK_BLOCKED"
            if authorized or blocked_readback:
                if trusted_review_reader is None or trusted_review_reader(nct, level["level"]) != workflow:
                    raise ValueError("Saved JSON cannot certify reviews; trusted current database readback required")
            elif workflow:
                if (workflow.get("status") != "TRUSTED_REVIEW_INFRASTRUCTURE_NOT_CONNECTED"
                        or workflow.get("history") or workflow.get("independentlyAdjudicated") is not False
                        or workflow.get("originalDocumentAuthenticationStatus") != "NOT_AUTHENTICATED"
                        or workflow.get("reviewerAuthorizationStatus") != "TRUSTED_INDIVIDUAL_AUTH_NOT_CONNECTED"
                        or workflow.get("clinicalReviewStatus") != "NOT_COMPLETED"
                        or workflow.get("independentChallengeStatus") != "NOT_COMPLETED"):
                    raise ValueError("Untrusted review authorization, authentication or event-history claim")
            completed = authorized and workflow.get("independentlyAdjudicated") is True
            expected_review = "INDEPENDENTLY_ADJUDICATED" if completed else "NOT_ADJUDICATED"
            if (level.get("scientificReviewStatus") != expected_review
                    or level.get("assessmentCompleted") is not completed
                    or level.get("scientificConclusion") != (workflow["findings"] if completed else None)
                    or level.get("score") is not None
                    or level.get("approvalProbability") is not None):
                raise ValueError("Preview refuses uncertified clinical assessments")
        lines = []
        for item in levels:
            submitted = item.get("submittedEvidenceLeads", [])
            if not isinstance(submitted, list):
                raise ValueError("Invalid evidence review queue")
            linked = []
            for source in submitted:
                if (not isinstance(source, dict)
                        or source.get("authenticationStatus")
                        != "SUBMITTED_SOURCE_NOT_INDEPENDENTLY_AUTHENTICATED"
                        or source.get("scientificReviewStatus") != "NOT_ADJUDICATED"):
                    raise ValueError("Preview rejects unreviewed source promotion")
                local = source.get("localByteReceipt")
                local_status = ""
                if local is not None:
                    if (not isinstance(local, dict)
                            or local.get("byteMatchStatus") not in {
                                "NO_LOCAL_RECEIPT",
                                "LOCAL_BYTES_MATCH_SUBMITTED_DIGEST_ONLY",
                                "LOCAL_DIGEST_MISMATCH",
                                "LOCAL_FILE_NOT_PRESENT",
                            }):
                        raise ValueError("Preview refuses invalid local receipt status")
                    local_status = (" · Local byte consistency: "
                                    + _text(local["byteMatchStatus"])
                                    + " (NOT original-source authenticated)")
                case = source.get("sourceVerificationCase")
                if case is not None:
                    if case.get("status") != "SOURCE_CASE_UNREVIEWED" or case.get("independentlyAuthenticated") is not False:
                        raise ValueError("Preview refuses source-case certification")
                    local_status += "<p>Source verification case: UNREVIEWED. Blockers: " + _text(", ".join(case["blockers"])) + "</p>"
                    local_status += "<p>Conflicts: " + _text("; ".join(case["conflicts"]) or "None submitted; not independently checked") + "</p>"
                    local_status += "<p>Limitations: " + _text("; ".join(case["limitations"])) + "</p>"
                linked.append(
                    '<li><span class="kind">' + _text(source.get("sourceKind")) +
                    "</span> — " + _text(source.get("role")) +
                    ": " + _text(source.get("claim")) + " — " +
                    _source_link(source.get("sourceUrl")) +
                    " (source date " + _text(source.get("sourceDate")) + ")" +
                    local_status + "</li>"
                )
            link_html = "<ul>" + "".join(linked) + "</ul>" if linked else "<span class='muted'>No source submissions</span>"
            for proposal in item.get("reviewProposalsUnreviewed", []):
                if (proposal.get("status") != "UNREVIEWED_PROPOSAL_NOT_SCIENTIFIC_ASSESSMENT"
                        or proposal.get("independentlyReviewed") is not False):
                    raise ValueError("Preview refuses proposed-review certification")
                link_html += "<p>UNREVIEWED review proposal: " + _text(proposal["proposalId"]) + "</p>"
                for label, key in (("Proposed findings", "findingsUnreviewed"), ("Proposed reasons", "reasonsUnreviewed"),
                                   ("Contradictions", "contradictoryEvidence"), ("Limitations", "limitations"), ("Blockers", "blockers")):
                    link_html += "<p>" + label + ": " + _text("; ".join(proposal[key])) + "</p>"
            if nct in research_by_nct:
                preliminary = research_by_nct[nct]["levels"][item["level"]-1]
                link_html += "<p><strong>PRELIMINARY RESEARCH — OWNER NOT REVIEWED</strong></p>"
                if preliminary.get("preliminaryResearchInterpretation"):
                    link_html += "<p>Research interpretation: " + _text(preliminary["preliminaryResearchInterpretation"]) + "</p>"
                if preliminary.get("publicLiteratureObservationUnreviewed"):
                    observation = preliminary["publicLiteratureObservationUnreviewed"]
                    link_html += "<p>Unreviewed literature observation: " + _text(observation["factualObservation"]) + " · " + _source_link(observation["sourceUrl"]) + " · publication " + _text(observation["publicationDateUnreviewed"]) + "</p>"
                for label, key in (("Supporting reasons", "supportingReasons"), ("Risks requiring review", "riskFactorsRequiringReview"),
                                   ("Missing evidence", "missingEvidence"), ("Not yet expected", "notYetExpectedEvidence")):
                    if preliminary.get(key):
                        link_html += "<p>" + label + ": " + _text("; ".join(preliminary[key])) + "</p>"
                for finding in preliminary["preliminaryFindings"]:
                    link_html += "<p>" + _text(finding["finding"]) + ": " + _text(json.dumps(finding["sourceValue"],ensure_ascii=False)) + " · locator " + _text(finding["locator"]) + " · " + _source_link(finding["sourceUrl"]) + "</p>"
                    link_html += "<p>Reasons: " + _text("; ".join(finding["reasons"])) + "</p>"
                for question in preliminary.get("outstandingSourceQuestions", []):
                    link_html += "<p>Outstanding source question: " + _text(question) + "</p>"
                for request in preliminary["requiredEvidence"]:
                    link_html += "<p>" + _text(request["state"]) + ": " + _text(request["requirement"]) + "</p>"
                link_html += "<p>Limitations: " + _text("; ".join(preliminary["limitations"])) + "</p>"
                link_html += "<p>Contradiction review: " + _text(preliminary["contradictionReviewStatus"]) + " · leads: " + _text("; ".join(preliminary["contradictoryFindings"]) or "Not adjudicated") + "</p>"
            if nct in handoff_by_nct:
                handoff_level = handoff_by_nct[nct]["levels"][item["level"] - 1]
                if (handoff_level.get("level") != item["level"]
                        or not isinstance(handoff_level.get("applicability"), str)
                        or not isinstance(handoff_level.get("evidenceCollectionStatus"), str)
                        or handoff_level.get("evidenceCollectionStatus") not in (
                            "COLLECTED_UNREVIEWED", "NOT_COLLECTED_AVAILABILITY_UNRESOLVED")):
                    raise ValueError("Review handoff level is inconsistent")
                questions = handoff_level["openReviewQuestions"]
                if any(not isinstance(q, str) or not 1 <= len(q) <= 2000 for q in questions):
                    raise ValueError("Invalid source review question")
                link_html += "<details><summary>Owner-only assessment handoff — OWNER NOT REVIEWED</summary>"
                link_html += "<p>Source collection: " + _text(handoff_level["evidenceCollectionStatus"]) + "</p>"
                link_html += "<p>Unreviewed phase applicability: " + _text(handoff_level["applicability"]) + "</p>"
                link_html += "<ul>" + "".join("<li>" + _text(q) + "</li>" for q in questions) + "</ul>"
                link_html += "<p>Owner checks evidence, weighs limitations and records any acceptance. Outside reviewers and external signoffs are NOT required for Levels 1–20.</p>"
                link_html += "</details>"
            workflow = item.get("reviewWorkflow", {})
            review_html = "<p>Scientific review: " + _text(item["scientificReviewStatus"].replace("_", " ")) + "</p>"
            for label, key in (("Source collection", "sourceCollectionStatus"),
                               ("Original document authentication", "originalDocumentAuthenticationStatus"),
                               ("Reviewer authorization", "reviewerAuthorizationStatus"),
                               ("Clinical review", "clinicalReviewStatus"),
                               ("Legacy independent challenge (inactive)", "independentChallengeStatus")):
                review_html += "<p>" + label + ": " + _text(workflow.get(key)) + "</p>"
            review_html += "<p>Registry fields missing: " + _text(", ".join(item.get("registryFieldsNotCaptured", [])) or "None captured as missing; not a scientific completeness claim") + "</p>"
            review_html += "<p>Phase-specific applicability: " + _text(item.get("pivotalReadoutRequirement") or item.get("pivotalSAPRequirement") or "Review at current phase") + "</p>"
            if item.get("verifiedPhaseBasis"):
                review_html += "<p>Verified phase from source review: " + _text(", ".join(item["verifiedPhaseBasis"])) + "</p>"
            review_html += "<p>Evidence disposition: " + _text(workflow.get("evidenceState", "UNREVIEWED")) + "</p>"
            review_html += "<p>Implementation: " + _text(item.get("implementationStatus")) + " · Automated tests: " + _text(item.get("automatedTestStatus")) + "</p>"
            review_html += "<p>Remaining blockers: " + _text("; ".join(workflow.get("blockers", []))) + "</p>"
            if workflow.get("status") == "AUTHORIZED_DATABASE_READBACK":
                label = "Independently adjudicated finding" if workflow.get("independentlyAdjudicated") else "Authorized review event (NOT final adjudication)"
                review_html += "<p><strong>" + label + "</strong></p>"
                context = workflow["binding"]
                review_html += "<p>Review evidence context: " + _text(context["indication"]) + " · " + _text(", ".join(context["phases"])) + " · cutoff " + _text(context["cutoffDate"]) + "</p>"
                review_html += "<p>Original document: " + _text(context["documentId"]) + " · version " + _text(context["documentVersion"]) + " · protocol " + _text(context["protocolVersion"]) + " · SHA-256 " + _text(context["documentSha256"]) + "</p>"
                review_html += "<p>Published " + _text(context["publicationDate"]) + " · retrieved " + _text(context["retrievalDate"]) + " · " + _source_link(context["sourceUrl"]) + "</p>"
                provenance = workflow.get("originalEvidenceProvenance")
                if provenance is not None:
                    review_html += "<p>Original publisher: " + _text(provenance["provenance"]["publisher"]) + " · retrieval: " + _text(provenance["provenance"]["retrievalMethod"]) + "</p>"
                    review_html += "<p>Source attestation authority: " + _text(provenance["attestationAuthority"]) + " · ID " + _text(provenance["attestationId"]) + " · attesting person " + _text(provenance["attestingPerson"]) + "</p>"
                    for amendment in provenance["amendments"]:
                        review_html += "<p>Amendment original: " + _text(amendment["documentId"]) + " · " + _text(amendment["documentVersion"]) + " · " + _text(amendment["protocolVersion"]) + " · SHA-256 " + _text(amendment["documentSha256"]) + " · " + _source_link(amendment["sourceUrl"]) + "</p>"
                for label, key in (("Findings", "findings"), ("Reasons", "reasons"),
                                   ("Contradictions", "contradictoryEvidence"), ("Limitations", "limitations")):
                    review_html += "<p>" + label + ": " + _text("; ".join(workflow[key])) + "</p>"
                review_html += "<details><summary>Append-only review-event history</summary><ol>"
                for event in workflow["history"]:
                    review_html += "<li>" + _text(event["eventId"]) + " · version " + _text(event["version"]) + " · " + _text(event["status"]) + " · " + _text(event["action"]) + " · " + _text(event["authorizedRole"]) + " / " + _text(event["reviewerIssuer"]) + " / " + _text(event["reviewerId"]) + " · " + _text(event["serverTimestamp"]) + " · predecessor " + _text(event["previousEventId"]) + " · findings " + _text("; ".join(event["findings"])) + "</li>"
                review_html += "</ol></details>"
            requests = item.get("originalEvidenceRequests", [])
            requests_text = ", ".join(map(str, requests)) if isinstance(requests, list) else ""
            if nct in handoff_by_nct:
                if workflow.get("status") == "AUTHORIZED_DATABASE_READBACK":
                    raise ValueError("Owner-only preview cannot silently display legacy independently signed readback")
                # The old readiness report contains multi-person review
                # requirements, but they are archived engineering, NOT active
                # owner assessment gates. Do not display their old blockers.
                requests_text = "Owner checks phase-appropriate evidence and missing sources; no external verification."
                review_html = (
                    "<p>Owner self-review: OWNER NOT REVIEWED.</p>"
                    "<p>No external clinician, statistician, source attestor, challenger or signoff required.</p>"
                    "<p>Published source evidence and questions remain unreviewed; no FDA forecast recorded.</p>"
                    "<p>Missing registry fields: "
                    + _text(", ".join(item.get("registryFieldsNotCaptured", []))
                            or "None recorded as missing; not proof of evidence completeness")
                    + "</p>"
                )
            lines.append(
                "<tr><td>" + _text(item["level"]) + " · " + _text(item.get("name")) +
                "</td><td>" + _text(item.get("readiness")) +
                "</td><td>" + _text(requests_text) +
                "</td><td>" + link_html +
                "</td><td>" + review_html + "</td></tr>"
            )
        summary = (
            _text(trial.get("company")) + " · " + _text(trial.get("ticker")) + " · " + _text(nct) +
            " · Phase: " + _text(trial.get("phaseGroup")) +
            " · Source submissions: " + _text(trial.get("sourceSubmissionCount", 0))
        )
        rows.append(
            "<details><summary>" + summary +
            "</summary><div class='detail'><p><strong>Registry phase/status (captured, NOT verified):</strong> " +
            _text(", ".join(trial.get("capturedRegistryPhasesUnreviewed", [])) or "Unknown") +
            " / " + _text(trial.get("capturedStudyStatusUnreviewed")) +
            " · <strong>Mapping status:</strong> " + _text(trial.get("applicationCycleVerification")) +
            "</p><p><strong>Candidate indications (not verified):</strong> " +
            _text(", ".join(trial.get("candidateIndicationsUnverified", [])) or "Not supplied") +
            " · <strong>Application cycle links:</strong> " +
            _text(", ".join(trial.get("candidateApplicationCycleIdsUnverified", [])) or "None") +
            "</p><div class='tablewrap'><table><thead><tr><th>Level</th><th>Evidence status</th>" +
            ("<th>Owner evidence checks</th><th>Source leads</th><th>Owner review</th>"
             if handoff_by_nct else
             "<th>Required evidence review</th><th>Submitted source leads</th><th>Scientific review</th>") +
            "</tr></thead><tbody>" + "".join(lines) + "</tbody></table></div></div></details>"
        )
    actual_completed = sum(level.get("assessmentCompleted") is True for trial in trials for level in trial["levels"])
    if report.get("scientificallyAdjudicatedLevels", 0) != actual_completed:
        raise ValueError("Review completion count must agree with authorized readback")
    css = """body{font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif;margin:0;color:#192536;background:#f4f7fa}
    main{max-width:1160px;margin:auto;padding:24px 18px 50px}
    h1{font-size:1.8rem;margin-bottom:6px}p{margin:8px 0}
    .notice{background:#fff4df;border:1px solid #c78924;border-radius:9px;padding:14px;margin:18px 0}
    .metrics{display:flex;flex-wrap:wrap;gap:12px;margin:16px 0}
    .metric{background:#fff;border-radius:9px;border:1px solid #d7e0eb;padding:12px;min-width:155px}
    .metric strong{display:block;font-size:1.5rem}.metric small{color:#5d6b7f}
    details{background:#fff;border:1px solid #d7e0eb;border-radius:8px;margin:9px 0}
    summary{cursor:pointer;font-weight:600;padding:14px;overflow-wrap:anywhere}
    .detail{padding:0 14px 14px}.muted{color:#69798b}
    .tablewrap{overflow-x:auto}table{border-collapse:collapse;width:100%;min-width:840px}
    td,th{border-bottom:1px solid #e5eaf0;text-align:left;padding:10px;vertical-align:top}
    th{font-size:.86rem;background:#f6f8fb}
    td{font-size:.86rem}ul{margin:0;padding-left:18px}
    .kind{font-weight:700}a{color:#1456a0}a:focus,summary:focus{outline:3px solid #1971c2}
    """
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>FOCUS — Scientific Levels 1–6 Evidence Review Preview</title>"
        "<style>" + css + "</style></head><body><main>"
        "<h1>FOCUS · Scientific Levels 1–6</h1>"
        "<p>Read-only evidence review preview. Original FOCUS membership remains unchanged.</p>" +
        ("<div class='notice'><strong>OWNER-ONLY RESEARCH — NO EXTERNAL VERIFICATION REQUIRED.</strong>"
         " Sources and proposed findings are preliminary; owner review has not been entered."
         " No calibrated FDA forecast or production deployment is implied.</div>"
         if handoff_by_nct else
         "<div class='notice'><strong>NOT MEDICAL ASSESSMENTS OR FDA FORECASTS.</strong>"
         " Submitted source metadata and proposed findings are unreviewed. Authorized findings require "
         "trusted current database readback. This page is not deployed to production.</div>") +
        "<section class='metrics' aria-label='Assessment readiness counts'>"
        "<div class='metric'><strong>" + _text(report.get("focusTrialCount")) +
        "</strong><small>FOCUS exact NCT trials</small></div>"
        "<div class='metric'><strong>" + _text(report.get("provisionalApplicationCycleCount")) +
        "</strong><small>Provisional application cycles</small></div>"
        "<div class='metric'><strong>" + _text(report.get("unmappedTrialCount", 0)) +
        "</strong><small>Trials without application mapping</small></div>"
        "<div class='metric'><strong>" + _text(report.get("sourceSubmissionCount", 0)) +
        "</strong><small>Source submissions awaiting authentication</small></div>" +
        ("<div class='metric'><strong>0</strong><small>Owner reviews recorded</small></div>"
         if handoff_by_nct else
         "<div class='metric'><strong>" + _text(report.get("scientificallyAdjudicatedLevels", 0)) + "</strong><small>Independently reviewed Levels 1–6</small></div>")
        + (
            "<div class='metric'><strong>" + _text(byte_summary.get("localByteMatches", 0))
            + "</strong><small>Local files matching submitted SHA-256 (NOT source-authenticated)</small></div>"
            "<div class='metric'><strong>" + _text(byte_summary.get("localDigestMismatches", 0))
            + "</strong><small>Local digest mismatches</small></div>"
            if byte_summary is not None else ""
        )
        + "</section><h2>Trial-by-trial review queues</h2>" +
        "".join(rows) + "</main></body></html>"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preliminary-research", type=Path,
                        help="Optional unreviewed current-source worksheets; never authorizes clinical signoff")
    parser.add_argument("--review-handoff", type=Path,
                        help="Optional unreviewed 32-trial owner-only source and self-check preparation queue")
    args = parser.parse_args()
    document = json.loads(args.report.read_text(encoding="utf-8"))
    preliminary = json.loads(args.preliminary_research.read_text(encoding="utf-8")) if args.preliminary_research else None
    handoff = json.loads(args.review_handoff.read_text(encoding="utf-8")) if args.review_handoff else None
    html = render(document, preliminary_research=preliminary, review_handoff=handoff)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(json.dumps({"status": "PREVIEW_ONLY", "trials": document["focusTrialCount"],
                      "output": str(args.output)}))


if __name__ == "__main__":
    main()

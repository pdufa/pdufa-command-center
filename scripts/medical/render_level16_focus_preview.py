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


def render(report, trusted_review_reader=None):
    if not isinstance(report, dict) or report.get("status") != "PHASE_FIRST_EVIDENCE_TRIAGE_ONLY":
        raise ValueError("Refusing non-readiness or scientific-prediction report")
    trials = report.get("trials")
    if (not isinstance(trials, list) or not trials
            or len(trials) != report.get("focusTrialCount")):
        raise ValueError("Preview requires the complete exact-NCT FOCUS report")
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
        if trial.get("fdaOutcomeJudgment") is not None or trial.get("fdaTimingJudgment") is not None:
            raise ValueError("Preview cannot display uncertified FDA predictions")
        for level in levels:
            workflow = level.get("reviewWorkflow", {})
            authorized = workflow.get("status") == "AUTHORIZED_DATABASE_READBACK"
            if authorized:
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
            workflow = item.get("reviewWorkflow", {})
            review_html = "<p>Scientific review: " + _text(item["scientificReviewStatus"].replace("_", " ")) + "</p>"
            for label, key in (("Source collection", "sourceCollectionStatus"),
                               ("Original document authentication", "originalDocumentAuthenticationStatus"),
                               ("Reviewer authorization", "reviewerAuthorizationStatus"),
                               ("Clinical review", "clinicalReviewStatus"),
                               ("Independent challenge", "independentChallengeStatus")):
                review_html += "<p>" + label + ": " + _text(workflow.get(key)) + "</p>"
            review_html += "<p>Registry fields missing: " + _text(", ".join(item.get("registryFieldsNotCaptured", [])) or "None captured as missing; not a scientific completeness claim") + "</p>"
            review_html += "<p>Phase-specific applicability: " + _text(item.get("pivotalReadoutRequirement") or item.get("pivotalSAPRequirement") or "Review at current phase") + "</p>"
            review_html += "<p>Remaining blockers: " + _text("; ".join(workflow.get("blockers", []))) + "</p>"
            if workflow.get("status") == "AUTHORIZED_DATABASE_READBACK":
                label = "Independently adjudicated finding" if workflow.get("independentlyAdjudicated") else "Authorized review event (NOT final adjudication)"
                review_html += "<p><strong>" + label + "</strong></p>"
                context = workflow["binding"]
                review_html += "<p>Review evidence context: " + _text(context["indication"]) + " · " + _text(", ".join(context["phases"])) + " · cutoff " + _text(context["cutoffDate"]) + "</p>"
                for label, key in (("Findings", "findings"), ("Reasons", "reasons"),
                                   ("Contradictions", "contradictoryEvidence"), ("Limitations", "limitations")):
                    review_html += "<p>" + label + ": " + _text("; ".join(workflow[key])) + "</p>"
                review_html += "<details><summary>Append-only review-event history</summary><ol>"
                for event in workflow["history"]:
                    review_html += "<li>" + _text(event["eventId"]) + " · version " + _text(event["version"]) + " · " + _text(event["status"]) + " · " + _text(event["action"]) + " · " + _text(event["authorizedRole"]) + " / " + _text(event["reviewerIssuer"]) + " / " + _text(event["reviewerId"]) + " · " + _text(event["serverTimestamp"]) + " · predecessor " + _text(event["previousEventId"]) + " · findings " + _text("; ".join(event["findings"])) + "</li>"
                review_html += "</ol></details>"
            requests = item.get("originalEvidenceRequests", [])
            requests_text = ", ".join(map(str, requests)) if isinstance(requests, list) else ""
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
            "</p><div class='tablewrap'><table><thead><tr><th>Level</th><th>Evidence status</th>"
            "<th>Required evidence review</th><th>Submitted source leads</th><th>Scientific review</th>"
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
        "<p>Read-only evidence review preview. Original FOCUS membership remains unchanged.</p>"
        "<div class='notice'><strong>NOT MEDICAL ASSESSMENTS OR FDA FORECASTS.</strong>"
        " Submitted source metadata and proposed findings are unreviewed. Authorized findings require "
        "trusted current database readback. This page is not deployed to production.</div>"
        "<section class='metrics' aria-label='Assessment readiness counts'>"
        "<div class='metric'><strong>" + _text(report.get("focusTrialCount")) +
        "</strong><small>FOCUS exact NCT trials</small></div>"
        "<div class='metric'><strong>" + _text(report.get("provisionalApplicationCycleCount")) +
        "</strong><small>Provisional application cycles</small></div>"
        "<div class='metric'><strong>" + _text(report.get("unmappedTrialCount", 0)) +
        "</strong><small>Trials without application mapping</small></div>"
        "<div class='metric'><strong>" + _text(report.get("sourceSubmissionCount", 0)) +
        "</strong><small>Source submissions awaiting authentication</small></div>"
        "<div class='metric'><strong>" + _text(report.get("scientificallyAdjudicatedLevels", 0)) + "</strong><small>Independently reviewed Levels 1–6</small></div>"
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
    args = parser.parse_args()
    document = json.loads(args.report.read_text(encoding="utf-8"))
    html = render(document)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(json.dumps({"status": "PREVIEW_ONLY", "trials": document["focusTrialCount"],
                      "output": str(args.output)}))


if __name__ == "__main__":
    main()

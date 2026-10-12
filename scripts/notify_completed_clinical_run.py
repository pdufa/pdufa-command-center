#!/usr/bin/env python3
"""Send one audited END email for each #2/#3/#4 GitHub clinical collector job.

Invoked by an independent workflow_run: completed notification workflow.
It works even if the collector runner failed before its final step, and it
never claims an all-source PDUFA baseline is complete.
"""
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone

from scripts.scan_email import (
    EmailSettings, EmailSendError, EmailSetupError, compose_end, report_summary,
    send_email,
)

WORKFLOW_NAME = "PDUFA One-Time Clinical Scan"
SCANS = {"2": "PIPELINE", "3": "PRE3", "4": "POST3"}
MISSING_SOURCES = [
    "FDA regulatory decisions", "SEC financing/dilution",
    "issuer announcements", "cash/runway", "complete market/ownership evidence",
    "full company-by-company coverage audit",
]


def _iso(value, default=None):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return default


def _get_json(url, token, *, opener=urllib.request.urlopen):
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "pdufa-end-scan-notifier",
    })
    with opener(request, timeout=30) as response:
        return json.load(response)


def _get_bytes(url, token, *, opener=urllib.request.urlopen):
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "pdufa-end-scan-notifier",
    })
    with opener(request, timeout=60) as response:
        return response.read(16 * 1024 * 1024 + 1)


def _report_from_artifact(blob):
    """Read only the audited report, never interpret arbitrary CSV as completion."""
    if len(blob) > 16 * 1024 * 1024:
        raise ValueError("Artifact exceeds notification size limit")
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        names = [name for name in archive.namelist()
                 if name.rsplit("/", 1)[-1] == "scan_execution_report.json"]
        if len(names) != 1:
            raise ValueError("Missing or ambiguous scan_execution_report.json")
        meta = archive.getinfo(names[0])
        if meta.file_size > 128 * 1024:
            raise ValueError("Scan report exceeds limit")
        data = json.loads(archive.read(meta).decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Scan report must be a JSON object")
    return data


def _job_for_scan(jobs, scan):
    expected = "PDUFA #" + scan + " " + SCANS[scan]
    matches = [job for job in jobs if job.get("name") == expected]
    # An absent/ambiguous job must not be silently marked successful.
    return matches[0] if len(matches) == 1 else None


def _completion(scan, run, job, report):
    """Return subject/body using truthful status, coverage counts, missing sources."""
    finished = _iso((job or {}).get("completed_at")) or _iso(run.get("updated_at")) or datetime.now(timezone.utc)
    began = _iso((job or {}).get("started_at")) or _iso(run.get("run_started_at")) or finished
    elapsed = max(0.0, (finished - began).total_seconds())
    outcome = (job or {}).get("conclusion", "missing")
    if report is None:
        status = "FAILED" if outcome != "success" else "UNVERIFIED"
        details = "Fresh collector report unavailable. No scan counts can be verified."
    elif report.get("scan") != scan or report.get("scan_kind") != "CLINICAL_SOURCE_COLLECTION_ONLY":
        status = "UNVERIFIED"
        details = "Report identity or scope mismatch; source counts not trusted."
    else:
        status, details = report_summary(
            report, 0 if outcome == "success" else 1, True, full_scope=True
        )
        if outcome != "success":
            status = "FAILED"
            details += "\nThe collector GitHub job did not succeed."
        elif status == "COMPLETE":
            status = "PARTIAL"  # A clinical collector alone is not a full baseline.
        studies = report.get("studies_checked")
        if isinstance(studies, int) and not isinstance(studies, bool):
            details += f"\nRegistry studies checked: {studies}"
        collector = report.get("collector_status")
        if collector:
            details += "\nCollector status: " + str(collector)[:60]
        warning_count = report.get("companies_with_warnings")
        if isinstance(warning_count, int):
            details += f"\nCompanies with warnings: {warning_count}"
    details += "\nGitHub job outcome: " + str(outcome)
    details += "\nBaseline: NOT VERIFIED / CLINICAL SOURCE ONLY."
    details += "\nMissing source families: " + ", ".join(MISSING_SOURCES)
    details += "\nCollector artifacts are in GitHub Actions; production dashboard inputs were not updated automatically."
    details += "\nView this scan: " + str(run.get("html_url", "https://github.com/pdufa/pdufa-command-center/actions"))
    subject, body = compose_end(scan, "CLINICAL SOURCE ONLY", str(run["id"]), finished, status, details, elapsed)
    return status, subject, body


def _fetch_run(repo, run_id, token, *, getter=_get_json, downloader=_get_bytes):
    base = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"
    run = getter(base, token)
    if run.get("name") != WORKFLOW_NAME or str(run.get("id")) != str(run_id):
        raise ValueError("This is not the authorized PDUFA collector workflow")
    if run.get("status") != "completed":
        raise ValueError("Collector workflow run is not complete")
    jobs_doc = getter(base + "/jobs?per_page=100", token)
    artifacts_doc = getter(base + "/artifacts?per_page=100", token)
    jobs = jobs_doc.get("jobs", [])
    artifacts = artifacts_doc.get("artifacts", [])
    results = []
    for scan in SCANS:
        job = _job_for_scan(jobs, scan)
        expected_artifact = f"clinical-scan-{scan}-{run_id}"
        named = [a for a in artifacts
                 if a.get("name") == expected_artifact and not a.get("expired", False)]
        report = None
        problem = None
        if len(named) == 1:
            try:
                blob = downloader(named[0]["archive_download_url"], token)
                report = _report_from_artifact(blob)
            except (KeyError, OSError, ValueError, zipfile.BadZipFile,
                    urllib.error.URLError) as exc:
                problem = type(exc).__name__
        else:
            problem = "missing_or_ambiguous_artifact"
        status, subject, body = _completion(scan, run, job, report)
        if problem:
            body += "\nArtifact parsing: " + problem + "\n"
        results.append((scan, status, subject, body))
    return results


def main():
    # workflow_run and manual workflow_dispatch both target exactly one run ID.
    try:
        with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as handle:
            event = json.load(handle)
        requested = event.get("inputs", {}).get("run_id")
        run_id = requested or event.get("workflow_run", {}).get("id")
        if not re.fullmatch(r"[1-9][0-9]{0,19}", str(run_id)):
            raise ValueError("Missing or invalid completed run ID")
        repo = os.environ["GITHUB_REPOSITORY"]
        if repo != "pdufa/pdufa-command-center":
            raise ValueError("Unexpected GitHub repository")
        token = os.environ["GH_TOKEN"]
        # Fail clearly if SMTP is not configured. Never print credential values.
        settings = EmailSettings.from_env()
        results = _fetch_run(repo, str(run_id), token)
    except (KeyError, OSError, ValueError, EmailSetupError,
            urllib.error.URLError) as exc:
        print("::error::PDUFA END notifier could not initialize: " + type(exc).__name__,
              file=sys.stderr)
        return 2
    failed = False
    for scan, status, subject, body in results:
        try:
            answer = send_email(settings, subject, body)
            print(f"PDUFA #{scan}: {status}; END email {answer['status']}; "
                  "submission is not proof of inbox delivery")
        except EmailSendError:
            failed = True
            print(f"::error::PDUFA #{scan}: END email failed or outcome unconfirmed",
                  file=sys.stderr)
            # Do not retry blindly: provider may have accepted the email.
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

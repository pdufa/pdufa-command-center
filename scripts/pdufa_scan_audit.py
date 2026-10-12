"""Publish auditable nightly clinical scan results for the Streamlit dashboard.

This validates archived scanner reports against their matching source-state
JSON. It does NOT verify FDA/SEC/issuer/market evidence or certify full coverage.
"""
import argparse
import io
import json
import os
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO = "pdufa/pdufa-command-center"
SCANS = {"2": ("PIPELINE", "all_phase_scan_state.json"),
         "3": ("PRE3", "phase_pipeline_state.json"),
         "4": ("POST3", "phase3_intake_status.json")}
MISSING_FAMILIES = [
    "FDA regulatory decision/date verification",
    "SEC financing and dilution verification",
    "issuer press release verification",
    "cash and runway verification",
    "complete market, ownership and short-interest verification",
    "issuer/program identity and complete source coverage audit",
]
MAX_ZIP = 100 * 1024 * 1024
MAX_JSON = 1024 * 1024


def now():
    return datetime.now(timezone.utc).isoformat()


def github(url, token):
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "pdufa-nightly-scan-audit",
    })
    with urllib.request.urlopen(req, timeout=90) as response:
        contents = response.read(MAX_ZIP + 1)
    if len(contents) > MAX_ZIP:
        raise ValueError("GitHub response exceeded audit download limit")
    return contents


def api(path, token):
    return json.loads(github("https://api.github.com/repos/" + REPO + path, token))


def archive_json(blob, basename):
    if len(blob) > MAX_ZIP:
        raise ValueError("Artifact too large")
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        matches = [x for x in archive.infolist()
                   if not x.is_dir() and x.filename.rsplit("/", 1)[-1] == basename]
        if len(matches) != 1:
            raise ValueError("Missing or ambiguous " + basename)
        if matches[0].file_size > MAX_JSON:
            raise ValueError("Report JSON is too large")
        result = json.loads(archive.read(matches[0]).decode("utf-8"))
        if not isinstance(result, dict):
            raise ValueError("Report JSON is not an object")
        return result


def nonnegative_count(value):
    return type(value) is int and value >= 0


def inspect_artifact(scan, artifact, token):
    row = {
        "scan": scan, "label": SCANS[scan][0], "status": "UNVERIFIED",
        "artifact_integrity": "NOT_CHECKED", "run_id": None,
        "new_records": None, "changed_trials_this_execution": None,
        "errors_count": None, "issues": [], "metrics": {},
    }
    try:
        blob = github(artifact["archive_download_url"], token)
        report = archive_json(blob, "nightly-clinical-" + scan + ".json")
        state = archive_json(blob, SCANS[scan][1])
        issues = []
        if str(report.get("scan")) != scan:
            issues.append("Scan identifier differs from artifact identifier")
        if report.get("scan_kind") != "CLINICAL_SOURCE_COLLECTION_ONLY":
            issues.append("Unexpected scan kind")
        if report.get("full_coverage_verified") is not False:
            issues.append("All-source coverage flag missing or invalid")
        expected_errors = state.get("errors", [])
        if not isinstance(expected_errors, list):
            issues.append("Source error list invalid")
        elif report.get("errors_count") != len(expected_errors):
            issues.append("Source/report error counts disagree")
        if report.get("collector_status") != state.get("status"):
            issues.append("Source/report collector statuses disagree")
        if report.get("collector_exit_code") != 0:
            issues.append("Collector exited unsuccessfully")
        for field in ("errors_count", "new_records", "changed_trials_this_execution",
                      "studies_checked", "companies_checked", "registry_companies"):
            value = report.get(field)
            if value is not None and not nonnegative_count(value):
                issues.append("Invalid count: " + field)
        if report.get("status") not in ("PARTIAL", "FAILED"):
            issues.append("Unexpected coverage status in clinical-only report")
        row.update({
            "status": ("PARTIAL" if report.get("status") == "PARTIAL" and not issues
                       else "FAILED"),
            "artifact_integrity": "PASS" if not issues else "ISSUES",
            "new_records": report.get("new_records"),
            "changed_trials_this_execution": report.get("changed_trials_this_execution"),
            "errors_count": report.get("errors_count"),
            "collector_status": report.get("collector_status"),
            "collected_at_utc": report.get("created_at_utc"),
            "issues": issues,
            "metrics": {k: report[k] for k in (
                "companies_checked", "companies_due", "studies_checked",
                "tracked_trials_checked", "tracked_trials_total", "matched_trials",
                "matched_posted_results", "registry_companies",
                "companies_with_warnings", "tracked_trials_with_warnings",
                "market_cap_source_unavailable")
                if nonnegative_count(report.get(k))},
        })
    except Exception as exc:
        row["status"] = "UNVERIFIED"
        row["artifact_integrity"] = "FAILED"
        row["issues"] = ["Cannot validate archived artifact: " + type(exc).__name__]
    return row


def previous_artifact(scan, previous_row, token):
    """Find the original archive for a previously published per-scan result."""
    source_id = previous_row.get("run_id")
    if type(source_id) is not int or source_id <= 0:
        return None
    try:
        response = api("/actions/runs/" + str(source_id) + "/artifacts?per_page=100", token)
    except Exception:
        return None
    expected = "nightly-clinical-" + scan + "-" + str(source_id)
    for artifact in response.get("artifacts", []):
        if artifact.get("name") == expected and not artifact.get("expired"):
            return artifact
    return None


def verified_total(rows, key):
    """Missing values must stay unknown; never convert missing counts to zero."""
    values = [row.get(key) for row in rows]
    return sum(values) if values and all(nonnegative_count(v) for v in values) else None


def gather(run_id, token, prior=None):
    run = api("/actions/runs/" + str(run_id), token)
    artifacts = api("/actions/runs/" + str(run_id) + "/artifacts?per_page=100", token)
    prior = prior if isinstance(prior, dict) else {}
    old_rows = {str(x.get("scan")): x for x in prior.get("scans", [])
                if isinstance(x, dict) and str(x.get("scan")) in SCANS}
    artifact_map = {}
    for item in artifacts.get("artifacts", []):
        name = str(item.get("name", ""))
        for scan in SCANS:
            if name == "nightly-clinical-" + scan + "-" + str(run_id) and not item.get("expired"):
                artifact_map[scan] = item
    rows = []
    for scan, (label, _) in SCANS.items():
        if scan in artifact_map:
            row = inspect_artifact(scan, artifact_map[scan], token)
            row["run_id"] = int(run_id)
            row["run_url"] = run.get("html_url")
        elif scan in old_rows:
            earlier = old_rows[scan]
            archived = previous_artifact(scan, earlier, token)
            if archived is not None:
                row = inspect_artifact(scan, archived, token)
                row["run_id"] = earlier.get("run_id")
                row["run_url"] = earlier.get("run_url")
            else:
                row = {
                    "scan": scan, "label": label, "status": "UNVERIFIED",
                    "artifact_integrity": "MISSING", "run_id": earlier.get("run_id"),
                    "run_url": earlier.get("run_url"),
                    "issues": ["Previously published artifact is missing, expired or inaccessible"],
                    "metrics": {}, "new_records": None,
                    "changed_trials_this_execution": None, "errors_count": None,
                }
        else:
            row = {"scan": scan, "label": label, "status": "UNVERIFIED",
                   "artifact_integrity": "MISSING", "run_id": None,
                   "issues": ["No audited artifact has been published for this scan"],
                   "metrics": {}, "new_records": None,
                   "changed_trials_this_execution": None, "errors_count": None}
        rows.append(row)
    failures = [x for x in rows if x["status"] in ("FAILED", "UNVERIFIED")]
    integrity = ("ISSUES" if failures or run.get("conclusion") not in ("success", None)
                 else "PASS")
    # COMPLETE is categorically forbidden with this clinical-only source set.
    coverage = ("FAILED" if any(x["status"] == "FAILED" for x in rows)
                else "UNVERIFIED" if any(x["status"] == "UNVERIFIED" for x in rows)
                else "PARTIAL")
    metrics = {"new_records": verified_total(rows, "new_records"),
               "changed_trials": verified_total(rows, "changed_trials_this_execution"),
               "errors": verified_total(rows, "errors_count")}
    history = [h for h in prior.get("history", []) if isinstance(h, dict)
               and h.get("run_id") != int(run_id)][:29]
    history.insert(0, {
        "run_id": int(run_id), "run_url": run.get("html_url"),
        "started_at_utc": run.get("run_started_at") or run.get("created_at"),
        "run_conclusion": run.get("conclusion"),
        "status": coverage, **metrics,
    })
    return {
        "schema_version": 1, "updated_at_utc": now(),
        "latest_run_id": int(run_id), "latest_run_url": run.get("html_url"),
        "latest_run_started_at_utc": run.get("run_started_at") or run.get("created_at"),
        "latest_run_conclusion": run.get("conclusion"),
        "scope": "CLINICAL_SCANS_2_3_4_ONLY",
        "status": coverage,
        "verification": {
            "checked_at_utc": now(),
            "artifact_integrity": integrity,
            "all_source_coverage": "NOT_VERIFIED",
            "description": "Archived clinical reports checked against source-state JSON; no independent FDA/SEC/issuer/market verification.",
        },
        "scans": rows, "metrics": metrics,
        "missing_required_source_families": MISSING_FAMILIES,
        "history": history,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run-id", type=int, required=True)
    p.add_argument("--out", type=Path, default=Path("data/nightly_scan_report.json"))
    p.add_argument("--only-scan", choices=["ALL", "2", "3", "4"], default="ALL")
    p.add_argument("--verify-only", action="store_true")
    args = p.parse_args()
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required to validate archived scan reports")
    prior = {}
    if args.out.exists():
        try:
            prior = json.loads(args.out.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    result = gather(args.run_id, token, prior=prior)
    if args.verify_only and args.only_scan != "ALL":
        keep = {r["scan"]: r for r in prior.get("scans", [])}
        result["scans"] = [r if r["scan"] == args.only_scan else keep.get(r["scan"], r)
                           for r in result["scans"]]
        result["verification"]["description"] += (
            " Targeted scan " + args.only_scan + " audited; other scans retain prior results.")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temp = args.out.with_suffix(".json.tmp")
    temp.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    temp.replace(args.out)
    print(json.dumps({"status": result["status"], "integrity": result["verification"]["artifact_integrity"],
                      "run_id": args.run_id, "scans": len(result["scans"])}, indent=2))


if __name__ == "__main__":
    main()

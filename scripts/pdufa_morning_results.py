"""Read-only 6 AM Pacific report of *published* overnight scan evidence.

No collection, trading, alerts, or source promotion occurs here.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")


def timestamp(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


def _int_or_none(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def make_snapshot(clinical, source, *, gem=None, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Snapshot time must be timezone aware")
    now = now.astimezone(timezone.utc)
    local = now.astimezone(PACIFIC)
    # At morning publication, tonight's most recent scheduled window started
    # 8:30 PM on the preceding calendar day in LA.
    morning = local.replace(hour=6, minute=0, second=0, microsecond=0)
    day_before = morning.date() - timedelta(days=1)
    window_start = datetime(
        day_before.year, day_before.month, day_before.day, 20, 30,
        tzinfo=PACIFIC,
    )
    cutoff_utc = window_start.astimezone(timezone.utc)
    ctime = timestamp(clinical.get("updated_at_utc"))
    stime = timestamp(source.get("updated_at_utc"))
    clinical_fresh = bool(ctime and cutoff_utc <= ctime <= now)
    source_fresh = bool(stime and cutoff_utc <= stime <= now)
    if clinical_fresh and source_fresh:
        readiness = "OVERNIGHT_REPORTS_PUBLISHED_WITH_EVIDENCE_GAPS"
    elif clinical_fresh:
        readiness = "SOURCE_VERIFICATION_PENDING_OR_STALE"
    elif source_fresh:
        readiness = "CLINICAL_REPORT_PENDING_OR_STALE"
    else:
        readiness = "OVERNIGHT_REPORTS_PENDING_OR_STALE"
    scans = clinical.get("scans", [])
    scanned = {
        str(r.get("scan")): {
            "collector_status": str(r.get("collector_status", "UNKNOWN")),
            "new_records": _int_or_none(r.get("new_records")),
            "changed_trials": _int_or_none(r.get("changed_trials_this_execution")),
        }
        for r in scans if isinstance(r, dict) and str(r.get("scan", "")) in {"2", "3", "4"}
    } if clinical_fresh else {}
    gem = gem if isinstance(gem, dict) else {}
    gem_time = timestamp(gem.get("generated_at_utc"))
    gem_fresh = bool(gem.get("scan") == "GEM" and
                     gem.get("trade_entry_authorized") is False and
                     gem.get("status") in ("PARTIAL", "FAILED") and
                     gem_time and cutoff_utc <= gem_time <= now)
    gem_registry = gem.get("clinical_registry") if gem_fresh else {}
    gem_registry = gem_registry if isinstance(gem_registry, dict) else {}
    cmp = source.get("comparison", {}) if source_fresh else {}
    if not isinstance(cmp, dict):
        cmp = {}
    recheck = source.get("public_ir_sec_recheck", {}) if source_fresh else {}
    if not isinstance(recheck, dict):
        recheck = {}
    due = _int_or_none(source.get("required_findings_due")) if source_fresh else None
    unresolved = _int_or_none(source.get("required_findings_unresolved")) if source_fresh else None
    cleared = due - unresolved if due is not None and unresolved is not None and unresolved <= due else None
    percentage = round(100 * cleared / due, 1) if cleared is not None and due else None
    return {
        "schema_version": 1,
        "report_type": "PDUFA_6AM_PACIFIC_MORNING_RESULTS",
        "scheduled_display_time_pacific": "06:00",
        "snapshot_date_pacific": morning.date().isoformat(),
        "generated_at_utc": now.isoformat(),
        "generated_at_pacific": local.isoformat(),
        "overnight_scan_window_started_pacific": window_start.isoformat(),
        "readiness": readiness,
        "clinical": {
            "overnight_report_published": clinical_fresh,
            "published_at_utc": ctime.isoformat() if ctime else None,
            "status": clinical.get("status") if clinical_fresh else "PENDING_OR_STALE",
            "runs": scanned,
            "source_run_url": clinical.get("latest_run_url") if clinical_fresh else None,
        },
        "sources": {
            "overnight_report_published": source_fresh,
            "published_at_utc": stime.isoformat() if stime else None,
            "status": source.get("status") if source_fresh else "PENDING_OR_STALE",
            "required_findings_due": due,
            "required_findings_cleared": cleared,
            "required_findings_unresolved": unresolved,
            "required_source_coverage_percent": percentage,
            "newly_resolved_claims": _int_or_none(cmp.get("resolved_count")),
            "new_claims": _int_or_none(cmp.get("new_count")),
            "public_ir_sec_recheck_status": recheck.get("status") if source_fresh else "PENDING_OR_STALE",
            "public_ir_sec_leads_checked": _int_or_none(recheck.get("leads_checked")) if source_fresh else None,
            "sec_transactions_verified": _int_or_none(recheck.get("sec_transactions_verified")) if source_fresh else None,
            "source_run_url": source.get("latest_run_url") if source_fresh else None,
        },
        "gem": {
            "overnight_report_published": gem_fresh,
            "status": gem.get("status") if gem_fresh else "PENDING_OR_STALE",
            "collector_status": gem.get("collector_status") if gem_fresh else "NOT REPORTED",
            "new_records": _int_or_none(gem_registry.get("new_records")) if gem_fresh else None,
            "stored_results": _int_or_none(gem_registry.get("stored_results")) if gem_fresh else None,
            "verified_phase3_tracking": _int_or_none(gem.get("verified_phase3_tracking")) if gem_fresh else None,
            "awaiting_second_financing": _int_or_none(gem.get("awaiting_second_financing")) if gem_fresh else None,
            "run_url": gem.get("run_url") if gem_fresh else None,
            "all_source_trade_verification": "NOT VERIFIED",
        },
        "trade_entry_eligible_from_morning_snapshot": False,
        "notice": "Read-only snapshot. SEC-verified individual closings do not prove two independent post-Phase-3 financings. A pending/stale component must not be represented as newly verified.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--clinical", type=Path, default=Path("data/nightly_scan_report.json"))
    parser.add_argument("--sources", type=Path, default=Path("data/pdufa_source_report.json"))
    parser.add_argument("--out", type=Path, default=Path("data/pdufa_am_6am_results.json"))
    parser.add_argument("--gem", type=Path, default=Path("data/gem_scan_block_report.json"))
    args = parser.parse_args(argv)
    def read(path):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            return obj if isinstance(obj, dict) else {}
        except (OSError, ValueError):
            return {}
    result = make_snapshot(read(args.clinical), read(args.sources), gem=read(args.gem))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"snapshot_date_pacific": result["snapshot_date_pacific"],
                      "readiness": result["readiness"],
                      "results_file": str(args.out)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

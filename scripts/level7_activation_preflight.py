"""Read-only Level 7 activation preflight; no database or report writes.

Usage: python scripts/level7_activation_preflight.py --db /secure/evidence.sqlite3
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path

from level7_store_diagnostic import inspect
from level7_focus_report import run


def check(db_path: Path, report_path: Path | None = None) -> dict:
    store = inspect(db_path)
    result = {"database": store, "reportStatus": "BLOCKED",
              "dashboardStatus": "NOT_CONFIGURED"}
    if store["status"] != "LEVEL7_STORE_FOUND":
        return result
    try:
        report = run(db_path)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        result["reportStatus"] = "INVALID_EVIDENCE_OR_ROSTER"
        return result
    result["reportStatus"] = "READY_TO_GENERATE"
    result["focusTrials"] = report["total"]
    result["trialsWithEvidence"] = report["trialsWithEvidence"]
    if report_path is not None:
        if not report_path.is_file():
            result["dashboardStatus"] = "REPORT_FILE_MISSING"
        else:
            try:
                served = json.loads(report_path.read_text(encoding="utf-8"))
                if (served.get("kind") == report["kind"]
                        and served.get("rosterAsOf") == report["rosterAsOf"]
                        and served.get("trials") == report["trials"]
                        and served.get("trialsWithEvidence") == report["trialsWithEvidence"]
                        and served.get("total") == 32):
                    result["dashboardStatus"] = "REPORT_MATCHES_EVIDENCE"
                else:
                    result["dashboardStatus"] = "REPORT_STALE_OR_MISMATCHED"
            except (OSError, ValueError, TypeError, AttributeError):
                result["dashboardStatus"] = "REPORT_INVALID"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()
    result = check(args.db, args.report)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["reportStatus"] == "READY_TO_GENERATE" else 1


if __name__ == "__main__":
    raise SystemExit(main())

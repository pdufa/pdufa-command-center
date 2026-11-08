#!/usr/bin/env python3
"""Fail-closed identity guard for retired P3 and P3 POST-DATA workspaces.

Clinical Phase 3 evidence, historic filenames, archived records and the existing
FOCUS sheet are NOT retired. This guard checks active destinations/navigation,
not old filenames or immutable scientific evidence.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(ok: bool, message: str) -> None:
    if not ok:
        raise AssertionError(message)


def main() -> None:
    for path in ("AGENTS.md", ".github/copilot-instructions.md"):
        policy = read(path)
        require("P3 POST-DATA" in policy and "retired" in policy.lower(),
                f"{path}: retirement instructions missing")
        require("FOCUS" in policy, f"{path}: canonical FOCUS instructions missing")

    focus = read("new-platform/frontend/app/focus/page.tsx")
    retired = read("new-platform/frontend/app/p3-post-data/page.tsx")
    nav = read("new-platform/frontend/app/GlobalNavigation.tsx")
    require("export default function FocusPage" in focus and "snapshot.records" in focus,
            "FOCUS must own the active trial roster")
    require("../p3-post-data/page" not in focus,
            "FOCUS must never re-export the retired page")
    require('permanentRedirect("/focus")' in retired and "snapshot.records" not in retired,
            "Legacy P3 URL must be redirect-only, never a second active roster")
    require('label:"FOCUS"' in nav and 'label:"POOL"' in nav,
            "Navigation must retain POOL and FOCUS")
    require(not re.search(r'label:\s*["\x27]P3(?: POST-DATA)?["\x27]', nav),
            "Retired P3 navigation reintroduced")

    promoter = read("scripts/auto_promote_p3_post_data.py")
    publisher = read("scripts/sync_p3_post_data_from_google_sheet.py")
    require('SHEET_NAME = "FOCUS"' in promoter,
            "Existing exact-NCT source intake must target FOCUS, not P3")
    require(bool(re.search(r'RANGE\s*=\s*"FOCUS!A4:[A-Z]{1,2}"', publisher)),
            "FOCUS source publisher must read the active FOCUS tab")
    require('SHEET_NAME = "P3"' not in promoter and 'P3 POST-DATA!' not in publisher,
            "Retired P3 spreadsheet destination used")

    workflow_titles = {
        ".github/workflows/p3-full-pool-discovery.yml": "POOL Master Evidence Nightly Discovery",
        ".github/workflows/p3-post-data-google-sheet-sync.yml": "FOCUS Google Sheets → Website source snapshot",
        ".github/workflows/p3-full-pool-tests.yml": "POOL master discovery safety checks",
        ".github/workflows/p3-auto-promotion-tests.yml": "FOCUS exact-NCT intake safety checks",
    }
    for path, title in workflow_titles.items():
        require(f"name: {title}" in read(path),
                f"{path}: active workflow still identifies a retired spreadsheet")

    print("PASS: P3/P3 POST-DATA retired as active workspaces; POOL and FOCUS preserved")


if __name__ == "__main__":
    main()

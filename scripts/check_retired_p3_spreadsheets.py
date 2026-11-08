#!/usr/bin/env python3
"""Enforce the owner's permanent retirement of obsolete P3 spreadsheet identities.

This is a narrow structural gate. Phase 3 clinical evidence is still active, and
legacy file names may remain as long as their effective source is FOCUS.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")

def main() -> None:
    agents = read("AGENTS.md")
    instructions = read(".github/copilot-instructions.md")
    for label, contents in (("AGENTS.md", agents), ("Copilot instructions", instructions)):
        assert "P3 POST-DATA" in contents and "retired" in contents.lower(), (
            f"{label}: permanent spreadsheet retirement directive missing"
        )
        assert "FOCUS" in contents, f"{label}: canonical FOCUS identity missing"

    focus = read("new-platform/frontend/app/focus/page.tsx")
    legacy = read("new-platform/frontend/app/p3-post-data/page.tsx")
    assert "export default function FocusPage" in focus
    assert 'from "../p3-post-data/page"' not in focus
    assert 'const source="https://docs.google.com/spreadsheets/d/' in focus
    assert "gid=202611061" in focus, "Active FOCUS source tab must remain the canonical target"
    assert 'permanentRedirect("/focus")' in legacy
    assert "snapshot.records" not in legacy, "Retired URL must not render a separate roster"

    # Older script filenames remain only for continuity. The exact active tab
    # used by both the promotion and the site roster import must be FOCUS.
    promoter = read("scripts/auto_promote_p3_post_data.py")
    publisher = read("scripts/sync_p3_post_data_from_google_sheet.py")
    assert 'SHEET_NAME = "FOCUS"' in promoter
    assert 'RANGE = "FOCUS!A4:AB"' in publisher
    assert 'SHEET_NAME = "P3"' not in promoter
    assert "P3 POST-DATA!" not in publisher
    print("PASS: retired P3 spreadsheet identities are not active FOCUS routes or write targets")

if __name__ == "__main__":
    main()

"""Release-only guard: scientific WT links must not alter existing preset code.

Run on GitHub Actions with origin/main fetched. Read-only; never calls an API or
writes to a database, preset, branch or release target.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

WORKSPACE = "new-platform/frontend/app/Workspace.tsx"
SELF = "new-platform/frontend/tests/scientific_wt_preset_release_parity.py"
WORKFLOW = ".github/workflows/scientific-wt-preset-release-parity.yml"
ADDED_LINKS = (
    '              {selectedRecord && trialSheetUrl(selectedRecord) && <a href={trialSheetUrl(selectedRecord)} className="trial-sheet-link">Open trial science · 20 levels / 40 assessments / two evidence-readiness grades ↗</a>}',
    '              {selectedRecord && !trialSheetUrl(selectedRecord) && <small className="subtle">Trial-science dossier unavailable: no exact NCT linked to this program.</small>}',
)
PROTECTED_PATH = re.compile(r"(?:^|[/._-])(?:presets?|restrictions?|fs[-_]?fa)(?:[/._-]|$)", re.I)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True, encoding="utf-8")


def verify() -> dict:
    main = git("show", "origin/main:" + WORKSPACE)
    current = Path(WORKSPACE).read_text(encoding="utf-8")
    lines = current.splitlines(keepends=True)
    indices = []
    for expected in ADDED_LINKS:
        found = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == expected]
        if len(found) != 1:
            raise ValueError("Expected science-only WT link missing or repeated")
        indices.extend(found)
    if indices[1] != indices[0] + 1:
        raise ValueError("Science-only WT links were moved apart")
    if any(expected in main for expected in ADDED_LINKS):
        raise ValueError("Production baseline already includes reviewed science links")
    normalized = "".join(line for i, line in enumerate(lines) if i not in indices)
    if normalized != main:
        raise ValueError("Existing WT/GEM/FS-FA workspace logic differs from production baseline")
    changed = git("diff", "--name-only", "origin/main...HEAD").splitlines()
    changed_protected = sorted(
        path for path in changed
        if path not in (SELF, WORKFLOW) and PROTECTED_PATH.search(path)
    )
    if changed_protected:
        raise ValueError("Preset/restriction files changed in science release candidate")
    return {
        "status": "PASS",
        "baseline": "origin/main",
        "workspace_presets_byte_identical_after_removing_two_reviewed_links": True,
        "prohibited_preset_or_restriction_file_changes": 0,
        "trial_links_added": 2,
        "production_modified": False,
        "qualification_presets_modified": False,
    }


if __name__ == "__main__":
    try:
        print(json.dumps(verify(), sort_keys=True))
    except (ValueError, OSError, subprocess.CalledProcessError, UnicodeError) as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__,
                          "production_modified": False}, sort_keys=True))
        sys.exit(1)

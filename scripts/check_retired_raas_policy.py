#!/usr/bin/env python3
"""Prevent reactivation of retired scoring while preserving read-only history.

Run in every CI, Codex or deployment session. This scans the checked-out
repository rather than trusting a dated inventory. It distinguishes archives
from sources that are reachable by current analysis, deployment and scans.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/"new-platform"/"frontend"
BACK=ROOT/"new-platform"/"backend"
ACTIVE=[
    BACK/"app"/name for name in (
        "main.py","medical_continuous.py","medical_on_demand.py",
        "medical_advanced_runtime.py","installation_monitor.py",
    )
]+[
    WEB/name for name in (
        "app/page.tsx","app/GlobalNavigation.tsx","app/main/page.tsx",
        "app/p3-post-data/page.tsx","app/focus/AnalyzeNowTrial.tsx",
        "app/medical-intelligence-preview/page.tsx",
        "app/medical-intelligence-preview/ContinuousMedicalAnalysis.tsx",
        "app/analyze-now/page.tsx","app/api/analyze-now/route.ts",
        "app/api/main/installation-progress/route.ts",
        "lib/main-install-progress.ts",
        "lib/phase-first-report.ts","lib/phase-first-clinical.ts",
        "app/phase-first/PhaseFirstTable.tsx",
        "app/api/phase-first/route.ts",
        "app/api/phase3-active-trial-scores/route.ts",
        "app/predictions/page.tsx",
    )
]
# Cover every current Next.js page except explicitly retired paths,
# so new pages cannot silently reinstate old scoring.
for page in sorted((WEB/"app").rglob("page.tsx")):
    rel=page.relative_to(WEB/"app")
    if not any(part.lower().startswith("raas-") for part in rel.parts):
        if page not in ACTIVE:
            ACTIVE.append(page)

FORBIDDEN=re.compile(r"raas",re.I)
EXE=re.compile(r"(?:python|node|bash|sh|uv|npm|pnpm)[^\n]*?(?:raas[\-_]|raas/)|uses:\s*[^\n]*raas",re.I)
WORKFLOW=ROOT/".github"/"workflows"
HISTORY_PREFIXES=("new-platform/frontend/data/","new-platform/frontend/lib/raas",
    "new-platform/frontend/tests/raas","data/raas","docs/raas",
    "tests/raas","scripts/raas","new-platform/frontend/app/raas-",
    "new-platform/frontend/app/api/raas-")
ERRORS=[]


def check_file(path,kind):
    if not path.exists():
        ERRORS.append("Required "+kind+" file missing: "+str(path.relative_to(ROOT)))
        return
    content=path.read_text(encoding="utf-8")
    if FORBIDDEN.search(content):
        for no,line in enumerate(content.splitlines(),1):
            if FORBIDDEN.search(line):
                ERRORS.append("Retired scoring referenced in active "+kind+
                    " "+str(path.relative_to(ROOT))+":"+str(no))


def run():
    if not (ROOT/"AGENTS.md").exists() or not (ROOT/".github/copilot-instructions.md").exists():
        ERRORS.append("Codex/Copilot permanent retirement instructions missing")
    for path in ACTIVE:
        check_file(path,"source")
    proxy=WEB/"proxy.ts"
    if not proxy.exists():
        ERRORS.append("Retired UI/API execution-blocking Proxy missing")
    else:
        code=proxy.read_text(encoding="utf-8")
        if "status:410" not in code or not re.search(r"raas\(\?:-",code):
            ERRORS.append("Legacy routes are not unconditionally retired with HTTP 410")
    for path in sorted(WORKFLOW.glob("*.yml")) + sorted(WORKFLOW.glob("*.yaml")):
        s=path.read_text(encoding="utf-8")
        if "raas" in path.name.lower():
            ERRORS.append("Executable retired workflow remains: "+path.name)
        if EXE.search(s.replace("python scripts/check_retired_raas_policy.py","")):
            ERRORS.append("Retired script referenced by a workflow: "+path.name)
    # New analysis must not import from preserved score snapshots,
    # including via aliases: explicit artifact references are disallowed.
    active=BACK/"app"/"medical_on_demand.py"
    if active.exists() and re.search(r"focus_legacy_score_snapshot|optional_legacy|historicalRaas|raasOverall",active.read_text(encoding="utf-8"),re.I):
        ERRORS.append("Analyze Now still depends on archived retired score records")
    # Historical data are deliberately not deleted.
    archives=[
        ROOT/"new-platform/frontend/data/raas-trial-score-history.json",
        ROOT/"new-platform/frontend/data/bottomOnlyScoreHistory20261107.json",
        BACK/"app"/"data"/"focus_legacy_score_snapshot.json",
    ]
    for p in archives:
        if not p.exists():
            ERRORS.append("Required immutable historical archive missing: "+str(p.relative_to(ROOT)))
    # Complete tree inventory: classify residual paths rather than
    # pretending all historical names disappeared from the codebase.
    legacy=[p for p in ROOT.rglob("*") if p.is_file() and FORBIDDEN.search(p.name)
            and not any(part in (".git","node_modules",".next","__pycache__") for part in p.parts)]
    print("Legacy named archival source/data files retained:",len(legacy))
    print("Reviewed live sources:",len(ACTIVE))
    print("Workflow files evaluated:",len(list(WORKFLOW.glob("*.yml")))+len(list(WORKFLOW.glob("*.yaml"))))
    if ERRORS:
        print("RETIRED_ARCHITECTURE_GUARD_FAILED",file=sys.stderr)
        for error in ERRORS[:70]:
            print(" - "+error,file=sys.stderr)
        if len(ERRORS)>70:
            print(" - ... "+str(len(ERRORS)-70)+" more",file=sys.stderr)
        return 1
    print("RETIRED_ARCHITECTURE_GUARD_PASS: no active dependencies, triggers, or UI references in guarded paths")
    return 0


if __name__=="__main__":
    raise SystemExit(run())

"""Pre-readout Phase 3 *manual source-review* worklist.

Creates an audit-friendly priority queue from already saved research rows.
A linked Phase 2 p-value improves review priority, but is NOT clinical
efficacy, a Phase 3 forecast or an automatically assigned score.
"""
from __future__ import annotations

from datetime import date
import re

ACTIVE = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION",
          "NOT_YET_RECRUITING"}
NCT = re.compile(r"^NCT\d{8}$")
COLUMNS = (
    "Ticker", "NCT ID", "Drug", "Indication",
    "Linked Phase 2 PRIMARY p", "Phase 2 PRIMARY evidence count",
    "Phase 2 PRIMARY registry sources", "NCT source",
    "Registry status", "Registry check", "Protocol check",
    "Company/program identity", "Market cap state",
    "Pre-readout research score /100", "Score status",
    "Needed before clinical score", "Review priority",
)


def scoring_review_queue(trials, limit=10):
    """Shortlist source-verified inputs for analyst review, never assert success.

    PRE PHASE 3 trials must be active Phase 3 studies with no posted registry
    results, and exactly attributed to their own ticker/NCT. Issuer release
    checking is a MANDATORY next step; registry activity alone cannot prove
    the corporate readout remains unreleased.
    """
    if not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("limit must be 1–100")
    out = []
    for item in trials or []:
        if not isinstance(item, dict):
            continue
        ticker = str(item.get("Ticker") or "").strip().upper()
        nct = str(item.get("NCT ID") or "").strip().upper()
        if (item.get("Trial phase") not in ("Phase 3", "Phase 2/3")
                or str(item.get("Registry status") or "").upper() not in ACTIVE
                or str(item.get("Registry results posted") or "").strip()
                or not re.fullmatch(r"[A-Z0-9.-]{1,15}", ticker)
                or not NCT.fullmatch(nct)
                or str(item.get("NCT source") or "") != f"https://clinicaltrials.gov/study/{nct}"):
            continue

        try:
            evidence_count = max(0, int(item.get("Phase 2 PRIMARY evidence count") or 0))
        except (ValueError, TypeError):
            evidence_count = 0
        has_p = evidence_count > 0
        fresh_registry = item.get("Registry check") == "RECENT"
        fresh_protocol = item.get("Protocol check") == "RECENT"
        verified_program = str(item.get("Company/program identity") or "").strip().upper() == "VERIFIED"
        eligible_cap = item.get("Market cap state") == "VERIFIED RECENT"
        steps = ["Issuer topline status: source-dated independent check",
                 "Confirm exact Phase 2 trial link, endpoint, effect size and clinical relevance",
                 "Review Phase 3 statistical design, safety, regulatory alignment, execution and quality"]
        if not has_p:
            steps.insert(1, "Locate linked Phase 2 PRIMARY analysis or document unavailable")
        if not fresh_protocol:
            steps.append("Refresh the Phase 3 protocol snapshot")
        if not fresh_registry:
            steps.append("Refresh the exact-NCT trial snapshot")
        if not verified_program:
            steps.append("Verify drug/issuer/program identity")
        if not eligible_cap:
            steps.append("Check current market cap and research-range eligibility")

        # Ranking determines *research order*, not a trading signal.
        priority = (int(has_p) * 4 + int(fresh_protocol) * 2
                    + int(fresh_registry) + int(verified_program)
                    + int(eligible_cap))
        record = {k: item.get(k, "") for k in COLUMNS}
        record.update({
            "Needed before clinical score": "; ".join(steps),
            "Review priority": priority,
            "Phase 2 PRIMARY evidence count": evidence_count,
            # The actual score stays unset until existing strict rubric passes.
            "Pre-readout research score /100": item.get("Pre-readout research score /100"),
        })
        out.append(record)
    out.sort(key=lambda r: (-r["Review priority"], r["Ticker"], r["NCT ID"]))
    # Avoid selecting a duplicate exact ticker/NCT trial snapshot.
    seen = set()
    unique = []
    for r in out:
        identity = (r["Ticker"], r["NCT ID"])
        if identity not in seen:
            unique.append(r)
            seen.add(identity)
        if len(unique) >= limit:
            break
    return unique

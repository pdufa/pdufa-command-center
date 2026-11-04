"""Fail-closed nightly monitoring for FDA-published submission actions, read-only.

Only publish dated FDA action markers after exact NDA match in Drugs@FDA.
Approval/TA status is not inferred from press releases, market news, or PDUFA
target dates. This source does not publish every review milestone or CRL.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PROGRAM_ID = "PDUFA-000069"
APPLICATION = "NDA219083"  # CYTK / MYQORZO, FDA original approval letter
FDA_APPLICATION_PAGE = (
    "https://www.accessdata.fda.gov/scripts/cder/daf/"
    "index.cfm?event=overview.process&ApplNo=219083"
)
SOURCE_URL = "https://open.fda.gov/apis/drug/drugsfda/"
WATCHED_CATEGORIES = [
    {"id": "original-approval", "title": "Initial FDA approval", "mode": "official_drugsfda"},
    {"id": "supplement-approval", "title": "Supplement approvals", "mode": "official_drugsfda"},
    {"id": "tentative-action", "title": "Tentative submission actions", "mode": "official_drugsfda"},
    {"id": "crl", "title": "Complete Response Letter", "mode": "separate_source_required"},
    {"id": "adcom", "title": "Advisory committee meetings and votes", "mode": "separate_source_required"},
    {"id": "pdufa-extension", "title": "PDUFA date changes or extensions", "mode": "separate_source_required"},
    {"id": "inspection", "title": "Manufacturing inspections", "mode": "separate_source_required"},
    {"id": "label", "title": "Label revisions and boxed warnings", "mode": "separate_source_required"},
    {"id": "rems", "title": "REMS approval or modifications", "mode": "separate_source_required"},
    {"id": "designation", "title": "Orphan, Breakthrough, Priority and Fast Track designations", "mode": "separate_source_required"},
    {"id": "submission", "title": "NDA/sNDA submissions and acceptance", "mode": "separate_source_required"},
    {"id": "review-letter", "title": "FDA review letters and information requests", "mode": "separate_source_required"},
    {"id": "resubmission", "title": "CRL resubmissions and withdrawal", "mode": "separate_source_required"},
]
FDA_DATE_RE = re.compile(r"^[0-9]{8}$")
NUM_RE = re.compile(r"^[0-9]{1,5}$")


def source_payload(timeout: float = 25) -> dict:
    query = urlencode({"search": 'application_number:"' + APPLICATION + '"', "limit": 10})
    url = "https://api.fda.gov/drug/drugsfda.json?" + query
    req = Request(url, headers={
        "User-Agent": "PDUFA-Command-Center-FDA-Action-Watcher/1.0 (research-only)",
        "Accept": "application/json",
    })
    with urlopen(req, timeout=timeout) as response:
        if response.status != 200:
            raise ValueError("Official FDA API returned non-200 status")
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("FDA response exceeded safe size")
        return json.loads(raw)


def extract_published_actions(payload: dict, as_of: date) -> list[dict]:
    rows = payload.get("results")
    if not isinstance(rows, list) or len(rows) != 1:
        raise ValueError("FDA source must contain exactly one application record")
    row = rows[0]
    if row.get("application_number") != APPLICATION:
        raise ValueError("FDA response did not match exact registered application")
    submissions = row.get("submissions")
    if not isinstance(submissions, list):
        raise ValueError("FDA application has no parseable submissions list")
    results = []
    seen = set()
    for sub in submissions:
        if not isinstance(sub, dict):
            continue
        kind = sub.get("submission_type")
        status = sub.get("submission_status")
        number = str(sub.get("submission_number", "")).strip()
        raw_date = sub.get("submission_status_date")
        if kind not in ("ORIG", "SUPPL") or status not in ("AP", "TA"):
            continue
        if not NUM_RE.fullmatch(number) or not isinstance(raw_date, str) or not FDA_DATE_RE.fullmatch(raw_date):
            raise ValueError("A potentially relevant FDA action has an invalid identity/date")
        action_date = date(int(raw_date[:4]), int(raw_date[4:6]), int(raw_date[6:]))
        if action_date > as_of:
            raise ValueError("FDA action has a future-dated status")
        if action_date < date(2025, 12, 19):
            continue
        # Original approval already exists as a source-linked CYTK event. Avoid duplication.
        if kind == "ORIG":
            continue
        key = (kind, number, status)
        if key in seen:
            raise ValueError("Duplicate FDA submission identity returned")
        seen.add(key)
        number_key = number.zfill(3)
        is_approval = status == "AP"
        date_string = action_date.isoformat()
        label = (
            "FDA supplement approval (NDA 219083, S-" + number_key + ")"
            if is_approval else
            "FDA tentative supplement action (NDA 219083, S-" + number_key + ")"
        )
        results.append({
            "id": "verified-openfda-nda219083-suppl-" + number,
            "date": date_string,
            "label": label,
            "chartLabel": ("FDA S-" + number_key + " AP") if is_approval else ("FDA S-" + number_key + " TA"),
            "detail": (
                "FDA Drugs@FDA submission status " + status +
                ". Exact supplement-to-MAPLE-HCM identity has not been independently verified; "
                "this marker represents the parent NDA submission only. "
                "Status date is not the source publication date."
            ),
            "source": FDA_APPLICATION_PAGE,
            "sourceDataset": SOURCE_URL,
            "sourceApplication": APPLICATION,
            "submissionType": kind,
            "submissionNumber": number,
            "submissionStatus": status,
            "category": "supplement-approval" if is_approval else "tentative-action",
            "planned": False,
        })
    return sorted(results, key=lambda e: (e["date"], e["id"]))


def merge_snapshot(old: dict, fetched: list[dict], checked_at: datetime) -> dict:
    previous = old.get("events", [])
    if not isinstance(previous, list):
        raise ValueError("Existing FDA marker history is invalid")
    events = {e["id"]: e for e in previous}
    for event in fetched:
        earlier = events.get(event["id"])
        if earlier and (earlier["date"] != event["date"] or
                        earlier.get("submissionStatus") != event["submissionStatus"]):
            raise ValueError("Official source changed previously stored status/date; manual audit required")
        events[event["id"]] = event
    return {
        "schemaVersion": 1,
        "programId": PROGRAM_ID,
        "applicationNumber": APPLICATION,
        "source": SOURCE_URL,
        "checkedAt": checked_at.astimezone(timezone.utc).isoformat(),
        "status": "SOURCE_CHECK_SUCCEEDED",
        "eventCount": len(events),
        "categories": WATCHED_CATEGORIES,
        "events": sorted(events.values(), key=lambda e: (e["date"], e["id"])),
        "limitations": (
            "Only Drugs@FDA approved/tentative supplementary submissions auto-plot. "
            "A public record can arrive after the FDA action. Other categories stay "
            "armed for separate official-source integration and produce no invented dates. "
            "NDA-level supplement approval is not proof of MAPLE-HCM-specific approval."
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Update published FDA overlay from exact NDA status actions")
    ap.add_argument("--out", default="new-platform/frontend/app/alpaca-cytk/fda-auto-events.json")
    args = ap.parse_args()
    now = datetime.now(timezone.utc)
    out = Path(args.out)
    old = json.loads(out.read_text()) if out.exists() else {}
    if old and (old.get("programId") != PROGRAM_ID or old.get("applicationNumber") != APPLICATION):
        raise SystemExit("Existing automatic FDA data belongs to another program/application")
    published = extract_published_actions(source_payload(), now.date())
    updated = merge_snapshot(old, published, now)
    out.parent.mkdir(parents=True, exist_ok=True)
    temp = out.with_suffix(".json.tmp")
    temp.write_text(json.dumps(updated, indent=2, sort_keys=True) + "\n")
    temp.replace(out)
    print(
        f"FDA exact application {APPLICATION}: {len(published)} source actions, "
        f"{updated['eventCount']} retained, checked {updated['checkedAt']}. "
        "Unpublished events were not marked as FDA actions."
    )


if __name__ == "__main__":
    main()

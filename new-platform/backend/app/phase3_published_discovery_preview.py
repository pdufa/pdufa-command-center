"""On-demand, read-only bridge from published scanner discoveries to research.

Never converts a scanner stage, date, or caller-provided VERIFIED string into
verified Phase 3/PDUFA evidence. Only server-maintained source attestations
may start research. A partial/stale workspace remains visible for discovery
but is categorically blocked from research.
"""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from urllib.parse import urlsplit

from .phase3_research_batch import MAX_BATCH, evaluate_candidate_batch
from .phase3_sheet_population_preview import build_sheet_population_preview

_CATALOG = Path(__file__).with_name("phase3_curated_announcements.json")
_ALLOWED_STAGES = (("GEM_JR", "GEM JR"), ("GEM", "GEM"), ("WT", "WT"))


def _reviewed_pair(record: object, *, target: str, as_of: date) -> tuple[dict, dict] | None:
    """Validate a curated, checked public announcement pair as of snapshot time."""
    if not isinstance(record, dict) or record.get("reviewerMethod") != "PRIMARY_PUBLIC_ISSUER_DISCLOSURE":
        return None
    try:
        reviewed = date.fromisoformat(record["reviewedOn"])
        p3, pdufa = record["phase3_results"], record["pdufa_assignment"]
        published = [date.fromisoformat(x["published_at"]) for x in (p3, pdufa)]
        event_dates = [date.fromisoformat(x["event_date"]) for x in (p3, pdufa)]
        target_day = date.fromisoformat(pdufa["pdufa_target_date"])
    except (KeyError, TypeError, ValueError):
        return None
    if not target or target_day.isoformat() != target:
        return None
    if any(d > as_of for d in [reviewed, *published, *event_dates]):
        return None
    if reviewed < max(published):
        return None
    for event in (p3, pdufa):
        if event.get("review_status") != "VERIFIED":
            return None
        url = event.get("source_url")
        if not isinstance(url, str):
            return None
        try:
            parsed = urlsplit(url)
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username
                    or parsed.password or parsed.fragment or any(ch.isspace() for ch in url)):
                return None
        except ValueError:
            return None
    return dict(p3), dict(pdufa)


def preview_published_discoveries(
    snapshot: dict, exact_keys: list[str], *, catalog: dict | None = None,
) -> dict:
    """Select <=200 exact published scanner identities without mutating state.

    Catalog entries are trusted *only* when stored server-side; never accept
    a catalog from an HTTP caller. The injection option exists for isolated tests.
    """
    if not isinstance(snapshot, dict):
        raise ValueError("Published workspace snapshot must be an object")
    if (not isinstance(exact_keys, list) or not exact_keys or len(exact_keys) > MAX_BATCH
            or any(not isinstance(k, str) or not k.strip() or len(k) > 512 for k in exact_keys)):
        raise ValueError("Select 1 to 200 nonempty exact identities")
    if len(set(exact_keys)) != len(exact_keys):
        raise ValueError("Duplicate requested exact identity")
    rows = snapshot.get("pipeline")
    if not isinstance(rows, list):
        raise ValueError("Published workspace pipeline must be a list")
    as_of = snapshot.get("asOf")
    try:
        cutoff = date.fromisoformat(as_of)
    except (TypeError, ValueError):
        raise ValueError("Published workspace snapshot has no valid as-of date") from None
    health = snapshot.get("sourceHealth") or {}
    health_state = health.get("state") if isinstance(health, dict) else None
    source_healthy = (snapshot.get("mode") == "LIVE_READ_ONLY_GITHUB_SOURCE"
                      and health_state == "COMPLETE_PUBLISHED"
                      and not health.get("issues"))
    if catalog is None:
        catalog = json.loads(_CATALOG.read_text(encoding="utf-8"))
    if (not isinstance(catalog, dict)
            or catalog.get("schemaVersion") != "pdufa-curated-phase3-announcements-v1"
            or not isinstance(catalog.get("cases"), dict)):
        raise ValueError("Invalid manually reviewed source catalog")

    requested = set(exact_keys)
    index = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Published discovery contains non-object row")
        key = row.get("id")
        if key not in requested:
            continue
        if key in index:
            # Quarantine duplicate exact identity; never choose the first.
            raise ValueError("Duplicate exact identity in published discovery")
        index[key] = row

    membership = {}
    groups = snapshot.get("members") or {}
    if not isinstance(groups, dict):
        raise ValueError("Published memberships must be an object")
    for stage_key, label in _ALLOWED_STAGES:
        group = groups.get(stage_key, {})
        group_rows = group.get("rows", []) if isinstance(group, dict) else []
        if not isinstance(group_rows, list):
            raise ValueError("Published membership rows must be a list")
        seen_group = set()
        for member in group_rows:
            if not isinstance(member, dict):
                raise ValueError("Invalid stage membership row")
            key = member.get("id")
            if key not in requested:
                continue
            if key in seen_group:
                raise ValueError("Duplicate stage membership for exact identity")
            seen_group.add(key)
            # Only membership already published as active and identity linked.
            # Never recalculate restrictions or change FS/FA assignments.
            source = index.get(key)
            if (source is not None
                    and member.get("membershipStatus") == "ACTIVE IN PUBLISHED STAGE LEDGER"
                    and member.get("candidateLinked") is True
                    and member.get("ticker") == source.get("ticker")):
                membership.setdefault(key, []).append(label)

    selected = []
    warnings = {}
    for key in exact_keys:
        row = index.get(key)
        if row is None:
            continue
        phase3 = {}
        pdufa = {}
        warning = None
        curated = catalog["cases"].get(key)
        if not source_healthy:
            warning = "PUBLISHED_SOURCE_HEALTH_NOT_COMPLETE"
        elif curated is None:
            warning = "NO_CURATED_PHASE3_PDUFA_SOURCE_PAIR"
        elif not isinstance(curated, dict):
            warning = "INVALID_CURATED_SOURCE_ATTESTATION"
        else:
            match = _reviewed_pair(curated, target=row.get("pdufaDate", ""), as_of=cutoff)
            if match is None:
                warning = "CURATED_ATTESTATION_NOT_CURRENT_OR_TARGET_MISMATCH"
            elif curated.get("nctId") and row.get("nctId") and curated["nctId"] != row["nctId"]:
                warning = "CLINICAL_TRIAL_IDENTITY_MISMATCH"
            else:
                phase3, pdufa = match
        warnings[key] = warning
        selected.append({
            "exact_key": key,
            "list_memberships": membership.get(key, []),
            "phase3_results": phase3,
            "pdufa_assignment": pdufa,
            "scientific_evidence": {},  # A start gate is not a completed SCIENCE dossier
        })
    batch = evaluate_candidate_batch(selected, as_of=as_of)
    preview = build_sheet_population_preview(batch)
    for result in batch["rows"]:
        result["discoveryFeed"] = "PUBLISHED_PIPELINE_INDEX"
        result["sourceWarning"] = warnings[result["exactKey"]]
    return {
        "mode": "READ_ONLY_PUBLISHED_DISCOVERY_RESEARCH_PREVIEW",
        "asOf": as_of, "sourceHealthState": health_state or "UNKNOWN",
        "sourceResearchVerified": source_healthy,
        "requested": len(exact_keys),
        "totalDiscovered": batch["totalDiscovered"],
        "missingExactKeys": [k for k in exact_keys if k not in index],
        "eligibleForResearch": batch["eligibleForResearch"],
        "blockedFromResearch": batch["blockedFromResearch"],
        "rows": batch["rows"],
        "sheetPreview": preview,
        "sheetPopulationStatus": "NOT_WRITTEN",
        "tradeAuthorized": False, "scannerScheduled": False,
        "researchSourcePolicy": "SERVER_CURATED_MANUAL_DISCLOSURES_ONLY",
    }

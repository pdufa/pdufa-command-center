"""Isolated, strictly read-only end-to-end archive pilot verification.

Invoked only for a known archival NCT on the review service. No HTTP
requests, writes, scheduler, scientific scoring, or trading actions.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .scientific_dossier import DOMAINS
from .scientific_dossier_archive import dossier_from_archive
from .scientific_pilot_keynote024 import PILOT_NCT_ID, keynote024_pilot_manifest
from .scientific_pilot_keynote024_results import keynote024_published_results

_ORIGINAL_PMIDS = {"27718847", "29129441", "33872070"}


def verify_archived_keynote024(
    nct_id: str,
    payload_gzip: bytes,
    expected_sha256: str,
    fetched_at: datetime,
) -> dict[str, Any]:
    """Validate one real stored record and source-attributed analysis bundle.

    Raises ValueError on mismatched identities, evidence, or unwanted scores.
    Returns only safe diagnostic counts, never trial payloads or credentials.
    """
    if nct_id != PILOT_NCT_ID:
        raise ValueError("Unexpected pilot trial identity")
    dossier = dossier_from_archive(
        "TRIAL|" + PILOT_NCT_ID,
        PILOT_NCT_ID,
        payload_gzip,
        expected_sha256,
        fetched_at,
    )
    manifest = keynote024_pilot_manifest()
    research = keynote024_published_results()
    if (manifest.get("nct_id") != PILOT_NCT_ID
        or research.get("nct_id") != PILOT_NCT_ID
        or dossier.get("nct_id") != PILOT_NCT_ID):
        raise ValueError("Pilot trial identity mismatch")
    if dossier.get("source_sha256") != expected_sha256:
        raise ValueError("Pilot source checksum mismatch")
    domain_keys = set(DOMAINS)
    if (len(DOMAINS) != 8 or set(dossier.get("domains", {})) != domain_keys
        or set(manifest.get("domains", {})) != domain_keys
        or set(research.get("domain_scores", {})) != domain_keys):
        raise ValueError("Eight-domain pilot coverage mismatch")
    if (dossier.get("overall_score") is not None
        or dossier.get("fda_approval_probability") is not None
        or manifest.get("overall_score") is not None
        or manifest.get("fda_approval_probability") is not None
        or research.get("overall_score") is not None
        or research.get("fda_approval_probability") is not None
        or any(domain.get("score") is not None for domain in dossier["domains"].values())
        or any(value is not None for value in research["domain_scores"].values())):
        raise ValueError("Pilot source material must remain scientifically unscored")
    snapshots = research.get("analysis_snapshots")
    if not isinstance(snapshots, list) or len(snapshots) != 3:
        raise ValueError("Pilot requires three distinct published analysis snapshots")
    actual_pmids = set()
    for snapshot in snapshots:
        if (not isinstance(snapshot, dict)
            or snapshot.get("nct_id") != PILOT_NCT_ID
            or snapshot.get("source_url") !=
                "https://pubmed.ncbi.nlm.nih.gov/" + str(snapshot.get("source_id")) + "/"):
            raise ValueError("Published source identity does not match archived pilot")
        actual_pmids.add(snapshot["source_id"])
    if actual_pmids != _ORIGINAL_PMIDS:
        raise ValueError("Expected original published sources not present")
    claims = dossier["domains"]["clinical_design"].get("claims", [])
    if any(claim.get("scientifically_verified") is not False for claim in claims):
        raise ValueError("Registry facts cannot be treated as fully verified findings")
    if dossier.get("assessment_status") != "incomplete":
        raise ValueError("Pilot assessment cannot be marked completed")
    return {
        "status": "PASS",
        "nct_id": PILOT_NCT_ID,
        "archived_source_verified": True,
        "scientific_domains": len(DOMAINS),
        "published_analyses": len(snapshots),
        "scientific_assessment_completed": False,
        "score_assigned": False,
        "read_only": True,
    }

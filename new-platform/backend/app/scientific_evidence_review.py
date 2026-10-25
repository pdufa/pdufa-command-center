"""Strict human-review gate for evidence promoted from research leads.

A PMID or FDA application search hit is not clinical evidence. Only a
reviewer-supplied claim with explicit source and NCT linkage can be added
as a reviewed finding. This module never assigns scores or probabilities.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
from typing import Any, Mapping
from urllib.parse import urlsplit
import re

from .scientific_dossier import DOMAINS

_NCT = re.compile(r"NCT[0-9]{8}\Z")
_PMID = re.compile(r"[1-9][0-9]{0,11}\Z")
_ALLOWED_KINDS = {"pubmed", "clinicaltrials", "fda"}
_ALLOWED_STANCES = {"supports", "contradicts", "inconclusive"}
_ALLOWED_CERTAINTY = {"low", "moderate", "high"}


def _source_url(kind: str, source_id: str) -> str:
    if kind == "pubmed" and _PMID.fullmatch(source_id):
        return f"https://pubmed.ncbi.nlm.nih.gov/{source_id}/"
    if kind == "clinicaltrials" and _NCT.fullmatch(source_id):
        return f"https://clinicaltrials.gov/study/{source_id}"
    if kind == "fda" and re.fullmatch(r"(?:NDA|BLA)[0-9]{6}", source_id):
        return f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm"
    raise ValueError("Unsupported source kind or identifier")


def attach_reviewed_finding(dossier: Mapping[str, Any], finding: Mapping[str, Any]) -> dict:
    """Attach a traceable finding; does not decide whether it is scientifically true.

    Review is explicit and auditable; clinical-trial association is supplied
    by the reviewer and never inferred from an FDA application or PubMed hit.
    """
    if not isinstance(dossier, Mapping) or not isinstance(finding, Mapping):
        raise ValueError("Dossier and finding must be objects")
    output = deepcopy(dict(dossier))
    domains = output.get("domains")
    nct_id = output.get("nct_id")
    if not isinstance(domains, dict) or not isinstance(nct_id, str) or not _NCT.fullmatch(nct_id):
        raise ValueError("Invalid dossier identity or domains")
    domain = finding.get("domain")
    if domain not in DOMAINS or domain not in domains:
        raise ValueError("Unsupported scientific domain")
    if finding.get("nct_id") != nct_id:
        raise ValueError("Reviewed finding NCT mismatch")
    kind, source_id = finding.get("source_kind"), finding.get("source_id")
    if kind not in _ALLOWED_KINDS or not isinstance(source_id, str):
        raise ValueError("Unsupported source")
    source_url = _source_url(kind, source_id)
    if kind == "clinicaltrials" and source_id != nct_id:
        raise ValueError("Registry finding NCT mismatch")
    claim = finding.get("claim")
    reviewer = finding.get("reviewer")
    rationale = finding.get("rationale")
    source_locator = finding.get("source_locator")
    if any(not isinstance(v, str) or not v.strip() or len(v) > cap
           for v, cap in ((claim, 2000), (reviewer, 120), (rationale, 2000), (source_locator, 500))):
        raise ValueError("Claim, reviewer, rationale, and source locator are required")
    stance, certainty = finding.get("stance"), finding.get("certainty")
    if stance not in _ALLOWED_STANCES or certainty not in _ALLOWED_CERTAINTY:
        raise ValueError("Explicit stance and evidence certainty required")
    try:
        published = date.fromisoformat(finding["source_date"])
        reviewed = datetime.fromisoformat(finding["reviewed_at"].replace("Z", "+00:00"))
    except (KeyError, ValueError, AttributeError, TypeError):
        raise ValueError("Valid source and review dates required") from None
    if reviewed.tzinfo is None or reviewed.utcoffset() is None:
        raise ValueError("Review timestamp must be timezone-aware")
    if published > reviewed.date():
        raise ValueError("Source date cannot follow review")
    if reviewed.astimezone(timezone.utc) > datetime.now(timezone.utc):
        raise ValueError("Review cannot be future-dated")
    item = {
        "nct_id": nct_id, "domain": domain, "claim": claim.strip(),
        "source_kind": kind, "source_id": source_id,
        "source_url": source_url, "source_locator": source_locator.strip(),
        "source_date": published.isoformat(), "reviewer": reviewer.strip(),
        "reviewed_at": reviewed.astimezone(timezone.utc).isoformat(),
        "rationale": rationale.strip(), "stance": stance, "certainty": certainty,
        "verification_status": "analyst_reviewed_claim",
        "independent_replication_confirmed": False,
    }
    target = domains[domain]
    if not isinstance(target, dict) or target.get("score") is not None:
        raise ValueError("Cannot modify a scored domain")
    target.setdefault("reviewed_findings", []).append(item)
    target["status"] = "reviewed_findings_present"
    if output.get("overall_score") is not None or output.get("fda_approval_probability") is not None:
        raise ValueError("Review cannot set scores or approval forecasts")
    output["assessment_status"] = "incomplete"
    return output

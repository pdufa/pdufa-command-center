"""Source-bound Levels 13–16 for exact trials and, where known, review cycles.

The engines report checked passages and unresolved comparisons. They do not
turn inventory into a scientific score, manufacture a prediction, or record
owner acceptance. Supplementary documents must come from a trusted collector
or immutable evidence store. This reader verifies the extracted text hash,
citation location, identity, and chronology, not remote content or authorship.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import re
from urllib.parse import urlsplit

from .hop_fda_application_crosswalk import canonical_application_id

VERSION = "extended-clinical-v1"
NAMES = {
    13: "Subgroups and unmet need",
    14: "FDA regulatory intelligence",
    15: "CMC and manufacturing",
    16: "Advisory committee and exceptions",
}
PHASES = {"EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4"}
FDA_HOSTS = {"www.fda.gov", "fda.gov", "www.accessdata.fda.gov", "accessdata.fda.gov"}
NCT = re.compile(r"NCT[0-9]{8}")
DIGEST = re.compile(r"[a-f0-9]{64}")
CYCLE = re.compile(r"(?:Original [1-9][0-9]*|S-[0-9]{1,3}|Review Cycle [1-9][0-9]*)", re.I)
APPLICATION_IN_TEXT = re.compile(r"\b(?:NDA|BLA)[ #:\-]*[0-9]{1,6}\b", re.I)
CYCLE_IN_TEXT = re.compile(r"\b(?:Original [1-9][0-9]*|S-[0-9]{1,3}|Review Cycle [1-9][0-9]*)\b", re.I)

# A match only identifies a passage for review. The retained value remains the
# exact quotation, with its original scope and uncertainty.
CRITERIA = {
    13: (
        ("subgroup_method", r"subgroup analyses?|subgroup analysis plan|exploratory subgroup|demographic subgroups",
         "Reconcile subgroup definitions and prespecification against the protocol and analysis plan."),
        ("subgroup_interaction", r"interaction(?: test| term| p[- ]?value)|heterogeneity",
         "Assess treatment-by-subgroup interaction and uncertainty. Within-subgroup significance does not establish heterogeneity."),
        ("standard_of_care", r"standard of care|usual care|current treatment|comparator",
         "Identify the current comparator for this indication, subtype and line of therapy."),
        ("unmet_need", r"unmet (?:medical |clinical )?need|limited (?:treatment|therapeutic) options",
         "Use indication-specific treatment limitations and patient-important outcomes to evaluate unmet need."),
    ),
    14: (
        ("review_pathway", r"priority review|accelerated approval|fast track|breakthrough therapy|standard review",
         "Identify the application-specific pathway and its date without treating a designation as an action."),
        ("agency_feedback", r"agency feedback|FDA feedback|FDA requested|FDA recommends|meeting minutes|information request",
         "Preserve exact agency feedback, including preliminary or conditional language."),
        ("review_timing", r"PDUFA|goal date|review timeline|major amendment",
         "Record only source-stated review timing and preserve the distinction between goal and action dates."),
    ),
    15: (
        ("manufacturing_control", r"manufacturing process|process validation|control strategy|release specification",
         "Review process controls and validation for the exact product and application cycle."),
        ("quality_consistency", r"comparability|lot consistency|stability|potency|batch consistency",
         "Keep reported comparability, stability and specification limitations visible."),
        ("inspection", r"pre[- ]approval inspection|FDA inspection|facility inspection|form 483|inspectional observations",
         "Capture inspection scope and dates. Unavailable or nonpublic information is an unresolved gap."),
    ),
    16: (
        ("committee_status", r"advisory committee|committee meeting|adcom",
         "Distinguish announced, held, canceled and unknown committee status."),
        ("committee_question", r"voting question|committee voted|vote tally|public hearing",
         "Preserve the exact voting question, tally and scope. Advice and FDA action are separate."),
        ("review_exception", r"waiv(?:er|ed)|exception|special protocol assessment|major amendment|resubmission",
         "Identify a documented exception or cycle change and its conditions. Silence does not establish a waiver."),
    ),
}


def _mapping(value):
    return value if isinstance(value, Mapping) else {}


def _publication(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Source needs a complete publication date")
    return date.fromisoformat(value)


def _capture(value):
    if not isinstance(value, str) or "T" not in value:
        raise ValueError("Source needs a timezone-aware capture instant")
    captured = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if captured.tzinfo is None:
        raise ValueError("Source needs a timezone-aware capture instant")
    return captured.astimezone(timezone.utc)


def _chronology(published_at, captured_at, cutoff):
    published, captured = _publication(published_at), _capture(captured_at)
    if not published <= captured.date() <= cutoff:
        raise ValueError("Source publication or capture crosses chronology or cutoff")
    return published


def _registry(source, nct, cutoff):
    if not isinstance(nct, str) or not NCT.fullmatch(nct) or source.get("nct_id") != nct:
        raise ValueError("Registry receipt does not match the requested NCT")
    if source.get("source_url") != f"https://clinicaltrials.gov/api/v2/studies/{nct}":
        raise ValueError("Registry receipt does not identify the original registry endpoint")
    if not DIGEST.fullmatch(str(source.get("raw_sha256", ""))):
        raise ValueError("Registry raw source digest missing")
    published = _chronology(source.get("published_at"), source.get("captured_at"), cutoff)
    document = json.loads(source["document_json"])
    packed = json.dumps(document, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if sha256(packed.encode()).hexdigest() != source.get("input_sha256"):
        raise ValueError("Frozen registry input digest mismatch")
    protocol = _mapping(_mapping(document).get("protocolSection"))
    status = _mapping(protocol.get("statusModule"))
    if (_mapping(protocol.get("identificationModule")).get("nctId") != nct
            or _mapping(status.get("lastUpdatePostDateStruct")).get("date") != published.isoformat()):
        raise ValueError("Registry contents do not match the identity and revision receipt")
    return protocol, status, document


def _contains(text, phrase):
    return bool(re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text, re.I))


def _receipt(level, item, nct, conditions, cutoff, protocol, documents, snapshot_captured_at):
    url = item.get("source_url")
    parsed = urlsplit(url if isinstance(url, str) else "")
    exact_protocol = level == 13 and parsed.hostname == "cdn.clinicaltrials.gov" and re.fullmatch(
        rf"/large-docs/{nct[-2:]}/{nct}/[A-Za-z0-9_.-]+\.pdf", parsed.path
    )
    if (parsed.scheme != "https" or parsed.netloc != parsed.hostname
            or (parsed.hostname not in FDA_HOSTS and not exact_protocol)
            or not parsed.path or parsed.query or parsed.fragment):
        raise ValueError("Supplementary receipt needs an original FDA source or exact-trial registry PDF")
    published = _chronology(item.get("published_at"), item.get("captured_at"), cutoff)
    if _capture(item.get("captured_at")) > _capture(snapshot_captured_at):
        raise ValueError("Supplementary evidence was captured after the frozen registry snapshot")
    if not DIGEST.fullmatch(str(item.get("raw_sha256", ""))):
        raise ValueError("Supplementary original document SHA-256 receipt missing")
    # When the collector supplies original bytes, verify their digest rather
    # than accepting an uncorroborated checksum claim. The collector must still
    # establish the URL and publication provenance independently.
    raw_bytes = item.get("raw_bytes")
    if raw_bytes is not None:
        if not isinstance(raw_bytes, bytes) or sha256(raw_bytes).hexdigest() != item["raw_sha256"]:
            raise ValueError("Supplementary original document bytes digest mismatch")
    body = item.get("text")
    if not isinstance(body, str) or sha256(body.encode()).hexdigest() != item.get("text_sha256"):
        raise ValueError("Supplementary extracted text digest mismatch")
    section, indication, excerpt = (item.get(key) for key in ("identity_excerpt", "indication", "excerpt"))
    if not all(isinstance(value, str) and value.strip() for value in (section, indication, excerpt)):
        raise ValueError("Identity excerpt, exact indication and quoted finding are required")
    if section not in body or excerpt not in body:
        raise ValueError("Identity and quotation are missing from the original extraction")
    if indication.casefold() not in {condition.casefold() for condition in conditions} or not _contains(section, indication):
        raise ValueError("Source passage does not establish the exact registered indication")
    if exact_protocol:
        filename = parsed.path.rsplit("/", 1)[1]
        leads = [_mapping(lead) for lead in documents if _mapping(lead).get("filename") == filename]
        study_id = _mapping(_mapping(protocol.get("identificationModule")).get("orgStudyIdInfo")).get("id")
        bound = _contains(section, nct) or isinstance(study_id, str) and len(study_id) >= 4 and _contains(section, study_id)
        if (not bound or len(leads) != 1 or not (leads[0].get("hasProtocol") is True or leads[0].get("hasSap") is True)
                or leads[0].get("date") != published.isoformat()):
            raise ValueError("Original registry PDF must reconcile to the exact trial and registered document date")
        uploaded = leads[0].get("uploadDate")
        if not isinstance(uploaded, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(?::[0-9]{2})?", uploaded):
            raise ValueError("Original registry PDF upload date unresolved")
        if not published <= _publication(uploaded[:10]) <= _capture(item.get("captured_at")).date():
            raise ValueError("Original registry PDF date and upload chronology conflict")
    elif set(re.findall(r"\bNCT[0-9]{8}\b", section)) != {nct} or excerpt not in section:
        raise ValueError("Quoted finding and exact trial must share an original source section")
    if not isinstance(item.get("locator"), str) or not item["locator"].strip():
        raise ValueError("Supplementary passage locator missing")
    identity = {"indication": indication}
    if level > 13:
        application, cycle = item.get("application"), item.get("cycle")
        canonical = canonical_application_id(application)
        if (canonical is None or not re.fullmatch(r"(?:NDA|BLA)[ #:\-]*[0-9]{1,6}", application, re.I)
                or {canonical_application_id(value) for value in APPLICATION_IN_TEXT.findall(section)} != {canonical}
                or not isinstance(cycle, str) or not CYCLE.fullmatch(cycle)
                or {match.casefold() for match in CYCLE_IN_TEXT.findall(section)} != {cycle.casefold()}):
            raise ValueError("Original passage does not identify the exact FDA application and review cycle")
        identity.update(application=canonical, cycle=cycle.casefold())
    return {**identity, **{key: item[key] for key in
             ("source_url", "published_at", "captured_at", "text_sha256", "locator", "excerpt")}}


def _protocol_passages(document, conditions, source_capture):
    originals = document.get("originalDocuments")
    if not isinstance(originals, list):
        return
    for original in originals:
        original = _mapping(original)
        if original.get("verification") != "ORIGINAL_LINKED_PDF_RETRIEVED":
            continue
        text = original.get("extractedText")
        pages = original.get("pages")
        raw_digest = original.get("sha256")
        captured = original.get("capturedAt")
        if (not isinstance(text, str) or not isinstance(pages, list)
                or not isinstance(raw_digest, str) or not DIGEST.fullmatch(raw_digest)):
            continue
        if _capture(captured) > source_capture:
            raise ValueError("Original protocol capture exceeds its containing snapshot")
        header = text[:6000]
        matched = [condition for condition in conditions if _contains(header, condition)]
        if len(matched) != 1:
            continue
        text_digest = sha256(text.encode()).hexdigest()
        for _, pattern, _ in CRITERIA[13]:
            for page in pages:
                page_text = _mapping(page).get("text")
                page_number = _mapping(page).get("page")
                if not isinstance(page_text, str) or type(page_number) is not int or page_number < 1:
                    continue
                match = re.search(pattern, page_text, re.I)
                if match is None:
                    continue
                passage = page_text[max(0, match.start()-180):match.end()+220].strip()
                if passage not in text:
                    continue
                yield {"source_url": original.get("url"), "published_at": original.get("registeredDocumentDate"),
                       "captured_at": captured, "text": text, "text_sha256": text_digest,
                       "raw_sha256": raw_digest, "identity_excerpt": header, "indication": matched[0],
                       "excerpt": passage, "locator": f"PDF page {page_number}"}
                break


def _check(identifier, explanation, citations, *, expected=True, comparable=True):
    if not comparable and citations:
        state = "UNRESOLVED_APPLICATION_OR_CYCLE"
    elif len({item["indication"].casefold() for item in citations}) > 1:
        state = "UNRESOLVED_INDICATION_SCOPE"
    elif len({" ".join(item["excerpt"].casefold().split()) for item in citations}) > 1:
        state = "UNRECONCILED_FINDINGS"
    elif citations:
        state = "SOURCE_PASSAGE_CHECKED"
    else:
        state = "MISSING" if expected else "NOT_YET_EXPECTED"
    return {"id": identifier, "state": state, "explanation": explanation,
            "citations": citations, "locator": "Original source section"}


def assess_clinical_level(level, source, *, nct, cutoff=None, evidence=()):
    """Assess a frozen registry row with optional trusted extraction receipts.

    Each supplementary receipt binds an exact quotation inside an identity
    section, original source URL, location, exact indication, UTC capture and
    publication, and SHA-256 of the retained text. Levels 14–16 require the
    source-stated application and cycle in the same section. Historical runs
    withhold all supplements until an outcome-isolated collection path exists.
    """
    if type(level) is not int or level not in CRITERIA:
        raise ValueError("Clinical extensions support Levels 13–16")
    today = datetime.now(timezone.utc).date()
    if cutoff is not None and (type(cutoff) is not date or cutoff >= today):
        raise ValueError("Historical assessment requires a past cutoff date")
    protocol, status, document = _registry(source, nct, cutoff or today)
    conditions = _mapping(protocol.get("conditionsModule")).get("conditions")
    conditions = [x for x in conditions if isinstance(x, str) and x.strip()] if isinstance(conditions, list) else []
    phases = _mapping(protocol.get("designModule")).get("phases")
    phase_verified = isinstance(phases, list) and bool(phases) and all(
        isinstance(phase, str) and phase in PHASES for phase in phases
    )
    early_phase = phase_verified and all(x in {"EARLY_PHASE1", "PHASE1", "PHASE2"} for x in phases)
    checked = []
    rejected = []
    if cutoff is None and phase_verified:
        candidates = list(evidence)
        if level == 13:
            try:
                candidates.extend(_protocol_passages(document, conditions, _capture(source["captured_at"])))
            except (ValueError, TypeError, UnicodeError) as exc:
                rejected.append({"state": "REJECTED_EVIDENCE", "reason": str(exc)})
        documents = document.get("documents")
        for item in candidates:
            item = _mapping(item)
            try:
                checked_item = _receipt(level, item, nct, conditions, today, protocol,
                                        documents if isinstance(documents, list) else [], source["captured_at"])
                checked_item["raw_sha256"] = item["raw_sha256"]
                checked.append(checked_item)
            except (ValueError, TypeError, UnicodeError) as exc:
                rejected.append({"state": "REJECTED_EVIDENCE", "reason": str(exc)})
    # Report each distinct source version and exact location, without allowing
    # repeated imports or inconsistent caller ordering to change the findings.
    distinct = {}
    for item in sorted(checked, key=lambda x: (_capture(x["captured_at"]), x["published_at"])):
        key = tuple(item.get(field, "") for field in (
            "source_url", "text_sha256", "locator", "excerpt", "indication", "application", "cycle"
        ))
        distinct.setdefault(key, item)
    checked = [distinct[key] for key in sorted(distinct)]
    identities = {(x.get("application"), x.get("cycle")) for x in checked}
    one_cycle = len(identities) <= 1
    checks = [
        _check(identifier, explanation, [item for item in checked if re.search(pattern, item["excerpt"], re.I)],
               expected=not early_phase or level == 13, comparable=one_cycle)
        for identifier, pattern, explanation in CRITERIA[level]
    ]
    if not phase_verified:
        checks = [{"id": "phase_first", "state": "MISSING", "explanation": "Resolve the exact trial's phase before advanced assessment.",
                   "citations": [], "locator": "protocolSection.designModule.phases"}]
    population = {
        key: value for key, value in _mapping(protocol.get("eligibilityModule")).items()
        if key in {"minimumAge", "maximumAge", "sex", "healthyVolunteers", "eligibilityCriteria"}
        and ((isinstance(value, str) and value.strip()) or type(value) is bool)
    } if cutoff is None else {}
    if level == 13 and phase_verified and cutoff is None:
        locator = "protocolSection.eligibilityModule"
        citations = [{**{key: source[key] for key in ("source_url", "published_at", "captured_at", "raw_sha256")},
                      "locator": locator}] if population else []
        checks.append({"id": "registered_population", "state": "SOURCE_REPORTED" if population else "MISSING",
                       "explanation": "Registered eligibility describes the target population. Subgroup enrollment and treatment effects require their own evidence.",
                       "locator": locator, "value": population, "citations": citations})
    pending = [item["explanation"] for item in checks if item["state"] not in {"SOURCE_PASSAGE_CHECKED", "SOURCE_REPORTED"}]
    if cutoff is not None:
        pending.append("Supplementary regulatory passages are withheld in historical mode until outcome-isolated capture is verified.")
    if not one_cycle:
        pending.append("Multiple FDA applications or cycles are present. An exact review-cycle target is unresolved.")
    if any(item["state"] == "UNRECONCILED_FINDINGS" for item in checks):
        evidence_status = "UNRECONCILED_FINDINGS"
    elif pending and (checked or any(item["citations"] for item in checks)):
        evidence_status = "PARTIAL_EVIDENCE"
    elif pending:
        evidence_status = "INSUFFICIENT_EVIDENCE"
    else:
        evidence_status = "SOURCE_PASSAGES_CHECKED"
    return {
        "level": level, "name": NAMES[level], "engineVersion": f"{VERSION}/level-{level}", "nct": nct,
        "context": {"phases": phases if phase_verified else [], "conditions": conditions,
                    "registryStatus": status.get("overallStatus"), "earlyPhase": early_phase,
                    "registeredPopulation": population},
        "checks": checks, "rejectedEvidence": rejected, "evidenceStatus": evidence_status,
        "score": {"value": None, "status": "NOT_SCORED", "kind": "NOT_VALIDATED"},
        "fdaPrediction": {"outcome": "ABSTAIN", "probability": None, "confidence": "NOT_VALIDATED",
                          "calibration": "NO_VALIDATED_FDA_MODEL"},
        "ownerReviewStatus": "OWNER_NOT_REVIEWED", "historicalAccuracyEligible": False,
        "risks": pending, "explanation": "Verified citation identity and chronology support source observations. Scientific adjudication remains unresolved.",
        "evidence": {key: source[key] for key in ("source_url", "published_at", "captured_at", "raw_sha256", "input_sha256")},
    }

"""Levels 17–18 conservative sponsor-disclosure and scientific challenge screens.

Source-backed discrepancies and competing explanations are observations for
owner review, not proof of misconduct, scientific causality or FDA approval.
"""
from __future__ import annotations
from datetime import date
import re

VERSION = "scientific-disclosure-challenge-v1"


def _date(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _accepted(level, evidence, key):
    accepted = level.get("acceptedEvidence") if isinstance(level, dict) else None
    receipt = accepted.get(key) if isinstance(accepted, dict) else None
    record = evidence.get(f"{level['level']}.{key}") if isinstance(level, dict) and isinstance(evidence, dict) else None
    if (not isinstance(receipt, dict) or receipt.get("sourceVerified") is not True
            or receipt.get("retrievalProvenance") != "RECORDED"
            or not isinstance(record, dict) or not isinstance(record.get("measurements"), dict)):
        return None
    return record["measurements"]


def _claim(value, trial_id, cutoff):
    if not isinstance(value, dict) or value.get("nctId") != trial_id:
        return None
    for field in ("claimKey", "claimText"):
        if not isinstance(value.get(field), str) or not 0 < len(value[field].strip()) <= 2000:
            return None
    when, asof = _date(value.get("disclosureDate")), _date(cutoff)
    if not when or not asof or when > asof:
        return None
    return {"nctId": trial_id, "claimKey": value["claimKey"].strip(),
            "claimText": value["claimText"].strip(), "disclosureDate": when.isoformat()}


def assess_disclosure(level, evidence, *, trial_id, cutoff):
    base = {"methodVersion": VERSION, "status": "NOT_ASSESSED",
            "score": None, "fdaPrediction": "ABSTAIN", "scientificValidation": "NOT_VERIFIED",
            "misrepresentationEstablished": False, "materialityEstablished": False,
            "limitations": [
                "A discrepancy may reflect a protocol change, new data, wording or changed context; intent is not inferred.",
                "Reviewed evidence records are not automatic authentication of the original issuer disclosure.",
                "A later statement is not automatically more accurate than an earlier statement.",
            ]}
    early = _accepted(level, evidence, "datedDisclosureVersions")
    later = _accepted(level, evidence, "materialChanges")
    if early is None or later is None:
        return {**base, "reason": "Two separately reviewed, dated source statements required."}
    a, b = _claim(early, trial_id, cutoff), _claim(later, trial_id, cutoff)
    if a is None or b is None or a["claimKey"].casefold() != b["claimKey"].casefold() or a["disclosureDate"] >= b["disclosureDate"]:
        return {**base, "status": "REJECTED_CLAIM_CONTEXT",
                "reason": "Exact trial, matching claim key and strictly chronological dated statement pair required."}
    different = a["claimText"] != b["claimText"]
    return {**base,
            "status": "CLAIM_CHANGE_REQUIRES_OWNER_REVIEW" if different else "SAME_TEXT_NOT_PROOF_OF_CONSISTENCY",
            "claimKey": a["claimKey"],
            "earlier": {"text": a["claimText"], "date": a["disclosureDate"],
                        "source": level["acceptedEvidence"]["datedDisclosureVersions"]["source"]},
            "later": {"text": b["claimText"], "date": b["disclosureDate"],
                      "source": level["acceptedEvidence"]["materialChanges"]["source"]},
            "textChanged": different,
            "ownerReconciliation": "NOT_COMPLETED"}


def _argument(value, trial_id):
    if not isinstance(value, dict) or value.get("nctId") != trial_id:
        return None
    result = {}
    for key in ("hypothesis", "evidenceRationale", "evaluationScope", "possibleDiscriminator"):
        v = value.get(key)
        if not isinstance(v, str) or not 0 < len(v.strip()) <= 2000:
            return None
        result[key] = v.strip()
    return result


def assess_challenge(level, evidence, *, trial_id):
    base = {"methodVersion": VERSION, "status": "NOT_ASSESSED",
            "score": None, "fdaPrediction": "ABSTAIN", "scientificValidation": "NOT_VERIFIED",
            "causalityEstablished": False, "scientificChallengeResolved": False,
            "ownerAcceptance": "NOT_RECORDED",
            "limitations": [
                "Two reviewed explanations can both be wrong; source citations do not validate either.",
                "An identified alternative mechanism is not proof of confounding or lack of efficacy.",
                "No fabricated owner signoff, outcome-labeled hindsight adjustment, or weighted certainty score.",
            ]}
    first = _accepted(level, evidence, "strongestCounterargument")
    second = _accepted(level, evidence, "alternativeCausality")
    if first is None or second is None:
        return {**base, "reason": "Two independently documented owner/source-reviewed counterargument records required."}
    a, b = _argument(first, trial_id), _argument(second, trial_id)
    if not a or not b or a["hypothesis"].casefold() == b["hypothesis"].casefold():
        return {**base, "status": "REJECTED_ARGUMENTS",
                "reason": "Two distinct, exact-trial, evidence-rationalized alternative hypotheses required."}
    return {**base, "status": "COMPETING_EXPLANATIONS_DOCUMENTED_NOT_RESOLVED",
            "counterargument": {**a, "source": level["acceptedEvidence"]["strongestCounterargument"]["source"]},
            "alternativeExplanation": {**b, "source": level["acceptedEvidence"]["alternativeCausality"]["source"]},
            "nextAction": "Owner must adjudicate the evidence, assumptions and discriminating tests."}

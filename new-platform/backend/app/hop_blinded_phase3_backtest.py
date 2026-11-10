"""Issue #980: FDA historical Phase-3-readout replay and anti-leakage gates.

No old RAAS scores, selected archive actions, or self-declared completeness
are independently validated historical labels. This module handles research
replay inputs only. Actual training and calibrated prediction stay blocked.
"""
from __future__ import annotations
from collections import Counter
from datetime import date
import hashlib,json,re
from urllib.parse import urlsplit

NCT=re.compile(r"NCT[0-9]{8}\Z")
APP=re.compile(r"(?:NDA|BLA)[0-9]{6}\Z")
SHA=re.compile(r"[0-9a-f]{64}\Z")
SOURCE_ROLES=frozenset({
    "PIVOTAL_PHASE3_RESULT","PUBLISHED_SAFETY_ANALYSIS",
    "REGULATORY_PRIOR_CYCLE","SEC_ISSUER_DISCLOSURE",
    "DATED_TRIAL_REGISTRY_VERSION","PUBLIC_CMC_RESEARCH_LEAD"
})
SOURCE_FIELDS=frozenset({
    "id","role","source_url","first_public_date","retrieved_date",
    "as_published_version_verified","sha256","summary"
})
_ALLOWED_CALLS=frozenset({"APPROVAL_LEAN","CRL_LEAN","ABSTAIN"})
_OUTCOMES=frozenset({"APPROVAL","COMPLETE_RESPONSE","WITHDRAWN","PENDING","FORMAL_EXTENSION","OTHER_UNRESOLVED"})

def _date(raw):
    if not isinstance(raw,str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}",raw):
        raise ValueError("INVALID_ISO_SOURCE_DATE")
    try:return date.fromisoformat(raw)
    except ValueError as error:raise ValueError("INVALID_CALENDAR_DATE") from error

def _url(raw):
    if not isinstance(raw,str) or any(c.isspace() for c in raw):return False
    try:
        u=urlsplit(raw)
        return u.scheme=="https" and bool(u.hostname) and bool(u.path.strip("/")) and u.username is None and u.password is None and not u.fragment
    except ValueError:return False

def freeze_predecision_evidence(raw:dict)->dict:
    """Prepare an exact application/NCT evidence-only packet with no FDA outcome.

    Source/version clocks must be established from original as-published
    records, not inferred from the present website or a later FDA decision.
    """
    if not isinstance(raw,dict) or set(raw)!={
        "applicationId","reviewCycle","programFamily","nctIds",
        "phase3ReadoutPublicOn","predictionCutoff","evidenceSources"}:
        raise ValueError("FORECAST_INPUT_MUST_EXCLUDE_FDA_OUTCOME")
    app=raw["applicationId"]
    ncts=raw["nctIds"]
    if (not isinstance(app,str) or not APP.fullmatch(app) or
        type(raw["reviewCycle"]) is not int or raw["reviewCycle"]<1 or
        not isinstance(raw["programFamily"],str) or not raw["programFamily"].strip() or
        not isinstance(ncts,list) or not ncts or len(set(ncts))!=len(ncts) or
        any(not isinstance(n,str) or not NCT.fullmatch(n) for n in ncts)):
        raise ValueError("INCOMPLETE_APPLICATION_PROGRAM_IDENTITY")
    phase3=_date(raw["phase3ReadoutPublicOn"])
    cutoff=_date(raw["predictionCutoff"])
    if not phase3<cutoff:
        raise ValueError("PREDICTION_MUST_FOLLOW_PUBLIC_PHASE3_READOUT")
    sources=raw["evidenceSources"]
    if not isinstance(sources,list) or not sources or len(sources)>150:
        raise ValueError("ORIGINAL_PREDECISION_DOCUMENTS_REQUIRED")
    items=[]
    seen=set()
    for row in sources:
        if not isinstance(row,dict) or set(row)!=SOURCE_FIELDS:
            raise ValueError("UNKNOWN_SOURCE_FIELD_COULD_LEAK_FDA_OUTCOME")
        if (not isinstance(row["id"],str) or not row["id"] or row["id"] in seen or
            row["role"] not in SOURCE_ROLES or not _url(row["source_url"]) or
            row["as_published_version_verified"] is not True or
            not isinstance(row["sha256"],str) or not SHA.fullmatch(row["sha256"]) or
            not isinstance(row["summary"],str) or not row["summary"].strip()):
            raise ValueError("UNTRUSTED_HISTORICAL_SOURCE_OR_VERSION")
        public=_date(row["first_public_date"])
        retrieved=_date(row["retrieved_date"])
        if public>cutoff or retrieved<public:
            raise ValueError("SOURCE_NOT_AVAILABLE_AS_OF_FROZEN_CUTOFF")
        if (row["role"] in ("PIVOTAL_PHASE3_RESULT","PUBLISHED_SAFETY_ANALYSIS")
                and public<phase3):
            raise ValueError("PIVOTAL_SOURCE_PRECEDES_REPORTED_READOUT")
        seen.add(row["id"])
        items.append(dict(row))
    if not any(x["role"]=="PIVOTAL_PHASE3_RESULT" for x in items):
        raise ValueError("MISSING_PUBLIC_PIVOTAL_PHASE3_EVIDENCE")
    packet={
        "schema":"MAIN_HOP_BLINDED_PHASE3_REPLAY_V1",
        "applicationId":app,"reviewCycle":raw["reviewCycle"],
        "programFamily":raw["programFamily"],
        "nctIds":sorted(ncts),
        "phase3ReadoutPublicOn":phase3.isoformat(),
        "predictionCutoff":cutoff.isoformat(),
        "sourceVersions":sorted(items,key=lambda x:x["id"]),
        "fdaOutcomeAvailableToResearchForecaster":False,
        "modelTrainingAuthorized":False
    }
    digest=hashlib.sha256(json.dumps(packet,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return {"frozenEvidence":packet,"frozenSourceSha256":digest,
            "officialForecast":"ABSTAIN","numericalFDAProbability":None,
            "independentlyVerifiedHistoricCase":False}

def evaluate_replay_protocol(*,frozen_packets:list,provisional_predictions:list,
                             outcome_vault:list,as_of:date)->dict:
    """Evaluate isolated retrospective research calls; never claim real accuracy.

    The release gate remains shut even if a caller self-declares all outcomes
    verified. Synthetic tests can inspect numerator/denominator math only.
    """
    if type(as_of) is not date:raise ValueError("AS_OF_DATE_REQUIRED")
    if not all(isinstance(x,list) for x in (frozen_packets,provisional_predictions,outcome_vault)):
        raise ValueError("INCOMPLETE_SEGREGATED_REPLAY_INPUTS")
    frozen={}
    families={"development":set(),"temporal_holdout":set()}
    for x in frozen_packets:
        if not isinstance(x,dict) or set(x)!={"frozenEvidence","frozenSourceSha256",
             "officialForecast","numericalFDAProbability","independentlyVerifiedHistoricCase"}:
            raise ValueError("FORGED_FROZEN_EVIDENCE_PACKET")
        packet=x["frozenEvidence"]
        if (not isinstance(packet,dict) or packet.get("schema")!="MAIN_HOP_BLINDED_PHASE3_REPLAY_V1" or
           packet.get("fdaOutcomeAvailableToResearchForecaster") is not False or
           packet.get("modelTrainingAuthorized") is not False or
           x["officialForecast"]!="ABSTAIN" or
           x["numericalFDAProbability"] is not None or
           x["independentlyVerifiedHistoricCase"] is not False):
            raise ValueError("HISTORICAL_OUTCOME_LEAK_OR_MODEL_RELEASE")
        if hashlib.sha256(json.dumps(packet,sort_keys=True,separators=(",",":")).encode()).hexdigest()!=x["frozenSourceSha256"]:
            raise ValueError("FROZEN_EVIDENCE_HASH_MISMATCH")
        ident=(packet["applicationId"],packet["reviewCycle"])
        if ident in frozen:raise ValueError("DUPLICATE_APPLICATION_REVIEW_CYCLE")
        frozen[ident]=packet
    predictions={}
    for row in provisional_predictions:
        if not isinstance(row,dict) or set(row)!={"applicationId","reviewCycle",
            "frozenSourceSha256","researchLean","researchVersion","isolationProof",
            "split","createdAtUtc"}:
            raise ValueError("MALFORMED_RESEARCH_PREDICTION")
        key=(row["applicationId"],row["reviewCycle"])
        packet=frozen.get(key)
        if (packet is None or key in predictions or
            row["researchLean"] not in _ALLOWED_CALLS or
            row["frozenSourceSha256"]!=hashlib.sha256(
                json.dumps(packet,sort_keys=True,separators=(",",":")).encode()).hexdigest() or
            row["isolationProof"]!="OUTCOME_VAULT_NOT_READ_BY_FORECAST_RUN" or
            row["split"] not in families or
            not isinstance(row["researchVersion"],str) or not row["researchVersion"] or
            not isinstance(row["createdAtUtc"],str) or "T" not in row["createdAtUtc"]):
            raise ValueError("PREDICTION_NOT_SEALED_FROM_OUTCOME_VAULT")
        # Date the prediction run honestly. A retrospective replay is never
        # falsely backdated as a prospective recorded 2024/25 forecast.
        families[row["split"]].add(packet["programFamily"])
        predictions[key]=row
    if families["development"] & families["temporal_holdout"]:
        raise ValueError("PROGRAM_FAMILY_CROSS_SPLIT_LEAKAGE")
    outcomes={}
    for row in outcome_vault:
        if not isinstance(row,dict) or set(row)!={"applicationId","reviewCycle",
          "finalAction","actionDate","firstPublicActionOn","originalFdaActionSource",
          "qualifiedOutcomeReviewerSignoff","exhaustiveFilingCohortVerified"}:
            raise ValueError("MALFORMED_SEPARATE_OUTCOME_VAULT")
        key=(row["applicationId"],row["reviewCycle"])
        if key in outcomes:raise ValueError("DUPLICATED_FDA_OUTCOME")
        if row["finalAction"] not in _OUTCOMES or not _url(row["originalFdaActionSource"]):
            raise ValueError("UNVERIFIED_FDA_ACTION_SOURCE")
        decision=_date(row["actionDate"])
        publication=_date(row["firstPublicActionOn"])
        if publication<decision or publication>as_of:
            raise ValueError("FDA_OUTCOME_CLOCK_INVALID")
        packet=frozen.get(key)
        if packet and decision<=_date(packet["predictionCutoff"]):
            raise ValueError("OUTCOME_ALREADY_OCCURRED_BEFORE_PREDICTION_CUTOFF")
        outcomes[key]=row
    known=Counter()
    correct=0
    predicted=0
    for key,row in predictions.items():
        outcome=outcomes.get(key)
        if not outcome:known["UNRESOLVED_OUTCOME"]+=1;continue
        action=outcome["finalAction"]
        known[action]+=1
        if action in ("APPROVAL","COMPLETE_RESPONSE") and row["researchLean"]!="ABSTAIN":
            predicted+=1
            if row["researchLean"]==("APPROVAL_LEAN" if action=="APPROVAL" else "CRL_LEAN"):
                correct+=1
    paired=sum(1 for key in predictions if key in outcomes)
    # A real cohort must be independently verified externally; self-assertions
    # in synthetic JSON can never by themselves establish validation.
    return {
        "status":"HISTORICAL_RESEARCH_REPLAY_DIAGNOSTIC_NOT_VALIDATED",
        "frozenApplicationReviewCycles":len(frozen),
        "sealedResearchPredictions":len(predictions),
        "observedOutcomeRecords":len(outcomes),
        "pairedWithObservedOutcomes":paired,
        "sourceActionCounts":dict(known),
        "researchCallsOnBinaryOutcomes":predicted,
        "researchCallMatches":correct,
        "researchCallCoverageOfPaired":(predicted/paired if paired else None),
        "researchMatchFractionAmongCalled":(correct/predicted if predicted else None),
        "developmentProgramFamilies":len(families["development"]),
        "untouchedTemporalHoldoutProgramFamilies":len(families["temporal_holdout"]),
        "independentlyVerifiedHistoricalCases":0,
        "independentRealBacktests":0,
        "measuredProspectiveAccuracy":None,
        "brierScore":None,
        "calibration":None,
        "fdaProbability":None,
        "trainingAuthorized":False,
        "caution":"Research diagnostics on supplied episodes are NOT independent performance estimates or evidence of a complete FDA cohort"
    }

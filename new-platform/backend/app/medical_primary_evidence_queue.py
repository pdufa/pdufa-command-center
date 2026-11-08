"""Prioritized EXACT-FOCUS scientific review queue built from saved primary records.

A method can only be graded in the separate append-only reviewer ledger.
Registry phases, posted results and source pointers are NOT scientific passes.
"""
from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException

from . import medical_continuous as core
from . import medical_assessment_ledger as ledger
from . import medical_registry_reconciliation as registry
from . import medical_scientific_triage as triage

BUCKETS = (
    "PHASE_RECONCILIATION_REQUIRED",
    "POSTED_PRIMARY_RESULTS_NEED_ADJUDICATION",
    "NO_POSTED_PRIMARY_RESULTS_FIND_ORIGINAL_READOUT",
)
ACTIONS = {
    BUCKETS[0]:(
        "Confirm exact trial phase, protocol version, completed phase and application cycle. "
        "Do not score a current-phase test until the phase conflict is resolved."
    ),
    BUCKETS[1]:(
        "Retrieve full posted primary results and the prespecified protocol/SAP. "
        "Check sample size, effect size, confidence intervals, multiplicity, "
        "missing data, serious harms, amendments and contradictory evidence; "
        "review against original clinical and FDA sources before assigning a grade."
    ),
    BUCKETS[2]:(
        "Seek exact-NCT company clinical readout, full-text peer-reviewed reports, "
        "supplements and original conference results. Verify the primary endpoints "
        "and dates against the official registry; do not infer benefit from study completion."
    ),
}


def readiness(engine):
    """One cheap no-write readiness check; defer expensive per-NCT detail to GET."""
    registry_cover=registry.coverage(engine)
    triage_cover=triage.coverage(engine)
    core_cover=ledger.coverage(engine)
    expected=len(core.roster())
    ready=(expected==29 and registry_cover["savedNcts"]==expected
           and registry_cover["status"]=="COMPLETE_REGISTRY_FACT_CAPTURE"
           and triage_cover["savedNcts"]==expected
           and triage_cover["status"]=="COMPLETE_SOURCE_TRIAGE"
           and core_cover["sourceComplete"]==expected)
    return {
        "status":"READY_FOR_EVIDENCE_REVIEW" if ready else "INCOMPLETE",
        "canonicalTrials":expected,
        "registryRecordsSaved":registry_cover["savedNcts"],
        "triageRecordsSaved":triage_cover["savedNcts"],
        "sourceResearchSaved":core_cover["sourceComplete"],
        "independentScientificReviewEvents":core_cover["reviewEvents"],
        "humanVerifiedPhases":core_cover["phaseVerifiedNcts"],
        "clinicalSignoff":False,
        "fdaPrediction":"ABSTAIN",
        "certainty":"NOT_VALIDATED",
    }


def build_queue(engine):
    state=readiness(engine)
    if state["status"]!="READY_FOR_EVIDENCE_REVIEW":
        raise RuntimeError("Exact 29-trial source and registry reconciliation must finish")
    ids=sorted(core.roster())
    rows=[]
    for nct in ids:
        registry_row=registry.latest(engine,nct)
        triage_row=triage.latest(engine,nct)
        if (registry_row["nct"]!=nct or triage_row["nct"]!=nct
                or registry_row["sourceRunId"]!=triage_row["sourceRunId"]
                or registry_row["scientificSignoff"] is not False
                or triage_row["scientificSignoff"] is not False):
            raise RuntimeError("Mismatched exact trial and saved original source identity")
        phase=registry_row["currentRegistryPhases"]
        phase_status=registry_row["phaseAgreement"]
        posted=registry_row["registryPostedPrimaryOutcomeMeasures"]
        registered=registry_row["registeredPrimaryOutcomeCount"]
        if not isinstance(posted,int) or posted<0 or not isinstance(registered,int) or registered<0:
            raise RuntimeError("Registry primary evidence counts must be nonnegative integers")
        if phase_status!="MATCHED_SINGLE_PHASE":
            category=BUCKETS[0]
        elif posted:
            category=BUCKETS[1]
        else:
            category=BUCKETS[2]
        rows.append({
            "nct":nct,
            "category":category,
            "reviewPriority":BUCKETS.index(category)+1,
            "phase":phase,
            "phaseAgreement":phase_status,
            "phaseReviewerStatus":"NOT_INDEPENDENTLY_ADJUDICATED",
            "officialRegistryUrl":registry_row["registryUrl"],
            "registryLastUpdate":registry_row["latestRecordUpdatePosted"],
            "primaryOutcomeDefinitions":registered,
            "primaryOutcomeResultsPosted":posted,
            "postedResultsSourceStatus":registry_row["resultsInterpretation"],
            "sourceTriageSnapshotId":triage_row["snapshotId"],
            "registrySnapshotId":registry_row["snapshotId"],
            "sourceRunId":triage_row["sourceRunId"],
            "methodPositions":triage_row["methodPositions"],
            "sourceClassCounts":triage_row["sourceClassCounts"],
            "scientificGradeStatus":"NOT_REVIEWED" if triage_row["methodsWithIndependentGrade"]==0
                                     else "REVIEW_EVENTS_EXIST_VALIDATE_IN_LEDGER",
            "independentlyGradedPositionsReported":triage_row["methodsWithIndependentGrade"],
            "nextEvidenceAction":ACTIONS[category],
            "clinicalFinding":None,
            "fdaPrediction":"ABSTAIN",
            "certainty":"NOT_VALIDATED",
        })
    rows.sort(key=lambda x:(x["reviewPriority"],
                            -x["primaryOutcomeResultsPosted"],
                            x["nct"]))
    for rank,row in enumerate(rows,1):
        row["reviewQueuePosition"]=rank
    buckets=Counter(x["category"] for x in rows)
    if sum(buckets.values())!=29:
        raise RuntimeError("The review queue cannot silently drop a trial")
    return {
        "schema":"EXACT_NCT_EVIDENCE_REVIEW_QUEUE_V1",
        "status":"READY_FOR_INDEPENDENT_EVIDENCE_REVIEW",
        "canonicalTrials":29,
        "phaseReconciliationRequired":buckets[BUCKETS[0]],
        "postedPrimaryResultsNeedReview":buckets[BUCKETS[1]],
        "noPostedPrimaryResults":buckets[BUCKETS[2]],
        "registeredPrimaryOutcomeDefinitions":sum(x["primaryOutcomeDefinitions"] for x in rows),
        "postedPrimaryOutcomeMeasures":sum(x["primaryOutcomeResultsPosted"] for x in rows),
        "reviewItems":rows,
        "reviewerScientificGradesWritten":state["independentScientificReviewEvents"],
        "clinicalSignoff":False,
        "fdaPredictions":{"APPROVAL":"ABSTAIN","CRL":"ABSTAIN","REVIEW_DELAY":"ABSTAIN"},
        "certainty":"NOT_VALIDATED",
        "note":"Queue priority measures review work, NOT success probability, "
               "observed medical risk, evidence strength or an FDA decision.",
    }


def install_routes(app,engine_provider,require_key,require_storage):
    """Never expose a score-write endpoint to a machine-readiness queue."""
    router=APIRouter(prefix="/api/internal/medical-primary-evidence-review",
                     dependencies=[Depends(require_key),Depends(require_storage)])

    @router.get("/readiness")
    def get_readiness():
        return readiness(engine_provider())

    @router.get("/queue")
    def get_queue():
        try:
            return build_queue(engine_provider())
        except RuntimeError:
            raise HTTPException(503,"Verified source data is incomplete or inconsistent")

    app.include_router(router)

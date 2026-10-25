"""KEYNOTE-024 protocol/SAP evidence crosswalk and two independent review gates.

The registry-linked protocol is amendment 024-11 dated 2017-12-20,
later than the 2016 interim PFS cutoff and labeled applicable only to
Japan. Never treat this as original pre-interim prespecification.
No scientific scores, FDA probabilities, FS/FA edits or trade actions.
"""
from __future__ import annotations

import re
from copy import deepcopy
from datetime import date
from math import isclose
from typing import Any, Mapping, Sequence

PILOT_NCT_ID = "NCT02142738"
REGISTRY_URL = "https://clinicaltrials.gov/study/NCT02142738"
PROTOCOL_URL = "https://cdn.clinicaltrials.gov/large-docs/38/NCT02142738/Prot_SAP_000.pdf"
ORIGINAL_URL = "https://pubmed.ncbi.nlm.nih.gov/27718847/"
ORIGINAL_MANUSCRIPT_URL = "https://www.nejm.org/doi/full/10.1056/nejmoa1606774"
REGULATORY_URL = "https://pmc.ncbi.nlm.nih.gov/articles/PMC5679831/"
FOLLOWUP_URL = "https://pubmed.ncbi.nlm.nih.gov/33872070/"
QOL_URL = "https://pubmed.ncbi.nlm.nih.gov/29129441/"
SOURCE_SUPPORTED = "SOURCE_SUPPORTED"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
BLOCKED = "BLOCKED"
_STATUSES = frozenset((SOURCE_SUPPORTED, REVIEW_REQUIRED, BLOCKED))
_HASH_RE = re.compile(r"[0-9a-f]{64}\Z")
_ALLOWED_SOURCES = frozenset((REGISTRY_URL, PROTOCOL_URL, ORIGINAL_URL,
                              REGULATORY_URL, FOLLOWUP_URL, QOL_URL,
                              ORIGINAL_MANUSCRIPT_URL))


def grade_review_inputs(checks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Pass/fail input sufficiency and independent reluctance, never clinical merit."""
    if not isinstance(checks, (list, tuple)) or not checks or len(checks) > 40:
        raise ValueError("A bounded checklist is required")
    if len({c.get("id") for c in checks if isinstance(c, Mapping)}) != len(checks):
        raise ValueError("Duplicate checklist identity")
    supported, pending, blocked, critical_blocked, critical_pending = [], [], [], [], []
    for check in checks:
        if not isinstance(check, Mapping):
            raise ValueError("Checklist item must be an object")
        if (not isinstance(check.get("id"), str)
            or not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", check["id"])
            or check.get("status") not in _STATUSES
            or not isinstance(check.get("critical"), bool)
            or not isinstance(check.get("title"), str) or not check["title"].strip()
            or not isinstance(check.get("finding"), str) or not check["finding"].strip()
            or not isinstance(check.get("next_action"), str) or not check["next_action"].strip()):
            raise ValueError("Incomplete or invalid evidence checklist item")
        refs = check.get("sources")
        if not isinstance(refs, list) or not refs or len(refs) > 5 or any(
            not isinstance(ref, Mapping)
            or ref.get("url") not in _ALLOWED_SOURCES
            or not isinstance(ref.get("locator"), str) or not ref["locator"].strip()
            for ref in refs
        ):
            raise ValueError("Every check needs a vetted source URL and locator")
        if check["status"] == SOURCE_SUPPORTED:
            supported.append(check["id"])
        elif check["status"] == REVIEW_REQUIRED:
            pending.append(check["id"])
            if check["critical"]:
                critical_pending.append(check["id"])
        else:
            blocked.append(check["id"])
            if check["critical"]:
                critical_blocked.append(check["id"])
    unresolved = pending + blocked
    if not unresolved:
        reluctance = "LOW"
    elif critical_blocked:
        reluctance = "HIGH"
    elif critical_pending or blocked:
        reluctance = "ELEVATED"
    else:
        reluctance = "MODERATE"
    return {
        "inputReadiness": {
            "grade": "FAIL" if unresolved else "PASS",
            "status": "NOT_READY_FOR_FULL_ANALYSIS" if unresolved else "READY_FOR_FULL_ANALYSIS_INPUT_REVIEW",
            "criteriaTotal": len(checks),
            "sourceSupported": len(supported),
            "unresolved": len(unresolved),
            "unresolvedIds": unresolved,
            "meaning": "Input completeness only; never a clinical efficacy or FDA approval grade.",
        },
        "reluctance": {
            "grade": reluctance,
            "status": "CONCLUSIONS_WITHHELD" if unresolved else "REVIEW_EVIDENCE_BEFORE_CONCLUSIONS",
            "criticalBlockedIds": critical_blocked,
            "criticalReviewIds": critical_pending,
            "meaning": "Caution about drawing scientific conclusions, not probability of failure.",
        },
        "fullTwentyLevelAnalysisCompleted": False,
        "scientificScore": None,
        "fdaApprovalProbability": None,
        "readOnly": True,
    }


def _same(value: Any, expected: float) -> bool:
    return type(value) in (int, float) and isclose(value, expected, rel_tol=0, abs_tol=1e-9)


def keynote024_protocol_readiness(
    dossier: Mapping[str, Any], research: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate stored pilot identities/results, then publish a sourced gap register."""
    if not isinstance(dossier, Mapping) or not isinstance(research, Mapping):
        raise ValueError("Scientific evidence objects required")
    if dossier.get("nct_id") != PILOT_NCT_ID or research.get("nct_id") != PILOT_NCT_ID:
        raise ValueError("Pilot NCT mismatch")
    sha = dossier.get("source_sha256")
    if not isinstance(sha, str) or not _HASH_RE.fullmatch(sha):
        raise ValueError("Checksum-verified archive required")
    if dossier.get("read_only") is not True:
        raise ValueError("Only read-only archive inputs are supported")
    if (dossier.get("overall_score") is not None
        or dossier.get("fda_approval_probability") is not None
        or research.get("overall_score") is not None
        or research.get("fda_approval_probability") is not None):
        raise ValueError("Cannot derive readiness from a scored dossier")
    snapshots = research.get("analysis_snapshots")
    if not isinstance(snapshots, list) or len(snapshots) != 3:
        raise ValueError("Exactly three historical analyses required")
    expected = {
        "keynote024_initial_2016": "27718847",
        "keynote024_pros_2017": "29129441",
        "keynote024_five_year_2021": "33872070",
    }
    by_id: dict[str, Mapping[str, Any]] = {}
    for snap in snapshots:
        if (not isinstance(snap, Mapping)
            or snap.get("analysis_id") not in expected
            or snap.get("nct_id") != PILOT_NCT_ID
            or snap.get("source_id") != expected[snap["analysis_id"]]
            or snap["analysis_id"] in by_id):
            raise ValueError("Original study publication identity mismatch")
        by_id[snap["analysis_id"]] = snap
    if set(by_id) != set(expected):
        raise ValueError("Required trial publications missing")
    initial = by_id["keynote024_initial_2016"]
    followup = by_id["keynote024_five_year_2021"]
    if (initial.get("data_cutoff_date") != "2016-05-09"
        or date.fromisoformat("2017-12-20") <= date.fromisoformat(initial["data_cutoff_date"])):
        raise ValueError("Later protocol date or trial cutoff incompatible")
    if (research.get("randomized_population") != 305
        or initial.get("arm_counts_randomized") != {"pembrolizumab": 154, "chemotherapy": 151}):
        raise ValueError("Randomized population identity mismatch")
    effects = initial.get("effects")
    if not isinstance(effects, Mapping):
        raise ValueError("Original efficacy missing")
    pfs, os_interim = effects.get("progression_free_survival"), effects.get("overall_survival")
    if (not isinstance(pfs, Mapping) or not isinstance(os_interim, Mapping)
        or pfs.get("analysis_role") != "prespecified_primary"
        or not _same(pfs.get("hazard_ratio"), 0.50)
        or pfs.get("hazard_ratio_95pct_ci") != [0.37, 0.68]
        or pfs.get("p_value") != "<0.001"
        or not _same(os_interim.get("hazard_ratio"), 0.60)
        or os_interim.get("hazard_ratio_95pct_ci") != [0.41, 0.89]):
        raise ValueError("Published primary/interim endpoint values mismatch")
    safety = initial.get("safety")
    if (not isinstance(safety, Mapping)
        or safety.get("treatment_related_adverse_events_grade_3_to_5_percent") !=
          {"pembrolizumab": 26.6, "chemotherapy": 53.3}):
        raise ValueError("Published treatment-related safety class mismatch")
    if not _same(followup.get("effective_crossover_percent_from_chemotherapy"), 66.0):
        raise ValueError("Long-term crossover disclosure incomplete")

    def check(key: str, title: str, status: str, critical: bool, finding: str,
              next_action: str, *refs: tuple[str, str]) -> dict:
        return {
            "id": key, "title": title, "status": status, "critical": critical,
            "finding": finding, "next_action": next_action,
            "sources": [{"url": url, "locator": locator} for url, locator in refs],
        }

    checks = [
        check("archive_identity", "Exact archived trial identity", SOURCE_SUPPORTED, True,
              "ClinicalTrials.gov NCT was checksum-verified before this appraisal.",
              "Retain source SHA-256 and acquisition timestamp for audit.",
              (REGISTRY_URL, "Protocol/Identification; exact NCT02142738")),
        check("primary_pfs", "Original randomized PFS", SOURCE_SUPPORTED, True,
              "Original PFS HR 0.50 (95% CI 0.37-0.68), p<0.001, is also reported in FDA-authored review.",
              "Reconcile PFS censoring to original pre-interim statistical analysis plan.",
              (ORIGINAL_URL, "2016 original randomized trial PFS result"),
              (REGULATORY_URL, "Table 1, KEYNOTE-024 primary PFS")),
        check("interim_os", "Early overall survival corroboration", SOURCE_SUPPORTED, False,
              "Original interim OS HR 0.60 (95% CI 0.41-0.89) is separately cited by FDA.",
              "Do not mix 2016 interim effect with later 2021 long-term OS.",
              (ORIGINAL_URL, "2016 original trial, secondary OS"),
              (REGULATORY_URL, "Table 1, interim OS")),
        check("reported_trae", "Published grade 3-5 treatment-related AEs", SOURCE_SUPPORTED, False,
              "Original grade 3-5 treatment-related AEs: 26.6% vs 53.3%, not all-cause events.",
              "Reconcile treated-population denominators and complete AE categories.",
              (ORIGINAL_URL, "2016 abstract, treatment-related adverse events")),
        check("pre_cutoff_protocol", "Contemporaneous original protocol", BLOCKED, True,
              "Registry-linked protocol is amendment 024-11 dated 2017-12-20, after 2016 interim cutoff; marked Japan-only.",
              "Retrieve original 2016 NEJM protocol PDF, inspect dated amendments and signed pre-cutoff SAP, then validate alpha-spending and censoring.",
              (PROTOCOL_URL, "Cover page 1, amendment 024-11, 2017-12-20, Japan-only"),
              (ORIGINAL_MANUSCRIPT_URL, "Supplementary Material: nejmoa1606774_protocol.pdf is listed, but full content, effective dates and signature remain unverified"),
              (ORIGINAL_URL, "Original electronic publication 2016-10-08")),
        check("multiplicity_alpha", "Prospective multiplicity and alpha spending", REVIEW_REQUIRED, True,
              "2017 SAP pp.113 and 122 specify one-sided 2.5% error control, ORR/PFS/OS ordering and OS alpha spending. FDA cites p=0.005 vs alpha 0.0118.",
              "Compare with pre-2016 plan and actual event counts and interim spending boundary.",
              (PROTOCOL_URL, "Sections 8.1.3 p.113 and 8.2.6 p.122"),
              (REGULATORY_URL, "Table 1 footnote b, interim alpha 0.0118")),
        check("safety_population", "Full AE denominators and attribution", REVIEW_REQUIRED, True,
              "2017 SAP p.113 specifies all-subjects-as-treated safety analysis and crossover handling; TRAEs are not all harms.",
              "Reconcile SAE, immune-mediated, fatal, exposure-adjusted and all-grade groups against posted tables.",
              (PROTOCOL_URL, "Section 8.1.2 p.113; ASaT and crossover"),
              (REGISTRY_URL, "Adverse events posted results")),
        check("longterm_crossover", "Crossover in long-term survival", REVIEW_REQUIRED, True,
              "2021 follow-up reports 66% effective crossover; long-term OS does not estimate an uncrossed counterfactual.",
              "Review adjusted OS, sensitivity and post-progression treatments.",
              (FOLLOWUP_URL, "2021 5-year follow-up results")),
        check("patient_flow_missingness", "Participant flow and missingness", REVIEW_REQUIRED, True,
              "SAP specifies ITT efficacy and missing responder assumptions, but full missing-data checks not completed.",
              "Compare randomized, treated, evaluated, and censored denominators by arm.",
              (PROTOCOL_URL, "Section 8.1.1 p.112, ITT and missing response"),
              (REGISTRY_URL, "Results, participant flow and baseline tables")),
        check("patient_reported_outcomes", "Exploratory quality-of-life", REVIEW_REQUIRED, False,
              "2017 PRO results use a nominal p-value; open-label questionnaires and missingness require separate review.",
              "Inspect original PRO plan and questionnaire completion rates.",
              (QOL_URL, "2017 patient-reported outcomes"),
              (PROTOCOL_URL, "Section 8.1.1 p.112, separate PRO plan")),
        check("historical_fda_basis", "Historical FDA efficacy review", SOURCE_SUPPORTED, False,
              "FDA-authored review describes past first-line NSCLC approval; this is not a prospective PDUFA forecast.",
              "Keep historical label chronology separate from future approvals.",
              (REGULATORY_URL, "FDA approval summary, Table 1")),
        check("full_regulatory_cmc", "Full FDA and CMC evidence", BLOCKED, True,
              "Registry, protocol and published results do not constitute a complete CMC, inspection and FDA review package.",
              "Acquire original FDA reviews, relevant labeling and manufacturing documentation.",
              (REGULATORY_URL, "FDA efficacy approval summary scope"),
              (REGISTRY_URL, "FDA-regulated drug indicator, not CMC package")),
    ]
    return deepcopy({
        "modelVersion": "scientific-readiness-two-grade-v1",
        "nctId": PILOT_NCT_ID,
        "protocol": {
            "url": PROTOCOL_URL, "documentDate": "2017-12-20",
            "amendment": "024-11", "regionalScope": "Japan-only amendment (cover note)",
            "afterInterimDataCutoff": True, "notProofOf2016Prespecification": True,
            "interimDataCutoff": "2016-05-09",
            "documentClassification": "later_protocol_and_sap",
        },
        **grade_review_inputs(checks),
        "original2016ProtocolSource": {
            "sourceUrl": ORIGINAL_MANUSCRIPT_URL,
            "listedFilename": "nejmoa1606774_protocol.pdf",
            "listingVerified": True,
            "pdfContentReviewed": False,
            "effectiveAmendmentsVerified": False,
            "originalSignedSapVerified": False,
            "preInterimAlphaSpendingVerified": False,
            "status": "source_listed_not_adjudicated",
            "blocking": True,
            "sourceLocator": "NEJM original article, Supplementary Material: Protocol",
            "caution": "Publication-linked supplement is not proof of the protocol/SAP version in force at the May 9, 2016 cutoff.",
        },
        "checks": checks,
        "preliminarySourceReviewAllowed": True,
        "independentReanalysisPerformed": False,
        "approvalForecastProduced": False,
        "fsFaModified": False,
        "tradingActionsEnabled": False,
        "disclaimer": "Source sufficiency and uncertainty only; no clinical success or FDA probability grade.",
    })

"""Source-attributed, preliminary evidence comparison for historical KEYNOTE-024.

All eight review questions remain open. This cross-source reading aid compares
facts reported by original publications and official PDFs; it does not parse
their content automatically, certify authenticity, establish prospective SAP
locking, independently adjudicate efficacy, or assign FDA-approval probability.

The static locators below were checked against official FDA correspondence,
the ClinicalTrials.gov posted protocol and the cited journal abstracts.
"""
from __future__ import annotations

from copy import deepcopy

from .scientific_reconciliation_worklist import (
    PROTOCOL_SAP, FDA_2016_APPROVAL, ORIGINAL_TRIAL, FOLLOWUP_5YEAR,
    QUALITY_OF_LIFE, REGISTRY, reconciliation_worklist,
)
from .scientific_source_documents import read_document_manifest
from .scientific_evidence_ledger import read_ledger

PILOT_NCT = "NCT02142738"
SCHEMA = "historical-pilot-preliminary-evidence-comparison-v1"

SOURCES = {
    "protocol_2017": {
        "label": "ClinicalTrials.gov protocol, Amendment 024-11 (Japan-only)",
        "url": PROTOCOL_SAP,
        "documentDate": "2017-12-20",
        "kind": "archived_original_pdf",
        "locator": "Cover and page 1; sections 8.1.3 and 8.2",
    },
    "fda_2016": {
        "label": "FDA supplement approval letter, BLA 125514/S-8 and S-12",
        "url": FDA_2016_APPROVAL,
        "documentDate": "2016-10-24",
        "kind": "archived_original_pdf",
        "locator": "FDA letter page 1; electronic signature page 6",
    },
    "reck_2016": {
        "label": "Reck et al., NEJM 2016 initial KEYNOTE-024 results",
        "url": ORIGINAL_TRIAL,
        "documentDate": "2016-10-08",
        "kind": "published_paper_abstract",
        "locator": "PubMed 27718847, Methods and Results",
    },
    "brahmer_2017": {
        "label": "Brahmer et al., Lancet Oncology 2017, quality of life",
        "url": QUALITY_OF_LIFE,
        "documentDate": "2017-11-09",
        "kind": "published_paper_abstract",
        "locator": "PubMed 29129441, Findings",
    },
    "reck_2021": {
        "label": "Reck et al., JCO 2021, five-year outcomes",
        "url": FOLLOWUP_5YEAR,
        "documentDate": "2021-04-19",
        "kind": "published_paper_abstract",
        "locator": "PubMed 33872070, Results; data cutoff June 1, 2020",
    },
    "registry": {
        "label": "ClinicalTrials.gov NCT02142738",
        "url": REGISTRY,
        "documentDate": None,
        "kind": "public_registry_landing_page",
        "locator": "NCT02142738: source version may change after archive retrieval",
    },
    "fda_peer_review": {
        "label": "FDA staff-authored pembrolizumab approval summary (2017)",
        "url": "https://pubmed.ncbi.nlm.nih.gov/28835513/",
        "documentDate": "2017",
        "kind": "regulator_authored_publication",
        "locator": "PubMed 28835513 and Table 1 (S-12 clinical/statistical reviews)",
    },
}

# Interpretations intentionally narrower than the underlying reports:
# the existence of a source and its reported facts are not independent review.
OBSERVATIONS = {
    "protocol_amendment_chronology": {
        "sourceIds": ["protocol_2017", "reck_2016"],
        "preliminaryObservation": (
            "The captured 20-Dec-2017 protocol is Amendment 024-11 and explicitly "
            "applies only to Japan. Its 2017 statistical section refers back to "
            "Amendment 08 and a May 9, 2016 cutoff. It is a later version, not "
            "proof of the protocol/SAP prospectively locked before unblinding."
        ),
        "analysisBoundary": "2016-05-09",
        "stillMissing": (
            "Obtain a dated, effective pre-unblinding protocol and standalone SAP "
            "or documented contemporaneous FDA statistical-review audit trail."
        ),
        "risk": "critical",
    },
    "baseline_population_indication": {
        "sourceIds": ["reck_2016", "fda_2016", "registry"],
        "preliminaryObservation": (
            "The original report randomized 305 patients (154 pembrolizumab; "
            "151 chemotherapy) with PD-L1 TPS at least 50% and no sensitizing "
            "EGFR/ALK alterations. FDA S-12 identifies the first-line "
            "PD-L1-high indication; S-8 concerns the previously treated setting."
        ),
        "reportedCounts": {"randomized": 305, "pembrolizumab": 154, "chemotherapy": 151},
        "stillMissing": (
            "Audit exact eligibility and analysis-set exclusions from the locked "
            "2016 version and FDA clinical review, including subgroup representation."
        ),
        "risk": "high",
    },
    "pfs_initial_vs_followup": {
        "sourceIds": ["reck_2016", "reck_2021", "fda_peer_review"],
        "preliminaryObservation": (
            "Initial May 2016 analysis: PFS 10.3 versus 6.0 months, "
            "HR 0.50 (95% CI 0.37–0.68); interim OS HR 0.60 "
            "(95% CI 0.41–0.89). Separate five-year report "
            "(June 2020 cutoff): OS 26.3 versus 13.4 months, "
            "HR 0.62 (95% CI 0.48–0.81). Do not join these "
            "different outcomes/cutoffs into one original analysis."
        ),
        "initialPfs": {
            "cutoff": "2016-05-09", "medianMonths": [10.3, 6.0],
            "hazardRatio": 0.50, "ci95": [0.37, 0.68], "reportedP": "<0.001",
        },
        "initialInterimOs": {
            "cutoff": "2016-05-09", "hazardRatio": 0.60,
            "ci95": [0.41, 0.89], "reportedP": "0.005",
        },
        "longTermOs": {
            "cutoff": "2020-06-01", "medianMonths": [26.3, 13.4],
            "hazardRatio": 0.62, "ci95": [0.48, 0.81],
        },
        "stillMissing": (
            "Cross-check complete efficacy tables, interim alpha allocations, "
            "censoring rules, prespecified populations and analysis version."
        ),
        "risk": "critical",
    },
    "crossover_adjustment": {
        "sourceIds": ["reck_2016", "reck_2021"],
        "preliminaryObservation": (
            "Long-term publication reports 99 chemotherapy-assigned patients "
            "receiving subsequent anti-PD-1/PD-L1 therapy, an effective "
            "crossover rate of 66.0%. This includes subsequent treatment "
            "and should not automatically be interpreted as 99 on-study "
            "protocol crossovers or as a causal crossover-adjusted OS estimate."
        ),
        "effectiveCrossover": {
            "patientsWithSubsequentAntiPd1Pdl1": 99,
            "chemotherapyRandomized": 151, "reportedPercent": 66.0,
        },
        "stillMissing": (
            "Verify on-study crossover versus later external treatment, "
            "and independently appraise prespecified versus post-hoc switching "
            "adjustments before making a causal interpretation."
        ),
        "risk": "high",
    },
    "safety_endpoint_taxonomy": {
        "sourceIds": ["reck_2016", "registry", "fda_peer_review"],
        "preliminaryObservation": (
            "The 2016 article reports treatment-related grade 3–5 events "
            "in 26.6% versus 53.3%; those are not interchangeable with "
            "immune-mediated or all-cause adverse events or serious AE counts."
        ),
        "reportedGrade3To5TraePercent": {
            "pembrolizumab": 26.6, "chemotherapy": 53.3,
        },
        "stillMissing": (
            "Reconcile dated registry tables, trial safety populations, "
            "attribution, exposure time, event grading and immune-mediated "
            "event denominators without pooling mismatched safety categories."
        ),
        "risk": "critical",
    },
    "exploratory_qol_multiplicity": {
        "sourceIds": ["brahmer_2017", "protocol_2017"],
        "preliminaryObservation": (
            "Prespecified exploratory QoL at week 15: mean changes "
            "+6.9 versus -0.9 points; reported difference 7.8 points "
            "(95% CI 2.9–12.8) with nominal two-sided p=0.0020. "
            "The PRO publication reports 299 patients with any PRO response; "
            "PRO analysis denominators differ from the 305 randomized."
        ),
        "reportedWeek15Difference": {
            "value": 7.8, "ci95": [2.9, 12.8], "nominalP": "0.0020",
            "pembrolizumabChange": 6.9, "chemotherapyChange": -0.9,
        },
        "stillMissing": (
            "Check the prospectively defined PRO analysis plan, missing-data "
            "handling, any multiplicity control and open-label response bias."
        ),
        "risk": "medium",
    },
    "2015_vs_2016_fda_actions": {
        "sourceIds": ["fda_2016", "fda_peer_review"],
        "preliminaryObservation": (
            "FDA letter electronically signed Oct 24, 2016 identifies S-8 "
            "(revision to previously treated TPS at least 1% indication) "
            "and S-12 (first-line metastatic NSCLC, TPS at least 50%, "
            "without EGFR/ALK genomic aberrations). Earlier treated-setting "
            "approval was Oct 2, 2015. This is a historical regulatory outcome, "
            "not a prospective FDA approval-probability prediction."
        ),
        "historicalAction": {
            "signedDate": "2016-10-24", "firstLineSupplement": "BLA 125514/S-12",
            "previouslyTreatedSupplement": "BLA 125514/S-8",
            "earlierTreatedApprovalDate": "2015-10-02",
        },
        "stillMissing": (
            "Compare original label, supplement file history and FDA review "
            "memoranda; do not transfer this outcome to other indications."
        ),
        "risk": "critical",
    },
    "independent_corroboration": {
        "sourceIds": ["reck_2016", "reck_2021", "fda_peer_review"],
        "preliminaryObservation": (
            "The NEJM original trial, its 2021 follow-up, and the FDA staff "
            "summary describe the same underlying KEYNOTE-024 cohort. "
            "Their agreement does not equal an independent replication "
            "in newly enrolled participants."
        ),
        "stillMissing": (
            "Locate and assess separately randomized cohorts with comparable "
            "biomarker eligibility, line of therapy, endpoint definitions and "
            "treatment comparators; document conflicting results."
        ),
        "risk": "high",
    },
}


def preliminary_pilot_evidence_comparison(nct_id: str) -> dict:
    """Return evidence leads without changing adjudication or database state."""
    if nct_id != PILOT_NCT:
        raise LookupError("Preliminary source comparison is currently available only for the pilot")
    # Fail closed if any archived PDF, its source metadata, or evidence ledger
    # has invalid integrity. No unreviewed document is silently omitted.
    manifest = read_document_manifest(nct_id)
    ledger = read_ledger(nct_id)
    worklist = reconciliation_worklist(nct_id)
    checks = []
    for question in worklist["checks"]:
        question_id = question["id"]
        observed = OBSERVATIONS[question_id]
        found = deepcopy(observed)
        found["questionId"] = question_id
        found["title"] = question["title"]
        found["reviewStatus"] = "preliminary_source_comparison_not_independently_adjudicated"
        found["independentlyResolved"] = False
        found["criteriaSatisfied"] = 0
        found["evidenceGateApproved"] = False
        checks.append(found)
    assert len(checks) == 8 and all(x["independentlyResolved"] is False for x in checks)

    docs = []
    for item in manifest["documents"]:
        docs.append({
            "documentId": item["documentId"],
            "gateId": item["gateId"],
            "sourceUrl": item["sourceUrl"],
            "sha256": item["sha256"],
            "byteLength": item["byteLength"],
            "byteIntegrityChecked": item["byteIntegrityChecked"],
            "documentContentScientificallyVerified": False,
        })

    result = {
        "schemaVersion": SCHEMA,
        "nctId": nct_id,
        "scope": "historical_pilot_only",
        "sources": deepcopy(SOURCES),
        "checks": checks,
        "checkCount": len(checks),
        "unresolvedCount": worklist["unresolvedChecks"],
        "independentlyResolvedCount": 0,
        "archivedPdfCount": manifest["sourceDocumentCount"],
        "archivedPdfManifests": docs,
        "verifiedIndependentGates": ledger["verifiedGateCount"],
        "sourceComparisonPerformed": True,
        "documentByteIntegrityChecked": True,
        "scientificallyVerified": False,
        "independentReplicationEstablished": False,
        "mayAssignScientificScore": False,
        "fdaApprovalProbability": None,
        "historicalRegulatoryOutcomeKnown": True,
        "tradingEnabled": False,
        "cautions": [
            "Source-level observation is not independent statistical or clinical adjudication.",
            "The 2017 Japan-only amendment cannot certify the pre-2016 locked SAP.",
            "The two stored PDFs are byte-checksummed but their full contents were not independently reanalyzed.",
            "Published estimates were not reconstructed from individual patient data.",
            "The actual 2016 FDA action is historical; no future approval probability is estimated.",
        ],
    }
    if (result["unresolvedCount"] != 8 or
            result["verifiedIndependentGates"] != 0 or
            any(doc["documentContentScientificallyVerified"] for doc in docs)):
        # Scientific gates can only change via independently adjudicated process.
        raise ValueError("Preliminary pilot source-comparison review policy violated")
    return result

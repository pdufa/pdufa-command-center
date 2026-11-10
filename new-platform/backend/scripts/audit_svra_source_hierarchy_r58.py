#!/usr/bin/env python3
"""MAIN R58: source-reported Savara multiplicity arithmetic, NOT an FDA forecast.

Only compares publicly reported p-values to the currently attached SAP's
Hochberg/gate rules. No patient-level analysis, inference of prospective
prespecification, clinical grade, independent signoff or model training.
"""
from __future__ import annotations

import json
from decimal import Decimal

NCT = "NCT04544293"
APPLICATION = "svra-molgramostim"
SAP_URL = "https://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/SAP_001.pdf"
SPONSOR_URL = (
    "https://investors.savarapharma.com/news/news-details/2024/"
    "Savara-Announces-Molgramostim-Nebulizer-Solution-Molgramostim-Achieved-"
    "Statistical-Significance-for-Primary-Endpoint-and-Multiple-Secondary-"
    "Endpoints-in-IMPALA-2-a-Pivotal-Phase-3-Clinical-Trial-in-Autoimmune-"
    "Pulmonary-Alveolar--06-26-2024/default.aspx"
)
GATES = {"DLCO_WEEK24": "0.0007", "DLCO_WEEK48": "0.0008"}
NON_JP_KR_WEEK24 = {
    "SGRQ_TOTAL": "0.0072",
    "SGRQ_ACTIVITY": "0.0149",
    "EXERCISE_CAPACITY": "0.0845",
}
NON_JP_KR_WEEK48 = {
    "SGRQ_TOTAL": "0.1046",
    "SGRQ_ACTIVITY": "0.1216",
    "EXERCISE_CAPACITY": "0.0234",
}


def hochberg_passed(p_values: dict[str, str], alpha: str) -> list[str]:
    """Hochberg step-up for a complete, named family of pre-reported p-values."""
    if not isinstance(p_values, dict) or not p_values:
        raise ValueError("COMPLETE_P_VALUE_FAMILY_REQUIRED")
    cutoff = Decimal(alpha)
    if not cutoff.is_finite() or not Decimal(0) < cutoff < Decimal(1):
        raise ValueError("INVALID_ALPHA")
    values: list[tuple[str, Decimal]] = []
    for name, raw in p_values.items():
        if not isinstance(name, str) or not name or not isinstance(raw, str):
            raise ValueError("UNTRUSTED_P_VALUE")
        p = Decimal(raw)
        if not p.is_finite() or not Decimal(0) <= p <= Decimal(1):
            raise ValueError("INVALID_P_VALUE")
        values.append((name, p))
    ranked = sorted(values, key=lambda item: (item[1], item[0]))
    n = len(ranked)
    for i in range(n - 1, -1, -1):
        if ranked[i][1] <= cutoff / Decimal(n - i):
            return sorted(name for name, _ in ranked[:i + 1])
    return []


def research_readout() -> dict:
    first_gate = Decimal(GATES["DLCO_WEEK24"]) <= Decimal("0.05")
    second_gate = first_gate and Decimal(GATES["DLCO_WEEK48"]) <= Decimal("0.05")
    week24 = hochberg_passed(NON_JP_KR_WEEK24, "0.025") if second_gate else []
    week48 = hochberg_passed(NON_JP_KR_WEEK48, "0.025") if second_gate else []
    return {
        "schema": "MAIN_R58_SVRA_SOURCE_REPORTED_MULTIPLICITY_RESEARCH_ONLY",
        "nct": NCT,
        "applicationCycleId": APPLICATION,
        "sources": {
            "currentSapDocumentDated": "2024-04-24",
            "currentSapUrl": SAP_URL,
            "sponsorSourceReleased": "2024-06-26",
            "sponsorSourceUrl": SPONSOR_URL,
        },
        "outsideJapanSouthKorea": {
            "week24DlcoGatePassesPublishedPThreshold": first_gate,
            "week48DlcoGatePassesPublishedPThreshold": second_gate,
            "week24Alpha": "0.025",
            "week24HochbergNamesPassingPublishedThresholds": week24,
            "week48Alpha": "0.025",
            "week48HochbergNamesPassingPublishedThresholds": week48,
        },
        "japanSouthKorea": {
            "rule": "DLCO_WEEK24_GATE_0.05_THEN_FOUR_ENDPOINT_HOCHBERG_ALPHA_0.05",
            "sourceConfirmedPrespecifiedAaDo2P": None,
            "confirmedFamilyVerdict": "UNDETERMINED",
            "thirdPartyMirrorAaDo2PNotEligibleForVerdict": "0.1043",
        },
        "sourceReportedStatisticsIndependentlyRecomputed": False,
        "originalSignedSapAndUnblindingChronologyIndependentlyVerified": False,
        "clinicalReviewerSignoff": False,
        "independentlyValidatedFdaPredictions": 0,
        "officialApprovalCrlForecast": "ABSTAIN",
        "officialReviewTimingForecast": "ABSTAIN",
        "fdaApprovalProbability": None,
        "measuredHistoricalAccuracy": None,
        "modelTrainingAuthorized": False,
        "clinicalOrProductionWritesAuthorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(research_readout(), indent=2, sort_keys=True))

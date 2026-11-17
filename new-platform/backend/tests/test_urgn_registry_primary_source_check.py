"""Preserved source packet primary CR is consistent with sponsors' UTOPIA readout."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
RECORD=ROOT/"research/source-links/URGN-NCT06331299-UTOPIA-NDA-source-audit-2026-11-17.json"


def load():
    return json.loads(RECORD.read_text(encoding="utf-8"))


def test_registry_exact_nct_packet_and_results_dates():
    d=load()
    p=d["registryPacketVerification"]
    assert p["exactNctId"]==d["nctId"]=="NCT06331299"
    assert p["sourcePacketCanonicalSha256"]=="15eac8f0c55e3eff205f89feb67f3177f0166af88bb30412621e44da6064c0ad"
    assert p["preservedGitHubWorkflowRunId"]==44120924177
    assert p["resultsFirstPostedDate"]=="2026-09-28"
    assert p["postedRecordLastUpdateDate"]=="2026-10-22"
    assert p["trialOverallStatusAtSnapshot"]=="COMPLETED"


def test_registry_primary_matches_sponsor_with_no_inferred_six_month_registry_result():
    d=load()
    p=d["registryPacketVerification"]
    r=p["primaryPosted"]
    sponsor=d["sponsorReportedClinicalResults"]
    assert r["valuePercent"]==sponsor["responseRatePercent"]==77.8
    assert r["denominator"]==sponsor["enrolledDenominator"]==99
    assert r["confidenceInterval95Percent"]==sponsor["responseRate95CI_percent"]==[68.3,85.5]
    assert p["secondarySixMonthDurationOfResponseRegistryStatus"]=="NOT_POSTED"
    assert sponsor["conditionalSixMonthDurationOfResponseKM_percent"]==94.5
    assert p["clinicallyAdjudicated"] is False
    assert d["scientificScore"] is None
    assert d["fdaApprovalProbability"] is None

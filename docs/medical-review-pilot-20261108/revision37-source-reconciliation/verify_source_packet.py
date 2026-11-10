"""Offline documentary packet integrity; never clinical adjudication or grading."""
from pathlib import Path
import datetime
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DIGEST = re.compile(r"[0-9a-f]{64}")
checks = {}

def check(name, condition):
    checks[name] = bool(condition)
    if not condition:
        raise ValueError("SOURCE_PACKET_INTEGRITY_FAILED: " + name)

packet = json.loads((HERE / "reviewer-barrier-packet.json").read_text())
receipt = json.loads((HERE / "accepted-manuscript-receipt.json").read_text())
metadata = json.loads((HERE / "metadata-retrieval-receipts.json").read_text())
pilot = json.loads((ROOT / "new-platform/frontend/data/acacia-pilot-prediction-workup-20261108.json").read_text())
positions = {a["id"] + ":L" + str(i) for a in pilot["criticalAssessmentEvidence"] for i in a["candidateMethodIndices"]}
check("exact_nct_and_doi", packet["nct"] == receipt["nct"] == metadata["nct"] == "NCT06081894" and receipt["doi"] == "10.1056/NEJMoa2603021")
check("five_named_barriers", len(packet["barriers"]) == len({b["id"] for b in packet["barriers"]}) == 5)
check("classification_allowlist", all(b["status"] in packet["classifications"] and all(g["status"] in packet["classifications"] for g in b["subgates"]) for b in packet["barriers"]))
check("method_positions_are_existing", len(positions) == 18 and all(set(f["positions"]) <= positions for f in packet["findings"]))
check("barrier_findings_are_resolvable", all(set(b["supportedFindingIds"]) <= {f["id"] for f in packet["findings"]} for b in packet["barriers"]))
check("source_receipt_exact_bytes", receipt["httpStatus"] == 200 and receipt["sourceBytes"] == 620808 and receipt["sourceSha256"] == "20a804bd113bb40231aec4da466864be0834f78b86c926c8142cc6a0afc67866")
check("accepted_not_final_version", receipt["version"] == "ACCEPTED_MANUSCRIPT_NOT_FINAL_VERSION_OF_RECORD" and receipt["exactIdentityChecks"]["paperPages"] == 33)
check("visual_documentary_scope_not_clinical", receipt["visualDocumentChecks"]["printedPages"] == [7, 11, 13] and receipt["visualDocumentChecks"]["independentClinicalSignoff"] is False)
check("original_license_preserved", receipt["licenseObservedAtOriginalRepository"] == "CC BY-NC-ND" and receipt["copiedToRepositoryOrTrainingCorpus"] is False)
check("no_full_licensed_document_import", not any(p.suffix.lower() in {".pdf", ".txt", ".png"} for p in HERE.iterdir()))
check("no_backdated_full_text_clock", receipt["firstPublicFullManuscriptAvailabilityVerified"] is False)
check("new_metadata_channels_succeeded", len(metadata["sources"]) == 3 and all(x["httpStatus"] == 200 and x["exactDoiMatched"] and x["originalClinicalDocument"] is False for x in metadata["sources"]))
for source in metadata["sources"]:
    path = HERE / source["artifact"]
    check(source["id"] + "_filtered_metadata_digest", hashlib.sha256(path.read_bytes()).hexdigest() == source["artifactSha256"] and path.stat().st_size == source["artifactBytes"] and bool(DIGEST.fullmatch(source["sourceResponseSha256"])))
check("population_arithmetic_not_clinical", packet["documentaryCalculations"][0]["result"] == 517 - 1 and packet["documentaryCalculations"][1]["result"] == round(100 * 7 / 258, 2))
check("coverage_and_grade_counts_preserved", packet["coverage"]["existingMappedPositionsBefore"] == packet["coverage"]["existingMappedPositionsAfter"] == 18 and packet["coverage"]["positionsNotSourceMapped"] == 782 and packet["coverage"]["officialMethodGradesBefore"] == packet["coverage"]["officialMethodGradesAfter"] == packet["coverage"]["clinicalLedgerWrites"] == 0)
check("review_authorization_still_pending", packet["barriers"][-1]["status"] == "REVIEW_PENDING" and packet["coverage"]["qualifiedPhaseSignoffs"] == packet["coverage"]["independentAssessmentsCompleted"] == 0)
check("forecasts_abstain", set(packet["fdaPredictions"].values()) == {"ABSTAIN"} and packet["certainty"] == "NOT_VALIDATED" and packet["accuracy"] == "NOT_CALIBRATED")
check("no_restricted_or_production_writes", packet["coverage"]["restrictedRequestsSent"] == packet["coverage"]["productionWrites"] == 0 and receipt["accessBypass"] is False)
original = Path("/tmp/acacia-r37-glasgow-accepted.pdf")
local_byte_check = None
if original.exists():
    local_byte_check = hashlib.sha256(original.read_bytes()).hexdigest() == receipt["sourceSha256"] and original.stat().st_size == receipt["sourceBytes"]
    check("temporary_original_digest_rechecked", local_byte_check)
result = {"schema": "ACACIA_BARRIER_PACKET_VALIDATION_V1", "checkedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(), "scope": "Documentary metadata/digest and safety-boundary checks, not independent scientific tests", "passed": sum(checks.values()), "failed": 0, "checks": checks, "temporaryOriginalAvailable": original.exists(), "temporaryOriginalDigestRechecked": local_byte_check, "artifacts": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.iterdir()) if p.is_file() and p.name != "validation-receipt.json"}}
(HERE / "validation-receipt.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"passed": result["passed"], "failed": 0, "independentScientificGrades": 0}))

#!/usr/bin/env python3
"""Auditable 741-NCT MAIN Phase 3 status scorecard.

Two distinct numerators: registry/SEC RESEARCH SOURCE COVERAGE and the number
of independently substantiated qualification requirements. A source URL, a
retrieved filing index, or a reviewer-reported assertion never promotes a gate.
Research only; no financial advice, orders, prediction, Pipeline/GEM changes.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.phase3_qualification_ledger import GATES
from scripts.phase3_rights_review_worklist import REQUIRED_REVIEW

TRIALS = 741
ISSUERS = 130
GATE_SLOTS = TRIALS * len(GATES)
REVIEW_SLOTS = TRIALS * len(REQUIRED_REVIEW)
NCT = re.compile(r"^NCT[0-9]{8}$")
GATE_STATES = {"PASS", "FAIL", "REVIEW"}


def exact_trials(items, label):
    if not isinstance(items, list) or len(items) != TRIALS:
        raise ValueError(f"Expected 741 {label} trial records")
    result = {}
    for row in items:
        if not isinstance(row, dict):
            raise ValueError(f"Malformed {label} record")
        nct = row.get("nct_id")
        if not isinstance(nct, str) or not NCT.fullmatch(nct) or nct in result:
            raise ValueError(f"Duplicated or invalid {label} NCT")
        result[nct] = row
    return result


def build_scorecard(ledger, program, sec, pilot, worklist, reviewed):
    if not all(isinstance(x, dict) for x in (ledger, program, sec, pilot, worklist, reviewed)):
        raise ValueError("Source reports must be objects")
    if (ledger.get("report_type") != "MAIN_PHASE3_QUALIFICATION_EVIDENCE_LEDGER_RESEARCH_ONLY"
        or ledger.get("total") != TRIALS
        or ledger.get("qualified_pipeline_total") is not None
        or program.get("report_type") != "MAIN_PHASE3_ORIGINAL_DRUG_INDICATION_TERMS_RESEARCH_ONLY"
        or program.get("total_trials") != TRIALS
        or program.get("total_saved_issuer_pointers") != ISSUERS
        or program.get("independently_verified_program_identities") != 0
        or program.get("independently_verified_commercial_rights") != 0
        or program.get("qualified_pipeline_total") is not None
        or sec.get("report_type") != "MAIN_PHASE3_SEC_RIGHTS_FILING_LEADS_RESEARCH_ONLY"
        or sec.get("total_trials") != TRIALS or sec.get("total_issuers") != ISSUERS
        or sec.get("verified_current_commercial_rights") != 0
        or sec.get("qualified_pipeline_total") is not None
        or pilot.get("report_type") != "MAIN_PHASE3_SEC_PRIMARY_RIGHTS_DOCUMENT_PILOT_RESEARCH_ONLY"
        or pilot.get("total_trials") != TRIALS or pilot.get("total_issuers") != ISSUERS
        or pilot.get("independently_verified_current_rights") != 0
        or pilot.get("qualified_pipeline_total") is not None
        or worklist.get("report_type") != "MAIN_PHASE3_COMMERCIAL_RIGHTS_REVIEW_WORKLIST_RESEARCH_ONLY"
        or worklist.get("total_trials") != TRIALS
        or worklist.get("total_issuer_research_pointers") != ISSUERS
        or worklist.get("rights_checks_required_per_trial") != len(REQUIRED_REVIEW)
        or worklist.get("independently_verified_current_rights") != 0
        or worklist.get("qualified_pipeline_total") is not None
        or reviewed.get("report_type") != "MAIN_PHASE3_RIGHTS_REVIEW_SUBMISSIONS_COVERAGE_RESEARCH_ONLY"
        or reviewed.get("trial_denominator") != TRIALS
        or reviewed.get("requirements_per_trial") != len(REQUIRED_REVIEW)
        or reviewed.get("checklist_slot_denominator") != REVIEW_SLOTS
        or reviewed.get("independently_verified_commercial_rights") != 0
        or reviewed.get("qualified_pipeline_total") is not None):
        raise ValueError("Incomplete or qualifying source report in scorecard")

    ledgers = exact_trials(ledger.get("records"), "ledger")
    programs = exact_trials(program.get("items"), "program")
    studies = exact_trials(sec.get("trials"), "SEC issuer association")
    workrows = exact_trials(worklist.get("items"), "review worklist")
    reviews = exact_trials(reviewed.get("items"), "review submission coverage")
    if not (set(ledgers) == set(programs) == set(studies) == set(workrows) == set(reviews)):
        raise ValueError("741 NCT source scopes do not match")
    if not isinstance(sec.get("issuers"), list) or len(sec["issuers"]) != ISSUERS:
        raise ValueError("Issuer SEC dataset is not complete")
    if not isinstance(pilot.get("issuers"), list) or len(pilot["issuers"]) != ISSUERS:
        raise ValueError("SEC primary document pilot issuer denominator changed")

    gate_counts = {gate: Counter() for gate in GATES}
    per_trial_unresolved = Counter()
    source_stage = Counter()
    priority = Counter()
    programs_named = 0
    complete_checklists = 0
    all_reviewed = 0
    real_doc_trials = 0
    trial_evidence = 0
    for nct, row in ledgers.items():
        p, s, w, review = programs[nct], studies[nct], workrows[nct], reviews[nct]
        gates = row.get("gates")
        if (not isinstance(gates, dict) or set(gates) != set(GATES)
            or any(gates[g] not in GATE_STATES for g in GATES)
            or row.get("qualified_pipeline") is not None
            or p.get("ticker") != row.get("ticker") or w.get("ticker") != row.get("ticker")
            or review.get("ticker") != row.get("ticker")
            or s.get("ticker") != row.get("ticker")
            or w.get("issuer_sec_cik") != s.get("saved_sec_cik")
            or p.get("commercial_rights_verified") is not False
            or p.get("qualified_pipeline") is not None
            or w.get("commercial_rights_verified") is not False
            or w.get("qualified_pipeline") is not None
            or review.get("commercial_rights_verified") is not False
            or review.get("checklist_independently_verified") is not False
            or review.get("qualified_pipeline") is not None):
            raise ValueError(f"{nct}: invalid original source or qualification drift")
        if gates["registry_identity"] != "PASS" or any(
                gates[g] != "REVIEW" for g in GATES if g != "registry_identity"):
            raise ValueError(f"{nct}: only original registry gate may be PASS at this research stage")
        for gate in GATES:
            gate_counts[gate][gates[gate]] += 1
        unresolved = sum(gates[g] == "REVIEW" for g in GATES)
        per_trial_unresolved[unresolved] += 1
        drugs = p.get("provisional_drug_or_biologic_names")
        if not isinstance(drugs, list) or w.get("registered_provisional_drugs") != drugs:
            raise ValueError(f"{nct}: original registered drugs changed")
        programs_named += bool(drugs)
        source_stage[w["source_review_stage"]] += 1
        priority[w["research_priority"]] += 1
        fetched = w.get("sec_source_documents_fetched")
        if not isinstance(fetched, list):
            raise ValueError("SEC source documents missing")
        real_doc_trials += bool(fetched)
        if w.get("commercial_rights_verified") is not False:
            raise ValueError("Research worklist cannot verify rights")
        checks = review.get("checks")
        if not isinstance(checks, dict) or set(checks) != set(REQUIRED_REVIEW):
            raise ValueError(f"{nct}: incomplete six-check review slots")
        submitted = 0
        reviewed_slots = 0
        for detail in checks.values():
            if not isinstance(detail, dict) or type(detail.get("evidence_count")) is not int:
                raise ValueError("Malformed six-check reviewer coverage")
            if detail["evidence_count"] < 0:
                raise ValueError("Negative review evidence")
            submitted += bool(detail["evidence_count"])
            attestations = detail.get("reviewer_attestations_count")
            if type(attestations) is not int or not 0 <= attestations <= detail["evidence_count"]:
                raise ValueError("Malformed reviewer attestation coverage")
            reviewed_slots += bool(attestations)
        trial_evidence += bool(submitted)
        complete_checklists += submitted == len(REQUIRED_REVIEW)
        all_reviewed += reviewed_slots == len(REQUIRED_REVIEW)

    if (programs_named != program.get("trials_with_provisional_drug_or_biologic_mentions")
        or programs_named != worklist.get("trials_with_any_original_provisional_drug")
        or real_doc_trials != worklist.get("trials_with_issuer_primary_document_text")
        or trial_evidence != reviewed.get("trial_count_with_any_submissions")
        or complete_checklists != reviewed.get("trials_with_all_six_submitted_checks")
        or all_reviewed != reviewed.get("trials_with_all_six_reviewer_reported_checks")):
        raise ValueError("Summary totals disagree with NCT records")

    totals = Counter()
    gates_detail = []
    for gate in GATES:
        counts = gate_counts[gate]
        if sum(counts.values()) != TRIALS:
            raise ValueError("Incomplete mandatory gate status denominator")
        totals.update(counts)
        gates_detail.append({
            "gate": gate, "total": TRIALS,
            "pass": counts["PASS"], "fail": counts["FAIL"], "review": counts["REVIEW"],
            "qualification_status": "VERIFIED_REGISTRY_IDENTITY_ONLY" if gate == "registry_identity"
                else "INDEPENDENT_VERIFICATION_NOT_COMPLETE",
        })

    selected = pilot.get("documents_selected_for_retrieval")
    attempted = pilot.get("documents_attempted")
    not_attempted = pilot.get("documents_not_attempted_missing_agent")
    fetched = pilot.get("documents_retrieved")
    blocked = pilot.get("documents_access_failed_or_blocked")
    if (any(type(v) is not int or v < 0 for v in (selected, attempted, not_attempted, fetched, blocked))
        or selected != attempted + not_attempted
        or attempted != fetched + blocked
        or fetched > selected):
        raise ValueError("SEC requested/fetched/missing source counts do not reconcile")
    if type(sec.get("issuer_metadata_fetched")) is not int or not 0 <= sec["issuer_metadata_fetched"] <= ISSUERS:
        raise ValueError("Invalid SEC issuer metadata coverage")
    if sec.get("issuer_metadata_unavailable_or_invalid") != ISSUERS - sec["issuer_metadata_fetched"]:
        raise ValueError("SEC issuer metadata unavailable denominator mismatch")
    with_submissions = reviewed.get("distinct_review_slots_with_submissions")
    without_submissions = reviewed.get("review_slots_without_submissions")
    reviewed_slots = reviewed.get("review_slots_with_reviewer_reported_findings")
    if (any(type(v) is not int or v < 0 for v in (with_submissions, without_submissions, reviewed_slots))
        or with_submissions + without_submissions != REVIEW_SLOTS
        or reviewed_slots > with_submissions):
        raise ValueError("Six-check evidence submission denominators do not reconcile")
    if not all(type(totals[k]) is int for k in ("PASS", "FAIL", "REVIEW")) or sum(totals.values()) != GATE_SLOTS:
        raise ValueError("Nine-gate coverage does not total 6669")

    # No probabilities: the number that satisfy all gates is unknown, not
    # equivalent to 0, because eight gate families have not been adjudicated.
    return {
        "report_type": "MAIN_PHASE3_QUALIFICATION_PROGRESS_SCORECARD_RESEARCH_ONLY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "historical_trial_count": TRIALS,
        "issuer_research_pointer_count": ISSUERS,
        "qualifying_pipeline_count": None,
        "gate_checks_denominator": GATE_SLOTS,
        "gate_checks_pass": totals["PASS"],
        "gate_checks_fail": totals["FAIL"],
        "gate_checks_review": totals["REVIEW"],
        "per_gate": gates_detail,
        "trials_by_unresolved_gate_count": {str(k): v for k, v in sorted(per_trial_unresolved.items())},
        "trials_with_provisional_registered_drug": programs_named,
        "trials_without_provisional_registered_drug": TRIALS - programs_named,
        "sec_issuer_indexes_fetched": sec["issuer_metadata_fetched"],
        "sec_issuer_indexes_not_fetched": sec["issuer_metadata_unavailable_or_invalid"],
        "sec_primary_documents_selected": selected,
        "sec_primary_documents_attempted": attempted,
        "sec_primary_documents_not_attempted_missing_contact": not_attempted,
        "sec_primary_documents_fetched": fetched,
        "sec_primary_documents_failed_or_blocked": blocked,
        "trial_issuer_text_available": real_doc_trials,
        "trial_issuer_text_unavailable": TRIALS - real_doc_trials,
        "source_review_priority_counts": dict(sorted(priority.items())),
        "source_review_stage_counts": dict(sorted(source_stage.items())),
        "rights_review_checklist_slots": REVIEW_SLOTS,
        "rights_slots_with_submissions": with_submissions,
        "rights_slots_without_submissions": without_submissions,
        "rights_slots_with_reviewer_reports": reviewed_slots,
        "trials_with_any_submissions": trial_evidence,
        "trials_with_all_six_submitted": complete_checklists,
        "trials_with_all_six_reviewer_reported": all_reviewed,
        "independently_verified_current_rights_trials": 0,
        "qualified_trial_count": None,
        "blockers": (
            ["SEC_USER_AGENT_IDENTIFYING_CONTACT_REQUIRED"] if not_attempted
            else ["NO_SEC_PRIMARY_DOCUMENTS_RETRIEVED"] if fetched == 0
            else ["TRIAL_SPECIFIC_LEGAL_RIGHTS_EVIDENCE_REVIEW"]
        ) + ["EIGHT_NONREGISTRY_MANDATORY_GATES_REQUIRE_VERIFICATION"],
        "limitations": (
            "The 741 source identities are a historical trial census, not qualified "
            "Pipeline, GEM JR or GEM entries. 741 registry PASS checks are NOT 741 "
            "qualified trials. 0/741 rights verified means none independently "
            "verified in this workflow, not absence of rights. Reviewer-reported "
            "evidence is not legal adjudication. No approval probabilities or "
            "trading actions. Preserve all independent FS/FA presets."
        ),
    }


def render_markdown(report):
    """Compact primary status with collapsed secondary details for GitHub Actions."""
    n = report
    lines = [
        "# MAIN Phase 3 — research qualification progress",
        "",
        f"Verified at: {n['generated_at_utc']} (UTC). **Research only; not a production Pipeline membership report.**",
        "",
        "| Metric | Confirmed / Denominator | Meaning |",
        "|:--|--:|:--|",
        f"| ClinicalTrials.gov source identity | {n['per_gate'][0]['pass']}/{TRIALS} | Original trial identities, not trial eligibility |",
        f"| Registered provisional drug/biologic named | {n['trials_with_provisional_registered_drug']}/{TRIALS} | Registry label, not independently verified molecule |",
        f"| SEC issuer indexes fetched | {n['sec_issuer_indexes_fetched']}/{ISSUERS} | Company filing metadata, not product rights |",
        f"| SEC primary document requests attempted | {n['sec_primary_documents_attempted']}/{n['sec_primary_documents_selected']} | Source access coverage |",
        f"| SEC primary documents fetched | {n['sec_primary_documents_fetched']}/{n['sec_primary_documents_selected']} | Original source text available to review |",
        f"| Trials with issuer primary text available | {n['trial_issuer_text_available']}/{TRIALS} | Issuer-level text only |",
        f"| Commercial-rights evidence slots with submissions | {n['rights_slots_with_submissions']}/{REVIEW_SLOTS} | Claims submitted, not legal rights verified |",
        f"| Independent commercial-rights determinations | 0/{TRIALS} | Not established in workflow |",
        f"| Mandatory gate checks verified PASS | {n['gate_checks_pass']}/{GATE_SLOTS} | Only registry identity gate is PASS |",
        f"| Mandatory gate checks unresolved REVIEW | {n['gate_checks_review']}/{GATE_SLOTS} | Independent verification outstanding |",
        "",
        f"**Qualified Pipeline total:** **UNKNOWN** (not zero).  **SEC selected but not attempted for missing identifying contact:** "
        f"{n['sec_primary_documents_not_attempted_missing_contact']}/{n['sec_primary_documents_selected']}.",
        "",
        "<details><summary>All nine mandatory gates (741 trials per gate)</summary>",
        "",
        "| Mandatory gate | PASS / 741 | FAIL / 741 | REVIEW / 741 |",
        "|:--|--:|--:|--:|",
    ]
    for gate in n["per_gate"]:
        lines.append(f"| {gate['gate']} | {gate['pass']}/{TRIALS} | {gate['fail']}/{TRIALS} | {gate['review']}/{TRIALS} |")
    lines += [
        "",
        "</details>",
        "",
        "<details><summary>Secondary rights source/reviewer coverage</summary>",
        "",
        f"- Submitted six-check requirements: {n['rights_slots_with_submissions']}/{REVIEW_SLOTS}",
        f"- Requirements with reviewer-reported findings: {n['rights_slots_with_reviewer_reports']}/{REVIEW_SLOTS}",
        f"- Trials with any submitted claim: {n['trials_with_any_submissions']}/{TRIALS}",
        f"- Trials with all six submissions: {n['trials_with_all_six_submitted']}/{TRIALS}",
        f"- Trials with all six reviewer reports: {n['trials_with_all_six_reviewer_reported']}/{TRIALS}",
        "",
        "Research queue priority distribution:",
    ]
    lines.extend(f"- {k}: {v}/{TRIALS}" for k, v in n["source_review_priority_counts"].items())
    lines += [
        "",
        "</details>",
        "",
        f"**Next blocker(s):** {', '.join(n['blockers'])}.",
        "",
        f"_{n['limitations']}_",
    ]
    return "\n".join(lines) + "\n"


def main():
    if len(sys.argv) != 9:
        sys.exit(
            "Usage: phase3_qualification_scorecard.py <ledger> <program> <sec-leads> "
            "<pilot-documents> <rights-worklist> <rights-review-submissions> "
            "<report.json> <summary.md>"
        )
    sources = [json.loads(Path(p).read_text(encoding="utf-8")) for p in sys.argv[1:7]]
    report = build_scorecard(*sources)
    json_path, md_path = (Path(sys.argv[7]), Path(sys.argv[8]))
    for p in (json_path, md_path):
        p.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(
        f"MAIN scorecard: {report['gate_checks_pass']}/{GATE_SLOTS} source-verified mandatory checks, "
        f"{report['gate_checks_review']}/{GATE_SLOTS} outstanding; "
        f"{report['rights_slots_with_submissions']}/{REVIEW_SLOTS} rights submissions; "
        f"qualified Pipeline UNKNOWN"
    )


if __name__ == "__main__":
    main()

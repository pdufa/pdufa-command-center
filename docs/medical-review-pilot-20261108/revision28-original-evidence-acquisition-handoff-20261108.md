# MAIN Revision 28 — original evidence acquisition handoff and unsent request draft

**Pilot:** ACACIA-HCM, NCT06081894, CY 6033.  
**Evidence snapshot:** 2026-11-08 (research-only; source gaps rechecked November 9 UTC).  
**Release:** Draft PR #965; no production medical code, no reviewer writes, no sponsor email sent.

## Installed

The Phase III review queue now connects to a versioned, exact-trial, research-only evidence acquisition packet containing **six original-source requests** that jointly cover all **18 source-mapped method positions** (the remaining 782 positions are not source mapped). The six requests are:

1. Authenticated final, dated and locked primary SAP with prespecified hypotheses, multiplicity, version history and approvals.
2. Full co-primary KCCQ-CSS/peak-VO2 sensitivity, missingness, intercurrent events and analysis population tables.
3. Original serious-heart-failure event definition and follow-up reconciliation for the secondary **11 treated/1 placebo** versus later sponsor **12 treated/3 placebo**.
4. Treatment-interruption numerators/denominators, LVEF, exposure/time-at-risk, event severity and causality.
5. Dated protocol amendments, original trial conduct, 516-versus-517 trial accounting and CONSORT.
6. Date- and indication-verified nonobstructive-HCM FDA supplement filing/acceptance/action-date status, **distinct from obstructive-HCM labeling**.

The source package records the exact mapped method positions, required original evidence, independent reviewer acceptance criteria and explicit acquisition state `DRAFT_NOT_SENT`. The original public-source audit references are [#42555289486](https://github.com/pdufa/pdufa-command-center/actions/runs/42555289486) and [#42556948533](https://github.com/pdufa/pdufa-command-center/actions/runs/42556948533). The prior audit did **not** authenticate a final locked primary SAP or reconcile HF event definitions. Publisher and Europe PMC automated retrieval failures are source-access failures, not evidence of nonexistence.

### Files

- `new-platform/frontend/lib/acacia-evidence-acquisition-handoff.ts`: exact-NCT, source/phase/grade-state guarded versioned packet and downloadable plain-text inquiry **DRAFT**. Validates six unique requests cover exactly the expected 18 mapped research positions and refuses changed official grade/phase/source states. No mail or patient-level data access code.
- `new-platform/frontend/app/api/predictions/medical-evidence-acquisition/route.ts`: dashboard-authenticated, GET-only `?nct=NCT06081894`, JSON or `&format=txt`, private no-store, exact-NCT validation and explicit draft-only download name. No POST/send/write.
- `new-platform/frontend/app/predictions/assessment/PilotEvidenceAcquisitionPacket.tsx`: six expandable original-evidence requests, affected positions, independent verification rules, source audit links and clearly labeled *unsent* inquiry download in PREDICTIONS.
- `new-platform/frontend/tests/acacia-evidence-acquisition-handoff.test.cjs`: validates six requirements, exact 18-position coverage, rejection of incorrect NCT/source/reviewer states, no authorized grades and no mail sends.
- `new-platform/backend/scripts/verify_medical_preview.py`: signed-in HTML, JSON and TXT live acceptance on Vercel preview; anonymously inaccessible, 422 for wrong NCT, zero clinical/sponsor writes.

### Access restrictions and scientific limitations

The published contact `medicalaffairs@cytokinetics.com` is provided solely as a **qualified-researcher eligibility inquiry**. Sponsor rules, timing, applicable clinical study sharing policy and data access agreement govern access. The app prepares an editable **unsent** inquiry; it has not submitted any request or represented that access is granted. The packet contains only high-level source requests and no identifiable patient data.

No new original documents were authenticated, no independent Phase III reviewer signed off, and no 0–5 clinical grades were issued (**0/800 official grades** for pilot). FDA approval/CRL/delay remains **ABSTAIN**; model accuracy is **NOT CALIBRATED**. Research-source availability/checklist counts must never be represented as FDA prediction accuracy.

**Next substantive research gate:** Obtain the actual original source documents under applicable public or sponsor-authorized terms, independently verify versions and methods, resolve serious-HF event differences, then use the separated append-only qualified reviewer workflow; expand to other methods and trials only with independent phase-specific source checks.

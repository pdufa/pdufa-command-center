# ORCA-2 six-level research review packet

OWNER-ONLY, OUTCOME-EXPOSED RESEARCH. Owner status: OWNER_NOT_REVIEWED. No external verification required. No claim of independent certification. Live deployment remains separately controlled.

Core originals are collected, not necessarily complete. Owner research can proceed without external signoff; scientific uncertainty and real source checks remain visible.

## Source inventory

| Source | Date / version (unreviewed) | Link | SHA-256 |
|---|---|---|---|
| registry | 2026-01-15 / 2026-01-15 | https://clinicaltrials.gov/api/v2/studies/NCT04576949 | 39ad68a0b06ec3f4ce59092aa14114ef6eeae1d43569edfa12b23dda6b490742 |
| protocol-v4 | 2021-03-08 / 4.0 | https://cdn.clinicaltrials.gov/large-docs/49/NCT04576949/Prot_000.pdf | c0ec264fb43b3b1a8cfdaaf7d61fa837f4b2abd8d747dfd858f1473f30d1ac08 |
| sap-v1 | 2022-03-25 / 1.0 | https://cdn.clinicaltrials.gov/large-docs/49/NCT04576949/SAP_001.pdf | 621617c3bbfbba9e8eadd2e7b35513e0693b8531119ebf3bac7b66fcb15ff3f2 |
| primary-report | 2023-07-11 / None | https://pmc.ncbi.nlm.nih.gov/articles/PMC10336611/ | 470eb255539db3aa78a240345396e6b68b2c8ced1d39ee89c62214c8ea4a52fd |
| sponsor-last-visit | 2022-01-04 / None | https://ir.achieverx.com/news-events/press-releases/detail/10/achieve-life-sciences-announces-completion-of-last-subject-last-follow-up-visit-in-phase-3-orca-2-trial-of-cytisinicline-for-smoking-cessation | a2a9751a04a1ca06677ee85257650e5fdfb4a894de382538cbfad3bd1fb3a63b |
| sponsor-pre-readout | 2022-03-10 / None | https://ir.achieverx.com/news-events/press-releases/detail/136/achieve-life-sciences-reports-financial-results-for-fourth-quarter-and-year-end-2021-and-provides-corporate-update | 057a9e4a6be4b274b23224895f9d82448bc5e4842271ff6fd7106ac7091e0e56 |
| sponsor-topline | 2022-04-27 / None | https://ir.achieverx.com/news-events/press-releases/detail/141/achieve-life-sciences-announces-successful-statistically-significant-smoking-cessation-results-in-phase-3-orca-2-clinical-trial-of-cytisinicline-in-adult-smokers | 24c6f6afdbda05195b56283a3287b8b752a1774cb1b23a5623dbc592a6eee620 |
| sponsor-dsmc-2021 | 2021-11-22 / None | https://ir.achieverx.com/news-events/press-releases/detail/13/achieve-life-sciences-announces-phase-3-orca-2-trial-of-cytisinicline-in-smoking-cessation-clears-final-review-by-data-safety-monitoring-committee-dsmc | daea2c6d0ed18233a813dddc016b34b6b4fcaa9db5e4c621b18b66837e7c20cd |
| fda-multiple-endpoints-2017 | January 2017 / Draft | https://www.fda.gov/media/102657/download | 2beceb66e56377248d0da43e96ce3177023d4027bf2b459bcec0ad0c1040d70b |
| fda-multiple-endpoints-2022 | October 2022 / Final | https://www.fda.gov/media/162416/download | 40284a050aab0037799072b2340e37d4b02ab6f7f2339fff6ea1cd55673a9563 |
| fda-e9 | September 1998 / Final | https://www.fda.gov/media/71336/download | f64a79a9800d523e50ac3c33af6fbd5de0c229b984e51b224bd5d58c26b12325 |

## Chronology

- 2020-10-06: Initial registry posting date reported in the current registry packet; original historical versions were not retrieved. Sources: registry; statusModule.studyFirstPostDateStruct.
- 2021-03-08: Collected protocol cover identifies version 4.0; statistical section describes primary multiplicity handling before primary completion. Sources: protocol-v4; cover; section 16.1.
- 2021-11-22: Sponsor reports final DSMC review and follow-up ongoing. This does not establish sponsor unblinding or absence of limited safety access. Sources: sponsor-dsmc-2021; dated article body.
- 2021-12-23: Registry reports actual primary completion and study completion on this date. Completion is not database lock. Sources: registry; statusModule.primaryCompletionDateStruct; completionDateStruct.
- 2022-01-04: Sponsor announces last follow-up visit occurred in late December 2021. It provides no exact database-lock or unblinding date. Sources: sponsor-last-visit; dated article body.
- 2022-03-10: Pre-readout disclosure anticipates topline results in Q2 2022; this is not a blinded-status attestation. Sources: sponsor-pre-readout; ORCA-2 completion/readout paragraph.
- 2022-03-25: SAP cover/header identifies version 1.0, dated March 25; effective approval date is not independently established. Sources: sap-v1; PDF pages 1–2.
- 2022-03-29: Embedded certificate reports signing complete on March 29. Document-internal signature claims are unauthenticated and do not certify the research workflow. Sources: sap-v1; PDF pages 51–52; Envelope Summary Events.
- 2022-04-27: Sponsor publishes topline ORCA-2 results. Public disclosure is distinct from actual analyst/sponsor unblinding. Sources: sponsor-topline; dated article body.
- 2023-07-11: Primary trial report publication date. Current full HTML has now been retrieved, unlike the prior failed primary full-text XML request. Sources: primary-report; article metadata; PMC10336611 / PMID37432430.
- UNRESOLVED: Actual database-lock date, unblinding date, legally effective SAP approval and earlier standalone SAP versions remain UNRESOLVED. Sources: protocol-v4, sap-v1, primary-report, sponsor-topline; protocol 7.3.3–7.3.4; SAP 1 and certificate; article methods.

Database lock, actual unblinding, effective approval date and earlier standalone SAP versions remain UNRESOLVED. Date ordering alone does not establish post-hoc analysis.

## Discrepancies and collection limits

- SAP section 1 references protocol v3.0 dated September 10, 2020, while the collected protocol is v4.0 dated March 8, 2021. Earlier protocol versions, amendment log and an owner reconciliation are missing.
- SAP cover date (March 25) and embedded signing completion (March 29) are different events; neither establishes database lock or first access to unblinded comparative data. No earlier standalone SAP was located in the searched sources; absence is not proven.
- The primary report names Hochberg multiplicity control but reference 23 is Benjamini/Hochberg false-discovery-rate literature; SAP section 10 specifies familywise-error control. Reconcile implemented procedure and reference accuracy; do not assume analysis failure.
- Protocol 16.1/16.2 and SAP 4.1.1/6.5/10 retain all-randomized efficacy analysis in their descriptions. There is no collected proof of a changed ITT population, but analysis-set approval and implementation records remain missing.
- The earlier first-case summary overstated primary-report full-text collection. Saved data showed only the COPD post-hoc full text; the primary report XML request failed. Primary-report HTML was retrieved in this run; the earlier report is preserved unchanged.
- Journal supplements 1–4 returned HTML download/challenge pages, not PDFs. Registry history JSON returned HTTP 403; history-page HTML alone is not a version history. A candidate SAP_000 URL returned 404. These access results do not prove nonpublic status or absence of earlier versions.
- Current sponsor archive redirects to achieverx.com and presents changed branding. Preserve ACHV/company/cycle relationships from the frozen FOCUS roster; ownership/alias reconciliation needs owner source cross-checking.
- FDA approved-drug query for cytisinicline returned no record; this does not exclude INDs, pending NDA submissions or other correspondence. FDA guidance is context, not trial-specific FDA endorsement.

## Level 1 — Source provenance

Core originals are available for owner source checking; provenance and package completeness remain unresolved. Matching bytes and embedded signing claims confer no independent trust.

- Registry original, registered protocol/SAP originals and primary report HTML are retained with exact receipts. FDA statistical guidance and contemporaneous sponsor disclosures are separately scoped. Sources: registry, protocol-v4, sap-v1, primary-report; sourceInventory; source-role and document-version fields.
- The retained SAP contains an embedded completion certificate; no external verification of that certificate or its signing chain has been performed. Sources: sap-v1; PDF pages 51–52.

Supporting reasons:
- Exact study code and NCT-linked source locators support traceability; original bytes were rechecked locally.

Contradictions/questions:
- Public URL, matching digest and embedded signature text are not independent authentication.

Risks and limitations:
- Historical registry revisions and journal supplement copies were not acquired; sponsor redirects require ownership reconciliation.

Missing information:
- Original history export, original protocol versions and complete amendment log
- Original SAP certificate/effective-approval record if available; owner research can proceed with this gap
- Owner source/version reconciliation and explicit owner self-review decision; no outside verification required.

Owner check questions:
- Verify source ownership, original bytes, exact trial identity, dates, versions and cutoff using original sources.
- Can the embedded certificate be cross-checked by the owner without exposing private signer information?

Remaining evidence issues:
- Earlier protocol/SAP versions and executed chronology remain incomplete.
- Owner acceptance has not been recorded; research can proceed without external verification.

Readiness: READY_FOR_OWNER_RESEARCH_WITH_UNRESOLVED_EVIDENCE.

| Gate | Passed |
|---|---|
| CODE_IMPLEMENTED | True |
| TESTS_PASSED | True |
| ORIGINAL_EVIDENCE_COLLECTED | True |
| OWNER_REVIEW_COMPLETED | False |

## Level 2 — Trial identity and phase

Phase 3 smoking-cessation research is appropriate. Preserve exact trial/population boundaries; do not import ORCA-3 or COPD post-hoc findings as ORCA-2 primary outcomes.

- Registry identifies ACH-CYT-03 / ORCA-2 as Phase 3, completed, in adult smokers; the primary paper describes 17 US sites, 810 randomized adults and smoking-cessation behavioral support. Sources: registry, protocol-v4, primary-report; identificationModule; designModule; eligibilityModule; paper Methods.
- The frozen application candidate achv-cytisinicline remains provisional; no verified application-cycle identity is bound. Sources: registry; packet candidateApplicationCycleIdsUnverified; no registry-to-FDA cycle attestation.

Supporting reasons:
- Study identifier, intervention, population and registered primary windows can be compared across retained sources.

Contradictions/questions:
- SAP references protocol v3.0 rather than collected v4.0; current website branding differs from frozen roster.

Risks and limitations:
- No owner source cross-checking of current phase/status, sponsor aliases or application cycle.

Missing information:
- Original application/submission-cycle documentary linkage
- Historical phase/status and eligibility amendment reconciliation
- Owner source/version reconciliation and explicit owner self-review decision; no outside verification required.

Owner check questions:
- Reconcile NCT04576949 / ACH-CYT-03 across all originals.
- Do any protocol amendments change the enrolled population or applicability?

Remaining evidence issues:
- Earlier protocol/SAP versions and executed chronology remain incomplete.
- Owner acceptance has not been recorded; research can proceed without external verification.

Readiness: READY_FOR_OWNER_RESEARCH_WITH_UNRESOLVED_EVIDENCE.

| Gate | Passed |
|---|---|
| CODE_IMPLEMENTED | True |
| TESTS_PASSED | True |
| ORIGINAL_EVIDENCE_COLLECTED | True |
| OWNER_REVIEW_COMPLETED | False |

## Level 3 — Efficacy and clinical findings

Reported cessation outcomes support a bounded efficacy research discussion. Treatment-end and follow-up effects, denominators, uncertainty and harms must be reconciled before an owner benefit-risk assessment.

- The report describes 810 randomized participants: 270 in the 12-week arm, 269 in the 6-week arm and 271 placebo. Continuous abstinence was 32.6% versus 7.0% at weeks 9–12 and 25.3% versus 4.4% at weeks 3–6. Sources: primary-report, registry; paper Results/Table 2; registry outcomeMeasuresModule.
- Reported follow-up abstinence was 21.1% versus 4.8% through week 24 for the 12-week comparison, and 8.9% versus 2.6% for the 6-week comparison. Outcomes have different windows and placebo rates. Sources: primary-report; paper Table 2.
- Safety analysis uses 809 exposed participants; placebo safety denominator is 270 rather than 271 randomized. The report lists serious adverse events but none judged treatment related, including one death in the 6-week group. Sources: primary-report; paper Table 3 and footnote; Results adverse events.
- The paper reports primary odds ratios of 6.3 (95% CI 3.7–11.6) for 12-week treatment and 8.0 (95% CI 3.9–16.3) for 6-week treatment. These are published estimates, not new calculations or an independent significance judgment. Sources: primary-report; paper Results and Table2.

Supporting reasons:
- Original primary report and posted aggregate registry results are collected; efficacy and safety populations are kept distinct.

Contradictions/questions:
- No treatment-related serious event is not the same as no serious events. Randomized and safety denominators differ for a stated exposure reason.

Risks and limitations:
- No active comparator; 24-week follow-up does not establish long-term disease-outcome benefit or exclude uncommon harms.

Missing information:
- Owner endpoint-by-endpoint registry/paper table reconciliation and sensitivity outputs
- Full CSR and adjudicated harms/death attribution evidence if lawfully available
- Owner source/version reconciliation and explicit owner self-review decision; no outside verification required.

Owner check questions:
- Confirm participant counts, outcome windows, effect estimates and uncertainty from originals.
- Review all serious events, death, withdrawals, adherence and missing data without equating attributed relatedness with absence of risk.

Remaining evidence issues:
- Earlier protocol/SAP versions and executed chronology remain incomplete.
- Owner acceptance has not been recorded; research can proceed without external verification.

Readiness: READY_FOR_OWNER_RESEARCH_WITH_UNRESOLVED_EVIDENCE.

| Gate | Passed |
|---|---|
| CODE_IMPLEMENTED | True |
| TESTS_PASSED | True |
| ORIGINAL_EVIDENCE_COLLECTED | True |
| OWNER_REVIEW_COMPLETED | False |

## Level 4 — Protocol and trial design

The collected design supports review preparation. Its execution, amendment history and safeguards against operational unblinding cannot be certified from planned procedures.

- Protocol v4.0 describes a randomized blinded placebo-controlled trial with three arms, two treatment durations, behavioral support and follow-up to week 24. Sources: protocol-v4, primary-report; protocol synopsis and sections 7/16; paper Methods.
- The protocol describes planned blinding/unblinding controls, not an executed unblinding timestamp. A sponsor DSMC review disclosure likewise does not establish comparative-data access history. Sources: protocol-v4, sponsor-dsmc-2021; protocol 7.3.3–7.3.4; sponsor November 22 disclosure.

Supporting reasons:
- A protocol predating primary completion is collected and can be compared with the reported study.

Contradictions/questions:
- SAP introductory protocol reference and current collected protocol version differ; formal amendment reconciliation is missing.

Risks and limitations:
- Exclusions limit generalization to serious mental illness, recent unstable cardiovascular disease and other excluded populations; missing visits/adherence may affect interpretation.

Missing information:
- Protocol versions 1–3 and amendment/IRB implementation records
- Executed allocation, database-lock and access/unblinding logs; deviations summary
- Owner source/version reconciliation and explicit owner self-review decision; no outside verification required.

Owner check questions:
- Which v3-to-v4 changes affected endpoints, population, conduct or analysis?
- Were blinding, randomization and behavioral support implemented as planned?

Remaining evidence issues:
- Earlier protocol/SAP versions and executed chronology remain incomplete.
- Owner acceptance has not been recorded; research can proceed without external verification.

Readiness: READY_FOR_OWNER_RESEARCH_WITH_UNRESOLVED_EVIDENCE.

| Gate | Passed |
|---|---|
| CODE_IMPLEMENTED | True |
| TESTS_PASSED | True |
| ORIGINAL_EVIDENCE_COLLECTED | True |
| OWNER_REVIEW_COMPLETED | False |

## Level 5 — Statistical analysis

Prespecification remains UNRESOLVED. March cover/signing dates after last visit do not establish post-hoc planning, and dates before public readout do not prove planning before unblinding.

- SAP v1.0 cover is dated March 25, 2022; its embedded completion certificate reports March 29, 2022. Registry primary completion is December 23, 2021; public topline disclosure is April 27, 2022. Sources: sap-v1, registry, sponsor-topline; SAP cover and PDF51–52; registry primaryCompletionDateStruct; dated sponsor article.
- Protocol 16.1 already describes Hochberg with overall one-sided alpha 0.025. SAP 10.1 describes primary familywise-error control, conditional alpha propagation to secondaries and exploratory endpoints without multiplicity protection. Bonferroni appears in sizing assumptions. Sources: protocol-v4, sap-v1; protocol 16.1; SAP 2 and 10.1–10.2.
- SAP describes all-randomized efficacy analysis and exposed safety analysis, allowances for an interim missed visit, missing-as-failure rules and tipping-point sensitivity analyses. These rules require reconciliation with the reported implementation. Sources: sap-v1, primary-report; SAP4.1.1,6.5,10.1.2.1; paper Statistical Analysis.
- The paper names Hochberg control, but its reference 23 concerns false-discovery-rate methodology. The SAP specifies familywise-error handling; the citation discrepancy is unresolved. Sources: primary-report, sap-v1; paper Statistical Analysis and reference23; SAP10.1.1.
- The recorded primary rule uses one-sided 0.025 when both primary P values are <=0.025; otherwise the favorable comparison must be <=0.0125. Secondary alpha is conditional: 0.025 if both primaries pass, or 0.0125 for the corresponding secondary if only one passes. The third secondary requires both preceding secondaries to pass. No trial P values were transformed or re-tested here. Sources: sap-v1; SAP section10.1.1, PDF pages29–30; mathematical symbols visually checked against retained original.

Supporting reasons:
- The earlier protocol records key primary multiplicity concepts; the collected SAP provides detailed alpha/missing-data rules.
- The embedded signing claim narrows the documented timeline without authenticating it.

Contradictions/questions:
- Protocol v3 reference versus collected v4; paper FDR reference versus SAP familywise-error specification.
- No original earlier SAP/version log, effective-approval confirmation, actual lock or unblinding timestamp is available.

Risks and limitations:
- Embedded certificate dates and protocol intentions are not independent proof of chronology.
- OCR/embedded-font artifacts require visual checking of mathematical symbols; no p-value conversion or significance certification was calculated.

Missing information:
- Earlier SAP drafts/final versions, tracked changes and prespecification/approval history
- Actual database-lock, first unblinded access and analysis-population approval timestamps
- Implemented statistical code/outputs, multiplicity hierarchy and sensitivity analyses; lawful CSR access if available
- Owner source/version reconciliation and explicit owner self-review decision; no outside verification required.

Owner check questions:
- Validate the certificate and distinguish signing completion from effective approval.
- Reconcile protocolv3/v4, all SAP versions, missing-data allowances and any data-driven amendments.
- Confirm the implemented familywise-error procedure and alpha propagation; resolve the paper reference discrepancy.

Remaining evidence issues:
- Earlier protocol/SAP versions and executed chronology remain incomplete.
- Owner acceptance has not been recorded; research can proceed without external verification.

Readiness: READY_FOR_OWNER_RESEARCH_WITH_UNRESOLVED_EVIDENCE.

| Gate | Passed |
|---|---|
| CODE_IMPLEMENTED | True |
| TESTS_PASSED | True |
| ORIGINAL_EVIDENCE_COLLECTED | True |
| OWNER_REVIEW_COMPLETED | False |

## Level 6 — Endpoint clinical relevance

Continuous abstinence is directly relevant to smoking behavior. Clinical importance, durability, tolerability, generalizability and comparative effectiveness still require owner indication-specific research; no mortality or cardiovascular benefit is inferred.

- Primary outcomes concern biochemically verified continuous smoking abstinence during the final four treatment weeks. Week-24 follow-up and later clinical disease outcomes are separate questions. Sources: protocol-v4, sap-v1, primary-report; protocol16.2; SAP4.1; paper Methods/Table2.
- The report includes a selected adult smoking population receiving behavioral support and excludes several psychiatric/cardiovascular/substance-use groups; safety follow-up is limited. Sources: primary-report, protocol-v4; paper Eligibility and Limitations; protocol inclusion/exclusion.

Supporting reasons:
- Abstinence definitions, biochemical threshold and follow-up duration are available for specialist inspection.

Contradictions/questions:
- Treatment-period response and later abstinence differ; they cannot be presented as durable disease benefit.

Risks and limitations:
- No head-to-head comparator or long-term morbidity endpoint; selected population limits transferability.

Missing information:
- Independent disease-specific endpoint/benefit-risk assessment
- Longer-term and excluded-population evidence where available; no assumption it is required to have been collected at this phase
- Owner source/version reconciliation and explicit owner self-review decision; no outside verification required.

Owner check questions:
- Are the abstinence definitions and missing-visit rules clinically interpretable?
- What benefit-risk conclusions are justified for this exact population and duration, and where should reviewers abstain?

Remaining evidence issues:
- Earlier protocol/SAP versions and executed chronology remain incomplete.
- Owner acceptance has not been recorded; research can proceed without external verification.

Readiness: READY_FOR_OWNER_RESEARCH_WITH_UNRESOLVED_EVIDENCE.

| Gate | Passed |
|---|---|
| CODE_IMPLEMENTED | True |
| TESTS_PASSED | True |
| ORIGINAL_EVIDENCE_COLLECTED | True |
| OWNER_REVIEW_COMPLETED | False |

## Owner self-review checklist

- Owner checks exact original sources, study identity, phase, dates, versions and cutoff; software checks support research without outside attestation.
- Owner compares efficacy, harms, populations, endpoints, statistical methods and competing explanations using the collected sources.
- Owner explicitly records acceptance with limitations, need for evidence or rejection through the active owner workflow; no owner decision has been recorded by this dossier.
- Retain old revisions and known outcome exposure; corrections create new source-bound revisions. No invented external certification or uncalibrated FDA probability.

## Original-source checks

- Exact NCT/study code, phase/status, population and frozen company/application relationship.
- Original URL, document SHA-256, retrieval/cutoff, source date/version and amendment history; a hash is not proof of ownership.
- SAP reference-version mismatch, embedded certificate claim, actual lock/unblinding, missing documents and contradictory findings. Unknown facts stay unresolved, but do not require an outside person for owner research.

# First genuine review candidate: ORCA-2, NCT04576949

PRELIMINARY CURRENT-SOURCE RESEARCH — NOT AUTHENTICATED OR ADJUDICATED.

This candidate has a collected registry packet, original registered protocol and SAP, posted results, indexed primary publication and public full text. It is selected for document availability, not a numerical ranking, an approval forecast or scientific signoff. The complete per-level worksheets and source digests are in `focus-source-research-20261114.json`. All material is outcome-exposed current research; do not use it in a blind historical prediction.

Company: Achieve Life Sciences (ACHV). Registry study identifier: ACH-CYT-03 (ORCA-2). Registry-listed phase: Phase 3; status: COMPLETED. Population: adult daily cigarette smokers intending to quit. Phase, identity and population have not been independently verified.

| Level | Collected observations and preliminary interpretation | Required independent work |
|---|---|---|
| 1 — Provenance | Registry packet plus publicly registered protocol v4.0 dated 2021-03-08 and SAP v1.0 dated 2022-03-25 are retained outside Git with SHA-256 receipts. Hash agreement supports byte consistency only. | Authorized verifier compares original source ownership, study code, NCT association, version history and dates, then supplies genuine signed attestation through approved infrastructure. |
| 2 — Identity/phase | Registry names NCT04576949, ACH-CYT-03, Phase 3, completed; the paper reports adult smokers receiving behavioral support. | Reconcile registry, protocol, report population and actual application cycle. Existing application mapping remains provisional. |
| 3 — Efficacy | The 2023-07-11 report describes 810 randomized adults. Reported continuous abstinence for the 12-week regimen was 32.6% versus 7.0% during weeks 9–12 and 21.1% versus 4.8% through week 24. These are reported research facts, not independently verified estimates. | Reconcile registry tables, treatment groups, denominators, confidence intervals, safety, missing follow-up and longer-term durability. Do not infer an FDA decision. |
| 4 — Design | The report describes randomized, double-blind placebo comparison with behavioral support and two treatment durations. A protocol is collected; actual conduct and amendment completeness remain unverified. | Review allocation concealment, masking, adherence, eligibility, attrition, amendments and generalizability beyond motivated adult smokers. |
| 5 — Statistics | SAP text describes ITT analysis and multiplicity handling with Hochberg; sizing discussion also mentions Bonferroni. This is a methods observation, not evidence of inconsistency or adequacy. | Verify the exact primary family, procedure, sidedness, estimands, imputation and secondary hierarchy against results. Registry primary completion is 2021-12-23; collected SAP is dated 2022-03-25. Obtain database-lock/unblinding records and prior SAP versions. Dates alone do not prove post-hoc analysis or misconduct. |
| 6 — Medical relevance | Continuous biochemically verified abstinence concerns smoking behavior directly; persistence through 24 weeks is distinct from long-term disease outcomes. | A qualified reviewer must assess clinical importance, generalizability, tolerability, durability and appropriate disease-specific standards; no mortality or cardiovascular benefit is established here. |

Sources:

- Registry: https://clinicaltrials.gov/api/v2/studies/NCT04576949 — saved posted version 2026-01-15, retrieved 2026-11-14.
- Protocol: https://cdn.clinicaltrials.gov/large-docs/49/NCT04576949/Prot_000.pdf — title-page date/version unreviewed.
- SAP: https://cdn.clinicaltrials.gov/large-docs/49/NCT04576949/SAP_001.pdf — title-page date/version unreviewed.
- Journal record: https://pubmed.ncbi.nlm.nih.gov/37432430/ — published 2023-07-11; public full-text XML retrieved through Europe PMC, PMID binding checked. Journal indexing is not independent verification of the study report.

No actual independent reviewer has signed this case. No source is independently authenticated. No assessment is complete.

The shortest path to a real assessment is to resolve A02–A04/A12 with a real identity administrator, source authority and five qualified, separately identified people, while approving A01/A05–A11 infrastructure and policy. After real-token qualification and isolated access/recovery acceptance, authorize the specific release under A14. Authenticate this frozen source package first, then clinician review, independent challenge and separate final adjudication. Resolve the SAP timing question before statistical adjudication. A13 application-cycle verification remains separately required for any application-level claim.


## Continued Level 5 investigation — original-source statistical chronology

**Research-only update, November 14, 2026. NOT independent scientific adjudication.**
This chronology distinguishes *document date*, *registry milestone*, *method's
appearance in earlier protocol text*, *final analysis-plan approval* and
*database lock/unblinding*. These are distinct facts; matching one does not
prove another. The guarded, machine-readable event ledger is
`orca2-statistical-chronology-20261114.json`, with the read-only evaluator
`scripts/medical/level16_orca2_statistical_timeline.py`.

| Dated item | Original source and locator | Bounded research finding |
|---|---|---|
| March 8, 2021 | [Protocol v4.0](https://cdn.clinicaltrials.gov/large-docs/49/NCT04576949/Prot_000.pdf), printed page 68, section 16.1 | Before the registry's recorded primary-completion date, this protocol version already specifies the Hochberg approach for the two primary comparisons and the one-sided overall type-I error rate of 0.025. |
| December 23, 2021 | [ClinicalTrials.gov NCT04576949](https://clinicaltrials.gov/study/NCT04576949), primary-completion field | Primary completion is a registry milestone, **not** proof of database lock, analysis-plan finalization or treatment-code unblinding. |
| March 25, 2022 | [Registered SAP v1.0](https://cdn.clinicaltrials.gov/large-docs/49/NCT04576949/SAP_001.pdf), printed pages 9, 29 and 42, sections 2.2, 10.1.1 and 13 | The later SAP explains that Bonferroni was used for sample-size simulations, while Hochberg handles primary outcome multiplicity. This is not by itself a Bonferroni-vs-Hochberg inconsistency. The SAP states there are no planned-analysis changes relative to protocol, but that statement itself has not been independently verified against full amendments and audit trails. |
| July 11, 2023 | [Published JAMA trial report](https://pmc.ncbi.nlm.nih.gov/articles/PMC10336611/), Methods, Statistical Analysis | The publication reports use of Hochberg for primary multiplicity, without independently proving when the final SAP was locked or who had access to unblinded data. |

**What is now better supported:** the intended Hochberg primary testing
procedure appears in the dated March 2021 protocol, preceding the registry's
December 2021 primary-completion milestone. The March 2022 SAP is not the
earliest cited public document containing that method. The Bonferroni
calculation in the later SAP concerns simulated sample-size/power assumptions,
not an alternative verified primary hypothesis-testing decision.

**What is still unresolved:** actual database-lock timestamp, treatment-code
unblinding date, whether all analyses were finalized before unblinding,
effective/signed SAP version history and revisions, full original protocol
amendment lineage, clinical-study-report change log, and an independent
biostatistician's familywise/error-control and analysis reconciliation.
The dated public documents do **not** establish a post-hoc change,
statistical misconduct, or complete statistical adequacy.

Every linked original remains source material requiring independent provenance
authentication. The research is current/outcome-exposed: it may inform
preliminary clinical research but is **not** a blind historical prediction,
FDA outcome judgment, numerical score or independently signed assessment.

To validate the source chronology's integrity without pretending to complete
a review, run:

```powershell
python -m unittest discover -s tests -p "test_level16_orca2_statistical_timeline.py" -v
python scripts/medical/level16_orca2_statistical_timeline.py
```

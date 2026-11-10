# MAIN Revision 71 — Five exact-NCT published pivotal source findings and 40 unsigned review gates

**November 9, 2026 Pacific time.** Draft development [PR #965](https://github.com/pdufa/pdufa-command-center/pull/965), branch `feature/medical-stage4-verified-method-matrix-20261108`. This is **research-source evidence intake**, not a signed professional clinical adjudication, FDA application decision, approval probability, time-frozen backtest or production release.

## Source provenance and implementation

- Parent original immutable [R70 11-article NLM PubMed XML research #42729546458](https://github.com/pdufa/pdufa-command-center/actions/runs/42729546458), with SHA-256 `03434b975e511b2d603227bab3e25768dbcc3a0e7b412d479d9afbd100cd2577`. Original raw XML SHA-256 `2aa5fac13c7741d7ed2d9b1c2d91101978661150c87324b566b88f75994e394b`.
- [R70 article role original XML parity #42730604681](https://github.com/pdufa/pdufa-command-center/actions/runs/42730604681) confirmed five provisional main reports and six other related, protocol, Phase 2 or background citations. The five below each map to exactly one original public NLM PMID, DOI, and original NCT.
- `new-platform/frontend/data/focus-r71-five-main-publication-source-review.json`: dated selected original journal and registry evidence crosswalk, DOI/journal source links, journal-reported endpoints and limitations, analysis populations, safety and trial-specific follow-up tasks.
- `new-platform/frontend/lib/focus-r71-pivotal-evidence-intake.ts`: fail-closed cross-reference to the original R70 NLM/PMID identity, source-only R68/69/70 scope, and five times eight unscored research domain positions.
- `new-platform/backend/scripts/verify_r71_original_publication_source_intake.py`: pinned NLM source SHA256, PMID, DOI, exact NCT, article dates, and original raw-XML abstract numeric-literal checks for the **authors' published reported effect**. Passing this check is **source attribution, not independent statistical reanalysis or clinical validation**.
- `new-platform/frontend/app/predictions/evidence-gaps/ScientificOriginalsIntakeR71.tsx` and its CSS. Per-NCT source-only panel appears within existing R69/R70 PubMed publication expansion and retains 29 unique FOCUS trials / 23 provisional application group memberships.
- `new-platform/frontend/tests/focus-r71-pivotal-evidence-intake.test.cjs`, `new-platform/frontend/scripts/verify-r71-five-source-review-browser.cjs`, `.github/workflows/main-r71-pivotal-source-sap-intake.yml`.

## Five unique main-paper candidates — journal reported, NOT independently validated

| Original exact NCT | Publication | Authors' reported primary outcome | Evidence access |
| --- | --- | --- | --- |
| [NCT05126758](https://pubmed.ncbi.nlm.nih.gov/42526472/) | HOPE-3, Lancet, July 29 2026, PMID 42526472 | PUL2.0 percentage-change difference **4.55%** (95% CI 0.47 to 8.63; p=0.029), randomized 54 vs 52 | Source PubMed abstract inspected; original prospectively signed protocol/SAP and full paper not independently adjudicated |
| [NCT05662241](https://www.nejm.org/doi/full/10.1056/NEJMoa2601337) | INDIGO, NEJM, June 2 2026, PMID 42233621 | Time to first qualifying disease flare, reported HR **0.44** (95% CI 0.28 to 0.71; p<0.001); 97 vs 97 | Publisher article/abstract and protocol+supplement listing found; historical SAP chronology, multiplicity and safety require independent review |
| [NCT06081894](https://www.nejm.org/doi/full/10.1056/NEJMoa2603021) | ACACIA-HCM, NEJM, August 28 2026, PMID 42663312 | Dual primary peak VO2 difference **+0.67 mL/kg/min** (p=0.003), KCCQ-CSS **+3.0** (p=0.02); randomized 258 vs 259 | Publisher article/abstract plus protocol+supplement listing found; dual-primary gate, clinical relevance, LVEF reduction and safety require independent review |
| [NCT06153693](https://pmc.ncbi.nlm.nih.gov/articles/PMC12210145/) | Launch-HTN, JAMA, online June 30 2025, PMID 40587141 | Week-6 office systolic BP difference **−9.1 mmHg** (95% CI −13.3 to −4.9; p<0.001), 1083 randomized overall | Open full PMC journal article inspected; JAMA **Supplement 1 extracted text** reviewed. Publisher lists protocol 2.1, 3.0, 3.1 and SAP amendments/windowing/imputation supplements. **Version/lock chronology NOT independently adjudicated** |
| [NCT06343779](https://pubmed.ncbi.nlm.nih.gov/42849489/) | RAPIDe-3, Lancet, online October 8 2026, PMID 42849489 | Median symptom-relief onset **1.28 h** versus more than **12 h** placebo (p<0.0001); 134 randomized / 88 paired primary analysis | PubMed and indexed publisher abstract inspected; no original signed SAP or full clinical reviewer signoff |

Specific safety follow-ups:
- HOPE-3: original safety table/denominators and study quality/inspection evidence must be reconciled to clinical decisions; publication's qualitative safety summary is **not** independently accepted.
- INDIGO: journal reports serious adverse events **10.3%** versus **18.6%**, needing risk/exposure/relatedness reconciliation.
- ACACIA-HCM: journal reports LVEF below 50% in **10.5%** versus **0.8%**, and serious adverse events **20.2%** versus **14.7%**; do not infer positive regulatory risk-benefit from small p-values.
- Launch-HTN: reported hyperkalemia, hyponatremia, eGFR adverse event signals need dose and exposure adjustment. JAMA article and Supplement 1 refer to treatment-policy estimand, **1000 imputations**, MAR and MNAR assumptions, sensitivity approaches and multiplicity graph; exact dated preunblinding SAP reconciliation is outstanding.
- RAPIDe-3: separate randomized **participants**, treated **attacks**, and **88 paired participants** in endpoint and safety denominators.

## Genuine science gates

Each of the five trial panels has **eight expandable domain requirements**: primary endpoint; estimand/analysis population; statistical model; multiplicity; missing data/intercurrent events; sensitivity; safety; and source versions/chronology. **40/40 remain unscored pending independently signed assessment**; the previously established 232 domain positions in the broader original 29-trial project are not marked complete.

Every report is dated and remains subject to source-publication vs retrospective prediction-origin leak checks. A journal-reported p-value does not prove a prospectively locked primary hypothesis, a favorable FDA efficacy finding, a properly applied missing-data model, clinical meaningfulness, correct safety denominator, or FDA application acceptance. No time-frozen historical FDA outcomes were accessed in Revision 71.

**Original signed preunblinding SAP version checks: 0. Independently qualified scientific reviewers signed: 0. Independently validated prospective FDA outcome forecasts: 0/23. Historical accuracy: unavailable. Official future approval/CRL/delay: ABSTAIN.** Research only; no production or model-training writes.

## Next

Independent original protocol/SAP version comparison and amendment chronology, source-complete supplement/CSR efficacy and safety reconciliation, and separate authorized study adjudication. Preserve both adverse and favorable original data, original receipt and publication dates. Do not release numerical FDA probability or claim 100% predictive accuracy without independent prospective/time-frozen validation.

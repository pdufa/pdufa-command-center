# Sinovac phase-first company batch — 6 November 2026

Sinovac (SVA) is third by trial prevalence in the existing research census: Alkermes34, Axsome28, Sinovac27. All27 exact NCTs were refreshed from the official registry; all individually list Phase3. Seventeen are completed and ten are ongoing/not-yet-recruiting. The census is not an actionable investment shortlist: the documented trading halt and absent verified USFDA application linkage remain explicit exclusions.

## Results

| Measurement | Result |
|---|---:|
| Companies reviewed | 1 |
| Exact trial registry documents reviewed | 27 |
| Other documents reviewed | 9: four original protocol/SAP PDFs, one publication abstract, three SEC documents, one manufacturer IR page |
| Phase-specific documentary facts linked | 14 across3 trials, including qualified program-level prior support |
| New existing Q01–Q30 slots filled | 9 across2 trials |
| Phase-first available items | 271 |
| Phase-first missing expected items | 358 |
| Pending items | 236 |
| Not yet expected items | 80 |
| Not applicable items | 27 |
| Conflicting items | 0 |
| Phase-first requirement slots | 972 =27×36 |
| Five-metric coverage | 0/5 for every trial; no accepted benchmark grades |
| New RAAS scores or FDA forecasts | 0 |
| New USFDA/PDUFA application links | 0; cumulative existing platform links28 trials/15 programs |
| Historical primary verdicts preserved | 14:12 met,2 nonbinary |
| New primary verdicts | 0 |

The14 checklist records and nine legacy question records overlap scientifically; they are not23 independent new scientific findings. Exact sources, dates, document checksums and question mappings are in `sinovacPhaseFirstEvidence20261106.json`. The other14 historical verdicts are reused rather than re-created or counted as newly recovered outcomes.

## Source findings

- **NCT05850364 / PRO-sIPV-4001:** original protocol and SAP retrieved from the registry CDN. SAP section4.3 specifies80% overall power,93.3% per-serotype power, one-sided alpha0.025 and a−10 percentage-point NI margin. Section7.9 specifies LOCF for missing FAS immunogenicity and no imputation of safety values. Section7.11 requires joint noninferiority across all three poliovirus serotypes. This is a documented plan, not proof that the assumptions or methods are adequate.
- **NCT06049927 / PRO-QINF-3005:** original protocol and SAP document80% overall power, SCR/GMT joint requirements, MAR multiple imputation with Rubin pooling, and a fixed-sequence hierarchy. These findings are not attributed to the distinct PRO-QINF-3003 trial.
- **NCT05850364 publication:** the exact NCT is stated in the official PubMed abstract, retrieved through NCBI efetch after publisher full text returned403. Trial-specific seroconversion and7-day AR rates are recorded. AR rates are not SAE rates. The all-serotype adjusted NI verdict remains unadjudicated; no PASS, FAIL or scientific grade is manufactured from the abstract.
- **HFMD4 prior support:** the June5 SEC release provides qualitative prior Phase2 safety/immunogenicity rationale. It is explicitly program-level support, has moderate confidence, lacks an independently matched Phase2 NCT and is not a result of current Phase3 trial NCT07611513.
- **China regulatory milestones:** the August17 SEC release reports NMPA PVRV-SF approval and HFMD2 application acceptance. These remain company/program context and are not converted into USFDA milestones or PDUFA dates.

## Remaining difficult records

1. **NCT05245552 / PRO-QINF-3003:** completed; no exact-trial final readout found using the NCT, protocol, manufacturer and publication avenues reviewed. The other influenza study's findings cannot fill this gap.
2. **NCT07211152 / PRO-QINF-3006:** completed pregnant-women study; no exact-NCT final public readout located in the reviewed sources.
3. **NCT05850364:** results and SAP are available, but the adjusted joint NI decision is unresolved. Full publisher text was inaccessible; no access controls were bypassed.
4. **NCT06734832:** recruiting in the registry. Qualitative issuer HFMD2 program updates do not supply a numerical exact-trial final outcome.

Missing means a gap in this reviewed source set, not proven public nonavailability. Most remaining gaps concern preclinical rationale, exact prior Phase1 findings, dose rationale, detailed earlier efficacy/safety and study-specific power. Pending ongoing results are excluded from the completeness denominator and never scored zero.

## Existing platform integration

Nine source facts were added to unoccupied exact-NCT/question slots in `phase3CompanyWebsiteEvidence20261105.json`: Q01×1, Q03×1, Q13×2, Q14×2, Q15×2 and Q29×1; all other Q01–Q30 increments are zero. Every record is `DOCUMENTED_SOURCE_FACT`, with no numerical score or prediction. The existing data-driven30-question audit and190-column export consume them automatically.

The legacy audit changes from13,053 to13,044 unscored slots and from9,546 to9,555 source facts. It retains61 predicted slots,200 observed slots, four trials with historical numerical predictions, and100 endpoint-adjudicated trials (72 met,17 not met,11 nonbinary). The separate phase-first358 missing items are not directly comparable with the legacy30-question missing-slot count.

The existing company research queue now records27 exact identity matches, partial review status,30 question-status entries per trial and the specific unresolved readouts. The manufacturer search log retains the historical14 verdicts and adds this batch's source list, counts and hard-to-resolve flags.

The `/phase-first` selector now includes Sinovac, defaults to the next reviewed company, exposes its explicit research-only eligibility restriction, and preserves Alkermes/Axsome access. The original Sinovac documentary scorecard is retained as an earlier snapshot and links to the current view. The existing918 released history events remain unchanged;54 new scope-specific events are appended (27 Sinovac and27 refreshed census records), for972 events over856 unique identifiers. A second snapshot run adds zero events. No database schema/live writes, calibrated score changes or Pipeline admissions are made. GEM/GEM JR and Streamlit remain inactive.

## Validation and release

Sixteen focused phase-first tests cover the company order, exact phases, pending/missing treatment, protocol identity, source-only question facts, historical verdict preservation, trading exclusion, API budgets and immutable history prefix. All1,282 frontend tests, TypeScript and the production build passed. Targeted company-coverage tests also passed after updating the research queue. Local browser checks passed at desktop and393px phone widths, including source details, saved history, trading exclusion, all four company/census scopes and762 unique CSV records with190 fields per row. Production status is verified separately; this report does not itself claim a deployment.

Reproduce reports with `node scripts/export_phase_first_reports.cjs sinovac`. The Sinovac CSVs provide every trial's five-metric coverage, every requirement's missingness, and972 evidence classifications with provenance. Refresh registry evidence with `python scripts/collect_company_phase_first.py --ticker SVA --cache /tmp/sva-registry --output /tmp/sva-registry.json`.

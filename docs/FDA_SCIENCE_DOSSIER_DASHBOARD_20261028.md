# Six-case SCIENCE dossier and MAIN integration — October 28, 2026

Continues PR #522 from verified commit 70787eae and successful Actions run #33. No restart, merge or deployment. The existing 146-row prediction history is read to select six priority events; its rows and probabilities are unchanged.

## Scientific reconstruction increment

The packet now contains **22 source observations**, classified by the auditor as **13 pre-cutoff research observations from 10 distinct SEC filings**, seven outcome-only exclusions, one late exclusion and one printed-date quarantine. These are research observations, not independently completed scientific assessments or verified frozen prediction features.

New source-reported findings:

- **TNXP:** the [March 18, 2025 10-K](https://www.sec.gov/Archives/edgar/data/1430306/000199937125002786/tnxp-10k_123124.htm), admitted using its exact SEC filing index, contrasts positive RELIEF/RESILIENT with negative RALLY, identifies adverse-event discontinuations and a possibly related pancreatitis event, and describes regulatory bridging and manufacturing context. Within-program trial comparisons are not independent FDA decision precedents. Full statistical plans, patient-level consistency and safety adjudication remain outstanding.
- **UNCY:** the [June 25, 2024 clinical disclosure](https://www.sec.gov/Archives/edgar/data/1766140/000121390024055436/ea020843701ex99-1_unicycive.htm) separates enrolled, safety and evaluable populations, treatment-related versus all-event discontinuations, and the lack of an efficacy-directed concurrent comparison. The [FDA-hosted historical Fosrenol label](https://www.accessdata.fda.gov/drugsatfda_docs/label/2004/21468lbl.pdf) adds comparator context: its long-term comparative adverse-event discontinuation rate cannot be directly compared with UNI-OLC-201's maintenance treatment-related fraction. The label's original public availability and exact original action cycle are not independently adjudicated, so this context is not admitted as a frozen feature or training case.
- **VNDA:** exact SEC indexes establish availability of the [November 28 pending hold-review disclosure](https://www.sec.gov/Archives/edgar/data/1347178/000162828025054225/vnda8-k11282025exhibit991.htm) and [December 4 hold-removal update](https://www.sec.gov/Archives/edgar/data/1347178/000162828025055393/vnda8-k1242025exhibit991.htm). The later issuer-reported status supersedes pending review before the research cutoff. Hold removal is distinct from NDA approval and from safety at other exposure patterns.
- **NVAX, BCRX and CORT:** retain the prior cutoff-bound observations, indication/formulation boundaries and contrary-evidence notes. BCRX's May 14 source remains quarantined because filing-index availability is unverified. No late source was admitted to fill a gap.

UNCY's original FDA CRL extracted signature page directly records June 27, 2025, 04:49:06 PM, with timezone unspecified. First-page visual verification remains incomplete. Original FDA action-document content remains recorded for four cases; UNCY is partial and CORT has only its corrected letter. No FDA PDF bytes or hashes were retained. Six action-evidence records do not establish six independently adjudicated model-eligible review cycles.

## Working implementation

`research/fda_science_dossier.py` derives eight scientific layer matrices from the existing catalog's forty questions. Each question retains the exact candidate source references, required documents, uncertainties and excluded/quarantined evidence. Independent conclusions, scores and probabilities stay null. Historical matching requirements cover exact indication, population, design, endpoints, pathway, manufacturing, review cycle and program family; missing evidence remains unknown.

The existing twenty numbered investigation boundaries are preserved. **Individual semantic definitions for the twenty levels are absent from the existing catalog.** The adapter exposes that gap rather than inventing definitions or claiming completed investigation depths. All six dossiers remain at zero independently certified assessments out of forty and zero completed depths out of twenty.

The read-only research queue attaches these dossiers and original-versus-partial/corrected FDA document metadata. A deterministic generator publishes a dated snapshot for the existing dashboard's `/installation-audit` research section. Expandable case details show application/action/cutoff timelines, supporting/opposing factors, source classifications, document requirements, forty-question gaps and validation blockers. The validator withholds counts if identities, chronology or abstention boundaries fail. There are no new scanner, storage, source-download or trading operations. This is a dated research view, not a live source refresh or production installation claim.

## Verification and status

- Relevant Python research suite: **96 passed, 20 subtests passed**.
- Frontend: **396 tests passed, zero failed**; TypeScript type checking and the standard production build passed. Local process restrictions initially blocked the build; it passed using the managed environment network permission, without code or dependency changes. GitHub Actions results are recorded in PR #522 after push.
- Existing backend suite previously passed **994 tests with seven warnings** at the preceding milestone. Backend application code is unchanged in this increment; this is prior evidence, not a fresh backend run.
- The workflow now checks dossier regressions, snapshot drift, frontend tests, type checking and the standard build on this PR. No live schedules or deployment triggers are added.

**Independent historical backtests: 0.** None of the six recovered forecasts qualifies for defensible chronological out-of-sample validation: model and lock artifacts postdate the 2025 decisions. Original prediction timestamps, frozen features and independently checked training chronology remain missing. Accuracy, calibration, Brier score, uncertainty intervals and coverage are unmeasured; PASS/FAIL probabilities remain withheld. Code tests, issuer filings and a rendered dossier do not validate predictive performance.

Highest priorities remain original-document retention/availability and review-cycle adjudication, original protocols/SAPs and full efficacy/safety/CMC reconstruction, semantic investigation-depth definitions, independently adjudicated comparators, and a leakage-safe model-training/evaluation cohort. FDA shell downloads remain blocked by the managed allowlist; no bypass or network-policy change was attempted. CORT original CRL and UNCY first-page verification remain blocked. No production deployment or database-readiness verification was performed.

PIPELINE → GEM JR → GEM → WT restrictions, memberships, original FS/FA associations, production archives, scanners and schedules remain unchanged. No sheet writes, trades or orders were enabled.

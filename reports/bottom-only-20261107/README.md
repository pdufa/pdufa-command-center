# BOTTOM Phase 3 post-data evidence and clinical scoring — 2026-11-07

The user expanded the assignment from the saved 23-trial research cohort to **all 29 current canonical active trials**. There are 5 exact-NCT overlaps, hence 47 preserved research identities and 18 historical records outside the active view. No TOP/Pipeline records or membership were changed. The original 23 baseline rows, 190-cell observations, prior reviews and histories remain preserved.

## Current canonical active results

- 29/29 trials processed and source-reviewed; 128/145 clinical factors numerically graded.
- 15/29 trials have complete five-factor numerical scores, using the approved equal 20% weights. Partial grades never become a combined score.
- Research data: 0 fully populated, 29 partial, 0 wholly unavailable. Review coverage is not data completeness.
- Field-level evidence completion: 2262/3770 applicable fields (60.0%). Each record retains all 190 columns; 60 archived scoring/forecast cells per trial are excluded from this evidence denominator.
- Source-question completion: 469/870 (53.9%). A sourced question does not automatically support a numerical clinical grade.
- All 47 preserved registry identities and phases were checked; publication discovery covers all 47 without a trial or result cap. Issuer/SEC evidence is accepted under the existing source policy and identified separately from registry/journal evidence.
- The saved 23-trial cohort now has 98/115 grades and 14 complete clinical scores. Across all 47 identities there are 203/235 grades and 26 complete scores.
- The archived 30-metric framework is retained for history, not reactivated; no claim of completed 30-metric numerical scorecards is made.

## Active factor counts

|Factor|Numerical|Pending evidence/results|Blocked rule|
|---|---:|---:|---:|
|Actual Phase 3 efficacy|29|0|0|
|Clinical importance and patient benefit|27|2|0|
|Statistical reliability|26|3|0|
|Replication and durability|27|2|0|
|Safety and tolerability|19|10|0|

## Every remaining active grade

Missing grades retain null. NOT_REPORTED means the retrieved source does not disclose the required detail; MISSING_EVIDENCE identifies an unresolved source gap, including access limitations; PENDING identifies future follow-up. These are not negative trial outcomes.

|Exact NCT|Factor|State and blocker|
|---|---|---|
|NCT06445023|post-1-5|NOT_REPORTED: Retrieved Phase 3 issuer readout and 2026 Q3 SEC filing provide qualitative tolerability but no exact-study arm-level all-cause SAE and discontinuation tables. Do not substitute Phase 2 data.|
|NCT06455202|post-1-5|NOT_REPORTED: Retrieved Phase 3 issuer readout and 2026 Q3 SEC filing provide qualitative tolerability but no exact-study arm-level all-cause SAE and discontinuation tables. Do not substitute CSU1 or Phase 2 data.|
|NCT05811247|post-1-2|MISSING_EVIDENCE: LunAIRo retrieved registry results quantify AHI but not patient fatigue/function or QoL results. SynAIRgy fatigue results belong to another exact NCT and are not substituted.|
|NCT05059223|post-1-3|MISSING_EVIDENCE: SYMPHONY release gives primary p=0.018 and multiple secondary p-values but no effect CI, full multiplicity or missing-data sensitivity analysis. No default statistical grade.|
|NCT05244304|post-1-5|NOT_REPORTED: DRAGON issuer reports four treatment-related drug discontinuations but no exact arm-level complete serious-event and severity table or safety exposure denominators.|
|NCT05126758|post-1-5|MISSING_EVIDENCE: HOPE-3 indexed Lancet abstract says safety similar; open issuer release lacks full AE/SAE/discontinuation table. Indexed full text is subscription-only. Exact arm-level data needed; HOPE-2 cannot substitute.|
|NCT04871282|post-1-3|MISSING_EVIDENCE: Accessible SEC10-Q reports RINGSIDE HR0.16,p<0.0001 and pain SEs but no primary PFS CI, full SAP or missing-data sensitivities. Detailed issuer page and search index return interstitials.|
|NCT04871282|post-1-4|MISSING_EVIDENCE: RINGSIDE filing provides Week12pain and Week24tumor-volume changes but no longitudinal PFS/response-duration estimates or independent confirmatory study sufficient for durability grading.|
|NCT04871282|post-1-5|MISSING_EVIDENCE: Accessible SEC readout only says safety consistent with GSI therapies; detailed IR page is access-blocked. Exact PartB arm-level AE/SAE and discontinuations remain unestablished.|
|NCT06411379|post-1-5|NOT_REPORTED: VELA-1/2 publication contains POOLED safety559active/279placebo, including SAEs2.5%vs1.8%,discontinuations2.9%vs1.4% and candidiasis7.3%vs0.4%. Exact VELA-1 safety counts are not separately disclosed; pooled counts cannot become exact-trial rates.|
|NCT06411899|post-1-5|NOT_REPORTED: VELA-2 exact arm safety counts are not supplied; published safety is pooled across VELA-1/2. Preserve pooled candidiasis and withdrawal signal as program evidence, not an exact VELA-2 numerical grade.|
|NCT06153693|post-1-2|NOT_REPORTED: Launch-HTN reports6/12-week blood pressure lowering, not measured patient symptom/function, stroke or survival benefit. A risk-factor surrogate is not automatically a numerical demonstrated patient-benefit grade.|
|NCT06343779|post-1-5|MISSING_EVIDENCE: RAPIDe-3 abstract documents two fatigue events, no severe/serious treatment-related events and no AE withdrawals, but not complete all-cause arm/exposure safety table. Indexed full Lancet report is subscription-only; no assumption all SAEs are zero.|
|NCT06669754|post-1-3|NOT_REPORTED: CHAPTER-3 reports83%attack reduction,p<0.0001 and sequential secondary multiplicity control, but no primary effect CI, full missing-data sensitivity or arm-level counts in retrieved topline.|
|NCT06669754|post-1-5|NOT_REPORTED: CHAPTER-3 reports no treatment-related SAEs and one AE withdrawal per arm, but no complete all-cause AE/SAE and severity counts. Those are distinct from no-drug-related-SAE statement.|
|NCT02500381|post-1-5|NOT_REPORTED: ESSENCE source provides product warning language and failed functional endpoint, but no exact trial arm-level AE/SAE and withdrawal table. Labels for separate exon-skipping drugs are not pooled trial safety evidence.|
|NCT06331299|post-1-4|PENDING: UTOPIA registry posts Month3response only; duration-of-response outcomes are NOT_POSTED. Do not transfer24-month ENVISION durability from UGN-102 to UGN-103.|

All 32 unresolved factors across the 47 preserved identities are listed in `bottom-missing-clinical-factors.csv`; the active 17 are enumerated above and in `coverage.json.currentActive.blockers`. One historical rule blocker remains: NCT05453968 efficacy, because the PK-primary APeX-P study has no approved conversion from PK findings to a primary clinical efficacy grade. No numerical threshold was invented.

## Evidence, discrepancies and score provenance

Each reviewed numerical factor retains the grade, approved finding/benchmark, cited observation, source URL/date, rationale and uncertainty. Original facts are retained; registry revisions append source versions. Notable audited distinctions include Essential3's -4.3 within-arm versus -2.6 placebo-adjusted TETRAS difference, failed VELA-2 prespecified composite versus positive TP-only endpoint, failed ESSENCE primary endpoint despite exploratory analyses, LunAIRo versus SynAIRgy adverse-event definitions, and UTOPIA/UGN-103 versus ENVISION/UGN-102 durability. Pooled VELA safety is recorded as program evidence without assigning exact-trial safety grades.

`source-retrieval-audit.json` preserves prior and new retrieval receipts; `publication-discovery-ledger.json` records paginated searches and article metadata. A search hit is a lead, not verified trial evidence. HTTP errors/interstitials are not accepted clinical sources. Government registry snapshots are preserved locally in `sources/`; full publisher/issuer captures are not redistributed. Source citations and exact observations remain in the canonical fact and review ledgers.

## Implementation and repeatability

- Extended the existing baseline/190-field matrices and reviewed-fact/review/history ledgers; no parallel spreadsheet or replacement score engine.
- Existing active post-data page/API uses only canonical active exact NCTs; horizontal five-factor expansion, sources and shared cross-stage history remain attached to trial identity.
- Registry backfill uses exact identity, phase checks, content-addressed snapshots and semantic clinical hashes. An actual clinical source change withholds stale grades pending review; administrative updates do not erase scores. Source harvesting never auto-invents subjective grades.
- Existing active Sheets workflow retains its triggers and schedule, and now harvests all retained/active evidence, recalculates the approved clinical scores and synchronizes existing exact-NCT cells through the established integration. No cancelled workflow was re-enabled.
- Canonical Sheets writes touch M/Q/R/S only, preserve prior values and notes, and leave validated overall probabilities and archived /30 cells unchanged. Active 29-trial sync receipt verifies 94 further cells and all 843 readback cells; the first five overlaps were synchronized earlier in 18 cells.

See `verification.json` for test/build/browser/deployment evidence and `sheets-active29-sync-receipt.json` for canonical sheet parity. Live verification and release references are recorded only after successful checks.

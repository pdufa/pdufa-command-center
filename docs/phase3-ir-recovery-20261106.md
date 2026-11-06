# Phase 3 IR recovery — 2026-11-06, Ardelyx batch

Started from main `a7cc2e0c8e4131c3f1885ab00e7a057b70d5c0f1`. Live audit matched every supplied baseline count. Existing roster and scoring history are preserved; evidence is overlaid by exact NCT in the master UI and export.

One company searched; all 10 Ardelyx census NCTs screened by identifiers and official registry identity. Seven trials enriched. Five official IR releases and two SEC 8-K disclosures reviewed; additional FDA labels, approval package, publications and correction notices cross-checked. This is partial issuer research, not exhaustion of the 762-trial queue.

Four new primary successes (T3MPO-1, T3MPO-2, PHREEDOM, AMPLIFY); zero failures; one descriptive/nonbinary safety extension (T3MPO-3). ACCEL enrollment and expected readout are source facts, not predictions or PDUFA dates. Five new trial/application links, cumulative 13 links across five programs. No new PDUFA goal dates. Zero numerical predictions added; four trials retain 61 existing prediction slots.

48 new question-specific records: 45 documentary facts and three items requiring interpretation. Some replace existing generic registry facts, so only 20 previously empty slots gain facts. Source-fact and observed-outcome columns are distinct. No information is labeled NOT_PUBLICLY_DISCLOSED merely because searches or access attempts failed.

| Question | Documented facts added | Interpretation pending | Remaining research | Numerical slots | Observed slots |
|---|---:|---:|---:|---:|---:|
| Q01 | 5 | 0 | 404 | 4 | 48 |
| Q02 | 0 | 0 | 747 | 4 | 0 |
| Q03 | 5 | 0 | 396 | 4 | 0 |
| Q04 | 0 | 0 | 758 | 4 | 0 |
| Q05 | 1 | 0 | 757 | 4 | 0 |
| Q06 | 2 | 0 | 756 | 4 | 0 |
| Q07 | 0 | 0 | 6 | 1 | 0 |
| Q08 | 0 | 0 | 11 | 1 | 0 |
| Q09 | 0 | 0 | 1 | 1 | 0 |
| Q10 | 0 | 0 | 1 | 1 | 0 |
| Q11 | 0 | 0 | 160 | 1 | 0 |
| Q12 | 1 | 0 | 1 | 1 | 0 |
| Q13 | 1 | 0 | 760 | 1 | 0 |
| Q14 | 1 | 0 | 760 | 1 | 0 |
| Q15 | 0 | 3 | 761 | 1 | 0 |
| Q16 | 0 | 0 | 758 | 4 | 0 |
| Q17 | 3 | 0 | 145 | 4 | 0 |
| Q18 | 1 | 0 | 684 | 3 | 0 |
| Q19 | 0 | 0 | 759 | 3 | 0 |
| Q20 | 0 | 0 | 761 | 1 | 0 |
| Q21 | 2 | 0 | 759 | 1 | 0 |
| Q22 | 1 | 0 | 492 | 1 | 0 |
| Q23 | 3 | 0 | 455 | 1 | 0 |
| Q24 | 5 | 0 | 485 | 4 | 0 |
| Q25 | 0 | 0 | 0 | 1 | 0 |
| Q26 | 1 | 0 | 760 | 1 | 0 |
| Q27 | 0 | 0 | 405 | 1 | 0 |
| Q28 | 2 | 0 | 759 | 1 | 0 |
| Q29 | 6 | 0 | 406 | 1 | 48 |
| Q30 | 5 | 0 | 748 | 1 | 0 |

Remaining unscored/research slots: **14,655**, versus **14,675** baseline. Endpoint totals: **39 met / 6 not met / 3 nonbinary / 714 unadjudicated**. FDA application unverified: **749**; PDUFA goal unverified: **754**.

## Provenance and limits

- Exact trial/protocol crosswalks and HTTP checks are in `phase3IrSourceValidation20261106.json`; all 10 issuer registry identities were retrieved. HTTP success alone is not scientific adjudication.
- IR T3MPO-2 and PHREEDOM pages returned 403 in the web tool; official SEC 8-K originals supplied the results.
- Later publication corrections require full-text interpretation. Original source-dated methods remain explicitly historical and flagged; no numerical robustness grade is inferred.
- T3MPO-3 issuer cohort (240) differs from the later publication population (312). They are not combined or substituted.
- PHREEDOM primary estimate uses an enriched efficacy set, not the full randomized population.
- T3MPO-1 secondary CSBM failure (p=0.27) survives its primary success.
- ACCEL does not inherit adult IBS-C approval. No pooled safety rates are imported as individual-trial findings.
- The saved queue enumerates all 762 NCTs. The other issuers are unreviewed or explicitly marked as legacy-evidence coverage; no full search is claimed.

## Verification

- Actual route execution validates 763 CSV lines, exact 190 fields on every line, all 762 unique NCTs, all 30 question partitions and audit/CSV parity.
- TypeScript and production build passed locally with the network-enabled execution setting.
- Initial restricted test run: 205/208 test files passed, three existing subprocess tests hit EPERM. Network-enabled rerun and GitHub checks are required before merge.
- Publication and clinical-source validation is distinct from software testing. Production verification follows merge; this report does not preclaim deployment.

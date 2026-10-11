# PRE PHASE 3 — First dated, source-reviewed scoring pilot

**Trial:** TRVI / Trevi Therapeutics, Haduvio (oral nalbuphine ER / NAL ER), OCEAN-1, **NCT07671911**.  
**Cutoff:** October 10, 2026, America/Los_Angeles.  
**Research rubric:** 80/100 (22 Phase 2 efficacy, 25 Phase 3 design, 10 safety, 12 regulatory alignment, 7 execution, 4 source quality).  
**Review scope:** First-pass, source-cited desk research of primary study, trial registry, company news archive and dated corporate releases. **Not independently audited by a clinical specialist, not a calibrated Phase 3 success probability, and not a trading signal.**

## Exact Phase 2 evidence / primary analysis

The peer-reviewed [CORAL randomized Phase 2b study](https://jamanetwork.com/journals/jama/fullarticle/2844186), published January 22, 2026, explicitly identifies **NCT05964335**, matching Trevi's nalbuphine ER program in IPF-associated chronic cough. It enrolled 165 patients, investigated 27/54/108 mg twice-daily doses against placebo, and prespecified relative change in objective 24-hour cough frequency at week 6. The primary comparison of 27 mg with placebo was **p=0.008** in the JAMA article, while 54 mg and 108 mg comparisons were **p<0.001**. All doses improved objectively measured cough frequency; primary-endpoint interpretation is YES for these reported comparisons, not proof of Phase 3 success.

The ClinicalTrials.gov primary-analysis collector separately displays numerical statistical-analysis p entries including 0.0028 and rounded 0.0000 for NCT05964335. These are registry-reported comparison results that may differ in analysis method, precision or contrast from the journal article. **Do not substitute the registry p=0.0028 for the peer-reviewed p=0.008, nor treat 0.0000 as a literal zero.** The strict pilot uses the primary journal comparator p=0.008 with its published January 22 date. The original registry values remain in their separate provenance columns.

Clinical relevance and limitations: 54 mg twice daily reduced mean objective cough frequency 53.4% from baseline compared with 16.9% with placebo at week 6. The study was short, the MMRM analysis depended on missing-at-random assumptions, and tolerability issues included nausea, vomiting, constipation and dizziness. None of this independently proves the longer-term OCEAN-1 outcome.

## Exact Phase 3 study and source-date check

[OCEAN-1 registry](https://clinicaltrials.gov/study/NCT07671911) (latest saved source revision 2026-09-14; saved verified check 2026-10-10) records an active randomized, double-masked, placebo-controlled trial (approximately 306 participants) with an objective primary cough endpoint at week 26. The recorded source is strictly for NCT07671911, **not** OCEAN-2.

Trevi's [March 9, 2026 End-of-Phase-2 announcement](https://ir.trevitherapeutics.com/news-releases/news-release-details/trevi-therapeutics-announces-completion-end-phase-2-meeting-0) reports FDA-program alignment for the two pivotal trials but also specifies final protocols were subject to FDA review. We **have not independently inspected FDA minutes**. Trevi's [August 6, 2026 quarterly release](https://ir.trevitherapeutics.com/news-releases/news-release-details/trevi-therapeutics-reports-second-quarter-2026-financial-results) says OCEAN-1 started Q2 2026, with **topline expected first half 2028**.

On **October 10, 2026** we reviewed the company's [dated press-release archive](https://ir.trevitherapeutics.com/news-events/press-releases), where the latest listed release was dated September 3, 2026, and the [issuer investor homepage](https://ir.trevitherapeutics.com/), still referencing the August 2026 corporate presentation. We found **no OCEAN-1 topline release in this issuer archive** on that review date. This supports the *narrow, source-scoped* `VERIFIED_UNRELEASED` status for the **October 10** assessment only; it is not a guarantee that no unpublished event or out-of-index disclosure exists. Results could appear later and invalidate the assertion. The strict scoring engine must suppress this 80/100 reviewed score on subsequent dates until the issuer/source check is explicitly refreshed.

## Outcome and next review

`data/phase3_pre_readout_evidence.csv` stores one exact-trial, dated 80/100 research rating with all six published domain sources, peer-reviewed Phase 2 primary p and the checked issuer archive. `pre_readout_score.assess` keeps **Phase 3 Success Probability % blank**. A dated pilot score is a product research assessment **not a medical or regulatory certification**. The contemporaneous clinical review gate is different from the POST PHASE 3 financing, stabilization, dilution and ENTRY READY gates.

**Key uncertainty still open:** independent clinical adjudication of the full protocol, dose-response and multiplicity, longer-duration safety, actual FDA feedback and any new issuer releases. This system does not impersonate such reviewers or imply that these checks are complete. Continuing source surveillance and rechecking on the new cutoff day remain necessary.

# MAIN Revision 39 — same-day 29-FOCUS / 23-application preliminary research delivery

**Research as-of:** 2026-11-09, with existing FOCUS roster last captured 2026-11-08. **Delivery:** #979, coordinated with #980 and Stage 4 draft #965. **Scope:** development branch only. No trial roster membership, underlying dossier, production engine, clinical reviewer grade or regulated-data infrastructure has been changed.

## Exactly what this first pass delivers

The canonical frontend roster \`p3PostDataActive.json\` has **29 unique NCT IDs**, reconciled against the **23 unique provisional application groups** in \`medical-intelligence-applications.ts\`. The corresponding backend snapshot paths \`focus_snapshot.json\` and \`focus_application_snapshot.json\` remain untouched. NCT02500381 supports **two** distinct Sarepta supplements; none of the 29 trials is erroneously counted as 29 independent applications.

The new \`focus-preliminary-application-research.ts\` creates a **dated, source-linked 23-group qualitative research workup** from the already authored application-specific specialist dossiers and exact application-specific questions. For each group: original source pointers and dates, selected clinical outcome evidence, selected adverse/contrary evidence, uncertain statistical/CMC/regulatory questions, supporting NCTs, requested application type/indication, source-reported (not guaranteed) target action date, separate review-delay/extension field and explicit missing evidence. It runs fail-closed on changed roster membership/count, unknown groups, missing seven-dimension clinical dossier, unsupported future source date, and unsupported "approved already" remapping.

| Preliminary research category | Number of application groups |
| --- | ---: |
| Favorable clinical evidence, **qualitative approval lean** (unvalidated) | 5 |
| Material efficacy concern, **qualitative CRL lean** (unvalidated) | 1 |
| **ABSTAIN**, due to inadequate application-specific verification | 16 |
| **Observed prior FDA approval**, not a future prediction | 1 |
| **Total** | **23** |

The five conditional research approval leans are \`cogt-gist\`, \`imnm-desmoid\`, \`phvs-ondemand\`, \`svra-molgramostim\` and \`zbio-obexelimab\`. The CRL-lean is \`capr-deramiocel\` due to the original FDA primary efficacy challenge and unresolved revised statistical methods. None is a clinical signoff, patient-level or full CMC adjudication, externally validated prediction, probability, or a statement of certain FDA outcome. All are substantially uncertain. This preliminary selection is frozen as source-code version \`MAIN_FOCUS_29_23_APP_RESEARCH_V1\` rather than being recomputed by an untracked model. Future revisions must preserve a commit-level history, not mutate past model performance or pretend the qualitative assessment was made at an earlier date.

The one completed prior FDA action, \`cytk-aficamten-ohcm\`, has FDA approval on **2025-12-19** for obstructive HCM ([FDA original product/trials snapshot](https://www.fda.gov/drugs/drug-trials-snapshots/drug-trials-snapshots-myqorzo)). FOCUS's recorded Nov 14 2026 action date must not be used as another future oHCM event. Its associated MAPLE NCT is additional supportive research, not automatically the SEQUOIA pivotal approval NCT. ACACIA (NCT06081894) concerns a separate *planned nonobstructive-HCM sNDA* and remains ABSTAIN.

**Critical independent source spot-checks (2026-11-09):**
- [Capricor August 24 extension statement](https://www.capricor.com/investors/news-events/press-releases/detail/354/capricor-therapeutics-announces-extension-of-pdufa-target) — November 22 target after 3-month amendment; the historical extension is observed, not a future delay forecast.
- [Savara April 15 extension statement](https://investors.savarapharma.com/news/news-details/2026/Savara-Announces-the-U-S--Food--Drug-Administration-FDA-Has-Extended-the-Review-Period-for-the-Molgramostim-Inhalation-Solution-Molgramostim-Biologics-License-Application-BLA-in-Autoimmune-Pulmonary-Alveolar-Proteinosis-Autoimmune-PAP/default.aspx) — November 22 target after major amendment, no named efficacy/safety/CMC concern in that communication; never infer absence of later concerns.
- [Cogent November 5 SEC disclosure](https://www.sec.gov/Archives/edgar/data/1622229/000119312526449926/cogt-ex99_1.htm) and [NDA acceptance plus PEAK analysis](https://investors.cogentbio.com/news-releases/news-release-details/cogent-biosciences-announces-fda-acceptance-new-drug-0) — November 30 GIST target; pivotal PFS HR 0.50 (95% CI 0.39–0.65), with clinically material grade 3+ hepatic laboratory imbalance requiring independent review.
- [Apnimed FDA acceptance](https://ir.apnimed.com/news-releases/news-release-details/apnimed-announces-fda-acceptance-new-drug-application-ad109) — February 28 2027, but AHI/treatment-discontinuation and symptom evidence require review; research ABSTAIN.
- [Immunome NDA acceptance](https://investors.immunome.com/immunome-announces-u-s-fda-acceptance-of-new-drug-application-for-varegacestat-for-the-treatment-of-adults-with-desmoid-tumors/) — April 28 2027, FDA status rechecked; source-linked RINGSIDE source dossier retained.
- [MoonLake November 4 SEC update](https://www.sec.gov/Archives/edgar/data/1821586/000182158626000013/moonlake-pressreleasexq320.htm) — BLA submitted but acceptance decision pending; VELA-2 primary composite p=0.053, research ABSTAIN.
- [Praxis FDA acceptance](https://ir.praxismedicines.com/news-releases/news-release-details/praxis-precision-medicines-announces-fda-acceptance-new-drug) — January 29 2027; dose withdrawal/safety require review.
- [Sarepta November SEC filing](https://www.sec.gov/Archives/edgar/data/873303/000119312526449721/srpt-20260930.htm) — Feb 28 2027 for two *separate* existing-product supplements; ESSENCE confirmatory primary did not reach significance.
- [FDA MYQORZO approval record](https://www.fda.gov/drugs/drug-trials-snapshots/drug-trials-snapshots-myqorzo) — completed 2025-12-19 oHCM action; not a pending 2026 approval case.

## Dashboard and machine-readable record

On \`/predictions\`, the new panel shows 29 NCT rows linking to their application judgments; 23 expandable source/benefit/counterevidence/missing-data records sorted by issuer-reported PDUFA date. Search/filter controls are active. A read-only JSON endpoint, \`/api/predictions/focus-preliminary\`, exposes a complete dated source-linked research version with no API writes.

**Official model status: 0 signed clinical reviews; 0 independently validated FDA forecasts; 0 measured historical out-of-time backtests; approval, CRL and review-delay prediction ABSTAIN for all FUTURE applications.** The one observed past approval is labeled as historical fact, not a new prediction. Delays and extensions have distinct fields; Capricor/Savara have a *previously observed formal extension* but no new extension prediction.

## Immediate barriers and continuation

Complete independent original clinical, trial/CMC and FDA application-cycle verification across all 23; support any lean with qualified clinical reviewer audit; capture immutable externally anchored research decision history; maintain blinded time-locked FDA outcome backtesting per issue #980; evaluate approved, CRL, pending, withdrawn and nonapproval cohorts with matched denominators. No claim of 100% predictive accuracy. Full production release requires explicit security/deployment authorization.

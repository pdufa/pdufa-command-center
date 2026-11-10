# MAIN Revision 70 — Original PubMed XML article evidence and provisional exact-trial role triage

**Verified November 9, 2026, Pacific time.** Development draft [PR #965](https://github.com/pdufa/pdufa-command-center/pull/965), branch `feature/medical-stage4-verified-method-matrix-20261108`. Production is not merged/deployed. Historical outcomes, model training, FOCUS/POOL rosters and retired scanning remain unchanged.

## Actual source and installation verification

1. [**R70 original 11 PubMed XML source research #42729546458**](https://github.com/pdufa/pdufa-command-center/actions/runs/42729546458) — **SUCCESS**. Restored SHA-pinned original R69 registry references, fetched all **11 NLM PubMed XML metadata/abstract article records** by the exact registered PMIDs, verified response integrity and archived original XML. [Original source artifact #13724930108](https://github.com/pdufa/pdufa-command-center/actions/runs/42729546458/artifacts/13724930108). Frozen report SHA-256 `03434b975e511b2d603227bab3e25768dbcc3a0e7b412d479d9afbd100cd2577`. Raw PubMed source XML SHA-256 `2aa5fac13c7741d7ed2d9b1c2d91101978661150c87324b566b88f75994e394b`.
2. [**R70 article metadata and browser acceptance #42730389740**](https://github.com/pdufa/pdufa-command-center/actions/runs/42730389740) — **SUCCESS**, exact code commit `cb1b627a1c4cc3ccc9401c5a1483983361f4c461`. All **13 focused frontend tests passed**, 0 failed; Python byte-exact article-data parity, TypeScript and optimized Next.js production-style build passed; real Chromium desktop 1365×850 and iPhone-emulated 390×844 interaction tests passed. [Browser receipts/artifact #13723798764](https://github.com/pdufa/pdufa-command-center/actions/runs/42730389740/artifacts/13723798764). Tests do not establish real signed-in iPhone Safari behavior.
3. [**R70 provisional publication-role display #42730093558**](https://github.com/pdufa/pdufa-command-center/actions/runs/42730093558) — **SUCCESS**, separate source-only article-role triage cross-linked from the original evidence recovery board.
4. [**NLM original XML-to-article-role crosscheck #42730604681**](https://github.com/pdufa/pdufa-command-center/actions/runs/42730604681) — **SUCCESS**. The provisional publication-role classification was independently compared to the frozen original article title/abstract study and phase metadata, rather than trusting role captions alone.
5. [**Exact-code READY development preview**](https://pdufa-new-dashboard-q92w4z3ga-pdufa.vercel.app/predictions/evidence-gaps), original article UI commit `cb1b627a1c4cc3ccc9401c5a1483983361f4c461`; independently HTTP-fetched with status 200 and confirmed original R70 article titles, DOI/article-type review details, exact NCT source sections, and clear ABSTAIN state. This is not production.

## Corrected PubMed source identities and interpretation

All 11 original PubMed records have a **ClinicalTrials.gov NCT databank association** to one of the seven FOCUS trials. Only **8/11** explicitly mention the exact NCT within the article *title or abstract*; **3/11** show the NCT only in PubMed's databank accessions. Even an explicit NCT string or Phase III indexing is not proof of a fully reviewed pivotal result, protocol/SAP concordance, an independent clinical assessment or FDA outcome prediction.

The following role triage is **provisional title/abstract source classification, not independent clinical adjudication**:

| Source content role from PubMed metadata/abstract | Count | Examples and original PMIDs |
| --- | ---: | --- |
| Candidate main Phase 3 efficacy report, requires full scientific adjudication | **5** | HOPE-3 `42526472`, INDIGO `42233621`, ACACIA-HCM original `42663312`, Launch-HTN `40587141`, RAPIDe-3 `42849489` |
| Related same-trial analyses, not separate Phase 3 pivotal trials | **2** | ACACIA-HCM `42667274` and `42663111` |
| Protocol/methods paper, not an outcomes report | **1** | INDIGO `41840328` |
| Earlier Phase 2 dose-selection component, not Phase 3 pivotal results | **1** | RINGSIDE `42848980` |
| Earlier Phase 1/2 cohort safety and pharmacokinetics, not the Phase 3 ESSENCE primary outcome | **1** | Casimersen `34105177` |
| Background reference curves, not an ESSENCE pivotal outcome | **1** | Muscle-size reference paper `40098309` |

This is one **trial crosswalk**, not 11 independent successful efficacy trials. ACACIA-HCM has three distinct publications linked to one NCT and must never be triple-counted as independent trial outcomes. NCT02500381 has two linked application groups but is one unique trial, not two trials.

## Engineering files

- `new-platform/backend/scripts/build_focus_pubmed_article_records_r70.py` and tests `new-platform/backend/tests/test_focus_pubmed_article_records_r70.py`.
- `.github/workflows/main-r70-original-pubmed-article-retrieval.yml`.
- `new-platform/backend/scripts/verify_r70_pubmed_metadata_dashboard_parity.py`.
- `new-platform/frontend/data/focus-r70-verified-pubmed-metadata-source.json`.
- `new-platform/frontend/lib/focus-r70-pubmed-article-source.ts`.
- `new-platform/frontend/app/predictions/evidence-gaps/OriginalPubmedArticleMetadataR70.tsx` and module CSS.
- Existing `OriginalPublicationLeadsR69.tsx` and `EvidenceRecoveryBoardR68.tsx` integrated with original article metadata.
- `new-platform/frontend/tests/focus-r70-original-pubmed-article-source.test.cjs` and `new-platform/frontend/scripts/verify-r70-pubmed-article-browser.cjs`.
- `.github/workflows/main-r70-original-pubmed-dashboard.yml`.
- The additional provisional article-role classification and XML crosscheck use `focus-r70-abstract-publication-triage.json`, `PublicationEvidenceRoleR70.tsx`, and `main-r70-pubmed-original-abstract-role-crosscheck.yml`. Preserve that research-only secondary audit, and avoid double-counting conclusions between the displays.

## True scientific and release constraints

- The original source content is **PubMed metadata and abstracts**, **not 11 independently read publisher full articles, CSRs or original signed historical SAPs**.
- Dated original paper availability must be assessed against prospective prediction dates: source publication dates may post-date any potential historical forecast origin. Research leads cannot be used as leaked retrospective predictors.
- Independent exact-trial pivotal *statistical and safety* assessments signed by qualified reviewers: **0**.
- 29 FOCUS unique NCT records and 23 provisional application-cycle groups; 232 unscored eight-domain review positions; original 466 PDF machine page references are not independent trial pass/fail tests.
- Independently validated future FDA approval/CRL predictions: **0/23**. Predicted probabilities and measured historical accuracy **unavailable**. Future approval/CRL/delay: **ABSTAIN**. No production, FOCUS/POOL, reviewer ledger, model training, retrospective FDA outcome, or retired RAAS/GEM scan writes.

## Next scientific installation gate

For the five **provisional main Phase 3** journal outcome reports, open the original full article and any accessible supplements, verify the exact trial identifiers and population, reconcile the original signed pre-unblinding protocol/SAP versus primary endpoint estimand, intercurrent events, multiplicity, missing data, sensitivity analyses, and adverse-event exposure denominators. Record contradictions and source dates before assigning any qualified signed clinical grade.

For the other six references, preserve their distinct background/earlier-phase/protocol/related-analysis roles and continue sponsor/journal/CSR/regulatory source recovery, especially for the other 10 FOCUS NCTs without PubMed references in the retained registry. No source-absence-to-failure inference.

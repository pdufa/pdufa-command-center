# MAIN R78 — Launch-HTN public disclosure chronology and official NDA target crosswalk

**Research cutoff:** November 9, 2026 Pacific. **Exact trial:** NCT06153693 / MLYS / lorundrostat. **Exact provisional application cycle:** `mlys-lorundrostat` (NDA). This evidence is original **public publisher, issuer and SEC disclosure**, not signed FDA application review, qualified scientific adjudication, independently authenticated SAP, or an original database-lock timestamp.

## What can now be established from original public sources

| Date | Public evidence and what it establishes | Original record |
| --- | --- | --- |
| January 24, 2025 | JAMA published report says last participant follow-up; **does not date final lock or unblinding** | [JAMA, published June 30, 2025](https://jamanetwork.com/journals/jama/fullarticle/2835763) |
| February 13, 2025 | Original JAMA Supplement 6 SAP v3.0/Amendment 2 and Supplement 7 multiple-imputation addendum show **printed electronic signature imprints**, not cryptographically authenticated signoffs | [JAMA publisher supplement index](https://jamanetwork.com/journals/jama/fullarticle/2835763) and R75 original PDF cover/signature page notes |
| February 23, 2025 | Original JAMA Supplement 5 windowing addendum shows electronic signature imprint; its cover says **2024** while the document header/signature materials say **2025** | Same original JAMA publication and R75 source note |
| March 7, 2025 | Issuer **scheduled** March 10 public pivotal data release; **not itself a public readout of results** | [Original Mineralys announcement](https://ir.mineralystx.com/news-events/press-releases/detail/59/mineralys-therapeutics-to-announce-topline-data-from) |
| March 10, 2025 | SEC Form 8-K Item 7.01/8.01 reported **positive Launch-HTN/Advance-HTN sponsor topline** and published the company-reported Week-6 numbers. This provides a source-dated public topline, **not the exact date of internal data lock or unblinding** | [Original March 10, 2025 SEC-hosted 8-K](https://ir.mineralystx.com/sec-filings/all-sec-filings/content/0001628280-25-011459/mlys-20250310.htm) |
| June 30, 2025 | Full JAMA article and protocol/SAP supplements publicly released. Journal says investigators and outcome analysts were **masked until final database lock**, but the journal supplies **no final database-lock date**. Public article date does not establish prospective SAP publication. | [JAMA original article](https://jamanetwork.com/journals/jama/fullarticle/2835763) |
| March 9, 2026 | **Issuer reported** FDA accepted lorundrostat NDA for adults with hypertension in combination with other antihypertensives; target assigned December 22, 2026. No original FDA acceptance letter independently authenticated in this research. | [Original Mineralys acceptance announcement](https://ir.mineralystx.com/news-events/press-releases/detail/93/mineralys-therapeutics-announces-fda-acceptance-of-nda-for) |
| November 4, 2026 | Original SEC Exhibit 99.1 states **FDA NDA review continuing as issuer reported** and PDUFA **December 22, 2026**. This is **target calendar evidence, not an approval, CRL, delay forecast, or regulator signoff**. | [SEC Exhibit 99.1, filed November 4, 2026](https://www.sec.gov/Archives/edgar/data/1933414/000193341426000142/mlys2026q38kex991.htm) |

**Strongest warranted chronological conclusion:** the printed February 2025 SAP signature imprints fall **after the JAMA-reported last follow-up** but **before the documented March 10 sponsor public topline**. The study authors describe masking until *final database lock*. This is **consistent with** a pre-unblinding signoff but is **not proof** that the relevant final SAP was version-locked before database unblinding. There is no independent evidence that the SAP changes were posthoc, either; document control, actual access permissions, original first-publication metadata and final lock timestamps remain absent.

**Source discrepancies:** two addendum cover date fields refer to **2024** while later header/signature imprints refer to **2025**. Keep both visible and unresolved. Do not infer intentional backdating, regulatory rejection or efficacy invalidity.

## Already-grounded NDA/application crosswalk

The canonical **29-trial FOCUS roster and 23 provisional application groups are unchanged**. Existing `new-platform/backend/app/data/focus_application_snapshot.json` already records exact NCT `NCT06153693`, cycle `mlys-lorundrostat`, type `NDA`, stage `UNDER_REVIEW`, goal `2026-12-22`, source date `2026-11-04`, and exact SEC Exhibit 99.1 URL. This revision cross-checks and displays that source rather than duplicating or altering the canonical roster or inventing a new cycle.

## Original history source limitation

The distinct [original ClinicalTrials.gov registry-history source check](https://github.com/pdufa/pdufa-command-center/actions/runs/42745873286) from the same draft Stage-4 branch ran, but **official history index returned unavailable**: historical full versions read **0** and history index versions **0**. This is a failed source retrieval, not evidence that there were no earlier registered versions. Even successful registry version dates would establish public registration snapshots, **not** the regulator-controlled original SAP lock, patient-level analysis code or private blinded-access timestamp.

## Implemented in the isolated Stage-4 draft

- Exact 9-event public chronology manifest `new-platform/frontend/data/focus-r78-launch-htn-public-chronology.json` with original source URL and source-date classification per event.
- Fail-closed crosswalk `new-platform/frontend/lib/focus-r78-launch-htn-public-chronology.ts` joins existing Launch-HTN original date and methods evidence; zero signed reviews and FDA outcome **ABSTAIN**.
- R78 trial-only read-only display in `new-platform/frontend/app/predictions/evidence-gaps/LaunchHtnPublicChronologyR78.tsx`, 9 source links, 6 specific original evidence gaps and an explicit timeline-vs-unblinding disclaimer.
- Dedicated adversarial source tamper tests `new-platform/frontend/tests/focus-r78-launch-htn-public-chronology.test.cjs`, pinned 29/23 canonical roster hash and SEC 2026 target-date check, platform typecheck/build, desktop/390px mobile browser link checks.
- Stage-4 work is **not merged**, does **not** alter production, and never revives retired RAAS/GEM or creates new clinical scores.

## What scientific evidence is still required

1. Obtain source-controlled **exact original signed SAP and protocol approval trail**, including the 2024/2025 internally inconsistent addenda.
2. Authenticate original **database final lock and actual unblinding authorization/first access timestamps**, including sponsor/data-management audit trails; distinguish participant completion and public topline release.
3. Reproduce locked H1–H7 multiplicity/familywise alpha, analysis populations, treatment-policy MAR/MNAR imputation and sensitivity from original statistical outputs.
4. Independently adjudicate treatment-arm safety and CMC/inspection/labeling evidence, including unknown nonpublic issues as **unknown**, never presumed defects.
5. Obtain independent qualified scientific/regulatory reviewer signatures and prospective or properly outcome-blind history calibration before authorizing FDA probabilities.

**Clinical truth at this stage:** signed expert assessments **0**, validated current application forecasts **0/23**, authenticated pre-unblinding original SAP locks **0**, actual final lock/unblinding dates **unknown**, actual FDA outcome **not established by this research**, **predicted FDA approval/CRL ABSTAIN**, predicted timing **UNKNOWN**. A published PDUFA **target** is not a prediction of action by that date.

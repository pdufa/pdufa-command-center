# Authoritative FDA outcome discovery and SEC issuer leads — 2026-10-27

## Critical FDA correction candidate
The `main:data/pdufa_source_report.json` for run `40443182030` marks `IONS|BEPIROVIRSEN_CHB_20261026` `REVIEW_REQUIRED` because the October 26 target date had passed and outcome was unresolved.

**New authoritative evidence:** FDA announced approval of **Hibsago (bepirovirsen)** on **2026-10-20**, ahead of its October 26 PDUFA target:
- FDA announcement: https://www.fda.gov/news-events/press-announcements/fda-approves-first-its-kind-chronic-hepatitis-b-treatment
- FDA approval letter, **NDA 221276**, original application: https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/221276Orig1s000Ltr.pdf
- FDA-approved labeling: https://www.accessdata.fda.gov/drugsatfda_docs/label/2026/221276Orig1s000lbl.pdf

**Disposition:** Strong primary-source evidence of an FDA **APPROVAL/PASS** for NDA 221276 original review cycle. This is a **proposed correction for adjudication and ingestion**, not a claim that the production source report or verified historical outcome corpus has been updated. Validate approval-letter signature/action date, applicant, product, indication, exact cycle, PDF bytes and SHA256, then link the trial/program event and publish the corrected same-cycle outcome. Preserve the earlier source report as immutable historical audit evidence. Do not treat an approval as evidence that any prior model forecast was correct.

## SEC identity leads, not automatic conflict clearance
- QNCX: SEC 2026-09-08 8-K lists Quince Therapeutics Inc., CIK 0001662774, QNCX on Nasdaq: https://www.sec.gov/Archives/edgar/data/1662774/000119312526390652/qncx-20260908.htm
- TBPH: SEC filing cover lists Theravance Biopharma Inc., CIK 0001583107, TBPH on Nasdaq, as of Sep 2026: https://www.sec.gov/Archives/edgar/data/1583107/000110465926106567/R1.htm
- The source report conflicts refer to SEC **submissions API responses** not identifying the requested ticker. A filing cover can independently support a historical ticker association, but must not be substituted for the exact response under audit or assert ongoing exchange listing after possible delisting. Check effective date and current status before closing conflicts.

## Required follow-up
1. Ingest and hash the FDA original approval letter in the source verification pipeline; verify applicant and cycle, and rerun the event-specific audit.
2. Add a regression test ensuring an authoritative FDA decision dated before the PDUFA target supersedes stale target-only `REVIEW_REQUIRED` state, without granting verified status from press releases alone.
3. Review SEC issuer identity checks against historical filing cover facts and effective listing dates, avoiding false conflicts from missing ticker metadata in API summaries.
4. Keep 20 SEC financing and 1 financial cash/runway issues open.

**Safety:** no source report, production DB, trading flags, FS/FA associations or live scanner changed in this research-only commit.

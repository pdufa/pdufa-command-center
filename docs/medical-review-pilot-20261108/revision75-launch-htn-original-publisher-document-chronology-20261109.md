# MAIN Revision 75 — original Launch-HTN published protocol/SAP date reconciliation

**Research date:** November 9, 2026 Pacific. **Original trial:** NCT06153693 / MLYS / lorundrostat Launch-HTN. **Source:** JAMA publisher's [June 30, 2025 article and nine-supplement list](https://jamanetwork.com/journals/jama/fullarticle/2835763); same [PMC public article and supplement listing](https://pmc.ncbi.nlm.nih.gov/articles/PMC12210145/). The journal article reports final participant follow-up **January 24, 2025**.

This note records **actual inspected publisher PDF page renders**, not downloaded immutable file bytes, cryptographically authenticated electronic signatures, original as-published pre-unblinding documents, independent blinded scientific assessment, or any FDA forecast.

## Seven public original publisher supplement documents

| JAMA supplement | Content | Exact publisher PDF physical pages inspected | Observed printed heading/effective date | Observed signature imprint | Caution |
| --- | --- | --- | --- | --- | --- |
| 1 | eMethods, multiplicity figure and sensitivity/safety tables | 1 of 37 | publication cover dated June 30, 2025 | not inspected | Scientific methods publication, not a signed original SAP |
| 2 | Protocol v3.1 EU | 1 of 80 | June 11, 2024 | not inspected | Printed EU version and effective date, independent approval history missing |
| 3 | Protocol v3.0 Amendment 2 | 1 of 81 | June 11, 2024 | not inspected | Original non-EU protocol v3.0 and source-version chain to reconcile |
| 4 | Protocol v2.1 UK Amendment 1 | 1 of 78 | January 8, 2024 | not inspected | Older UK protocol, not a complete original signed amendment chain |
| 5 | SAP 3.0 windowing addendum v1.0 | 1–2 of 5 | Header February 22, **2025**; cover field February 22, **2024** | February 23, 2025 | Conflicting printed years, source-controlled version and actual original lock need independent adjudication |
| 6 | SAP v3.0 Amendment 2 | 1–2 of 70 | February 13, 2025 | Three printed electronic signature imprints dated February 13, 2025 | Original signatures have not been cryptographically validated; evidence of prospective locking before unblinding unknown |
| 7 | SAP 3.0 multiple-imputation addendum v1.0 | 1–2 of 10 | Header February 13, **2025**; cover field February 13, **2024** | February 13, 2025 | Second conflicting printed year; chronology needs independent reconciliation |

The PDF-linked file names are preserved exactly in [R73's seven-document source index](https://github.com/pdufa/pdufa-command-center/blob/feature/medical-stage4-verified-method-matrix-20261108/new-platform/frontend/data/focus-r73-launch-htn-original-document-index.json). The stable publisher article above is the source locator; signed temporary CDN query URLs are deliberately **not** committed.

The trial's **last reported follow-up predates the printed SAP signoffs**, but this does not establish when the analysis database was locked or when the treatment blind was broken. A final plan can be signed after last participant follow-up and still precede database lock/unblinding; original independent signature/authentication chronology is essential.

### Provenance and access limitations

- **Actual public publisher PDF pages rendered and visually inspected:** 10 physical pages across all seven supplements. Their printed dates and electronic signature *images* were reviewed; these are not authenticated provenance receipts.
- **Exact original PDF SHA-256 receipts recorded in the repository:** **0 of 7**. The [R74 live bounded capture workflow](https://github.com/pdufa/pdufa-command-center/actions/runs/42741220354) returned **seven HTML/non-PDF responses**, refusing to treat a publisher/PMC download interstitial as original bytes. The separate R74 safety and receipt generation pipeline passed. The publicly linked JAMA PDF *pages* are nevertheless viewable through the publisher site, not a secure byte archive owned by this project.
- **Original first-publication date of each exact protocol/SAP file:** unknown; JAMA publication on June 30, 2025 does not prove each individual source document was separately public before analysis.
- **Signed pre-unblinding locked SAP independently authenticated:** 0; **independent signed scientific grades:** 0; **validated FDA forecasts:** 0/23; approval/CRL **ABSTAIN**, review timing **UNKNOWN**. No retired RAAS/GEM reintroduction or production writes.

## Remaining adjudication decisions

1. Independently validate original electronic signature evidence and source-controlled amendment/approval histories for all relevant protocol and SAP versions, especially disputed **2024 vs 2025** printed dates in supplements 5 and 7.
2. Obtain authentic blinded database-lock and unblinding dates, statistical plan release/signoff chain, and the sponsor's original regulatory submission to establish whether plan text was prospectively in effect.
3. Independently reconcile H1–H7 multiplicity, 1,000 treatment-policy imputations, MAR/MNAR assumptions and exact analysis denominator, while keeping original efficacy and sensitivity results distinct.
4. Reconcile arm-level potassium, sodium, renal function, serious adverse events and withdrawal exposure; independently review FDA CMC and label evidence.
5. Only after original-source verification and clinical signoff consider evidence-based preliminary case conclusions; do not invent a numerical FDA approval probability or historical accuracy.

## Implemented and accepted separately

The draft [Stage 4 PR #965](https://github.com/pdufa/pdufa-command-center/pull/965) now stores this research in `focus-r75-launch-htn-source-date-reconciliation.json`, enforces original version/date invariants in `focus-r75-launch-htn-chronology.ts`, tests malicious falsification and renders the new only-for-Launch-HTN page. [R75 source-only engineering workflow](https://github.com/pdufa/pdufa-command-center/actions/runs/42742169250) **SUCCESS**: Source data/7-case crosswalk tests, TypeScript and Next build, retirement audit and canonical 29-trial/23-cycle preservation. Success is **engineering validation of sourced observations**, not medical acceptance.

# First re-fetched original FDA approval source: NDA206627 (research only)

**Source observation recorded October 25, 2026. No independent human FDA
review-cycle adjudication or training approval.**

The original Drugs@FDA tabular source contained `NDA206627 ORIG 1`,
while the separately preserved openFDA approval-centric registry JSON
omitted **the entire application**. The pinned key-by-key comparison
found one tabular-only submission key out of **6,033**, with **6,032**
matching originals across the two archives. This case was selected
specifically to investigate that source mismatch; it is **not a
random or complete historic decision sample**.

The FDA's public original
[approval package PDF for 206627Orig1s000](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2014/206627Orig1s000Approv.pdf)
was fetched again by the isolated official-source research workflow
[40258696091](https://github.com/pdufa/pdufa-command-center/actions/runs/40258696091).
This was an actual independent byte retrieval of a **fixed** FDA URL,
not a copy of the prior JSON publication summary.

| Primary-source observation | Observed FDA evidence |
|---|---|
| Retrieved public PDF length | **53,383 bytes** |
| Exact PDF SHA-256 | `655cdf0c02d95b43edf62465b5a1b5b6b9583fb4b5e31b1dcaa99dfe39ac589b` |
| Total source PDF pages | **16** |
| Inspected cover page | PDF page 1 (zero-based 0) |
| Inspected original approval-letter page | PDF page 4 (zero-based 3) |
| Original application reference | `206627Orig1s000` on cover, `NDA 206627` on letter |
| Drug as named by FDA | Hysingla ER (hydrocodone bitartrate) |
| FDA published approval date | **November 20, 2014** |
| FDA original action-letter language | FDA letter states the application is approved |

All five specific document-level text consistency checks passed.
The reusable, synthetic-tested extractor
`hop_fda_nda206627_primary_source.py` checks application identifiers,
drug/ingredient, approval date and FDA action wording at exact page
indices. `scripts/probe_hop_nda206627_primary_fda_approval.py` retrieves
only that official HTTPS URL, rejects a redirected/non-PDF/oversized
document, and publishes a count/hashes-only audit without free text.
The report is in the published aggregate Actions
[artifact 12623760290](https://github.com/pdufa/pdufa-command-center/actions/runs/40258696091/artifacts/12623760290).

Frozen result:
`new-platform/backend/app/research_sources/hop_fda_nda206627_original_primary_observation_20261025.json`.
The checked-in index is intentionally **not** a machine training label.
No approval rate or probability was calculated. The source's reported
original application and date are document observations; the real
application review-cycle chronology, inclusion/exclusion protocol,
source-signed adjudication and independent second review have not yet
been established. The pipeline may not reinterpret a source-level
`APPROVAL` heading as an independently verified training decision.

This is one genuine original FDA action document examined out of
a far larger unresolved historical source universe; the separate
124-letter identity-gap worklist and 154-letter shared-PDF review
remain unresolved and **may overlap**. No progress percentage for
independently verified regulatory outcomes is justified from this
document inspection alone.

**Model eligible = 0; independently adjudicated review-cycle outcomes = 0;
complete NDA/BLA approval/nonapproval denominator = false; predictions null.**
The PR stays draft. No production deployment, night scans, trades,
GEM JR/GEM association or FS/FA preset reassignment occurred.

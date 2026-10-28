# First real FDA primary action-letter research sample — 2026-10-28

**Research scope:** Two purposively selected signed FDA letters, one APPROVAL and one COMPLETE RESPONSE. This is not a consecutive or representative FDA cohort. It is not a backtest and cannot support any prediction accuracy claim.

## Primary FDA evidence reviewed

| Outcome documented in FDA letter | Exact identity | Signed action | Official document |
|---|---|---|---|
| APPROVED | NDA 213973, QINLOCK/ripretinib, reference ID 4609421 | 2020-05-15 | https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2020/213973Orig1s000ltr.pdf |
| COMPLETE_RESPONSE | BLA 761303/Original 1, odronextamab, reference ID 5352252 | 2024-03-22 | https://download.open.fda.gov/crl/CRL_BLA761303Original1_20240322.pdf |

The ripretinib FDA letter says NDA 213973 was approved effective on the letter date for advanced GIST following at least three kinase inhibitors. The original unit number is visible in the FDA-hosted filename, not independently reconciled with the full application cycle history.

The odronextamab FDA letter identifies BLA 761303/Original 1 and states that the application cannot be approved in its present form. Its clinical deficiency concerns confirmatory-trial progress in follicular lymphoma. Its signed date is March 22, 2024. The separate Original 2 must not be merged with Original 1. A CRL is a nonapproval decision at that review, not permanent rejection.

Potential earlier public label chronology: Regeneron's dated March 25, 2024 sponsor release https://investor.regeneron.com/news-releases/news-release-details/regeneron-provides-update-biologics-license-application, which still requires separately documented source adjudication.

## What remains unverified

- Both FDA PDF pages were inspected through web rendering, but original PDF bytes were not retained. No original-file SHA-256 has been claimed.
- An FDA-signed action date is **not** proof of first publication date. Original public availability of the FDA PDFs is unknown. In particular, a redacted CRL posted as part of later transparency releases cannot be used as a pre-2024 feature.
- Exact review-cycle ordinal, original and revised PDUFA targets, public-label dates, full application histories and frozen predecision features are missing.
- No independent second-source reviewer has certified the cycle and action. There is no proven complete FDA application denominator.
- FDA's CRL publication archive was released in selective batches, including early releases favoring applications eventually approved. It cannot be treated as a representative approval/failure sample.

## New read-only audit contract

The source register is new-platform/backend/app/research_sources/hop_fda_primary_action_letter_samples.json; schema and fail-closed validator are new-platform/backend/app/hop_primary_action_letter_samples.py. It checks exact source IDs, unit identity, signature dates, FDA URL hostname, distinct reference IDs and source claims. It rejects any unearned model-training certification.

The complete return has two **FDA-signed action observations**, **zero independently adjudicated model cycles**, **zero independent real historical backtests**, no PASS/FAIL probability, and an explicit block list.

Offline research check (from the repository root):

```sh
PYTHONPATH=new-platform/backend python -c 'from datetime import date; from app.hop_primary_action_letter_samples import load_primary_letter_samples; print(load_primary_letter_samples(as_of=date(2026,10,28)))'
```

The optional file-only evidence hash script uses original bytes supplied from a controlled download, not a filename claim:

```sh
PYTHONPATH=new-platform/backend python new-platform/backend/scripts/audit_hop_fda_pdf_bytes.py NDA213973_ORIGINAL_1_20200515_APPROVED /path/to/original_fda_document.pdf
```

A SHA-256 calculated from a local file proves its identity for future comparisons, not that it came from FDA or that the historical cycle was reviewed. The script neither downloads nor writes a PDF, database, spreadsheet or trade.

## Next evidence gates

1. Obtain original FDA PDF bytes using approved source retrieval, retain verified provenance and calculate SHA-256 fingerprints. Confirm content and electronic signature independently.
2. Independently reconcile exact Original/supplement/review-cycle history and original/revised PDUFA dates.
3. Establish separately the earliest public outcome-label date and strictly earlier feature snapshot.
4. Create a prespecified complete historical FDA cohort with nonapproval and approval cases plus nonbinary dispositions, with a validated denominator and independent reviewer signoffs.
5. Reserve a genuinely unseen, related-program-disjoint final test cohort.

**These two real, selected decision documents are research source anchors, not model-eligible training rows and not a measured PASS/FAIL forecast.**

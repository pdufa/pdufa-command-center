# HOP historical FDA outcomes CSV intake — quarantine only

This is an **offline, schema-only intake** for separately sourced historical FDA
action records. Passing format checks is not proof of a verified decision, a
complete application cohort, or a validated prediction model. All tests are fictitious.

Template: new-platform/backend/data/hop_historical_outcomes_template.csv

## Three distinct dates

- decision_date: official FDA action date for the exact application and review cycle;
  it still requires original-document verification.
- public_features_as_of: historical trial-feature snapshot date, strictly BEFORE
  the FDA action. Modern trial records are not historical snapshots.
- feature_source_url: an HTTPS source reference offered for independently checking
  the historical feature. HTTPS syntax is not provenance verification.
- feature_source_first_public_on: the source's original public availability date,
  on or BEFORE public_features_as_of and strictly BEFORE the FDA decision.
  A later issue/print date is not a substitute for an independently verified
  earlier online-publication date.
- evidence_as_of: date FDA outcome evidence became available, on or AFTER the
  decision. It must never be used as a predictor.

Each record also carries an exact NDA/BLA/ANDA application identity, review cycle,
drug, sponsor, indication, modality, phase, primary FDA HTTPS outcome source and
source title. The source-publication date must be independently established,
not accepted merely because a submitter typed it. One dated feature source does
not verify every feature or establish that a cohort is representative.
A domain-format check never proves source-page content or outcome adjudication.

## Run (from repository root)

    PYTHONPATH=new-platform/backend python new-platform/backend/scripts/validate_hop_outcomes_csv.py new-platform/backend/data/hop_historical_outcomes_template.csv --as-of 2026-10-25

The empty template is expected to report REVIEW_REQUIRED. A populated file can
report SCHEMA_VALIDATED_REVIEW_REQUIRED, but model_eligible_records=0,
independently_verified=false, probability=null must remain unchanged.

This importer does NOT fetch data, insert into a database, independently review
FDA decision letters, populate probabilities, run scans, or place orders.
Independent document-page attribution, complete approval/nonapproval denominator,
point-in-time trial evidence, and walk-forward validation remain prerequisites.

A publication-selected CRL PDF archive, approved-only product registry, or
provisional PDF page match does NOT establish a complete FDA review-cycle cohort.

## Point-in-time provenance case: KEYNOTE-024 (illustrative; no model label)

The FDA's signed 2016-10-24 approval letter for BLA 125514/S-8 and S-12
(Reference ID 4003165) says the S-12 first-line NSCLC indication was approved
effective on the letter date. The S-8 and S-12 indications are **different**;
a historical review-cycle key must not collapse them. FDA original letter,
pages 1 and 6:
https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2016/125514Orig1s008,125514Orig1s012ltr.pdf

The KEYNOTE-024 randomized-trial paper is indexed by PubMed with electronic
publication on **2016-10-08** and print issue on **2016-11-10** (PMID 27718847):
https://pubmed.ncbi.nlm.nih.gov/27718847/

This illustrates why **first public availability** is different from a later
print-issue date. A reviewer must separately establish the precise feature,
public source and historical availability. Merely copying the contemporary
abstract into a current trial record does NOT establish a period-correct
predictor, and the paper cannot be the independent second reviewer of the FDA
decision. No historical outcome CSV was populated by this example.

A separate FDA letter for BLA 125514/S-47 with an effective date of
**2019-04-11** records fulfillment of **KEYNOTE-042** commitment 3127-2.
That is subsequent regulatory evidence, NOT predecision KEYNOTE-024 input
and NOT proof of KEYNOTE-024 commitment 3127-1 being fulfilled.
FDA letter pages 1 and 3:
https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2019/125514Orig1s047ltr.pdf

These sources support a reproducible *candidate* evidence timeline.
No reviewer pairing, complete outcome denominator, proof of each feature's
historical public date, or statistically calibrated HOP prediction is
established by this note. Maintain model_eligible_records=0, independent
verification false and probability null.

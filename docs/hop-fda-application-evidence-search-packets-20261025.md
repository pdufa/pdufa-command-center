# Original FDA application evidence-search research packets (2026-10-25)

**Research-only; not FDA outcome adjudication.** The previously saved
official-source gap audit contains **124 published letter references**:
**107 references grouped under 84 distinct candidate NDA/BLA applications**,
plus **17 ambiguous/unparseable references** which cannot be grouped by
application identity. Twenty of the 84 candidate applications have more than
one published letter reference; this does *not* imply multiple review cycles
or FDA decisions.

The new `new-platform/backend/app/hop_fda_gap_research_packets.py` creates
**101 private evidence-search tickets** (84 application packets and 17
individual ambiguous-identity packets). The primary grouping key is the
provisional normalized NDA/BLA application ID, not a biotech ticker,
drug name, reported approval rate or forecast. Every grouped packet carries
all source-letter SHA-256 identifiers, the distinct published document type
counts, a concrete FDA application search phrase, a reason it needs source
investigation, and **blank** manual source-evidence fields.

An investigator can fill the private packet's `manual_evidence_lead_url`,
`manual_evidence_document_type`, optional document byte digest, and
research notes. A separate offline screening tool only validates exact
unmodified packet identities, official HTTPS FDA/Gov domain allowlist,
permitted evidence-document types, digest syntax, and safe note length.
**It cannot establish that any URL returns the claimed document, that
a PDF really corresponds to a review cycle, that a human identity was
authenticated, or that an FDA action was approved/nonapproved.**
Even with complete text and digest claims, the results remain
`UNVERIFIED_FDA_SOURCE_LEAD_REQUIRES_INDEPENDENT_REVIEW`.

## Private local workflow

The isolated `hop-drugsfda-original-source-research.yml` run
builds the individual letter-level review queue in its runner's
`private_original_tables` directory. It now also creates
`unverified_original_fda_application_research_packets.json` privately
there, alongside the raw research source tables. **Neither the per-letter
queue nor the grouped per-application packets are uploaded to the CI artifact.**
Only an aggregate research audit is published with total packet counts and
source fingerprints.

To check a privately filled set of packets outside CI:

```bash
PYTHONPATH=new-platform/backend python \
  new-platform/backend/scripts/screen_hop_fda_grouped_evidence_leads.py \
  --private-unverified-letter-queue /private/unverified_published_letter_review_worklist.json \
  --submitted-grouped-research-packets /private/filled_fda_application_packets.json \
  --as-of 2026-10-25 \
  --private-output-json /private/evidence_lead_screening.json
```

The offline validator intentionally exits nonzero **even when every URL
and digest is structurally accepted**, so no caller can interpret a
successful shell exit as an authenticated FDA action or permission to
train, recalibrate or trade.

The next scientific dependency is the actual authenticated original
FDA application/action-letter evidence, including the complete set of
review cycles for both approvals and nonapprovals. Independent
adjudicators must resolve ambiguous IDs, whether apparent repeat letters
represent distinct cycles, effective original action dates, and public
predecision clinical predictors. Separately establish the full original
NDA/BLA decision denominator and time-forward calibration.

**Scientific gate status: independently verified review-cycle outcomes = 0;
model-eligible records = 0; approval rate/probability/accuracy unavailable.**
GEM JR/GEM original FS/FA preset assignments, scans and production
probabilities are unchanged. The research work remains an unmerged draft.

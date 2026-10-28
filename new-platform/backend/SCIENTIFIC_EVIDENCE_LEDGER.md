# Scientific Assessment — Independent Evidence Ledger (isolated review)

**Purpose:** Give scientific reviewers an auditable place to collect independent-source citations, assertions, contradictions, dates, and corrections for **GEM JR, GEM, and WT** pilot trials. This is not independent adjudication itself and does not calculate FDA approval probability.

## Read-only review experience

On the isolated [Scientific Assessment panel](https://pdufa-scientific-assessment-review.onrender.com/scientific-assessment/batches), enter the existing internal review API key and inspect one exact archived NCT trial. The authenticated `GET /api/scientific-assessment?exact_id=TRIAL|NCT########` includes `evidenceLedger` when the trial's gzip/SHA-256/NCT identity check passes. The ledger is **separate from** the 20-stage investigation, registry-reported quantitative results, and two evidence grades.

The screen shows the four external evidence gates, previously identified bibliographic source candidates, and the persistent revision history. Linked sources are opened manually; no server-side crawling occurs. For the existing KEYNOTE-024 historical pilot, **seven source candidates** appear as *candidate citations*, including three separately dated reports, an FDA-staff-authored journal article, an NCI summary, the sponsor-provided [trial protocol/SAP](https://cdn.clinicaltrials.gov/large-docs/38/NCT02142738/Prot_SAP_000.pdf), and the [FDA October 24, 2016 S-8/S-12 approval letter](https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2016/125514Orig1s008,125514Orig1s012ltr.pdf). The FDA primary document is distinguishable from an FDA-staff-authored journal article, and the linked 2017 protocol upload may include amendments made **after** the original 2016 trial analysis. All remain unadjudicated. These are citations for human review, **not automatically verified sources**.

## Stored evidence candidates — append-only

Table: `scientific_evidence_ledger` (created additively in the isolated PostgreSQL review database).

An entry includes exact NCT, one of four independent-review gate IDs, HTTPS source URL, source type, optional publication date, bounded claim text, relationship (**supports**, **contradicts**, **context**, **unresolved**), uncertainty/caution note, reviewer label, UTC recorded time, a thread ID, per-thread revision number, optional `supersedesId`, and canonical SHA-256 of the stored assertion.

Corrections are **new records**: revision N+1 references the immediately preceding record. Previous revisions remain intact. A unique database constraint prevents two successful competing writes to the same thread/revision. Changing a stored field without an updated checksum causes a ledger-integrity error and the UI does not display the compromised ledger. Because only a privileged DB administrator could rewrite both data and hash, this is tamper **detection**, not cryptographically irreversible external notarization.

Each stored entry is forcibly labeled `pending_independent_review`; API clients **cannot** set `verified`, supply an independent-review override, or cause the existing 16-item analysis-readiness rubric to promote a gate. The 20-stage and six/eight-domain scientific scores stay independently evidence-gated. A newly submitted URL does not prove authenticity, publication quality, an endpoint result, clinical effectiveness or regulatory status.

## Writing is disabled by default

`POST /api/scientific-assessment/evidence-ledger/NCT########` is installed but will return **403** until the review operator explicitly enables the isolated-service-only `PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED=1`.

The write operation then also requires both:
- the existing `x-pdufa-internal-key` header;
- a **different** `x-pdufa-scientific-review-key` header matching a separately configured `PDUFA_SCIENTIFIC_REVIEW_WRITE_KEY`.

It is fenced to the exact isolated Render service ID `srv-dbehn9fb9u1s739ok5vg` and persistent PostgreSQL. Production cannot use it. **Do not paste either key into a conversation, a GitHub commit, or a URL.** The read-only browser panel never saves or exposes the second credential. Operators should configure it only through Render's secure environment management.

Request example (illustrative, NOT runnable without the two secure keys):

```json
{
  "gateId": "published_results",
  "sourceUrl": "https://pubmed.ncbi.nlm.nih.gov/27718847/",
  "sourceType": "peer_reviewed_publication",
  "sourcePublishedAt": "2016-10-08",
  "claimText": "Published data identify an analysis requiring protocol reconciliation.",
  "relationship": "context",
  "caution": "Independently compare populations, prespecification and reported statistical methods.",
  "recordedBy": "Review curator",
  "supersedesId": null
}
```

The source URL must be public HTTPS without an IP literal, local domain, URL credentials or fragment. The application **never fetches** submitted URLs. A wrong NCT, corrupt archive, invalid date, unsupported gate, unknown `verified` field, missing key or production service rejects writes. A successful request returns **201**, with an *unverified* candidate.

## Validation and next phase

The offline test suite verifies authenticated reading, default-denied writing, isolated-service ID, separate review credential, versioned non-destructive corrections, contradictory claims, checksum tampering detection and no scientific score promotion. Chromium tests cover the citation/source and conflict display and key clearing. Isolated deployment startup logs `SCIENTIFIC_EVIDENCE_LEDGER_STORAGE` with candidate revision counts only.

**Still required for true independent verification:** obtain full-text source documents, verify source identity/date and exact trial/indication, audit population and statistical claims against the original protocol/SAP and registry revisions, reconcile contradictory evidence and FDA/CMC files, require reviewer attestation and audit history, then independently validate completion of the four gates. No automatic scientific success/failure decision or FDA approval forecast should occur before this work.

## Historical pilot: eight evidence reconciliation questions

The KEYNOTE-024 panel now includes **eight prioritized, linked, unadjudicated questions** in its source reconciliation worksheet:

1. **Protocol version and statistical-lock chronology:** the protocol/SAP link is dated December 20, 2017, after the May 2016 original trial cutoff and FDA's October 2016 action. Verify the prospectively binding version and interim alpha-spending plan.
2. **Exact population and FDA indication:** ensure PD-L1 TPS >=50% and EGFR/ALK restrictions match the original first-line population; never combine the S-8 previously-treated and S-12 first-line indications.
3. **Original PFS versus later OS:** do not combine 2016 primary-endpoint/interim estimates with five-year follow-up under one purported timepoint.
4. **Crossover:** assess the effect of switching to immunotherapy after chemotherapy progression on long-term survival comparisons.
5. **Safety definitions:** differentiate treatment-related grade 3–5, all-cause, immune-mediated, and serious events and match the proper denominators and exposure.
6. **Exploratory quality of life:** check nominal p-values, incomplete questionnaires and multiplicity.
7. **Historic FDA actions:** verify supplement numbers, October 24, 2016 decision, target indication and postmarketing commitments, rather than treating the historic approval as a future PDUFA probability.
8. **Independent corroboration:** require distinct experiments or populations; institutionally hosted summaries of the same study are not independent replication.

All eight entries have `status=open_unadjudicated`, `independentlyVerified=false` and no score. They link to the **source candidate documents** but do not assert scientific appraisal or retrospectively invent prior verification. Other exact trial records receive a four-gate generic checklist until their own evidence is investigated.

No new trial, candidate ranking, financial scan, trade order, or live scientific score is created. The isolated staging startup log `SCIENTIFIC_SOURCE_RECONCILIATION` confirms seven pilot source URLs and eight open tasks without any write.

## Source-linked reviewer statements — recorded, not independently confirmed

The isolated review backend now has a separate append-only `scientific_reviewer_findings` table for documenting the human evidence-analysis process. This stores a **reviewer-authored statement**, not a verified scientific result or a professional-license check.

Each statement must identify an **exact archived NCT trial**, a valid question ID from that trial's reconciliation worklist, a known question citation or a same-gate source candidate in the validated ledger, and a **specific source locator** such as a section, table or PDF page. It also records one of `supports`, `contradicts`, `uncertain`, or `not_assessable`; a bounded factual assertion; a reason for uncertainty; a reviewer *label*; the date; and SHA-256 checksum.

Corrections **never rewrite** an earlier statement. Use `supersedesId` to append a new version in the same thread. The database enforces one successor per parent to prevent competing revisions. The read-only view shows all historic versions and identifies disputes **only between latest independent threads** (a retracted contradiction does not remain a current dispute). A tampered statement prevents the whole ledger or packet from being displayed as trustworthy. A SHA-256 integrity check is not a cryptographic signature or an identity-verification mechanism.

### Review-only submission API

`POST /api/scientific-assessment/reviewer-statements/NCT########` accepts:

```json
{
  "questionId": "protocol_amendment_chronology",
  "sourceUrl": "https://cdn.clinicaltrials.gov/large-docs/38/NCT02142738/Prot_SAP_000.pdf",
  "sourceLocator": "Protocol amendment table, PDF page 5",
  "findingType": "uncertain",
  "assertion": "The posted amendment chronology must be reconciled with the prospectively effective analysis plan.",
  "uncertainty": "The linked protocol version was posted after the original interim analysis.",
  "reviewerLabel": "Independent source reviewer",
  "reviewerAttestsReadSource": true,
  "supersedesId": null
}
```

This API uses **both** the ordinary internal API key and the distinct evidence-review write key; it is accessible only from the exact isolated service with the separate `PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED=1` setting. Writes remain disabled unless the operator explicitly enables this gated facility in Render. The browser **does not** store the review key or provide a way to bypass the gate. Do not put credentials in a GitHub commit, URL, screenshot or chat.

The source URL is checked against the question's known citations or an existing same-gate ledger candidate. Claims of `verified=true`, `resolved=true`, `approvalProbability`, and any extra fields are rejected. Attesting to reading a document is **not** proof of reviewer qualifications or independent evidence validation.

### Scientific meaning of reviewer-statement statuses

A document with two contradictory reviewer statements is **disputed**, not disproven. An apparently supportive review statement is **unconfirmed**, not scientific success. All questions remain `open_unadjudicated`, both existing evidence grades stay on the same conservative rubric, and no FDA approval probability or independent scientific score is assigned. A separate, authenticated independent-review attestation, conflict-resolution procedure and clinical verification process will be needed before any gate can legitimately become verified.

The read-only trial page and downloadable scientific packet now expose source locators, revision history, dispute flags and the number of reviewer statements per unresolved question. Initial production deployment contains **no prefilled reviewer findings**; these records can only arise from a deliberately authenticated, review-service-only write.

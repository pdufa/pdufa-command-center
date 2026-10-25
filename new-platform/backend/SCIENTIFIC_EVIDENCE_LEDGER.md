# Scientific Assessment — Independent Evidence Ledger (isolated review)

**Purpose:** Give scientific reviewers an auditable place to collect independent-source citations, assertions, contradictions, dates, and corrections for **GEM JR, GEM, and WT** pilot trials. This is not independent adjudication itself and does not calculate FDA approval probability.

## Read-only review experience

On the isolated [Scientific Assessment panel](https://pdufa-scientific-assessment-review.onrender.com/scientific-assessment/batches), enter the existing internal review API key and inspect one exact archived NCT trial. The authenticated `GET /api/scientific-assessment?exact_id=TRIAL|NCT########` includes `evidenceLedger` when the trial's gzip/SHA-256/NCT identity check passes. The ledger is **separate from** the 20-stage investigation, registry-reported quantitative results, and two evidence grades.

The screen shows the four external evidence gates, previously identified bibliographic source candidates, and the persistent revision history. Linked sources are opened manually; no server-side crawling occurs. For the existing KEYNOTE-024 historical pilot, **five previously documented references** appear as *candidate citations*, including three separately dated reports, an FDA-staff-authored journal article (not a substitute for FDA.gov decisions), and an NCI summary (not an independent replication). These are citations for human review, **not automatically verified sources**.

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

# MAIN Phase 3 — commercial-rights evidence submission rules

This is a **research-only audit queue**, not a registry of legally established rights and **not** a Pipeline, GEM JR, or GEM promotion mechanism.

- The dated original census contains **741 NCT trial records** associated with **130 SEC issuer research pointers**. Neither count establishes current eligibility.
- The commercial-rights review worklist contains **six checks for each trial**, or **4,446 review slots**.
- \`data/phase3_rights_review_submissions.json\` initially contains \`[]\`. It is the only submission input to this workflow. A zero count means **no claims have been submitted to this version-controlled intake**, not that rights do not exist.
- When the review intake changes via a GitHub pull request, the qualification workflow validates each submission. The resulting research report is saved as \`main_phase3_rights_review_submissions_coverage.json\` in the research-only GitHub Actions artifact.
- Entries are source and issuer-bound, but **reviewer identity and conclusions are reported assertions, not independently authenticated facts**. No number of accepted-looking assertions modifies the qualification ledger.

## Example of a PENDING submission

The following is a **schema example with a fictitious trial and company**, not a submission to add to the actual dataset. Do not add it to the repository as live evidence.

\`\`\`json
{
  "nct_id": "NCT00000001",
  "ticker": "EXAMPLE",
  "issuer_sec_cik": "0000000001",
  "check": "VERIFY_CURRENT_US_TERRITORIAL_DEVELOPMENT_OR_COMMERCIAL_RIGHTS",
  "source_url": "https://example.com/illustrative-primary-disclosure",
  "source_sha256": null,
  "observed_at_utc": "2026-10-26T00:00:00Z",
  "claim": "Possible rights disclosure needing original-source verification.",
  "reviewer_status": "PENDING"
}
\`\`\`

Use the **actual** NCT, ticker, CIK, registry intervention/condition and source URL from the generated rights worklist. A pending outside URL must be a public HTTPS source and carries **no verified-document hash**.

## Allowed reported reviewer states

| Value | Meaning |
|---|---|
| \`PENDING\` | A proposed research source awaiting document and legal-entity review |
| \`REVIEWER_REPORTS_SUPPORT\` | A named reviewer reports supporting source language; still **not a validated rights determination** |
| \`REVIEWER_REPORTS_NO_SUPPORT\` | A named reviewer reports the source does not support the required assertion |
| \`REVIEWER_INCONCLUSIVE\` | A named reviewer reports that the source does not resolve the claim |

For any reviewer-reported state other than \`PENDING\`, the submission must include \`reviewer\` (nonempty name/identifier), \`reviewed_at_utc\` (UTC), and \`source_sha256\` **exactly matching a previously fetched SEC primary document for that trial's issuer**. A saved CIK or SEC filing URL by itself is not enough. This rule is deliberately restrictive. Other independently verifiable source types need their own verified source-adapter code and tests before they can be treated as reviewed in this workflow.

Record a separate source URL per NCT/check combination. Duplicate URLs for the same trial/check are blocked. If two reviewers report contradicting findings on two separate primary documents, the worklist shows a conflict.

## The six required checks

1. \`VERIFY_CURRENT_ISSUER_AND_LEGAL_ENTITY_CHAIN\`
2. \`MATCH_ACTUAL_DRUG_AND_INDICATION_TO_PRIMARY_DISCLOSURE\`
3. \`VERIFY_CURRENT_US_TERRITORIAL_DEVELOPMENT_OR_COMMERCIAL_RIGHTS\`
4. \`VERIFY_EFFECTIVE_EXPIRATION_TERMINATION_AND_TRANSFER_DATES\`
5. \`REVIEW_EXCLUSIVITY_SUBLICENSE_AND_COUNTERPARTY_LIMITATIONS\`
6. \`INDEPENDENTLY_REVIEW_AND_DATE_ORIGINAL_SOURCE_DOCUMENT\`

**What is not yet installed:** authentication of external reviewer identities, complete legal review of ownership/licensing or FDA decisions, and automated production qualification. The GitHub runner currently has no configured \`SEC_USER_AGENT\` identifying contact, so SEC *primary-document* requests were not attempted in the latest verified workflow. Do not invent a contact identity or interpret these missing documents as adverse evidence.

The existing Pipeline restriction of **$300M–$10B market capitalization** and all independent GEM JR/GEM FS/FA presets remain unchanged.

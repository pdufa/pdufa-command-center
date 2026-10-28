# KEYNOTE-024 original 2016 protocol supplement: source listing vs signed SAP

## Verified source discovery (not PDF content verification)

The original NEJM KEYNOTE-024 article (online October 2016; DOI 10.1056/NEJMoa1606774) explicitly lists a **Protocol** supplement named `nejmoa1606774_protocol.pdf` (~3.17 MB), separate from a supplementary appendix. Primary publisher: https://www.nejm.org/doi/full/10.1056/nejmoa1606774 . PubMed PMID 27718847: https://pubmed.ncbi.nlm.nih.gov/27718847/ .

The publisher listing is evidence that a supplement was attached to the publication. **It is not evidence that the full PDF was successfully read, signed, or effective before the original interim data cutoff (May 9, 2016).** A later registry-linked SAP/amendment is dated December 20, 2017 and marked Japan-only; it cannot retroactively verify the original pre-interim statistical plan.

The original 2016 article describes a blinded independent central-review PFS primary endpoint, randomized ITT efficacy population, as-treated safety population, independent monitoring committee, and a second interim analysis. Those descriptions are **published methodological statements**, not a validated contemporaneous alpha-spending schedule or independently audited statistical code.

## Required to unlock original pre-interim protocol/SAP gate

1. Obtain the publisher-linked 2016 PDF and preserve exact bytes, SHA-256, access date, version history, document title, and page references.
2. Extract and independently check each protocol/SAP effective date, amendment, signature or approval, geography, and change-control history relative to May 9, 2016.
3. Verify the prospectively applicable PFS/OS/ORR endpoint hierarchy, alpha-spending and interim efficacy thresholds, data cutoff, censoring and missingness, crossover rules, safety risk windows and analysis populations.
4. Compare those requirements with published analyses and the archived registry; record differences as unresolved until adjudicated.

**Current result:** source listing verified; PDF contents **not** verified; original signed SAP **not** verified; pre-interim alpha **not** verified. The 12-input review remains 5 source-supported, 7 unresolved; **Input Readiness FAIL**, **Reluctance HIGH**. This source discovery changes neither grade, any scientific score, any FDA probability, nor trading functionality.

## Code contract

`scientific_protocol_readiness.keynote024_protocol_readiness` returns `original2016ProtocolSource` with explicit verified listing and false document-content/effective-date/alpha-verification flags, and attaches the original journal URL to the existing BLOCKED `pre_cutoff_protocol` gate. Tests assert the gate stays blocked. This is a review-branch-only, read-only change.

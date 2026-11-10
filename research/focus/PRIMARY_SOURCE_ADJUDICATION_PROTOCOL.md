# Stage 4.3 — FOCUS primary-source adjudication protocol

Status: **PROTOCOL ONLY — NO CLINICAL TRIAL ADJUDICATED**.

## Scope and immutable boundaries
- Canonical roster: `new-platform/frontend/data/p3PostDataActive.json` (29 ticker/NCT pairs).
- Preliminary dossiers: `research/focus/*preliminary-evidence*.md`. These are research leads, **not independently validated findings**.
- Workqueue: `python scripts/build_focus_adjudication_queue.py`.
- Do not alter historical prediction versions, scores, the canonical roster, or historical outcomes while adjudicating.
- Do not turn a missing endpoint, CMC package, or FDA correspondence into a negative finding. Mark unavailable, unreported, or not applicable as appropriate.

## Review procedure for EACH ticker/NCT
1. Verify the NCT identifier, study phase, sponsor, drug, indication, enrollment, primary endpoint, analysis population, and key dates against the current ClinicalTrials.gov record and protocol amendments. Record the retrieval date and URL.
2. Obtain primary sponsor disclosures, full trial protocol/statistical analysis plan where public, results postings, peer-reviewed publication, and FDA source documents where available. Cite the exact section/table/page and document date. Distinguish sponsor claims from independent findings.
3. Perform eight separate assessments: mechanism/disease; design/population; endpoints/statistics; benefit; safety; subgroups/external validity; FDA/CMC; independent challenge. Record the phase-appropriate evidence and conflicting findings.
4. Record an explicit status for each: VERIFIED, PARTIAL, UNAVAILABLE, NOT_APPLICABLE, or DISPUTED. Each VERIFIED result needs primary source URL, document date, quoted location, reviewer identity, review timestamp, and rationale.
5. For a second-reviewer challenge, require a distinct reviewer, a reproducible counterargument search, and a signed resolution of material disagreements. The same automated summary cannot self-certify independent review.
6. Gate any publication of a probability on verified outcome labels, a prespecified model version, leakage-controlled historical backtesting, calibration, uncertainty bounds, and an as-of timestamp. Without these, show **NOT CALCULATED**.
7. Preserve append-only prediction history and record any reassessment trigger (protocol amendment, topline readout, FDA action, safety signal, manufacturing update).

## Acceptance checks
- Exactly 29 distinct canonical ticker/NCT pairs are addressed.
- Exactly 232 category reviews are tracked, with no assumed VERIFIED statuses.
- Every claim is traceable to a dated primary source or explicitly labeled secondary source.
- No future information leaks into historical prediction backtests.
- An unresolved material disagreement blocks the independently adjudicated designation.
- Scientific confidence is not equated to the modeled FDA approval probability.

## Initial execution order
Begin with the first canonical trial (ABVX / NCT05507203), complete its source inventory, then proceed to ABVX / NCT05507216. Continue in canonical roster order; report missing source material rather than inventing it.

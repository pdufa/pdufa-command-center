# MAIN Revision 42 — source-fingerprinted posted ClinicalTrials.gov outcome research (29 FOCUS trials)

**As of:** November 9, 2026. **Issues:** #979 (preliminary assessments for all 29 FOCUS exact NCTs), #980 (historical FDA validation), draft #965 (Stage 4). This revision preserves all prior trial/application crosswalks, 23 provisional application research leans, existing 800-method scientific framework and official ABSTAIN release gate.

## New original public evidence extraction

Run \`new-platform/backend/scripts/extract_focus_registry_outcomes_r42.py\` on the existing backend exact-NCT roster. For **each of 29 FOCUS trials**, retrieve only its exact identified ClinicalTrials.gov API v2 record over HTTPS (no redirects, max 5 MB per NCT, bounded concurrent reads), verify the returned \`nctId\`, and SHA-256 fingerprint the actual retrieved response.

Extract as source-reported **research facts**: current registered phase/status/last posted update; presence/absence of \`resultsSection\`; the count of \`PRIMARY\` outcome measures; each reported primary-measure title, time frame, unit, analysis count, analysis method, **p-value as an unmodified string**, and confidence interval lower/upper values as published; adverse-event row counts and availability of flow, safety and outcome modules. Source outcome descriptions are intentionally abbreviated; the original registry source URL and current-response hash retain provenance.

The output is a 29-row immutable, dated research receipt with coverage/exception totals and per-NCT primary facts. It is not a snapshot from the historical period before an FDA decision, because the current API can contain later edits. It cannot be placed in retrospective training or a blinded historical replay without authenticated original as-published timing.

\`main-focus-registryposted-r42.yml\` tests the parser with synthetic studies, fetches the public registry, compares exact 29 NCTs and 23 provisional application groups, and retains a separate 90-day GitHub artifact, not permanent archival. Failure of any NCT record fetch blocks full completion; uncollected trials are recorded as unknown, never assessed negatively.

## Clinical interpretation and release gates

- P-values and CIs from the registry are **reported observations**, not independently recalculated statistics, multiplicity-corrected claims, clinically significant effects or qualified Phase 3 passes.
- An absent registry results section does **not** imply that trial results, publications or sponsor press releases are unavailable elsewhere; Phase 3 data source discovery remains broader than this registry.
- Serious or other adverse-event **row count** does **not** mean number of participants harmed or establish comparative safety; group denominators and event definitions require independent review.
- The registry record alone does not verify final SAP, protocol amendment timing, CONSORT populations, pharmacovigilance/safety, CMC, FDA acceptance, approval/CRL odds or a future review extension.
- **Independent scientific method grades 0; verified FDA application forecasts 0; qualifying historical FDA backtests 0; accuracy NOT CALIBRATED; future approval/CRL/timing predictions ABSTAIN.** Existing Rev39 preliminary qualitative research judgments are unchanged.

## Next pass

Once the real retrieval job succeeds, report actual results coverage and the exact number of posted primary measures. Pin only an authenticated digest and research fields to the development dashboard; do not claim the number of outcomes as an FDA performance or clinical proficiency score. Map each recorded primary outcome to its associated existing application and trial, then reconcile against original as-published pivotal company reports, independent study statistical analysis plans and adverse-event safety definitions.

Source API documentation: https://clinicaltrials.gov/data-api/how-download-study-records and https://www.nlm.nih.gov/pubs/techbull/ma24/ma24_clinicaltrials_api.html. This procedure does not automatically run in the background beyond the configured GitHub workflow.

# Run Levels 1–6 from ASSESSMENTS

The ASSESSMENTS page (`/predictions/assessment`) now has an owner-directed runner:

1. Sign in using the existing dashboard login.
2. Choose a FOCUS trial and click **Run selected trial · Levels 1–6**, or click **Run all 32 FOCUS trials · Levels 1–6**.
3. Expand each level to inspect its automated checks, source observations, preliminary interpretation, supporting reasons, contradictions, limitations and owner questions.
4. Download the JSON assessment run to retain it. Runs are session-only and are **not saved to the database**. No owner acceptance is recorded automatically.

The run executes six separate phase-first processors over the collected evidence package. It does not merely count registry fields: it incorporates the retained clinical research worksheets, the detailed ORCA-2 dossier, original protocol/SAP collection status and validated ORCA-2/ORCA-3 publication observations. Available reported counts/percentages and odds-ratio intervals are checked for consistency. Clinical importance, statistical adequacy and unresolved chronology remain owner questions, not software-certified conclusions.

The source mode is **collected evidence, no new retrieval**, with its exact cutoff displayed. A new run timestamp does not mean fresh sources. Regenerate the package from retained research when source versions change:

```bash
python scripts/medical/export_level16_assessment_evidence.py
python scripts/medical/export_level16_assessment_evidence.py --check
```

The reproducibility check runs in CI. Original PDF/XML/HTML bodies and private paths remain outside the website package; it contains bounded observations, aggregate reported results, source URLs/dates and evidence-record digests. Digests do not certify provenance.

Each run gets a server-generated UUID and timestamps. One-trial mode returns six level results; all-trial mode returns 32 exact trials / 192 level results. All outputs remain `OWNER_NOT_REVIEWED`, and FDA probabilities remain null. Source gaps, conflicts, unresolved phase and not-yet-expected future-phase evidence are distinct. The three unmapped trials remain runnable and explicitly unmapped; 29 provisional trial mappings / 23 cycles are not promoted to verified FDA identities. Current-source research remains excluded from blind historical calibration.

`GET /api/assessments/levels1-6` returns trial choices only. `POST` accepts exactly `{"scope":"ONE","nct":"NCT04576949"}` or `{"scope":"ALL"}`. Both require the existing valid server-checked dashboard session. POST also enforces same origin, bounded JSON and the canonical FOCUS cohort. Client-provided sources, roles and review claims are rejected. No new identity provider, external reviewer, attestation or A01–A14 approval is required for owner research. Existing account security remains separate from medical review status.

No background runs, database writes, worker/scan changes, Levels 7–20 processing, historical prediction updates, merge or deployment are performed by these controls. The new interface runs after this development branch is deployed through the separately authorized release process; a local build or test is not a live deployment.

## Level 3 directional predictor

Choose a trial and click **Run Level 3 predictor · selected trial**, or use **Run Level 3 predictor · all 32 trials**. These run only Level 3. The original six-level buttons also include the prediction card. Trial choices display their position plus ticker and exact NCT; always identify a trial by NCT, since a row position can change.

The card returns **Approval lean**, **CRL lean**, or **Insufficient evidence**, with original citations, reported primary comparisons, reasons, contradictions, missing evidence and limitations. These are conditional, unvalidated **clinical-evidence hypotheses**, not complete FDA application forecasts. No numerical score, probability, pending FDA action, verified application identity, owner acceptance or blind accuracy is inferred. Runs remain session-only with JSON download.

Method `level3-clinical-lean-v1` supports the two explicitly source-extracted ORCA Phase 3 abstinence reports. Each must have the exact NCT/PMID, original full-text receipt/digest/date, an in-cutoff retrieval, one provisional application relationship, original safety observations, and both unique primary comparison IDs. Reported counts, rounded percentages and intervals must be consistent. Both primary comparisons favoring treatment with reported 95% odds-ratio intervals above 1 support an Approval lean **on efficacy evidence only**. Both favoring placebo with intervals below 1 support a CRL lean **on adverse efficacy evidence only**. Inconclusive, mixed, incomplete or opposing secondary evidence leads to abstention. Missing documents, early phase, registry endpoint descriptions, results posting, null results or lack of an FDA search match never imply a CRL. This rule does not verify multiplicity or prespecification and is not generalized to other endpoint types/diseases.

With the retained November 14 evidence, ORCA-2 and ORCA-3 return conditional Approval leans; the other 30 trials return Insufficient evidence with actionable gaps. Trial 14 in this roster is CLDX/NCT06455202: the package lacks its extracted quantitative results, so sponsor source pointers alone do not produce a lean. No genuine CRL lean is asserted by this dataset. Negative-branch tests use clearly synthetic altered data only, never stored clinical records. Extend source-extracted disease-specific interpretations before extending directional coverage.

Serious events, deaths, safety-population differences, chronology uncertainty, provisional application relationships, manufacturing/inspection gaps and lack of current filing confirmation remain visible. In particular, ORCA-2 database-lock/unblinding chronology remains unresolved. ORCA-3 online publication (2025-04-21) and indexed issue (2025-06-01) dates are preserved separately. No original historical research file is rewritten. A new timestamp is not evidence freshness, scientific validation or prospective blinding.

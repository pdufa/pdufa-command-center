# Scientific Investigation: 20-stage evidence map

This is the **scientific investigation source-coverage layer**, not a claim that 20 levels have been fully analyzed or that a trial is likely to obtain FDA approval. It builds on existing authenticated six-domain assessment and preserves all GEM JR/GEM FS/FA restriction associations.

## Operation

Visit `/scientific-assessment/batches`, enter the isolated review internal API key, and inspect the exact NCT identifier. An authenticated GET `/api/scientific-assessment?exact_id=TRIAL|NCT########` loads the archived ClinicalTrials.gov API v2 record only after validating gzip decompression, SHA-256 checksum, and exact NCT identity.

The response retains existing `registryEvidence` and `assessment` and adds `investigation20` with 20 ordered stages, each containing observed field paths, presence/count indicators, evidence limitations, source URL, and the date the archived snapshot was retrieved. The UI displays 20 collapsible sections so it remains manageable on iPhone/Safari. This is a historical archive view, **not** a real-time ClinicalTrials.gov refresh.

## 20 stages

1. Trial identity and protocol
2. Indication and disease context
3. Trial phase and development context
4. Timeline from trial start to filing
5. Eligibility and trial population
6. Treatment arms and comparators
7. Randomization and masking
8. Sample size and statistical power
9. Prespecified primary endpoints
10. Secondary and exploratory endpoints
11. Statistical analysis and multiplicity
12. Observed efficacy results
13. Safety and adverse events
14. Participant flow and missing data
15. Baseline balance and confounding
16. Mechanism and target validation
17. Biomarkers and subgroup coherence
18. Replication and publication review
19. Regulatory and manufacturing readiness
20. Integrated benefit-risk and PDUFA synthesis

## Interpretation and limits

- `registry_fields_present`: at least one relevant archived field exists. This is **not** scientific verification.
- `external_review_required`: independent sources or methodological review are necessary, even if some registry fields exist.
- `not_documented_in_archive`: the mapped fields are not present in this snapshot.
- `scientificallyVerifiedLevels=0`, `overallScore=null`, and `fdaApprovalProbability=null` by design. None of the 20 stages can promote an independent evidence assessment just because registry fields were found.
- Field paths refer to the precise object locations in the **archived JSON**. They are data provenance pointers, not direct links to independent peer-reviewed validation.
- Registry dates are study metadata. They must not be presented as a Phase 3 readout date, FDA submission date, PDUFA decision date, or positive outcome without separate confirmation.
- The existing independent six-domain scoring model remains evidence-gated and separate from GEM JR/GEM/WT screening classifications.

## Next step toward actual depth-20 analysis

For the **shortlisted GEM JR, GEM and WT** trials (not all ~11,000 registry trials), assemble a comprehensive review dossier with explicit source citations, versioned documents, results numerical extraction, adverse-event denominators, missing-data/multiplicity analyses, independent publications, label precedents, FDA documents, and a critical uncertainty register. Store auditable human-reviewed conclusions separately from the source-coverage counts. Never equate screening rank, mechanistic plausibility, or trial registry status with approval probability.

This rollout affects only the isolated review backend and UI. No production deployment, automatic batch, trading order, or existing FS/FA preset association is changed.

# Scientific Assessment — Two evidence grades

The isolated Scientific Assessment review panel includes two separate, auditable grades when inspecting an exact archived NCT ID. **Neither grade measures clinical success, probability of FDA approval, or the strength of a treatment effect.**

## Grade 1 — Analysis input readiness (A–F)

A letter grade reflects the proportion of **16 defined evidence-input requirements** documented in the checksum-verified archive and independent source-review workflow.

The 12 archival requirements are archive identity/integrity, indication, design/phase, eligibility, interventions/arms, enrollment, trial timeline, registered primary endpoint, posted primary estimate with uncertainty, safety counts and denominators, participant flow, and baseline characteristics. The four independent-review requirements are dated protocol/SAP reconciliation, complete published results/study report reconciliation, independent biological corroboration, and official agency/regulatory/CMC document verification.

The coverage thresholds are A ≥90%, B ≥75%, C ≥60%, D ≥40%, and F otherwise. This is **input coverage**, not performance; missing evidence reduces completeness but does not imply an unsuccessful study. Even a thorough archived registry posting cannot satisfy the final four independent requirements on its own. A full scientific conclusion is therefore **NOT READY** at this stage. The separate `passFail` means "the evidence-input checklist is incomplete," **not** "the trial failed its endpoints."

Each requirement contains a stable identifier, present/missing flag, source JSON path when applicable, evidence classification, and concrete next action. The output also records the rubric version and the archived snapshot timestamp.

## Grade 2 — Scientific reluctance (A–F scale, currently F)

Reluctance evaluates **whether the system should issue an efficacy or FDA success conclusion**. On the currently supported archive-only inputs, **F = critical reluctance / withhold the conclusion** because independent protocol, clinical, biological, and regulatory review is not loaded. It does **not** describe treatment failure, adverse events, market risk, or drug quality. Lower reluctance grades are intentionally unavailable until an audited independent-source ingestion and adjudication process exists. No unsupported optimism or fabricated certainty is allowed.

The two scores therefore need not match: a registry can have input-readiness grade B with reluctance grade F. This expresses a comprehensive registry record that is still insufficient for confident scientific judgment.

## Data integrity and security

Both grades derive from a previously archived source record read only **after** bounded gzip decompression, SHA-256 verification, and exact NCT identity checking. An invalid archive returns `readinessGrades=null`. The existing API key is required to read the panel; the key is not placed in page source, browser storage, or logs. No publication citation contained within a registry record can self-certify independent verification. No user-supplied field can mark independent evidence as reviewed.

The grade screen shows all 16 gates and the missing inputs. The review-only startup log emits a sanitized grade/checklist diagnostic without writing any trial scores or altering the PostgreSQL archive. Production scanners, trading systems and original GEM JR/GEM FS/FA preset relationships remain unchanged.

## Subsequent work

Implement a separate versioned independent-evidence ledger with exact references, source dates, conflicting findings, verification status, and reviewer attestation, then recompute verified readiness and caution grades. Pilot on the shortlisted **GEM JR, GEM and WT** population instead of all ~11,000 trials. A verified *scientific conclusion* remains a separate analytical process and must never be inferred from either evidence grade.

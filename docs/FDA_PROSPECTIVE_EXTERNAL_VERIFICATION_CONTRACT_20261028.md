# Prospective PDUFA prediction: external evidence contract

**Status:** RESEARCH ONLY — NOT READY. This document specifies acceptance requirements; it does not claim that any external service is connected.

## 1. Prediction freeze

- Serialize each prediction with exact trial/program identity, indication, model commit, evidence-manifest digest, PASS/CRL/EXTENSION/ABSTAIN label, and prediction cutoff.
- Verify that the frozen entry appears exactly once in the audited ledger, with the expected hash-chain head.
- Obtain an **external** timestamp attestation covering the ledger head or an unambiguous canonical digest of the frozen entry. Preserve the complete original receipt, signing certificate chain, issuer identity, timestamp policy, and verification result.
- A locally signed receipt with a self-declared date is **not** sufficient. An independently trusted time authority must prove issuance before the cutoff and before any relevant FDA outcome became public.
- Require receipt-to-entry binding and verify the trust chain, signature, certificate validity at the attested time, policy, and digest algorithm. Reject unverifiable, revoked, expired-at-signing, or mismatched receipts. Account for service outages by marking the forecast **UNVERIFIED**, not silently backdating it.

## 2. FDA outcome authentication

- Retrieve the primary FDA decision source from an authenticated official FDA channel or original FDA correspondence independently verified with the issuer. Preserve exact source URI, retrieval UTC time, response headers where available, raw bytes, SHA-256, and archival reference.
- Record explicit program/drug/indication/application identity and distinguish an approval, complete response letter, and documented action-date extension.
- An absence of an FDA approval listing is **not** evidence of a CRL. Sponsor press releases alone do not authenticate confidential FDA correspondence.
- Have a second reviewer confirm the label and decision date against the source. Preserve independently verifiable reviewer identity and signed review artifact.
- If FDA material is confidential or inaccessible, mark **OUTCOME_UNVERIFIED** rather than inferring the decision.

## 3. Prospective scoring boundary

- Include only frozen forecasts with independently verified predecision timestamp evidence and independently authenticated outcome records.
- Score PASS / CRL / EXTENSION separately. ABSTAIN counts toward coverage, not as correct or incorrect.
- Report denominators, class confusion matrix, coverage, calibration, and uncertainty intervals only after a sufficient genuinely prospective cohort is available.
- Historical cases may support retrospective research but **must not** be counted as prospective prediction accuracy.
- Never represent research-only hash chaining, local signature verification, or self-attested flags as independently trusted proof.

## 4. Required integrations (not installed)

1. Independently operated timestamp service with a documented trust root and immutable receipts.
2. Official FDA primary-source acquisition and document provenance verification.
3. Independent reviewer signing and decision-label adjudication.
4. End-to-end evidence fixture and negative tests for wrong trial, altered bytes, late receipt, untrusted issuer, revoked credentials, missing CRL, and outcome leakage.

**Deployment gate:** Keep validated accuracy and trading readiness **NOT READY / ABSTAIN** until all four integrations and a prospective cohort are independently audited. Preserve production and existing GEM JR/GEM FS/FA preset associations.

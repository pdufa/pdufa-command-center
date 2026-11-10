# MAIN Revision 79 — source-authenticity and blinded SAP-lock evidence acceptance gate

**Work date:** November 9, 2026 (Pacific). **Draft only:** [PR #965](https://github.com/pdufa/pdufa-command-center/pull/965). **Case:** Launch-HTN / NCT06153693 / MLYS, provisional lorundrostat NDA application-cycle `mlys-lorundrostat`.

## What R79 actually adds

R73–R78 established public published source documents, JAMA publication/printed SAP dates, paper-reported efficacy and H1–H7 methods, sponsor SEC public readout on March 10, 2025, and the reported December 22, 2026 PDUFA target. None contains independent sponsor-controlled final DB-lock and first-unblind timestamps or cryptographically verified original SAP custody. Published document images **are not proof of prospective lock**, even when their printed signature dates precede the public topline announcement.

**R79 adds a strict binary provenance requirement before treating prospective prespecification as authenticated.** It is separate from clinical efficacy/safety and does not produce a predictive numerical grade:

| Original source requirement | Source state | What could genuinely resolve it |
| --- | --- | --- |
| Original SAP controlled version 3.0 Amendment 2 bytes and SHA-256 provenance | Published imprint only, no original byte receipt | Controlled original PDF bytes, independent original custody receipt and SHA-256 |
| SAP finalization approval and audit log | Not obtained | Sponsor system audit showing approved original SAP version, approving signer authority and recorded timestamp |
| Final database-lock audit | Not obtained | Immutable source-controlled final lock record; distinguish soft locks |
| First actual access to unblinded treatment allocations | Not obtained | Audited first blind-break event, authorizer and access timestamp |
| Original SAP amendments / protocol version-controlled approval chain | Not obtained | Dated version history with traceable effect on H1–H7/missingness |
| Printed 2024 versus 2025 year discrepancy in addenda 5 and 7 | Not reconciled | Authenticated source-origin amendment records and controlled release audit |
| Independently trusted source custodian and statistical reviewer attestations | Not obtained | Distinct externally authorized public trust keys and signed record-integrity acknowledgments |

**Actual verified original requirements: 0/7.** Original seven PDF source byte receipts: **0/7**; approved trustworthy cryptographic signer keys: **0**. This does **not** mean the real sponsor did not lock its database, only that this project cannot independently authenticate these events from obtained source materials.

## Authority and chronological acceptance logic

- Original [FDA/ICH E9, §5.1](https://www.hhs.gov/guidance/sites/default/files/hhs-guidance-documents/FDA/E9-Statistical-Principles-for-Clinical-Trials.pdf): analysis planning may evolve during blinded review; final plan should precede unblinding; retain formal finalization and blind-break records.
- Original [FDA/ICH E6(R3), §3.16.2](https://www.fda.gov/media/169090/download): statistical programming, authorized post-unblinding changes, quality control and traceable audit records.
- **Key distinction:** final follow-up ≠ database lock ≠ first unblinding ≠ public SEC topline. The published dates may be consistent with a valid analysis plan but cannot independently establish its chronological authority.
- A SAP finalized *after* final database lock but *before* blind break is flagged for independent expert review, not automatically labeled fraudulent or a clinical defect; the regulatory guideline's core requirement is before breaking the blind.

## Implemented technical packet verifier

File: `new-platform/backend/scripts/verify_r79_sap_lock_provenance_packet.cjs`. The tool uses Node's native SHA-256 and Ed25519 public-key verification without adding a production dependency.

It requires the exact trial/application identity, three **original event-specific source byte buffers** and matching SHA receipts, recorded original SAP finalization, final DB-lock and first treatment unblinding timestamps, controlled SAP version and reconciled amendment chain, and cryptographic attestations under two **separately supplied externally approved** trust anchors from independent organizations (source custodian and statistical reviewer). Public keys are **not** accepted from the attestation packet and **no trust anchors exist in the deployed draft**.

It explicitly rejects any source digest mismatch, first unblinding preceding SAP finalization or database lock, cross-trial identity, missing amended-plan reconciliation, unknown or reused signing keys, same-organization signers, invalid/tampered signature, malformed timestamps, and absent original bytes. A fully synthetic **test** packet can produce at most `SIGNED_SOURCE_PACKET_COHERENT_NOT_CLINICALLY_APPROVED`; it **never** releases scientific grades or FDA outcomes. In particular, a technical signed packet by itself is **not** a signed independent clinical benefit-risk review or original sponsor custody. Sponsor-source evidence must be reviewed by qualified people before any clinical release.

Current research manifest `new-platform/frontend/data/focus-r79-launch-htn-sap-lock-evidence-gates.json` asserts all seven blockers and zero trust anchors; stricter frontend validator `new-platform/frontend/lib/focus-r79-launch-htn-sap-lock-evidence-gates.ts` fails closed if anyone changes missing states into a success claim without new independent provenance/release work. Read-only `LaunchHtnProspectiveSapGateR79.tsx` shows exact blockers within existing Launch-HTN evidence view only.

### Engineering acceptance and regression

- `new-platform/backend/tests/test_r79_sap_lock_provenance_packet.cjs`: generated **synthetic** Ed25519 trust keys used solely for tests; covers valid synthetic record consistency, missing source bytes/key anchors, altered byte/record, cross-NCT and same-organization signer attacks, and chronology rejection. No test key is deployed as an approved real reviewer.
- `new-platform/frontend/tests/focus-r79-launch-htn-sap-lock-evidence-gates.test.cjs`: checks 7/7 actual blocker IDs, all 0 certified counts and strict FDA ABSTAIN; adversarial evidence, clinical-grade and production-write attacks fail closed.
- `.github/workflows/main-r79-launch-htn-authentic-sap-lock.yml`: dedicated source integrity and typecheck/Next build acceptance in original draft only.
- Existing Chromium 1365-pixel desktop and 390-pixel mobile source-review workflow now opens the new R79 panel, counts all seven blockers and checks two cited official standards, no grade and visible ABSTAIN.

## Remaining scientific, regulatory and accuracy limits

No original fully signed pre-unblinding SAP has been authenticated; no first unblinding or final lock log supplied; no source-level independent H1–H7/alpha/1000-imputation replication, safety/CMC signed review or blinded historical FDA accuracy audit completed. Current independent reviewed clinical grades **0**, validated FDA forecasts **0/23**, calibrated accuracy **unavailable**, future approval/CRL **ABSTAIN**, timing forecast **UNKNOWN**. No production deploy, automatic trade, source roster mutation, retired scoring revival or false medical-grade release.

**Next real scientific step:** obtain and independently authenticate sponsor-controlled SAP versions and original lock/blind-break audit logs, then run R79 against those real bytes and externally approved signer keys; independently adjudicate temporal and statistical materiality before any certified FDA application opinion.

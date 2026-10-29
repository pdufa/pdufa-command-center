# Genuine RFC 3161 timestamp integration fixture

The test in `tests/test_fda_rfc3161_real_token_integration.py` is **opt-in**. A skipped test means **no external evidence has been validated**.

Provide the following five environment variables from a trusted test fixture:

- `PDUFA_TSA_TOKEN_DER_FILE`: path to DER-encoded RFC 3161 token.
- `PDUFA_TSA_TRUSTED_CA_PEM_FILE`: path to a reviewed TSA trust bundle.
- `PDUFA_TSA_CA_BUNDLE_SHA256`: pinned SHA-256 digest of the exact trust bundle bytes.
- `PDUFA_TSA_EXPECTED_IMPRINT_SHA256`: digest of the exact frozen prediction payload represented by the token.
- `PDUFA_TSA_TEST_CUTOFF_UTC`: documented prediction cutoff, later than the token generation time.

Verify the trust bundle's provenance independently of the token supplier. Preserve issuer, policy OID, revocation evidence, issuance date, exact token bytes, and digest binding. An arbitrary PEM file plus a matching local pin is not independently trusted. Never use live credentials in repository fixtures.

The test checks cryptographic validity and token time with OpenSSL; it does **not** independently establish the issuer's operational trust, validate the full policy and revocation history, authenticate FDA outcomes, or authorize prospective accuracy reporting.

**Readiness remains NOT READY / ABSTAIN until independent audits and genuine prospective outcomes are complete.**

# ZEVASKYN original FDA source observations — October 27, 2026 Pacific

Status: connected-tool document text examined; independent review and original-byte
retention incomplete. These observations extend the earlier
`docs/outcome_fda_bl125807_abeona_primary_source_2026-10-26.md` review. They do not
populate an independently verified outcome cohort or a predecision feature set.

| Official source | PDF page | Observation |
| --- | --- | --- |
| [FDA CRL](https://download.open.fda.gov/crl/CRL_BLA125807_20240416.pdf) | 1, 9 | BL 125807/0, Abeona, prademagene zamikeracel; action dated April 16, 2024. A partial reply cannot restart a review cycle. |
| [FDA approval](https://www.fda.gov/media/186513/download) | 1 | Same published STN and sponsor; approval dated April 28, 2025. The letter lists four associated NCTs without identifying all their roles. |
| [FDA regulatory action summary](https://www.fda.gov/media/186796/download) | 1, 4, 6 | BLA 125807/0; original receipt September 25, 2023; CRL April 16, 2024; resubmission October 28, 2024; action due April 29, 2025. |

The summary supplies an FDA source for the resubmission previously supported only
by a sponsor SEC statement. Its retrospective account supports separate action
observations. It cannot make the later approval a substitute for the earlier CRL,
nor establish public availability before either action. The sources' document
dates differ from their unknown publication dates. Preserve both printed STN
forms; this single cross-reference does not justify normalizing every legacy BL
identifier across the archive.

Observed source documents: **3**. Observed action headings: **1 approval, 1 complete
response** for **1 selected application**. Independently verified eligible PASS
cycles: **0**; FAIL cycles: **0**; model-eligible records: **0**. These counts concern
this intake only, not FDA's full decision population. No model metric or accuracy
estimate is available.

The JSON observations explicitly leave cycle ordinal, original publication dates
and original-PDF SHA-256 unknown. The JSONL action queue deliberately retains null
cycle/publication fields and therefore fails eligibility checks in the staging
audit. Nulls must be filled from independent source adjudication, not guessed from
the number of letters. The manifest can request original PDFs when authorized
access becomes available. Connected-tool extracts are not original PDF bytes.

Executed checks:

```bash
python scripts/ingest_fda_documents.py research/fda/zevaskyn-document-manifest-20261027.json --mode download
python scripts/audit_fda_decisions.py research/fda/zevaskyn-action-observations-20261027.jsonl --as-of 2026-10-27
```

Manifest dry-run validates three source URLs without fetching or certifying them.
A real CLI download attempt failed with
`Tunnel connection failed: 403 Forbidden`; no archive was created. The connected
research tool successfully opened all three exact FDA PDF URLs. No proxy or
network-policy bypass was attempted.

Next: retain original documents through the supported network configuration or
reviewed offline exports, independently adjudicate action/cycle/indication identity
and publication chronology, and obtain original dated predecision scientific
features. The prior CRL can become a feature for a later cycle only if its public
availability before that later prediction cutoff is separately established.

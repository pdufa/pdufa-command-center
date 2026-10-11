# First-ten SEC financing audit

This audit extends the existing `sec_step4.py` and `sec_financing_closure.py` process. It **does not overwrite** `data/second_financing_status.csv` or the Streamlit trading dashboard.

## Batch and interpretation

The first 10 rows of `data/second_financing_status.csv` form a reproducible validation batch: BFRI, SRRK, IRD, VTRS, IONS, INO, AGIO, CYTK, SMMT and CAPR.

Five rows have a previously researched second-financing source URL; five do not. Historical labels such as `VERIFIED_SECOND_POST_PHASE3_FINANCING` are carried through as *prior research claims*, not promoted to fresh independent verification.

Outputs always contain:
- the exact event key, registered issuer CIK and SEC source URL;
- the existing research label and claimed closing date;
- SEC retrieval result and SHA-256 of any fetched document;
- a possible closing excerpt for human review, if detectable;
- `independent_closure_verified=NO` and `entry_ready=NO` until separately verified in the existing reviewer-attestation and entry-gate workflows.

The source checker requires issuer-matched official SEC archive URLs. It refuses unmatched or missing issuer identity; it does not infer a financing close from a prospectus, filing metadata, 10-Q/10-K mention, or lack of a response.

## Run locally

```bash
python -m unittest discover -s tests -p 'test_financing_first10_audit.py' -v
python scripts/financing_first10_audit.py --output output/first10_financing_audit.csv
```

Offline is the default. To attempt a genuine SEC check, configure a descriptive User-Agent with **your own valid contact address** (never a fake placeholder) in the `SEC_USER_AGENT` environment variable:

```bash
python scripts/financing_first10_audit.py --live --output output/first10_financing_live.csv
```

For GitHub Actions, add `SEC_USER_AGENT` as a repository secret and manually launch **SEC First-Ten Financing Audit** with `live_sec_check=true`. The batch report is retained as a workflow artifact for 30 days. The workflow runs offline safety tests on matching development branches.

## Access denied

A 403 means *SEC access failed*. It never means a financing is closed or absent, and this script never retries a 403 from another IP or proxy. Check the real User-Agent, SEC fair-access policy, and request rate. If access remains denied, contact `webmaster@sec.gov` with error details and IP as advised by the SEC. The tool uses one request per issuer document and a half-second pause between requests. It intentionally makes no claim that this eliminates IP-level blocking.

## Next checkpoint

Only after source text and the original first/second post-readout financing sequence are reviewed and documented should the specific named financing gate be allowed to pass. Separate checks remain necessary for current ATM/dilution, Phase 3 clinical evidence, PDUFA identity/date, cash runway and post-readout price stabilization. Never mark an entry READY from SEC retrieval alone.

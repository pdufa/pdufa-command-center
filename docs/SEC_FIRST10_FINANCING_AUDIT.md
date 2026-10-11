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


## Initial document-level spot checks (October 10, 2026)

These are human-readable research leads, not automatically accepted certification or ENTRY READY decisions.

| Issuer | Source-level finding | Follow-up |
|---|---|---|
| BFRI | [SEC Exhibit 99.1](https://www.sec.gov/Archives/edgar/data/1858685/000149315225019006/ex99-1.htm) says the asset purchase closing released the final $2.5M of an $11M financing; do not treat the asset acquisition closing alone as a new financing. | Reconcile the separate original convertible-note financing and later capital funding as two distinct post-readout transactions. |
| SRRK | [2026 10-Q](https://www.sec.gov/Archives/edgar/data/1727196/000110465926056667/srrk-20260331x10q.htm) reports receipt of $50M from a next tranche on September 29, 2025. | Check whether a tranche of an existing loan counts as a *second separate financing* under the strategy's definition. |
| IRD | [2025 10-K](https://www.sec.gov/Archives/edgar/data/1228627/000114036126009247/ef20060643_10k.htm) explicitly states a $25M private placement closed February 18, 2026. | Independently check first-financing event and mapping to the correct program. |
| CYTK | The linked [8-K](https://www.sec.gov/Archives/edgar/data/1061983/000119312526214606/d138544d8k.htm) describes underwriting and is signed May 8; the signature date is **not** itself closing proof. A separate [company announcement](https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Closing-of-Public-Offering-of-Common-Stock-and-Full-Exercise-of-the-Underwriters-Option-to-Purchase-Additional-Shares-for-Gross-Proceeds-of-805-Million/default.aspx) explicitly confirms the $805M offering closed May 8, 2026. | Replace or supplement the current proof with explicit closing evidence and independently assess the ordered first/second financing chain. |
| SMMT | [2026 10-Q](https://www.sec.gov/Archives/edgar/data/1599298/000159929826000068/smmt-20260630.htm) says an October 2025 private placement was completed, but also reports 2026 ATM sales and remaining ATM capacity utilized after June 30. | Keep ATM/dilution risk as a separate **unresolved** entry gate regardless of completed PIPE. |

The GitHub Actions report is still intentionally conservative: it requires compliant direct SEC retrieval and human review, even where a publicly accessible document appears to corroborate a historical claim.

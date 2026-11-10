# MAIN Revision 27 — alternative public evidence recovery and controlled access route

**Pilot:** ACACIA-HCM / NCT06081894 / CY 6033. **Evidence-check date:** November 9, 2026 UTC. **Deployment scope:** isolated draft PR #965; no production clinical-code changes.

## Actual alternative retrieval results, not an assumption of document absence

Installed the standard-library-only, read-only runner `scripts/medical/acacia_alternative_public_evidence.py` and 9 regression tests. It attempts source retrieval from three fixed, allowlisted public research URLs, checks exact article identity when reachable, and archives only time, source URI, retrieval status, bytes, SHA-256 and narrowly validated source facts. It never preserves copyrighted full-text article bytes or offers clinical score writes.

[GitHub Actions source audit #42556948533](https://github.com/pdufa/pdufa-command-center/actions/runs/42556948533) **SUCCESS** after an XML article-title parser fix. Nine offline tests passed. Exact real-world results were **UNAVAILABLE** for the NEJM article landing endpoint, Europe PMC responder full-text XML endpoint, and Europe PMC echo full-text XML endpoint. Archived metadata-only artifact: **13648026480**, receipt SHA-256 `79aef1d6785acf06b65976aea075f7d0c0e12554d241dc335dbc4460069059a8`. This is **not proof that these public manuscripts or supplements are absent**; independent web indexes list them, but the isolated GitHub runner could not retrieve their content.

### Public research leads, with explicit source strength

- [Original pivotal NEJM article DOI](https://www.nejm.org/doi/10.1056/NEJMoa2603021) **lists** an original protocol supplement, a supplementary appendix, and the [data sharing statement](https://www.nejm.org/doi/suppl/10.1056/NEJMoa2603021/suppl_file/nejmoa2603021_data-sharing.pdf). A publisher *listing* is not byte-verification of a **final dated locked primary SAP** or independent original sensitivity results.
- [Secondary responder paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC13674601/) reports that the multidomain responder analysis was included in a statistical analysis plan before lock/unblinding and describes use of the last available observation (weeks 8–36) and classification of those without post-week-8 observations as nonresponders. This supports a **specific secondary responder methodological description**, not confirmation that the primary co-primary estimands, multiplicity testing and all sensitivity analyses were independently reproduced.
- [Secondary echocardiography paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC13674599/) is another public same-trial research source. It is not a substitute for an authenticated original primary SAP or a complete HF adverse-event case list.
- [October 12 Cytokinetics safety disclosure](https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Additional-Data-from-ACACIA-HCM-Presented-at-the-HFSA-Annual-Scientific-Meeting-2026/default.aspx), retrieved by the **previous** original-source audit #42555289486, describes 2 LVEF-associated treated HF events + 10 additional treated HF serious events = **12 treated versus 3 placebo**. It does **not** explain the separate secondary paper's **11/1** event count without matched definitions, analysis windows and event-level original data.

### Published data-access pathway (not a data handoff)

The study's published [data sharing statement](https://www.nejm.org/doi/suppl/10.1056/NEJMoa2603021/suppl_file/nejmoa2603021_data-sharing.pdf) directs qualified researcher submissions to **medicalaffairs@cytokinetics.com**, with a committee review, data-sharing terms and restrictions tied to US/Europe marketing-authorization decisions. It states data availability beginning **24 months after study end**. Any source request must meet the sponsor's actual eligibility and timeline; an inquiry does not imply entitlement to confidential data. **No email or source request was sent.**

## Installation work

- `scripts/medical/acacia_alternative_public_evidence.py`, `tests/test_acacia_alternative_public_evidence.py`, and branch-only GitHub workflow `.github/workflows/main-acacia-alternate-public-evidence.yml` record explicit source reachability without making unsupported research/clinical claims.
- The signed-in PREDICTIONS Phase III review worklist now has a new expandable **Alternative source recovery** section and metadata in its GET-only JSON API: archived audit run, exact source statuses and published source links, qualified researcher contact, `automaticRequestSent=false`, final locked SAP `false`, primary sensitivity `false`, HF event discrepancy `false`. The workflow does not send mail or authorize evidence submission.
- The original 18 queue entries, five bounded research checklists/calculations, 13 source-only leads and 782 unmapped method positions are unchanged. Exactly **0/800** authorized pilot scientific grades, FDA **ABSTAIN**, prediction accuracy **NOT CALIBRATED**. No original phase signoffs or reviewer events.

## Next substantive scientific gates

1. Access and independently verify the actual dated final locked CY6033 primary SAP; determine original hypotheses, estimands and analysis amendments.
2. Acquire fully reported primary missingness/sensitivity/CONSORT evidence and compare against prespecified handling.
3. Obtain event-level source definitions, windows, safety population and time-at-risk for conflicting HF SAE reports, plus corrected interruption denominators.
4. Route source packets through qualified independent reviewer signoffs before any 0–5 method grade.
5. Expand phase-first reviewed methods and finally calibrate an FDA outcome model against independent historical cases.

**Never interpret automated network access failures as evidence that the underlying trial records do not exist or fail scientific criteria.**

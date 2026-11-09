# MAIN Revision 21 — pilot source history and staged nightly check

Date: November 8, 2026 (Pacific). Exact research trial: ACACIA-HCM / NCT06081894 / CY 6033. Draft PR #965.

## Verified installation

A one-trial public-source monitor uses Python standard library and two fixed original-source indexes: [ClinicalTrials.gov exact study](https://clinicaltrials.gov/api/v2/studies/NCT06081894) and [Europe PMC original pivotal paper](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID%3A42663312&format=json&pageSize=5). It checks exact identity, fails closed for malicious source substitutions, bounds JSON to 350 KB, rejects redirects, and never calls a clinical grade, forecast, or production write endpoint.

Every run produces a JSON receipt with UTC observation time, repository SHA, SHA-256 source digests, source-status classification, any new registry results or SAP-title *candidate* findings, and the three dated documentary-readiness checklist calculations (5.1=3/5, 4.2=3/5, 5.3=2/5). The receipt includes its own SHA-256 and links to a previous receipt only if that previous source list, URLs, statuses and digest pass validation. A changed source fingerprint requires research review; it is not scientific proof or FDA probability.

## Actual archived runs

- [Run 42549064100](https://github.com/pdufa/pdufa-command-center/actions/runs/42549064100) — first MATCH/MATCH, 9 regression checks pass, artifact 13644038318.
- [Run 42549164875](https://github.com/pdufa/pdufa-command-center/actions/runs/42549164875) — confirms PREVIOUS_VALID, hash-linked prior receipt, MATCH/MATCH and no changed public-source digests; artifact 13644876475.
- [Run 42549195926](https://github.com/pdufa/pdufa-command-center/actions/runs/42549195926) — confirms later source-history validation tests passed.

The GitHub Actions workflow retains source receipt artifacts for up to 90 days. The PREDICTIONS screen links the run archive via an expandable section. The latest private backend scientific ledger has **0/800 authorized clinical method grades**, FDA APPROVAL/CRL/REVIEW_DELAY **ABSTAIN**, and accuracy **NOT CALIBRATED**.

## Critical activation boundary

The workflow includes a proposed nightly 8:17 PM America/Los_Angeles schedule. GitHub Actions schedule events only run on the **default branch**, currently main. The workflow exists only on the draft MAIN feature branch, so its nightly schedule is **NOT ACTIVE**. Push-triggered source checks are real, but they are not unattended daily runs. Activation requires separate review and explicit approval to promote *only the isolated public research workflow*, without merging the unfinished draft app or changing production. Even after activation, first actual schedule-triggered run must be verified.

The on-view 15-minute source checks remain separate. These probes do not automatically retrieve and adjudicate new signed SAPs, regrade any of the 800 methods, update 29 FOCUS trials, or generate FDA predictions. The final CY 6033 locked SAP, discrepant serious-HF event definitions, clinical reviewer signoffs and FDA model calibration remain outstanding.

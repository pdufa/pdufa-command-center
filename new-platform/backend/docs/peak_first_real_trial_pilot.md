# PEAK: first source-dated Phase 3 batch research pilot (27 Oct 2026)

**Scope:** A reproducible, read-only source-announcement case for the new FastAPI batch endpoint. Not a complete scientific assessment, FDA-cycle certification, probability model, or trade recommendation.

## Exact case and dates

- Trial identity: `COGT|NCT05208047|BEZUCLASTINIB+SUNITINIB|GIST-POST-IMATINIB`.
- May 28, 2026: Cogent reports the FDA accepted the GIST NDA with priority review and assigned **November 30, 2026** as the PDUFA target date. This is a **company announcement of an FDA assignment**, not direct FDA action-letter adjudication. Source: https://investors.cogentbio.com/news-releases/news-release-details/cogent-biosciences-announces-fda-acceptance-new-drug-0
- May 30, 2026: Cogent publicly releases detailed Phase 3 PEAK results at ASCO. Source: https://cogentbiosciences.gcs-web.com/news-releases/news-release-details/cogent-biosciences-announces-detailed-clinical-data-peak-phase-3
- Source review cutoff: **October 27, 2026**. Both public disclosures are earlier than cutoff. The gate allows **research to start**, not an FDA decision or trading.
- Trial's GEM JR/GEM/WT membership is intentionally **not inferred**. The fixture carries an empty list and cannot modify FS/FA presets.

## Expected outcome / limits

1. Source-announcement eligibility: yes, for the two reviewed public reports; pre-May 30 snapshot: no.
2. SCIENCE: **0 independently reviewed evidence questions** in this fixture. The current API's independent-investigation catalog is **not yet the planned 40-assessment clinical dossier**. `science.required` reports its actual implementation count; don't substitute that for 40.
3. OUTCOME and MAIN: no conclusions or approval probabilities. Historical FDA cycles and exact FDA receipt/cycle have not been independently adjudicated.
4. Sheet population: **PREVIEW_ONLY**, `writtenToSheet: false`, `readinessGrade: NOT ASSESSED`, `approvalProbability: null`.
5. Trading: `tradeAuthorized: false`. No scanner/scheduler activation and no production list membership changes.
6. `review_status: VERIFIED` in this fixture means that a named dated public disclosure was manually checked; it is **not an independently adjudicated FDA cycle**, and the API currently trusts this caller assertion. An upstream source-review control is still needed before accepting untrusted scanner rows as verified.

## Verification

Offline, from repository root:

```sh
python -m pip install -r new-platform/backend/requirements.txt
PYTHONPATH=new-platform/backend python -m pytest -q new-platform/backend/tests/test_phase3_real_trial_peak.py
```

Authenticated live smoke from an authorized environment **with the key already injected securely**:

```sh
python new-platform/backend/scripts/smoke_real_trial_readonly.py
```

Use `--empty` for the empty batch. The smoke script obtains the key only from `PDUFA_INTERNAL_API_KEY`, never prints it, verifies PostgreSQL readiness, requests a batch, checks exact identity and PREVIEW_ONLY response, and fails on any unsupported probability or write claim. Never paste keys into chats, terminal history, CI logs, or public issue comments.

The offline test is not proof that the live API accepted the PEAK candidate; report those two checks separately.

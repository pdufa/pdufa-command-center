# URGN / UTOPIA exact-NCT source verification (2026-11-17)

ClinicalTrials.gov identifier **NCT06331299**; UGN-103 intravesical
mitomycin for recurrent low-grade intermediate-risk non-muscle-invasive
bladder cancer. The independent NCI listing confirms trial identity and the
primary endpoint, 3-month complete response.

## Sources and report dates

- May 15, 2026: UroGen press release reports six-month conditional
  response durability (94.5%, 95% CI 86.1–97.9) for initial complete
  responders and describes the UTOPIA single-arm design. This is
  sponsor-reported, **not independent comparative efficacy**.
  https://investors.urogen.com/node/11591/pdf
- May 27, 2026: Original JCO/ASCO 2026 abstract, DOI
  10.1200/JCO.2026.44.16_suppl.4604, explicitly identifies NCT06331299.
  https://ascopubs.org/doi/10.1200/JCO.2026.44.16_suppl.4604
- October 19, 2026: UroGen announces the FDA **accepted** an NDA for
  UGN-103 for review and assigned a **June 14, 2027** PDUFA action date.
  https://urogen.gcs-web.com/news-releases/news-release-details/urogen-announces-fda-acceptance-new-drug-application-ugn-103
- November 2026: The company's SEC 10-Q confirms that the August filing
  was accepted in October, for the same indication and trial, with the
  June 14, 2027 target date.
  https://www.sec.gov/Archives/edgar/data/1668243/000143774926034780/urgn20260930_10q.htm
- NCI exact trial registry identity:
  https://www.cancer.gov/research/participate/clinical-trials-search/v?id=NCI-2025-00695

## Important distinctions

77 of 99 patients (77.8%, 95% CI 68.3–85.5) are reported as achieving
three-month complete response. The six-month 94.5% Kaplan–Meier durability
estimate is *conditional on having a three-month complete response*;
it is NOT a 94.5% response rate out of all 99 patients. Historical study
estimates and product ENVISION comparisons are not a randomized direct
control arm of the single-arm UTOPIA study.

An accepted NDA is not approval. No FDA original acceptance letter,
NDA application number, approval decision, clinical adjudication, score, or
calibrated success probability is established here. Source disclosures
must be cutoff-date screened for blind backtesting. Data are development-
only, without automatic production updates.

Research record: research/source-links/URGN-NCT06331299-UTOPIA-NDA-source-audit-2026-11-17.json


## Primary result cross-check against archived official registry

The independently preserved ClinicalTrials.gov API-v2 packet for NCT06331299
was downloaded as part of the successfully completed raw POOL recovery
workflow 44120924177 (artifact 14349176150). Its canonical JSON SHA-256
is 15eac8f0c55e3eff205f89feb67f3177f0166af88bb30412621e44da6064c0ad.

The October 22, 2026 registry snapshot lists trial status COMPLETED, primary
completion September 11, 2025, study completion September 15, 2026, and
results first posted September 28, 2026. Its original PRIMARY measure is
the 3-month complete response rate of **77.8% (95% CI 68.3–85.5), N=99**,
matching the sponsor-reported primary figure.

**Critically, the registry secondary outcome for Duration of Response in
3-month responders is marked NOT_POSTED.** The sponsor's conditional
six-month DOR Kaplan–Meier estimate (94.5%) must be shown with sponsor
provenance, rather than mislabeled as a posted ClinicalTrials.gov secondary
result. No independent clinical/statistical validation has been completed.

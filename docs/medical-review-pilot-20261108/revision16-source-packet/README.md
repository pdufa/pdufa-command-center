# ACACIA-HCM: additive reviewer-ready source packet, revision 16

Exact trial: **NCT06081894 / CY 6033 / ACACIA-HCM / symptomatic nonobstructive HCM**.
Built from Revision 15 (`415debd9e2722a058b5d6b5d6c0a4835e5bdba43`) and its
preserved source history. No earlier source, finding, reviewer event or roster
entry is replaced. This packet is research preparation, not a database import,
independent clinical adjudication, signed phase event or grade.

The [800-position register](reviewer-ready-800-positions.json) enumerates every
installed assessment/method question, phase-first priority, source requirement,
known source lead, limitation and reviewer dependency. It preserves the prior
15 candidate lead positions and adds three targeted source-quality handoffs
(4.3:4, 5.4:4, 8.2:4). **18 handoff positions and 782 unexamined positions** do
not mean 18 graded or completed scientific tests. All 800 official grades and
all numerical grading recommendations remain null. The current independently
verified phase is still absent, and the authorized review gate is unsatisfied.

## New original sources obtained

The [receipt manifest](retrieval-manifest.json) preserves seven successful
responses with exact URL, retrieval time, byte count and SHA-256: two new
same-trial conference PDFs, the sponsor publication index, three FDA responses,
and one official Colombian trial record. An official Japanese registry request
returned 403 and is recorded separately. No confidential CSR or patient-level
listing was obtained or represented as publicly obtainable.

| Source | Publication/version | Exact scope and limitation |
| --- | --- | --- |
| [CMR presentation](https://cytokinetics.com/wp-content/uploads/2026/11/Masri_2026_HCMS_ACACIA-HCM-CMR.pdf) | Sponsor index: HCMS oral presentation, Nov 6, 2026. Retrieved PDF created Nov 7; 14 pages. | ACACIA same-trial imaging subset, not independent replication; original PDF preserved. |
| [Patient-reported-health presentation](https://cytokinetics.com/wp-content/uploads/2026/11/AHA-HCMS26-ACACIA-KCCQ_PRO-oral_final.pdf) | Sponsor index: HCMS oral presentation, Nov 6, 2026. Retrieved PDF created Nov 7; 17 pages. | Same-trial secondary health-status analysis; does not replace pivotal endpoints or authenticate the final SAP. |
| [FDA label](https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/219083s000lbl.pdf) | Revised December 2025 | NDA 219083 original obstructive-HCM indication; regulatory context only for this nHCM pilot. |
| [FDA trial snapshot](https://www.fda.gov/drugs/drug-trials-snapshots/drug-trials-snapshots-myqorzo) | Approval described: Dec 19, 2025 | Explicitly SEQUOIA-HCM / **NCT05186818**, 282 patients with obstructive HCM. Cannot establish ACACIA approval or its safety denominator. |
| [openFDA application index](https://api.fda.gov/drug/drugsfda.json?search=products.active_ingredients.name:%22AFICAMTEN%22&limit=100) | Index last updated Nov 6, 2026 | NDA219083 original approval and REMS supplement listed. Pending/confidential supplements need not appear; no inference that an nHCM submission does not exist. |
| [INVIMA clinical-trial record](https://www.invima.gov.co/estudio/20241173982-un-estudio-multic%C3%A9ntrico-aleatorizado-doble-ciego-de-fase-3-para-evaluar-la-eficacia-y-s) | Administrative act March 14, 2025 | Matches NCT06081894 and CY6033. Clinical-trial authorization is not Colombian marketing approval, global completion or FDA approval. |

## Findings prepared for independent review

CMR PDF pages 4–7 identify 69 enrolled and 61 paired scans (25 aficamten, 36
placebo). Reported LVMI and wall-thickness differences favor treatment; other
imaging measures are nonsignificant. Selection, incomplete paired imaging,
precision and the surrogate nature of these measures limit inference. The
original page-6 graph and numbers were visually checked after rendering.

The health-status PDF reports **KCCQ-OSS** +4.0 points at week 36 (95% CI
1.6–6.5), which must remain separate from pivotal **KCCQ-CSS** +3.0. Its methods
require baseline plus a follow-up measurement; secondary comparisons lack
multiplicity adjustment. It explicitly says responder thresholds were not
directly established in nHCM. Week-36 symptom and angina comparisons include
zero in their confidence intervals; later variable-time end-of-treatment
findings do not replace those comparisons. Methods page 7 and results page 11
were visually checked. These are source-reported supportive analyses, not a
new clinical verdict or proof of final SAP compliance.

The structured register records nine bounded findings, precise source pages,
classification, and methodological limits. FDA evidence strengthens the
**cross-indication exclusion**: an obstructive-HCM approval cannot be copied to
this nonobstructive-HCM application. The source-specific heart-failure SAE
11/1 versus 12/3 and interruption-numerator questions remain unresolved;
these new presentations do not provide the missing original event listings.

## Remaining source and reviewer dependencies

- Final signed/locked **CY 6033** SAP, complete primary appendix, earliest
  amendment effective date, database-lock/unblinding chronology and official
  v26/v27 registry field-level comparison remain unverified. The previously
  obtained 90-page Amendment 04 protocol is preserved and was not downloaded
  again or relabeled as the SAP. Wrong-trial CY6031 SAP remains excluded.
- Original participant accounting, safety populations/windows and serious-event
  listings remain necessary; a publicly inaccessible CSR is not a failed trial.
- Exact nHCM filing/acceptance is not established by the Nov 4 issuer disclosure,
  the original oHCM FDA approval or another indication's PDUFA date.
- The official [jRCT lead](https://jrct.mhlw.go.jp/latest-detail/jRCT2031250066)
  was identified, but direct retrieval returned 403. No Japanese cohort values,
  protocol crosswalk or phase confirmation are claimed from inaccessible text.
  [ANZCTR](https://www.anzctr.org.au/Trial/Registration/TrialReview.aspx?id=23472&isClinicalTrial=True)
  explicitly imports ClinicalTrials.gov and is not independent corroboration.
- Qualified independent reviewer authorization, current phase-event verification
  and method-specific adjudication remain mandatory before official grades.
  This packet creates **0 phase events, 0 database audit receipts, 0 method
  grades and 0 completed scientific assessments**. FDA APPROVAL, CRL and delay
  remain **ABSTAIN**; certainty **NOT_VALIDATED**, accuracy **NOT_CALIBRATED**.

Validation: `python docs/medical-review-pilot-20261108/revision16-source-packet/verify_packet.py`.
This checks preserved byte receipts, exact 40×20 coverage, unique identifiers,
source references, current catalog digest and null grades. It verifies packet
integrity, not independent clinical signoff. No live database or production
service was written.

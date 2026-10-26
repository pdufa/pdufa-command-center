# FDA original-submission source discrepancy reconciliation — October 25, 2026

**Status:** actual FDA source membership reconciled, regulatory decision-cycle
denominator still unknown. All records remain quarantined from PDUFA/GEM/WT
historical prediction training and live scoring.

## The difference is one specific original-submission record

The research workflow
[40252457591](https://github.com/pdufa/pdufa-command-center/actions/runs/40252457591)
reused **both pinned, actual historical source files**:
the 2026-10-25 FDA tabular Applications/Submissions archive and the saved
OpenFDA Drugs@FDA approval-centric registry artifact
[12611090768](https://github.com/pdufa/pdufa-command-center/actions/runs/40224730350/artifacts/12611090768).

The workflow compared **NDA/BLA application ID + ORIGINAL submission number**
and retained a small, audited result in
[artifact 12620868565](https://github.com/pdufa/pdufa-command-center/actions/runs/40252457591/artifacts/12620868565)
with public aggregate counts and the single mismatching public application ID.
Raw FDA table rows and the original registry JSON were **not** uploaded by
this new workflow.

| Cross-source comparison | Observed count |
|---|---:|
| Tabular original NDA/BLA submission keys | **6,033** |
| Saved OpenFDA original NDA/BLA submission keys | **6,032** |
| Shared exact original submission keys | **6,032** |
| Tabular-only original submission keys | **1** |
| OpenFDA-only original submission keys | **0** |
| Shared-key raw status-code differences | **0** |
| Shared-key raw status-date differences | **0** |

The **single unmatched tabular original key** is
`NDA206627, ORIG 1`. The **entire NDA206627 application record** is absent from the saved OpenFDA registry artifact; it is not merely a present application whose original-submission row was omitted. The reconciliation distinguishes both types of source omission and reports one whole-application absence versus zero missing-original-only entries. The difference is not 1 FDA denial, one additional
verified regulatory cycle, one additional PDUFA target, or evidence of a
missing drug that was never approved. No source-date or status difference
appeared in the 6,032 overlapping original submission entries.

This also explains the one-entry difference in *distinct original application
counts*: the tabular file describes 5,973 applications, while the OpenFDA
artifact has 5,972. The published PDF letter review universe is another,
separately incomplete and differently sourced set of evidence.

## Independently discoverable FDA primary-source review lead

FDA publishes an
[original approval package for NDA 206627 / Original 1](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2014/206627Orig1s000Approv.pdf).
The title page names Hysingla ER, hydrocodone bitartrate, Purdue Pharma L.P.,
and gives the original FDA **approval date November 20, 2014**. The
included original action letter identifies NDA 206627 and states approval
effective on its letter date. The cited pages appear at PDF page indices
0 and 3 (zero-based). This is a concrete public evidence lead for a source
coverage discrepancy; it is not yet a signed *independent human* adjudication
of the exact regulatory review-cycle chronology and cannot be used as a
released training label.

There is **no indication from this comparison** that the 6,033 published
source submissions represent 6,033 complete, unique historical NDA/BLA FDA
review cycles. The official tabular export and OpenFDA source are different
representations, and archival selection may explain missing rows. Treat both
as approval-centric; never estimate nonapproval frequencies from these.

## Reproduce the comparison

The pinned comparison source fingerprints are:

- Official FDA tabular Applications.txt:
  `f7fc18dcc826b74b250f7c87d1d9e4b04b56207fc9eac882801a64745a388dd6`
- Official FDA tabular Submissions.txt:
  `d74236b31ebe27ce80f529c6d7b6921f9ca95029d91fd92a30bdd95aaf0b3d00`
- Saved OpenFDA approved registry JSON:
  `adb24d7921d56bc3824b57e785164a32287efc69a9d3fe9b940da97f6c65f5b2`

From the repository's official-source research workflow, the new
`scripts/reconcile_hop_drugsfda_original_sources.py` audits those pinned
source table bytes and the saved JSON. The script rejects source version,
scientific status, duplicate key, schema, or sample-consistency tampering,
then publishes only a bounded discrepancy inventory. Its synthetic regression
tests and the real-result regression pin enforce no outcome/model promotion.

**Outstanding scientific gates**: independently adjudicate the original
FDA record and broader regulatory action-cycle source history; recover the
complete original NDA/BLA population including never-approved and
nonapproved cycles; establish exact public predecision trial evidence
cutoffs; run out-of-time calibration and validation. Every result remains
`REVIEW_REQUIRED`, with **0 independently verified review cycles, 0
model-eligible records, and approval rate/probability/accuracy unavailable**.

Preserve the existing GEM JR/GEM FS/FA restrictions and functionality;
no production deployment, scanner changes, trades, or new probability
display is authorized by this research reconciliation.

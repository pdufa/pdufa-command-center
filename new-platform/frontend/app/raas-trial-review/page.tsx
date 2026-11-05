/** Saved research dossier for an exact clinical trial, never an approved RAAS grade. */
import type {Metadata} from "next";
import Link from "next/link";
import registry from "../../public/raas-registry-evidence-index.json";
import {buildTrialMetricReviewDossier}
 from "../../lib/raas-trial-metric-review-dossier";
import ReviewDossierClient from "./ReviewDossierClient";
import RaasWorksheetPreflight from "./RaasWorksheetPreflight";
import css from "../raas-history/page.module.css";
export const metadata:Metadata={
 title:"RAAS · Exact Trial 60-Metric Review | PDUFA",
 description:"Trial-specific TOP and BOTTOM research review workbench with original NCT source links, provisional work and independent review gaps."
};
type Query={nctId?:string|string[];ticker?:string|string[]};
export default async function RaasTrialReviewPage({
 searchParams
}:{searchParams:Promise<Query>}){
 const p=await searchParams;
 const nctId=typeof p.nctId==="string"?p.nctId:"";
 const ticker=typeof p.ticker==="string"?p.ticker:"";
 const dossier=buildTrialMetricReviewDossier(registry,nctId,ticker);
 return <main className={css.root} data-raas-trial-metric-review-workspace="unapproved">
  <header className={css.header}>
   <Link className={css.back} href="/raas-evidence-backlog">
    ← Back to 762-trial evidence queue</Link>
   <h1>RAAS · exact-trial 60-metric review</h1>
   <p>Select any TOP or BOTTOM requirement to inspect its primary source leads,
    clinical and financial review checklist, and any existing source-checked
    provisional finding. The evidence panel opens alongside the metric list
    on wide screens.</p>
  </header>
  <p className={css.disclaimer}>
   <strong>Review workspace only.</strong> Registry evidence is not an
   independently confirmed readout or a validated treatment benefit. An AI
   source check is not an authenticated independent human review; no metric
   or composite RAAS score is approved here. Missing metrics are N/A,
   not zero. FDA PASS / CRL / EXTENSION probabilities remain unvalidated.
  </p>
  {dossier?<><section className={css.notice}
   data-raas-expert-review-worksheet="unsigned-editable-csv">
   <strong>60-metric independent reviewer worksheet</strong>
   <p>Download the exact-trial editable worksheet, with 30 TOP and
    30 BOTTOM requirements, dated registry source leads, and blank
    fields for benchmark, source, uncertainty and critical-risk findings.
    Complete it offline and retain it separately. A filled worksheet
    is not an authenticated expert sign-off or an approved RAAS score.</p>
   <p><a href={"/api/raas-unsigned-review-worksheet?"+
    new URLSearchParams({nctId,ticker}).toString()}
    data-raas-review-worksheet-download="true">
    Download editable 60-metric review worksheet (CSV)</a></p>
  </section><RaasWorksheetPreflight key={dossier.trial.nctId+":"+dossier.trial.ticker} dossier={dossier}/><ReviewDossierClient dossier={dossier}/></>:
   <section className={css.notice} role="alert">
    The requested NCT/ticker combination has no exact matching saved
    research record. No alternative program or trial was substituted.
    {" "}<Link href="/raas-evidence-backlog">Find a trial in the evidence queue</Link>.
   </section>}
  <p className={css.foot}><Link href="/raas-evidence-changes">Check latest exact-trial source changes</Link> · {" "}<Link href="/raas-review-queue">
   Existing source-reviewed metric assignments</Link> ·
   {" "}<Link href="/raas-worklist">All 60 RAAS metric definitions</Link>.
   This workflow does not activate retired GEM or GEM JR scans.
  </p>
 </main>;
}

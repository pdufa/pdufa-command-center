import type {Metadata} from "next";
import Link from "next/link";
import Phase3ReadoutSheets from "../Phase3ReadoutSheets";
import css from "../raas-history/page.module.css";

export const metadata:Metadata={
 title:"RAAS TOP and BOTTOM Phase 3 Trial Spreadsheets | PDUFA",
 description:"Review the two dated, issuer-classified TOP/BOTTOM Phase 3 spreadsheets, five-factor clinical RAAS worklists and source verification gaps."
};
export default function RaasTopBottomPage(){
 return <main className={css.root} data-raas-primary-score-scope="TOP_BOTTOM_ONLY">
  <header className={css.header}>
   <Link className={css.back} href="/tools">← TOOLS</Link>
   <h1>RAAS · TOP and BOTTOM spreadsheets</h1>
   <p><strong>Only source-classified trials in these two spreadsheets
    receive TOP/BOTTOM RAAS research metric assessments.</strong>
    Each stage has five clinical-science assessments. Expanded ingredients,
    history and stage-specific CSV exports stay with the trial.</p>
   <p><strong>Not scored here:</strong> the 11,000+ trial POOL;
    unclassified Phase 3 trials; and the 762-NCT registry-only research
    inventory. Those sources may supply candidates and evidence, but cannot
    establish the correct readout stage.</p>
  </header>
  <Phase3ReadoutSheets/>
  <p className={css.disclaimer}>
   Dated issuer-readout evidence is a research classification, not a live
   FDA-approval status or independently validated full RAAS rating.
   Missing metric grades remain N/A, never an invented 0/100 score.
  </p>
 </main>;
}

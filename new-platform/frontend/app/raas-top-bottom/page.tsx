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
   <p><strong>TOP now includes the current $300M–$10B,
    source-recorded Phase 3 candidate universe.</strong>
    Unverified readout statuses are clearly labeled and receive research-only
    five-factor checklists, not invented classified TOP scores.
    The issuer-classified TOP and BOTTOM sheets keep their dated evidence,
    five clinical factors and trial history.</p>
   <p><strong>TOP cap screening:</strong> only Phase 3 records with a dated,
    source-verified listed-issuer cap between $300 million and $10 billion
    are included; known Phase 3 public readouts are excluded.
    The wider 11,000+ trial POOL and unverified market-cap records are not
    automatically included.</p>
  </header>
  <Phase3ReadoutSheets/>
  <p className={css.disclaimer}>
   Dated issuer-readout evidence is a research classification, not a live
   FDA-approval status or independently validated full RAAS rating.
   Missing metric grades remain N/A, never an invented 0/100 score.
  </p>
 </main>;
}

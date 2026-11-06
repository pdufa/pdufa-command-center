import type {Metadata} from "next";
import Link from "next/link";
import Phase3SourceOnlySheets from "../Phase3SourceOnlySheets";
import css from "../raas-history/page.module.css";
export const metadata:Metadata={title:"TOP and BOTTOM Phase 3 Trial Spreadsheets | PDUFA",
 description:"Active Phase 3 TOP and BOTTOM spreadsheets: 235 Pre-Data and 23 Post-Data, with preserved historical trial archive."};
export default function RaasTopBottomPage(){
 return <main className={css.root} data-phase3-no-surveys-ratings="true">
  <header className={css.header}>
   <Link className={css.back} href="/tools">← TOOLS</Link>
   <h1>Phase 3 · TOP and BOTTOM spreadsheets</h1>
   <p><strong>Surveys and ratings cancelled</strong> refers to the retired legacy survey/questionnaire system. Separate phase-first clinical ratings, evidence completeness and saved RAAS grades are shown only when the source review supports them. Original trial histories remain preserved.</p>
   <p>Reconciled active Phase 3 studies: <strong>235 Pre-Data</strong> and <strong>23 Post-Data</strong>. Completed, terminated, withdrawn and unknown-status trials remain in the historical research census, not the active spreadsheets.</p>
  </header>
  <Phase3SourceOnlySheets/>
 </main>;
}

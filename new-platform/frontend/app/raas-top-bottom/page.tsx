import type {Metadata} from "next";
import Link from "next/link";
import Phase3SourceOnlySheets from "../Phase3SourceOnlySheets";
import css from "../raas-history/page.module.css";
export const metadata:Metadata={title:"TOP and BOTTOM Phase 3 Trial Spreadsheets | PDUFA",
 description:"Source-only Phase 3 TOP and BOTTOM spreadsheets. Surveys and ratings are cancelled."};
export default function RaasTopBottomPage(){
 return <main className={css.root} data-phase3-no-surveys-ratings="true">
  <header className={css.header}>
   <Link className={css.back} href="/tools">← TOOLS</Link>
   <h1>Phase 3 · TOP and BOTTOM spreadsheets</h1>
   <p><strong>Surveys and ratings cancelled.</strong> Existing trial data and historical source evidence remain preserved.</p>
   <p>The TOP list screens dated $300M–$10B Phase 3 issuer records and excludes documented public Phase 3 readouts. Unverified readout candidates remain clearly labeled.</p>
  </header>
  <Phase3SourceOnlySheets/>
 </main>;
}

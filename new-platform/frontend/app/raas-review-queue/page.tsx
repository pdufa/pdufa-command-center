import type {Metadata} from "next";
import Link from "next/link";
import css from "../raas-history/page.module.css";
export const metadata:Metadata={title:"RAAS surveys and ratings cancelled | PDUFA",
 description:"The former raas-review-queue survey and rating workspace is retired. Historical data is preserved."};
export default function CancelledRaasPage(){
 return <main className={css.root} data-raas-ratings-retired="raas-review-queue">
  <header className={css.header}>
   <Link className={css.back} href="/tools">← TOOLS</Link>
   <h1>Surveys and ratings cancelled</h1>
   <p>This scoring and survey workspace is no longer active. Historical source records and trial data are preserved, but no new ratings are generated here.</p>
   <p><Link href="/raas-top-bottom">Open source-only TOP and BOTTOM Phase 3 spreadsheets</Link></p>
  </header>
 </main>;
}

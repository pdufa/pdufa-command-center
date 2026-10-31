"use client";

import { useState } from "react";
import styles from "./FunnelWorkspace.module.css";

const CENSUS_TOTAL=741;
type BatchSize=5|10|25;

/** Explicit user-triggered downloads; no silent bulk requests or unreviewed qualification. */
export default function BatchRegistryExport(){
 const [batchSize,setBatchSize]=useState<BatchSize>(25);
 const [offset,setOffset]=useState(0);
 const end=Math.min(offset+batchSize,CENSUS_TOTAL);
 const download="/api/phase3-batch?offset="+offset+"&limit="+batchSize+"&format=csv";
 return <section className={styles.panel} aria-label="Bulk current registry evidence download">
   <h3>Current official registry · batch evidence export</h3>
   <p className={styles.muted}>Review 5, 10, or 25 historical NCT records per request from ClinicalTrials.gov. Source records retain NEEDS REVIEW status; no therapy is automatically Pipeline-qualified or scored.</p>
   <div className={styles.pagination}>
     <label htmlFor="registry-batch-size">Batch size</label>
     <select id="registry-batch-size" value={batchSize} onChange={e=>{
       const value=Number(e.target.value);
       if(value===5||value===10||value===25){setBatchSize(value);setOffset(0);}
     }}>
       <option value={5}>5 trials</option><option value={10}>10 trials</option><option value={25}>25 trials</option>
     </select>
     <button type="button" disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-batchSize))}>Previous batch</button>
     <span>Historical census {offset+1}–{end} of {CENSUS_TOTAL}</span>
     <button type="button" disabled={end>=CENSUS_TOTAL} onClick={()=>setOffset(Math.min(Math.floor((CENSUS_TOTAL-1)/batchSize)*batchSize,offset+batchSize))}>Next batch</button>
   </div>
   <p><a href={download} download={"pdufa-registry-batch-"+offset+".csv"}>Download {end-offset} current registry evidence rows (CSV)</a></p>
   <p className={styles.muted}>Import only the data rows under A:X in Google Sheet tab 20, preserving the formula in Y and independently reviewed entries. If even one official study cannot be verified, this batch returns no CSV; retry a smaller size. Automatic website-to-Sheets synchronization remains unconfigured.</p>
 </section>;
}

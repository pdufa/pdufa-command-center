import Link from "next/link";
import {FOCUS_R44_SAFETY} from "../../lib/focus-r44-registry-safety";

export default function FocusPostedSafetyR44(){
 const data=FOCUS_R44_SAFETY;
 const outer={background:"#f7f9fc",border:"1px solid #b9c8d8",borderRadius:12,
   padding:16,margin:"14px 0 18px"} as const;
 if(!data)return <section aria-label="R44 FOCUS safety research" style={outer}>
   Original source evidence receipt or exact 29-trial crosswalk failed validation. Safety research withheld.
 </section>;
 return <section aria-label="R44 original posted trial arm-specific safety evidence" style={outer}>
  <h2 style={{fontSize:20,margin:"2px 0 7px"}}>ClinicalTrials.gov original safety tables · 29 FOCUS trials</h2>
  <p style={{fontSize:13,lineHeight:1.6}}>
   Public original registry captures as of {data.asOf}: <strong>{data.counts.registryAdverseEventsModules}/29</strong> trials
   with adverse-event results, <strong>{data.counts.seriousEventTermRows}</strong> serious-event term rows,
   <strong>{data.counts.otherEventTermRows}</strong> other-event term rows, and
   <strong> {data.counts.eventGroupRows}</strong> reporting arms/groups.
   These are source-reported entries, not counted patients or graded clinical safety results.
  </p>
  <p style={{fontSize:12,lineHeight:1.55}}>
   The other {data.absent.length} FOCUS trials have no current posted registry results module; this does
   <strong> not</strong> establish that full Phase 3 safety findings are absent elsewhere.
   Where studies use multiple arms, doses, crossover or extensions, totals must not be pooled.
   All event terms and the original 29 full JSON records remain in
   <a href={data.sourceArtifactUrl} target="_blank" rel="noopener noreferrer"
    style={{color:"#0d665c",fontWeight:700}}> the hashed original-source archive</a>.
   Artifact access expires {data.sourceArtifactExpiresAt.slice(0,10)}.
  </p>
  <details style={{border:"1px solid #becbd8",borderRadius:9,padding:12,background:"#fff"}}>
   <summary style={{cursor:"pointer",fontWeight:800}}>
    Inspect all 12 posted safety trial records and their 28 source-reported arms
   </summary>
   <div style={{display:"grid",gap:9,paddingTop:12}}>
    {data.items.map(t=><article key={t.nct} style={{border:"1px solid #dae1ea",borderRadius:9,padding:11}}>
      <div><strong>{t.ticker} · {t.nct}</strong>
       <span style={{fontSize:11,marginLeft:8}}>
        {t.seriousEventTerms} serious event terms · {t.otherEventTerms} other terms
       </span>
      </div>
      <p style={{fontSize:11,margin:"5px 0 8px"}}>Provisional application(s): {t.applicationCycleIds.join(", ")}.
      Counts below are individual reporting-group totals, not pairwise effect estimates.</p>
      <div style={{overflowX:"auto"}}>
        <table style={{borderCollapse:"collapse",width:"100%",minWidth:520,fontSize:11,textAlign:"left"}}>
         <thead><tr style={{background:"#eef2f9"}}>
          <th style={{padding:6}}>Source arm / group</th>
          <th style={{padding:6}}>Any serious AE (affected / at risk)</th>
          <th style={{padding:6}}>All-cause deaths (affected / at risk)</th>
          <th style={{padding:6}}>Other AEs (affected / at risk)</th>
         </tr></thead>
         <tbody>{t.groups.map((g,i)=><tr key={i}>
          <td style={{padding:6,borderBottom:"1px solid #e2e6ed"}}>{g[0]}</td>
          <td style={{padding:6,borderBottom:"1px solid #e2e6ed"}}>{g[1]} / {g[2]}</td>
          <td style={{padding:6,borderBottom:"1px solid #e2e6ed"}}>{g[3]} / {g[4]}</td>
          <td style={{padding:6,borderBottom:"1px solid #e2e6ed"}}>{g[5]} / {g[6]}</td>
         </tr>)}</tbody>
        </table>
      </div>
      <div style={{fontSize:12,display:"flex",gap:13,marginTop:8,flexWrap:"wrap"}}>
       <a href={"https://clinicaltrials.gov/study/"+t.nct} target="_blank" rel="noopener noreferrer"
           style={{color:"#0b6657"}}>Original trial record</a>
       <Link href={"/predictions/assessment?nct="+t.nct} style={{color:"#0b6657"}}>Review scientific evidence</Link>
      </div>
    </article>)}
   </div>
  </details>
  <details style={{background:"#fff",border:"1px solid #becbd8",borderRadius:9,padding:12,marginTop:9}}>
   <summary style={{fontWeight:750,cursor:"pointer"}}>Show 17 other exact FOCUS NCTs without current registry result modules</summary>
   <div style={{fontSize:12,display:"flex",flexWrap:"wrap",gap:12,paddingTop:9}}>
    {data.absent.map(t=><a href={"https://clinicaltrials.gov/study/"+t.nct} target="_blank" rel="noopener noreferrer"
       key={t.nct} style={{color:"#0b6657"}}>{t.ticker} · {t.nct}</a>)}
   </div>
  </details>
  <p style={{fontSize:12,lineHeight:1.55,margin:"12px 0 0"}}>
   <strong>Source evidence only:</strong> clinical reviewer signoffs 0, qualified scientific scores 0,
   validated FDA application forecasts 0, real independent historical backtests 0.
   No FDA probability, study-level causal safety verdict or predicted approval has been released.
   Current original sources do not substitute for locked SAP, full integrated safety reports, CMC or regulator adjudication.
  </p>
 </section>;
}

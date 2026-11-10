import Link from "next/link";
import {FOCUS_R45_CURRENT_TEXT} from "../../lib/focus-r45-current-primary-text";

export default function FocusCurrentEndpointConcordanceR45(){
 const data=FOCUS_R45_CURRENT_TEXT;
 const outer={border:"1px solid #b3d3ce",borderRadius:12,padding:16,background:"#f8fbfa",margin:"14px 0 18px"} as const;
 if(!data)return <section aria-label="R45 endpoint source text comparison" style={outer}>
    Current registered-versus-posted primary outcome receipt or exact trial crosswalk changed; research view withheld.
 </section>;
 return <section aria-label="R45 29 trial current primary endpoint text research" style={outer}>
  <h2 style={{fontSize:20,margin:"3px 0 7px"}}>Current registry primary endpoint reconciliation · 29 trials</h2>
  <p style={{fontSize:13,lineHeight:1.6}}>
   Original-source current ClinicalTrials.gov evidence from {data.asOf}: <strong>{data.counts.currentRegisteredPrimaryTitles}</strong> registered primary outcomes,
   <strong> {data.counts.postedPrimaryTables}</strong> posted result tables, and
   <strong> {data.counts.exactCurrentTitleTimeframeMatches}</strong> exact current title/time-frame matches.
   No differences were found among these 16 currently posted result tables.
  </p>
  <p style={{fontSize:12,lineHeight:1.55}}>
   <strong>Not a locked SAP validation:</strong> current registry entries may have changed after the original
   trial readout. Matching today does not prove the endpoints or their statistical hierarchy were
   prespecified, or establish FDA efficacy, approval, probability or accuracy.
   The other 17 NCTs currently lack deposited registry results but may have publications elsewhere.
   <a href={data.sourceArtifactUrl} target="_blank" rel="noopener noreferrer" style={{marginLeft:5,color:"#0b6657",fontWeight:700}}>
      Original current-registry files and reproducible comparison receipt
   </a>.
  </p>
  <details style={{border:"1px solid #c6d7d1",borderRadius:9,padding:12,background:"#fff"}}>
   <summary style={{cursor:"pointer",fontWeight:800}}>
    Expand all 29 trial-level current registered / posted primary outcome counts
   </summary>
   <div style={{overflowX:"auto",paddingTop:9}}>
    <table style={{borderCollapse:"collapse",minWidth:610,width:"100%",fontSize:12,textAlign:"left"}}>
     <thead><tr style={{background:"#eaf3f0"}}>
      {["Ticker","Exact NCT","Currently registered","Currently posted","Current exact title/time matches","Evidence status"].map(h=>
        <th key={h} style={{padding:7,borderBottom:"2px solid #d3dfda"}}>{h}</th>)}
     </tr></thead>
     <tbody>{data.items.map(x=><tr key={x.nct}>
       <td style={{padding:7,borderBottom:"1px solid #e0eae5",fontWeight:700}}>{x.ticker}</td>
       <td style={{padding:7,borderBottom:"1px solid #e0eae5"}}>
         <Link href={"/predictions/assessment?nct="+x.nct} style={{color:"#0b6657"}}>{x.nct}</Link>
       </td>
       <td style={{padding:7,borderBottom:"1px solid #e0eae5"}}>{x.currentRegisteredPrimaryCount}</td>
       <td style={{padding:7,borderBottom:"1px solid #e0eae5"}}>{x.postedPrimaryCount}</td>
       <td style={{padding:7,borderBottom:"1px solid #e0eae5"}}>{x.exactCurrentTitleTimeframeMatchCount}</td>
       <td style={{padding:7,borderBottom:"1px solid #e0eae5"}}>
         {x.postedPrimaryCount?"Current text agrees · historical SAP unverified":"No current posted result · external sources still needed"}
       </td>
      </tr>)}</tbody>
    </table>
   </div>
  </details>
  <p style={{fontSize:12,margin:"12px 0 0"}}>
   Original pre-readout registry history: NOT VERIFIED · locked SAP/multiplicity: NOT VERIFIED ·
   clinical signoffs: 0 · scientific grades: 0 · validated FDA forecasts: 0/23 ·
   historical independent backtests: 0. Official pending FDA outcome and review-delay forecasts remain ABSTAIN.
  </p>
 </section>;
}

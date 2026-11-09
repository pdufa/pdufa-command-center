import Link from "next/link";
import {FOCUS_R43_SOURCE_CHALLENGES} from "../../lib/focus-r43-regulatory-challenges";

const outer={border:"1px solid #b8d2cb",borderRadius:12,padding:16,margin:"14px 0 18px",
 background:"#f6faf8"} as const;

export default function FocusRegulatorySourceChallengesR43(){
 const data=FOCUS_R43_SOURCE_CHALLENGES;
 if(!data)return <section aria-label="R43 regulatory original-source evidence" style={outer}>
  Regulatory source crosswalk failed closed. Research-only source evidence withheld.
 </section>;
 return <section aria-label="R43 original regulator safety statistical and filing challenges" style={outer}>
  <h2 style={{fontSize:20,margin:"1px 0 7px"}}>Regulatory and safety source challenges · 3 priority applications</h2>
  <p style={{fontSize:13,lineHeight:1.6}}>
    Source-checked {data.sourceCheckedOn}. These three <strong>application-level research challenges</strong> are attached to
    the existing 29 FOCUS / 23 provisional application roster, not counted as new FDA decisions.
    <strong> No scientific scores, calibrated probability, clinical signoff or approval/CRL forecast was released.</strong>
  </p>
  <p style={{fontSize:12,lineHeight:1.5}}>
    Important history correction: Savara's May 2025 FDA letter was <strong>Refusal to File (RTF), not CRL</strong>.
    Historical RTFs must not contaminate the FDA post-review CRL backtest denominator.
    Existing formal review extensions are observations, not predictions of new delays.
  </p>
  <div style={{display:"grid",gap:9}}>
   {data.records.map(r=><details key={r.cycleId} style={{background:"#fff",padding:12,
      border:"1px solid #ccdcd5",borderRadius:9}}>
      <summary style={{cursor:"pointer",lineHeight:1.5}}>
       <strong>{r.ticker} · {r.title}</strong>
       <span style={{display:"block",fontSize:12,color:"#566e64"}}>
        {r.ncts.join(", ")} · Sponsor-reported target {r.reportedPdufaDate} · Source challenge, not an FDA prediction
       </span>
      </summary>
      <div style={{fontSize:12,lineHeight:1.65,paddingTop:10}}>
       <strong>Evidence supporting and challenging the research hypothesis</strong>
       <ul style={{paddingLeft:20}}>
        {r.observations.map((s,i)=><li key={i} style={{marginBottom:6}}>{s}</li>)}
       </ul>
       <p><strong>What still blocks a qualified conclusion:</strong> {r.challenge}</p>
       {r.historicalStatusCorrection?<p><strong>Historical classification:</strong> {r.historicalStatusCorrection.replaceAll("_"," ")}</p>:null}
       {r.observedFormalExtension?<p><strong>Observed prior formal extension:</strong> {r.observedFormalExtension.replaceAll("_"," ")} (not a future timing forecast).</p>:null}
       <p><strong>Official FDA outcome:</strong> {r.officialOutcomeForecast} · <strong>Future extension forecast:</strong> {r.reviewTimingForecast}.</p>
       <p><strong>Exact original public source links:</strong></p>
       <ul style={{paddingLeft:20}}>
        {r.sources.map(s=><li key={s.url}><a href={s.url} target="_blank" rel="noopener noreferrer"
          style={{color:"#0b6657"}}>{s.label}</a> · {s.type.replaceAll("_"," ").toLowerCase()} · {s.date}</li>)}
       </ul>
       <Link href={"/predictions/assessment?nct="+r.ncts[0]} style={{color:"#0b6657",fontWeight:700}}>
         Open exact-NCT scientific evidence review
       </Link>
      </div>
    </details>)}
  </div>
  <p style={{fontSize:12,margin:"12px 0 0"}}>
   Research-only, as of {data.asOf}. All 23 application research profiles remain available above;
   the other 20 groups have not received this new targeted source challenge.
   No production or clinical reviewer records are changed.
  </p>
 </section>;
}

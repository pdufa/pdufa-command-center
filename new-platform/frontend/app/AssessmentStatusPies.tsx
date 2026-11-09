import type {EvidencePieSlice,LatestReleasedTrial} from "../lib/focus-assessment-chart";
import {evidencePieSlices} from "../lib/focus-assessment-chart";

const panel={
  background:"#fff",border:"1px solid #bfd6d0",borderRadius:14,
  padding:"clamp(14px,2.3vw,22px)",minWidth:0
} as const;

function Pie({slices,description}:{slices:readonly EvidencePieSlice[];description:string}){
  const total=slices.reduce((sum,part)=>sum+Math.max(0,part.value),0);
  const shown=slices.filter(part=>part.value>0);
  let angle=-90;
  const paths=shown.map(part=>{
    const start=angle;
    const portion=360*part.value/total;
    angle+=portion;
    const point=(degrees:number)=>{
      const radians=degrees*Math.PI/180;
      return [110+91*Math.cos(radians),110+91*Math.sin(radians)];
    };
    const [x1,y1]=point(start);
    const [x2,y2]=point(start+portion);
    return {
      key:part.key,color:part.color,
      d:portion>=359.999?null:
        `M 110 110 L ${x1.toFixed(3)} ${y1.toFixed(3)} A 91 91 0 ${portion>180?1:0} 1 ${x2.toFixed(3)} ${y2.toFixed(3)} Z`
    };
  });
  return <svg role="img" aria-label={description} viewBox="0 0 220 220"
    style={{width:"min(100%,230px)",height:"auto",display:"block",margin:"0 auto"}}>
    <title>{description}</title>
    {total===0?<circle cx="110" cy="110" r="91" fill="#e2e8ed" stroke="#c3cbd2" strokeWidth="2"/>:
      paths.map(part=>part.d?
        <path key={part.key} d={part.d} fill={part.color} stroke="#fff" strokeWidth="1.5"/>:
        <circle key={part.key} cx="110" cy="110" r="91" fill={part.color}/>)}
  </svg>;
}

function Legend({slices}:{slices:readonly EvidencePieSlice[]}){
  const total=slices.reduce((sum,row)=>sum+row.value,0);
  return <div aria-label="Evidence-check categories" style={{display:"grid",gap:8,marginTop:10}}>
    {slices.map(slice=><div key={slice.key}
      style={{display:"flex",alignItems:"center",justifyContent:"space-between",gap:8,fontSize:12}}>
      <span style={{display:"flex",alignItems:"center",gap:7,minWidth:0}}>
        <span aria-hidden="true" style={{width:11,height:11,background:slice.color,borderRadius:2,flexShrink:0}}/>
        {slice.label}
      </span>
      <strong style={{whiteSpace:"nowrap",fontVariantNumeric:"tabular-nums"}}>
        {slice.value.toLocaleString("en-US")}{total>0?` · ${Math.round(slice.value*100/total)}%`:""}
      </strong>
    </div>)}
  </div>;
}

export default function AssessmentStatusPies({
  asOf,totalTrials,totalChecks,overall,latest
}:{
  asOf:string;totalTrials:number;totalChecks:number;
  overall:EvidencePieSlice[];latest:LatestReleasedTrial|null;
}){
  const latestSlices=latest?evidencePieSlices(latest.counts):[];
  return <section aria-label="Assessment pie-chart summary" style={{
    display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,330px),1fr))",
    gap:14,margin:"16px 0 22px"
  }}>
    <div style={panel} data-testid="total-assessments-pie">
      <div style={{fontSize:11,letterSpacing:".08em",fontWeight:800,color:"#45645c"}}>TOTAL · FOCUS EVIDENCE</div>
      <h2 style={{fontSize:20,margin:"7px 0 3px"}}>All assessment checks</h2>
      <p style={{fontSize:13,lineHeight:1.55,color:"#4b655d",margin:"0 0 12px"}}>
        <strong>{totalChecks} evidence checks</strong> across {totalTrials} exact-NCT trials.
        The slices show evidence readiness, not completed scientific assessments.
      </p>
      <Pie slices={overall} description={`All ${totalChecks} FOCUS evidence checks by source status`}/>
      <Legend slices={overall}/>
      <p style={{fontSize:11,color:"#597268",margin:"13px 0 0"}}>Saved FOCUS snapshot: {asOf}. Source pointers are not independently verified.</p>
    </div>
    <div style={panel} data-testid="latest-prediction-pie">
      <div style={{fontSize:11,letterSpacing:".08em",fontWeight:800,color:"#45645c"}}>LATEST · PREDICTED TRIAL</div>
      <h2 style={{fontSize:20,margin:"7px 0 3px"}}>Last published prediction</h2>
      {latest?<>
        <p style={{fontSize:13,lineHeight:1.55,color:"#4b655d",margin:"0 0 12px"}}>
          <strong>{latest.ticker} · {latest.nct}</strong> · {latest.decision}.
          Published {latest.releasedAt}. The pie shows that trial's evidence-check
          disposition, <strong>not FDA outcome probabilities</strong>.
        </p>
        <Pie slices={latestSlices} description={`Evidence-check breakdown for last published prediction: ${latest.ticker} ${latest.nct}`}/>
        <Legend slices={latestSlices}/>
      </>:<>
        <p style={{fontSize:13,lineHeight:1.55,color:"#4b655d",margin:"0 0 12px"}}>
          <strong>No FDA prediction has been independently validated and published.</strong>
          The current 29-trial intake remains ABSTAIN / NOT VALIDATED.
        </p>
        <Pie slices={[]} description="No published prediction exists, so no latest-trial pie data are available"/>
        <div style={{textAlign:"center",fontSize:14,fontWeight:800,color:"#546e76",marginTop:12}}>
          NO PREDICTION RELEASED
        </div>
        <p style={{fontSize:12,lineHeight:1.6,color:"#597268",margin:"9px 0 0"}}>
          No percentages are shown until a saved trial-specific prediction has
          an explicit publication record. A completed source scan does not qualify.
        </p>
      </>}
    </div>
  </section>;
}

import Link from "next/link";
import type {PieSlice,PredictionAccuracySummary} from "../lib/focus-assessment-chart";

const panel={
  background:"#fff",border:"1px solid #bfd6d0",borderRadius:14,
  padding:"clamp(14px,2.3vw,22px)",minWidth:0
} as const;
const muted={fontSize:12,lineHeight:1.6,color:"#536b67"} as const;

function Pie({slices,description}:{slices:readonly PieSlice[];description:string}){
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

function Legend({slices,unit}:{slices:readonly PieSlice[];unit:"count"|"probability"}){
  return <div aria-label="Chart categories" style={{display:"grid",gap:8,marginTop:10}}>
    {slices.map(slice=><div key={slice.key}
      style={{display:"flex",alignItems:"center",justifyContent:"space-between",gap:8,fontSize:12}}>
      <span style={{display:"flex",alignItems:"center",gap:7,minWidth:0}}>
        <span aria-hidden="true" style={{width:11,height:11,background:slice.color,borderRadius:2,flexShrink:0}}/>
        {slice.label}
      </span>
      <strong style={{whiteSpace:"nowrap",fontVariantNumeric:"tabular-nums"}}>
        {unit==="count"?slice.value.toLocaleString("en-US"):`${(slice.value*100).toFixed(1)}%`}
      </strong>
    </div>)}
  </div>;
}

/** Two different units: observed accuracy across decided cycles, and the most
 * recent completed cycle's prediction distribution if independently calibrated.
 */
export default function AssessmentStatusPies({
  totalCompleted,compared,correct,incorrect,awaitingDecision,accuracyPercent,
  comparisonSlices,latest,auditAsOf
}:PredictionAccuracySummary){
  return <section aria-label="FDA prediction accuracy and most recent completed prediction" style={{
    display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,330px),1fr))",
    gap:14,margin:"16px 0 22px"
  }}>
    <div style={panel} data-testid="total-assessments-pie">
      <div style={{fontSize:11,letterSpacing:".08em",fontWeight:800,color:"#45645c"}}>
        OVERALL · ACTUAL FDA DECISIONS
      </div>
      <h2 style={{fontSize:20,margin:"7px 0 3px"}}>Overall prediction accuracy</h2>
      <p style={{fontSize:13,lineHeight:1.55,color:"#4b655d",margin:"0 0 12px"}}>
        Comparing frozen, completed FDA outcome predictions against subsequently verified FDA approval or CRL decisions.
      </p>
      <Pie slices={comparisonSlices} description={`${correct} correct predictions and ${incorrect} incorrect predictions compared with verified FDA decisions`}/>
      <Legend slices={comparisonSlices} unit="count"/>
      <p style={{fontWeight:800,textAlign:"center",margin:"12px 0 5px",fontSize:18}}>
        {accuracyPercent===null?"No verified comparisons yet":`${accuracyPercent.toFixed(1)}% correct`}
      </p>
      <p style={{...muted,margin:"0"}}>
        {compared} decided application cycles compared · {awaitingDecision} awaiting a comparable verified decision
        · {totalCompleted} completed prediction cycles recorded.
      </p>
      <p style={{...muted,margin:"10px 0 0"}}>
        Accuracy uses only decisions after the first frozen prediction for each FDA application cycle.
        Pending, withdrawn or unverified FDA actions do not count as wrong predictions.
        Review delays are a separate forecasting outcome.
        {auditAsOf?` Audit updated: ${auditAsOf}.`:""}
      </p>
    </div>

    <div style={panel} data-testid="latest-prediction-pie">
      <div style={{fontSize:11,letterSpacing:".08em",fontWeight:800,color:"#45645c"}}>
        MOST RECENT · COMPLETED PREDICTION
      </div>
      <h2 style={{fontSize:20,margin:"7px 0 3px"}}>Last completed prediction</h2>
      {latest?<>
        <p style={{fontSize:13,lineHeight:1.55,color:"#4b655d",margin:"0 0 12px"}}>
          <strong>{latest.ticker} · {latest.applicationCycleId}</strong><br/>
          {latest.drug} · {latest.indication}<br/>
          Frozen: {new Date(latest.completedAt).toLocaleString("en-US",{timeZone:"America/Los_Angeles"})}
        </p>
        <Pie slices={latest.probabilitySlices} description={latest.probabilitySlices.length?
          `Calibrated FDA approval versus CRL prediction for ${latest.ticker} ${latest.applicationCycleId}`:
          `Last completed prediction ${latest.predictionId} has no validated probability breakdown`}/>
        {latest.probabilitySlices.length?
          <Legend slices={latest.probabilitySlices} unit="probability"/>:
          <p style={{textAlign:"center",fontSize:13,fontWeight:800,color:"#637078"}}>
            Numerical probability NOT VALIDATED
          </p>}
        <p style={{fontSize:13,margin:"10px 0 3px"}}>
          <strong>Predicted outcome:</strong> {latest.predictedOutcome==="APPROVAL"?"FDA approval":"Complete Response Letter (CRL)"}
        </p>
        <p style={{...muted,margin:"0"}}>
          <strong>Actual FDA decision:</strong> {latest.actualOutcome==="PENDING"?"Pending or not independently verified":latest.actualOutcome}
          {latest.actualOutcome!=="PENDING"&&latest.actualSourceUrl?
            <> · <a href={latest.actualSourceUrl} rel="noopener noreferrer" target="_blank">Official decision source</a></>:null}
        </p>
        <p style={{...muted,margin:"10px 0 0"}}>
          This chart shows the prediction's approval/CRL probability split only when
          a calibrated distribution was saved with the completed forecast. It is not a pie of historical accuracy.
        </p>
        <Link href={`/predictions/assessment?nct=${encodeURIComponent(latest.ncts[0])}`}
          style={{fontSize:12,fontWeight:700}}>Open exact-NCT assessment</Link>
      </>:<>
        <p style={{fontSize:13,lineHeight:1.55,color:"#4b655d",margin:"0 0 12px"}}>
          No independently completed and frozen FDA decision prediction is recorded
          in the verified audit registry.
        </p>
        <Pie slices={[]} description="No completed FDA prediction is recorded for the most recent prediction chart"/>
        <div style={{textAlign:"center",fontSize:14,fontWeight:800,color:"#546e76",marginTop:12}}>
          NO COMPLETED PREDICTION
        </div>
        <p style={{...muted,margin:"9px 0 0"}}>
          Source collection and partial clinical research do not count as a completed
          FDA prediction. The 29-trial intake currently remains ABSTAIN / NOT VALIDATED.
        </p>
      </>}
    </div>
  </section>;
}

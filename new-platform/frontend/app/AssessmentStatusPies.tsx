import Link from "next/link";
import type {PieSlice,PredictionAccuracySummary} from "../lib/focus-assessment-chart";

const panel={
  background:"#fff",border:"1px solid #bfd6d0",borderRadius:14,
  padding:"clamp(14px,2.3vw,22px)",minWidth:0
} as const;
const muted={fontSize:12,lineHeight:1.6,color:"#536b67"} as const;

function Pie({
  slices,description,emptyTitle="0",emptySubtitle="verified decisions"
}:{
  slices:readonly PieSlice[];description:string;
  emptyTitle?:string;emptySubtitle?:string;
}){
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
    {total===0?<g>
      <circle cx="110" cy="110" r="91" fill="#f3f6f7" stroke="#b6c6cd" strokeWidth="5"/>
      <text x="110" y="110" textAnchor="middle" fill="#3e555c" fontSize="36" fontWeight="800">{emptyTitle}</text>
      <text x="110" y="133" textAnchor="middle" fill="#607780" fontSize="12">{emptySubtitle}</text>
    </g>:
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
      <Pie slices={comparisonSlices} description={`${correct} accurate predictions and ${incorrect} not accurate predictions compared with verified FDA decisions`} emptyTitle={String(compared)} emptySubtitle="FDA decisions"/>
      <Legend slices={comparisonSlices} unit="count"/>
      <p style={{fontWeight:800,textAlign:"center",margin:"12px 0 5px",fontSize:18}}>
        {accuracyPercent===null?"No verified comparisons yet":`${accuracyPercent.toFixed(1)}% correct`}
      </p>
      <p style={{...muted,margin:"0"}}>
        <strong>Accurate: {correct}</strong> · <strong>Not Accurate: {incorrect}</strong>
        {" · "}{compared} decided application cycles compared
        {" · "}{awaitingDecision} awaiting a comparable verified decision
        {" · "}{totalCompleted} completed prediction cycles recorded.
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
        <Pie
          slices={latest.decisionVerdict!=="AWAITING_DECISION"?latest.decisionComparisonSlices:latest.probabilitySlices}
          description={latest.decisionVerdict!=="AWAITING_DECISION"?
            `The most recent completed prediction was ${latest.decisionVerdict==="ACCURATE"?"accurate":"not accurate"} compared with the FDA decision`:
            latest.probabilitySlices.length?
              `Calibrated approval versus CRL probabilities for the most recent completed prediction`:
              `The most recent completed prediction awaits a verified FDA decision and has no validated probability breakdown`}
          emptyTitle="0" emptySubtitle="verified decisions"
        />
        {latest.decisionVerdict!=="AWAITING_DECISION"?
          <Legend slices={latest.decisionComparisonSlices} unit="count"/>:
          latest.probabilitySlices.length?
            <Legend slices={latest.probabilitySlices} unit="probability"/>:
            <p style={{textAlign:"center",fontSize:13,fontWeight:800,color:"#637078"}}>
              No independently validated probabilities yet
            </p>}
        <p style={{fontSize:13,margin:"10px 0 3px"}}>
          <strong>Predicted outcome:</strong> {latest.predictedOutcome==="APPROVAL"?"FDA approval":"Complete Response Letter (CRL)"}
        </p>
        <p style={{fontSize:13,margin:"4px 0",fontWeight:800,color:latest.decisionVerdict==="ACCURATE"?"#147456":latest.decisionVerdict==="NOT_ACCURATE"?"#aa503e":"#687781"}}>
          Prediction validity: {latest.decisionVerdict==="ACCURATE"?"Accurate":latest.decisionVerdict==="NOT_ACCURATE"?"Not Accurate":"Awaiting FDA Decision"}
        </p>
        <p style={{...muted,margin:"0"}}>
          <strong>Actual FDA decision:</strong> {latest.actualOutcome==="PENDING"?"Pending or not independently verified":latest.actualOutcome}
          {latest.actualOutcome!=="PENDING"&&latest.actualSourceUrl?
            <> · <a href={latest.actualSourceUrl} rel="noopener noreferrer" target="_blank">Official decision source</a></>:null}
        </p>
        <p style={{...muted,margin:"10px 0 0"}}>
          Once the actual FDA decision is independently verified, the chart shows Accurate or Not Accurate
          for this one completed prediction. Before that, it shows the calibrated approval/CRL
          probability split if one exists, or a clearly labeled empty-data state.
        </p>
        <Link href={`/predictions/assessment?nct=${encodeURIComponent(latest.ncts[0])}`}
          style={{fontSize:12,fontWeight:700}}>Open exact-NCT assessment</Link>
      </>:<>
        <p style={{fontSize:13,lineHeight:1.55,color:"#4b655d",margin:"0 0 12px"}}>
          No independently completed and frozen FDA decision prediction is recorded
          in the verified audit registry.
        </p>
        <Pie slices={[]} description="No completed FDA prediction is recorded for the most recent prediction chart" emptyTitle="0" emptySubtitle="completed"/>
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

import {bestFitTrend} from "../lib/assessment-best-fit-trend";
type TrendPoint={at:string;value:number;label?:string};
type DatedComparison={date:string|null|undefined;matched:boolean|null|undefined};

/**
 * Build a chart only from the case dates and matches in the current archive.
 * Cases on the same day collapse into one cumulative checkpoint. Records
 * without a resolvable action date or a directional result are excluded.
 * This NEVER changes the historical or prospective scoring registries.
 */
export function cumulativeDatedAgreement(rows:readonly DatedComparison[]):TrendPoint[]{
  const known=rows.filter((r):r is DatedComparison&{date:string;matched:boolean}=>
    typeof r.date==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(r.date)&&
    Number.isFinite(Date.parse(r.date))&&
    typeof r.matched==="boolean");
  known.sort((a,b)=>a.date.localeCompare(b.date));
  const result:TrendPoint[]=[];
  let count=0,matches=0;
  for(const item of known){
    count++;
    if(item.matched)matches++;
    const point={at:item.date,value:100*matches/count,label:matches+"/"+count+" compared"};
    if(result.length&&result[result.length-1].at===item.date)result[result.length-1]=point;
    else result.push(point);
  }
  return result;
}

const ink="#255d50";
const accent="#08745c";
const grey="#536d65";

/** Small, responsive historical/forecast trend directly within its parent chart.
 * Draws no line when fewer than two distinct, valid timestamps are recorded.
 */
export default function ChartTrendInset({
  title,points,kind,emptyText,testId
}:{
  title:string;points:readonly TrendPoint[];
  kind:"retrospective"|"prospective"|"level";
  emptyText:string;testId:string;
}){
  const valid=points.filter(p=>
    typeof p.at==="string"&&Number.isFinite(Date.parse(p.at))&&
    Number.isFinite(p.value)&&p.value>=0&&p.value<=100);
  const dedup=new Map<string,TrendPoint>();
  for(const point of valid)dedup.set(point.at,point);
  const chronological=[...dedup.values()].sort((a,b)=>Date.parse(a.at)-Date.parse(b.at));
  const fit=bestFitTrend(chronological.map(p=>({x:Date.parse(p.at),y:p.value})));
  const hasLine=fit!==null;
  const W=440,H=140,L=36,R=15,T=18,B=32;
  const values=chronological.map(x=>x.value);
  const bottom=hasLine?Math.max(0,Math.floor((
    Math.min(...values,fit.yStart,fit.yEnd)-10)/20)*20):0;
  const bottomY=H-B;
  const X=(t:number)=>L+(t-fit!.xStart)*(W-L-R)/(fit!.xEnd-fit!.xStart);
  const Y=(v:number)=>T+(100-Math.max(bottom,Math.min(100,v)))*(bottomY-T)/(100-bottom);
  return <div data-testid={testId} style={{
    border:"1px solid #d1e6dc",background:"#f7fcf9",borderRadius:10,
    padding:"10px 11px",margin:"12px 0 0",minWidth:0}}>
    <div style={{display:"flex",justifyContent:"space-between",alignItems:"baseline",flexWrap:"wrap",gap:6}}>
      <strong style={{fontSize:13,color:ink}}>{title}</strong>
      <span style={{fontSize:10,fontWeight:850,color:kind==="retrospective"?"#7a5d99":"#28735d"}}>
        {kind==="retrospective"?"HISTORICAL · NOT BLIND":kind==="level"?"RECORDED LEVELS ONLY":"FROZEN, VERIFIED OBSERVATIONS ONLY"}
      </span>
    </div>
    {hasLine?<svg data-testid={testId+"-line"} role="img" aria-label={
      title+": "+chronological.length+" dated cumulative or recorded observations from "+
      chronological[0].at+" to "+chronological.at(-1)!.at+". "+
      chronological.at(-1)!.value.toFixed(1)+" percent. "+
      (kind==="retrospective"?"Outcome-aware retrospective, not blind accuracy.":"")
    } viewBox={"0 0 "+W+" "+H}
      style={{display:"block",width:"100%",height:"auto",maxHeight:170,margin:"4px 0"}}>
      {[bottom,(bottom+100)/2,100].map(v=><g key={v}>
        <line x1={L} x2={W-R} y1={Y(v)} y2={Y(v)} stroke="#deebe3" strokeWidth="1"/>
        <text x={L-5} y={Y(v)+3} textAnchor="end" fontSize="10" fill={grey}>{Math.round(v)}%</text>
      </g>)}
      <line data-testid={testId+"-best-fit"}
        x1={X(fit!.xStart)} y1={Y(fit!.yStart)}
        x2={X(fit!.xEnd)} y2={Y(fit!.yEnd)}
        stroke={accent} strokeWidth="4.2" strokeLinecap="round">
        <title>Least-squares best-fit line across recorded observations, not future performance</title>
      </line>
      {chronological.map(p=><circle key={p.at} cx={X(Date.parse(p.at))} cy={Y(p.value)} r="3.5"
        fill={accent} stroke="#fff" strokeWidth="1">
        <title>{p.at+" · "+p.value.toFixed(1)+"% "+(p.label??"")}</title>
      </circle>)}
      <text x={L} y={H-5} fontSize="11" textAnchor="start" fill={grey}>
        {chronological[0].at.slice(5)}
      </text>
      <text x={W-R} y={H-5} fontSize="11" textAnchor="end" fill={grey}>
        {chronological.at(-1)!.at.slice(5)}
      </text>
      <text x={W-R} y={Math.max(13,Y(chronological.at(-1)!.value)-8)}
        fontSize="12" fontWeight="850" textAnchor="end" fill={ink}>
        {chronological.at(-1)!.value.toFixed(1)}%
      </text>
    </svg>:
    <div data-testid={testId+"-empty"} role="status" style={{
      minHeight:68,display:"flex",flexDirection:"column",justifyContent:"center",
      gap:3,fontSize:12,color:grey,lineHeight:1.45}}>
      <strong style={{fontSize:13,color:"#375b53"}}>No trend line available yet</strong>
      {emptyText}
    </div>}
    <p style={{fontSize:11,color:grey,lineHeight:1.5,margin:"4px 0 0"}}>
      {hasLine?
        (kind==="retrospective"?
          "Straight best-fit line: least-squares summary of cumulative directional agreement; dots show recorded values. Not validated future accuracy.":
         kind==="prospective"?
          "Straight best-fit line summarizes only valid, time-stamped forecasts; dots show actual recorded versions.":
          "Straight best-fit line summarizes recorded assessments for the same case; it does not infer other levels."):
        "A real trend requires at least two dated observations for this exact metric; no line is invented."}
    </p>
  </div>;
}

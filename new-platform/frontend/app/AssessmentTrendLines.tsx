import type {
  OverallAccuracyTrendPoint,LastPredictionTrendPoint
} from "../lib/focus-assessment-chart";
import {bestFitTrend} from "../lib/assessment-best-fit-trend";

type Point={at:string;first:number;second:number};
const green="#168a6d";
const orange="#c86b50";
const panel={
  background:"#fff",border:"1px solid #bfd6d0",borderRadius:14,
  padding:"clamp(14px,2.3vw,22px)",minWidth:0
} as const;

function PerformanceLineChart({
  points,heading,firstLabel,secondLabel,emptyText
}:{
  points:readonly Point[];heading:string;firstLabel:string;
  secondLabel:string;emptyText:string;
}){
  const xStart=56,xEnd=698,yTop=20,yBottom=196;
  const times=points.map(point=>Date.parse(point.at));
  const distinct=new Set(times).size;
  // Two different, valid observation times are required for an honest trend.
  const usable=points.length>=2&&distinct>=2&&
    times.every(Number.isFinite)&&
    points.every(point=>Number.isFinite(point.first)&&Number.isFinite(point.second)&&
      point.first>=0&&point.first<=100&&point.second>=0&&point.second<=100);
  const minTime=usable?Math.min(...times):0;
  const maxTime=usable?Math.max(...times):0;
  const plotX=(at:string)=>xStart+(Date.parse(at)-minTime)/(maxTime-minTime)*(xEnd-xStart);
  const plotY=(value:number)=>yBottom-(value/100)*(yBottom-yTop);
  const firstFit=usable?bestFitTrend(points.map(point=>({x:Date.parse(point.at),y:point.first}))):null;
  const secondFit=usable?bestFitTrend(points.map(point=>({x:Date.parse(point.at),y:point.second}))):null;
  const formatDate=(at:string)=>at.slice(0,10);
  return <div>
    <svg role="img" viewBox="0 0 735 250" style={{width:"100%",height:"auto",display:"block"}}
      aria-label={usable?
        `${heading}: ${firstLabel} and ${secondLabel} percentages over ${points.length} dated observations`:
        `${heading}: insufficient verified history to draw a line`}>
      <title>{heading}</title>
      {[0,25,50,75,100].map(value=><g key={value}>
        <line x1={xStart} y1={plotY(value)} x2={xEnd} y2={plotY(value)}
          stroke={value===0?"#91a8ae":"#e1eaeb"} strokeWidth={value===0?1.5:1}
          strokeDasharray={value===0?undefined:"4 5"}/>
        <text x={xStart-12} y={plotY(value)+4} textAnchor="end" fill="#647a7e" fontSize="12">
          {value}%
        </text>
      </g>)}
      <line x1={xStart} y1={yTop} x2={xStart} y2={yBottom} stroke="#91a8ae" strokeWidth="1.5"/>
      {usable?<>
        {firstFit&&<line data-testid="performance-best-fit-first"
          x1={xStart} y1={plotY(Math.max(0,Math.min(100,firstFit.yStart)))}
          x2={xEnd} y2={plotY(Math.max(0,Math.min(100,firstFit.yEnd)))}
          stroke={green} strokeWidth="4" strokeLinecap="round">
          <title>{firstLabel+" least-squares best-fit trend across dated observations"}</title>
        </line>}
        {secondFit&&<line data-testid="performance-best-fit-second"
          x1={xStart} y1={plotY(Math.max(0,Math.min(100,secondFit.yStart)))}
          x2={xEnd} y2={plotY(Math.max(0,Math.min(100,secondFit.yEnd)))}
          stroke={orange} strokeWidth="4" strokeLinecap="round">
          <title>{secondLabel+" least-squares best-fit trend across dated observations"}</title>
        </line>}
        {points.map((point,i)=><g key={point.at+"-"+i}>
          <circle cx={plotX(point.at)} cy={plotY(point.first)} r="4" fill={green} stroke="white" strokeWidth="1.5"/>
          <circle cx={plotX(point.at)} cy={plotY(point.second)} r="4" fill={orange} stroke="white" strokeWidth="1.5"/>
        </g>)}
        <text x={xStart} y={yBottom+25} textAnchor="start" fontSize="12" fill="#647a7e">
          {formatDate(points[0].at)}
        </text>
        <text x={xEnd} y={yBottom+25} textAnchor="end" fontSize="12" fill="#647a7e">
          {formatDate(points[points.length-1].at)}
        </text>
      </>:<text x={(xStart+xEnd)/2} y={(yTop+yBottom)/2}
        textAnchor="middle" fontSize="15" fontWeight="700" fill="#65777b">
        No verified trend yet
      </text>}
    </svg>
    <div style={{display:"flex",gap:"10px 20px",flexWrap:"wrap",fontSize:12,margin:"0 0 10px"}}>
      {[[firstLabel,green],[secondLabel,orange]].map(([name,color])=><span key={name}
        style={{display:"inline-flex",alignItems:"center",gap:7}}>
        <span aria-hidden="true" style={{height:3,width:19,background:color,borderRadius:2}}/>
        <strong>{name}</strong>
      </span>)}
    </div>
    <p style={{fontSize:12,color:"#596f73",lineHeight:1.55,margin:"0"}}>
      {usable?`${points.length} dated observations. Straight lines are least-squares best fits; dots are recorded values, not predicted future performance.`:emptyText}
    </p>
  </div>;
}

export default function AssessmentTrendLines({
  overallTrend,latestTrend,latestCycle
}:{
  overallTrend:readonly OverallAccuracyTrendPoint[];
  latestTrend:readonly LastPredictionTrendPoint[];
  latestCycle:string|null;
}){
  return <section aria-label="Prediction competitiveness and performance history"
    style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,330px),1fr))",
      gap:14,margin:"-8px 0 22px"}}>
    <div style={panel} data-testid="overall-accuracy-line">
      <div style={{fontSize:11,letterSpacing:".08em",fontWeight:800,color:"#45645c"}}>
        TOTAL · PERFORMANCE OVER TIME
      </div>
      <h2 style={{fontSize:19,margin:"7px 0 4px"}}>Overall competitiveness trend</h2>
      <p style={{fontSize:12,color:"#536b67",lineHeight:1.55,margin:"0 0 12px"}}>
        Cumulative Accurate vs. Not Accurate percentages as independently verified
        FDA decisions arrive. The latest point matches the total pie.
      </p>
      <PerformanceLineChart
        heading="Overall prediction accuracy over FDA decisions"
        firstLabel="Accurate %" secondLabel="Not Accurate %"
        points={overallTrend.map(p=>({at:p.date,first:p.accuratePct,second:p.notAccuratePct}))}
        emptyText="At least two different FDA decision dates with completed, predecision-frozen forecasts and verified outcomes are needed. No historical accuracy is inferred from source scans."
      />
    </div>
    <div style={panel} data-testid="latest-outlook-line">
      <div style={{fontSize:11,letterSpacing:".08em",fontWeight:800,color:"#45645c"}}>
        LAST · PREDICTION HISTORY
      </div>
      <h2 style={{fontSize:19,margin:"7px 0 4px"}}>Latest prediction outlook trend</h2>
      <p style={{fontSize:12,color:"#536b67",lineHeight:1.55,margin:"0 0 12px"}}>
        {latestCycle?`Exact FDA review cycle: ${latestCycle}. `:""}
        Comparison of calibrated Approval vs. CRL probabilities
        across frozen, dated prediction versions of the same application.
      </p>
      <PerformanceLineChart
        heading="Latest prediction approval versus CRL outlook over revisions"
        firstLabel="Approval %" secondLabel="CRL %"
        points={latestTrend.map(p=>({at:p.recordedAt,first:p.approvalPct,second:p.crlPct}))}
        emptyText="At least two dated, independently calibrated prediction versions for the latest exact FDA application cycle are required. An FDA decision, source scan or single snapshot does not create a trend."
      />
    </div>
  </section>;
}

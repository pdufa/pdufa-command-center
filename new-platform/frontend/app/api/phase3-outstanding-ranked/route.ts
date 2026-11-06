import ledger from "../../../public/phase3-unified-classifications-2026-11-05.json";
import {GET as getMissingAudit} from "../phase3-missing-data-audit/route";

export const dynamic="force-dynamic";
export const maxDuration=60;

type RankedTrial={
 rank:number;nctId:string;ticker:string;company:string;indication:string;
 registryStatus:string;classificationCode:string;unscored:number;
 documentedFacts:number;predicted:number;observed:number;endpointReviewed:boolean;
 missingProtocol:boolean;missingFDAApplication:boolean;missingPDUFA:boolean;
 clinicalTrialUrl:string;
};
type RankedCompany={
 rank:number;ticker:string;company:string;trials:number;
 outstanding:number;averageOutstanding:number;maxUnscored:number;
 mostIncompleteNct:string;endpointNotReviewed:number;missingPDUFA:number;
};
function parseCsv(csv:string):string[][]{
 const rows:string[][]=[];let values:string[]=[];let cell="";let quoted=false;
 const text=csv.replace(/^\uFEFF/,"");
 for(let i=0;i<text.length;i++){
  const ch=text[i];
  if(ch==='"'){
   if(quoted&&text[i+1]==='"'){cell+='"';i++;}
   else quoted=!quoted;
  }else if(ch===","&&!quoted){values.push(cell);cell="";}
  else if((ch==="\r"||ch==="\n")&&!quoted){
   if(ch==="\r"&&text[i+1]==="\n")i++;
   values.push(cell);
   if(values.length>1||values[0]!=="")rows.push(values);
   values=[];cell="";
  }else cell+=ch;
 }
 if(cell!==""||values.length){values.push(cell);rows.push(values);}
 return rows;
}
function csvField(x:unknown):string{
 const s=x==null?"":String(x).replace(/[\r\n]+/g," ");
 return '"'+s.replace(/"/g,'""')+'"';
}
function csvResponse(headers:string[],rows:(string|number|boolean)[][],name:string){
 const body=[headers,...rows].map(row=>row.map(csvField).join(",")).join("\r\n")+"\r\n";
 return new Response("\uFEFF"+body,{headers:{
  "Content-Type":"text/csv; charset=utf-8",
  "Content-Disposition":'attachment; filename="'+name+'"',
  "Cache-Control":"no-store"
 }});
}
export async function GET(request:Request){
 const auditUrl=new URL("/api/phase3-missing-data-audit?format=csv",request.url);
 const auditResponse=await getMissingAudit(new Request(auditUrl));
 if(!auditResponse.ok)return Response.json({error:"Missing-data audit unavailable"},{status:503});
 const parsed=parseCsv(await auditResponse.text());
 const headers=parsed.shift()||[];
 const index=(heading:string)=>headers.indexOf(heading);
 const required=["NCT","Ticker","Unscored questions","Documented source facts",
  "Numerically predicted questions","Observed endpoint/readout facts","Primary endpoint reviewed",
  "Protocol summary saved","FDA application not verified","PDUFA date not verified"];
 if(required.some(h=>index(h)<0)||parsed.length!==762||
    ledger.rows.length!==762)return Response.json({error:"Ranked trial input integrity failed"},{status:503});
 const roster=new Map(ledger.rows.map(r=>[r.nctId,r] as const));
 const records=parsed.map(values=>{
  const nctId=values[index("NCT")],meta=roster.get(nctId);
  if(!meta)throw Error("Unknown trial NCT "+nctId);
  const count=(heading:string)=>Number(values[index(heading)]||0);
  const flag=(heading:string)=>values[index(heading)]==="true";
  return {
   rank:0,nctId,ticker:values[index("Ticker")],company:meta.company||"",
   indication:meta.indication||"",registryStatus:values[index("Registry status")],
   classificationCode:values[index("Classification")],
   unscored:count("Unscored questions"),
   documentedFacts:count("Documented source facts"),
   predicted:count("Numerically predicted questions"),
   observed:count("Observed endpoint/readout facts"),
   endpointReviewed:flag("Primary endpoint reviewed"),
   missingProtocol:!flag("Protocol summary saved"),
   missingFDAApplication:flag("FDA application not verified"),
   missingPDUFA:flag("PDUFA date not verified"),
   clinicalTrialUrl:meta.registrySourceUrl||"https://clinicaltrials.gov/study/"+nctId
  } satisfies RankedTrial;
 });
 if(new Set(records.map(r=>r.nctId)).size!==762||
    records.some(r=>r.predicted+r.observed+r.documentedFacts+r.unscored!==30||
      r.unscored<0||r.unscored>30))
  return Response.json({error:"Trial assessment reconciliation failed"},{status:503});
 records.sort((a,b)=>b.unscored-a.unscored||
   a.ticker.localeCompare(b.ticker)||a.nctId.localeCompare(b.nctId));
 records.forEach((r,i)=>{r.rank=i+1;});
 const byTicker=new Map<string,Omit<RankedCompany,"rank"|"averageOutstanding">>();
 for(const r of records){
  let g=byTicker.get(r.ticker);
  if(!g){
   g={ticker:r.ticker,company:r.company,trials:0,outstanding:0,
      maxUnscored:-1,mostIncompleteNct:"",
      endpointNotReviewed:0,missingPDUFA:0};
   byTicker.set(r.ticker,g);
  }
  g.trials++;
  g.outstanding+=r.unscored;
  g.endpointNotReviewed+=r.endpointReviewed?0:1;
  g.missingPDUFA+=r.missingPDUFA?1:0;
  if(r.unscored>g.maxUnscored){
   g.maxUnscored=r.unscored;g.mostIncompleteNct=r.nctId;
  }
 }
 const companies:RankedCompany[]=[...byTicker.values()].map(g=>({
  ...g,rank:0,averageOutstanding:Math.round(g.outstanding/g.trials*100)/100
 })).sort((a,b)=>b.outstanding-a.outstanding||
  b.averageOutstanding-a.averageOutstanding||a.ticker.localeCompare(b.ticker));
 companies.forEach((g,i)=>{g.rank=i+1;});
 const totalUnscored=records.reduce((s,r)=>s+r.unscored,0);
 const totalByCompany=companies.reduce((s,g)=>s+g.outstanding,0);
 if(totalUnscored!==totalByCompany)return Response.json({error:"Company totals do not reconcile"},{status:503});
 const format=new URL(request.url).searchParams.get("format");
 if(format==="trials.csv")return csvResponse(
  ["Rank","Company","Ticker","NCT","Indication","Registry status","Unscored of 30",
   "Documented facts","Predicted","Observed","Primary endpoint reviewed",
   "Protocol missing","FDA application unverified","PDUFA date unverified","ClinicalTrials.gov URL"],
  records.map(r=>[r.rank,r.company,r.ticker,r.nctId,r.indication,r.registryStatus,
   r.unscored,r.documentedFacts,r.predicted,r.observed,r.endpointReviewed,
   r.missingProtocol,r.missingFDAApplication,r.missingPDUFA,r.clinicalTrialUrl]),
  "Phase3-762-Trials-Ranked-Most-Missing-2026-11-06.csv");
 if(format==="companies.csv")return csvResponse(
  ["Rank","Company","Ticker","Trial count","Total unscored assessments",
   "Average unscored per trial","Highest unscored in one trial",
   "Most incomplete trial NCT","Primary endpoints not reviewed","PDUFA dates unverified"],
  companies.map(g=>[g.rank,g.company,g.ticker,g.trials,g.outstanding,
   g.averageOutstanding,g.maxUnscored,g.mostIncompleteNct,g.endpointNotReviewed,g.missingPDUFA]),
  "Phase3-Companies-Ranked-Outstanding-2026-11-06.csv");
 return Response.json({
  asOf:ledger.asOf,generatedAt:new Date().toISOString(),
  source:"Current exact-NCT 762-row missing-data audit (30 questions per trial)",
  scoringNote:"Ranking counts UNSCORED assessments; documented source facts awaiting scientific interpretation are not counted as unscored. This is not a 190/192-column blank-cell count.",
  trialsCount:records.length,companiesCount:companies.length,totalUnscored,
  trials:records,companies
 },{headers:{"Cache-Control":"no-store"}});
}

/** Download retained exact-NCT source revisions without computed clinical grades. */
import history from "../../../data/raas-registry-evidence-change-history.json";
export const dynamic="force-dynamic";
type Event={
 eventId:string;observedAt:string;nctId:string;ticker:string;sourceUrl:string;
 previousSourceHash:string;newSourceHash:string;
 changeCategories:string[];reviewFlag:string;candidateResearchMetricIds:string[];
 before:{postedResults:boolean;postedPrimaryOutcomeCount:number;
  seriousAdverseEventTermCount:number};
 after:{postedResults:boolean;postedPrimaryOutcomeCount:number;
  seriousAdverseEventTermCount:number};
};
const headers=[
 "eventId","observedAt","nctId","ticker","sourceUrl",
 "previousSourceHash","newSourceHash","changeCategories","reviewFlag",
 "candidateResearchMetricIds","priorPostedResults","newPostedResults",
 "priorPrimaryOutcomeCount","newPrimaryOutcomeCount",
 "priorSeriousEventTerms","newSeriousEventTerms",
 "approvedRaasScore","calibratedFdaProbability"
];
const cell=(v:unknown)=>{
 const x=String(v??"");
 return '"'+(/^\s*[=+@-]/.test(x)?"'"+x:x).replaceAll('"','""')+'"';
};
export function GET(){
 const events=(history as unknown as {events:Event[]}).events;
 const rows=events.map(e=>[
  e.eventId,e.observedAt,e.nctId,e.ticker,e.sourceUrl,
  e.previousSourceHash,e.newSourceHash,e.changeCategories.join("|"),
  e.reviewFlag,e.candidateResearchMetricIds.join("|"),
  e.before.postedResults,e.after.postedResults,
  e.before.postedPrimaryOutcomeCount,e.after.postedPrimaryOutcomeCount,
  e.before.seriousAdverseEventTermCount,e.after.seriousAdverseEventTermCount,
  "N/A","N/A"
 ]);
 const csv="\uFEFF"+headers.join(",")+"\r\n"+
  rows.map(r=>r.map(cell).join(",")).join("\r\n")+"\r\n";
 return new Response(csv,{status:200,headers:{
  "Content-Type":"text/csv; charset=utf-8",
  "Content-Disposition":'attachment; filename="raas-registry-evidence-change-history.csv"',
  "Cache-Control":"no-store","X-Content-Type-Options":"nosniff"
 }});
}

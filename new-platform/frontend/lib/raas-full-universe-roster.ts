/** Read-only cap-screened Phase 3 research universe returned by the
 * existing authenticated TOOLS CSV. Never imply that a restricted issuer-cap
 * screen verifies PDUFA eligibility or confirms any public Phase 3 readout.
 */
import type {ReadoutClassification,ReadoutRow} from "./phase3-public-readout";
const NCT=/^NCT\d{8}$/;
const TICKER=/^[A-Z]{1,7}(?:[.-][A-Z]{1,3})?$/;
const STAGES=new Set(["Phase 3","Phase 3 Results"]);
export type RaasScreenedTrialRoster={
 rows:ReadoutRow[];sourceAsOf:string;source:"MARKET_CAP_RESTRICTED_PHASE3_POOL";
 details:ReadonlyMap<string,{drug:string;indication:string;recordedStage:"Phase 3"|"Phase 3 Results"}>;
};
export const RAAS_RESTRICTED_PHASE3_CSV_QUERY=
 "/api/scope-funnel?view=pool&tools=1&recordKind=trials&stages="+
 encodeURIComponent("Phase 3,Phase 3 Results")+
 "&offset=0&limit=50&format=csv";
/** Only source-recorded Phase 3 (not Phase 3 Results), within dated
 * verified $300M–$10B Nasdaq/NYSE issuer-cap restriction.
 * Endpoint emits all matches in one exact-NCT CSV (no 50-row truncation).
 */
export const RAAS_RESTRICTED_TOP_PHASE3_CSV_QUERY=
 "/api/scope-funnel?view=pool&tools=1&recordKind=trials&stages="+
 encodeURIComponent("Phase 3")+
 "&offset=0&limit=50&format=csv";
/** RFC-4180 fields, with bounded file and row sizes. Explicitly rejects
 * corrupt/mixed schemas instead of inventing a trial universe count.
 */
function parseCsv(s:string):string[][]{
 if(typeof s!=="string"||s.length>5_000_000||s.length<20||
    s.includes("\0"))throw Error("RAAS_ROSTER_CSV_INVALID");
 const t=s.charCodeAt(0)===0xfeff?s.slice(1):s;
 const rows:string[][]=[];let row:string[]=[],field="",quoted=false,finished=false;
 for(let i=0;i<t.length;i++){
  const c=t[i],next=t[i+1];
  if(quoted){
   if(c==='"'&&next==='"'){field+='"';i++;}
   else if(c==='"'){quoted=false;finished=true;}
   else field+=c;
  }else if(c==='"'&&!field&&!finished){quoted=true;}
  else if(c===","){
   row.push(field);field="";finished=false;
  }else if(c==="\r"||c==="\n"){
   if(c==="\r"&&next==="\n")i++;
   if(field||row.length||finished){
    row.push(field);
    if(row.length>60)throw Error("RAAS_ROSTER_CSV_INVALID");
    rows.push(row);row=[];field="";finished=false;
   }
  }else if(finished||c==='"')throw Error("RAAS_ROSTER_CSV_INVALID");
  else field+=c;
  if(field.length>1500||rows.length>25001)throw Error("RAAS_ROSTER_CSV_TOO_LARGE");
 }
 if(quoted)throw Error("RAAS_ROSTER_CSV_INVALID");
 if(field||row.length||finished){row.push(field);rows.push(row);}
 return rows;
}
const headers=[
 "NCT ID","Ticker","Company","Drug / therapy",
 "Disease / indication","Recorded development stage","Source snapshot as of"
] as const;
export function parseRaasScreenedPhase3Csv(
 csv:string,classified:ReadoutClassification
):RaasScreenedTrialRoster{
 if(!classified||classified.total!==741||
  classified.pre.length+classified.post.length+classified.unverified.length!==741)
  throw Error("RAAS_ROSTER_CLASSIFICATION_INVALID");
 const parsed=parseCsv(csv),head=parsed[0];
 if(!head||parsed.length===1||parsed.length>25001)
  throw Error("RAAS_ROSTER_EMPTY");
 const locate=(name:string)=>head.indexOf(name);
 if(new Set(head).size!==head.length||headers.some(h=>locate(h)<0)||
  head.length<20||head.length>60)throw Error("RAAS_ROSTER_HEADER_INVALID");
 const known=new Map([...classified.pre,...classified.post].map(r=>[r.nctId,r]));
 const ids=new Set<string>();const result:ReadoutRow[]=[];
 const details=new Map<string,{drug:string;indication:string;recordedStage:"Phase 3"|"Phase 3 Results"}>();
 let sourceAsOf="";
 for(const values of parsed.slice(1)){
  if(values.length!==head.length)throw Error("RAAS_ROSTER_ROW_SHAPE_INVALID");
  const pick=(n:typeof headers[number])=>values[locate(n)].trim();
  const id=pick("NCT ID"),ticker=pick("Ticker"),company=pick("Company"),
    drug=pick("Drug / therapy"),indication=pick("Disease / indication"),
    stage=pick("Recorded development stage"),asOf=pick("Source snapshot as of");
  if(!NCT.test(id)||!TICKER.test(ticker)||ids.has(id)||!company||
     company.length>250||drug.length>300||indication.length>300||
     !STAGES.has(stage)||!asOf||Number.isNaN(Date.parse(asOf))||
     (sourceAsOf&&asOf!==sourceAsOf))
    throw Error("RAAS_ROSTER_ROW_INVALID");
  sourceAsOf=asOf;ids.add(id);
  details.set(id,{drug,indication,recordedStage:stage as "Phase 3"|"Phase 3 Results"});
  const verified=known.get(id);
  // Use only direct dated issuer evidence from the verified classification;
  // phase/status names in a source registry are not readout evidence.
  const evidence=verified?.ticker===ticker?verified.evidence:null;
  result.push({nctId:id,ticker,company,sourceUrl:"https://clinicaltrials.gov/study/"+id,
   status:"UNKNOWN",pipelineQualification:null,fdaPdufaVerification:false,
   evidence:evidence||null});
 }
 return {rows:result,sourceAsOf,source:"MARKET_CAP_RESTRICTED_PHASE3_POOL",details};
}

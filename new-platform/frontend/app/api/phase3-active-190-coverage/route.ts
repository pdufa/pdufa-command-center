import {GET as export190} from "../phase3-unified-190-columns/route";
import {activePhase3Cohorts} from "../../../lib/phase3-active-cohorts";
import {phaseFirstReport} from "../../../lib/phase-first-report";
import {UNIVERSAL_PHASE3_QUESTIONS} from "../../../lib/phase3-universal-questions";
import {isObservedStatus,isSourceFactStatus,requiresResearchStatus} from "../../../lib/phase3-ir-research";

export const dynamic="force-dynamic";
export const maxDuration=60;

/** Parse the actual exported matrix, not an independent or guessed coverage count. */
function parseCsv(csv:string):string[][]{
 const rows:string[][]=[];
 let row:string[]=[],cell="",quoted=false;
 const input=csv.replace(/^\uFEFF/,"");
 for(let i=0;i<input.length;i++){
  const ch=input[i];
  if(ch==='"'){
   if(quoted&&input[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;
  }else if(ch===","&&!quoted){row.push(cell);cell="";}
  else if(ch==="\n"&&!quoted){row.push(cell.replace(/\r$/,""));rows.push(row);row=[];cell="";}
  else if(ch!=="\r"||quoted)cell+=ch;
 }
 if(quoted)throw Error("UNCLOSED_CSV_QUOTE");
 if(cell||row.length){row.push(cell);rows.push(row);}
 return rows;
}
const csvCell=(value:unknown)=>{
 let s=value==null?"":String(value).replace(/[\r\n]+/g," ");
 if(/^[=+@-]/.test(s))s="'"+s;
 return '"'+s.replace(/"/g,'""')+'"';
};
const statusEvidence=(status:string)=>isObservedStatus(status)||isSourceFactStatus(status);
const nonblank=(s:string)=>s!==""&&s!=="NOT_VERIFIED"&&s!=="UNKNOWN";
const percent=(a:number,b:number)=>b?Math.round(a/b*1000)/10:null;

/** Auditable current 190-column matrix for the active universe only. */
export async function GET(request:Request){
 try{
  const query=new URL(request.url).searchParams;
  const format=query.get("format")||"json";
  const live=query.get("live")==="1";
  if(query.has("live")&&!["0","1"].includes(query.get("live")||""))
   return Response.json({error:"live must be 0 or 1"},{status:400});
  if(!["json","csv"].includes(format))return Response.json({error:"format must be json or csv"},{status:400});
  const result=await export190(new Request("http://phase3.internal/api/phase3-unified-190-columns?cohort=active"+(live?"&live=1":"")));
  if(!result.ok)return Response.json({error:"190-column source export not ready"},{status:503});
  const matrix=parseCsv(await result.text());
  const [headers,...data]=matrix;
  const cohort=[...activePhase3Cohorts.pre,...activePhase3Cohorts.post];
  const identity=new Map(cohort.map(r=>[r.nctId,r] as const));
  if(!headers||headers.length!==190||data.length!==258||cohort.length!==258||
    new Set(data.map(r=>r[0])).size!==258||
    data.some(r=>r.length!==190||!identity.has(r[0]))||
    UNIVERSAL_PHASE3_QUESTIONS.length!==30)
    return Response.json({error:"Active 258-trial 190-column integrity mismatch"},{status:503});
  const phase=phaseFirstReport("census");
  const existing=new Map(phase.trials.map(r=>[r.trialId,r] as const));
  if(existing.size!==phase.trials.length||data.some(r=>!existing.has(r[0])))
    return Response.json({error:"Trial identity and research-score crosswalk incomplete"},{status:503});
  const perQuestion=UNIVERSAL_PHASE3_QUESTIONS.map((q,i)=>({
   number:i+1,heading:q.heading,documented:0,predicted:0,unscored:0,
   numericQuestionScores:0,sourceUrlPresent:0
  }));
  const rows=data.map(cells=>{
   const id=cells[0],study=identity.get(id)!,rating=existing.get(id)!;
   let documented=0,predicted=0,unscored=0,numericQuestionScores=0,sourceUrlPresent=0;
   const missingQuestionNumbers:number[]=[];
   for(let i=0;i<30;i++){
    const base=40+i*5,status=cells[base]||"";
    const source=cells[base+4]||"",number=cells[base+2]||"";
    const hasNumeric=number.trim()!==""&&Number.isFinite(Number(number))&&Number(number)>=0&&Number(number)<=100;
    if(statusEvidence(status)){documented++;perQuestion[i].documented++;}
    else if(status==="PREDICTED_PRE_READOUT"){predicted++;perQuestion[i].predicted++;}
    else if(requiresResearchStatus(status)||status==="NOT_PUBLICLY_DISCLOSED"){
     unscored++;perQuestion[i].unscored++;missingQuestionNumbers.push(i+1);
    }else throw Error("UNKNOWN_QUESTION_STATUS_"+status+"_"+id);
    if(hasNumeric){numericQuestionScores++;perQuestion[i].numericQuestionScores++;}
    if(source){sourceUrlPresent++;perQuestion[i].sourceUrlPresent++;}
   }
   if(documented+predicted+unscored!==30)throw Error("QUESTION_COUNT_"+id);
   const ratingScored=rating.ratingCoverage.scored;
   const clinicalRating=ratingScored>0?rating.overallRating:null;
   return {
    nctId:id,ticker:study.ticker,company:study.company,cohort:study.cohort,
    columnCount:190,nonemptyCells:cells.filter(nonblank).length,
    metadataCellsPresent:cells.slice(0,40).filter(nonblank).length,
    documentedQuestions:documented,predictedQuestions:predicted,
    unscoredQuestions:unscored,numericQuestionScores,
    sourceUrlQuestions:sourceUrlPresent,
    missingQuestionNumbers,
    evidenceCompletenessPercent:rating.evidenceCompleteness,
    clinicalResearchRating:clinicalRating,
    clinicalScoredFactors:ratingScored,
    clinicalEligibleFactors:rating.ratingCoverage.eligible,
    savedRaasScore:rating.raasScore,
    fdaPredictionStatus:rating.fdaPrediction.status,
    sourceModelVersion:rating.modelVersion
   };
  });
  const totals={
   trials:rows.length,columnsPerTrial:190,expectedCells:rows.length*190,
   nonemptyCells:rows.reduce((a,r)=>a+r.nonemptyCells,0),
   documentedQuestions:rows.reduce((a,r)=>a+r.documentedQuestions,0),
   predictedQuestions:rows.reduce((a,r)=>a+r.predictedQuestions,0),
   unscoredQuestions:rows.reduce((a,r)=>a+r.unscoredQuestions,0),
   numericQuestionScores:rows.reduce((a,r)=>a+r.numericQuestionScores,0),
   clinicalRatedTrials:rows.filter(r=>r.clinicalResearchRating!==null).length,
   raasScoredTrials:rows.filter(r=>r.savedRaasScore!==null).length,
   preTrials:activePhase3Cohorts.pre.length,postTrials:activePhase3Cohorts.post.length,
   questionSlots:rows.length*30
  };
  if(totals.documentedQuestions+totals.predictedQuestions+totals.unscoredQuestions!==totals.questionSlots)
   return Response.json({error:"Research question coverage does not reconcile"},{status:503});
  if(format==="csv"){
   const names=["NCT","Ticker","Company","Cohort","190 columns present","Nonblank/190 (includes status placeholders)",
    "Metadata nonblank/40","Evidence-backed questions/30","Prospective predicted questions/30",
    "Unscored questions/30","Numerical question scores","Questions with source URLs",
    "Phase-first evidence completeness %","Reviewed clinical rating","Reviewed clinical factors","Eligible clinical factors",
    "Saved RAAS score","FDA prediction status","Unscored question numbers"];
   const values=rows.map(r=>[r.nctId,r.ticker,r.company,r.cohort,r.columnCount,r.nonemptyCells,
    r.metadataCellsPresent,r.documentedQuestions,r.predictedQuestions,r.unscoredQuestions,
    r.numericQuestionScores,r.sourceUrlQuestions,r.evidenceCompletenessPercent,
    r.clinicalResearchRating,r.clinicalScoredFactors,r.clinicalEligibleFactors,r.savedRaasScore,
    r.fdaPredictionStatus,r.missingQuestionNumbers.join("|")]);
   return new Response("\uFEFF"+[names,...values].map(x=>x.map(csvCell).join(",")).join("\r\n")+"\r\n",{
    headers:{"Content-Type":"text/csv; charset=utf-8","Cache-Control":"no-store",
     "Content-Disposition":'attachment; filename="PDUFA-258-Active-Trials-190-Field-Coverage-2026-11-06'+(live?"-live-official-registry":"")+'.csv"'}
   });
  }
  return Response.json({asOf:activePhase3Cohorts.asOf,liveOfficialRegistry:live,
   officialRegistryCheckedAt:live?new Date().toISOString():null,
   totals,perQuestion,rows,
   definitions:{
    nonemptyCells:"Includes status labels, missing-evidence descriptions and other metadata; NOT the number of verified scientific facts.",
    documentedQuestions:"Exact-trial observed or source-supported information; not prospective predictions.",
    predictedQuestions:"Previously reviewed prospective answers, never counted as observed outcomes.",
    unscoredQuestions:"Questions without an evidence-based assessment; not failed trials.",
    evidenceCompletenessPercent:"Phase-first documented evidence availability, not clinical efficacy or FDA approval probability.",
    clinicalResearchRating:"Only accepted exact-NCT, phase-appropriate benchmark grades.",
    savedRaasScore:"Existing approved RAAS scores only; never inferred from this 190-field export."
   }},{headers:{"Cache-Control":"no-store"}});
 }catch(e){
  return Response.json({error:"Active evidence audit could not be reconciled"},{status:503});
 }
}

/** Read-only scientific evidence follow-up; never marks a level scientifically complete. */
const object=(x:unknown):x is Record<string,unknown>=>!!x&&typeof x==="object"&&!Array.isArray(x);
const NCT=/^NCT[0-9]{8}$/;
const ACTIONS=new Set(["COLLECT_AND_REVIEW_SOURCE","RESOLVE_REJECTED_SOURCE",
 "VERIFY_PUBLICATION_CLAIM","RECHECK_REPORTED_UNPUBLISHED"]);
const STATES=new Set(["NOT_ASSESSED","REJECTED_EVIDENCE",
 "UNVERIFIED_UNPUBLISHED_CLAIM","UNPUBLISHED"]);
const statuses=new Set(["RESEARCH_QUEUE_READY","NO_ACTIVE_GAPS_NOT_SCIENTIFIC_VALIDATION",
 "BLOCKED_UNVERIFIED_INTAKE"]);
type QueueTask={id:string;level:number;criterion:string;state:string;action:string;
 priorityOrder:number;reason:string;rejectionReason?:string|null};
type Deferred={id:string;level:number;criterion:string;state:"NOT_YET_EXPECTED";reason:string};
type SourceLead={name:string;url:string};
type SourceAvenue={level:number;status:"UNSEARCHED_CANDIDATE_LEADS";sourceClass:string;
 instruction:string;identityGate:string;sourceLeads:SourceLead[];reviewResult:null;fdaPrediction:"ABSTAIN"};
type Queue={nctId:string;asOf:string;status:string;tasks:QueueTask[];
 deferred:Deferred[];reviewedCriteria:number;unresolvedCriteria:number;
 researchAvenues?:Record<string,SourceAvenue>;
 score:null;scientificValidation:"NOT_VERIFIED";fdaPrediction:"ABSTAIN"};
const safeText=(x:unknown):x is string=>typeof x==="string"&&x.length<=512;
function idMatches(item:Record<string,unknown>,nctId:string):boolean{
 const level=item.level,criterion=item.criterion;
 return typeof level==="number"&&Number.isInteger(level)&&level>=9&&level<=20&&
  typeof criterion==="string"&&/^[A-Za-z][A-Za-z0-9]{0,90}$/.test(criterion)&&
  item.id===nctId+":L"+String(level).padStart(2,"0")+":"+criterion;
}
function validAvenues(raw:unknown,nctId:string):raw is Record<string,SourceAvenue>{
 if(!object(raw)||Object.keys(raw).length!==12)return false;
 const permitted=new Set([
  "https://clinicaltrials.gov/study/"+nctId,
  "https://pubmed.ncbi.nlm.nih.gov/?term="+nctId,
  "https://www.fda.gov/drugsatfda",
  "https://www.sec.gov/edgar/search/",
 ]);
 return Array.from({length:12},(_,i)=>i+9).every(n=>{
  const avenue=raw[String(n)];
  if(!object(avenue)||avenue.level!==n||
   avenue.status!=="UNSEARCHED_CANDIDATE_LEADS"||
   avenue.reviewResult!==null||avenue.fdaPrediction!=="ABSTAIN"||
   !safeText(avenue.sourceClass)||!safeText(avenue.instruction)||
   !safeText(avenue.identityGate)||!Array.isArray(avenue.sourceLeads)||
   avenue.sourceLeads.length>2)return false;
  const leads=avenue.sourceLeads;
  if(n===19&&leads.length!==0)return false;
  if(n!==19&&leads.length===0)return false;
  return leads.every(lead=>object(lead)&&safeText(lead.name)&&safeText(lead.url)&&
   permitted.has(lead.url));
 });
}
export function validAdvancedResearchQueue(value:unknown,nctId:string):value is Queue{
 if(!object(value)||!NCT.test(nctId)||value.nctId!==nctId||
  value.methodVersion!=="scientific-advanced-research-queue-v1"||
  !safeText(value.asOf)||!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(value.asOf)||
  !statuses.has(String(value.status))||value.score!==null||
  value.scientificValidation!=="NOT_VERIFIED"||value.fdaPrediction!=="ABSTAIN"||
  !Array.isArray(value.tasks)||!Array.isArray(value.deferred)||
  value.tasks.length>60||value.deferred.length>60||
  typeof value.reviewedCriteria!=="number"||typeof value.unresolvedCriteria!=="number"||
  !Number.isSafeInteger(value.reviewedCriteria)||!Number.isSafeInteger(value.unresolvedCriteria)||
  value.reviewedCriteria<0||value.unresolvedCriteria!==value.tasks.length)return false;
 if(value.status==="BLOCKED_UNVERIFIED_INTAKE"&&(value.tasks.length||value.deferred.length))return false;
 if(value.researchAvenues!==undefined&&!validAvenues(value.researchAvenues,nctId))return false;
 const ids=new Set<string>();
 for(let i=0;i<value.tasks.length;i++){
  const t=value.tasks[i];
  if(!object(t)||!idMatches(t,nctId)||!STATES.has(String(t.state))||
   !ACTIONS.has(String(t.action))||t.priorityOrder!==i+1||
   !safeText(t.reason)||!(t.rejectionReason==null||safeText(t.rejectionReason))||
   ids.has(String(t.id)))return false;
  ids.add(String(t.id));
 }
 for(const item of value.deferred){
  if(!object(item)||!idMatches(item,nctId)||item.state!=="NOT_YET_EXPECTED"||
   !safeText(item.reason)||ids.has(String(item.id)))return false;
  ids.add(String(item.id));
 }
 return true;
}
export default function AdvancedEvidenceResearchQueue({value,nctId}:{value:unknown;nctId:string}){
 if(!validAdvancedResearchQueue(value,nctId))
  return <p>Exact-trial advanced scientific research queue unavailable or unverified.</p>;
 const taskLine=(task:QueueTask)=><li key={task.id}>
  <strong>#{task.priorityOrder} · L{String(task.level).padStart(2,"0")} · {task.criterion}</strong>
  {" · "}{task.state} · {task.action}
  {task.rejectionReason&&" · Reason: "+task.rejectionReason}
 </li>;
 return <section aria-label="Levels 9 through 20 exact-trial evidence research queue">
  <h3>Scientific evidence research queue · Levels 9–20</h3>
  <p>Trial {nctId} · Snapshot {value.asOf} · {value.status}. Reviewed criteria: {value.reviewedCriteria}.
   Active source-review work items: {value.unresolvedCriteria}; deferred as not yet expected: {value.deferred.length}.</p>
  <p>Workflow order does not represent scientific importance, FDA approval probability, or validated assessment scores. Missing and unpublished items are not failures.</p>
  {value.status==="BLOCKED_UNVERIFIED_INTAKE"?
   <p>Verified trial phase and source cutoff are required before generating a research queue.</p>:
   value.tasks.length===0?
    <p>No active source-review gaps were produced. This does not mean any scientific level is validated.</p>:
    <>
     <ol>{value.tasks.slice(0,8).map(taskLine)}</ol>
     {value.tasks.length>8&&<details><summary>View remaining {value.tasks.length-8} evidence tasks</summary>
      <ol start={9}>{value.tasks.slice(8).map(taskLine)}</ol>
     </details>}
    </>}
  {value.researchAvenues&&<details><summary>Original-source research leads · Levels 9–20 (not searched)</summary>
   <p>Each link is only a starting point for independent source review. No search, retrieval, verification, clinical conclusion, or FDA application link has been established by this queue.</p>
   <ul>{Array.from({length:12},(_,i)=>i+9).map(n=>{
    const avenue=value.researchAvenues![String(n)];
    return <li key={n}><strong>L{String(n).padStart(2,"0")} · {avenue.sourceClass}</strong>
     <p>{avenue.instruction} {avenue.identityGate}</p>
     {avenue.sourceLeads.length>0?<ul>{avenue.sourceLeads.map(lead=>
      <li key={lead.url}><a href={lead.url} target="_blank" rel="noopener noreferrer">{lead.name}</a> · Not yet searched</li>
     )}</ul>:<p>Owner-controlled record required; no public source link can establish this evidence.</p>}
    </li>;
   })}</ul>
  </details>}
  {value.deferred.length>0&&<details><summary>{value.deferred.length} criteria not yet expected</summary>
   <ul>{value.deferred.map(item=><li key={item.id}>L{String(item.level).padStart(2,"0")} · {item.criterion}: {item.state}</li>)}</ul>
  </details>}
 </section>;
}

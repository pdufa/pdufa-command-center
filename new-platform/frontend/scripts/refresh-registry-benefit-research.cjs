"use strict";
/** Reproducible, source-pinned scheduled ClinicalTrials.gov research archive.
 * Reads 375 COMPLETED NCTs from the immutable dated Phase 3 census. It never
 * assigns commercial eligibility, FDA decisions or competitive ranks.
 */
const fs=require("node:fs/promises");
const path=require("node:path");
const ts=require("typescript");
const {createRequire}=require("node:module");
const sourceDir=path.join(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(
 ts.transpileModule(require("node:fs").readFileSync(file,"utf8"),{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}
 }).outputText,file
);
const {parsePhase3CensusCsv}=require(path.join(sourceDir,"lib/phase3-census-rows.ts"));
const {parseRegistryBenefitResearch}=require(path.join(sourceDir,"lib/registry-benefit-research.ts"));
const filename=path.join(sourceDir,"data/registry-benefit-research-snapshot.json");
const censusFile=path.join(sourceDir,"public/phase3-census-2026-10-26.csv");
const MAX_BYTES=800000;
const MAX_KEEP_MS=72*3600000;
const now=Date.now();
const startedAt=new Date(now).toISOString();
const sleep=t=>new Promise(resolve=>setTimeout(resolve,t));
const exact=(r,id)=>r&&r.nctId===id&&r.sourceUrl==="https://clinicaltrials.gov/study/"+id
  &&r.comparisonVerified===false&&r.benefitRank===null
  &&r.fdaDecisionVerified===false&&r.truncatedEvidence&&Array.isArray(r.primary)
  &&Array.isArray(r.seriousAdverseEvents)
  &&Number.isFinite(Date.parse(r.retrievedAt));
async function previousRecords(){
 try{
  const raw=JSON.parse(await fs.readFile(filename,"utf8"));
  if(raw.schemaVersion!==1||!Array.isArray(raw.records))return new Map();
  return new Map(raw.records.filter(x=>exact(x,x.nctId)).map(x=>[x.nctId,x]));
 }catch{return new Map();}
}
async function official(id){
 const url="https://clinicaltrials.gov/api/v2/studies/"+id;
 const response=await fetch(url,{method:"GET",redirect:"error",
   headers:{Accept:"application/json"},signal:AbortSignal.timeout(15000)});
 if(!response.ok||!(response.headers.get("content-type")||"").includes("json")
   ||Number(response.headers.get("content-length"))>MAX_BYTES)
  throw Error("UNAVAILABLE_OR_INVALID_SOURCE");
 const body=await response.text();
 if(body.length>MAX_BYTES)throw Error("SOURCE_TOO_LARGE");
 const packet=parseRegistryBenefitResearch(JSON.parse(body),id,new Date().toISOString());
 if(!exact(packet,id))throw Error("BAD_PACKET_IDENTITY");
 return packet;
}
async function main(){
 const census=parsePhase3CensusCsv(await fs.readFile(censusFile,"utf8"));
 const eligible=census.rows.filter(x=>x.status==="COMPLETED");
 if(eligible.length!==375)throw Error("PINNED_CENSUS_COMPLETED_COUNT_CHANGED");
 const previous=await previousRecords();
 let pointer=0,success=0,failures=0,reused=0;
 const output=new Map();
 async function worker(){
  for(;;){
   const index=pointer++;
   if(index>=eligible.length)break;
   const id=eligible[index].nctId;
   try{
    const result=await official(id);
    output.set(id,result);success++;
   }catch{
    failures++;
    const previousRecord=previous.get(id);
    if(exact(previousRecord,id)&&now-Date.parse(previousRecord.retrievedAt)<=MAX_KEEP_MS){
      output.set(id,previousRecord);reused++;
    }
   }
   await sleep(250);
  }
 }
 await Promise.all(Array.from({length:3},()=>worker()));
 if(success===0)throw Error("REGISTRY_REFRESH_NO_PRIMARY_SOURCE_SUCCESS");
 const records=eligible.map(x=>output.get(x.nctId)).filter(Boolean);
 const payload={schemaVersion:1,censusAsOf:"2026-10-26",scanStartedAt:startedAt,
  scanned:eligible.length,successful:success,failed:failures,
  reusedWithin72Hours:reused,records};
 const bytes=JSON.stringify(payload,null,2)+"\n";
 if(bytes.length>8_000_000)throw Error("RESEARCH_SOURCE_ARCHIVE_OVER_LIMIT");
 await fs.mkdir(path.dirname(filename),{recursive:true});
 await fs.writeFile(filename,bytes,{encoding:"utf8",flag:"w"});
 process.stdout.write(JSON.stringify({completed:true,scanned:eligible.length,successful:success,
   failed:failures,reused,records:records.length,withoutEvidence:eligible.length-records.length})+"\n");
}
main().catch(e=>{process.stderr.write("REGISTRY_RESEARCH_REFRESH_FAILED "+e.message+"\n");process.exitCode=1;});

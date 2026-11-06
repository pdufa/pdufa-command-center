import ledger from "../../../public/phase3-unified-classifications-2026-11-05.json";

export const dynamic="force-dynamic";
export const maxDuration=60;

/** Evidence-only registry collection; results posted is NOT a documented favorable outcome. */
type Registry={
 nctId:string;phase:string;registryStatus:string;sourceUpdated:string;
 interventionNames:string;drugInterventions:string;primaryOutcomes:string;primaryTimeframes:string;
 secondaryOutcomeCount:number|null;enrollment:number|null;enrollmentType:string;
 allocation:string;masking:string;comparators:string;
 registryResultsPosted:boolean|null;resultsFirstPosted:string;
 registryResultsOutcomeMeasureCount:number|null;statisticalAnalysesCount:number|null;
 adverseEventsPosted:boolean|null;protocolOrSAPDocuments:string;
 publicationPMIDs:string;internationalIds:string;registryUrl:string;
};
type FetchStatus={batch:number;status:"retrieved"|"failed";count:number;error?:string};
const names=[
 "NCT","Ticker","Company","Registry evidence fetched","Saved registry status","Live registry status",
 "Live registry updated","Phase","Registered intervention names","Registered drug names (not proof of efficacy)",
 "Primary endpoint(s)","Primary endpoint timeframe(s)","Number of secondary endpoints",
 "Enrollment","Enrollment type","Allocation","Masking","Comparator arms",
 "Registry results posted (not PASS)","Results first posted","Result outcome measures",
 "Statistical analyses posted","Adverse-event results posted","Public protocol / SAP documents",
 "Registry publication PMID(s)","International secondary ID(s)","ClinicalTrials.gov source URL"
];
const csv=(cell:unknown)=>{
 let s=cell===null||cell===undefined?"":String(cell).replace(/[\r\n]+/g," ");
 if(/^[=+@-]/.test(s))s="'"+s;
 return '"'+s.replace(/"/g,'""')+'"';
};
const row=(cells:unknown[])=>cells.map(csv).join(",");
const split=<T,>(a:readonly T[],size:number):T[][]=>
 Array.from({length:Math.ceil(a.length/size)},(_,i)=>a.slice(i*size,i*size+size) as T[]);
const sleep=(ms:number)=>new Promise<void>(resolve=>setTimeout(resolve,ms));

export async function loadLivePhase3Registry(){
 if(ledger.total!==762||ledger.rows.length!==762||new Set(ledger.rows.map(x=>x.nctId)).size!==762)
  throw Error("762-trial census integrity failed");
 const batches=split(ledger.rows.map(x=>x.nctId),25);
 const found=new Map<string,Registry>();
 const statuses:FetchStatus[]=[];
 let next=0;
 async function worker(){
  while(next<batches.length){
   const i=next++,batch=batches[i];
   const endpoint="https://clinicaltrials.gov/api/v2/studies?"+new URLSearchParams({
    "filter.ids":batch.join(","),pageSize:"100",format:"json"
   });
   let error="Not attempted",ok=false;
   for(let attempt=0;attempt<2&&!ok;attempt++){
    try {
     const response=await fetch(endpoint,{cache:"no-store",
      headers:{Accept:"application/json"},signal:AbortSignal.timeout(14000)});
     if(!response.ok){error="Registry HTTP "+response.status;if(response.status===429||response.status===503)await sleep(450*(attempt+1));continue;}
     const result=await response.json() as {studies?:Array<Record<string,unknown>>};
     if(!Array.isArray(result.studies)){error="Invalid registry response";continue;}
     for(const study of result.studies){
      const p=(study.protocolSection||{}) as Record<string,unknown>;
      const obj=(v:unknown)=>v&&typeof v==="object"&&!Array.isArray(v)?v as Record<string,unknown>:{};
      const arr=(v:unknown)=>Array.isArray(v)?v as Array<Record<string,unknown>>:[];
      const text=(v:unknown)=>v===null||v===undefined?"":String(v);
      const ident=obj(p.identificationModule),nct=text(ident.nctId);
      if(!batch.includes(nct))continue;
      const status=obj(p.statusModule),design=obj(p.designModule),
       designInfo=obj(design.designInfo),masking=obj(designInfo.maskingInfo),
       arms=obj(p.armsInterventionsModule),outcomes=obj(p.outcomesModule),
       refs=obj(p.referencesModule),results=obj(study.resultsSection),
       outcomeModule=obj(results.outcomeMeasuresModule),adverse=obj(results.adverseEventsModule),
       docs=obj(obj(study.documentSection).largeDocumentModule);
      const interventions=arr(arms.interventions);
      const primary=arr(outcomes.primaryOutcomes);
      const analytics=arr(outcomeModule.outcomeMeasures);
      const largeDocs=arr(docs.largeDocs);
      const completion=obj(status.resultsFirstPostDateStruct);
      const registryUrl="https://clinicaltrials.gov/study/"+nct;
      const registry:Registry={
       nctId:nct,
       phase:Array.isArray(design.phases)?design.phases.map(text).join("; "):"",
       registryStatus:text(status.overallStatus),
       sourceUpdated:text(obj(status.studyLastPostDateStruct).date),
       interventionNames:interventions.map(x=>text(x.name)).filter(Boolean).join("; "),
       drugInterventions:interventions.filter(x=>x.type==="DRUG").map(x=>text(x.name)).filter(Boolean).join("; "),
       primaryOutcomes:primary.map(x=>text(x.measure)).filter(Boolean).slice(0,6).join(" | "),
       primaryTimeframes:primary.map(x=>text(x.timeFrame)).filter(Boolean).slice(0,6).join(" | "),
       secondaryOutcomeCount:arr(outcomes.secondaryOutcomes).length,
       enrollment:Number(obj(design.enrollmentInfo).count)||null,
       enrollmentType:text(obj(design.enrollmentInfo).type),
       allocation:text(designInfo.allocation),
       masking:text(masking.masking),
       comparators:arr(arms.armGroups).filter(x=>/COMPARATOR|NO_INTERVENTION/.test(text(x.type)))
        .map(x=>text(x.type)+": "+text(x.label)).slice(0,8).join(" | "),
       registryResultsPosted:Boolean(study.hasResults),
       resultsFirstPosted:text(completion.date),
       registryResultsOutcomeMeasureCount:analytics.length,
       statisticalAnalysesCount:analytics.reduce((n,x)=>n+arr(x.analyses).length,0),
       adverseEventsPosted:Object.keys(adverse).length>0,
       protocolOrSAPDocuments:largeDocs.filter(x=>/PROTOCOL|SAP|STATISTICAL/i.test(text(x.type)))
        .map(x=>text(x.type)+" "+text(x.date)+" "+registryUrl).slice(0,8).join(" | "),
       publicationPMIDs:arr(refs.references).filter(x=>x.type==="RESULT"||x.type==="DERIVED")
        .map(x=>text(x.pmid)).filter(Boolean).slice(0,8).join("; "),
       internationalIds:arr(ident.secondaryIdInfos).map(x=>text(x.id)).filter(Boolean).slice(0,8).join("; "),
       registryUrl
      };
      found.set(nct,registry);
     }
     statuses.push({batch:i,status:"retrieved",count:result.studies.length});
     ok=true;
    }catch(e){error=e instanceof Error?e.message:String(e);if(attempt===0)await sleep(350);}
   }
   if(!ok)statuses.push({batch:i,status:"failed",count:0,error});
  }
 }
 await Promise.all(Array.from({length:5},()=>worker()));
 const rows=ledger.rows.map(original=>({original,registry:found.get(original.nctId)||null}));
 return {rows,statuses,failedBatches:statuses.filter(x=>x.status==="failed").length};
}

export async function GET(request:Request){
 let data:Awaited<ReturnType<typeof loadLivePhase3Registry>>;
 try{data=await loadLivePhase3Registry();}
 catch(e){return Response.json({error:e instanceof Error?e.message:"Registry audit failed"},{status:503});}
 const {rows,statuses,failedBatches}=data;
 const observed=rows.filter(r=>r.registry!==null);
 const summary={
  asOf:new Date().toISOString(),scope:"Official registry facts; DOES NOT establish clinical endpoint PASS/FAIL or FDA approval",
  census:762,studiesFetched:observed.length,studiesNotFetched:762-observed.length,
  batchCount:statuses.length,failedBatches,
  primaryOutcomesAvailable:observed.filter(r=>Boolean(r.registry?.primaryOutcomes)).length,
  drugInterventionsAvailable:observed.filter(r=>Boolean(r.registry?.drugInterventions)).length,
  registryResultsPosted:observed.filter(r=>r.registry?.registryResultsPosted===true).length,
  statisticalAnalysesAvailable:observed.filter(r=>(r.registry?.statisticalAnalysesCount||0)>0).length,
  protocolOrSAPDocuments:observed.filter(r=>Boolean(r.registry?.protocolOrSAPDocuments)).length,
  statusChanges:observed.filter(r=>r.registry!.registryStatus!==r.original.registryStatus).map(r=>({
   nctId:r.original.nctId,previous:r.original.registryStatus,current:r.registry!.registryStatus
  }))
 };
 const u=new URL(request.url);
 if(u.searchParams.get("format")==="json")
  return Response.json({summary,records:rows.map(r=>({
   nctId:r.original.nctId,ticker:r.original.ticker,
   savedRegistryStatus:r.original.registryStatus,
   sourceState:r.registry?"FETCHED":"UNAVAILABLE",...r.registry
  }))},{headers:{"Cache-Control":"no-store"}});
 const csvRows=[row(names),...rows.map(({original:r,registry:g})=>
  row([r.nctId,r.ticker,r.company,g?"FETCHED":"UNAVAILABLE",r.registryStatus,
   g?.registryStatus,g?.sourceUpdated,g?.phase,g?.interventionNames,g?.drugInterventions,
   g?.primaryOutcomes,g?.primaryTimeframes,g?.secondaryOutcomeCount,g?.enrollment,g?.enrollmentType,
   g?.allocation,g?.masking,g?.comparators,g?.registryResultsPosted,g?.resultsFirstPosted,
   g?.registryResultsOutcomeMeasureCount,g?.statisticalAnalysesCount,g?.adverseEventsPosted,
   g?.protocolOrSAPDocuments,g?.publicationPMIDs,g?.internationalIds,g?.registryUrl]))];
 if(csvRows.length!==763||names.length!==27)
  return Response.json({error:"Export shape mismatch"},{status:503});
 return new Response("\uFEFF"+csvRows.join("\r\n")+"\r\n",{
  headers:{
   "Content-Type":"text/csv; charset=utf-8",
   "Content-Disposition":'attachment; filename="Phase3-762-Live-Registry-Evidence-Backfill.csv"',
   "Cache-Control":"no-store",
   "X-Trials-Fetched":String(observed.length),
   "X-Failed-Registry-Batches":String(failedBatches)
  }
 });
}

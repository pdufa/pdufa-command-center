/**
 * One-off evidence discovery, never an automatic Phase 3 PASS/FAIL evaluator.
 * Trial identifiers are exact NCTs in the published 762-trial ledger.
 * External results are discovery leads until manually adjudicated.
 */
import fs from "node:fs/promises";
const ROOT=process.env.HARVEST_OUTPUT_DIR||"/vercel";
const BASE="https://pdufa-new-dashboard.vercel.app";
const NOW=new Date().toISOString();
const sleep=(n)=>new Promise(r=>setTimeout(r,n));
const url=(s)=>String(s||"");
async function fetchText(link,{timeout=18000,tries=2,headers={}}={}){
 let last;
 for(let i=0;i<tries;i++){
  try {
   const r=await fetch(link,{signal:AbortSignal.timeout(timeout),headers:{"User-Agent":"PDUFA trial research recheck (public research; contact OpenAI support)","Accept":"application/json,text/html,application/xml",...headers}});
   const t=await r.text();
   if(r.status===429||r.status===503){last="HTTP "+r.status;if(i+1<tries){await sleep((i+1)*1200);continue;}}
   return {ok:r.ok,status:r.status,text:t};
  }catch(e){last=String(e);if(i+1<tries)await sleep(700);}
 }
 return {ok:false,status:0,error:last,text:""};
}
async function json(link,opts){
 const x=await fetchText(link,opts);
 if(!x.ok)return {error:x.error||"HTTP "+x.status,status:x.status};
 try{return {data:JSON.parse(x.text),status:x.status};}catch(e){return {error:"JSON_PARSE_FAILURE",status:x.status};}
}
async function workers(arr,concurrency,fn){
 let cursor=0;
 await Promise.all(Array.from({length:concurrency},async()=>{
  while(cursor<arr.length){const i=cursor++;await fn(arr[i],i);}
 }));
}
const lead=await json(BASE+"/phase3-unified-classifications-2026-11-05.json");
if(!lead.data||lead.data.total!==762||lead.data.rows.length!==762)throw new Error("762-trial ledger unavailable or inconsistent");
const roster=lead.data.rows;
const rosterMap=new Map(roster.map(x=>[x.nctId,x]));
if(rosterMap.size!==762)throw new Error("Duplicate NCT in roster");
const records=Object.fromEntries(roster.map(x=>[x.nctId,{
 nctId:x.nctId,ticker:x.ticker,company:x.company,
 savedRegistryStatus:x.registryStatus,savedClassification:x.classificationCode,
 ctgov:{retrieved:false},pubmed:{candidatePMIDs:[],verifiedArticleMapping:false},sec:{mentions:null},sourceErrors:[]
}]));
const chunks=(a,n)=>Array.from({length:Math.ceil(a.length/n)},(_,i)=>a.slice(i*n,i*n+n));
const registryChunks=chunks(roster.map(x=>x.nctId),25);
let registryCalls=0,registryErrors=0;
await workers(registryChunks,4,async (part,i)=>{
 const target="https://clinicaltrials.gov/api/v2/studies?"+new URLSearchParams({"filter.ids":part.join(","),pageSize:"100",format:"json"});
 const r=await json(target,{timeout:24000,tries:2});registryCalls++;
 if(!r.data?.studies){registryErrors++;for(const id of part)records[id].sourceErrors.push("ClinicalTrials.gov "+(r.error||r.status));return;}
 for(const s of r.data.studies){
  const p=s.protocolSection||{},id=p.identificationModule?.nctId;
  if(!records[id])continue;
  const stat=p.statusModule||{},d=p.designModule||{},ai=p.armsInterventionsModule||{},out=p.outcomesModule||{};
  const results=s.resultsSection||{};
  const om=results.outcomeMeasuresModule?.outcomeMeasures||[];
  const doc=s.documentSection?.largeDocumentModule?.largeDocs||[];
  const refs=p.referencesModule?.references||[];
  records[id].ctgov={
   retrieved:true,url:"https://clinicaltrials.gov/study/"+id,
   registryStatus:stat.overallStatus||null,
   sourceLastUpdate:stat.studyFirstPostDateStruct?.date||null,
   studyLastUpdatePosted:stat.studyLastPostDateStruct?.date||null,
   phase:d.phases||[],
   primaryCompletion:stat.primaryCompletionDateStruct?.date||null,
   hasResults:Boolean(s.hasResults),resultsFirstPosted:stat.resultsFirstPostDateStruct?.date||null,
   interventions:(ai.interventions||[]).map(x=>({name:x.name,type:x.type})),
   primaryOutcome:(out.primaryOutcomes||[]).map(x=>({measure:x.measure,timeFrame:x.timeFrame})),
   secondaryOutcomeCount:(out.secondaryOutcomes||[]).length,
   enrollment:d.enrollmentInfo||null,
   allocation:d.designInfo?.allocation||null,masking:d.designInfo?.maskingInfo?.masking||null,
   resultsOutcomeMeasureCount:om.length,
   resultsAnalysisCount:om.reduce((n,x)=>n+(x.analyses?.length||0),0),
   adverseEventsPosted:Boolean(results.adverseEventsModule),
   documents:doc.slice(0,5).map(x=>({type:x.type,documentDate:x.date,url:x.url||null})),
   publicationReferences:refs.filter(x=>x.type==="RESULT"||x.type==="DERIVED").slice(0,8)
     .map(x=>({pmid:x.pmid||null,type:x.type,citation:x.citation||""})),
   secondaryIds:(p.identificationModule?.secondaryIdInfos||[]).map(x=>x.id),
   sponsor:p.sponsorCollaboratorsModule?.leadSponsor?.name||null
  };
 }
 for(const id of part)if(!records[id].ctgov.retrieved)records[id].sourceErrors.push("Study not returned in ClinicalTrials.gov batch");
});
const eutils="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/";
const pubmedQueries=chunks(roster.map(x=>x.nctId),20);
let pubmedCallCount=0,pubmedErrors=0;
const candidatePmids=new Set();
for(let i=0;i<pubmedQueries.length;i++){
 const part=pubmedQueries[i];
 const term=part.map(id=>'"'+id+'"[All Fields]').join(" OR ");
 const r=await json(eutils+"esearch.fcgi?"+new URLSearchParams({db:"pubmed",term,retmode:"json",retmax:"600",tool:"pdufa_trial_evidence_audit"}),{timeout:30000,tries:2});
 pubmedCallCount++;
 if(!r.data?.esearchresult){pubmedErrors++;continue;}
 for(const pmid of (r.data.esearchresult.idlist||[]))candidatePmids.add(pmid);
 await sleep(400);
}
// Match exact NCT string inside public PubMed XML. Articles may refer to several trials.
// This generates candidate article links, NOT success/failure conclusions.
let pubmedArticleCount=0,pubmedArticleNctMatches=0,pubmedXmlErrors=0;
for(const group of chunks([...candidatePmids],50)){
 const q=await fetchText(eutils+"efetch.fcgi?"+new URLSearchParams({db:"pubmed",id:group.join(","),rettype:"xml",retmode:"xml",tool:"pdufa_trial_evidence_audit"}),{timeout:36000,tries:2});
 if(!q.ok){pubmedXmlErrors++;continue;}
 const blocks=q.text.match(/<PubmedArticle[\s\S]*?<\/PubmedArticle>/g)||[];
 for(const block of blocks){
  pubmedArticleCount++;
  const pmid=block.match(/<PMID[^>]*>(\d+)<\/PMID>/)?.[1];
  const found=[...new Set(block.match(/\bNCT\d{8}\b/gi)||[])];
  for(const nct of found){
   const r=records[nct.toUpperCase()];
   if(r&&pmid){
    r.pubmed.candidatePMIDs.push(pmid);
    r.pubmed.verifiedArticleMapping=true;
    pubmedArticleNctMatches++;
   }
  }
 }
 await sleep(400);
}
let secCalls=0,secErrors=0,secRateLimited=0;
await workers(roster,4,async (trial,i)=>{
 const id=trial.nctId;
 const target="https://efts.sec.gov/LATEST/search-index?"+new URLSearchParams({q:'"'+id+'"',forms:"8-K,10-K,10-Q,6-K,20-F,40-F",from:"0",size:"4"});
 const r=await json(target,{timeout:22000,tries:2});secCalls++;
 if(r.status===429)secRateLimited++;
 if(!r.data?.hits){secErrors++;records[id].sourceErrors.push("SEC EFTS "+(r.error||r.status));}
 else {
  const hits=r.data.hits.hits||[];
  records[id].sec={
   mentions:r.data.hits.total?.value||0,
   examples:hits.slice(0,3).map(x=>({id:x._id,date:x._source?.file_date||null,
    form:x._source?.form||null,filingEntity:x._source?.display_names?.[0]||null})),
   searchUrl:"https://www.sec.gov/edgar/search/#/q="+encodeURIComponent(id)
  };
 }
 await sleep(470);
});
const sourceProbes={};
const probeLinks={
 aact:"https://aact.ctti-clinicaltrials.org/landing",
 ctis:"https://euclinicaltrials.eu/ctis-public/search",
 ctisUnauthenticatedAPI:"https://euclinicaltrials.eu/ctis-public-api/search?query=NCT05021536",
 priorEU:"https://www.clinicaltrialsregister.eu/ctr-search/search?query=NCT05021536",
 who:"https://trialsearch.who.int/?Term=NCT05021536",
 fdaDrugs:"https://api.fda.gov/drug/drugsfda.json?search="+encodeURIComponent("products.brand_name:RELYVRIO")+"&limit=3",
 fdaCRL:"https://api.fda.gov/transparency/crl.json?limit=1"
};
await workers(Object.entries(probeLinks),4,async ([name,url])=>{
 const r=await fetchText(url,{timeout:16000,tries:1});
 sourceProbes[name]={httpStatus:r.status,reachable:r.ok,contentType:r.text.slice(0,1)==="{"?"JSON":"HTML/other",
  limitation:name==="aact"?"AACT relational cloud credentials needed for query":
   ["ctis","priorEU","who"].includes(name)?"Public portal: cannot assert exact NCT matches from homepage":
   name==="ctisUnauthenticatedAPI"?"Not an unauthenticated public API":
   name.startsWith("fda")?"No direct NCT-to-application crosswalk; brand name alone does not establish FDA status":
   null};
});
const all=Object.values(records),have=r=>Boolean(r.ctgov.retrieved);
const sum=(fn)=>all.filter(fn).length;
const summary={
 generatedAt:NOW,censusAsOf:lead.data.asOf,
 scope:"Live online source discovery for all 762 saved NCTs. Candidate links never constitute verified Phase 3 PASS/FAIL, FDA actions, PDUFA dates or calibrated predictions.",
 roster:762,uniqueNcts:rosterMap.size,
 clinicalTrials:{
  batchQueries:registryCalls,batchErrors:registryErrors,
  studiesRetrieved:sum(have),
  statusesChangedFromSaved:sum(r=>have(r)&&r.ctgov.registryStatus!==r.savedRegistryStatus),
  unknownStatusStillUnknown:sum(r=>have(r)&&r.ctgov.registryStatus==="UNKNOWN"),
  interventionNamesRecovered:sum(r=>have(r)&&r.ctgov.interventions.length>0),
  primaryOutcomeAvailable:sum(r=>have(r)&&r.ctgov.primaryOutcome.length>0),
  postedResultsAvailable:sum(r=>have(r)&&r.ctgov.hasResults),
  postedStatisticalAnalyses:sum(r=>have(r)&&r.ctgov.resultsAnalysisCount>0),
  publicDocumentsFound:sum(r=>have(r)&&r.ctgov.documents.length>0),
  publicationReferences:sum(r=>have(r)&&r.ctgov.publicationReferences.length>0),
  foreignSecondaryIds:sum(r=>have(r)&&r.ctgov.secondaryIds.length>0)
 },
 pubMed:{searchQueries:pubmedCallCount,queryErrors:pubmedErrors,articleIdsFromSearch:candidatePmids.size,articlesParsed:pubmedArticleCount,
  articleCrossReferencesMatched:pubmedArticleNctMatches,studiesWithExactNctArticleMention:sum(r=>r.pubmed.candidatePMIDs.length>0),
  xmlErrors:pubmedXmlErrors},
 sec:{exactNctQueries:secCalls,queryErrors:secErrors,rateLimitResponses:secRateLimited,
  studiesWithExactIdFilingMentions:sum(r=>(r.sec.mentions||0)>0),
  totalMatchingFilingMentions:all.reduce((n,r)=>n+(r.sec.mentions||0),0)},
 probes:sourceProbes,
 reconciliationNeeded:{
  unknownRegistry:all.filter(r=>r.ctgov.registryStatus==="UNKNOWN").map(r=>r.nctId),
  changedRegistry:all.filter(r=>have(r)&&r.ctgov.registryStatus!==r.savedRegistryStatus)
   .slice(0,50).map(r=>({nctId:r.nctId,old:r.savedRegistryStatus,current:r.ctgov.registryStatus})),
  studiesWithPostedResults:all.filter(r=>have(r)&&r.ctgov.hasResults).map(r=>r.nctId)
 },
 caveats:[
  "AACT mirrors ClinicalTrials.gov but requires its own cloud account to run SQL in this audit",
  "PUBMED exact NCT mentions are citation discovery only; not endpoint adjudications",
  "SEC exact NCT mentions are filing leads only, never automated PASS/FAIL",
  "FDA drug names and sponsor filings require exact drug/indication/application mapping",
  "CTIS, EUCTR and WHO web pages are accessible but mapping international identifiers is a separate step",
  "Registry COMPLETED, UNKNOWN, TERMINATED do not establish clinical outcome"
 ]
};
const output={schemaVersion:1,summary,records:all};
await fs.writeFile(ROOT+"/phase3-six-source-harvest-20261105.json",JSON.stringify(output));
await fs.writeFile(ROOT+"/phase3-six-source-harvest-summary-20261105.json",JSON.stringify(summary,null,2)+"\n");
console.log(JSON.stringify({output:ROOT+"/phase3-six-source-harvest-20261105.json",summary}));

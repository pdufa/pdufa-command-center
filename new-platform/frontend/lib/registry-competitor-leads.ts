/** Candidate competitor discovery from the *existing* dated Phase 3 registry archive.
 * Exact shared condition term creates a research LEAD only, never a verified
 * head-to-head comparator, commercial competitor, or competitive advantage.
 * Historical trials are not assumed to be active or FDA-qualified.
 */
import type {RegistryBenefitResearch} from "./registry-benefit-research";
export type RegistryPeerLead={
  nctId:string;therapy:string;sharedConditions:string[];resultsPosted:boolean;
  sourceUrl:string;retrievedAt:string;
};
export type RegistryPeerLeads={
  nctId:string;status:"RESEARCH_LEADS_ONLY";totalCandidates:number;
  displayed:RegistryPeerLead[];truncated:boolean;
};
const clean=(s:string)=>s.toLowerCase().replace(/\s+/g," ").trim();
const controls=new Set(["placebo","vehicle","sham","standard of care","best supportive care"]);
function therapies(item:RegistryBenefitResearch):string[]{
  return [...new Set(item.interventions.map(clean).filter(v=>v.length>2&&!controls.has(v)))];
}
function commonConditions(a:RegistryBenefitResearch,b:RegistryBenefitResearch):string[]{
  const target=new Set(a.conditionNames.map(clean).filter(v=>v.length>=5));
  return [...new Set(b.conditionNames.filter(n=>target.has(clean(n))))];
}
export function discoverRegistryPeerLeads(
  records:readonly RegistryBenefitResearch[],maxPerTrial=8
):Record<string,RegistryPeerLeads>{
  if(!Number.isSafeInteger(maxPerTrial)||maxPerTrial<1||maxPerTrial>30)
    throw Error("INVALID_PEER_LEAD_LIMIT");
  if(records.length>375)throw Error("UNBOUNDED_REGISTRY_PEER_SOURCE");
  const seen=new Set<string>(),output:Record<string,RegistryPeerLeads>={};
  for(const item of records){
    if(!/^NCT\d{8}$/.test(item.nctId)||seen.has(item.nctId)||
      item.sourceUrl!=="https://clinicaltrials.gov/study/"+item.nctId)
      throw Error("PEER_IDENTITY_INVALID");
    seen.add(item.nctId);
  }
  for(const trial of records){
    const own=therapies(trial);
    const candidates:RegistryPeerLead[]=[];
    if(!own.length||!trial.conditionNames.length){output[trial.nctId]={
      nctId:trial.nctId,status:"RESEARCH_LEADS_ONLY",totalCandidates:0,displayed:[],truncated:false
    };continue;}
    for(const other of records){
      if(other.nctId===trial.nctId)continue;
      const shared=commonConditions(trial,other);
      const drugs=therapies(other);
      if(!shared.length||!drugs.length)continue;
      // Do not label a separate study of the same experimental intervention as a rival.
      const distinct=drugs.filter(t=>!own.includes(t));
      if(!distinct.length)continue;
      candidates.push({nctId:other.nctId,therapy:distinct.join(" / ").slice(0,220),
        sharedConditions:shared.slice(0,5),resultsPosted:other.resultsPosted,
        sourceUrl:other.sourceUrl,retrievedAt:other.retrievedAt});
    }
    candidates.sort((a,b)=>Number(b.resultsPosted)-Number(a.resultsPosted)||a.nctId.localeCompare(b.nctId));
    output[trial.nctId]={nctId:trial.nctId,status:"RESEARCH_LEADS_ONLY",
      totalCandidates:candidates.length,displayed:candidates.slice(0,maxPerTrial),
      truncated:candidates.length>maxPerTrial};
  }
  return output;
}

/** Snapshot-wide progress metrics. These count historical registry lead
 * suggestions, NOT validated active competitors or comparable trial outcomes.
 * Completeness is restricted to the dated, 375-study research archive.
 */
export type RegistryPeerDiscoverySummary={
  scope:"HISTORICAL_375_PHASE3_REGISTRY_ARCHIVE";
  studiesInArchive:number;studiesWithPostedResults:number;
  studiesWithConditionMatchedLeads:number;postedResultStudiesWithLeads:number;
  totalMatchedStudyLinks:number;validatedClinicalComparisons:0;
  stockAppreciationRanks:0;
};
export function summarizeRegistryPeerLeads(
  records:readonly RegistryBenefitResearch[],
  leads:Record<string,RegistryPeerLeads>
):RegistryPeerDiscoverySummary{
  if(records.length!==Object.keys(leads).length||records.length>375)
    throw Error("PEER_SUMMARY_ARCHIVE_MISMATCH");
  let studiesWithConditionMatchedLeads=0,postedResultStudiesWithLeads=0;
  let totalMatchedStudyLinks=0;
  for(const row of records){
    const item=leads[row.nctId];
    if(!item||item.status!=="RESEARCH_LEADS_ONLY"||
       !Number.isSafeInteger(item.totalCandidates)||item.totalCandidates<0)
      throw Error("PEER_SUMMARY_INVALID");
    totalMatchedStudyLinks+=item.totalCandidates;
    if(item.totalCandidates){
      studiesWithConditionMatchedLeads++;
      if(row.resultsPosted)postedResultStudiesWithLeads++;
    }
  }
  return {scope:"HISTORICAL_375_PHASE3_REGISTRY_ARCHIVE",
    studiesInArchive:records.length,
    studiesWithPostedResults:records.filter(row=>row.resultsPosted).length,
    studiesWithConditionMatchedLeads,postedResultStudiesWithLeads,
    totalMatchedStudyLinks,validatedClinicalComparisons:0,
    stockAppreciationRanks:0};
}

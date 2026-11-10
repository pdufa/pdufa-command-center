/** MAIN R69: source-only publication leads listed in retained original
 * ClinicalTrials.gov referencesModule. DERIVED references are merely citations
 * associated with the NCT record; not independently confirmed exact trial
 * pivotal outcomes, scientific results, FDA decisions or reviewer signatures.
 */
import raw from "../data/focus-r69-original-pubmed-leads.json";
import {FOCUS_R68_EVIDENCE_RECOVERY} from "./focus-r68-evidence-recovery";

const SOURCE_SHA="8b11d9f7e6f8896286944a454569b59cac9d63c5350fcb9665e6ff47e5519e77";
const PMIDS_BY_NCT:Record<string,string>={
  NCT02500381:"40098309,34105177",
  NCT04871282:"42848980",
  NCT05126758:"42526472",
  NCT05662241:"42233621,41840328",
  NCT06081894:"42667274,42663312,42663111",
  NCT06153693:"40587141",
  NCT06343779:"42849489"
};
type Compact={
 schema:string;run:number;artifact:number;originalR69Sha256:string;
 rows:unknown[];
};
export function buildR69RegistryPublicationLeads(input:unknown=raw){
 const prior=FOCUS_R68_EVIDENCE_RECOVERY;
 if(!prior||prior.uniqueTrials!==29||
    prior.provisionalApplicationCycles!==23||
    prior.trialsWithoutCurrentPostedPrimary!==17||
    prior.validatedFDAForecasts!==0||
    prior.independentClinicalGrades!==0||
    prior.allFutureFdaOutcomes!=="ABSTAIN"||
    prior.historicalPredictionAccuracy!==null||
    prior.sourceMissingDoesNotMeanTrialFailure!==true||
    prior.noWritesToHistoricalOutcomesOrProduction!==true||
    !input||typeof input!=="object"||Array.isArray(input))return null;
 const d=input as Compact;
 if(Object.keys(d).sort().join("|")!==
      ["artifact","originalR69Sha256","rows","run","schema"].join("|")||
    d.schema!=="MAIN_R69_COMPACT_UNVERIFIED_ORIGINAL_REGISTRY_PUBLICATION_LEADS"||
    d.run!==42727350931||d.artifact!==13723526354||
    d.originalR69Sha256!==SOURCE_SHA||
    !Array.isArray(d.rows)||d.rows.length!==17)return null;
 const sources=new Map(prior.rows.map(r=>[r.nct,r]));
 if(sources.size!==29)return null;
 const seen=new Set<string>(),allPubmed=new Set<string>();
 let linkedTrials=0;
 const cases=[];
 for(const item of d.rows){
  if(!Array.isArray(item)||item.length!==2||
     typeof item[0]!=="string"||!/^NCT\d{8}$/.test(item[0])||
     seen.has(item[0])||!Array.isArray(item[1])||
     item[1].length>10)return null;
  const nct=item[0];
  const missing=sources.get(nct);
  if(!missing||missing.sourcePrimaryTableAvailable||
     missing.officialFutureFdaOutcome!=="ABSTAIN"||
     missing.scientificAssessmentLevel!=="UNASSESSED_SOURCE_ONLY"||
     missing.qualifiedReviewerSigned!==false||missing.clinicalScienceScore!==null||
     missing.originalRegistrySHA256.length!==64)return null;
  const pmids=item[1];
  if(pmids.some(x=>typeof x!=="string"||!/^[1-9]\d{5,9}$/.test(x))||
     pmids.join(",")!==(PMIDS_BY_NCT[nct]??""))return null;
  seen.add(nct);
  if(pmids.length)linkedTrials++;
  const links=pmids.map((id:string)=>{
   if(allPubmed.has(id))return null;
   allPubmed.add(id);
   return {
    pmid:id,
    pubmedUrl:"https://pubmed.ncbi.nlm.nih.gov/"+id+"/",
    registryCitationType:"DERIVED" as const,
    exactNctPaperMatchVerified:false,
    paperContainsPivotalEndpointVerified:false,
    articleBodyIndependentlyReviewed:false,
    qualifiedScientificReviewerSigned:false,
    clinicalResult:null,
   };
  });
  if(links.some(x=>x===null))return null;
  cases.push({
   nct,ticker:missing.ticker,applicationCycles:[...missing.applicationCycles],
   sourceUpdatedDate:missing.originalSourceUpdatedDate,
   sourceRegistryUrl:missing.sourceRegistryUrl,
   originalRegistrySHA256:missing.originalRegistrySHA256,
   sourcePrimaryTablePostedInRetainedRecord:false,
   sourceReferenceLeads:links as NonNullable<typeof links[number]>[],
   referenceLeadStatus:pmids.length?
     "UNVERIFIED_REGISTRY_DERIVED_PUBLICATION_REFERENCE" as const:
     "NO_PUBMED_REFERENCE_IN_RETAINED_REGISTRY" as const,
   independentExactStudyMatchVerified:false,
   independentlyVerifiedPivotalStudyOutcome:null,
   qualifiedReviewerSigned:false,
   scientificMethodGrade:null,
   futureFDAOutcome:"ABSTAIN" as const,
  });
 }
 if(seen.size!==17||linkedTrials!==7||allPubmed.size!==11||
    Object.keys(PMIDS_BY_NCT).length!==7||
    [...sources.values()].filter(x=>!x.sourcePrimaryTableAvailable).some(x=>!seen.has(x.nct)))
    return null;
 return {
  schema:"MAIN_R69_UNREVIEWED_EXACT_SOURCE_PUBLICATION_LEADS" as const,
  originalResearchRun:d.run,originalResearchArtifact:d.artifact,
  sourceArchiveUrl:"https://github.com/pdufa/pdufa-command-center/actions/runs/"+
   d.run+"/artifacts/"+d.artifact,
  originalResearchSha256:SOURCE_SHA,
  exactNctsInResearch:29,
  provisionalApplications:23,
  retainedRegistryPrimaryMissingNcts:17,
  casesWithUnverifiedPublicationLeads:7,
  casesWithoutPubmedLeadsInArchive:10,
  candidateReferenceCount:11,
  cases,
  paperTextIndependentReviews:0,
  exactNctPivotalOutcomeVerified:0,
  scientificReviewSignoffs:0,
  fdaForecastsValidated:0,
  measuredForecastAccuracy:null,
  futureFdaOutcome:"ABSTAIN" as const,
  registryReferenceIsNotOriginalPivotalStudyResults:true,
  originalSourceOnlyNoNetworkOrProductionWrites:true,
 };
}
export const FOCUS_R69_REGISTRY_PUBLICATION_LEADS=buildR69RegistryPublicationLeads();

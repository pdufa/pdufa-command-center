/** MAIN R70 source-only PubMed metadata/abstract inspection.
 * All 11 original article titles, DOI and NCT accession relationships come
 * from original NLM XML digest and separate immutable R69 source receipt.
 * Article-level text/source labels are not independent clinical science grades,
 * time-frozen forecasts, medical reviewer signoffs or full-text validation.
 */
import source from "../data/focus-r70-verified-pubmed-metadata-source.json";
import {FOCUS_R69_REGISTRY_PUBLICATION_LEADS} from "./focus-r69-original-publication-leads";
import {FOCUS_R68_EVIDENCE_RECOVERY} from "./focus-r68-evidence-recovery";

const REPORT_SHA="03434b975e511b2d603227bab3e25768dbcc3a0e7b412d479d9afbd100cd2577";
const XML_SHA="2aa5fac13c7741d7ed2d9b1c2d91101978661150c87324b566b88f75994e394b";
const NCT=/^NCT\d{8}$/;
const PMID=/^[1-9]\d{5,9}$/;
type ArticleRow=[string,string,string,string,string|null,boolean,boolean,string[],string[]];
type Snapshot={
 schema:string;run:number;artifact:number;originalResearchSha256:string;
 originalPubmedXmlSha256:string;entries:ArticleRow[];
};
export function buildR70SourceArticleView(input:unknown=source){
 const prior=FOCUS_R69_REGISTRY_PUBLICATION_LEADS;
 const original=FOCUS_R68_EVIDENCE_RECOVERY;
 if(!prior||!original||
    prior.exactNctsInResearch!==29||prior.provisionalApplications!==23||
    prior.retainedRegistryPrimaryMissingNcts!==17||
    prior.casesWithUnverifiedPublicationLeads!==7||
    prior.candidateReferenceCount!==11||
    prior.paperTextIndependentReviews!==0||
    prior.exactNctPivotalOutcomeVerified!==0||
    prior.scientificReviewSignoffs!==0||
    prior.fdaForecastsValidated!==0||
    prior.futureFdaOutcome!=="ABSTAIN"||
    prior.registryReferenceIsNotOriginalPivotalStudyResults!==true||
    original.uniqueTrials!==29||original.provisionalApplicationCycles!==23||
    original.validatedFDAForecasts!==0||
    original.allFutureFdaOutcomes!=="ABSTAIN"||
    !input||typeof input!=="object"||Array.isArray(input))return null;
 const d=input as Snapshot;
 if(Object.keys(d).sort().join("|")!==
       ["artifact","entries","originalPubmedXmlSha256","originalResearchSha256","run","schema"].join("|")||
    d.schema!=="MAIN_R70_ORIGINAL_PUBMED_METADATA_DISPLAY_ONLY"||
    d.run!==42729546458||d.artifact!==13724930108||
    d.originalResearchSha256!==REPORT_SHA||
    d.originalPubmedXmlSha256!==XML_SHA||
    !Array.isArray(d.entries)||d.entries.length!==11)return null;
 const expected=new Map<string,string>();
 for(const study of prior.cases)
  for(const lead of study.sourceReferenceLeads){
   if(expected.has(lead.pmid)||study.futureFDAOutcome!=="ABSTAIN"||
      study.qualifiedReviewerSigned!==false)return null;
   expected.set(lead.pmid,study.nct);
  }
 if(expected.size!==11)return null;
 const found=new Set<string>();
 const studies=new Map<string,ReturnType<typeof articleRow>[]>();
 let articleText=0,accessionOnly=0;
 function articleRow(r:ArticleRow){
   const [nct,pmid,title,journal,doi,inArticleText,inDatabankOnly,pubtypes,sourceWords]=r;
   const isTrialPhase2=pubtypes.some(t=>/Clinical Trial, Phase I$|Clinical Trial, Phase II$/.test(t));
   const isTrialPhase3=pubtypes.includes("Clinical Trial, Phase III");
   const titleProtocol=/\bprotocol\b/i.test(title);
   const titlePhase2=/\bphase\s*(?:II|2)\b/i.test(title);
   const metadataCautions=[
      ...(inDatabankOnly?["Only databank NCT cross-reference; study identity not in title/abstract"]:[]),
      ...(isTrialPhase2?["PubMed indexed as Phase I/II; not an independently adjudicated pivotal Phase III report"]:[]),
      ...(titlePhase2?["Title identifies Phase 2 component; cannot substitute for Phase 3 results"]:[]),
      ...(titleProtocol?["Title indicates a protocol/methods article, not established result report"]:[]),
      ...(isTrialPhase3?["PubMed indexed Phase III; exact pivotal endpoint and signed SAP still require review"]:[]),
      ...(sourceWords.includes("EXPLORATORY_OR_SECONDARY_TERM")?
        ["Exploratory or secondary terms appear in source abstract; prevent duplicate primary-outcome counting"]:[]),
   ];
   return {nct,pmid,title,journal,doi,
     pubmedUrl:"https://pubmed.ncbi.nlm.nih.gov/"+pmid+"/",
     articleTextExplicitExactNct:inArticleText,
     pubmedDatabankOnlyExactNct:inDatabankOnly,
     pubmedPublicationTypes:[...pubtypes],
     machineLiteralArticleScopeFlags:[...sourceWords],
     metadataCautions,
     isPhase3PivotalEfficacyIndependentlyAdjudicated:false as const,
     isFullTextIndependentlyReviewed:false as const,
     hasSourceDatesLockedAgainstPredictions:false as const,
     hasVerifiedOriginalPreUnblindingSAP:false as const,
     scientificGrade:null,
     qualifiedReviewerSigned:false as const,
     futureFdaOutcome:"ABSTAIN" as const,
   };
 }
 for(const row of d.entries){
   if(!Array.isArray(row)||row.length!==9)return null;
   const [nct,pmid,title,journal,doi,inText,inDbOnly,pubtypes,words]=row;
   if(typeof nct!=="string"||!NCT.test(nct)||
      typeof pmid!=="string"||!PMID.test(pmid)||
      expected.get(pmid)!==nct||found.has(pmid)||
      typeof title!=="string"||title.length<5||title.length>700||
      typeof journal!=="string"||journal.length<3||journal.length>240||
      (doi!==null&&(typeof doi!=="string"||!/^10\.[^\s]{3,170}$/.test(doi)))||
      typeof inText!=="boolean"||typeof inDbOnly!=="boolean"||
      inText===inDbOnly||!Array.isArray(pubtypes)||!Array.isArray(words)||
      pubtypes.some(x=>typeof x!=="string"||x.length>130)||
      words.some(x=>typeof x!=="string"||![
       "PHASE_1_OR_2_TERM","PHASE_3_TERM","PROTOCOL_OR_METHODS_TERM",
       "PRIMARY_ENDPOINT_TERM","EXPLORATORY_OR_SECONDARY_TERM"].includes(x)))return null;
   found.add(pmid);
   articleText+=Number(inText);
   accessionOnly+=Number(inDbOnly);
   const article=articleRow(row);
   studies.set(nct,[...(studies.get(nct)??[]),article]);
 }
 if(found.size!==11||articleText!==8||accessionOnly!==3||studies.size!==7||
    prior.cases.some(x=>(studies.get(x.nct)?.length??0)!==x.sourceReferenceLeads.length))return null;
 return {
   schema:"MAIN_R70_NLM_ORIGINAL_ARTICLE_METADATA_REVIEW_ONLY" as const,
   sourceArchiveRun:d.run,sourceArchiveArtifact:d.artifact,
   sourceResearchSha256:REPORT_SHA,
   originalXmlSha256:XML_SHA,
   sourceArchiveUrl:"https://github.com/pdufa/pdufa-command-center/actions/runs/"+
     d.run+"/artifacts/"+d.artifact,
   originalPubmedRecordsRetrieved:11,
   trialsWithListedReferences:7,
   primaryMissingCurrentRegistryTrials:17,
   originalNctStudyLinkedByPubmedDatabase:11,
   exactNctMentionedInTitleOrAbstract:8,
   exactNctOnlyLinkedByDatabank:3,
   studies:[...studies.entries()].map(([nct,articles])=>({nct,articles})),
   independentlyAdjudicatedPivotalPrimaryPublications:0,
   originalFullTextHumanReviews:0,
   signedStatisticalScienceGrades:0,
   validatedFDAForecasts:0,
   measuredAccuracy:null,
   futureFDAOutcome:"ABSTAIN" as const,
   sourceOnlyNoHistoricalOutcomeOrProductionWrites:true,
 };
}
export const FOCUS_R70_ARTICLE_SOURCE=buildR70SourceArticleView();

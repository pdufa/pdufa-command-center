/** MAIN R64: source-locked, read-only view of the original R63 eight-domain
 * page leads. NOT scientific assessments, completed 800 tests, clinical grades,
 * FDA approval/CRL predictions or historical accuracy.
 */
import rawSnapshot from "../data/focus-r64-original-method-pages.json";
import {FOCUS_R60_ORIGINAL_TRIAL_REVIEW} from "./focus-r60-original-trial-research";
import {FOCUS_PRELIMINARY_R39} from "./focus-preliminary-application-research";

export const EIGHT_SOURCE_DOMAINS = [
  {key:"PRIMARY_ENDPOINT",label:"Primary endpoint"},
  {key:"ESTIMAND_ANALYSIS_POPULATION",label:"Estimand and analysis population"},
  {key:"STATISTICAL_MODEL",label:"Statistical model"},
  {key:"MULTIPLICITY_CONTROL",label:"Multiplicity control"},
  {key:"MISSING_DATA_INTERCURRENT_EVENTS",label:"Missing data and intercurrent events"},
  {key:"SENSITIVITY_ANALYSIS",label:"Sensitivity analysis"},
  {key:"ADVERSE_EVENTS_SAFETY",label:"Adverse events and safety"},
  {key:"PROTOCOL_SAP_VERSION_CHANGES",label:"Protocol/SAP version changes"}
] as const;

const R63_SHA="b39028e972c45949147d405c447af45ef8ceab7089d8e89247cacd1d2cef6a18";
const R63_RUN=42713443428;
const R63_ARTIFACT=13717655352;
const NCT=/^NCT\d{8}$/;
const FILE=/^(?:Prot|SAP|Prot_SAP)_\d{3}\.pdf$/;
type Doc=[string,string];
type Ref=[number,number];
type TrialPages=[string,Ref[][]];
type PageIndex={
  rev:number;originalRun:number;originalArtifact:number;originalR63Sha256:string;
  docs:Doc[];trialPageLeads:TrialPages[];
};
export function buildR64OriginalMethodPageView(input:unknown=rawSnapshot){
  const research=FOCUS_R60_ORIGINAL_TRIAL_REVIEW;
  if(!research||research.counts.uniqueNcts!==29||
     research.counts.applicationGroups!==23||
     research.counts.independentlyValidatedFdaForecasts!==0||
     research.allOfficialFDAForecasts!=="ABSTAIN"||
     research.predictionAccuracy!==null||
     FOCUS_PRELIMINARY_R39.trials.length!==29||
     FOCUS_PRELIMINARY_R39.applications.length!==23||
     FOCUS_PRELIMINARY_R39.summary.independentlyValidatedFDAForecasts!==0||
     !input||typeof input!=="object"||Array.isArray(input))return null;
  const data=input as PageIndex;
  const keys=new Set(["rev","originalRun","originalArtifact","originalR63Sha256","docs","trialPageLeads"]);
  if(Object.keys(data).some(k=>!keys.has(k))||
     data.rev!==64||data.originalRun!==R63_RUN||
     data.originalArtifact!==R63_ARTIFACT||data.originalR63Sha256!==R63_SHA||
     !Array.isArray(data.docs)||data.docs.length!==22||
     !Array.isArray(data.trialPageLeads)||data.trialPageLeads.length!==12)return null;

  const sourceMap=new Map(research.trials.map(t=>[t.nct,t]));
  if(sourceMap.size!==29)return null;
  const docs=new Set<string>();
  for(const doc of data.docs){
    if(!Array.isArray(doc)||doc.length!==2||
       typeof doc[0]!=="string"||!NCT.test(doc[0])||
       typeof doc[1]!=="string"||!FILE.test(doc[1])||
       !sourceMap.has(doc[0]))return null;
    const key=doc.join("/");
    if(docs.has(key))return null;
    docs.add(key);
  }

  const byNct=new Map<string,Ref[][]>();
  const linkedDocs=new Set<number>();
  let leads=0;
  for(const trial of data.trialPageLeads){
    if(!Array.isArray(trial)||trial.length!==2||
       typeof trial[0]!=="string"||!NCT.test(trial[0])||
       !sourceMap.has(trial[0])||byNct.has(trial[0])||
       !Array.isArray(trial[1])||trial[1].length!==8)return null;
    let hasAny=false;
    for(const domain of trial[1]){
      if(!Array.isArray(domain)||domain.length>25)return null;
      const unique=new Set<string>();
      for(const ref of domain){
        if(!Array.isArray(ref)||ref.length!==2||
           !Number.isSafeInteger(ref[0])||ref[0]<0||ref[0]>=data.docs.length||
           !Number.isSafeInteger(ref[1])||ref[1]<1||ref[1]>1800||
           data.docs[ref[0]][0]!==trial[0])return null;
        const token=ref.join(":");
        if(unique.has(token))return null;
        unique.add(token);
        linkedDocs.add(ref[0]);
        hasAny=true;
        leads++;
      }
    }
    if(!hasAny)return null;
    byNct.set(trial[0],trial[1]);
  }
  if(leads!==466||linkedDocs.size!==22||byNct.size!==12||
     [...sourceMap.keys()].some(n=>byNct.has(n)!==data.docs.some(doc=>doc[0]===n)))return null;
  const details=research.trials.map(t=>{
    const domains=EIGHT_SOURCE_DOMAINS.map(({key,label},i)=>({
      key,label,
      level:"UNASSESSED_SOURCE_ONLY" as const,
      scientificScore:null,
      qualifiedReviewerSigned:false as const,
      originalSourceVersionBeforeUnblindingVerified:false as const,
      references:(byNct.get(t.nct)?.[i]??[]).map(([doc,page])=>{
        const [nct,filename]=data.docs[doc];
        const originalUrl="https://cdn.clinicaltrials.gov/large-docs/"+
          nct.slice(-2)+"/"+nct+"/"+filename;
        return {filename,pdfPageOneBased:page,originalUrl,
                pageUrl:originalUrl+"#page="+page};
      })
    }));
    return {
      nct:t.nct,ticker:t.ticker,applicationCycles:[...t.cycles],
      domains,sourcePdfDocumentsWithPageLeads:
        data.docs.filter(doc=>doc[0]===t.nct).length,
      totalPageLeads:domains.reduce((n,d)=>n+d.references.length,0),
      installedScientificResearchStage:4,
      independentlyCompletedAssessmentLevel:null,
      signedScientificGrades:0,
      officialFdaOutcome:"ABSTAIN" as const,
      accuracy:null
    };
  });
  return {
    schema:"MAIN_R64_VIEW_ONLY_ORIGINAL_R63_EIGHT_DOMAIN_PAGE_LEADS" as const,
    originalRun:R63_RUN,originalArtifact:R63_ARTIFACT,
    archiveUrl:"https://github.com/pdufa/pdufa-command-center/actions/runs/"+
      R63_RUN+"/artifacts/"+R63_ARTIFACT,
    uniqueNctCount:29,applicationGroups:23,
    sourceReviewDimensions:8,unscoredSourceReviewSlots:232,
    originalCurrentAttachedDocuments:23,
    documentFilesWithMachinePageLeads:22,
    trialsWithCurrentPageLeads:12,trialsWithoutCurrentPageLeads:17,
    sourcePageLeadCount:466,
    trials:details,
    clinicalMethodScores:0,qualifiedReviewerSignoffs:0,
    independentlyValidatedFdaForecasts:0,
    measuredForecastAccuracy:null,
    officialFutureFdaOutcome:"ABSTAIN" as const,
    not800CompletedScientificAssessments:true,
    noProductionWritesOrModelTraining:true,
  };
}
export const FOCUS_R64_METHOD_PAGE_VIEW=buildR64OriginalMethodPageView();

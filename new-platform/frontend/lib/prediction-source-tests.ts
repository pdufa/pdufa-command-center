/**
 * Evidence-only source tests for one exact ClinicalTrials.gov NCT.
 *
 * These checks establish which registry fields are present and which evidence
 * remains unreviewed. They are NOT 12 validated clinical tests, FDA verdicts,
 * numerical forecasts, or finished specialist adjudications.
 */
import {FOCUS_SPECIALTY_ASSESSMENT_QUEUE} from "./focus-specialty-assessment";

export type TestState="SOURCE_FIELD_PRESENT"|"SOURCE_FIELD_MISSING"|"INDEPENDENT_REVIEW_REQUIRED"|"NOT_AUTOMATED";
export type EvidenceTest={index:number;key:string;title:string;state:TestState;summary:string;sourceUrl:string;nextRequired:string};
export const TEST_NAMES=[
 "Exact registry identity",
 "Current registry phase and status",
 "Conditions, interventions and sponsor",
 "Study design and allocation",
 "Prespecified primary outcomes",
 "Official registry results posting",
 "Outcome results and statistical analyses",
 "Reported serious adverse events",
 "Participant flow and attrition reporting",
 "Disease-specific specialist research",
 "FDA review, manufacturing and sponsor corroboration",
 "Historical outcome calibration and prediction"
] as const;
export type EvidenceRun={
  nct:string;ticker:string;mode:"FULL"|"SINGLE";executedAt:string;
  registrySourceUrl:string;registryLastUpdate:string|null;
  researchState:"SOURCE_INSPECTION_ONLY";
  tests:EvidenceTest[];executedCount:number;
  prediction:{approval:"ABSTAIN";crl:"ABSTAIN";reviewDelay:"ABSTAIN";certainty:"NOT_VALIDATED"};
  message:string;
};
type R=Record<string,unknown>;
const object=(x:unknown):R=>x&&typeof x==="object"&&!Array.isArray(x)?x as R:{};
const array=(x:unknown):unknown[]=>Array.isArray(x)?x:[];
const string=(x:unknown):string=>typeof x==="string"?x.trim():"";
const nested=(x:unknown,...keys:string[]):R=>keys.reduce<R>((a,k)=>object(a[k]),object(x));
const field=(x:unknown,key:string)=>object(x)[key];
const textList=(xs:unknown,max=3):string=>array(xs).map(x=>string(x)).filter(Boolean).slice(0,max).join("; ");
const display=(value:unknown,max=130)=>string(value).slice(0,max)||"Not recorded";
const show=(value:string,max=220)=>value.slice(0,max);

export function createSourceTests(study:unknown,nct:string):EvidenceTest[]{
  const trial=FOCUS_SPECIALTY_ASSESSMENT_QUEUE.find(r=>r.nct===nct);
  if(!trial||!/^NCT\d{8}$/.test(nct))throw Error("EXACT_FOCUS_NCT_REQUIRED");
  const protocol=nested(study,"protocolSection");
  const id=nested(protocol,"identificationModule");
  if(string(id.nctId)!==nct)throw Error("REGISTRY_NCT_ID_MISMATCH");
  const status=nested(protocol,"statusModule");
  const design=nested(protocol,"designModule");
  const studyDesign=nested(design,"designInfo");
  const arms=nested(protocol,"armsInterventionsModule");
  const conditions=nested(protocol,"conditionsModule");
  const sponsor=nested(protocol,"sponsorCollaboratorsModule");
  const outcomes=nested(protocol,"outcomesModule");
  const results=nested(study,"resultsSection");
  const resultOutcomes=nested(results,"outcomeMeasuresModule");
  const events=nested(results,"adverseEventsModule");
  const flow=nested(results,"participantFlowModule");
  const source="https://clinicaltrials.gov/study/"+nct;
  const tests:EvidenceTest[]=[];
  const add=(title:string,state:TestState,summary:string,nextRequired:string,sourceUrl=source)=>{
    tests.push({index:tests.length,key:"test-"+(tests.length+1),title,state,summary,nextRequired,sourceUrl});
  };
  const phases=textList(design.phases,3);
  const overall=string(status.overallStatus);
  const studyTypes=string(design.studyType);
  const conditionsText=textList(conditions.conditions);
  const interventions=array(arms.interventions).map(x=>string(object(x).name)).filter(Boolean);
  const sponsorName=string(nested(sponsor,"leadSponsor").name);
  const armsCount=array(arms.armGroups).length;
  const primary=array(outcomes.primaryOutcomes);
  const posted=array(resultOutcomes.outcomeMeasures);
  const outcomeAnalyses=posted.reduce((n,x)=>n+array(object(x).analyses).length,0);
  const serious=array(events.seriousEvents);
  const reportsEvents=!!Object.keys(events).length;
  const periods=array(flow.periods);
  const hasResults=field(study,"hasResults")===true||Object.keys(results).length>0;
  const application=trial.applications;
  const lenses=[...new Set(application.map(x=>x.specialty).filter(Boolean))];

  add("Exact registry identity","SOURCE_FIELD_PRESENT",
    "ClinicalTrials.gov returned the requested exact record "+nct+"; title: "+display(id.briefTitle)+".",
    "Independently confirm sponsor, therapy and application-cycle identity against FDA/issuer documents.");
  add("Current registry phase and status",phases&&overall?"SOURCE_FIELD_PRESENT":"SOURCE_FIELD_MISSING",
    "Reported phase: "+(phases||"missing")+"; status: "+(overall||"missing")+
    "; last record update posted: "+display(nested(status,"lastUpdatePostDateStruct").date)+".",
    "Reconcile any phase changes, study completion, and whether final pivotal Phase 3 data exist.");
  add("Conditions, interventions and sponsor",conditionsText&&interventions.length&&sponsorName?"SOURCE_FIELD_PRESENT":"SOURCE_FIELD_MISSING",
    "Condition(s): "+(conditionsText||"missing")+"; intervention(s): "+(interventions.slice(0,3).join("; ")||"missing")+
      "; lead sponsor: "+(sponsorName||"missing")+".",
    "Verify sponsor rights, selected formulation, dose, population, and current indication.");
  add("Study design and allocation",studyTypes&&Object.keys(studyDesign).length?"SOURCE_FIELD_PRESENT":"SOURCE_FIELD_MISSING",
    "Study type: "+(studyTypes||"missing")+"; allocation: "+display(studyDesign.allocation)+
    "; model: "+display(studyDesign.interventionModel)+"; registered arms: "+armsCount+".",
    "Read original protocol, statistical analysis plan, amendments and handling of missing data.");
  add("Prespecified primary outcomes",primary.length?"SOURCE_FIELD_PRESENT":"SOURCE_FIELD_MISSING",
    primary.length+" registered primary outcome(s). "+(primary.length?"Example: "+show(display(object(primary[0]).measure))+".":"No primary outcomes recorded in this response."),
    "Verify prespecification date, endpoint validity, multiplicity and applicable statistical estimands.");
  add("Official registry results posting",hasResults?"SOURCE_FIELD_PRESENT":"SOURCE_FIELD_MISSING",
    hasResults?"Record reports results; "+posted.length+" outcome result measure(s) were found.":
      "No posted registry-results section was returned; a sponsor press release is not equivalent to posted tabular registry results.",
    "If absent, source full results from dated sponsor filings, medical publications and FDA review packages.");
  add("Outcome results and statistical analyses",posted.length&&outcomeAnalyses?"SOURCE_FIELD_PRESENT":
    posted.length?"INDEPENDENT_REVIEW_REQUIRED":"SOURCE_FIELD_MISSING",
    posted.length+" posted result outcome(s); "+outcomeAnalyses+" recorded analysis block(s). Presence does not establish statistical significance or efficacy.",
    "Independently inspect effect sizes, confidence intervals, p-values, censoring and prespecified analysis population.");
  add("Reported serious adverse events",reportsEvents?"SOURCE_FIELD_PRESENT":"SOURCE_FIELD_MISSING",
    reportsEvents?"Registry has an adverse-events results module; "+serious.length+
      " distinct serious-event entries.":"Registry response contains no posted adverse-events module.",
    "Assess severity, exposure, comparator imbalance, withdrawals and unreported longer-term risks.");
  add("Participant flow and attrition reporting",periods.length?"SOURCE_FIELD_PRESENT":"SOURCE_FIELD_MISSING",
    periods.length+" registered participant-flow period(s); enrollment: "+display(nested(design,"enrollmentInfo").count?String(nested(design,"enrollmentInfo").count):"not reported")+".",
    "Quantify randomized, treated, completed, missing and withdrawn populations; independently evaluate missingness bias.");
  add("Disease-specific specialist research",lenses.length&&application.some(x=>x.partialCaseDimensions>0)?"INDEPENDENT_REVIEW_REQUIRED":"SOURCE_FIELD_MISSING",
    application.length+" mapped FDA application cycle(s); "+lenses.length+" mapped specialty lens(es): "+
      (lenses.join("; ")||"none")+"; "+
      application.reduce((n,x)=>n+x.partialCaseDimensions,0)+" partial research dimension(s).",
    "Source-linked specialist interpretations are preliminary; independently re-check original clinical evidence, counterarguments and diagnosis-specific clinical relevance.",
    "https://pdufa-new-dashboard.vercel.app/predictions/assessment?nct="+nct);
  add("FDA review, manufacturing and sponsor corroboration","NOT_AUTOMATED",
    "This source scan does not independently retrieve or adjudicate FDA current-cycle communications, CMC inspections, SEC filings or original sponsor results.",
    "Verify separately against current FDA Drugs@FDA, SEC, sponsor disclosures, FDA reviews and manufacturing records.",
    application[0]?.sourceUrl??source);
  add("Historical outcome calibration and prediction","NOT_AUTOMATED",
    "No independently validated outcome model or historical prospective calibration is available. Approval, CRL and review delay remain ABSTAIN.",
    "Develop a time-locked FDA application dataset, out-of-time validation, independently reviewed outcome models, and calibrated certainty.",
    source);
  if(tests.length!==TEST_NAMES.length)throw Error("SOURCE_TEST_COUNT_MISMATCH");
  return tests;
}

export function makeEvidenceRun(study:unknown,nct:string,mode:"FULL"|"SINGLE",testIndex?:number):EvidenceRun{
  const trial=FOCUS_SPECIALTY_ASSESSMENT_QUEUE.find(r=>r.nct===nct);
  if(!trial)throw Error("EXACT_FOCUS_NCT_REQUIRED");
  if(mode==="SINGLE"&&(!Number.isInteger(testIndex)||(testIndex as number)<0||(testIndex as number)>=TEST_NAMES.length))
    throw Error("INVALID_SOURCE_TEST_INDEX");
  const tests=createSourceTests(study,nct);
  const status=nested(study,"protocolSection","statusModule");
  const selected=mode==="SINGLE"?[tests[testIndex!]]:tests;
  return {
    nct,ticker:trial.ticker,mode,executedAt:new Date().toISOString(),
    registrySourceUrl:"https://clinicaltrials.gov/study/"+nct,
    registryLastUpdate:string(nested(status,"studyFirstPostDateStruct").date)||string(nested(status,"lastUpdatePostDateStruct").date)||null,
    researchState:"SOURCE_INSPECTION_ONLY",tests:selected,executedCount:selected.length,
    prediction:{approval:"ABSTAIN",crl:"ABSTAIN",reviewDelay:"ABSTAIN",certainty:"NOT_VALIDATED"},
    message:"Each executed test checks recorded source fields, not independent scientific accuracy. No regulatory outcome prediction is certified or released."
  };
}

/**
 * MAIN revision 25: an exact-trial, phase-first research review queue.
 *
 * Source leads are NOT clinical tests. This is a reproducible worklist, not
 * an estimated treatment effect, rank of FDA risk, or reviewer-authorized
 * result. Every source and source-to-method mapping is pinned to the dated
 * original ACACIA research snapshot. No ledger writer is imported.
 */
import {evaluatePilotScientificSignals} from "./acacia-quantitative-science";
import {evaluateClinicalRubricReadiness} from "./phase3-clinical-quality-rubric";
import {evaluateAdditionalPilotReadiness,evaluatePilotReadiness} from "./pilot-research-readiness";

export type QueueStatus="DOCUMENT_CHECKLIST"|"PUBLISHED_NUMERIC_RECALCULATION"|"SOURCE_LEAD_ONLY";
export type QueuePosition={
  id:string;
  reviewOrder:number;
  assessmentId:string;
  assessmentLabel:string;
  methodIndex:number;
  evidenceStatus:QueueStatus;
  sourceIds:string[];
  sourceUrls:string[];
  missingOriginalEvidence:string;
  sourceGapAuditNote:string|null;
  sourceGapAuditRun:number|null;
  reviewPriority:"CRITICAL_PHASE3_RESEARCH";
  clinicalGrade:null;
  qualifiedReviewerSignoff:false;
  fdaProbability:null;
  sourceSnapshotAsOf:string;
};
export type Phase3ReviewQueue={
  schema:"MAIN_ACACIA_PHASE3_REVIEW_QUEUE_V1";
  nct:"NCT06081894";
  phaseBasis:"REGISTRY_REPORTED_PHASE3_NOT_INDEPENDENTLY_VERIFIED";
  sourceSnapshotAsOf:string;
  positions:QueuePosition[];
  summary:{mappedSourceLeads:18;documentChecklist:3;quantitativeMethods:2;
    sourceLeadOnly:13;positionsNotSourceMapped:782;
    officialClinicalGrades:0;qualifiedPhaseSignoffs:0};
  status:"RESEARCH_WORKLIST_NOT_CLINICAL_GRADE";
  fdaPrediction:"ABSTAIN";
  calibratedAccuracy:null;
};
type Snapshot={
  nct:string;phaseReported:string;phaseIndependentReviewerVerified:boolean;
  asOf:string;
  scientificFramework:{positions:number;mappedCandidateMethodLeads:number;
    methodPositionsUnexamined:number;independentlyGradedMethodPositions:number;
    currentPhaseReviewSignoffs:number;independentlyCompletedAssessments:number};
  criticalAssessmentEvidence:Array<{id:string;label:string;
    sourceLeadIds:string[];candidateMethodIndices:number[];remaining:string}>;
  sources:Record<string,{url:string;label:string;sha256?:string;retrieved?:boolean}>;
  finalDecision:{approval:string;crl:string;reviewDelay:string;certainty:string;
    calibratedAccuracy:null;calibratedProbabilities:null};
};
const EXPECTED_METHODS:Readonly<Record<string,readonly number[]>>={
  "4.1":[1],"4.2":[1,2],"4.3":[1,4],"4.4":[1],"4.5":[1],
  "5.1":[1,12],"5.2":[1],"5.3":[1,19],"5.4":[1,4],
  "8.1":[1],"8.2":[1,4,5]
};
const SOURCE_URLS:Readonly<Record<string,string>>={
  CTIS_AM04:"https://github.com/pdufa/pdufa-command-center/actions/runs/42525291355/artifacts/13634488398",
  NEJM_PIVOTAL:"https://pubmed.ncbi.nlm.nih.gov/42663312/",
  SEC_10Q:"https://www.sec.gov/Archives/edgar/data/1061983/000119312526447408/cytk-20260930.htm",
  ISSUER_MAY_2025:"https://ir.cytokinetics.com/press-releases/press-release-details/2025/Cytokinetics-Reports-First-Quarter-2025-Financial-Results-and-Provides-Business-Update-05-06-2025/default.aspx",
  REGISTRY:"https://clinicaltrials.gov/study/NCT06081894",
  ECHO_ANALYSIS:"https://pmc.ncbi.nlm.nih.gov/articles/PMC13674599/",
  RESPONDER_ANALYSIS:"https://pmc.ncbi.nlm.nih.gov/articles/PMC13674601/",
  HCMS_KCCQ_OSS_20261106:"https://cytokinetics.com/wp-content/uploads/2026/11/AHA-HCMS26-ACACIA-KCCQ_PRO-oral_final.pdf",
  HCMS_CMR_20261106:"https://cytokinetics.com/wp-content/uploads/2026/11/Masri_2026_HCMS_ACACIA-HCM-CMR.pdf",
  FDA_ORIGINAL_OHCM_2025:"https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/219083s000lbl.pdf",
  INVIMA_ACACIA_2025:"https://www.invima.gov.co/estudio/20241173982-un-estudio-multic%C3%A9ntrico-aleatorizado-doble-ciego-de-fase-3-para-evaluar-la-eficacia-y-s"
};
const ORIGINAL_PROTOCOL_SHA="853ffd80a547df8a7b813b8985c7116dd6168a640f18521f61b95cf33a8ca5f8";
const ORDER=["5.3","5.1","4.2","5.2","4.3","4.4","4.5","5.4","8.2","8.1","4.1"] as const;
const DOCUMENTED=new Set(["5.1:L1","4.2:L1","5.3:L1"]);
const NUMERIC=new Set(["5.1:L12","5.3:L19"]);
// Archived exact-run research findings. A live registry record may later differ.
// These are evidence-search observations, never clinical grades or file absence proof.
const AUDIT_RUN=42555289486;
const SAP_GAP="2026-11-09 archived source audit: current official registry response did not list an SAP; final locked SAP remains unverified, and journal supplement fetches were unavailable to the automated checker.";
const SAFETY_GAP="2026-11-09 archived sponsor source: 2 HF SAE cases associated with LVEF below 50% plus 10 other treated HF SAE cases = 12 versus 3 placebo; secondary 11/1 source definition remains unreconciled.";
const evidenceAuditNote=(assessment:string):string|null=>
  assessment==="5.3"?SAFETY_GAP:
  ["4.2","4.3","5.1","5.2","8.2"].includes(assessment)?SAP_GAP:null;
const sourceOK=(sources:Snapshot["sources"])=>{
  if(!sources||typeof sources!=="object"||
     !Object.entries(SOURCE_URLS).every(([id,url])=>
       sources[id]?.url===url&&typeof sources[id]?.label==="string"&&sources[id].label.length>10))
    return false;
  return sources.CTIS_AM04.sha256===ORIGINAL_PROTOCOL_SHA&&sources.CTIS_AM04.retrieved===true;
};
/** Strictly withhold on extra/missing source leads, invalid sources or any signed
 * clinical work. A source-verified scientific outcome is NOT inferred.
 */
export function buildPhase3ReviewQueue(p:Snapshot):Phase3ReviewQueue|null {
  if(!p||p.nct!=="NCT06081894"||p.phaseReported!=="PHASE3"||
    p.phaseIndependentReviewerVerified!==false||
    !/^20\d{2}-\d{2}-\d{2}$/.test(p.asOf)||
    p.scientificFramework?.positions!==800||
    p.scientificFramework?.mappedCandidateMethodLeads!==18||
    p.scientificFramework?.methodPositionsUnexamined!==782||
    p.scientificFramework?.independentlyGradedMethodPositions!==0||
    p.scientificFramework?.currentPhaseReviewSignoffs!==0||
    p.scientificFramework?.independentlyCompletedAssessments!==0||
    p.finalDecision?.approval!=="ABSTAIN"||p.finalDecision.crl!=="ABSTAIN"||
    p.finalDecision.reviewDelay!=="ABSTAIN"||
    p.finalDecision.certainty!=="NOT_VALIDATED"||
    p.finalDecision.calibratedAccuracy!==null||
    p.finalDecision.calibratedProbabilities!==null||
    !sourceOK(p.sources))return null;
  const statistical=evaluatePilotScientificSignals(p as unknown as Parameters<typeof evaluatePilotScientificSignals>[0]);
  const rubric=evaluateClinicalRubricReadiness(statistical,p as unknown as Parameters<typeof evaluateClinicalRubricReadiness>[1]);
  const first=evaluatePilotReadiness(p as unknown as Parameters<typeof evaluatePilotReadiness>[0]);
  const others=evaluateAdditionalPilotReadiness(p as unknown as Parameters<typeof evaluateAdditionalPilotReadiness>[0]);
  if(!statistical||!rubric||!first||!others||
    first.points!==3||others[0]?.points!==3||others[1]?.points!==2)return null;
  const assessments=p.criticalAssessmentEvidence;
  if(!Array.isArray(assessments)||assessments.length!==ORDER.length||
    new Set(assessments.map(x=>x.id)).size!==ORDER.length)return null;
  const items:QueuePosition[]=[];
  for(const group of assessments){
    const expected=EXPECTED_METHODS[group.id];
    if(!expected||!Array.isArray(group.candidateMethodIndices)||
      group.candidateMethodIndices.length!==expected.length||
      group.candidateMethodIndices.some((n,i)=>n!==expected[i])||
      typeof group.label!=="string"||group.label.trim().length<8||
      typeof group.remaining!=="string"||group.remaining.trim().length<20||
      !Array.isArray(group.sourceLeadIds)||!group.sourceLeadIds.length||
      new Set(group.sourceLeadIds).size!==group.sourceLeadIds.length||
      group.sourceLeadIds.some(id=>!SOURCE_URLS[id]||p.sources[id]?.url!==SOURCE_URLS[id]))return null;
    for(const methodIndex of expected){
      const id=group.id+":L"+methodIndex;
      const evidenceStatus=DOCUMENTED.has(id)?"DOCUMENT_CHECKLIST":
        NUMERIC.has(id)?"PUBLISHED_NUMERIC_RECALCULATION":"SOURCE_LEAD_ONLY";
      items.push({
        id,reviewOrder:0,assessmentId:group.id,assessmentLabel:group.label,
        methodIndex,evidenceStatus,
        sourceIds:[...group.sourceLeadIds],
        sourceUrls:group.sourceLeadIds.map(k=>SOURCE_URLS[k]),
        missingOriginalEvidence:group.remaining,
        sourceGapAuditNote:evidenceAuditNote(group.id),
        sourceGapAuditRun:evidenceAuditNote(group.id)?AUDIT_RUN:null,
        reviewPriority:"CRITICAL_PHASE3_RESEARCH",
        clinicalGrade:null,qualifiedReviewerSignoff:false,
        fdaProbability:null,sourceSnapshotAsOf:p.asOf
      });
    }
  }
  if(items.length!==18||new Set(items.map(x=>x.id)).size!==18||
    items.filter(x=>x.evidenceStatus==="DOCUMENT_CHECKLIST").length!==3||
    items.filter(x=>x.evidenceStatus==="PUBLISHED_NUMERIC_RECALCULATION").length!==2||
    items.filter(x=>x.evidenceStatus==="SOURCE_LEAD_ONLY").length!==13)return null;
  items.sort((a,b)=>ORDER.indexOf(a.assessmentId as typeof ORDER[number])-
    ORDER.indexOf(b.assessmentId as typeof ORDER[number])||a.methodIndex-b.methodIndex);
  items.forEach((x,i)=>{x.reviewOrder=i+1;});
  return {
    schema:"MAIN_ACACIA_PHASE3_REVIEW_QUEUE_V1",nct:"NCT06081894",
    phaseBasis:"REGISTRY_REPORTED_PHASE3_NOT_INDEPENDENTLY_VERIFIED",
    sourceSnapshotAsOf:p.asOf,positions:items,
    summary:{
      mappedSourceLeads:18,documentChecklist:3,quantitativeMethods:2,
      sourceLeadOnly:13,positionsNotSourceMapped:782,
      officialClinicalGrades:0,qualifiedPhaseSignoffs:0
    },
    status:"RESEARCH_WORKLIST_NOT_CLINICAL_GRADE",
    fdaPrediction:"ABSTAIN",calibratedAccuracy:null
  };
}
export function reviewQueueCsv(q:Phase3ReviewQueue):string{
  // Spreadsheet formula injection defense even if source text changes later.
  const cell=(value:string|number|null)=>{
    let s=value===null?"":String(value);
    if(/^\s*[=+@-]/.test(s))s="'"+s;
    return '"'+s.replace(/"/g,'""').replace(/[\r\n]+/g," ")+'"';
  };
  const columns=["Research order","Trial","Method position","Assessment",
    "Research status","Original evidence needed","Source references",
    "Public source gap (dated audit)","Official clinical grade","Qualified reviewer","FDA prediction","Evidence snapshot"];
  const rows=q.positions.map(p=>[
    p.reviewOrder,q.nct,p.id,p.assessmentLabel,p.evidenceStatus,
    p.missingOriginalEvidence,p.sourceUrls.join(" ; "),p.sourceGapAuditNote,"UNSCORED",
    "NOT SIGNED",q.fdaPrediction,p.sourceSnapshotAsOf
  ]);
  return [columns,...rows].map(row=>row.map(cell).join(",")).join("\r\n")+"\r\n";
}

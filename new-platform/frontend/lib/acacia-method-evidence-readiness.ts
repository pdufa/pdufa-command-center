/** Rev37 source-authenticated documentary handoff, not clinical review or FDA probability.
 * Exact NCT only. Computes the canonical 40x20 method positions and overlays
 * the preexisting 18 research leads + three verified registry packet mappings.
 */
import {buildPhase3ReviewQueue} from "./acacia-phase3-review-queue";

export type MethodSourceState =
  "ORIGINAL_REGISTRY_RECEIPT_AVAILABLE"|"RESEARCH_LEAD_ONLY"|"NO_MAPPED_SOURCE";
export type MethodReadiness = {
  id:string;assessmentId:string;methodIndex:number;sourceState:MethodSourceState;
  researchEvidenceStatus:string|null;
  missingOriginalEvidence:string;
  originalDocumentLinks:readonly string[];
  sourceLeads:readonly string[];
  reviewerStatus:"PHASE_AND_METHOD_SIGNOFF_PENDING";
  officialGrade:null;fdaProbability:null;
};
const EXPECTED_VERSIONS=[26,27,29,30];
const VERSION_ARTIFACTS=[
  "v26_original_registry.json","v27_original_registry.json",
  "v29_original_registry.json","v30_original_registry.json"
];
const ORIGINAL_METHODS=["4.2:L1","4.4:L1","8.2:L1"];
const DIGEST=/^[a-f0-9]{64}$/;
const SOURCE_ROOT="docs/medical-review-pilot-20261108/revision36-original-history";
const BLOB_ROOT="https://github.com/pdufa/pdufa-command-center/blob/feature/medical-stage4-verified-method-matrix-20261108/";
const BLOCKED_GAP="No exact-method source mapping yet. Identify phase-appropriate originals and obtain qualified independent review; missing evidence is not a failed scientific test.";
export function buildAcaciaMethodReadiness(pilot:unknown,history:unknown){
  if(!pilot||typeof pilot!=="object"||Array.isArray(pilot)||!history||typeof history!=="object"||Array.isArray(history))return null;
  const p=pilot as Record<string,any>,h=history as Record<string,any>;
  if(p.nct!=="NCT06081894"||p.protocolCode!=="CY 6033"||
    p.scientificFramework?.assessments!==40||
    p.scientificFramework?.methodsPerAssessment!==20||
    p.scientificFramework?.positions!==800||
    p.phaseIndependentReviewerVerified!==false||
    p.scientificFramework?.independentlyGradedMethodPositions!==0||
    p.scientificFramework?.currentPhaseReviewSignoffs!==0||
    p.finalDecision?.approval!=="ABSTAIN"||p.finalDecision?.crl!=="ABSTAIN"||
    p.finalDecision?.reviewDelay!=="ABSTAIN"||p.finalDecision?.calibratedAccuracy!==null||
    h.nct!=="NCT06081894"||h.protocol!=="CY 6033"||h.revision!==36||
    h.sourceVersionCompleteness!==true||h.accessMethod!=="STANDARD_PUBLIC_HISTORY_UI"||
    h.sourceDirectory!==SOURCE_ROOT||h.originalHistoryIndex?.sha256===undefined||
    !DIGEST.test(h.originalHistoryIndex.sha256)||
    h.officialClinicalGrades!==0||h.qualifiedPhaseSignoffs!==0||
    h.newlyCompletedScientificMethods!==0||h.newlyMappedPositions!==0||
    !Array.isArray(h.mappedExistingPositions)||!Array.isArray(h.versions)||
    h.versions.length!==4||h.mappedExistingPositions.length!==3||
    ORIGINAL_METHODS.some((id,i)=>h.mappedExistingPositions[i]!==id))return null;
  const originals: string[]=[];
  for(let i=0;i<4;i++){
    const v=h.versions[i];
    if(!v||v.version!==EXPECTED_VERSIONS[i]||v.apiIndex!==EXPECTED_VERSIONS[i]-1||
       v.artifact!==VERSION_ARTIFACTS[i]||v.phaseIndependentReviewerVerified!==false||
       v.enrollment?.type!=="ESTIMATED"||!DIGEST.test(String(v.sourceSha256))||
       !Number.isInteger(v.sourceBytes)||v.sourceBytes<1000||
       !/^20\d{2}-\d{2}-\d{2}$/.test(String(v.submitted))||
       !/^20\d{2}-\d{2}-\d{2}$/.test(String(v.posted))||v.posted<v.submitted||
       !Array.isArray(v.primary)||v.primary.length!==(i===0?1:2)||
       v.primary.some((x:Record<string,any>)=>typeof x?.measure!=="string"||
          !/Week 36/i.test(String(x.timeFrame))||
          typeof x.description!=="string"||x.description.length<10))return null;
    const endpointText=v.primary.map((x:Record<string,any>)=>x.measure.toLowerCase()).join(" ");
    if(!endpointText.includes("kccq")||
       (i!==0&&!endpointText.includes("pvo2")))return null;
    originals.push(BLOB_ROOT+SOURCE_ROOT+"/"+v.artifact);
  }
  const q=buildPhase3ReviewQueue(p as Parameters<typeof buildPhase3ReviewQueue>[0]);
  if(!q||q.positions.length!==18||q.summary.positionsNotSourceMapped!==782)return null;
  const mapped=new Map(q.positions.map(x=>[x.id,x]));
  const originalSet=new Set(ORIGINAL_METHODS);
  if(ORIGINAL_METHODS.some(id=>!mapped.has(id)))return null;
  const positions:MethodReadiness[]=[];
  for(let layer=1;layer<=8;layer++){
    for(let heading=1;heading<=5;heading++){
      const assessmentId=layer+"."+heading;
      for(let methodIndex=1;methodIndex<=20;methodIndex++){
        const id=assessmentId+":L"+methodIndex;
        const lead=mapped.get(id), original=originalSet.has(id);
        positions.push({
          id,assessmentId,methodIndex,
          sourceState:original?"ORIGINAL_REGISTRY_RECEIPT_AVAILABLE":
            lead?"RESEARCH_LEAD_ONLY":"NO_MAPPED_SOURCE",
          researchEvidenceStatus:lead?.evidenceStatus??null,
          missingOriginalEvidence:lead?.missingOriginalEvidence??BLOCKED_GAP,
          originalDocumentLinks:original?originals:[],
          sourceLeads:lead?.sourceUrls??[],
          reviewerStatus:"PHASE_AND_METHOD_SIGNOFF_PENDING",
          officialGrade:null,fdaProbability:null
        });
      }
    }
  }
  const sourceReceiptPositions=positions.filter(x=>x.sourceState==="ORIGINAL_REGISTRY_RECEIPT_AVAILABLE").length;
  const otherLeads=positions.filter(x=>x.sourceState==="RESEARCH_LEAD_ONLY").length;
  const unmapped=positions.filter(x=>x.sourceState==="NO_MAPPED_SOURCE").length;
  if(positions.length!==800||sourceReceiptPositions!==3||otherLeads!==15||unmapped!==782||
     positions.some(x=>x.officialGrade!==null))return null;
  return {
    schema:"MAIN_ACACIA_METHOD_EVIDENCE_READINESS_R37",
    nct:"NCT06081894" as const,phase:"PHASE3_REPORTED_NOT_INDEPENDENTLY_SIGNED",
    methodPositions:positions,
    prioritizedResearchHandoffs:q.positions.map(x=>positions.find(p=>p.id===x.id)!),
    counts:{total:800,originalRegistryDocumentaryReferences:3,
      mappedLeadsWithoutNewOriginalRegistryPacket:15,unmapped:782,
      documentaryOrNumericResearchFindings:5,clinicallyGraded:0,
      independentPhaseSignoffs:0,independentClinicalReviews:0,
      verifiedHistoricalFdaCohortCases:0},
    note:"Three original registry document mappings are documentary leads, not independently reviewed clinical methods; 15 other mapped positions and 782 unmapped positions remain blocked from official grades.",
    scientificStatus:"REVIEW_HANDOFF_ONLY_NO_AUTHORIZED_SCORES" as const,
    fdaPrediction:"ABSTAIN" as const,accuracy:"NOT_CALIBRATED" as const,
    reviewWritesAuthorized:false as const,
    originalVersionPublicPostingDates:h.versions.map((v:Record<string,any>)=>String(v.posted)),
  };
}

/** Download-ready 800-row reviewer *research* worksheet, not a clinical grade ledger.
 * All statuses are explicitly sourced from an exact-NCT, fail-closed snapshot.
 */
export function exportAcaciaMethodReadinessCsv(
  report:ReturnType<typeof buildAcaciaMethodReadiness>
):string{
  if(!report||report.methodPositions.length!==800||report.nct!=="NCT06081894"||
     report.counts.clinicallyGraded!==0||report.fdaPrediction!=="ABSTAIN"||
     report.reviewWritesAuthorized!==false)throw Error("UNVERIFIED_REVIEW_HANDOFF");
  const csvCell=(value:string|number|null):string=>{
    let s=value===null?"":String(value).replace(/[\r\n\t]+/g," ");
    if(/^\s*[=+\-@]/.test(s))s="'"+s;
    return '"'+s.replace(/"/g,'""')+'"';
  };
  const columns=[
    "Exact NCT","Method position","Assessment ID","Method index",
    "Source state","Research-only category","Missing original evidence",
    "Original preserved registry references","Other research source leads",
    "Public posting dates of recovered versions","Independent reviewer gate",
    "Authorized clinical grade","FDA forecast","Forecast accuracy"
  ];
  const rows=report.methodPositions.map(p=>[
    report.nct,p.id,p.assessmentId,p.methodIndex,p.sourceState,
    p.researchEvidenceStatus??"NOT_MAPPED",
    p.missingOriginalEvidence,p.originalDocumentLinks.join(" ; "),
    p.sourceLeads.join(" ; "),report.originalVersionPublicPostingDates.join(" ; "),
    p.reviewerStatus,"UNASSIGNED",report.fdaPrediction,report.accuracy
  ]);
  return [columns,...rows].map(row=>row.map(csvCell).join(",")).join("\r\n")+"\r\n";
}

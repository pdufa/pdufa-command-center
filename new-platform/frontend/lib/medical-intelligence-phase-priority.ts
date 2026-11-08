/**
 * Deterministic, phase-aware INVESTIGATION PRIORITY for all 40×20 scientific positions.
 *
 * This is not a medical finding, evidence strength score, physician opinion,
 * FDA probability or historical result. Priority ranks describe where to
 * INVESTIGATE FIRST in the verified phase. There are always 800 positions.
 *
 * A confirmed adverse event / deviation may elevate a particular position only
 * if a human-verified exact-NCT, phase-matched source finding is supplied.
 * Unobserved risk-watch prompts and missing evidence NEVER become risk findings.
 * Retired RAAS and 1–20 survey systems are not dependencies.
 */
import type {TrialPhase,AssessmentDescriptor} from "./medical-intelligence-assessment-rankings";

export type PriorityTier="CRITICAL"|"HIGH"|"MODERATE"|"LOW"|"VERIFY_PHASE";
export type InvestigationMethod={id:number;name:string};
export type VerifiedTestRisk={
  nct:string;phase:Exclude<TrialPhase,"UNKNOWN">;assessmentId:string;methodLevel:number;
  riskId:string;severity:"HIGH"|"CRITICAL";
  finding:string;sourceUrls:readonly string[];verifiedOn:string;
  verified:true;
};
export type PrioritizedScientificTest={
  id:string;nct:string;phase:TrialPhase;assessmentId:string;assessmentLabel:string;
  layerId:string;level:number;methodName:string;
  rank:number|null;
  priority:PriorityTier;
  phaseApplicability:"CURRENT_PHASE"|"FORWARD_LOOKING"|"VERIFY_PHASE";
  basis:"PHASE_RELEVANCE"|"VERIFIED_RISK"|"PHASE_UNVERIFIED";
  grade:null;
  reason:string;
  matchedRiskIds:readonly string[];
};
export type PrioritySummary={
  nct:string;phase:TrialPhase;total:number;ranked:number;
  counts:Record<PriorityTier,number>;
  tests:PrioritizedScientificTest[];
};
export const PRIORITY_ORDER:readonly PriorityTier[]=["CRITICAL","HIGH","MODERATE","LOW","VERIFY_PHASE"];
const POINTS:Readonly<Record<Exclude<PriorityTier,"VERIFY_PHASE">,number>>={
  CRITICAL:4,HIGH:3,MODERATE:2,LOW:1
};
const VALID_PHASES:readonly TrialPhase[]=["EARLY_PHASE1","PHASE1","PHASE2","PHASE3","PHASE4","UNKNOWN"];
const SCIENCE_METHOD_WEIGHT:Readonly<Record<number,number>>={
  1:3,2:2,3:2,4:3,5:3,6:2,7:1,8:2,9:2,10:1,
  11:3,12:3,13:2,14:2,15:2,16:2,17:1,18:1,19:3,20:3
};
const ALL_ASSESSMENTS=["1.1","1.2","1.3","1.4","1.5","2.1","2.2","2.3","2.4","2.5",
  "3.1","3.2","3.3","3.4","3.5","4.1","4.2","4.3","4.4","4.5",
  "5.1","5.2","5.3","5.4","5.5","6.1","6.2","6.3","6.4","6.5",
  "7.1","7.2","7.3","7.4","7.5","8.1","8.2","8.3","8.4","8.5"] as const;

/**
 * Explicit evidence-investigation policy for each phase. CRITICAL means
 * "investigate earlier", not "a verified critical medical risk was found".
 * HIGH means phase-relevant and important. The rest are MODERATE except
 * designated forward-looking domains, which are LOW.
 */
const PHASE_CRITICAL:Record<Exclude<TrialPhase,"UNKNOWN">,readonly string[]>={
  EARLY_PHASE1:["1.1","1.5","2.1","2.2","2.3","3.3","3.4","4.5","5.3","8.1"],
  PHASE1:["1.5","2.1","2.2","2.3","3.3","3.4","3.5","4.5","5.3","8.1"],
  PHASE2:["3.3","4.1","4.2","4.3","4.4","4.5","5.1","5.3","5.4","8.1"],
  PHASE3:["4.1","4.2","4.3","4.4","4.5","5.1","5.2","5.3","5.4","8.1","8.2"],
  PHASE4:["4.5","5.3","5.5","6.1","6.4","7.4","7.3","8.1","8.2","8.4"]
};
const PHASE_HIGH:Record<Exclude<TrialPhase,"UNKNOWN">,readonly string[]>={
  EARLY_PHASE1:["1.2","1.3","1.4","2.4","2.5","3.1","3.2","3.5","4.1","4.2","4.3","4.4","5.4","6.1","8.2","8.5"],
  PHASE1:["1.1","1.2","1.3","1.4","2.4","2.5","3.1","3.2","4.1","4.2","4.3","4.4","5.1","5.4","6.1","8.2","8.5"],
  PHASE2:["1.3","1.4","1.5","2.1","2.2","2.3","2.5","3.4","3.5","5.2","5.5","6.1","6.3","6.4","8.2","8.5"],
  PHASE3:["1.3","1.4","1.5","2.2","2.3","3.3","3.4","3.5","5.5","6.1","6.3","6.4","7.1","7.2","7.3","7.4","7.5","8.3","8.4","8.5"],
  PHASE4:["1.3","1.5","2.3","2.5","3.3","3.5","4.2","4.3","5.1","5.2","5.4","6.2","6.3","6.5","7.1","7.2","7.5","8.3","8.5"]
};
const PHASE_FORWARD:Record<Exclude<TrialPhase,"UNKNOWN">,readonly string[]>={
  EARLY_PHASE1:["5.1","5.2","5.5","7.1","7.2","7.3","7.4","7.5","8.3","8.4"],
  PHASE1:["5.2","5.5","7.1","7.2","7.3","7.4","7.5","8.3","8.4"],
  PHASE2:["7.1","7.2","7.4","7.5","8.3"],
  PHASE3:[],
  PHASE4:[]
};
export const PRIORITY_PHASE_GUIDANCE:Record<TrialPhase,string>={
  EARLY_PHASE1:"First-human biological fit, exposure and safety; later pivotal/FDA tests remain future-looking.",
  PHASE1:"Dose, PK/PD, target engagement and safety are most urgent; Phase 3 efficacy is not yet due.",
  PHASE2:"Preliminary efficacy, valid endpoints, dose, safety and pivotal-study readiness.",
  PHASE3:"Pivotal design, prespecified efficacy, statistical integrity, safety and reproducibility.",
  PHASE4:"Postmarketing safety, real-world effectiveness, durability and confirmatory obligations.",
  UNKNOWN:"Verify the exact-NCT current phase before assigning a clinical investigation priority."
};
function validDay(value:string):boolean{
  if(!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;
  const d=new Date(value+"T00:00:00Z");
  return !Number.isNaN(d.getTime())&&d.toISOString().slice(0,10)===value;
}
function baseline(nct:string,phase:TrialPhase,id:string){
  if(phase==="UNKNOWN")return {tier:"VERIFY_PHASE" as PriorityTier,app:"VERIFY_PHASE" as const};
  const current=phase as Exclude<TrialPhase,"UNKNOWN">;
  const critical=PHASE_CRITICAL[current].includes(id);
  const high=PHASE_HIGH[current].includes(id);
  const forward=PHASE_FORWARD[current].includes(id);
  if((critical&&high)||(critical&&forward)||(high&&forward))
    throw Error("An assessment cannot have conflicting priority rules");
  const tier:PriorityTier=critical?"CRITICAL":high?"HIGH":forward?"LOW":"MODERATE";
  return {tier,app:forward?"FORWARD_LOOKING" as const:"CURRENT_PHASE" as const};
}
function validatePolicy(){
  const expected=new Set(ALL_ASSESSMENTS);
  for(const phase of VALID_PHASES.filter(x=>x!=="UNKNOWN") as Exclude<TrialPhase,"UNKNOWN">[]){
    for(const id of [...PHASE_CRITICAL[phase],...PHASE_HIGH[phase],...PHASE_FORWARD[phase]])
      if(!expected.has(id as typeof ALL_ASSESSMENTS[number]))throw Error("Unknown phase priority ID: "+id);
    for(const id of ALL_ASSESSMENTS)baseline("",phase,id);
  }
}
validatePolicy();

/** All 800 test slots, each given an auditable priority and stable 1–800 ordering. */
export function rankScientificInvestigations(
  assessments:readonly AssessmentDescriptor[],
  methods:readonly InvestigationMethod[],
  nct:string,phase:TrialPhase,
  confirmedRisks:readonly VerifiedTestRisk[]=[]
):PrioritySummary{
  if(!/^NCT\d{8}$/.test(nct)||!VALID_PHASES.includes(phase))
    throw Error("An exact NCT and supported phase are required");
  const assessmentIds=assessments.map(x=>x.id);
  if(assessments.length!==40||new Set(assessmentIds).size!==40||
     assessmentIds.some(id=>!ALL_ASSESSMENTS.includes(id as typeof ALL_ASSESSMENTS[number])))
    throw Error("Priority ranking requires the exact 40 scientific assessments");
  if(methods.length!==20||new Set(methods.map(m=>m.id)).size!==20||
     methods.some(m=>!SCIENCE_METHOD_WEIGHT[m.id]||!m.name?.trim()))
    throw Error("Priority ranking requires the exact 20 scientific methods");
  const byId=new Map<string,VerifiedTestRisk[]>();
  for(const risk of confirmedRisks){
    if(phase==="UNKNOWN"||risk.nct!==nct||risk.phase!==phase||
      risk.verified!==true||!assessmentIds.includes(risk.assessmentId)||
      !SCIENCE_METHOD_WEIGHT[risk.methodLevel]||!methods.some(m=>m.id===risk.methodLevel)||
      !risk.riskId.trim()||!risk.finding.trim()||!validDay(risk.verifiedOn)||
      !risk.sourceUrls.length||risk.sourceUrls.some(url=>!/^https:\/\/[^/]+/.test(url))||
      (risk.severity!=="HIGH"&&risk.severity!=="CRITICAL"))
      throw Error("Escalation requires an exact, dated, independently verified test-specific risk");
    const key=risk.assessmentId+":"+risk.methodLevel;
    byId.set(key,[...(byId.get(key)||[]),risk]);
  }
  const rows:PrioritizedScientificTest[]=assessments.flatMap(a=>methods.map(method=>{
    const key=a.id+":"+method.id;
    const rule=baseline(nct,phase,a.id);
    const risks=byId.get(key)||[];
    let tier=rule.tier;
    if(risks.some(r=>r.severity==="CRITICAL"))tier="CRITICAL";
    else if(risks.some(r=>r.severity==="HIGH")&&tier!=="CRITICAL")tier="HIGH";
    const elevated=risks.length>0;
    return {
      id:a.id+":L"+method.id,nct,phase,assessmentId:a.id,assessmentLabel:a.label,
      layerId:a.layerId,level:method.id,methodName:method.name,priority:tier,rank:null,
      phaseApplicability:rule.app,
      basis:phase==="UNKNOWN"?"PHASE_UNVERIFIED" as const:
            elevated?"VERIFIED_RISK" as const:"PHASE_RELEVANCE" as const,
      grade:null,
      matchedRiskIds:risks.map(r=>r.riskId),
      reason:phase==="UNKNOWN"?PRIORITY_PHASE_GUIDANCE.UNKNOWN:
        elevated?"Evidence-linked current-phase risk raises this specific test's investigation priority.":
        (rule.app==="FORWARD_LOOKING"?
          "Future-phase investigation, retained in the 800-test framework but not required for current-phase success. ":
          "Current-phase investigation priority. ")+PRIORITY_PHASE_GUIDANCE[phase]
    };
  }));
  rows.sort((a,b)=>{
    const ap=a.priority==="VERIFY_PHASE"?0:POINTS[a.priority];
    const bp=b.priority==="VERIFY_PHASE"?0:POINTS[b.priority];
    return bp-ap||SCIENCE_METHOD_WEIGHT[b.level]-SCIENCE_METHOD_WEIGHT[a.level]||
      a.assessmentId.localeCompare(b.assessmentId,undefined,{numeric:true})||a.level-b.level;
  });
  rows.forEach((row,i)=>{if(phase!=="UNKNOWN")row.rank=i+1;});
  const counts={CRITICAL:0,HIGH:0,MODERATE:0,LOW:0,VERIFY_PHASE:0};
  for(const row of rows)counts[row.priority]++;
  return {nct,phase,total:rows.length,ranked:phase==="UNKNOWN"?0:rows.length,counts,tests:rows};
}

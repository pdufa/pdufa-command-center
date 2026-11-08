/**
 * Current-phase, last-verified-event scientific ratings and risk flags.
 * Contrasts with the separately preserved prior-phase-end baseline.
 * A risk-to-monitor prompt is NOT evidence that the risk occurred.
 * No archived scoring system imports; no FDA probability is inferred.
 */
import {
  rankTrialAssessments, type TrialPhase, type AssessmentDescriptor,
  type AssessmentTestReview, type AssessmentRanking,
} from "./medical-intelligence-assessment-rankings";

export type PhaseEventKind =
  | "DOSE_UPDATE" | "ENROLLMENT_UPDATE" | "PROTOCOL_UPDATE"
  | "SAFETY_READOUT" | "INTERIM_READOUT" | "PRIMARY_READOUT"
  | "FDA_FEEDBACK" | "PHASE_COMPLETION";
export type TestEvidenceDomain =
  | "BIOLOGY" | "DOSE_PKPD" | "SAFETY" | "EFFICACY"
  | "STATISTICS" | "EXECUTION" | "DESIGN" | "REGULATORY" | "CMC";
export type PhaseRiskDomain =
  | "DOSE_EXPOSURE" | "SAFETY" | "EFFICACY" | "STATISTICS"
  | "TRIAL_EXECUTION" | "REGULATORY" | "CMC" | "DURABILITY"
  | "CONFIRMATORY" | "REAL_WORLD_GENERALIZABILITY";
export type PhaseMilestone = {
  id: string;
  nct: string;
  phase: TrialPhase;
  kind: PhaseEventKind;
  occurredOn: string;
  publishedOn: string;
  title: string;
  sourceUrls: readonly string[];
  verified: boolean;
};
export type EventTestGrade = AssessmentTestReview & {
  milestoneId: string;
  domain: TestEvidenceDomain;
  sourcePublishedOn: string;
};
export type CurrentPhaseRisk = {
  nct: string;
  phase: TrialPhase;
  milestoneId: string;
  domain: PhaseRiskDomain;
  level: "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
  state: "OPEN" | "RESOLVED";
  finding: string;
  evidenceUrls: readonly string[];
};
export type PhaseRiskPrompt = {domain:PhaseRiskDomain;question:string};
/** These are investigation priorities, never factual observed risks. */
export const PHASE_RISK_WATCHLIST:Record<TrialPhase,readonly PhaseRiskPrompt[]>={
  EARLY_PHASE1:[
    {domain:"DOSE_EXPOSURE",question:"Dose escalation, exposure and target engagement adequate?"},
    {domain:"SAFETY",question:"Any dose-limiting or serious emergent toxicity?"},
    {domain:"TRIAL_EXECUTION",question:"First-in-human enrollment and monitoring proceeding as planned?"}
  ],
  PHASE1:[
    {domain:"DOSE_EXPOSURE",question:"Therapeutic exposure and maximum tolerated or selected dose supported?"},
    {domain:"SAFETY",question:"Any serious adverse events, DLTs, discontinuations or immunogenicity?"},
    {domain:"EFFICACY",question:"Are any early signals controlled and interpretable rather than assumed efficacy?"}
  ],
  PHASE2:[
    {domain:"EFFICACY",question:"Magnitude and repeatability of preliminary benefit versus control?"},
    {domain:"STATISTICS",question:"Endpoint validity, missing data, multiplicity and underpowered findings?"},
    {domain:"DOSE_EXPOSURE",question:"Dose-selection and exposure-response evidence support pivotal planning?"},
    {domain:"SAFETY",question:"Toxicity profile and duration adequate for Phase 3 advancement?"}
  ],
  PHASE3:[
    {domain:"EFFICACY",question:"Prespecified primary endpoint and clinically meaningful effect achieved, when reported?"},
    {domain:"STATISTICS",question:"Multiplicity, amendments, missingness, prespecified versus post-hoc estimates?"},
    {domain:"TRIAL_EXECUTION",question:"Enrollment, retention, blinding and site/data integrity risks?"},
    {domain:"SAFETY",question:"Serious harms, exposure and benefit-risk consistency?"},
    {domain:"REGULATORY",question:"FDA endpoints and evidence requirements resolved for the exact indication?"}
  ],
  PHASE4:[
    {domain:"SAFETY",question:"New or cumulative rare/long-term safety signals?"},
    {domain:"DURABILITY",question:"Durability and effectiveness in practice?"},
    {domain:"CONFIRMATORY",question:"Postmarketing commitments and confirmatory results on track?"},
    {domain:"REAL_WORLD_GENERALIZABILITY",question:"Effectiveness across populations and care settings?"}
  ],
  UNKNOWN:[{domain:"TRIAL_EXECUTION",question:"Confirm exact-NCT trial phase before assessing current-phase risk."}]
};
const GRADE_DOMAINS:Record<PhaseEventKind,readonly TestEvidenceDomain[]>={
  DOSE_UPDATE:["DOSE_PKPD","BIOLOGY","SAFETY"],
  ENROLLMENT_UPDATE:["EXECUTION"],
  PROTOCOL_UPDATE:["DESIGN","EXECUTION"],
  SAFETY_READOUT:["SAFETY","DOSE_PKPD"],
  INTERIM_READOUT:["BIOLOGY","DOSE_PKPD","SAFETY","EFFICACY","STATISTICS"],
  PRIMARY_READOUT:["BIOLOGY","DOSE_PKPD","SAFETY","EFFICACY","STATISTICS","DESIGN"],
  FDA_FEEDBACK:["REGULATORY","CMC","DESIGN"],
  PHASE_COMPLETION:[],
};
const DAY=/^\d{4}-\d{2}-\d{2}$/;
function validDay(day:string){
  if(!DAY.test(day))return false;
  const date=new Date(day+"T00:00:00Z");
  return !Number.isNaN(date.valueOf()) && date.toISOString().slice(0,10)===day;
}
function sourceLinks(urls: readonly string[]){
  return urls.length>0 && urls.every(url=>/^https:\/\/[^/]+/.test(url));
}
const SEVERITY:Record<CurrentPhaseRisk["level"],number>={CRITICAL:4,HIGH:3,MODERATE:2,LOW:1};
export type CurrentPhaseSnapshot={
  nct:string;
  phase:TrialPhase;
  latestVerifiedMilestone:PhaseMilestone|null;
  currentScores:AssessmentRanking[];
  activeRisks:CurrentPhaseRisk[];
  resolvedRisks:CurrentPhaseRisk[];
  watchlist:readonly PhaseRiskPrompt[];
  unverifiedEventCount:number;
  note:string;
};

/**
 * Scores are sourced ONLY from the most recent verified milestone in the current
 * phase; they are not an estimate of the entire phase, last completed phase or FDA odds.
 * A protocol/enrollment event may rate execution but never efficacy.
 */
export function assessLatestPhaseActivity(
  descriptors:readonly AssessmentDescriptor[],
  nct:string, phase:TrialPhase, asOf:string,
  milestones:readonly PhaseMilestone[],
  reviews:readonly EventTestGrade[],
  riskFindings:readonly CurrentPhaseRisk[],
):CurrentPhaseSnapshot{
  if(!/^NCT\d{8}$/.test(nct) || !Object.hasOwn(PHASE_RISK_WATCHLIST,phase) || !validDay(asOf))
    throw Error("Valid current trial NCT, phase and as-of date required");
  const eventIds=new Set<string>();
  for(const event of milestones){
    if(event.nct!==nct||event.phase!==phase||!event.id||eventIds.has(event.id))
      throw Error("Event must match the exact NCT and current verified phase without duplicates");
    eventIds.add(event.id);
    if(!validDay(event.occurredOn)||!validDay(event.publishedOn)||
       event.occurredOn>event.publishedOn||event.publishedOn>asOf)
      throw Error("Event requires an actual dated, not future, publication");
    if(!event.title.trim()||!sourceLinks(event.sourceUrls))
      throw Error("Event requires a meaningful description and original-source links");
  }
  const verified=milestones.filter(e=>e.verified).sort((a,b)=>
    b.occurredOn.localeCompare(a.occurredOn)||b.publishedOn.localeCompare(a.publishedOn)||a.id.localeCompare(b.id));
  const latest=verified[0]||null;
  const reviewed:AssessmentTestReview[]=[];
  for(const review of reviews){
    const event=milestones.find(e=>e.id===review.milestoneId);
    if(!event||review.nct!==nct||review.phase!==phase)
      throw Error("Test review must refer to a same-phase exact-NCT event");
    if(!event.verified||!validDay(review.sourcePublishedOn)||
       review.sourcePublishedOn>asOf||review.sourcePublishedOn>review.recordedAt)
      throw Error("Current test grading requires a verified dated source available when reviewed");
    if(review.disposition==="SCORED"){
      if(!GRADE_DOMAINS[event.kind].includes(review.domain))
        throw Error("Event cannot grade scientific claims outside its observed test domain");
      if(!review.evidenceUrls.some(url=>event.sourceUrls.includes(url)))
        throw Error("Test rating must cite the actual milestone source");
    }
    if(event.id===latest?.id) reviewed.push(review);
  }
  const currentScores=rankTrialAssessments(descriptors,nct,phase,reviewed);
  const observed:CurrentPhaseRisk[]=[];
  for(const risk of riskFindings){
    const event=milestones.find(e=>e.id===risk.milestoneId);
    if(!event||!event.verified||risk.nct!==nct||risk.phase!==phase||
       !Object.hasOwn(SEVERITY,risk.level)||!["OPEN","RESOLVED"].includes(risk.state)||
       !risk.finding.trim()||!sourceLinks(risk.evidenceUrls)||
       !risk.evidenceUrls.some(url=>event.sourceUrls.includes(url)))
      throw Error("Risk finding requires verified current-phase evidence and exact event attribution");
    observed.push(risk);
  }
  const activeRisks=observed.filter(r=>r.state==="OPEN").sort((a,b)=>SEVERITY[b.level]-SEVERITY[a.level]||a.domain.localeCompare(b.domain));
  const resolvedRisks=observed.filter(r=>r.state==="RESOLVED");
  return {
    nct,phase,latestVerifiedMilestone:latest,currentScores,activeRisks,resolvedRisks,
    watchlist:PHASE_RISK_WATCHLIST[phase],
    unverifiedEventCount:milestones.length-verified.length,
    note:latest
      ? "Latest verified activity only. Grade coverage is provisional until each applicable test has been reviewed; risks are evidence-specific, not approval probabilities."
      : "No independently verified current-phase milestone available. All scientific grades and observed risks remain unassigned."
  };
}

/** Sole-owner, source-linked medical intelligence boundary. No third-party review gate. */
export type DmiSource={id:string;url:string;title:string;sourceDate:string|null;retrievedAt:string;locator:string;observation:string;status:string;evidenceType:string;reliability:string;identifiers:string[];kind:'FACT'|'INFERENCE'|'HYPOTHESIS'};
export type DmiFinding={text:string;status:string;kind:string;sourceIds:string[];limitations:string};
export type DmiRisk={id:string;title:string;status:string;consequence:string;severity:string;evidence:string;counterevidence:string;resolution:string;missingDocuments:string[];sourceIds:string[];counterSourceIds:string[]};
export type DmiDecision={leading:string;confidence:string;rationale:string;contraryArgument:string;evidenceWouldChange:string;sourceIds:string[];predictionTimestamp:string};
export type DmiApplication={id:string;applicationNumber:string|null;applicationType:string;reviewCycle:string;company:string;ticker:string;drug:string;indication:string;nctIds:string[];pdufa:{date:string|null;status:string;sourceIds:string[]};progress:{stage:string;status:string};outcome:DmiDecision;timing:DmiDecision;blockers:string[];sections:{id:string;title:string;findings:DmiFinding[]}[];failureRisks:DmiRisk[];arguments:{approval:{text:string;sourceIds:string[]}[];crl:{text:string;sourceIds:string[]}[];delay:{text:string;sourceIds:string[]}[]};sources:DmiSource[];independentChallenge:{status:string;independenceStatement:string};gaps:string[]};
export type DmiSnapshot={schemaVersion:1;asOf:string;generatedAt:string;inventory:{poolTrials:number;focusTrials:number;applications:number;metadataScreenedTrials:number;sourceExtractedTrials:number;fullyReviewedTrials:number;incompleteTrials:number;completedDecisions:number;unresolvedBlockers:number;sourceDocuments:number};applications:DmiApplication[];sources:DmiSource[];limitations:string[];conditions:unknown[];precedents:unknown[];installationLevels?:{level:number;name:string;state:string;evidence:string}[]};
const outcomes=new Set(['Traditional approval','Accelerated approval','Complete Response Letter','Withdrawal','Indeterminate']);
const timing=new Set(['Decision by current PDUFA goal date','Formal PDUFA extension','Missed goal date without documented formal extension','Indeterminate']);
export function parseDeepMedicalSnapshot(raw:unknown):DmiSnapshot{
 if(!raw||typeof raw!=='object')throw Error('DMI_SNAPSHOT_INVALID');
 const packet=raw as DmiSnapshot;
 const keys=new Set(['schemaVersion','asOf','generatedAt','inventory','applications','sources','limitations','conditions','precedents','installationLevels']);
 if(Object.keys(raw).some(key=>!keys.has(key)))throw Error('DMI_UNKNOWN_SCHEMA_FIELD');
 if(packet.schemaVersion!==1||!Array.isArray(packet.applications)||!Array.isArray(packet.sources)||!Number.isFinite(Date.parse(packet.generatedAt)))throw Error('DMI_SNAPSHOT_INVALID');
 const ids=new Set<string>(),allSources=new Map<string,DmiSource>();
 for(const s of packet.sources){
  if(allSources.has(s.id)||!s.id||!/^https:\/\//.test(s.url)||!s.observation||!Number.isFinite(Date.parse(s.retrievedAt)))throw Error('DMI_SOURCE_INVALID');
  if(s.sourceDate&&(!Number.isFinite(Date.parse(s.sourceDate))||s.sourceDate>packet.asOf.slice(0,10)))throw Error('DMI_FUTURE_SOURCE');
  allSources.set(s.id,s);
 }
 for(const a of packet.applications){
  if(!a.id||ids.has(a.id)||!a.drug||!a.indication||!a.nctIds.length||a.nctIds.some(n=>!/^NCT\d{8}$/.test(n)))throw Error('DMI_APPLICATION_IDENTITY_INVALID');ids.add(a.id);
  if(!outcomes.has(a.outcome.leading)||!timing.has(a.timing.leading))throw Error('DMI_SEPARATE_DECISION_LABELS_REQUIRED');
  // A provisional application judgment may be prepared by the owner alone.
  // It still needs dated sources and a contrary argument, not a second reviewer.
  if(a.outcome.leading!=='Indeterminate'&&a.outcome.sourceIds.length===0)throw Error('DMI_OWNER_PROVISIONAL_DECISION_NEEDS_CITED_EVIDENCE');
  if(a.pdufa.date&&a.pdufa.status!=='VERIFIED_CURRENT_APPLICATION_GOAL')throw Error('DMI_GOAL_NOT_VERIFIED');
  for(const source of a.sources)if(!allSources.has(source.id))throw Error('DMI_SOURCE_REFERENCE_INVALID');
  const refs=[...a.outcome.sourceIds,...a.timing.sourceIds,...a.pdufa.sourceIds,...a.sections.flatMap(s=>s.findings.flatMap(f=>f.sourceIds)),...a.failureRisks.flatMap(r=>[...r.sourceIds,...r.counterSourceIds]),...Object.values(a.arguments).flatMap(items=>items.flatMap(i=>i.sourceIds))];
  if(refs.some(id=>!allSources.has(id)))throw Error('DMI_SOURCE_REFERENCE_INVALID');
  if(a.failureRisks.some(r=>r.status==='UNKNOWN'&&r.severity!=='UNKNOWN'))throw Error('DMI_UNKNOWN_IS_NOT_CONFIRMED_DEFICIENCY');
  for(const d of [a.outcome,a.timing])if(!d.rationale||!d.contraryArgument||!d.evidenceWouldChange||!Number.isFinite(Date.parse(d.predictionTimestamp)))throw Error('DMI_DECISION_TRACE_REQUIRED');
 }
 return packet;
}

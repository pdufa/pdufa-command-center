/**
 * Attach SAVED regulatory application candidates to the same published POOL
 * clinical trial rows. A PDUFA target belongs to an application, not to an NCT
 * trial. Joining an application never creates a trial, establishes pivotal
 * status, or establishes that the target is currently pending.
 */
import {parseEvidenceCsv} from "./restriction-evidence";
import type {PoolTrialRecord} from "./pool-pipeline-funnel";

export type ToolPdufaApplication={
  eventKey:string;
  ticker:string;
  drug:string;
  indication:string;
  targetDate:string;
  targetConfirmation:string;
  savedOutcome:string;
  savedCheckStatus:string;
  decisionDate:string;
  applicationType:string;
  evidenceUrl:string;
  checkedAt:string;
  studyRole:"NOT_ESTABLISHED";
};
export type ToolPdufaIndex=Map<string,ToolPdufaApplication[]>;

const validNct=(value:string)=>/^NCT\d{8}$/.test(value);
const validDate=(value:string)=>/^\d{4}-\d{2}-\d{2}$/.test(value)
  && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0,10)===value;
function sourceUrl(value:string):string{
  try{const url=new URL(value);return url.protocol==="https:"&&!url.username&&!url.password?url.href:"";}catch{return "";}
}
function lookupKey(nct:string,ticker:string){return nct+"|"+ticker.toUpperCase();}

/**
 * nct_id may contain several explicitly recorded NCT IDs. Link only against
 * the exact NCT and exact issuer ticker. Avoid ticker-only, date-only, or
 * program-name fuzzy joins. Rows without a valid NCT stay solely as programs.
 */
export function buildToolPdufaIndex(csv:string):ToolPdufaIndex{
  const rows=parseEvidenceCsv(csv);
  if(rows.length>5000 || (rows.length>0&&!["event_key","ticker","nct_id","pdufa_date","pdufa_confirmation"]
    .every(field=>field in rows[0])))throw Error("PDUFA_CANDIDATE_SOURCE_INVALID");
  const index:ToolPdufaIndex=new Map();
  for(const row of rows){
    const ticker=(row.ticker||"").toUpperCase().trim();
    const eventKey=(row.event_key||"").trim();
    if(!/^[A-Z][A-Z0-9.-]{0,14}$/.test(ticker)||!eventKey.startsWith(ticker+"|"))continue;
    const target=(row.pdufa_date||"").trim();
    const item:ToolPdufaApplication={
      eventKey,ticker,drug:(row.drug||"").trim(),indication:(row.indication||"").trim(),
      targetDate:validDate(target)?target:"",
      targetConfirmation:(row.pdufa_confirmation||"UNVERIFIED").trim(),
      savedOutcome:(row.outcome||"").trim(),
      savedCheckStatus:(row.check_status||"").trim(),
      decisionDate:validDate((row.decision_date||"").trim())?row.decision_date.trim():"",
      applicationType:(row.application_type||"").trim(),
      evidenceUrl:sourceUrl(row.pdufa_evidence_url||""),
      checkedAt:(row.last_checked||"").trim(),
      studyRole:"NOT_ESTABLISHED"
    };
    const ncts=[...new Set((row.nct_id||"").toUpperCase().split(/[|;,\s]+/).filter(validNct))];
    for(const nct of ncts){
      const key=lookupKey(nct,ticker);
      const group=index.get(key)||[];
      if(!group.some(entry=>entry.eventKey===eventKey))group.push(item);
      index.set(key,group);
    }
  }
  return index;
}
export function matchedToolPdufaApplications(trial:PoolTrialRecord,index:ToolPdufaIndex|null):ToolPdufaApplication[]{
  if(!index||!trial.id.startsWith("TRIAL|")||!trial.ticker)return [];
  const nct=trial.id.slice(6);
  if(!validNct(nct))return [];
  return index.get(lookupKey(nct,trial.ticker))||[];
}

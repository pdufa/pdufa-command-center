/**
 * Read-only, exact-NCT acceptance evidence for the CURRENT FOCUS final listing.
 *
 * The source of population membership is p3PostDataActive.json ONLY.
 * POOL, the 741/375 historical Phase-3 census and the all-phase TOOLS
 * market-cap screen must never be unioned into this acceptance roster.
 * Source pointers are not independently adjudicated clinical/FDA proof.
 */
import snapshot from "../data/p3PostDataActive.json";

export type FocusTrialGateState="RECORDED_POINTER"|"SOURCE_REVIEW_REQUIRED"|"MISSING_EVIDENCE";
export type FocusTrialGateId=
  "trial-identity"|"listing-market-cap"|"final-phase3-readout"|
  "therapy-indication"|"commercial-rights"|"fda-pathway"|"sheets-sync";
export type FocusTrialGate={
  id:FocusTrialGateId;title:string;state:FocusTrialGateState;
  note:string;sourceUrl:string|null;
};
export type FocusTrialAuditRow={
  nct:string;ticker:string;company:string;gates:FocusTrialGate[];
  pointers:number;review:number;missing:number;independentlyVerified:0;
};
export type FocusTrialAudit={
  asOf:string;sourceUrl:string;trialCount:number;uniqueCompanies:number;
  checksPerTrial:7;totalChecks:number;pointers:number;review:number;missing:number;
  independentlyVerified:0;
  rows:FocusTrialAuditRow[];
};
const NCT=/^NCT\d{8}$/;
const TICKER=/^[A-Z0-9][A-Z0-9.-]{0,14}$/;
const http=(v:unknown):string|null=>typeof v==="string"&&
  /^https:\/\/[^\s/]+(?:\/[^\s]*)?$/.test(v)?v:null;
const obj=(v:unknown):v is Record<string,unknown>=>
  v!==null&&typeof v==="object"&&!Array.isArray(v);
const text=(v:unknown)=>typeof v==="string"?v.trim():"";

export function assessFinalFocusRoster(input:unknown):FocusTrialAudit {
  if(!obj(input)||input.schemaVersion!==1||
     !/^\d{4}-\d{2}-\d{2}$/.test(text(input.asOf))||
     !Array.isArray(input.records)||input.records.length===0||
     input.records.length>5000||text(input.origin)!=="FOCUS / Google Sheet"||
     !http(input.source)||!String(input.source).startsWith("https://docs.google.com/spreadsheets/"))
    throw new Error("FOCUS_FINAL_ROSTER_INVALID");
  const asOf=text(input.asOf);
  const sheet=http(input.source)!;
  const seen=new Set<string>();
  const rows:FocusTrialAuditRow[]=[];
  for(const entry of input.records){
    if(!obj(entry))throw new Error("FOCUS_FINAL_ROW_INVALID");
    const nct=text(entry.nct),ticker=text(entry.ticker),company=text(entry.company);
    // Enforce exact source identities and uniqueness; do not silently merge
    // duplicate NCTs, substitute a ticker or guess a missing identifier.
    if(!NCT.test(nct)||!TICKER.test(ticker)||!company||seen.has(nct))
      throw new Error("FOCUS_FINAL_IDENTITY_OR_DUPLICATE");
    seen.add(nct);
    const resultSource=http(entry.resultsUrl);
    const regulator=http(entry.regulatoryUrl);
    const cap=typeof entry.marketCap==="number"?entry.marketCap:NaN;
    const capPointer=Number.isFinite(cap)&&cap>=300_000_000&&cap<=10_000_000_000;
    const drug=text(entry.drug),indication=text(entry.indication);
    const rightsSource=http(entry.rightsSourceUrl);
    const fdaStatus=text(entry.fdaStatus);
    const gates:FocusTrialGate[]=[
      {id:"trial-identity",title:"Exact final-list NCT and recorded issuer",
        state:"RECORDED_POINTER",
        note:"Exact NCT and ticker are recorded in the FOCUS roster. Independent current sponsor/product linkage remains to be verified.",
        sourceUrl:"https://clinicaltrials.gov/study/"+nct},
      {id:"listing-market-cap",title:"Current public listing and $300M–$10B cap",
        state:capPointer?"RECORDED_POINTER":"MISSING_EVIDENCE",
        note:capPointer?"FOCUS reports a dated in-range cap as of "+asOf+"; this does not establish a live listing, quote, or commercial rights.":
          "Missing, malformed, or outside-range market-cap evidence; retain for review, do not auto-qualify.",
        sourceUrl:capPointer?sheet:null},
      {id:"final-phase3-readout",title:"Exact public final pivotal Phase 3 readout",
        state:resultSource?"SOURCE_REVIEW_REQUIRED":"MISSING_EVIDENCE",
        note:resultSource?"A linked source is recorded, but a registry study page or filing is not itself independent proof of a positive, final pivotal readout.":
          "No trial-specific result-source URL in the final roster.",
        sourceUrl:resultSource},
      {id:"therapy-indication",title:"Exact drug, indication and pivotal population",
        state:drug&&indication?"SOURCE_REVIEW_REQUIRED":"MISSING_EVIDENCE",
        note:drug&&indication?"Drug and indication names are recorded; independently reconcile with NCT and FDA application cycle.":
          "Explicit therapy and indication are not jointly recorded in this FOCUS snapshot; do not infer them from company.",
        sourceUrl:drug&&indication?resultSource:null},
      {id:"commercial-rights",title:"Current issuer's territorial commercial rights",
        state:text(entry.commercialRights)&&rightsSource?"SOURCE_REVIEW_REQUIRED":"MISSING_EVIDENCE",
        note:text(entry.commercialRights)&&rightsSource?"Commercial rights have a source pointer; independent ownership review is required.":
          "Exact program, territory and developer/license rights are not source-attested in this roster.",
        sourceUrl:rightsSource},
      {id:"fda-pathway",title:"Exact FDA application status and PDUFA cycle",
        state:fdaStatus&&regulator?"SOURCE_REVIEW_REQUIRED":"MISSING_EVIDENCE",
        note:fdaStatus&&regulator?"Roster reports \""+fdaStatus+"\". Planned filing, submitted filing and actual FDA-accepted PDUFA date are different stages; verify independently.":
          "Missing FDA pathway source or status in the roster.",
        sourceUrl:regulator},
      {id:"sheets-sync",title:"Signed final-list Google Sheets synchronization",
        state:"SOURCE_REVIEW_REQUIRED",
        note:"The dated FOCUS snapshot identifies the Sheets source. This alone does not verify a successful nightly read/write round trip or no dropped records.",
        sourceUrl:sheet},
    ];
    if(gates.length!==7||new Set(gates.map(g=>g.id)).size!==7)
      throw new Error("FOCUS_FINAL_GATES_INCOMPLETE");
    rows.push({nct,ticker,company,gates,
      pointers:gates.filter(g=>g.state==="RECORDED_POINTER").length,
      review:gates.filter(g=>g.state==="SOURCE_REVIEW_REQUIRED").length,
      missing:gates.filter(g=>g.state==="MISSING_EVIDENCE").length,
      independentlyVerified:0});
  }
  const sum=(key:"pointers"|"review"|"missing")=>rows.reduce((n,r)=>n+r[key],0);
  return {asOf,sourceUrl:sheet,trialCount:rows.length,
    uniqueCompanies:new Set(rows.map(r=>r.ticker)).size,
    checksPerTrial:7,totalChecks:rows.length*7,
    pointers:sum("pointers"),review:sum("review"),missing:sum("missing"),
    independentlyVerified:0,rows};
}
export const FOCUS_FINAL_TRIAL_AUDIT=assessFinalFocusRoster(snapshot);

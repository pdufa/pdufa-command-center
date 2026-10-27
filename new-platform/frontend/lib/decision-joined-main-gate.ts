import {assessJoinedDecisionResearch,type JoinedDecisionResearchGate} from "./decision-joined-research-gate";
import {auditHistoricalMarketPair,type HistoricalMarketRecord} from "./decision-market-audit";
import type {ResearchReadiness} from "./decision-research-readiness";
import type {AnalogueTarget,HistoricalPdufaAnalogue} from "./decision-historical-analogues";
import type {HistoricalCoverageInput} from "./decision-historical-coverage";
import type {HistoricalSourceRecord} from "./decision-historical-source-chronology";

/** MAIN joins research evidence with separately audited market data; no trading signal is issued. */
export type MainEvidence={programId:string;ticker:string;asOf:string;restrictionsReviewed:boolean;unresolvedCriticalRisks:number;marketEntry:HistoricalMarketRecord|null;marketExit:HistoricalMarketRecord|null};
export type JoinedMainDecision=JoinedDecisionResearchGate&{mainStatus:"NOT_READY"|"EVIDENCE_READY_FOR_REVIEW";mainIssues:string[];tradeAuthorized:false};
export function assessJoinedMainDecision(
 science:ResearchReadiness|null,outcome:ResearchReadiness|null,target:AnalogueTarget,
 history:HistoricalPdufaAnalogue[],coverage:HistoricalCoverageInput,
 chronology:Record<string,HistoricalSourceRecord[]>,main:MainEvidence|null,now=new Date()
):JoinedMainDecision{
 const research=assessJoinedDecisionResearch(science,outcome,target,history,coverage,chronology,now);
 const issues=[...research.issues];
 const mainIssues:string[]=[];
 if(!main)mainIssues.push("MAIN: evidence record missing");
 else{
  if(main.programId!==target.programId||main.asOf!==target.asOf)mainIssues.push("MAIN: program or cutoff mismatch");
  if(!Number.isFinite(Date.parse(main.asOf))||Date.parse(main.asOf)>now.getTime()+300000)mainIssues.push("MAIN: invalid or future cutoff");
  if(!/^[A-Z][A-Z0-9.-]{0,9}$/.test(main.ticker))mainIssues.push("MAIN: invalid ticker");
  if(main.restrictionsReviewed!==true)mainIssues.push("MAIN: restrictions not reviewed");
  if(!Number.isSafeInteger(main.unresolvedCriticalRisks)||main.unresolvedCriticalRisks!==0)mainIssues.push("MAIN: unresolved critical risks");
  if(!main.marketEntry||!main.marketExit)mainIssues.push("MAIN: audited market pair missing");
  else{
   if(main.marketEntry.programId!==main.programId||main.marketExit.programId!==main.programId||
      main.marketEntry.ticker!==main.ticker||main.marketExit.ticker!==main.ticker)
    mainIssues.push("MAIN: market pair identity mismatch");
   const entryAt=Date.parse(main.marketEntry.observedAt),exitAt=Date.parse(main.marketExit.observedAt),cutoff=Date.parse(main.asOf);
   if(!Number.isFinite(entryAt)||!Number.isFinite(exitAt)||entryAt>=cutoff||exitAt>=cutoff)mainIssues.push("MAIN: market observations must precede decision cutoff");
   const entryCaptured=Date.parse(main.marketEntry.capturedAt),exitCaptured=Date.parse(main.marketExit.capturedAt);
   if(!Number.isFinite(entryCaptured)||!Number.isFinite(exitCaptured)||entryCaptured>=cutoff||exitCaptured>=cutoff)mainIssues.push("MAIN: market captures must precede decision cutoff");
   const market=auditHistoricalMarketPair(main.marketEntry,main.marketExit);
   mainIssues.push(...market.issues.map(issue=>"MAIN: "+issue));
  }
 }
 issues.push(...mainIssues);
 return {...research,status:issues.length?"NOT_READY":"EVIDENCE_READY_FOR_REVIEW",issues,
  mainStatus:mainIssues.length?"NOT_READY":"EVIDENCE_READY_FOR_REVIEW",mainIssues,tradeAuthorized:false};
}

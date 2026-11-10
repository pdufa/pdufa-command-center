/** Dated MAIN R92 crosswalk acceptance: current-registry text only.
 * Public protocol/result alignment may have been edited after unblinding.
 * Never promote this receipt to prospectively approved SAP certification.
 */
import source from "../data/focus-r92-current-protocol-results-primary-text-audit-20261110.json";
import previous from "../data/focus-r91-posted-original-results-readbacks-20261110.json";
import {R92_CURRENT_PROTOCOL_RESULTS_ROSTER} from "./focus-r92-protocol-results-crosswalk";

function norm(x:string|null){
 return (x??"").toLowerCase().normalize("NFKC")
  .replace(/[%]/gu," percent ")
  .replace(/[^a-z0-9]+/gu," ").replace(/\s+/gu," ").trim();
}
export function buildR92DatedCrosswalkAudit(input:typeof source=source){
 const r=R92_CURRENT_PROTOCOL_RESULTS_ROSTER;
 if(!r||r.registeredResultNcts!==12||r.exactFocusTrials!==29||
    r.provisionalFDACycles!==23||
    r.independentScientificSignoffs!==0||
    r.originalSignedSAPsAuthenticated!==0||
    input.schema!=="MAIN_R92_12_NCT_CURRENT_REGISTRY_PRIMARY_PROTOCOL_TO_POSTED_TEXT_READBACKS_NOT_PRE_UNBLINDING_SAP"||
    input.observedDateUtc!=="2026-11-10"||
    input.sourceOriginalEffectiveDateBeforeUnblindingIndependentlyKnown!==false||
    input.sourceRegulatoryStatus!=="CURRENT_REGISTRY_TEXT_ONLY"||
    input.researchOnly!==true||input.FDAOutcome!=="ABSTAIN"||
    input.rows.length!==12||previous.rows.length!==12||
    input.counts.exactFocusTrialPopulation!==29||
    input.counts.provisionalApplicationCycles!==23||
    input.counts.exactNctsChecked!==12||
    input.counts.originalCurrentProtocolPrimaryEntries!==16||
    input.counts.currentPostedResultsPrimaryEntries!==16||
    input.counts.exactNormalizedTitleAndTimeFrameTextMatches!==16||
    input.counts.titleMatchesWithDifferingTimeFrame!==0||
    input.counts.lexicalOrAmbiguousReviewEntries!==0||
    input.counts.currentRawResponseHashesMatchingR91!==12||
    input.counts.independentlyAuthenticatedSignedFinalSAPs!==0||
    input.counts.qualifiedClinicalStatisticalReviewSignoffs!==0||
    input.counts.validatedFDAForecasts!==0)return null;
 const prev=new Map(previous.rows.map(x=>[x.nct,x]));
 const roster=new Map(r.rows.map(x=>[x.nct,x]));
 if(prev.size!==12||roster.size!==12)return null;
 const seen=new Set<string>(),items=[];
 let planned=0,posted=0,matched=0;
 for(const row of input.rows){
  const past=prev.get(row.nct),original=roster.get(row.nct);
  if(!past||!original||seen.has(row.nct)||row.ticker!==original.ticker||
     row.sourceUrl!==original.sourceUrl||
     row.currentOriginalApiSha256!==past.officialPublicRawSourceSha256||
     row.archivedR91ApiSha256!==past.officialPublicRawSourceSha256||
     row.currentApiSourceByteMatchesR91!==true||
     !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/u.test(row.checkedAtUtc)||
     row.currentProtocolPrimaryCount!==row.plannedPrimaryOutcomes.length||
     row.postedResultsPrimaryCount!==row.postedPrimaryOutcomes.length||
     row.postedResultsPrimaryCount!==past.observedPrimaryOutcomeCount||
     row.exactTitleAndTimeFrameMatches!==row.postedResultsPrimaryCount||
     row.matchedTitleButDifferingTimeFrame!==0||
     row.ambiguousOrLexicalResearchReview!==0||
     row.plannedEntriesWithoutExactText.length!==0||
     row.textualCorrespondence.length!==row.postedResultsPrimaryCount||
     row.originalPreUnblindingSignedSAPAuthenticated!==false||
     row.originalRegulatedFinalProtocolApprovalVerified!==false||
     row.independentClinicalEndpointAdjudication!==false||
     row.qualifiedIndependentStatisticalReview!==false||
     row.FDAOutcome!=="ABSTAIN")return null;
  seen.add(row.nct);
  const sourceTitles=past.originalReportedPrimaryOutcomes.map(x=>({
   title:x.title,timeFrame:x.timeFrame
  }));
  const planMap=new Map(row.plannedPrimaryOutcomes.map(x=>[x.key,x]));
  if(planMap.size!==row.plannedPrimaryOutcomes.length)return null;
  for(let i=0;i<row.postedPrimaryOutcomes.length;i++){
   const p=row.postedPrimaryOutcomes[i],old=sourceTitles[i],
     match=row.textualCorrespondence[i];
   if(!old||p.title!==old.title||p.timeFrame!==old.timeFrame||
      !match||match.postedOutcomeKey!==p.key||
      match.postedTitle!==p.title||match.postedTimeFrame!==p.timeFrame||
      match.state!=="EXACT_TITLE_AND_TIME_FRAME"||
      match.interpretation!=="TEXTUAL_REGISTRY_LEAD_ONLY_NO_PRESPECIFICATION_OR_SAP_CLAIM"||
      match.possibleProtocolKeys.length!==1)return null;
   const protocol=planMap.get(match.possibleProtocolKeys[0]);
   if(!protocol||norm(protocol.title)!==norm(p.title)||
      norm(protocol.timeFrame)!==norm(p.timeFrame))return null;
  }
  planned+=row.currentProtocolPrimaryCount;
  posted+=row.postedResultsPrimaryCount;
  matched+=row.exactTitleAndTimeFrameMatches;
  items.push({
   nct:row.nct,ticker:row.ticker,
   studyUrl:row.sourceUrl,
   protocolPrimaryCount:row.currentProtocolPrimaryCount,
   postedPrimaryCount:row.postedResultsPrimaryCount,
   exactTextualMatches:row.exactTitleAndTimeFrameMatches,
   reportedPrimaryTitles:row.postedPrimaryOutcomes.map(x=>x.title),
   sourceSHA256:row.currentOriginalApiSha256,
   originalSAPProspectivityVerified:false as const,
   qualifiedClinicalReviewSigned:false as const,
   FDAForecast:"ABSTAIN" as const
  });
 }
 if(seen.size!==12||[...roster.keys()].some(id=>!seen.has(id))||
    planned!==16||posted!==16||matched!==16)return null;
 items.sort((a,b)=>a.ticker.localeCompare(b.ticker)||a.nct.localeCompare(b.nct));
 return {
  schema:"MAIN_R92_CURRENT_PRIMARY_TEXT_12_NCT_SOURCE_AUDIT_NO_SAP_SIGNOFF" as const,
  sourceDateUtc:input.observedDateUtc,
  checkedNcts:12 as const,
  plannedPrimaryTextEntries:16 as const,
  postedPrimaryTextEntries:16 as const,
  exactCurrentRegistryTitleTimeframeMatches:16 as const,
  observedTextDifferences:0 as const,
  rawR91SourceHashesStable:12 as const,
  independentSignedSAPAttestations:0 as const,
  qualifiedIndependentMedicalReviews:0 as const,
  calibratedFDAPredictions:0 as const,
  rows:items
 };
}
export const R92_DATED_CROSSWALK_AUDIT=buildR92DatedCrosswalkAudit();

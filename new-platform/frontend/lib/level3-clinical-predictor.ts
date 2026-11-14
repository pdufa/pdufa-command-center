/** Owner research hypothesis, not a calibrated FDA application model.
 * v1 deliberately supports only the source-extracted ORCA abstinence contrasts.
 * Do not generalize endpoint direction, odds ratios or significance to other diseases.
 */
import type {EvidenceTrial,Source} from './level16-assessment-runner';

export type ClinicalLean = 'APPROVAL_LEAN'|'CRL_LEAN'|'INSUFFICIENT_EVIDENCE';
export type Level3Prediction = {
 call:ClinicalLean; label:string; methodVersion:'level3-clinical-lean-v1';
 scope:'LEVEL3_CLINICAL_EVIDENCE_ONLY'; fdaApplicationForecast:false;
 evidenceCutoffDate:string; reasons:string[]; contradictions:string[];
 limitations:string[]; missingEvidence:string[]; sources:Source[];
 ownerReviewStatus:'OWNER_NOT_REVIEWED'; score:null; approvalProbability:null;
 prospectivelyBlind:false; historicalPredictionInputPermitted:false;
};
const labels={APPROVAL_LEAN:'Approval lean',CRL_LEAN:'CRL lean',INSUFFICIENT_EVIDENCE:'Insufficient evidence'};
const profiles:Record<string,{pmid:string;primaryIds:string[]}>= {
 NCT04576949:{pmid:'37432430',primaryIds:['PRIMARY_CYT6_W3_6','PRIMARY_CYT12_W9_12']},
 NCT05206370:{pmid:'40257755',primaryIds:['PRIMARY_CYT6_W3_6','PRIMARY_CYT12_W9_12']},
};
/** A directional comparison is meaningful only in this higher-is-better abstinence domain.
 * An inconclusive interval, a null result or an unavailable document is not adverse evidence.
 */
export function abstinenceDirection(c:EvidenceTrial['reportedComparisons'][number]):'FAVORABLE'|'ADVERSE'|'UNRESOLVED'{
 const [lo,hi]=c.ci95Reported;
 const counts=[c.activeAbstinent,c.activeRandomized,c.activePct,c.placeboAbstinent,c.placeboRandomized,c.placeboPct];
 if(!counts.every(Number.isFinite)||c.activeRandomized<=0||c.placeboRandomized<=0||
  c.activeAbstinent<0||c.activeAbstinent>c.activeRandomized||c.placeboAbstinent<0||c.placeboAbstinent>c.placeboRandomized||
  Math.abs(100*c.activeAbstinent/c.activeRandomized-c.activePct)>=0.051||
  Math.abs(100*c.placeboAbstinent/c.placeboRandomized-c.placeboPct)>=0.051||
  c.ci95Reported.length!==2||![lo,hi,c.oddsRatioReported].every(Number.isFinite)||
  lo<=0||lo>c.oddsRatioReported||c.oddsRatioReported>hi)return 'UNRESOLVED';
 if(c.activePct>c.placeboPct&&lo>1)return 'FAVORABLE';
 if(c.activePct<c.placeboPct&&hi<1)return 'ADVERSE';
 return 'UNRESOLVED';
}
export function predictLevel3(t:EvidenceTrial,cutoff:string):Level3Prediction{
 const level=t.levels.find(l=>l.level===3);
 const reasons:string[]=[],missingEvidence:string[]=[];
 const limitations=[
  'Unvalidated, conditional clinical-evidence hypothesis. Approval lean and CRL lean are not an FDA decision, numerical score or probability.',
  'This trial is not the complete application. Manufacturing, inspections, regulatory correspondence, current filing status and other supporting trials are not evaluated by this Level 3 rule.',
  'Application-cycle links remain provisional. No pending FDA action or PDUFA date is inferred.',
  'Saved sources only at the stated cutoff; this run retrieves no new evidence and is not a prospectively blind prediction.',
  'Reported confidence intervals provide a bounded directional signal, not a verification of multiplicity, prespecification or clinical benefit-risk adequacy.',
  ...(level?.limitations||[]),
 ];
 const contradictions=[...(level?.contradictions||[])];
 let call:ClinicalLean='INSUFFICIENT_EVIDENCE';
 const profile=profiles[t.nct],binding=t.publishedComparisonSource;
 const source=binding&&t.sources.find(s=>s.url===binding.sourceUrl&&s.digest===binding.documentSha256&&s.date===binding.publicationDate);
 if(!t.phases.includes('PHASE3')||t.phases.includes('NA'))missingEvidence.push('Confirmatory Phase 3 clinical evidence is not available to this FDA-direction rule. Earlier-phase trials do not require future Phase 3 results for their own phase assessment.');
 if(t.applicationMappingStatus!=='PROVISIONAL_NOT_VERIFIED'||t.provisionalApplicationCycleIds.length!==1)missingEvidence.push('An unambiguous provisional application relationship is missing; no cross-trial or cross-application substitution is permitted.');
 if(!profile)missingEvidence.push('A source-extracted, disease-specific primary-endpoint interpretation is not implemented for this trial. Registry posting or planned endpoints alone cannot produce a lean.');
 const validDate=(value:string)=>/^\d{4}-\d{2}-\d{2}$/.test(value)&&Number.isFinite(Date.parse(value+'T00:00:00Z'))&&new Date(value+'T00:00:00Z').toISOString().slice(0,10)===value;
 if(!validDate(cutoff)||!profile||!binding||binding.nct!==t.nct||binding.pmid!==profile.pmid||binding.endpointDomain!=='CO_VERIFIED_SMOKING_ABSTINENCE'||
  !source||!validDate(binding.publicationDate)||binding.publicationDate>cutoff||
  !/(Z|[+-]\d{2}:\d{2})$/.test(binding.retrievedAt)||!Number.isFinite(Date.parse(binding.retrievedAt))||new Date(binding.retrievedAt).toISOString().slice(0,10)>cutoff){
  missingEvidence.push('Original full-text receipt, exact-NCT publication binding and in-cutoff source version must be reconciled.');
 }
 if(!t.reportedClinicalResultsPresent||!t.reportedComparisons.length)missingEvidence.push('Collected quantitative clinical results are missing. A registered endpoint is not demonstrated efficacy.');
 if(!t.publishedSafety)missingEvidence.push('Original safety observations are missing; absence of a reported harm is not safety clearance.');
 if(profile){
  const primary=t.reportedComparisons.filter(c=>c.classification==='PRIMARY');
  if(primary.length!==profile.primaryIds.length||!profile.primaryIds.every(id=>primary.filter(c=>c.id===id).length===1))missingEvidence.push('The complete exact primary comparison set is missing or duplicated. Secondary-only or subgroup results cannot substitute.');
  if(!missingEvidence.length){
   const directions=primary.map(abstinenceDirection);
   for(const c of primary)reasons.push(`${c.id}: abstinence ${c.activePct}% (${c.activeAbstinent}/${c.activeRandomized}) versus ${c.placeboPct}% (${c.placeboAbstinent}/${c.placeboRandomized}); reported OR ${c.oddsRatioReported}, 95% CI ${c.ci95Reported.join('–')}. ${c.locator}.`);
   if(directions.every(d=>d==='FAVORABLE')){
    call='APPROVAL_LEAN';reasons.push('Both extracted primary abstinence comparisons favor treatment, with reported intervals above the null. This supports only a conditional clinical-efficacy lean toward approval.');
   }else if(directions.every(d=>d==='ADVERSE')){
    call='CRL_LEAN';reasons.push('Both extracted primary abstinence comparisons favor placebo, with reported intervals below the null. This is affirmative adverse clinical evidence supporting a conditional CRL lean, not a regulatory finding.');
   }else missingEvidence.push('Primary directions conflict, are inconclusive or fail numerical consistency. Reconcile original results before a directional estimate.');
   if(call!=='INSUFFICIENT_EVIDENCE'&&t.reportedComparisons.filter(c=>c.classification==='SECONDARY').some(c=>abstinenceDirection(c)===(call==='APPROVAL_LEAN'?'ADVERSE':'FAVORABLE'))){
    call='INSUFFICIENT_EVIDENCE';contradictions.push('A secondary outcome runs against the primary directional hypothesis; reconcile endpoints and time windows.');
   }
  }
 }
 if(call==='INSUFFICIENT_EVIDENCE')reasons.push('Abstain from a directional call until the listed evidence or interpretation gaps are resolved. Missing evidence does not imply a CRL.');
 if(binding?.indexedPublicationDate&&binding.indexedPublicationDate!==binding.publicationDate)limitations.push(`Publication dates differ: primary report online date ${binding.publicationDate}; indexed issue date ${binding.indexedPublicationDate}. Preserve both dates; neither is an unblinding or database-lock date.`);
 if(t.publishedSafety)limitations.push('Serious events, deaths and discontinuations are reported in the safety evidence. Investigator judgments of unrelatedness do not establish absence of risk; safety denominators and clinical importance require owner review.');
 if(t.statisticalChronology)limitations.push('ORCA-2 SAP chronology/database lock/unblinding and protocol version discrepancies remain unresolved. Dates alone do not establish post-hoc analysis.');
 return {call,label:labels[call],methodVersion:'level3-clinical-lean-v1',scope:'LEVEL3_CLINICAL_EVIDENCE_ONLY',fdaApplicationForecast:false,evidenceCutoffDate:cutoff,reasons,contradictions,limitations,missingEvidence,sources:source?[source]:t.sources.filter(s=>s.kind==='REGISTRY'),ownerReviewStatus:'OWNER_NOT_REVIEWED',score:null,approvalProbability:null,prospectivelyBlind:false,historicalPredictionInputPermitted:false};
}

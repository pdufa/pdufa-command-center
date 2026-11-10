/** MAIN R83: read-only evidence-gap handoff for all 29 exact FOCUS NCTs.
 * This file deliberately does not produce grades, FDA forecasts or probabilities.
 * The 23 provisional application identities are metadata, not 23 verified filings.
 */
import {FOCUS_R81_SOURCE_READINESS} from "./focus-r81-all-focus-source-readiness";

type Source = NonNullable<typeof FOCUS_R81_SOURCE_READINESS>;
export const R83_SOURCE_SNAPSHOT = "R81_SOURCE_ONLY_2026-11-09";
export const R83_CSV_COLUMNS = [
  "Source snapshot", "Exact NCT", "Ticker", "Provisional application cycle IDs",
  "Retained registry primary table", "Retained registry arm safety",
  "Retained method PDF page leads", "Published pivotal report in five-case R71 subset",
  "Original dated prospective SAP authenticated", "Independent scientific signoff",
  "FDA application forecast", "Next independent evidence work",
  "ClinicalTrials.gov original", "Published source lead"
] as const;

function quoteCsv(value:string):string {
  // Quote everything, neutralize spreadsheet formula prefixes and strip row breaks.
  const safe = /^[=+\-@\t\r]/u.test(value) ? "'" + value : value;
  return '"' + safe.replace(/[\r\n]+/gu, " ").replace(/"/gu, '""') + '"';
}
function availability(value:boolean):string {
  return value ? "PRESENT_IN_RETAINED_SOURCE_NOT_ADJUDICATED" :
    "NOT_PRESENT_IN_RETAINED_SNAPSHOT_NOT_EVIDENCE_OF_FAILURE";
}
function nextEvidenceStep(row:Source["rows"][number]):string {
  const steps:string[] = [];
  if(row.currentRegistryPrimaryTable) {
    steps.push("verify pivotal efficacy/statistics against original protocol and prespecified SAP");
  } else {
    steps.push("locate dated original pivotal efficacy results outside retained registry tables");
  }
  if(row.currentRegistrySafetyArms) {
    steps.push("reconcile arm-level adverse events, denominators and exposure windows");
  } else {
    steps.push("locate original arm-level safety and exposure data");
  }
  if(row.retainedMethodPageLeads) {
    steps.push("authenticate locked protocol/SAP version and amendment chronology");
  } else {
    steps.push("locate original protocol/SAP and dated methods pages");
  }
  if(!row.indexedOriginalPivotalPublication) {
    steps.push("research original publisher/sponsor report beyond five-case R71 intake");
  }
  steps.push("obtain qualified independent scientific and regulatory adjudication");
  return steps.join("; ");
}

/** Each exact NCT appears once; multi-cycle links stay in a single cell. */
export function buildR83EvidenceGapChecklist(
  source:Source|null=FOCUS_R81_SOURCE_READINESS
):string|null {
  if(!source || source.schema!==
      "MAIN_R81_FOCUS_29_TRIAL_23_CYCLE_RESEARCH_SOURCE_READINESS_NOT_GRADED" ||
    source.rows.length!==29 || source.applicationGroups.length!==23 ||
    source.exactTrials!==29 || source.provisionalCycles!==23 ||
    source.R71PublicationLeads!==5 ||
    source.originalSignedProspectiveSAPsVerified!==0 ||
    source.independentScientificSignoffs!==0 ||
    source.validFutureFDAApplicationForecasts!==0 ||
    source.completedScientificSourceReviews!==0 ||
    source.accuracyCalibrated!==false || source.FDAOutcome!=="ABSTAIN" ||
    source.noProductionOrModelTrainingWrites!==true) return null;

  const byNct=new Map(source.rows.map(row=>[row.nct,row]));
  if(byNct.size!==29) return null;
  const seenCycles=new Set<string>();
  for(const group of source.applicationGroups) {
    if(seenCycles.has(group.cycleId) || !/^[a-z0-9]+(?:-[a-z0-9]+)+$/u.test(group.cycleId) ||
      group.ncts.length!==group.trialCount ||
      group.ncts.length<1 || group.clinicalGrade!==null ||
      group.validatedFDAApplicationForecasts!==0 ||
      group.independentlySignedScientificReviews!==0 ||
      group.prospectivelyAuthenticatedSAPs!==0 || group.FDAOutcome!=="ABSTAIN" ||
      group.ncts.some(nct=>!byNct.get(nct)?.cycleIds.includes(group.cycleId))) return null;
    seenCycles.add(group.cycleId);
  }

  const records:string[][]=[];
  const linkedCycles=new Set<string>();
  for(const row of source.rows) {
    if(!/^NCT\d{8}$/u.test(row.nct) ||
      row.cycleIds.length<1 || row.cycleIds.length>2 ||
      row.cycleIds.some(id=>!seenCycles.has(id)) ||
      row.scientificGrade!==null || row.originalProspectiveSAPAuthenticated!==false ||
      row.independentScienceReviewed!==false ||
      row.validatedFDAApplicationPrediction!==false ||
      row.officialFDAOutcome!=="ABSTAIN") return null;
    row.cycleIds.forEach(id=>linkedCycles.add(id));
    records.push([
      R83_SOURCE_SNAPSHOT, row.nct, row.ticker, row.cycleIds.join(" | "),
      availability(row.currentRegistryPrimaryTable),
      availability(row.currentRegistrySafetyArms),
      availability(row.retainedMethodPageLeads),
      row.indexedOriginalPivotalPublication ?
        "INDEXED_SOURCE_LEAD_NOT_ADJUDICATED" :
        "NOT_INDEXED_IN_FIVE_CASE_SUBSET_OTHER_SOURCES_POSSIBLE",
      "NOT_VERIFIED", "NOT_SIGNED", "ABSTAIN_NOT_VALIDATED",
      nextEvidenceStep(row),
      "https://clinicaltrials.gov/study/" + row.nct,
      row.publisherOrPubmedUrl ?? ""
    ]);
  }
  if(linkedCycles.size!==23 ||
    source.rows.filter(row=>row.indexedOriginalPivotalPublication).length!==5 ||
    source.rows.filter(row=>row.currentRegistryPrimaryTable).length!==12 ||
    source.rows.filter(row=>row.currentRegistrySafetyArms).length!==12 ||
    source.rows.filter(row=>row.retainedMethodPageLeads).length!==12) return null;

  records.sort((a,b)=>a[2].localeCompare(b[2])||a[1].localeCompare(b[1]));
  return [R83_CSV_COLUMNS.map(quoteCsv).join(","),
    ...records.map(record=>record.map(quoteCsv).join(","))].join("\r\n")+"\r\n";
}

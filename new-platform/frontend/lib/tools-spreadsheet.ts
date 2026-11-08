import {normalizePoolStage, type PoolTrialRecord} from "./pool-pipeline-funnel";
import {exactProgramTimeline,pacificToday,pipelineDayCounts,type TimelineDates} from "./pipeline-timeline";
import {matchedToolPdufaApplications,type ToolPdufaApplication,type ToolPdufaIndex} from "./tools-pdufa-links";
import {
  SPECIAL_DESIGNATION_CATEGORIES,
  type DesignationIndex,
  type DesignationKey,
  type DesignationEvidence,
} from "./trial-designations";

export type ToolSourceEvidence={
  eventKey:string;source:string;designationDate:string;checkedAt:string;
  verification:DesignationEvidence["verification"];note:string;
};
export type ToolSpreadsheetRow={
  id:string;nctId:string;ticker:string;company:string;drug:string;indication:string;
  stage:string;selectedStage:string;
  timeline:TimelineDates;
  designationMatches:Partial<Record<DesignationKey,ToolSourceEvidence[]>>;
  pdufaApplications:ToolPdufaApplication[];
  studyRole:"NOT_ESTABLISHED";
};

export function toolSpreadsheetRow(
  trial:PoolTrialRecord,
  stages:readonly string[],
  designations:readonly DesignationKey[],
  index:DesignationIndex|null,
  pdufaIndex:ToolPdufaIndex|null=null
):ToolSpreadsheetRow {
  const nctId=trial.id.startsWith("TRIAL|")?trial.id.slice(6):"";
  const stage=normalizePoolStage(trial.stage);
  // A source-verified date must belong to this same NCT, issuer and reported
  // therapy/indication. Registry completion and ticker-only FDA applications
  // cannot establish either timeline event.
  const hasExactIdentity=/^NCT\d{8}$/.test(nctId)&&!!trial.ticker?.trim()&&
    !!trial.drug?.trim()&&!!trial.indication?.trim()&&
    (!trial.nctId||trial.nctId===nctId);
  const timeline=exactProgramTimeline(trial,hasExactIdentity);
  const designationMatches:ToolSpreadsheetRow["designationMatches"]={};
  if(index && /^NCT\d{8}$/.test(nctId)){
    const linked=(index.trialEvents[nctId]||[])
      .map(key=>index.programs[key])
      .filter(program=>!!program && !!trial.ticker && program.ticker===trial.ticker.toUpperCase());
    // Enrich one master trial row with ALL documented designation categories,
    // even before any checkbox is selected. Selection still controls filtering.
    for(const {key} of SPECIAL_DESIGNATION_CATEGORIES){
      const evidence:ToolSourceEvidence[]=[];
      for(const program of linked){
        const value=program.designations[key];
        if(value?.status!=="GRANTED" || value.verification==="UNVERIFIED" || !value.source)continue;
        evidence.push({
          eventKey:program.eventKey,source:value.source,designationDate:value.designationDate,
          checkedAt:value.checkedAt,verification:value.verification,note:value.note
        });
      }
      if(evidence.length)designationMatches[key]=evidence;
    }
  }
  return {
    id:trial.id,nctId,ticker:trial.ticker||"",company:trial.company||"",
    drug:trial.drug||"",indication:trial.indication||"",stage,
    selectedStage:stages.includes(stage)?stage:"",timeline,
    pdufaApplications:matchedToolPdufaApplications(trial,pdufaIndex),
    studyRole:"NOT_ESTABLISHED",
    designationMatches
  };
}

function safeCell(value:string):string {
  const cleaned=value.replace(/[\r\n\t]+/g," ").trim();
  // Prevent Excel/Sheets formula execution from externally sourced free text.
  const safe=/^[=+\-@]/.test(cleaned)?"'"+cleaned:cleaned;
  return '"'+safe.replace(/"/g,'""')+'"';
}
export function renderToolsSpreadsheetCsv(
  trials:readonly PoolTrialRecord[],
  stages:readonly string[],
  designations:readonly DesignationKey[],
  index:DesignationIndex|null,
  sourceAsOf:string,
  pdufaIndex:ToolPdufaIndex|null=null
):string {
  const labels=new Map(SPECIAL_DESIGNATION_CATEGORIES.map(item=>[item.key,item.label]));
  const today=pacificToday();
  const headers=[
    "NCT ID","Ticker","Company","S - Days since verified Phase 3 data release","D - Days to verified PDUFA target","Drug / therapy","Disease / indication","Recorded development stage",
    "Documented FDA special designations (partial)",
    "Saved PDUFA target dates (application-level, not trial-level)",
    "PDUFA candidate source status","PDUFA application event keys","PDUFA record evidence links",
    "Pivotal/supporting study role",
    ...stages.map(stage=>"Selected stage: "+stage),
    ...designations.map(key=>"Selected designation: "+(labels.get(key)||key)),
    ...designations.map(key=>"Evidence link: "+(labels.get(key)||key)),
    ...designations.map(key=>"Designation date: "+(labels.get(key)||key)),
    ...designations.map(key=>"Verification: "+(labels.get(key)||key)),
    "Source snapshot as of"
  ];
  const rows=[headers.map(safeCell).join(",")];
  for(const trial of trials){
    const item=toolSpreadsheetRow(trial,stages,designations,index,pdufaIndex);
    const days=pipelineDayCounts(item.timeline,today);
    const documented=Object.entries(item.designationMatches)
      .filter(([,evidence])=>!!evidence?.length).map(([key])=>labels.get(key as DesignationKey)||key);
    const values=[
      item.nctId,item.ticker,item.company,
      days.daysSincePhase3Release===null?"":String(days.daysSincePhase3Release),
      days.daysToPdufa===null?"":String(days.daysToPdufa),
      item.drug,item.indication,item.stage,
      documented.join(" | "),
      item.pdufaApplications.map(a=>a.targetDate).filter(Boolean).join(" | "),
      item.pdufaApplications.map(a=>a.targetConfirmation+(a.savedOutcome?"; saved outcome: "+a.savedOutcome:"")).join(" | "),
      item.pdufaApplications.map(a=>a.eventKey).join(" | "),
      item.pdufaApplications.map(a=>a.evidenceUrl).filter(Boolean).join(" | "),
      "NOT ESTABLISHED",
      ...stages.map(stage=>item.stage===stage?"MATCH":""),
      ...designations.map(key=>item.designationMatches[key]?.length?"SOURCE-LINKED GRANT":""),
      ...designations.map(key=>[...new Set((item.designationMatches[key]||[]).map(v=>v.source))].join(" | ")),
      ...designations.map(key=>[...new Set((item.designationMatches[key]||[]).map(v=>v.designationDate).filter(Boolean))].join(" | ")),
      ...designations.map(key=>[...new Set((item.designationMatches[key]||[]).map(v=>v.verification))].join(" | ")),
      sourceAsOf
    ];
    // Calendar-day integers are generated, not untrusted user strings, so a
    // negative D can stay numeric in Excel/Google Sheets instead of text.
    rows.push(values.map((value,i)=>i===3||i===4?(value===""?safeCell(""):String(Number(value))):safeCell(value)).join(","));
  }
  return "\uFEFF"+rows.join("\r\n")+"\r\n";
}

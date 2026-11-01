import {normalizePoolStage, type PoolTrialRecord} from "./pool-pipeline-funnel";
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
    selectedStage:stages.includes(stage)?stage:"",
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
  const headers=[
    "NCT ID","Ticker","Company","Drug / therapy","Disease / indication","Recorded development stage",
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
    const documented=Object.entries(item.designationMatches)
      .filter(([,evidence])=>!!evidence?.length).map(([key])=>labels.get(key as DesignationKey)||key);
    const values=[
      item.nctId,item.ticker,item.company,item.drug,item.indication,item.stage,
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
    rows.push(values.map(safeCell).join(","));
  }
  return "\uFEFF"+rows.join("\r\n")+"\r\n";
}

import {normalizePoolStage, type PoolTrialRecord} from "./pool-pipeline-funnel";
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
};

export function toolSpreadsheetRow(
  trial:PoolTrialRecord,
  stages:readonly string[],
  designations:readonly DesignationKey[],
  index:DesignationIndex|null
):ToolSpreadsheetRow {
  const nctId=trial.id.startsWith("TRIAL|")?trial.id.slice(6):"";
  const stage=normalizePoolStage(trial.stage);
  const designationMatches:ToolSpreadsheetRow["designationMatches"]={};
  if(index && /^NCT\d{8}$/.test(nctId)){
    const linked=(index.trialEvents[nctId]||[])
      .map(key=>index.programs[key])
      .filter(program=>!!program && !!trial.ticker && program.ticker===trial.ticker.toUpperCase());
    for(const key of designations){
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
  sourceAsOf:string
):string {
  const labels=new Map(SPECIAL_DESIGNATION_CATEGORIES.map(item=>[item.key,item.label]));
  const headers=[
    "NCT ID","Ticker","Company","Drug / therapy","Disease / indication","Recorded development stage",
    ...stages.map(stage=>"Selected stage: "+stage),
    ...designations.map(key=>"Selected designation: "+(labels.get(key)||key)),
    ...designations.map(key=>"Evidence link: "+(labels.get(key)||key)),
    ...designations.map(key=>"Designation date: "+(labels.get(key)||key)),
    ...designations.map(key=>"Verification: "+(labels.get(key)||key)),
    "Source snapshot as of"
  ];
  const rows=[headers.map(safeCell).join(",")];
  for(const trial of trials){
    const item=toolSpreadsheetRow(trial,stages,designations,index);
    const values=[
      item.nctId,item.ticker,item.company,item.drug,item.indication,item.stage,
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

/** On-demand read-only impact preview using the ORIGINAL restriction engine.
 * Each stage starts independently with the same saved Pipeline trial universe.
 * Missing source evidence is UNKNOWN (retained), never treated as a FAIL.
 * This preview does not approve a GEM admission or alter FS/FA associations.
 */
import type { CatalogEntry } from "./restriction-catalog";
import { calculateCatalogImpact, selectedRestrictionList, catalogDefinition } from "./restriction-catalog";
import { defaultRestrictionSettings, type ImpactRecord, type RestrictionEvidence } from "./restriction-impact";
import type { GoalRestrictionStage } from "./goal-restrictions";

export type GoalImpactStep = {
  id: string;
  title: string;
  before: number;
  excluded: number;
  after: number;
  pending: number;
  unknownAlone: number;
};
export type GoalImpactStage = {
  total: number;
  excluded: number;
  remaining: number;
  passed: number;
  pending: number;
  steps: GoalImpactStep[];
};
export type GoalImpactReport = {
  total: number;
  asOf: string;
  evidenceFetchedAt: string;
  sources: string[];
  stages: Record<GoalRestrictionStage,GoalImpactStage>;
};
const STAGES:GoalRestrictionStage[]=["PIPELINE","GEM_JR","GEM"];
const REQUIRED_SOURCES=["company_registry.csv","phase_pipeline_market_caps.csv","all_phase_trials.csv"];

export function fullGoalRestrictionEvidence(value:unknown): value is RestrictionEvidence {
  if(!value || typeof value!=="object" || Array.isArray(value)) return false;
  const data=value as Partial<RestrictionEvidence>;
  if(typeof data.fetchedAt!=="string" || !Number.isFinite(Date.parse(data.fetchedAt))
      || !data.issuers || typeof data.issuers!=="object" || Array.isArray(data.issuers)
      || !data.trialTypes || typeof data.trialTypes!=="object" || Array.isArray(data.trialTypes)
      || !Array.isArray(data.issues) || data.issues.length
      || !Array.isArray(data.sources) || data.sources.length!==3) return false;
  const names=new Set(data.sources.map(s=>s?.name));
  return names.size===3 && REQUIRED_SOURCES.every(name=>names.has(name)) &&
    data.sources.every(source=>typeof source?.url==="string" &&
      source.url==="https://raw.githubusercontent.com/pdufa/pdufa-command-center/main/data/"+source.name &&
      Number.isSafeInteger(source.rows) && source.rows>0);
}
export function calculateGoalRestrictionImpact(
  rows:ImpactRecord[], entries:CatalogEntry[], evidence:RestrictionEvidence, asOf:string,
):GoalImpactReport {
  if(!fullGoalRestrictionEvidence(evidence)) throw new Error("Published restriction evidence incomplete");
  if(!Number.isFinite(Date.parse(asOf)) || !Array.isArray(rows) || !rows.length)
    throw new Error("Published Pipeline baseline unavailable");
  const ids=new Set<string>();
  for(const row of rows) {
    if(!row || typeof row.id!=="string" || !row.id || typeof row.ticker!=="string")
      throw new Error("Invalid saved Pipeline program identity");
    ids.add(row.id);
  }
  if(!ids.size) throw new Error("No saved Pipeline records");
  const settings=defaultRestrictionSettings();
  // Preserve approved entry-cap semantics: current-market-cap observations do
  // not stand in for missing admission-date market-cap evidence.
  settings.capBasis="entry";
  const stages={} as Record<GoalRestrictionStage,GoalImpactStage>;
  for(const stage of STAGES) {
    const selected=selectedRestrictionList(entries,stage);
    // A separate calculation with *only* the selected stage's own rules:
    // GEM JR and GEM are not pre-filtered by another stage's checklist.
    const calculated=calculateCatalogImpact(rows,selected,settings,evidence,asOf);
    const steps:GoalImpactStep[]=[];
    for(const rule of selected){
      const key=rule.stage===stage ? rule.id : stage+"|"+rule.id;
      const step=calculated.steps.get(key);
      if(!step || step.step===null) throw new Error("Missing selected rule result");
      steps.push({id:rule.id,title:catalogDefinition(rule).title,
        before:step.before,excluded:step.newlyExcluded,after:step.remaining,
        pending:step.pending,unknownAlone:step.aloneUnknown});
    }
    const final=calculated.stages.find(item=>item.stage===stage);
    if(!final) throw new Error("Missing stage impact");
    stages[stage]={total:calculated.total,excluded:final.excluded,
      remaining:final.remaining,passed:final.passed,pending:final.pending,steps};
  }
  return {total:ids.size,asOf,evidenceFetchedAt:evidence.fetchedAt,
    sources:evidence.sources.map(x=>x.name),stages};
}

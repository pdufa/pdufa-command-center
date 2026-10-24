/** Read-only GOAL view of the very same per-stage restriction selections
 * used by Workspace. Does not write to the catalog, alter FS/FA membership,
 * claim qualification, or calculate speculative filter/score impacts.
 */
import type { CatalogEntry } from "./restriction-catalog";
import { selectedRestrictionList, catalogDefinition, catalogStagePriority, marketCapLimitLabel } from "./restriction-catalog";

export type GoalRestrictionStage = "PIPELINE" | "GEM_JR" | "GEM";
export type GoalRestrictionItem = {
  id: string;
  title: string;
  priority: string;
  valueLabel: string | null;
};
export type GoalRestrictionSummaries = Record<GoalRestrictionStage, GoalRestrictionItem[]>;
const STAGES: GoalRestrictionStage[] = ["PIPELINE","GEM_JR","GEM"];

export function goalRestrictionSummaries(entries: CatalogEntry[]): GoalRestrictionSummaries {
  const build = (stage:GoalRestrictionStage):GoalRestrictionItem[] =>
    selectedRestrictionList(entries,stage).map(entry => {
      const definition = catalogDefinition(entry);
      const isNumeric = entry.value?.trim() && Number.isFinite(Number(entry.value));
      const numericRange = definition.numeric && isNumeric
        ? entry.value.trim() + (entry.maximum?.trim() ? " – " + entry.maximum.trim() : "") +
          (definition.unit ? " " + definition.unit : "")
        : null;
      return {
        id: entry.id,
        title: definition.title,
        priority: catalogStagePriority(entry,stage),
        valueLabel: marketCapLimitLabel(entry) || numericRange || null,
      };
    });
  return Object.fromEntries(STAGES.map(stage=>[stage,build(stage)])) as GoalRestrictionSummaries;
}

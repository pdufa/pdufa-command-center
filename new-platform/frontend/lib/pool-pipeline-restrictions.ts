/** Pool -> Pipeline restriction-only view, independent of GEM JR and GEM.
 *
 * This is an additive transition layer: the previous browser configuration,
 * saved GEM JR / GEM presets and historical scan evidence are not mutated.
 * Callers must save the returned values under a NEW versioned key.
 */
import type { CatalogEntry, CatalogDefinition } from "./restriction-catalog";
import { catalogDefinition } from "./restriction-catalog";

export type PoolPipelineEntry = CatalogEntry & {
  stage: "" | "PIPELINE";
  additionalStages: [];
  stagePriorities: { PIPELINE?: string };
};

/** A GEM JR screening result is not a standalone eligibility rule. */
export function poolRuleAllowed(id: string): boolean {
  return id !== "gem_jr_source";
}

export function detachGemAssociations(entries: readonly CatalogEntry[]): PoolPipelineEntry[] {
  return entries.filter(entry => poolRuleAllowed(entry.id)).map(entry => {
    const pipelineMember = entry.stage === "PIPELINE" ||
      (entry.additionalStages || []).includes("PIPELINE");
    const savedPipelinePriority = entry.stagePriorities?.PIPELINE;
    const priority = pipelineMember
      ? (typeof savedPipelinePriority === "string" ? savedPipelinePriority :
        entry.stage === "PIPELINE" ? (entry.priority || "") : "")
      : "";
    const rank = /^[1-9]\\d{0,3}$/.test(priority) ? priority : "";
    return {
      ...entry,
      // There is one active list only. Unassigned rules remain available in POOL.
      stage: rank ? "PIPELINE" : "",
      additionalStages: [],
      priority: rank,
      stagePriorities: rank ? { PIPELINE: rank } : {},
      enabled: !!rank && entry.enabled,
    };
  });
}

/** Clear historical preset descriptors in the active Pool editor. */
export function poolRuleDefinition(entry: CatalogEntry): CatalogDefinition {
  const original = catalogDefinition(entry);
  return {
    ...original,
    associations: [],
    category: entry.stage === "PIPELINE" ? "Pipeline restriction" : "Pool: available restriction",
    help: original.help.replace(/GEM JR\\s*\\/\\s*GEM|GEM JR|GEM|FS\\s*\\/\\s*FA/g, "prior screening"),
  };
}

/** No GEM association is serialized in the active Pool/Pipeline settings. */
export function validatePoolPipeline(entries: readonly CatalogEntry[]): boolean {
  return entries.every(entry =>
    poolRuleAllowed(entry.id) &&
    (entry.stage === "" || entry.stage === "PIPELINE") &&
    (!entry.additionalStages || entry.additionalStages.length === 0) &&
    Object.keys(entry.stagePriorities || {}).every(stage => stage === "PIPELINE"));
}

/** Published screening snapshot is immutable per deployment, but its age is not.
 * Validate at every request, including on long-lived serverless instances.
 */
export const TOOLS_SNAPSHOT_MAX_AGE_MS=36*60*60*1000;
export const TOOLS_SNAPSHOT_FUTURE_SKEW_MS=5*60*1000;

export function isToolsSnapshotFresh(generatedAtMs:number,nowMs:number):boolean{
  return Number.isFinite(generatedAtMs)&&Number.isFinite(nowMs)&&
    generatedAtMs<=nowMs+TOOLS_SNAPSHOT_FUTURE_SKEW_MS&&
    nowMs-generatedAtMs<=TOOLS_SNAPSHOT_MAX_AGE_MS;
}

export function parseToolsSnapshotTimestamp(value:unknown):number{
  return typeof value==="string"?Date.parse(value):NaN;
}

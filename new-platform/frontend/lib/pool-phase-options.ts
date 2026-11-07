/** The documented POOL stage categories. Match POOL_STAGES in pool-pipeline-funnel.ts. */
export const POOL_PHASE_OPTIONS=[
 "Early Phase 1","Phase 1","Phase 1/2","Phase 2","Phase 2/3",
 "Phase 3","Phase 3 Results","NDA/BLA Submission","FDA Acceptance",
 "PDUFA Decision","Post-Decision","Phase 4","Not Applicable","Unknown"
] as const;
export type PoolPhase=typeof POOL_PHASE_OPTIONS[number];
export type PoolPhaseSelection=readonly PoolPhase[]|null; // null = All phases
export function togglePoolPhase(selection:PoolPhaseSelection,phase:PoolPhase):PoolPhaseSelection{
 const current=selection===null?[...POOL_PHASE_OPTIONS]:[...selection];
 const next=current.includes(phase)?current.filter(x=>x!==phase):[...current,phase];
 return next.length===POOL_PHASE_OPTIONS.length?null:
  POOL_PHASE_OPTIONS.filter(x=>next.includes(x));
}

/**
 * GEM / GEM JR research rows are not the persisted stage membership ledger.
 * The live checkbox intersection and the table must use the same candidate pool.
 */
export type GemRowPool<T>={passes:T[];needsReview:T[]};
export function pickGemResearchRows<T>(args:{
 pipeline:T[];savedStage:T[];livePreview?:GemRowPool<T>|null;
 completedScan?:GemRowPool<T>|null;savedOnly?:boolean;
}):T[]{
 if(args.savedOnly)return args.savedStage;
 const screened=args.completedScan??args.livePreview;
 return screened?[...screened.passes,...screened.needsReview]:args.pipeline;
}

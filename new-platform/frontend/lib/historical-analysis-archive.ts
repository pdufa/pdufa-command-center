/** Immutable historical records only. This module never imports a calculator,
 * reinterprets a stored grade, updates a ledger, or feeds an active decision.
 */
import {readFile} from "node:fs/promises";
import {join} from "node:path";
export const HISTORICAL_ARCHIVE_FILES={
 "trial-score-history":"raas-trial-score-history.json",
 "post-data-score-history":"bottomOnlyScoreHistory20261107.json",
 "post-data-research-history":"bottomOnlyResearchHistory20261107.json",
 "pre-data-research-history":"topOnlyResearchHistory20261107.json",
 "metric-assessments":"raas-reviewed-metric-assessments.json"
} as const;
export type HistoricalArchiveSource=keyof typeof HISTORICAL_ARCHIVE_FILES;
export async function readHistoricalArchive(source:HistoricalArchiveSource,nctId?:string){
 if(!(source in HISTORICAL_ARCHIVE_FILES))throw Error("UNKNOWN_ARCHIVE_SOURCE");
 if(nctId&&!/^NCT\d{8}$/.test(nctId))throw Error("INVALID_EXACT_NCT");
 const raw=JSON.parse(await readFile(join(process.cwd(),"data",HISTORICAL_ARCHIVE_FILES[source]),"utf8")) as {records?:unknown[]};
 if(!Array.isArray(raw.records))throw Error("ARCHIVE_SCHEMA_INVALID");
 const records=nctId?raw.records.filter(record=>record!==null&&typeof record==="object"&&"nctId" in record&&record.nctId===nctId):raw.records;
 return {source,file:HISTORICAL_ARCHIVE_FILES[source],readOnly:true,scope:"HISTORICAL_ARCHIVE_ONLY",totalRecords:raw.records.length,matchedRecords:records.length,records};
}


// Permanently retired artifact writer: refuse imports and commands before I/O.
throw new Error("RAAS_PERMANENTLY_RETIRED: this archived writer cannot run or modify historical records.");

/** Append-only phase/rating snapshots. Existing RAAS ledgers are never edited. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'../new-platform/frontend'),ts=require(path.join(root,'node_modules/typescript'));
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}
}).outputText,f);
const {phaseFirstReport}=require(path.join(root,'lib/phase-first-report.ts'));
const file=path.join(root,'data/phaseFirstRatingHistory20261106.json');
const ledger=fs.existsSync(file)?JSON.parse(fs.readFileSync(file,'utf8')):{schemaVersion:1,scope:'PHASE_FIRST_APPEND_ONLY_RATING_HISTORY',records:[]};
const ids=new Set(ledger.records.map(r=>r.eventId));let added=0;
for(const scope of ['alkermes','axsome','sinovac','census']){
 const report=phaseFirstReport(scope);
 for(const t of report.trials){
  const payload={trialId:t.trialId,nctId:t.nctId,ticker:t.ticker,programId:t.programId,drug:t.drug,indication:t.indication,
   phase:t.phase,status:t.status,sourceDate:t.sourceDate,sourceUrl:t.sourceUrl,modelVersion:t.modelVersion,
   overallRating:t.overallRating,ratingKind:t.ratingKind,ratingCoverage:t.ratingCoverage,
   factors:t.factors,evidenceCounts:t.evidenceCounts,raasScore:t.raasScore,fdaPrediction:t.fdaPrediction};
  const evidenceFingerprint=crypto.createHash('sha256').update(JSON.stringify({payload,evidence:t.evidence})).digest('hex');
  // Trial continuity never includes phase, spreadsheet or score in the key.
  const eventId=crypto.createHash('sha256').update(t.trialId+'|'+scope+'|'+t.modelVersion+'|'+evidenceFingerprint).digest('hex');
  if(ids.has(eventId))continue;
  ledger.records.push({eventId,continuityKey:t.trialId,sourceScope:scope,recordedAt:new Date().toISOString(),
   sourceAsOf:report.asOf,evidenceFingerprint,payload});ids.add(eventId);added++;
 }
}
if(added||!fs.existsSync(file))fs.writeFileSync(file,JSON.stringify(ledger,null,2)+'\n');
console.log(JSON.stringify({added,events:ledger.records.length,distinctTrials:new Set(ledger.records.map(r=>r.continuityKey)).size}));

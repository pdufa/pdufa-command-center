/** Reproducible read-only reports; the existing190-column export is unchanged. */
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../new-platform/frontend'),ts=require(path.join(root,'node_modules/typescript'));
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText,f);
const {phaseFirstReport}=require(path.join(root,'lib/phase-first-report.ts'));
const scope=process.argv[2]||'axsome';if(!['axsome','alkermes','census'].includes(scope))throw Error('UNKNOWN_SCOPE');
const report=phaseFirstReport(scope),dir=path.resolve(__dirname,'../reports/phase-first-2026-11-06');fs.mkdirSync(dir,{recursive:true});
const quote=v=>'"'+String(v??'').replaceAll('"','""')+'"';
const csv=(name,rows)=>fs.writeFileSync(path.join(dir,scope+'-'+name+'.csv'),rows.map(r=>r.map(quote).join(',')).join('\r\n')+'\r\n');
const totals={};
for(const t of report.trials)for(const e of t.evidence){const row=totals[e.id]??(totals[e.id]={id:e.id,label:e.label});row[e.status]=(row[e.status]||0)+1;}
const statuses=['AVAILABLE','MISSING','PENDING','NOT YET EXPECTED','NOT APPLICABLE','CONFLICTING'];
csv('evidence-by-requirement',[['Requirement','Label',...statuses],...Object.values(totals).map(r=>[r.id,r.label,...statuses.map(s=>r[s]||0)])]);
csv('trial-coverage',[['Trial','Phase','Status','Overall research rating','Scored components','Eligible components','Efficacy','Clinical benefit','Statistics','Reproducibility','Safety','RAAS','FDA eligibility',...statuses],...report.trials.map(t=>[t.trialId,t.phase.label,t.status,t.overallRating,t.ratingCoverage.scored,t.ratingCoverage.eligible,...t.factors.map(f=>f.score),t.raasScore,t.fdaPrediction.status,...statuses.map(s=>t.evidenceCounts[s])])]);
csv('evidence-register',[['Trial','Requirement','Label','Status','Evidence','URL','Date','Date kind','Confidence','Reviewed at'],...report.trials.flatMap(t=>t.evidence.map(e=>[t.trialId,e.id,e.label,e.status,e.evidence,e.sourceUrl,e.evidenceDate,e.dateKind,e.confidence,e.reviewedAt]))]);
const {trials,surveyHierarchy,...summary}=report;fs.writeFileSync(path.join(dir,scope+'-summary.json'),JSON.stringify({...summary,requirementsPerTrial:36,byRequirement:Object.values(totals)},null,2)+'\n');
console.log(JSON.stringify({scope,trials:report.trialCount,evidenceCounts:report.evidenceCounts,output:dir}));

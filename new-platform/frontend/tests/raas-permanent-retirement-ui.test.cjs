const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),ts=require('typescript');
const root=path.resolve(__dirname,'..');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}).outputText,f);
test('every legacy RAAS API is permanently gone without executing a calculator',()=>{
 const dirs=fs.readdirSync(path.join(root,'app/api')).filter(n=>n.startsWith('raas-'));
 assert.ok(dirs.length>0);
 for(const dir of dirs){
  const file=path.join(root,'app/api',dir,'route.ts'),code=fs.readFileSync(file,'utf8');
  assert.ok(!/^import\s/m.test(code),file);
  const {GET}=require(file),response=GET(new Request('http://localhost/api/'+dir));
  assert.equal(response.status,410,dir);assert.match(code,/RAAS_PERMANENTLY_RETIRED/);
 }
});
test('compatibility score endpoints cannot expose current or recalculated ratings',async()=>{
 for(const name of ['p3-post-data-research','phase3-active-trial-scores']){
  const response=require(path.join(root,'app/api',name,'route.ts')).GET(new Request('http://localhost/api/'+name));
  assert.equal(response.status,410);const body=await response.json();assert.equal(body.status,'RETIRED');assert.ok(!('scores' in body));
 }
});
test('active FOCUS, tools and predictions do not load retired scoring workspaces',()=>{
 for(const relative of ['app/p3-post-data/page.tsx','app/ToolsOpeningTrialGrid.tsx','app/ToolsResultsSpreadsheet.tsx','app/predictions/page.tsx','app/phase-first/PhaseFirstTable.tsx']){
  const code=fs.readFileSync(path.join(root,relative),'utf8');
  assert.doesNotMatch(code,/from\s+["'][^"']*(?:raas-|Raas|bottom-only-completion|bottom-only-exports|BottomOnlyCompletionSheet)/,relative);
  assert.doesNotMatch(code,/<Raas|<BottomClinicalRating|\.raasScore|\.overallRating|\.ratingCoverage/,relative);
 }
});
test('historical archive exports exact-NCT original records only and rejects unknown sources',async()=>{
 const {GET}=require('../app/api/archive/raas/route.ts');
 assert.equal((await GET(new Request('http://localhost/api/archive/raas?nctId=CLDX'))).status,422);
 assert.equal((await GET(new Request('http://localhost/api/archive/raas?source=../../other'))).status,404);
 const response=await GET(new Request('http://localhost/api/archive/raas?source=trial-score-history&nctId=NCT06445023'));
 const result=await response.json();assert.equal(response.status,200);assert.equal(result.readOnly,true);assert.equal(result.scope,'HISTORICAL_ARCHIVE_ONLY');
 const expected=require('../data/raas-trial-score-history.json').records.filter(r=>r.nctId==='NCT06445023');
 assert.deepEqual(result.records,expected);
 const module=require('../app/api/archive/raas/route.ts');assert.equal(module.POST,undefined);assert.equal(module.PUT,undefined);assert.equal(module.DELETE,undefined);
});

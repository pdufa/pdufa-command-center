const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');
const React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
for(const ext of ['.ts','.tsx'])
 require.extensions[ext]=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
 }).outputText,file);
const source=fs.readFileSync(path.join(__dirname,'../app/focus/page.tsx'),'utf8');
const {FocusTwentyHeaders,FocusTwentyCells,FocusOverviewCells}=require('../app/FocusOverallLevelMatrix.tsx');
const {FOCUS_CHART_SNAPSHOT_TRIALS}=require('../lib/focus-chart-snapshot.ts');

test('FOCUS website spreadsheet is above the chart, gate checks, research and indications sections',()=>{
 const table=source.indexOf('id="focus-site-spreadsheet"');
 assert.ok(table>0);
 for(const after of ['<FocusSavedAssessments/>','<IndicationIntelligence mode="focus"','aria-label="Final trial gate coverage"']){
  assert.ok(table<source.indexOf(after),after);
 }
 assert.match(source,/href="#focus-site-spreadsheet"/);
 assert.match(source,/id="focus-site-spreadsheet"/);
});

test('visible FOCUS table leads with Overall and L01–L03 immediately after ticker before long metadata',()=>{
 const spreadsheet=source.indexOf('data-testid="focus-full-table-scroller"');
 assert.ok(spreadsheet>=0);
 const tableHead=source.indexOf('<thead ',spreadsheet);
 assert.ok(tableHead>spreadsheet);
 const head=source.slice(tableHead,source.indexOf('</thead>',tableHead));
 const tic=head.indexOf('>Ticker</th>'),overall=head.indexOf('<FocusOverallHeaders'),first3=head.indexOf('<FocusTwentyHeaders startLevel={1} endLevel={3}/>'),nct=head.indexOf('>NCT / Trial</th>'),later=head.indexOf('<FocusTwentyHeaders className="assessment-level" startLevel={4} endLevel={20}/>');
 assert.ok(tic>=0&&tic<overall&&overall<first3&&first3<nct&&later>nct);
 const tableBody=source.indexOf('<tbody>{sortedTrials.map(',tableHead);
 assert.ok(tableBody>tableHead);
 const rows=source.slice(tableBody,source.indexOf('</tbody>',tableBody));
 const r0=rows.indexOf('<TickerChartButton ticker={t.ticker}/>'),rO=rows.indexOf('<FocusOverviewCells'),r3=rows.indexOf('<FocusTwentyCells nct={t.nct} levels={savedLevels[t.nct]} startLevel={1} endLevel={3}/>'),rN=rows.indexOf('clinicaltrials.gov/study/');
 assert.ok(r0>=0&&r0<rO&&rO<r3&&r3<rN);
 assert.match(rows,/className="assessment-level" startLevel=\{4\} endLevel=\{20\}/);
});

test('L01–L03 survey columns render without the collapsed assessment-level CSS class',()=>{
 const h=renderToStaticMarkup(React.createElement('tr',null,React.createElement(FocusTwentyHeaders,{startLevel:1,endLevel:3})));
 for(const n of ['L01','L02','L03'])assert.ok(h.includes('title="'+n+' —'));
 assert.ok(!h.includes('title="L04 —')&&!h.includes('assessment-level'));
 const tail=renderToStaticMarkup(React.createElement('tr',null,React.createElement(FocusTwentyHeaders,{startLevel:4,endLevel:20,className:'assessment-level'})));
 assert.ok(!tail.includes('title="L01 —')&&tail.includes('title="L20 —')&&tail.includes('assessment-level'));
});

test('visible FOCUS website grid contains all 32 evidence numbers each for L01 L02 L03 and overall',()=>{
 assert.equal(FOCUS_CHART_SNAPSHOT_TRIALS.length,32);
 const markup=renderToStaticMarkup(React.createElement('table',null,React.createElement('tbody',null,
  FOCUS_CHART_SNAPSHOT_TRIALS.map(t=>React.createElement('tr',{key:t.nct},
   React.createElement(FocusOverviewCells,{nct:t.nct,levels:t.levels}),
   React.createElement(FocusTwentyCells,{nct:t.nct,levels:t.levels,startLevel:1,endLevel:3})
  ))
 )));
 for(const n of ['01','02','03'])assert.equal((markup.match(new RegExp('data-testid="provisional-L'+n+'-score"','g'))||[]).length,32);
 assert.equal((markup.match(/data-testid="overall-evidence-readiness-value"/g)||[]).length,32);
 assert.equal((markup.match(/data-testid="overall-evidence-readiness-value">Pending/g)||[]).length,0);
});

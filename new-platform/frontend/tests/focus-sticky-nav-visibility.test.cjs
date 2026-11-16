const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const read=p=>fs.readFileSync(path.join(__dirname,'../app',p),'utf8');
test('FOCUS jump-to-sort and spreadsheet anchors clear the sticky site navigation',()=>{
 const nav=read('GlobalNavigation.tsx'),focus=read('focus/page.tsx');
 assert.match(nav,/position:"sticky",top:0,zIndex:1000/);
 assert.match(focus,/id="focus-site-spreadsheet" style=\{\{fontSize:22,margin:"12px 0 6px",scrollMarginTop:104\}\}/);
 assert.match(focus,/id="focus-sort-feedback" data-testid="focus-sort-feedback" role="status"/);
 assert.match(focus,/scrollMarginTop:104/);
 assert.match(focus,/document\.getElementById\('focus-sort-feedback'\)\?\.scrollIntoView/);
});
test('chart deep link clears nav and both sorting dialogs stack above it',()=>{
 const chart=read('FocusSavedAssessments.tsx'),sorter=read('NumericSortSettings.tsx');
 assert.match(chart,/id="focus-chart-quick-view"/);
 assert.match(chart,/borderRadius:10,scrollMarginTop:104/);
 assert.equal((sorter.match(/zIndex:2000,background:"#0008"/g)||[]).length,2);
 assert.doesNotMatch(sorter,/zIndex:1000,background:"#0008"/);
});

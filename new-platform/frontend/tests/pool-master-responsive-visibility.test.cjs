"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const root=path.join(__dirname,"..");
const component=fs.readFileSync(path.join(root,"app/PoolMasterSpreadsheet.tsx"),"utf8");
const style=fs.readFileSync(path.join(root,"app/PoolMasterSpreadsheet.module.css"),"utf8");
const workspace=fs.readFileSync(path.join(root,"app/FunnelWorkspace.tsx"),"utf8");
test("POOL master uses the existing paginated source, not a restricted stage-only filter",()=>{
 assert.match(workspace,/view=section==="pool"\?"pool"/);
 assert.match(workspace,/<PoolMasterSpreadsheet[\s\S]*?rows=\{page\?\.rows\.filter/);
 assert.match(component,/FOCUS gates not established for this record/);
});
test("32 columns are segmented, all source rows preserved, and separate viewport layouts retained",()=>{
 for(const key of ["clinical","dates","qualifiers","focus"])assert.match(component,new RegExp('key:"'+key+'"'));
 assert.match(component,/pdufa:pool-column-layout:v1:/);
 assert.match(component,/hiddenColumns/);
 assert.match(component,/hiddenSegments/);
 assert.match(component,/expanded/);
 assert.match(component,/Showing 3 identity columns/);
 assert.match(component,/Not on current FOCUS roster — unassessed/);
});
test("mobile uses half-viewport optional columns; desktop fits more and pins identity",()=>{
 assert.match(style,/@media \(max-width:640px\)/);
 assert.match(style,/\.dataColumn\{width:50vw;min-width:50vw;max-width:50vw\}/);
 assert.match(style,/width:clamp\(180px,18vw,260px\)/);
 assert.match(style,/\.ticker\{/);
 assert.match(style,/\.company\{/);
 assert.match(style,/\.nct\{/);
});
test("POOL Master component parses as valid TypeScript JSX",()=>{
 const source=ts.createSourceFile("PoolMasterSpreadsheet.tsx",component,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
 assert.deepEqual(source.parseDiagnostics.map(e=>ts.flattenDiagnosticMessageText(e.messageText,"; ")),[]);
});


test("two main POOL buttons have separate segment-group handlers and pressed colors",()=>{
 assert.match(component,/const toggleClinical=\(\)=>edit\(l=>\(\{\.\.\.l,\.\.\.toggleColumnGroup\(l,GROUP_CLINICAL,l\.columnOrder\)/);
 assert.match(component,/const toggleQualification=\(\)=>edit\(l=>\(\{\.\.\.l,\.\.\.toggleColumnGroup\(l,GROUP_QUALIFICATION,l\.columnOrder\)/);
 assert.match(component,/aria-pressed=\{clinicalVisible\} onClick=\{toggleClinical\}/);
 assert.match(component,/aria-pressed=\{qualificationVisible\} onClick=\{toggleQualification\}/);
 assert.match(component,/clinicalVisible\?"Hide All":"Show All"/);
 assert.match(component,/qualificationVisible\?"Hide All":"Show All"/);
 assert.match(style,/\.actions button\[data-visibility="visible"\]/);
 assert.match(style,/\.actions button\[data-visibility="hidden"\]/);
 assert.match(component,/onClick=\{resetView\}/);
});
test("column-group buttons do not alter the opposite group's visibility or hidden-column preferences",()=>{
 const {toggleColumnGroup,isGroupVisible}=require("../lib/pool-column-visibility.ts");
 const cols={clinical:["phase","status"],dates:["start"],
  qualifiers:["cap"],focus:["membership"]};
 const a=["clinical","dates"],b=["qualifiers","focus"];
 let state={expanded:["qualifiers","focus"],hiddenSegments:[],hiddenColumns:["status"]};
 assert.equal(isGroupVisible(state,a,cols),false);
 assert.equal(isGroupVisible(state,b,cols),true);
 state=toggleColumnGroup(state,a,cols);
 assert.equal(isGroupVisible(state,a,cols),true);
 assert.equal(isGroupVisible(state,b,cols),true);
 assert.equal(state.hiddenColumns.includes("status"),false);
 state=toggleColumnGroup(state,b,cols);
 assert.equal(isGroupVisible(state,a,cols),true);
 assert.equal(isGroupVisible(state,b,cols),false);
 state=toggleColumnGroup(state,a,cols);
 assert.equal(isGroupVisible(state,a,cols),false);
 assert.equal(isGroupVisible(state,b,cols),false);
 state=toggleColumnGroup(state,b,cols);
 assert.equal(isGroupVisible(state,b,cols),true);
 assert.equal(isGroupVisible(state,a,cols),false);
});

test("POOL column reordering supports drag/drop and segment transfers",()=>{
 assert.ok(component.includes('const resetColumnOrder=()=>{'));
 assert.ok(component.includes('Reset Column Order'));
 assert.ok(component.includes('onDragStart={event=>dragStart(event,"segment",s.key)}'));
 assert.ok(component.includes('onDragStart={event=>dragStart(event,"column",key)}'));
 assert.ok(component.includes('onDrop={event=>dropOnColumn(event,s.key,key)}'));
 assert.ok(component.includes('onDrop={event=>dropOnSegment(event,s.key)}'));
 assert.ok(component.includes('aria-label={"Move "+c.label+" to another segment"}'));
 assert.ok(component.includes('layout.segmentOrder'));
 assert.ok(component.includes('layout.columnOrder'));
 assert.ok(component.includes('window.localStorage.setItem(storageKey(device)'));
 assert.ok(style.includes('.dragHandle{'));
 assert.ok(style.includes('.movePair button{'));
});
test("Column Order button toggles an editor, and reset is an independent action within it",()=>{
 assert.ok(component.includes('<span>Clinical &amp; Dates</span>'));
 assert.ok(component.includes('<span>Qualification &amp; FOCUS</span>'));
 assert.ok(component.includes('<span>Column Order</span>'));
 assert.ok(component.includes('<small>{orderEditorOpen?"Close":"Edit"}</small>'));
 assert.ok(component.includes('const [orderEditorOpen,setOrderEditorOpen]=useState(false)'));
 assert.ok(component.includes('setOrderEditorOpen(open=>!open)'));
 assert.ok(component.includes('onClick={toggleOrderEditor}'));
 assert.ok(component.includes('aria-expanded={orderEditorOpen}'));
 assert.ok(component.includes('aria-controls="pool-column-editor"'));
 assert.ok(component.includes('orderEditorOpen&&<div className={css.orderEditor}'));
 assert.ok(component.includes('onClick={resetColumnOrder}'));
 assert.ok(component.includes('(orderEditorOpen||(expanded&&!hidden))'));
 assert.ok(component.includes('draggable={orderEditorOpen}'));
 assert.ok(component.includes('Column and segment order restored'));
 assert.ok(style.includes('.actions .resetOrder[data-editor-open="false"]'));
 assert.ok(style.includes('.actions .resetOrder[data-editor-open="true"]'));
 assert.ok(style.includes('background:#6c42a5!important'));
 assert.ok(style.includes('.actions button[data-visibility="visible"]'));
 assert.ok(style.includes('.actions button[data-visibility="hidden"]'));
});
test("Three toolbar buttons remain equally wide on all screens",()=>{
 assert.ok(style.includes('.actions{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));width:100%'));
 assert.ok(style.includes('.actions{grid-template-columns:repeat(3,minmax(0,1fr));gap:5px}'));
 assert.ok(style.includes('.actions .groupButton,.actions .resetOrder{'));
 assert.ok(!style.includes('.actions .resetOrder{grid-column:1/-1}'));
});

test("Phase checkboxes and Reset, sort buttons and circled info buttons are wired into POOL",()=>{
 assert.ok(component.includes('POOL_PHASE_OPTIONS.map(phase=>'));
 assert.ok(component.includes('All Phases (show everything)'));
 assert.ok(component.includes('Reset Phases'));
 assert.ok(component.includes('togglePoolPhase(selectedPhases,phase'));
 assert.ok(component.includes('onPhasesChange'));
 assert.ok(component.includes('onClick={()=>updateSort(key)}'));
 assert.ok(component.includes('aria-sort={sortOrder(c.key)}'));
 assert.ok(component.includes('className={css.infoButton} onClick={()=>showInfo(key)}'));
 assert.ok(component.includes('ⓘ'));
 assert.ok(component.includes('all matching POOL trials'));
 assert.ok(style.includes('.phaseChoices{'));
 assert.ok(style.includes('.infoPanel{'));
 assert.ok(style.includes('.sortButton,.infoButton{'));
});

test("latest download buttons highlight independently and Phase leads the matching column sections without inventing classification",()=>{
 const phase=component.indexOf('data-segment="phase-filter"');
 const remainingSections=component.indexOf('{orderedSegments.map(',phase);
 const choices=component.indexOf('<div className={css.latestDownloadToolbar}');
 const view=component.indexOf('<p className={css.viewport}');
 assert.ok(choices>=0&&view>choices);
 assert.ok(phase>=0&&remainingSections>phase,"The approved Phase group remains before the four column sections");
 assert.ok(component.includes('<span>Newly Registered</span>'));
 assert.ok(component.includes('<span>Newly Discovered</span>'));
 assert.ok(component.includes('aria-pressed={latestDownloadChoice==="registered"}'));
 assert.ok(component.includes('aria-pressed={latestDownloadChoice==="discovered"}'));
 assert.ok(component.includes('setLatestDownloadChoice(current=>current==="registered"?null:"registered")'));
 assert.ok(component.includes('setLatestDownloadChoice(current=>current==="discovered"?null:"discovered")'));
 assert.ok(component.includes('trial rows are not classified or hidden'));
 assert.ok(style.includes('.registeredButton[aria-pressed="true"]'));
 assert.ok(style.includes('.discoveredButton[aria-pressed="true"]'));
});

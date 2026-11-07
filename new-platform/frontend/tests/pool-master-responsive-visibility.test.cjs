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

test("POOL Master offers drag/drop, arrow reorder, cross-segment moves and top reset order",()=>{
 assert.match(component,/const resetColumnOrder=\(\)=>edit/);
 assert.match(component,/Reset Column Order/);
 assert.match(component,/onDragStart=\{event=>dragStart\(event,"segment",s.key\)\}/);
 assert.match(component,/onDragStart=\{event=>dragStart\(event,"column",key\)\}/);
 assert.match(component,/onDrop=\{event=>dropOnColumn\(event,s.key,key\)\}/);
 assert.match(component,/onDrop=\{event=>dropOnSegment\(event,s.key\)\}/);
 assert.match(component,/aria-label=\{"Move "\+c.label\+" to another segment"\}/);
 assert.match(component,/layout.segmentOrder/);
 assert.match(component,/layout.columnOrder/);
 assert.match(component,/window.localStorage.setItem\(storageKey\(device\)/);
 assert.match(style,/\.dragHandle\{/);
 assert.match(style,/\.movePair button\{/);
});

test("top action labels and independent Column Order editor toggle",()=>{
 assert.match(component,/<span>Clinical &amp; Dates<\\/span>/);
 assert.match(component,/<span>Qualification &amp; FOCUS<\\/span>/);
 assert.match(component,/<span>Column Order<\\/span>/);
 assert.match(component,/<small>\\{orderEditorOpen\\?"Close":"Edit"\\}<\\/small>/);
 assert.match(component,/onClick=\\{toggleOrderEditor\\}/);
 assert.match(component,/aria-expanded=\\{orderEditorOpen\\}/);
 assert.match(component,/aria-controls="pool-column-editor"/);
 assert.match(component,/orderEditorOpen&&<div className=\\{css.orderEditor\\}/);
 assert.match(component,/onClick=\\{resetColumnOrder\\}/);
 assert.match(component,/Reset Column Order/);
 assert.match(style,/background:#6c42a5!important/);
 assert.match(style,/\\.actions \\.resetOrder\\[data-editor-open="false"\\]/);
 assert.match(style,/\\.actions \\.resetOrder\\[data-editor-open="true"\\]/);
 assert.match(style,/\\.actions button\\[data-visibility="visible"\\]/);
 assert.match(style,/\\.actions button\\[data-visibility="hidden"\\]/);
});
test("all three POOL toolbar buttons occupy one 100% row at equal 33.3% widths on every viewport",()=>{
 assert.match(style,/\.actions\{display:grid;grid-template-columns:repeat\(3,minmax\(0,1fr\)\);width:100%/);
 assert.match(style,/@media\(max-width:640px\)\{\s*\.actions\{grid-template-columns:repeat\(3,minmax\(0,1fr\)\)/);
 assert.match(style,/\.actions \.groupButton,\.actions \.resetOrder\{[\s\S]*?min-width:0;width:100%/);
 assert.doesNotMatch(style,/\.actions \.resetOrder\{grid-column:1\/-1\}/);
});

test("Column Order click reveals actual editable controls and never resets column order directly",()=>{
 assert.match(component,/const toggleOrderEditor=\\(\\)=>\\{/);
 assert.match(component,/setOrderEditorOpen\\(open=>!open\\)/);
 assert.match(component,/\\(orderEditorOpen\\|\\|\\(expanded&&!hidden\\)\\)/);
 assert.match(component,/\\{orderEditorOpen&&<span className=\\{css.dragHandle\\}/);
 assert.match(component,/\\{orderEditorOpen&&<>[\\s\\S]*?<select className=\\{css.moveTo\\}/);
 assert.match(component,/onClick=\\{resetColumnOrder\\}/);
 assert.match(component,/Column and segment order restored/);
 assert.match(component,/draggable=\\{orderEditorOpen\\}/);
});

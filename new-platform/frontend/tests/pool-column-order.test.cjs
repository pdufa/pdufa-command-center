"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const {
 normalizePoolColumnOrder,reorderPoolSegment,stepPoolSegment,
 movePoolColumn,stepPoolColumn
}=require("../lib/pool-column-order.ts");
const defaults={clinical:["phase","status","drug"],dates:["start","posted"],qualifiers:["cap","path"],focus:["membership"]};
const segs=["clinical","dates","qualifiers","focus"];
test("migrates old layout preserving default 29-column order and segment membership",()=>{
 const l=normalizePoolColumnOrder(null,defaults,segs);
 assert.deepEqual(l.segmentOrder,segs);
 assert.deepEqual(l.columnOrder,defaults);
 assert.deepEqual(normalizePoolColumnOrder({},defaults,segs),l);
});
test("reorders segments, including arrows and drag/drop placement",()=>{
 let l=normalizePoolColumnOrder(null,defaults,segs);
 l=reorderPoolSegment(l,"focus","clinical");
 assert.deepEqual(l.segmentOrder,["focus","clinical","dates","qualifiers"]);
 l=stepPoolSegment(l,"focus",1);
 assert.deepEqual(l.segmentOrder,["clinical","focus","dates","qualifiers"]);
 assert.deepEqual(stepPoolSegment(l,"clinical",-1),l);
});
test("reorders columns in a segment, then transfers a column into another segment",()=>{
 let l=normalizePoolColumnOrder(null,defaults,segs);
 l=stepPoolColumn(l,"drug",-1);
 assert.deepEqual(l.columnOrder.clinical,["phase","drug","status"]);
 l=movePoolColumn(l,"cap","clinical","drug");
 assert.deepEqual(l.columnOrder.clinical,["phase","cap","drug","status"]);
 assert.deepEqual(l.columnOrder.qualifiers,["path"]);
 assert.equal(Object.values(l.columnOrder).flat().filter(x=>x==="cap").length,1);
 l=movePoolColumn(l,"cap","focus");
 assert.deepEqual(l.columnOrder.focus,["membership","cap"]);
});
test("saved custom layouts normalize independently and self-heal duplicate and unknown keys",()=>{
 const custom={segmentOrder:["focus","dates","focus","deleted"],
 columnOrder:{focus:["membership","cap","membership","BAD"],clinical:["status"],dates:["posted"],qualifiers:["path"]}};
 const restored=normalizePoolColumnOrder(custom,defaults,segs);
 assert.deepEqual(restored.segmentOrder,["focus","dates","clinical","qualifiers"]);
 assert.deepEqual(restored.columnOrder.focus,["membership","cap"]);
 assert.deepEqual(restored.columnOrder.clinical,["status","phase","drug"]);
 assert.equal(new Set(Object.values(restored.columnOrder).flat()).size,8);
 const phone=normalizePoolColumnOrder(custom,defaults,segs);
 const pc=normalizePoolColumnOrder(null,defaults,segs);
 assert.notDeepEqual(phone.segmentOrder,pc.segmentOrder);
 assert.deepEqual(pc.columnOrder,defaults);
});
test("resetting order does not require touching independent visibility settings",()=>{
 const layout={expanded:["clinical"],hiddenSegments:["dates"],hiddenColumns:["phase"],
  ...normalizePoolColumnOrder(null,defaults,segs)};
 const changed={...layout,...movePoolColumn(layout,"cap","clinical")};
 const restored={...changed,...normalizePoolColumnOrder(null,defaults,segs)};
 assert.deepEqual(restored.segmentOrder,segs);
 assert.deepEqual(restored.columnOrder,defaults);
 assert.deepEqual(restored.expanded,["clinical"]);
 assert.deepEqual(restored.hiddenSegments,["dates"]);
 assert.deepEqual(restored.hiddenColumns,["phase"]);
});

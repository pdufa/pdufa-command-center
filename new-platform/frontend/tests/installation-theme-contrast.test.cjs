const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.join(__dirname,"../app");
const src=fs.readFileSync(path.join(root,"installation-audit/InstallationLiveNavigator.tsx"),"utf8");
const css=fs.readFileSync(path.join(root,"installation-audit/InstallationLiveNavigator.module.css"),"utf8");
const predictions=fs.readFileSync(path.join(root,"predictions/FocusPredictionNavigator.module.css"),"utf8");

const rgb=(hex)=>hex.match(/[0-9a-f]{2}/gi).map(x=>parseInt(x,16)/255)
  .map(x=>x<=0.04045?x/12.92:((x+0.055)/1.055)**2.4);
const luminance=(hex)=>rgb(hex).reduce((sum,x,i)=>sum+x*[0.2126,0.7152,0.0722][i],0);
const contrast=(a,b)=>{const x=luminance(a),y=luminance(b);return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05)};

test("INSTALLATION adopts the same dark navy and teal palette as PREDICTIONS",()=>{
 for(const color of ["#071824","#0b3543","#0a2c3b","#39717b","#e7f9fc","#45ebba"]){
  assert.ok(predictions.includes(color),"PREDICTIONS missing baseline "+color);
  assert.ok((src+css).includes(color),"INSTALLATION missing PREDICTIONS color "+color);
 }
 assert.match(src,/InstallationLiveNavigator\.module\.css/);
 assert.match(src,/background:"radial-gradient\(/);
});

test("task labels, status cards and scientific questions cannot inherit white text on white surfaces",()=>{
 assert.match(src,/background:task\.id===active\?\.taskId\?"#145751":"#0b3040"/);
 assert.match(src,/background:q\.id===chosenQuestion\?"#145751":"#0a2c3b",color:"#e7f9fc"/);
 assert.match(src,/textAlign:"left",width:"100%",background:"transparent",color:"#e7f9fc"/);
 assert.doesNotMatch(src,/background:"#fff"/);
 assert.ok(contrast("e7f9fc","0a2c3b")>=7);
 assert.ok(contrast("e7f9fc","0b3040")>=7);
 assert.ok(contrast("c1dfe2","0a2c3b")>=7);
 assert.ok(contrast("6af8cf","0b3040")>=7);
 assert.match(css,/\.navigator button:focus-visible/);
 assert.match(css,/\.navigator button\[aria-pressed="true"\]/);
});

test("accessibility fix retains evidence-gated cursor and real audit source",()=>{
 assert.match(src,/No verified active installation task is currently reported/);
 assert.match(src,/taskList\.some\(t=>t\.id===c\.taskId\)/);
 assert.match(src,/!c\.taskId\|\|!c\.observedAt/);
 assert.match(src,/live-task-evidence/);
});

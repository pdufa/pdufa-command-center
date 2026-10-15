// Verify the deployed SCANS screen includes GEM source sections beyond the header.
const {chromium}=require("playwright-core");
const fs=require("fs");
const path=require("path");
const output=path.join(process.cwd(),"scans-acceptance-artifacts");
fs.mkdirSync(output,{recursive:true});
const report={checked_at:new Date().toISOString(),checks:{},failures:[],notes:[]};
const URL="https://pdufa-command-center-hvtzovdjssqmzhrlzbbhwu.streamlit.app/";
const required=[
  "GEMS — GITHUB SCAN LOGS",
  "GEM — MASTER STOCK LIST",
  "GEM — UNIFIED MASTER LIST",
  "GEM ELIGIBILITY — WHY STOCKS ARE ON HOLD",
  "BROAD PHASE 3 DISCOVERY — BEFORE FINANCING #2",
  "GEM SOURCE & MODEL READINESS",
  "OPTIONAL STAGE-SPECIFIC RESEARCH CHECKS — AUDIT ONLY",
  "NIGHTLY SCAN REPORT",
];
const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function appFrame(page){
  for(const frame of page.frames()){
    try {
      const text=await frame.locator("body").innerText({timeout:3000});
      if(text.includes("BIO PDUFA COMMAND CENTER"))return {frame,text};
    }catch(_){}
  }
  return null;
}
async function run(){
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||"/usr/bin/google-chrome",headless:true,args:["--no-sandbox","--disable-dev-shm-usage"]});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:920}});
  const r=await page.goto(URL,{waitUntil:"domcontentloaded",timeout:60000});
  report.http=r?.status();
  if(report.http!==200)throw Error("Dashboard HTTP "+report.http);
  let frame;
  for(let n=0;n<100;n++){
    frame=await appFrame(page);
    if(frame&&await frame.frame.getByRole("tab",{name:"SCANS",exact:true}).count())break;
    if(n===55)await page.reload({waitUntil:"domcontentloaded",timeout:60000});
    await pause(1100);
  }
  if(!frame)throw Error("Deployed PDUFA app did not load");
  await frame.frame.getByRole("tab",{name:"SCANS",exact:true}).click({timeout:20000});
  let text="",selected=false;
  for(let n=0;n<125;n++){
    const obs=await appFrame(page);
    if(obs){
      text=obs.text;
      selected=await obs.frame.getByRole("tab",{name:"SCANS",exact:true}).getAttribute("aria-selected")==="true";
    }
    const missing=required.filter(s=>!text.includes(s));
    if(selected&&!missing.length)break;
    await pause(950);
  }
  report.checks.scansTabSelected=selected;
  report.checks.noStreamlitException=!/This app has encountered an error|Traceback \(most recent call last\)/i.test(text);
  report.checks.noSourceLoadFailure=!text.includes("GEM scan source load failed");
  for(const label of required)report.checks[label]=text.includes(label);
  report.notes.push("Browser rendering checks do not certify source freshness, financing, or trade entry.");
  report.notes.push(text.includes("SEC FINANCING RECHECK PARTIAL/STALE")?"SEC source explicitly stale/partial":"SEC freshness must be independently checked");
  report.failures=Object.keys(report.checks).filter(k=>!report.checks[k]);
  await page.screenshot({path:path.join(output,"scans-desktop.png"),fullPage:false});
  fs.writeFileSync(path.join(output,"visible-scans-excerpt.txt"),text.slice(0,15000));
 }finally{await browser.close();}
}
run().catch(e=>report.failures.push(String(e.stack||e).slice(0,1200)))
.finally(()=>{
 fs.writeFileSync(path.join(output,"scans-section-check.json"),JSON.stringify(report,null,2));
 console.log(JSON.stringify(report,null,2));
 process.exitCode=report.failures.length?1:0;
});

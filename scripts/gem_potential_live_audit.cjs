// Acceptance for the sole GEM JR/GEM reference dashboards. No legacy workbench.
const {chromium} = require("playwright-core");
const fs = require("fs");
const path = require("path");
const url = "https://pdufa-command-center-hvtzovdjssqmzhrlzbbhwu.streamlit.app/";
const output = path.join(process.cwd(), "gem-potential-live-artifacts");
fs.mkdirSync(output, {recursive:true});
const result = {timestamp:new Date().toISOString(),url,checks:{},errors:[],evidence:{}};
let browser;
const delay = ms => new Promise(resolve=>setTimeout(resolve,ms));
async function appFrame(page) {
  for(const frame of page.frames()) {
    try {if((await frame.locator("body").innerText({timeout:2500})).includes("BIO PDUFA COMMAND CENTER"))return frame;}catch{}
  }
  return null;
}
async function ready(page,stage) {
  const until=Date.now()+125000;
  while(Date.now()<until) {
    const host=await appFrame(page);
    if(host) {
      const text=await host.locator("body").innerText({timeout:5000});
      if(/This app has encountered an error|Traceback \(most recent call last\)/i.test(text))throw Error("Streamlit exception: "+stage);
      const frame=page.frames().find(f=>f.url().includes("gem_reference_dashboard"));
      if(frame && await frame.getByRole("heading",{name:stage+" Candidates",exact:true}).count())return frame;
    }
    await delay(1000);
  }
  throw Error(stage+" new reference dashboard did not load");
}
async function audit() {
  browser=await chromium.launch({executablePath:process.env.CHROME_PATH||"/usr/bin/google-chrome",headless:true,args:["--no-sandbox","--disable-dev-shm-usage"]});
  const page=await browser.newPage({viewport:{width:1672,height:1000}});
  const errors=[];page.on("pageerror",e=>errors.push(String(e.message||e).slice(0,300)));
  result.http=(await page.goto(url,{waitUntil:"domcontentloaded",timeout:60000}))?.status();
  let host;
  for(let i=0;i<100;i++){host=await appFrame(page);if(host&&await host.getByRole("tab",{name:"GEM JR",exact:true}).count())break;await delay(1000);}
  if(!host)throw Error("Streamlit app did not load");
  for(const stage of ["GEM JR","GEM"]) {
    await host.getByRole("tab",{name:stage,exact:true}).click();
    let dashboard=await ready(page,stage);
    for(const label of ["Entry Checklist ("+stage+")","Exit Checklist ("+stage+")","Scan Diagnostics"]) {
      if(!await dashboard.getByRole("heading",{name:label,exact:true}).count())throw Error(stage+" missing "+label);
    }
    const table=dashboard.locator(".candidate-table");
    const rows=await table.locator("tbody tr").count();
    if(rows) {
      const watches=table.getByRole("button",{name:/^Watch /});
      const trades=table.getByRole("button",{name:/^Trade workspace for /});
      if(await watches.count()!==rows||await trades.count()!==rows)throw Error("Independent W/T controls missing");
      await table.locator('button[data-action="select"]').first().click();
      const search=dashboard.getByRole("searchbox",{name:"Search candidates",exact:true});
      await search.fill("ZZZZ_NO_MATCH");
      if(!await dashboard.getByText("No matching candidates",{exact:true}).count())throw Error("Search does not filter candidates");
      await search.fill("");
      if(await dashboard.locator(".candidate-table tbody tr").count()!==rows)throw Error("Search reset failed");
      await dashboard.getByRole("button",{name:"1M",exact:true}).click();
      if(!await dashboard.getByRole("heading",{name:/1M Trading Chart/}).count())throw Error("Chart range selection failed");
    }
    if(await host.getByText("DETAILED SOURCE WORKBENCH / VERIFIED MASTER",{exact:true}).count())throw Error("Retired GEM layout is still present");
    result.checks[stage+" reference layout and controls"]=true;
    result.evidence[stage]={displayed_candidates:rows};
    await page.screenshot({path:path.join(output,stage.toLowerCase().replace(/ /g,"-")+"-reference-desktop.png"),fullPage:false});
    await page.setViewportSize({width:390,height:844});
    await delay(500);
    const overflows=await dashboard.locator("body").evaluate(el=>el.scrollWidth>el.clientWidth+2);
    if(overflows)throw Error(stage+" mobile page overflows its viewport");
    await page.screenshot({path:path.join(output,stage.toLowerCase().replace(/ /g,"-")+"-reference-mobile.png"),fullPage:false});
    result.checks[stage+" responsive"]=true;
    await page.setViewportSize({width:1672,height:1000});
    host=await appFrame(page);
  }
  result.evidence.pageErrors=errors;
  if(errors.length)throw Error("Browser JavaScript errors: "+errors.join("; "));
}
(async()=>{try{await audit();}catch(error){result.errors.push(String(error.stack||error));process.exitCode=1;}finally{if(browser)await browser.close();fs.writeFileSync(path.join(output,"gem-potential-browser-result.json"),JSON.stringify(result,null,2));console.log(JSON.stringify({checks:result.checks,errors:result.errors,http:result.http},null,2));}})();

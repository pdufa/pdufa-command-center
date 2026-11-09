/** Single-trial adapter for the ordinary public CT.gov history user interface.
 * Saves only the public original study/index responses initiated by that page.
 * No credential, custom user-agent, challenge handling, or denied-API retry.
 * Original version validation/comparison remains in acacia_ctg_historical_versions.py.
 */
const {chromium} = require('playwright');
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const NCT = 'NCT06081894';
const VERSIONS = [[26,25],[27,26],[29,28],[30,29]];
const out = path.resolve(process.argv[2] || 'acacia-public-browser-history');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
(async () => {
  fs.mkdirSync(out,{recursive:true});
  const receipt = {schema:'MAIN_CTG_PUBLIC_UI_CAPTURE_V1',nct:NCT,
    retrievedAt:new Date().toISOString(),accessMethod:'STANDARD_PUBLIC_HISTORY_UI',
    credentialsUsed:false,customUserAgent:false,accessRestrictionBypass:false,
    clinicalSignoff:false,gradedMethods:0,fdaPrediction:'ABSTAIN',versions:[],index:null,indexAttempts:[]};
  const browser = await chromium.launch({executablePath:process.env.CHROMIUM_EXECUTABLE || '/usr/bin/chromium',headless:true,
    args:['--no-sandbox'],...(process.env.HTTPS_PROXY ? {proxy:{server:process.env.HTTPS_PROXY}} : {})});
  try {
    for (const [version,index] of VERSIONS) {
      const page = await browser.newPage();
      const pageUrl = `https://clinicaltrials.gov/study/${NCT}?a=${version}&tab=history`;
      const record = {version,apiIndex:index,pageUrl,startedAt:new Date().toISOString(),status:'NOT_RETRIEVED'};
      const jobs = [];
      page.on('response', response => {
        const url = new URL(response.url());
        if (url.origin !== 'https://clinicaltrials.gov') return;
        const isIndex = url.pathname === `/api/int/studies/${NCT}` && url.search === '?history=true';
        const isVersion = url.pathname === `/api/int/studies/${NCT}/history/${index}` && !url.search;
        if (!isIndex && !isVersion) return;
        jobs.push((async () => {
          const entry = {sourceUrl:url.href,httpStatus:response.status(),retrievedAt:new Date().toISOString()};
          if (response.status() !== 200) {
            entry.status = 'PUBLIC_UI_SOURCE_UNAVAILABLE';
          } else if (!response.headers()['content-type']?.includes('json')) {
            entry.status = 'NON_JSON_RESPONSE';
          } else {
            const bytes = await response.body();
            if (bytes.length > 2_500_000) throw Error('SOURCE_TOO_LARGE');
            JSON.parse(bytes.toString('utf8'));
            entry.artifact = isIndex ? 'original_history_index.json' : `v${version}_original_registry.json`;
            entry.sha256 = sha(bytes); entry.bytes = bytes.length; entry.status = 'ORIGINAL_BYTES_CAPTURED_NOT_YET_VALIDATED';
            if (isVersion || receipt.index?.httpStatus !== 200) fs.writeFileSync(path.join(out,entry.artifact),bytes);
          }
          if (isIndex) {
            receipt.indexAttempts.push(entry);
            if (receipt.index === null || (receipt.index.httpStatus !== 200 && entry.httpStatus === 200)) receipt.index = entry;
          }
          if (isVersion) Object.assign(record,entry);
        })());
      });
      try {
        const response = await page.goto(pageUrl,{waitUntil:'domcontentloaded',timeout:30000});
        record.pageHttpStatus = response.status();
        await page.waitForResponse(r => new URL(r.url()).pathname === `/api/int/studies/${NCT}/history/${index}`,{timeout:15000})
          .catch(() => {});
        await page.waitForLoadState('networkidle',{timeout:7000}).catch(() => {});
        await Promise.all(jobs);
        // Save the visibly rendered public record for human source review.
        const text = await page.locator('body').innerText();
        const artifact = `v${version}_public_page.txt`;
        fs.writeFileSync(path.join(out,artifact),text);
        record.renderedPage = {artifact,sha256:sha(Buffer.from(text)),bytes:Buffer.byteLength(text)};
        await page.screenshot({path:path.join(out,`v${version}_public_page.png`),fullPage:false});
      } catch (error) {record.error = String(error.message).slice(0,200);}
      receipt.versions.push(record); await page.close();
    }
  } finally {
    await browser.close();
    fs.writeFileSync(path.join(out,'public_browser_receipt.json'),JSON.stringify(receipt,null,2)+'\n');
  }
  console.log(JSON.stringify({nct:NCT,versions:receipt.versions.map(v=>({version:v.version,status:v.status,httpStatus:v.httpStatus})),officialGrades:0}));
})().catch(error=>{console.error(error.message);process.exitCode=1});

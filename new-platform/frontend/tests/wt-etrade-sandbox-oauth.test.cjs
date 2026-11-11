"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
require.extensions[".ts"]=(mod,filename)=>{
  const compiled=ts.transpileModule(fs.readFileSync(filename,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}
  }).outputText;
  mod._compile(compiled,filename);
};

test("E*TRADE sandbox requires all server keys and a 32-byte cookie-encryption key",()=>{
  const env={...process.env};
  try{
    delete process.env.ETRADE_SANDBOX_CONSUMER_KEY;
    delete process.env.ETRADE_SANDBOX_CONSUMER_SECRET;
    delete process.env.ETRADE_SANDBOX_COOKIE_KEY;
    const c=require("../lib/etrade-sandbox-oauth.ts");
    assert.equal(c.sandboxConfigured(),false);
    process.env.ETRADE_SANDBOX_CONSUMER_KEY="sandbox-test-key";
    process.env.ETRADE_SANDBOX_CONSUMER_SECRET="sandbox-test-secret";
    assert.equal(c.sandboxConfigured(),false);
    process.env.ETRADE_SANDBOX_COOKIE_KEY="abcd";
    assert.equal(c.sandboxConfigured(),false);
    process.env.ETRADE_SANDBOX_COOKIE_KEY="0".repeat(64);
    assert.equal(c.sandboxConfigured(),true);
    const pending=c.sealPending("sample-request-token","sample-request-secret");
    assert.doesNotMatch(pending,/sample-request-token|sample-request-secret/);
    assert.deepEqual(c.readPending(pending)?.token,"sample-request-token");
    assert.equal(c.readAccess(pending),null);
    const access=c.sealAccess("sample-access-token","sample-access-secret");
    assert.equal(c.readPending(access),null);
    assert.equal(c.readAccess(access)?.token,"sample-access-token");
    // Mutate an authenticated tag byte (not the final base64url character:
    // its unused padding bits can decode to the same bytes).
    const tamperedParts=pending.split(".");
    tamperedParts[2]=(tamperedParts[2][0]==="A"?"B":"A")+tamperedParts[2].slice(1);
    assert.equal(c.readPending(tamperedParts.join(".")),null);
    const url=new URL(c.authorizeSandboxUrl("token/a+b"));
    assert.equal(url.origin,"https://us.etrade.com");
    assert.equal(url.searchParams.get("key"),"sandbox-test-key");
    assert.equal(url.searchParams.get("token"),"token/a+b");
    const header=c.oauthHeader("GET","https://api.etrade.com/oauth/request_token",
      "sandbox-test-key","sandbox-test-secret",undefined,undefined,{oauth_callback:"oob"});
    assert.match(header,/oauth_signature_method="HMAC-SHA1"/);
    assert.match(header,/oauth_callback="oob"/);
    assert.match(header,/oauth_signature="/);
    assert.doesNotMatch(header,/sandbox-test-secret/);
    const before=Date.now;Date.now=()=>before()+301000;
    try{assert.equal(c.readPending(pending),null);}
    finally{Date.now=before;}
  }finally{
    for(const key of ["ETRADE_SANDBOX_CONSUMER_KEY","ETRADE_SANDBOX_CONSUMER_SECRET","ETRADE_SANDBOX_COOKIE_KEY"]){
      if(Object.prototype.hasOwnProperty.call(env,key))process.env[key]=env[key];
      else delete process.env[key];
    }
  }
});

test("sandbox connection endpoints cannot submit, preview, cancel or change orders",()=>{
  const root=path.join(__dirname,"../app/api/etrade-sandbox");
  const routes=["status","begin","complete","accounts","disconnect"];
  for(const route of routes){
    const file=path.join(root,route,"route.ts");
    assert.equal(fs.existsSync(file),true);
    const text=fs.readFileSync(file,"utf8");
    assert.doesNotMatch(text,/\/orders\//i);
    assert.doesNotMatch(text,/\bplaceOrder\b|\bpreviewOrder\b|\bsubmitOrder\b/);
  }
  const lib=fs.readFileSync(path.join(__dirname,"../lib/etrade-sandbox-oauth.ts"),"utf8");
  assert.match(lib,/SANDBOX_API_HOST="https:\/\/apisb\.etrade\.com"/);
  assert.doesNotMatch(lib,/https:\/\/api\.etrade\.com\/v1\/accounts/);
  assert.doesNotMatch(lib,/\/orders\/(?:preview|place|cancel)/);
  const src=fs.readFileSync(path.join(__dirname,"../app/WtEtradeSandboxConnect.tsx"),"utf8");
  assert.match(src,/data-etrade-sandbox-only="true"/);
  assert.match(src,/Order submission: DISABLED/);
  assert.doesNotMatch(src,/\/api\/etrade[^"'\s]*\/orders\//);
  const wt=fs.readFileSync(path.join(__dirname,"../app/WtEtradeOrderPrep.tsx"),"utf8");
  assert.match(wt,/WtEtradeSandboxConnect/);
  const begin=fs.readFileSync(path.join(root,"begin/route.ts"),"utf8");
  assert.match(begin,/hasSession/);
  const complete=fs.readFileSync(path.join(root,"complete/route.ts"),"utf8");
  const disconnect=fs.readFileSync(path.join(root,"disconnect/route.ts"),"utf8");
  assert.match(complete,/origin!==req\.nextUrl\.origin/);
  assert.match(disconnect,/origin!==req\.nextUrl\.origin/);
  assert.match(disconnect,/revokeSandboxToken/);
});

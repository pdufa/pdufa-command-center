/**
 * E*TRADE retail OAuth 1.0a -- SANDBOX CONNECTIVITY ONLY.
 *
 * The OAuth endpoints are shared; a sandbox consumer key scopes access to
 * https://apisb.etrade.com. No live account endpoint or order endpoint is used.
 * Secrets/tokens are stored in encrypted HttpOnly cookies, never browser JS.
 * This module intentionally exposes no order placement or order-preview call.
 */
import {createCipheriv,createDecipheriv,createHmac,randomBytes} from "node:crypto";

const OAUTH_HOST="https://api.etrade.com";
const AUTHORIZE_HOST="https://us.etrade.com/e/t/etws/authorize";
export const SANDBOX_API_HOST="https://apisb.etrade.com";
export const REQUEST_COOKIE="pdufa_wt_etrade_sb_request";
export const ACCESS_COOKIE="pdufa_wt_etrade_sb_access";
export const OAUTH_REQUEST_MAX_AGE=300; // E*TRADE request tokens expire after 5 minutes.
export const ACCESS_MAX_AGE=7200; // Reauthorize rather than silently renewing.
const AAD=Buffer.from("pdufa-wt-etrade-sandbox-token-v1","utf8");

type TokenPair={token:string;secret:string;issuedAt:number};
const enc=(v:string)=>encodeURIComponent(v).replace(/[!'()*]/g,c=>"%"+c.charCodeAt(0).toString(16).toUpperCase());

function getConfig(){
  const consumerKey=(process.env.ETRADE_SANDBOX_CONSUMER_KEY||"").trim();
  const consumerSecret=(process.env.ETRADE_SANDBOX_CONSUMER_SECRET||"").trim();
  const cookieKey=(process.env.ETRADE_SANDBOX_COOKIE_KEY||"").trim();
  if(!consumerKey||!consumerSecret||!/^[0-9a-f]{64}$/i.test(cookieKey))
    return null;
  return {consumerKey,consumerSecret,cookieKey:Buffer.from(cookieKey,"hex")};
}
export function sandboxConfigured(){return getConfig()!==null;}

function encrypt(pair:TokenPair):string {
  const config=getConfig();
  if(!config)throw new Error("Sandbox not configured");
  const iv=randomBytes(12);
  const cipher=createCipheriv("aes-256-gcm",config.cookieKey,iv);
  cipher.setAAD(AAD);
  const body=Buffer.concat([cipher.update(JSON.stringify(pair),"utf8"),cipher.final()]);
  return "v1."+iv.toString("base64url")+"."+cipher.getAuthTag().toString("base64url")+"."+body.toString("base64url");
}
function decrypt(text:string|undefined,maxAge:number):TokenPair|null {
  const config=getConfig();
  if(!config||!text||text.length>4096)return null;
  const parts=text.split(".");
  if(parts.length!==4||parts[0]!=="v1")return null;
  try{
    const iv=Buffer.from(parts[1],"base64url");
    const tag=Buffer.from(parts[2],"base64url");
    const body=Buffer.from(parts[3],"base64url");
    if(iv.length!==12||tag.length!==16||body.length>2048)return null;
    const decipher=createDecipheriv("aes-256-gcm",config.cookieKey,iv);
    decipher.setAAD(AAD);decipher.setAuthTag(tag);
    const raw=Buffer.concat([decipher.update(body),decipher.final()]).toString("utf8");
    const value=JSON.parse(raw) as Partial<TokenPair>;
    if(typeof value.token!=="string"||!value.token||typeof value.secret!=="string"||!value.secret||
      typeof value.issuedAt!=="number"||!Number.isSafeInteger(value.issuedAt)||
      Date.now()<value.issuedAt||Date.now()-value.issuedAt>maxAge*1000)return null;
    return {token:value.token,secret:value.secret,issuedAt:value.issuedAt};
  }catch{return null;}
}
export function readPending(cookie:string|undefined){return decrypt(cookie,OAUTH_REQUEST_MAX_AGE);}
export function readAccess(cookie:string|undefined){return decrypt(cookie,ACCESS_MAX_AGE);}
export function sealPending(token:string,secret:string){return encrypt({token,secret,issuedAt:Date.now()});}
export function sealAccess(token:string,secret:string){return encrypt({token,secret,issuedAt:Date.now()});}

/** Stable OAuth 1.0a HMAC-SHA1 signer with RFC 5849 percent-encoding. */
export function oauthHeader(
  method:"GET"|"POST",url:string,consumerKey:string,consumerSecret:string,
  token?:string,tokenSecret?:string,extra:Record<string,string>={}
):string {
  const parsed=new URL(url);
  if(parsed.protocol!=="https:")throw new Error("HTTPS required");
  const oauth:Record<string,string>={
    oauth_consumer_key:consumerKey,
    oauth_nonce:randomBytes(18).toString("hex"),
    oauth_signature_method:"HMAC-SHA1",
    oauth_timestamp:String(Math.floor(Date.now()/1000)),
    oauth_version:"1.0",
    ...(token?{oauth_token:token}:{}),
    ...extra,
  };
  const params:Array<[string,string]>=[
    ...Array.from(parsed.searchParams.entries()),
    ...Object.entries(oauth),
  ];
  params.sort((a,b)=>enc(a[0]).localeCompare(enc(b[0]))||enc(a[1]).localeCompare(enc(b[1])));
  const query=params.map(([k,v])=>enc(k)+"="+enc(v)).join("&");
  const base=method+"&"+enc(parsed.origin+parsed.pathname)+"&"+enc(query);
  const signingKey=enc(consumerSecret)+"&"+enc(tokenSecret||"");
  const signature=createHmac("sha1",signingKey).update(base,"utf8").digest("base64");
  const header={...oauth,oauth_signature:signature};
  return "OAuth "+Object.entries(header).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>enc(k)+'="'+enc(v)+'"').join(", ");
}
async function oauthGet(path:"/oauth/request_token"|"/oauth/access_token",token?:TokenPair,extra:Record<string,string>={}){
  const config=getConfig();
  if(!config)throw new Error("E*TRADE sandbox credentials not installed");
  const url=OAUTH_HOST+path;
  const auth=oauthHeader("GET",url,config.consumerKey,config.consumerSecret,token?.token,token?.secret,extra);
  const response=await fetch(url,{method:"GET",headers:{Authorization:auth,Accept:"text/plain"},redirect:"error",
    cache:"no-store",signal:AbortSignal.timeout(12000)});
  if(!response.ok)throw new Error("E*TRADE OAuth request rejected");
  const txt=await response.text();
  if(txt.length>8192)throw new Error("Unexpected OAuth response size");
  const form=new URLSearchParams(txt);
  const next=form.get("oauth_token"),secret=form.get("oauth_token_secret");
  if(!next||!secret)throw new Error("E*TRADE returned incomplete OAuth credentials");
  return {token:next,secret};
}
export async function requestSandboxToken(){
  return oauthGet("/oauth/request_token",undefined,{oauth_callback:"oob"});
}
export function authorizeSandboxUrl(token:string):string {
  const config=getConfig();
  if(!config)throw new Error("Sandbox credentials missing");
  const u=new URL(AUTHORIZE_HOST);
  u.searchParams.set("key",config.consumerKey);u.searchParams.set("token",token);
  return u.toString();
}
export async function exchangeSandboxVerifier(pending:TokenPair,verifier:string){
  if(!/^[A-Za-z0-9]{4,64}$/.test(verifier))throw new Error("Invalid verifier format");
  return oauthGet("/oauth/access_token",pending,{oauth_verifier:verifier});
}
export async function revokeSandboxToken(access:TokenPair){
  const config=getConfig();
  if(!config)throw new Error("Sandbox not configured");
  const url=OAUTH_HOST+"/oauth/revoke_access_token";
  const auth=oauthHeader("GET",url,config.consumerKey,config.consumerSecret,access.token,access.secret);
  const response=await fetch(url,{headers:{Authorization:auth,Accept:"text/plain"},
    cache:"no-store",redirect:"error",signal:AbortSignal.timeout(12000)});
  if(!response.ok)throw new Error("E*TRADE sandbox token revocation unsuccessful");
}

export async function listSandboxAccounts(access:TokenPair){
  const config=getConfig();
  if(!config)throw new Error("Sandbox credentials missing");
  const url=SANDBOX_API_HOST+"/v1/accounts/list.json";
  const auth=oauthHeader("GET",url,config.consumerKey,config.consumerSecret,access.token,access.secret);
  const result=await fetch(url,{headers:{Authorization:auth,Accept:"application/json"},
    cache:"no-store",redirect:"error",signal:AbortSignal.timeout(12000)});
  if(!result.ok)throw new Error("Sandbox account listing unavailable; token may be inactive");
  const raw=await result.text();
  if(raw.length>150000)throw new Error("Unexpected accounts response size");
  const parsed=JSON.parse(raw);
  const values=parsed?.AccountListResponse?.Accounts?.Account;
  const rows=Array.isArray(values)?values:values?[values]:[];
  return rows.slice(0,20).map((x:Record<string,unknown>)=>({
    name:String(x.accountName||x.accountDesc||"Sandbox brokerage").slice(0,100),
    accountType:String(x.accountType||"UNKNOWN").slice(0,40),
    status:String(x.accountStatus||"UNKNOWN").slice(0,30),
  }));
}

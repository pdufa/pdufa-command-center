/** Deduplicate concurrent owner-page reads without caching completed responses. */
let pending:Promise<unknown>|null=null;
export function readSavedFocus():Promise<unknown>{
 if(pending)return pending;
 pending=fetch('/api/assessments/runtime?focus=true',{cache:'no-store'}).then(async response=>{
  const body=await response.json();if(!response.ok)throw Error(body.error||'Saved FOCUS results unavailable');return body;
 }).finally(()=>{pending=null;});
 return pending;
}

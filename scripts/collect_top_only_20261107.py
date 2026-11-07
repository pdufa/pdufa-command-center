"""Refresh only the frozen live TOP identifiers; never requests another sheet."""
import concurrent.futures,datetime as dt,json,pathlib,time,urllib.request,urllib.error
from collect_phase_first_registry_20261106 import project,ROOT
D=ROOT/'new-platform/frontend/data';C=pathlib.Path('/tmp/top-only-20261107/registry');C.mkdir(parents=True,exist_ok=True)
def main():
 baseline=json.loads((D/'topOnlyBaseline20261107.json').read_text());ids=[r['nctId'] for r in baseline['records']];assert len(ids)==len(set(ids))
 def one(n):
  path=C/(n+'.json');url='https://clinicaltrials.gov/api/v2/studies/'+n
  if path.exists():return json.loads(path.read_text())
  for attempt in range(3):
   try:
    s=json.loads(urllib.request.urlopen(url,timeout=35).read());now=dt.datetime.now(dt.timezone.utc).isoformat();r=project(s,now,url,{n});p=s['protocolSection'];r.update(eligibility=p.get('eligibilityModule',{}),completion=p['statusModule'].get('completionDateStruct'),briefSummary=p.get('descriptionModule',{}).get('briefSummary'),sourceState='VERIFIED_CURRENT_REGISTRY');path.write_text(json.dumps(r));return r
   except Exception as e:
    if attempt==2:return {'trialId':n,'sourceState':'SOURCE_BLOCKED','blocker':str(e),'sourceUrl':url,'retrievedAt':dt.datetime.now(dt.timezone.utc).isoformat()}
    time.sleep(15 if isinstance(e,urllib.error.HTTPError) and e.code==429 else attempt+1)
 with concurrent.futures.ThreadPoolExecutor(3) as pool:records=list(pool.map(one,ids))
 assert {r['trialId'] for r in records}==set(ids)
 (D/'topOnlyRegistry20261107.json').write_text(json.dumps({'schemaVersion':1,'scope':'FROZEN_EXISTING_TOP_ONLY','retrievedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'records':records},indent=2)+'\n')
 print(json.dumps({'topTrials':len(ids),'verified':sum(r['sourceState']=='VERIFIED_CURRENT_REGISTRY' for r in records),'blocked':sum(r['sourceState']=='SOURCE_BLOCKED' for r in records)}))
if __name__=='__main__':main()

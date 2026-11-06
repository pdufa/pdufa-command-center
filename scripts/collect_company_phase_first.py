"""Resume exact-NCT registry research for one company in the existing census.
Does not change census membership, grades, predictions or pipeline eligibility.
"""
import argparse
import concurrent.futures
import datetime as dt
import json
import time
import urllib.request
from pathlib import Path
from collect_phase_first_registry_20261106 import project, ROOT

def collect(ticker, cache, output):
    rows=json.loads((ROOT/'new-platform/frontend/public/phase3-unified-classifications-2026-11-05.json').read_text())['rows']
    ids=[r['nctId'] for r in rows if r['ticker']==ticker]
    if not ids or len(set(ids))!=len(ids):
        raise ValueError('UNKNOWN_TICKER_OR_DUPLICATE_CENSUS')
    cache.mkdir(parents=True,exist_ok=True)
    def fetch(nct):
        url='https://clinicaltrials.gov/api/v2/studies/'+nct
        saved=cache/(nct+'.json')
        if saved.exists():
            snapshot=json.loads(saved.read_text())
        else:
            for attempt in range(3):
                try:
                    study=json.loads(urllib.request.urlopen(url,timeout=45).read())
                    snapshot={'retrievedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'study':study}
                    saved.write_text(json.dumps(snapshot))
                    break
                except Exception:
                    if attempt==2:raise
                    time.sleep(attempt+1)
        return project(snapshot['study'],snapshot['retrievedAt'],url,{nct})
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        records=list(pool.map(fetch,ids))
    if {r['trialId'] for r in records}!=set(ids):raise ValueError('INCOMPLETE_IDENTITY_SET')
    payload={'schemaVersion':1,'asOf':max(r['retrievedAt'] for r in records),
        'scope':f'Exact {len(ids)} {ticker} trials in existing 762-trial census; not an exhaustive acquired-program sponsor census',
        'records':records}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps({'ticker':ticker,'trials':len(records),'output':str(output)}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ticker',required=True)
    p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();collect(a.ticker,a.cache,a.output)

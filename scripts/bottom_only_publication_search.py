"""Repeatable full-inventory primary-publication search; never infers grades.
Raw indexed abstracts remain local research captures; the committed ledger stores
bibliography, query, exact-NCT matching flags, retrieval date and source URLs.
"""
from __future__ import annotations
import concurrent.futures
import json
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'new-platform/frontend/data'
SOURCES=ROOT/'reports/bottom-only-20261107/sources'

def search_trial(trial,drug):
    nct=trial['nctId'];alias=re.split(r'\s|\(',drug or '')[0].strip()
    query=nct if not alias else f'{nct} OR ("{alias}" AND ("phase 3" OR "phase III"))'
    cursor='*';results=[];urls=[]
    try:
        while True:
            url='https://www.ebi.ac.uk/europepmc/webservices/rest/search?'+urlencode({'format':'json','resultType':'core','query':query,'pageSize':100,'cursorMark':cursor})
            urls.append(url)
            with urlopen(Request(url,headers={'User-Agent':'PDUFA source research'}),timeout=40) as response:page=json.load(response)
            results.extend(page.get('resultList',{}).get('result',[]))
            following=page.get('nextCursorMark')
            if not following or following==cursor or not page.get('resultList',{}).get('result'):break
            cursor=following
        path=SOURCES/(nct+'-publication-search.json');path.write_text(json.dumps({'query':query,'results':results},indent=2)+'\n')
        bibliography=[]
        for row in results:
            bibliography.append({**{k:row.get(k) for k in ['id','source','title','authorString','firstPublicationDate','doi','pmcid','isOpenAccess','fullTextUrlList']},'exactNctInAbstract':nct in row.get('abstractText',''),'sourceUrl':'https://europepmc.org/article/'+str(row.get('source','MED'))+'/'+str(row.get('id',''))})
        return {'nctId':nct,'query':query,'sourceUrls':urls,'retrievedAt':datetime.now(timezone.utc).isoformat(),'state':'SEARCH_COMPLETED','bibliography':bibliography,'note':'A search hit is a lead, not an accepted clinical finding. Match exact NCT or explicit protocol/drug/indication crosswalk before grading.'}
    except Exception as exc:
        return {'nctId':nct,'query':query,'sourceUrls':urls,'retrievedAt':datetime.now(timezone.utc).isoformat(),'state':'ACCESS_BLOCKED','error':str(exc),'bibliography':[]}

def collect_publications():
    baseline=json.loads((DATA/'bottomOnlyBaseline20261107.json').read_text());reviews=[]
    for name in ['raas-reviewed-metric-assessments.json','raas-clinical-five-reviewed-increment.json','bottomOnlyReviewedGradeIncrement20261107.json']:reviews+=json.loads((DATA/name).read_text())['records']
    drugs={r['nctId']:r['drug'] for r in reviews if r['stage']=='post'}
    SOURCES.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        results=list(pool.map(lambda t:search_trial(t,drugs.get(t['nctId'],t.get('drug'))),baseline['records']))
    discovery=ROOT/'reports/bottom-only-20261107/publication-discovery-ledger.json'
    archive=json.loads(discovery.read_text()) if discovery.exists() else {'schemaVersion':1,'captures':[]}
    for result in results:
        fingerprint=hashlib.sha256(json.dumps({k:v for k,v in result.items() if k!='retrievedAt'},sort_keys=True).encode()).hexdigest()
        if not any(r.get('fingerprint')==fingerprint for r in archive['captures']):
            archive['captures'].append({**result,'fingerprint':fingerprint})
    discovery.write_text(json.dumps(archive,indent=2,ensure_ascii=False)+'\n')
    target=DATA/'bottomOnlyReviewedFacts20261107.json';ledger=json.loads(target.read_text())
    ledger.setdefault('publicationSearchHistory',[])
    for old in ledger.get('publicationSearches',[]):
        if old not in ledger['publicationSearchHistory']:ledger['publicationSearchHistory'].append(old)
    ledger['publicationSearches']=[{**r,'totalHits':len(r['bibliography']),
      'bibliography':[b for b in r['bibliography'] if b['exactNctInAbstract']],
      'otherHitsRetainedIn':'reports/bottom-only-20261107/publication-discovery-ledger.json'} for r in results]
    target.write_text(json.dumps(ledger,indent=2,ensure_ascii=False)+'\n')
    return results
if __name__=='__main__':
    results=collect_publications();print(json.dumps({'processed':len(results),'blocked':sum(r['state']=='ACCESS_BLOCKED' for r in results),'exactNctAbstracts':sum(sum(p['exactNctInAbstract'] for p in r['bibliography']) for r in results)}))

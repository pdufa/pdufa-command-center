"""Refresh every saved BOTTOM NCT; never alter membership, grades or old facts.

Network collection uses --fetch. Offline extraction is deterministic. A changed
source hash invalidates the review receipt; subjective grades require review.
Run the frontend bottom-only-recalculate.cjs afterwards. No workflow is enabled.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'new-platform/frontend/data'
REPORT = ROOT / 'reports/bottom-only-20261107'
SOURCES = REPORT / 'sources'

def read(path): return json.loads(path.read_text())
def write(path, value): path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
def collect(nct):
    url = 'https://clinicaltrials.gov/api/v2/studies/'+nct
    try:
        with urlopen(Request(url, headers={'User-Agent':'PDUFA clinical research evidence backfill'}), timeout=45) as response:
            raw = response.read()
        document=json.loads(raw)
        if document['protocolSection']['identificationModule']['nctId'] != nct:
            raise ValueError('EXACT_NCT_MISMATCH')
        digest=hashlib.sha256(raw).hexdigest()
        # Content-addressed archive retains every prior registry revision.
        archive=SOURCES/(nct+'-'+digest+'.json')
        if not archive.exists(): archive.write_bytes(raw)
        latest=SOURCES/(nct+'-registry.json')
        if latest.exists():
            old=latest.read_bytes()
            prior=SOURCES/(nct+'-'+hashlib.sha256(old).hexdigest()+'.json')
            if not prior.exists(): prior.write_bytes(old)
        latest.write_bytes(raw)
        return {'nctId':nct,'sourceUrl':url,'sha256':digest,'retrievedAt':datetime.now(timezone.utc).isoformat(),'state':'VERIFIED'}
    except Exception as exc:
        return {'nctId':nct,'sourceUrl':url,'state':'MISSING_EVIDENCE','error':str(exc)}

def extract(nct, document):
    p=document['protocolSection']; identification=p['identificationModule']
    if identification['nctId'] != nct: raise ValueError('EXACT_NCT_MISMATCH:'+nct)
    d=p.get('designModule',{}); s=p.get('statusModule',{}); results=document.get('resultsSection',{})
    url='https://clinicaltrials.gov/api/v2/studies/'+nct
    dated=s.get('lastUpdatePostDateStruct',{}).get('date')
    if 'PHASE3' not in d.get('phases',[]): raise ValueError('PHASE3_MISMATCH:'+nct)
    om=results.get('outcomeMeasuresModule',{}).get('outcomeMeasures',[])
    modules={
      6:('protocolSection.eligibilityModule',p.get('eligibilityModule')),
      7:('protocolSection.outcomesModule.primaryOutcomes',p.get('outcomesModule',{}).get('primaryOutcomes')),
      9:('protocolSection.designModule.designInfo',d.get('designInfo')),
      11:('protocolSection.armsInterventionsModule',p.get('armsInterventionsModule')),
      12:('protocolSection.designModule.enrollmentInfo',d.get('enrollmentInfo')),
      17:('resultsSection.outcomeMeasuresModule.outcomeMeasures', [o for o in om if o.get('type')=='SECONDARY' and o.get('reportingStatus')=='POSTED']),
      23:('resultsSection.adverseEventsModule',results.get('adverseEventsModule')),
      24:('resultsSection.participantFlowModule',results.get('participantFlowModule')),
      25:('protocolSection.statusModule',s),
      26:('resultsSection.baselineCharacteristicsModule',results.get('baselineCharacteristicsModule')),
    }
    facts=[]
    for question,(pointer,value) in modules.items():
        if not value: continue
        facts.append({'nctId':nct,'question':question,'sourceUrl':url,'sourceDate':dated,
          'retrievedAt':'2026-11-07','classification':'REGISTRY_REPORTED_FACT',
          'evidence':json.dumps(value,ensure_ascii=False,separators=(',',':')),
          'criticalLimit':'Registry-reported data, not an independently adjudicated clinical grade. Keep phase, analysis population, arm denominators and exposure periods separate; NOT_POSTED outcomes remain pending.',
          'sourceType':'REGISTRY','sourcePointer':pointer,'evidenceStatus':'VERIFIED'})
    return facts,{'nctId':nct,'phase':d.get('phases'), 'identity':identification,
      'sponsor':p.get('sponsorCollaboratorsModule'), 'statusAndDates':s,'design':d,
      'arms':p.get('armsInterventionsModule'),'outcomes':p.get('outcomesModule'),
      'resultsAvailable':bool(results),'reportedResults':results or None,
      'protocolAndSap':document.get('documentSection'),
      'sourceUrl':url,'sourceDate':dated,'retrievedAt':'2026-11-07',
      'missingResultsMeaning':'Registry results absence does not negate documented issuer/publication readout.'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--fetch',action='store_true');args=parser.parse_args()
    SOURCES.mkdir(parents=True,exist_ok=True)
    baseline=read(DATA/'bottomOnlyBaseline20261107.json'); ids=[r['nctId'] for r in baseline['records']]
    if len(ids)!=len(set(ids)): raise ValueError('DUPLICATE_BOTTOM_NCT')
    if args.fetch:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: receipts=list(pool.map(collect,ids))
        write(REPORT/'registry-refresh-receipt.json',receipts)
        if any(r['state']!='VERIFIED' for r in receipts): raise RuntimeError('Incomplete refresh; prior facts preserved. See receipt.')
    ledger=read(DATA/'bottomOnlyReviewedFacts20261107.json')
    existing={(r['nctId'],r['question'],r['sourceUrl']) for r in ledger['records']}
    reviews=[]
    for nct in ids:
        facts,review=extract(nct,read(SOURCES/(nct+'-registry.json')));reviews.append(review)
        for fact in facts:
            key=(nct,fact['question'],fact['sourceUrl'])
            if key not in existing: ledger['records'].append(fact);existing.add(key)
    # The raw research file is an exact-NCT, field-addressed evidence snapshot,
    # not a replacement spreadsheet or alternate grading system.
    for review in reviews:
        review['sourceHash']=hashlib.sha256((SOURCES/(review['nctId']+'-registry.json')).read_bytes()).hexdigest()
    ledger['registryReviews']=reviews
    write(DATA/'bottomOnlyReviewedFacts20261107.json',ledger)
    print(json.dumps({'processed':len(reviews),'totalFacts':len(ledger['records']),'registryResults':sum(r['resultsAvailable'] for r in reviews)}))
if __name__=='__main__': main()

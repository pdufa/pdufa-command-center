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
import re
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'new-platform/frontend/data'
REPORT = ROOT / 'reports/bottom-only-20261107'
SOURCES = REPORT / 'sources'

def read(path): return json.loads(path.read_text())
def write(path, value): path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
def fact_fingerprint(fact):
    if fact.get('sourceHash'):return fact['sourceHash']
    if not fact.get('sourcePointer'):return 'UNVERSIONED'
    try: value=json.loads(fact['evidence'])
    except (ValueError,KeyError):return 'UNVERSIONED'
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def clinical_fingerprint(document):
    p=document['protocolSection']
    # Administrative status/contact/date changes do not invalidate clinical
    # observations. Actual arms, analysis population, outcomes or results do.
    clinical={'nctId':p['identificationModule']['nctId'],
      'design':p.get('designModule'),'arms':p.get('armsInterventionsModule'),
      'outcomes':p.get('outcomesModule'),'eligibility':p.get('eligibilityModule'),
      'results':document.get('resultsSection'),'documents':document.get('documentSection')}
    return hashlib.sha256(json.dumps(clinical,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def reconcile_active_inventory(baseline, matrix, active, documents):
    """Append newly qualified exact NCTs; never remove an inactive research row."""
    known={r['nctId'] for r in baseline['records']}
    if len(known)!=len(baseline['records']) or len(matrix['headers'])!=190:
        raise ValueError('BOTTOM_INVENTORY_INTEGRITY')
    appended=[]
    for row in active['records']:
        nct=row['nct']
        if not re.fullmatch(r'NCT\d{8}',nct):raise ValueError('INVALID_ACTIVE_NCT')
        if nct in known:continue
        cap=row.get('marketCap')
        if not isinstance(cap,(int,float)) or isinstance(cap,bool) or not 300_000_000<=cap<=10_000_000_000:
            raise ValueError('ACTIVE_CAP_ELIGIBILITY:'+nct)
        document=documents[nct]
        extract(nct,document)  # Exact identity and Phase 3, before any append.
        p=document['protocolSection'];status=p.get('statusModule',{})
        posted=bool(document.get('resultsSection'))
        kind='REGISTRY_RESULTS_POSTED' if posted else 'CANONICAL_READOUT_REQUIRES_SOURCE_REVIEW'
        date=status.get('resultsFirstPostDateStruct',{}).get('date') if posted else None
        registry='https://clinicaltrials.gov/study/'+nct
        record={'nctId':nct,'ticker':row['ticker'],'company':row['company'],
          'registryStatus':status.get('overallStatus','UNKNOWN'),'rosterStatus':status.get('overallStatus','UNKNOWN'),
          'registryAsOf':datetime.now(timezone.utc).isoformat(),
          'classificationCode':'P3_POST_DATA_REGISTRY' if posted else 'P3_POST_DATA_CANONICAL_REVIEW_REQUIRED',
          'classification':'Canonical active exact-NCT Phase 3 post-data candidate',
          'classificationEvidence':'Existing canonical active roster; exact NCT registry identity checked. New clinical grading requires explicit review.',
          'classificationVerified':posted,'readoutEvidenceType':kind,'readoutSourceDate':date,
          'readoutEvidenceUrl':row['resultsUrl'],'readoutOutcome':'NOT_INDEPENDENTLY_REVIEWED',
          'drug':None,'indication':'; '.join(p.get('conditionsModule',{}).get('conditions',[])),
          'registeredInterventions':'; '.join(x['name'] for x in p.get('armsInterventionsModule',{}).get('interventions',[])),
          'registrySourceUrl':registry,'fdaApplicationStatus':row['fdaStatus'],'fdaReviewType':'NOT_VERIFIED',
          'pdufaGoalDate':row['fdaStatus'] if re.fullmatch(r'\d{4}-\d{2}-\d{2}',row['fdaStatus']) else None,
          'marketCapSourceStatus':'VERIFIED','inDatedMarketCapScreen':True,'cohort':'POST_DATA',
          'evidenceBasis':kind,'originalClassificationCode':'CANONICAL_ACTIVE_SHEET','correctionApplied':False}
        baseline['records'].append(record);known.add(nct);appended.append(record)
        cells=['']*190
        values={0:nct,1:row['ticker'],2:row['company'],3:record['classification'],4:record['classificationCode'],
          5:record['registryStatus'],6:record['rosterStatus'],7:active['asOf'],8:kind,9:date or '',
          10:record['readoutOutcome'],12:record['indication'],13:record['registeredInterventions'],
          14:row['fdaStatus'],16:record['pdufaGoalDate'] or '',17:row['resultsUrl'],18:registry,
          19:record['classificationEvidence'],25:kind,29:'VERIFIED',30:'TRUE',38:active['asOf'],
          39:'New exact active NCT; no numerical clinical review or forecast is inferred.'}
        for index,value in values.items():cells[index]=str(value)
        for question in range(30):cells[40+5*question]='UNSCORED'
        matrix['rows'].append(cells)
    return appended
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
      1:('resultsSection.outcomeMeasuresModule.outcomeMeasures',[o for o in om if o.get('type')=='PRIMARY' and o.get('reportingStatus')=='POSTED']),
      3:('resultsSection.adverseEventsModule',results.get('adverseEventsModule')),
      6:('protocolSection.eligibilityModule',p.get('eligibilityModule')),
      7:('protocolSection.outcomesModule.primaryOutcomes',p.get('outcomesModule',{}).get('primaryOutcomes')),
      8:('protocolSection.outcomesModule.primaryOutcomes.timeFrame',[o.get('timeFrame') for o in p.get('outcomesModule',{}).get('primaryOutcomes',[]) if o.get('timeFrame')]),
      9:('protocolSection.designModule.designInfo',d.get('designInfo')),
      10:('protocolSection.designModule.designInfo.maskingInfo',d.get('designInfo',{}).get('maskingInfo')),
      11:('protocolSection.armsInterventionsModule',p.get('armsInterventionsModule')),
      12:('protocolSection.designModule.enrollmentInfo',d.get('enrollmentInfo')),
      17:('resultsSection.outcomeMeasuresModule.outcomeMeasures', [o for o in om if o.get('type')=='SECONDARY' and o.get('reportingStatus')=='POSTED']),
      18:('resultsSection.outcomeMeasuresModule.outcomeMeasures',[o for o in om if o.get('reportingStatus')=='POSTED' and re.search(r'fatigue|quality of life|KCCQ|PROMIS|Epworth|SGRQ|symptom|patient.report',o.get('title',''),re.I)]),
      23:('resultsSection.adverseEventsModule',results.get('adverseEventsModule')),
      24:('resultsSection.participantFlowModule',results.get('participantFlowModule')),
      25:('protocolSection.statusModule',s),
      26:('resultsSection.baselineCharacteristicsModule',results.get('baselineCharacteristicsModule')),
      27:('protocolSection.armsInterventionsModule.interventions',p.get('armsInterventionsModule',{}).get('interventions')),
    }
    facts=[]
    for question,(pointer,value) in modules.items():
        if not value: continue
        facts.append({'nctId':nct,'question':question,'sourceUrl':url,'sourceDate':dated,
          'retrievedAt':datetime.now(timezone.utc).isoformat(),'classification':'REGISTRY_REPORTED_FACT',
          'evidence':json.dumps(value,ensure_ascii=False,separators=(',',':')),
          'criticalLimit':'Registry-reported data, not an independently adjudicated clinical grade. Keep phase, analysis population, arm denominators and exposure periods separate; NOT_POSTED outcomes remain pending.',
          'sourceType':'REGISTRY','sourcePointer':pointer,'evidenceStatus':'VERIFIED'})
        facts[-1]['sourceHash']=fact_fingerprint(facts[-1])
    return facts,{'nctId':nct,'phase':d.get('phases'), 'identity':identification,
      'sponsor':p.get('sponsorCollaboratorsModule'), 'statusAndDates':s,'design':d,
      'arms':p.get('armsInterventionsModule'),'outcomes':p.get('outcomesModule'),
      'resultsAvailable':bool(results),'reportedResults':results or None,
      'protocolAndSap':document.get('documentSection'),
      'sourceUrl':url,'sourceDate':dated,'retrievedAt':datetime.now(timezone.utc).isoformat(),
      'missingResultsMeaning':'Registry results absence does not negate documented issuer/publication readout.'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--fetch',action='store_true');args=parser.parse_args()
    SOURCES.mkdir(parents=True,exist_ok=True)
    baseline=read(DATA/'bottomOnlyBaseline20261107.json')
    active=read(DATA/'p3PostDataActive.json')
    if any(not re.fullmatch(r'NCT\d{8}',r['nct']) for r in active['records']):raise ValueError('INVALID_ACTIVE_NCT')
    ids=list(dict.fromkeys([r['nctId'] for r in baseline['records']]+[r['nct'] for r in active['records']]))
    if len(ids)!=len(set(ids)): raise ValueError('DUPLICATE_BOTTOM_NCT')
    if args.fetch:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: receipts=list(pool.map(collect,ids))
        receipt_path=REPORT/'registry-refresh-receipt.json'
        prior=read(receipt_path) if receipt_path.exists() else {'schemaVersion':1,'runs':[]}
        if isinstance(prior,list):prior={'schemaVersion':1,'runs':[{'records':prior,'note':'Preserved legacy receipt'}]}
        prior['runs'].append({'retrievedAt':datetime.now(timezone.utc).isoformat(),'records':receipts})
        write(receipt_path,prior)
        if any(r['state']!='VERIFIED' for r in receipts): raise RuntimeError('Incomplete refresh; prior facts preserved. See receipt.')
    documents={nct:read(SOURCES/(nct+'-registry.json')) for nct in ids}
    matrix=read(DATA/'bottomOnly190Baseline20261107.json')
    appended=reconcile_active_inventory(baseline,matrix,active,documents)
    if appended:
        write(DATA/'bottomOnlyBaseline20261107.json',baseline)
        write(DATA/'bottomOnly190Baseline20261107.json',matrix)
        history=read(DATA/'bottomOnlyResearchHistory20261107.json')
        for row in appended:
            history['records'].append({'eventId':'BOTTOM_ACTIVE_INTAKE_'+row['nctId'],
              'nctId':row['nctId'],'recordedAt':datetime.now(timezone.utc).date().isoformat(),
              'eventType':'CANONICAL_ACTIVE_EXACT_NCT_INTAKE','outcome':row['readoutOutcome'],
              'readoutEvidenceUrl':row['readoutEvidenceUrl'],
              'note':'New qualified canonical exact NCT captured. Clinical ratings pending; prior TOP/BOTTOM history retained.'})
        write(DATA/'bottomOnlyResearchHistory20261107.json',history)
    ledger=read(DATA/'bottomOnlyReviewedFacts20261107.json')
    existing={(r['nctId'],r['question'],r['sourceUrl'],fact_fingerprint(r)) for r in ledger['records']}
    reviews=[]
    for nct in ids:
        facts,review=extract(nct,read(SOURCES/(nct+'-registry.json')));reviews.append(review)
        for fact in facts:
            key=(nct,fact['question'],fact['sourceUrl'],fact_fingerprint(fact))
            if key not in existing: ledger['records'].append(fact);existing.add(key)
    # The raw research file is an exact-NCT, field-addressed evidence snapshot,
    # not a replacement spreadsheet or alternate grading system.
    for review in reviews:
        raw=(SOURCES/(review['nctId']+'-registry.json')).read_bytes()
        review['rawSourceHash']=hashlib.sha256(raw).hexdigest()
        review['sourceHash']=clinical_fingerprint(json.loads(raw))
    if args.fetch:ledger['sourceAsOf']=datetime.now(timezone.utc).date().isoformat()
    ledger['registryReviews']=reviews
    write(DATA/'bottomOnlyReviewedFacts20261107.json',ledger)
    print(json.dumps({'processed':len(reviews),'totalFacts':len(ledger['records']),'registryResults':sum(r['resultsAvailable'] for r in reviews)}))
if __name__=='__main__': main()

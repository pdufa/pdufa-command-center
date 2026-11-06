"""Exact-identity, phase-first registry projection. No scientific scores inferred."""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'new-platform/frontend/data'
FIELDS='NCTId,Phase,OverallStatus,StudyType,LastUpdatePostDate,OrgStudyId,BriefTitle,LeadSponsorName,Condition,InterventionName,InterventionType,PrimaryOutcomeMeasure,PrimaryOutcomeTimeFrame,SecondaryOutcomeMeasure,SecondaryOutcomeTimeFrame,EnrollmentCount,EnrollmentType,DesignAllocation,DesignMasking,DesignInterventionModel,StartDate,PrimaryCompletionDate,StudyFirstPostDate,HasResults'
def project(study, retrieved, search_url, expected=None):
 p=study['protocolSection'];i=p['identificationModule'];n=i['nctId']
 if expected is not None and n not in expected:raise ValueError('UNREQUESTED_NCT')
 s=p['statusModule'];d=p.get('designModule',{});updated=s['lastUpdatePostDateStruct']['date']
 dt.date.fromisoformat(updated)
 if updated>retrieved[:10]:raise ValueError('FUTURE_SOURCE_DATE')
 arms=p.get('armsInterventionsModule',{});out=p.get('outcomesModule',{})
 docs=study.get('documentSection',{}).get('largeDocumentModule',{}).get('largeDocs',[])
 return dict(trialId=n,nctId=n,title=i['briefTitle'],protocol=i.get('orgStudyIdInfo',{}).get('id'),
  acronym=i.get('acronym'),sponsor=p['sponsorCollaboratorsModule']['leadSponsor']['name'],
  phases=d.get('phases',[]),studyType=d.get('studyType','UNKNOWN'),status=s['overallStatus'],
  whyStopped=s.get('whyStopped'),indications=p.get('conditionsModule',{}).get('conditions',[]),
  interventions=[x for x in arms.get('interventions',[]) if x.get('type') not in ['OTHER']],
  arms=arms.get('armGroups',[]),design=d.get('designInfo',{}),enrollment=d.get('enrollmentInfo'),
  primary=out.get('primaryOutcomes',[]),secondary=out.get('secondaryOutcomes',[]),
  start=s.get('startDateStruct'),primaryCompletion=s.get('primaryCompletionDateStruct'),
  firstPosted=s.get('studyFirstPostDateStruct'),sourceDate=updated,retrievedAt=retrieved,
  sourceUrl='https://clinicaltrials.gov/study/'+n,sourceSearchUrl=search_url,
  hasResults=bool(study.get('hasResults') or study.get('resultsSection')),
  results=study.get('resultsSection',{}),documents=docs,
  publications=p.get('referencesModule',{}).get('references',[]),
  sourceSha256=hashlib.sha256(json.dumps(study,sort_keys=True).encode()).hexdigest())

def main(local):
 retrieved=dt.datetime.now(dt.timezone.utc).isoformat()
 source=json.loads((local/'all-registry.json').read_text());studies={s['protocolSection']['identificationModule']['nctId']:s for s in source['studies']}
 urls=source['searchUrls'][:]
 for f in sorted(local.glob('supplement-*.json')):
  r=json.loads(f.read_text());urls.append(r['url'])
  if r['response'].get('nextPageToken'):raise ValueError('SUPPLEMENT_PAGINATION_NOT_EXHAUSTED')
  for s in r['response']['studies']:studies[s['protocolSection']['identificationModule']['nctId']]=s
 rows=[project(s,retrieved,source['searchUrls'][0]) for s in studies.values()]
 (DATA/'alkermesPhaseFirstRegistry20261106.json').write_text(json.dumps(dict(schemaVersion=1,
  asOf=retrieved,scope='Sponsor/collaborator registry search plus current compound aliases; association is not current ownership',
  searchUrls=urls,records=rows),indent=2)+'\n')
 ids=[r['nctId'] for r in json.loads((ROOT/'new-platform/frontend/public/phase3-unified-classifications-2026-11-05.json').read_text())['rows']]
 target=DATA/'phaseFirstCensusRegistry20261106.json'
 saved=json.loads(target.read_text()) if target.exists() else dict(schemaVersion=1,asOf=retrieved,records=[])
 existing={r['trialId']:r for r in saved['records']}
 batches=[ids[i:i+25] for i in range(0,len(ids),25) if any(n not in existing for n in ids[i:i+25])]
 def collect(batch):
  u='https://clinicaltrials.gov/api/v2/studies?'+urllib.parse.urlencode({'filter.ids':','.join(batch),'fields':FIELDS,'pageSize':100})
  for attempt in range(3):
   try:
    b=urllib.request.urlopen(u,timeout=45).read();r=json.loads(b)
    if r.get('nextPageToken'):raise ValueError('UNEXPECTED_PAGINATION')
    rr=[project(s,retrieved,u,set(batch)) for s in r['studies']]
    if {x['trialId'] for x in rr}!=set(batch):raise ValueError('MISSING_OR_DUPLICATE_IDENTITIES')
    return rr
   except Exception:
    if attempt==2:raise
    time.sleep(attempt+1)
 with concurrent.futures.ThreadPoolExecutor(4) as pool:
  for result in pool.map(collect,batches):
   existing.update({r['trialId']:r for r in result});saved.update(asOf=retrieved,records=[existing[n] for n in ids if n in existing]);target.write_text(json.dumps(saved,indent=2)+'\n')
 if set(existing)!=set(ids):raise ValueError('CENSUS_IDENTITY_MISMATCH')
 print(json.dumps(dict(alkermesRegistryTrials=len(rows),censusTrials=len(existing))))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--local',type=Path,default=Path('/tmp/phase-first-alks'));main(p.parse_args().local)

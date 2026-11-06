"""Reviewed company-by-company batch; raw inputs in --source-dir are resumable.

Preserves earlier normalized slots and adjudications unless explicitly replaced.
Registry design, observed outcomes, source-date gaps and interpretation stay distinct.
"""
import argparse
import hashlib
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / 'new-platform/frontend/data'
COMPANIES = {
 'ABVX': ('https://ir.abivax.com/', 'https://www.abivax.com/'),
 'ADMA': ('https://ir.admabiologics.com/', 'https://www.admabiologics.com/'),
 'AGEN': ('https://investor.agenusbio.com/', 'https://www.agenusbio.com/pipeline/'),
 'ALEC': ('https://investors.alector.com/', 'https://www.alector.com/pipeline/'),
 'ALMS': ('https://investors.alumis.com/', 'https://www.alumis.com/pipeline/'),
 'ALT': ('https://ir.altimmune.com/', 'https://altimmune.com/pipeline/'),
 'ANNX': ('https://ir.annexonbio.com/', 'https://annexonbio.com/pipeline/'),
 'AQST': ('https://investors.aquestive.com/', 'https://aquestive.com/pipeline/'),
}
ABX_HBV = 'https://ir.abivax.com/news-releases/news-release-details/analysis-ongoing-abx203-phase-iibiii-trial-chronic-hepatitis-b'
ABX_COVID = 'https://ir.abivax.com/news-releases/news-release-details/abivax-follows-dsmb-recommendation-stop-phase-2b3-mir-age-covid/'
ADMA = 'https://www.globenewswire.com/news-release/2014/12/03/688334/33130/en/ADMA-Biologics-Announces-Positive-Top-Line-Phase-III-Data-for-Primary-Immune-Deficiency-Disease-PIDD-Patients.html'
AGEN_RCC = 'https://www.sec.gov/Archives/edgar/data/1098972/000115752306002979/a5109442ex99-1.txt'
AGEN_MEL = 'https://www.sec.gov/Archives/edgar/data/1098972/000115752306005819/a5161907ex99_1.txt'
BRAVA = 'https://investor.agenusbio.com/news/news-details/2021/Agenus-Provides-Update-on-Balstilimab-Development-10-22-2021/default.aspx'
ALEC = 'https://www.sec.gov/Archives/edgar/data/1653087/000119312525245102/alec-ex99_1.htm'
ALMS = 'https://investors.alumis.com/news-releases/news-release-details/alumis-envudeucitinib-delivers-leading-skin-clearance-among-next'
ALT = 'https://altimmune.gcs-web.com/node/17931'
ANNX = 'https://ir.annexonbio.com/news-releases/news-release-details/annexon-announces-positive-topline-results-pivotal-phase-3-trial'
ANNX_PRO = 'https://annexonbio.com/wp-content/uploads/2026/07/EAN-2026-PROs_ePoster_Draft_v4.00_18Jun2026_Final.pdf'
AQST = 'https://www.accessdata.fda.gov/drugsatfda_docs/nda/2024/218623Orig1s000MedR.pdf'


def main(source_dir):
 def read(n): return json.loads((DATA/n).read_text())
 def write(n,r): (DATA/n).write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n')
 ir=read('phase3CompanyWebsiteEvidence20261105.json')
 endpoints=read('phase3EndpointAdjudications20261105.json')
 queue=read('phase3InvestorRelationsResearchQueue20261106.json')
 trial_company={t['nctId']:c for c in queue['companies'] if c['ticker'] in COMPANIES for t in c['trials']}
 baseline_protocols={r['nctId']:r['sponsorProtocol'] for r in read('phase3PopulationGeography20261106.json')['records']}
 facts={(r['nctId'],r['assessmentNumber']):r for r in ir['assessmentRecords'] if r.get('recoveryBatch')!='COMPANY_WEBSITE_PASS_20261106'}
 prior_keys=set(facts)
 registry={};raw=[];batch_keys=set()
 def fact(n,q,text,url,date,status='DOCUMENTED_SOURCE_FACT',**extra):
  # Do not erase earlier curated observations in this company pass.
  if (n,q) in prior_keys: return
  facts[n,q]=dict(nctId=n,assessmentNumber=q,evidence=text,sourceUrl=url,
   publicationDate=date,classification=status,reviewedAt='2026-11-06',recoveryBatch='COMPANY_WEBSITE_PASS_20261106',
   sourceLocator=extra.pop('sourceLocator','Exact-NCT registry / trial-specific original document'),
   evidenceScope='HISTORICAL_SOURCE_FACT_NOT_PREDICTION',**extra)
  batch_keys.add((n,q))
 for n,c in trial_company.items():
  b=(source_dir/(n+'.json')).read_bytes();r=json.loads(b);p=r['protocolSection'];i=p['identificationModule']
  assert i['nctId']==n and i['orgStudyIdInfo']['id']==baseline_protocols[n]
  date=p['statusModule']['lastUpdatePostDateStruct']['date'];assert date<='2026-11-06'
  registry[n]=r;raw.append(dict(nctId=n,sourceUrl='https://clinicaltrials.gov/study/'+n,
   publicationDate=date,retrievedAt='2026-11-06',sourceSha256=hashlib.sha256(b).hexdigest(),registry=r))
  url='https://clinicaltrials.gov/study/'+n;d=p['designModule'];info=d.get('designInfo',{});primary=p.get('outcomesModule',{}).get('primaryOutcomes',[])
  text={
   7:'Registered primary outcomes: '+'; '.join(x['measure'] for x in primary),
   8:'Registered primary timing: '+'; '.join(x.get('timeFrame','unspecified') for x in primary),
   9:'Registry allocation/model: '+str(info.get('allocation','unspecified'))+' / '+str(info.get('interventionModel','unspecified')),
   10:'Registry masking: '+str(info.get('maskingInfo',{}).get('masking','unspecified'))+'; masking integrity not independently assessed.',
   12:'Registered enrollment: '+str(d.get('enrollmentInfo',{}))+'. This is not an efficacy/safety analysis denominator.',
   25:'Registry status '+p['statusModule']['overallStatus']+'. '+p['statusModule'].get('whyStopped',''),
  }
  for q,t in text.items():fact(n,q,t,url,date)
  arms=p.get('armsInterventionsModule',{}).get('armGroups',[])
  if arms:fact(n,11,'Registered arms: '+'; '.join(x['label']+' ('+x.get('type','unspecified')+')' for x in arms)+'. No independent comparator-adequacy score.',url,date)
  if any('placebo' in x['label'].lower() or x.get('type')=='PLACEBO_COMPARATOR' for x in arms):
   fact(n,27,'Placebo comparator explicitly named in registered arms; not a judgment about placebo suitability.',url,date)
  sec=p.get('outcomesModule',{}).get('secondaryOutcomes',[])
  if sec:fact(n,17,'Registered secondary measures (not positive results): '+'; '.join(x['measure']+' ['+x.get('timeFrame','unspecified')+']' for x in sec),url,date)
  res=r.get('resultsSection',{})
  if res:
   fact(n,29,'Exact-NCT results posted to registry. This documents historical public availability; no forecast generated.',url,date)
   ae=res.get('adverseEventsModule',{});groups=ae.get('eventGroups',[])
   if groups:
    common='; '.join(f"{g['title']}: {g.get('otherNumAffected','not reported')}/{g.get('otherNumAtRisk','not reported')} participants with non-serious events" for g in groups)
    serious='; '.join(f"{g['title']}: {g.get('seriousNumAffected','not reported')}/{g.get('seriousNumAtRisk','not reported')} participants with all-cause SAEs; deaths {g.get('deathsNumAffected','not reported')}/{g.get('deathsNumAtRisk','not reported')}" for g in groups)
    fact(n,3,common+'. Reporting threshold '+str(ae.get('frequencyThreshold','unspecified'))+'%; attribution and acceptability are not inferred.',url,date)
    fact(n,23,serious+'. Keep original period/cohort labels; extension groups are not concurrent randomized controls.',url,date)
   flow=res.get('participantFlowModule',{});periods=flow.get('periods',[]);labels={g['id']:g['title'] for g in flow.get('groups',[])}
   if periods:
    t=[]
    for per in periods:
     t.append(per['title']+': '+'; '.join(m['type']+' '+', '.join(labels[x['groupId']]+' '+x['numSubjects'] for x in m['achievements']) for m in per.get('milestones',[])))
    fact(n,24,' | '.join(t)+'. Noncompletion is distinct from treatment-related discontinuation; no retention grade.',url,date)
 # Explicit source-supported efficacy verdicts only. Futility/no-enrollment and
 # continuation records are deliberately not assigned a final efficacy verdict.
 verdicts={
  'NCT01814800':('PRIMARY_ENDPOINT_MET',ADMA,'2014-12-03','RI-002 ADMA-003 achieved its predefined SBI-rate endpoint in the single-arm PIDD trial: no serious bacterial infections. A threshold-based success, not randomized superiority.'),
  'NCT00033904':('PRIMARY_ENDPOINT_NOT_MET','https://pubmed.ncbi.nlm.nih.gov/18602688/','2008-07-03','C-100-12 Part I recurrence-free survival: HR .923 (95% CI .729-1.169), p=.506; primary endpoint not met. Publication expressly names NCT00033904. Exploratory subgroup signals do not establish a Part II outcome.'),
  'NCT00039000':('PRIMARY_ENDPOINT_NOT_MET',AGEN_MEL,'2006-06-05','C-100-21 overall ITT survival: 9.4 versus 10.7 months; HR 1.157, nominal one-sided p=.157. Primary superiority was not demonstrated. Selected patients receiving >=10 doses are a separate, potentially biased subgroup.'),
  'NCT04374136':('PRIMARY_ENDPOINT_NOT_MET',ALEC,'2025-10-21','INFRONT-3 did not meet its clinical co-primary CDR plus NACC FTLD-SB endpoint at 96 weeks. Significant plasma-progranulin biomarker change does not establish clinical efficacy.'),
  'NCT06586112':('PRIMARY_ENDPOINT_MET',ALMS,'2026-01-06','Issuer explicitly reports ONWARD1 met all primary and secondary endpoints. No averaged program response rate or pooled safety rate assigned to this individual trial.'),
  'NCT06588738':('PRIMARY_ENDPOINT_MET',ALMS,'2026-01-06','Issuer explicitly reports ONWARD2 met all primary and secondary endpoints. No averaged program response rate or pooled safety rate assigned to this individual trial.'),
  'NCT04701164':('PRIMARY_ENDPOINT_MET',ANNX,'2024-06-04','GBS-02 ANX005 30 mg/kg met week-8 GBS-DS primary endpoint: proportional odds ratio 2.4, p=.0058. No success inferred for the 75 mg/kg comparison or other Annexon studies.'),
  'NCT03428360':('NO_BINARY_PASS_FAIL','https://clinicaltrials.gov/study/NCT03428360','2021-08-05','42-1703 is a single-arm diazepam buccal-film safety study: 84 with >=1 TEAE and 18 with >=1 serious TEAE in the primary outcome table. No prespecified binary efficacy success threshold.'),
 }
 existing={r['nctId']:r for r in endpoints['records'] if r.get('recoveryBatch')!='COMPANY_WEBSITE_PASS_20261106'}
 for n,(outcome,url,date,t) in verdicts.items():
  crosswalk='Exact registry '+n+' = '+baseline_protocols[n]+'; '+registry[n]['protocolSection']['identificationModule']['briefTitle']
  if n not in existing: existing[n]=dict(nctId=n,endpointOutcome=outcome,rationale=t,evidenceUrl=url,
   sourceDate=date,reviewedAt='2026-11-06',recoveryBatch='COMPANY_WEBSITE_PASS_20261106',identityCrosswalk=crosswalk,
   identityEvidenceUrl='https://clinicaltrials.gov/study/'+n,evidenceType='OFFICIAL_SOURCE_EXACT_PROTOCOL_CROSSWALK',
   qualification='Historical source result only; no new prediction or pooled/continuation-trial substitution.')
  fact(n,1,t,url,date,'DOCUMENTED_NON_BINARY_ENDPOINT' if outcome=='NO_BINARY_PASS_FAIL' else 'DOCUMENTED_PRIMARY_ENDPOINT_MET' if outcome=='PRIMARY_ENDPOINT_MET' else 'DOCUMENTED_PRIMARY_ENDPOINT_NOT_MET')
  fact(n,29,'Trial-specific historical public readout: '+t,url,date)
 # Company-specific recoveries and explicit unresolved-source qualifications.
 details=[
 ('NCT02249988',1,'ABX203-002 interim futility analysis indicated primary endpoint unlikely to be reached. This is not a located final endpoint analysis; final adjudication remains pending.',ABX_HBV,'2016-06-17','REQUIRES_INTERPRETATION'),
 ('NCT04393038',1,'miR-AGE was stopped for futility after planned interim analysis of 305 participants. No between-group difference was observed; no invented final p-value or final binary verdict.',ABX_COVID,'2021-03-05','DOCUMENTED_SOURCE_FACT'),
 ('NCT04943627',30,'Issuer withdrew balstilimab BLA and discontinued BRAVA after pembrolizumab full approval. The prior accelerated-approval response rate is not a BRAVA result; historical December 16, 2021 goal is not a future PDUFA.',BRAVA,'2021-10-22','DOCUMENTED_SOURCE_FACT'),
 ('NCT06111014',29,'Issuer discontinued latozinemab continuation after parent INFRONT-3 failure; no independent clinical efficacy result attributed to this continuation study.',ALEC,'2025-10-21','DOCUMENTED_SOURCE_FACT'),
 ('NCT04374136',4,'Clinical co-primary failure despite significant progranulin biomarker change; target engagement is distinct from clinical target validation.',ALEC,'2025-10-21','DOCUMENTED_SOURCE_FACT'),
 ('NCT04701164',17,'30 mg/kg MRC sum score day-8 p<.0001 and week-8 p=.0351; ventilation duration p=.0356. These secondary p-values are nominal in the issuer release, not multiplicity-adjusted.',ANNX,'2024-06-04','DOCUMENTED_SOURCE_FACT'),
 ('NCT04701164',18,'Exact-NCT poster reports EQ-5D-5L, rFSS and PGIC. PGIC adjusted OR day 8: 2.5 (95% CI 1.4-4.6), p=.0028; week 8: 1.4 (0.8-2.6), p=.2917. No independent meaningfulness or multiplicity grade.',ANNX_PRO,'2026-06-27','DOCUMENTED_SOURCE_FACT'),
 ('NCT03428360',18,'FDA review confirms caregiver electronic-diary usability and PedsQL 3.0 Epilepsy Module/Parent Proxy for ages 2-5. Instrument documentation is not proof of a meaningful benefit.',AQST,'2024-04-26','DOCUMENTED_SOURCE_FACT'),
 ('NCT03428360',20,'Primary outcome table reports 18 participants with serious TEAEs, adverse-events module reports 17/130 with SAEs. Time window/TEAE versus SAE definitions require reconciliation; neither value silently replaced.', 'https://clinicaltrials.gov/study/NCT03428360','2021-08-05','REQUIRES_INTERPRETATION'),
 ('NCT07795164',28,'PERFORMA initiation release states FDA feedback informed registrational design; intended 52-week histology interim analysis and longer-term clinical outcomes are plans, not Phase 3 success.',ALT,'2026-08-03','DOCUMENTED_SOURCE_FACT'),
 ('NCT00538915',1,'Registry NABI-7101 SBI rate is .035 per person-year in ITT 58, safety population 63. FDA archived review reports threshold success, but undated review and later-label .037/CI .101 differences require dated source/analysis reconciliation before new binary adjudication.','https://clinicaltrials.gov/study/NCT00538915',registry['NCT00538915']['protocolSection']['statusModule']['lastUpdatePostDateStruct']['date'],'REQUIRES_INTERPRETATION'),
 ]
 for n,q,t,url,date,status in details:fact(n,q,t,url,date,status)
 # Regulatory links require exact FDA identity. A source about a planned filing
 # is retained as a fact but does not create an application-link record.
 regulatory={
  'NCT01814800':('BLA_125590_ASCENIV_PIDD','FDA_APPROVED_HISTORICAL','2019-04-01','https://www.fda.gov/media/122533/download','FDA approval letter expressly names NCT01814800 and BLA 125590. Historical April 1, 2019 approval; no future goal date.'),
  'NCT03428360':('NDA_218623_LIBERVANT_EPILEPSY_AGE_2_5','FDA_REVIEW_DOCUMENTED_HISTORICAL','2024-04-26',AQST,'FDA clinical review table expressly identifies 42-1703 / NCT03428360 as supportive safety evidence for NDA 218623. This review is not itself an approval letter or proof of efficacy in all enrolled ages.'),
 }
 by_nct={r['nctId']:r for r in ir['records']}
 for n,c in trial_company.items():
  if n not in by_nct:
   v=verdicts.get(n);p=registry[n]['protocolSection'];source_date=p['statusModule']['lastUpdatePostDateStruct']['date']
   by_nct[n]=dict(nctId=n,ticker=c['ticker'],company=c['company'],study=baseline_protocols[n],
    drug='; '.join(i['name'] for i in p.get('armsInterventionsModule',{}).get('interventions',[]) if i.get('type') in ['DRUG','BIOLOGICAL']),
    sourceDate=v[2] if v else source_date,companyUrl=v[1] if v and 'clinicaltrials.gov' not in v[1] else '',
    specificEvidence=v[3] if v else 'Company website and exact-NCT registry reviewed; no independent final efficacy verdict added.',
    crosswalk='Exact registry '+n+' = '+baseline_protocols[n])
  if n in regulatory:
   program,status,date,url,t=regulatory[n];by_nct[n].update(regulatoryProgramId=program,
    regulatoryEvidenceStatus=status,regulatoryEvidenceUrl=url,regulatorySourceDate=date,
    regulatoryEvidence=t,regulatoryReviewType='STANDARD')
   fact(n,30,t,url,date)
 # Ensure every company has an explicit resumable search record and hard-case list.
 hard={
  'ABVX':['NCT02249988 / ABX203-002: final trial-specific endpoint table not located after archived 2016/2017 releases and registry search. Interim futility is documented; no final verdict invented.'],
  'AGEN':['NCT00126178 / C-100-12 Part 2: no separate outcome located. Part 1 NCT00033904 results must not be borrowed. Older Antigenics sponsor name searched.'],
  'ADMA':['NCT00538915 / NABI-7101: old manufacturer/sponsor and undated FDA review versus later label analysis differ. Need a dated exact-analysis crosswalk for binary verdict; registry observations retained.'],
 }
 log=[]
 for c in queue['companies']:
  if c['ticker'] not in COMPANIES:continue
  ticker=c['ticker'];c.update(officialInvestorRelationsUrl=COMPANIES[ticker][0],searchStatus='PARTIALLY_REVIEWED')
  extra=hard.get(ticker,[])
  c['blockers']=list(dict.fromkeys(c['blockers']+extra))
  for t in c['trials']:
   n=t['nctId'];t.update(identityMatched=True,assessmentReviewStatus='PARTIALLY_REVIEWED',questionReview=[dict(number=q,status=facts.get((n,q),{}).get('classification','NOT_YET_REVIEWED')) for q in range(1,31)])
  log.append(dict(ticker=ticker,company=c['company'],trials=len(c['trials']),reviewedAt='2026-11-06',
   status='PARTIAL_SOURCE_REVIEW',officialInvestorRelationsUrl=COMPANIES[ticker][0],manufacturerUrl=COMPANIES[ticker][1],
   exactRegistryTrials=[t['nctId'] for t in c['trials']],requiresUserDirection=bool(extra),hardToResolve=extra,
   scope='Manufacturer/IR source pass completed; not all 30 scientific judgments completed. Registry and no-result statuses are distinct from absent public information.'))
 ir['assessmentRecords']=list(facts.values());ir['records']=list(by_nct.values())
 ir['trialCount']=len(ir['records']);ir['companyCount']=len({r['ticker'] for r in ir['records']})
 ir['regulatoryApplicationLinkCount']=sum(bool(r.get('regulatoryEvidenceStatus')) for r in ir['records'])
 ir['regulatoryApplicationProgramCount']=len({r['regulatoryProgramId'] for r in ir['records'] if r.get('regulatoryProgramId')})
 endpoints['records']=list(existing.values());endpoints['totalReviewed']=len(existing)
 endpoints['counts']={k:sum(r['endpointOutcome']==k for r in existing.values()) for k in endpoints['counts']}
 write('phase3CompanyWebsiteEvidence20261105.json',ir);write('phase3EndpointAdjudications20261105.json',endpoints)
 write('phase3InvestorRelationsResearchQueue20261106.json',queue)
 write('phase3CompanyBatchRegistrySources20261106.json',dict(asOf='2026-11-06',scope='Exact trial snapshots, no forecasts',records=raw))
 write('phase3CompanyWebsiteSearchLog20261106.json',dict(asOf='2026-11-06',companyUniverse=len(queue['companies']),
  policy='Incremental company passes; unsearched companies remain pending. Hard cases are not NOT_PUBLICLY_DISCLOSED.',
  discoverySources=['https://www.biopharmawatch.com/PDUFA-calendar','https://www.fdatracker.com/fda-calendar/','https://www.assyro.com/tools/pdufa-calendar/2026','https://checkrare.com/2026-orphan-drugs-pdufa-dates-and-fda-approvals/'],
  discoveryBlockers=['FDA Tracker enhanced calendar requires login; public alternatives used.'],companies=log))
 print(json.dumps(dict(companies=len(log),trials=len(raw),newAssessmentSlots=len(batch_keys),totalNormalizedSlots=len(facts),endpoints=endpoints['counts'],hardCompanies=list(hard))))


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source-dir',type=Path,default=Path('/tmp/company-recovery'))
 main(p.parse_args().source_dir)

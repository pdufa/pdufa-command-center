"""Reviewed issuer/scientific/FDA evidence; registry design facts remain separate."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'new-platform/frontend/data'
def read(name): return json.loads((ROOT/name).read_text())
def write(name,value): (ROOT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
ir=read('phase3CompanyWebsiteEvidence20261105.json')
adjudications=read('phase3EndpointAdjudications20261105.json')
queue=read('phase3InvestorRelationsResearchQueue20261106.json')
registry={r['nctId']:r for r in read('phase3PopulationGeography20261106.json')['records']}
IR='https://ir.ionis.com/news-releases/news-release-details/'
BALANCE='https://www.sec.gov/Archives/edgar/data/874015/000114036124018449/ef20026226_ex99-1.htm'
OASIS=IR+'ionis-presents-positive-results-oasis-hae-and-oasisplus-studies'
NEURO=IR+'eplontersen-phase-3-results-published-jama-show-consistent-and'
CARDIO='https://ir.ionispharma.com/news-releases/news-release-details/update-cardio-ttransform-phase-3-trial-eplontersen-adults'
CORE='https://ir.ionis.com/static-files/ca2193a5-e267-4261-b57c-ab1315aa5fad'
FDACORE='https://www.accessdata.fda.gov/drugsatfda_docs/label/2026/218614s004lbl.pdf'
FDABALANCE='https://www.fda.gov/drugs/drug-trials-snapshots/drug-trials-snapshot-tryngolza'
FDAOASIS='https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/219407s000lbl.pdf'
FDANEURO='https://www.fda.gov/drugs/drug-trials-snapshots/drug-trials-snapshots-wainua'
SAVARA='https://investors.savarapharma.com/news/news-details/2026/Savara-Reports-Second-Quarter-2026-Financial-Results-and-Provides-Business-Update/default.aspx'

rows=[
 ('NCT04568434','BALANCE','ISIS 678354-CS3','olezarsen','2024-04-07',BALANCE,'PRIMARY_ENDPOINT_MET',
  '80 mg monthly met six-month triglyceride primary comparison: placebo-adjusted -44%, p<0.001. The 50 mg comparison was not significant (-22%, p=0.078).',
  'SAEs: 80 mg 14%, 50 mg 19%, placebo 39%; no olezarsen-related serious TEAEs reported.'),
 ('NCT05139810','OASIS-HAE','ISIS 721744-CS5','donidalorsen','2024-05-31',OASIS,'PRIMARY_ENDPOINT_MET',
  'Primary monthly HAE attack-rate reduction versus placebo: 80 mg Q4W 81%, p<0.001; Q8W 55%, p=0.004 over weeks 1-25.',
  'No serious TEAEs related to donidalorsen; one Q8W participant discontinued for noncompliance and a TEAE. Not pooled with OASISplus.'),
 ('NCT04136184','NEURO-TTRansform','ION-682884-CS3','eplontersen','2023-09-28',NEURO,'PRIMARY_ENDPOINT_MET',
  'All three co-primary endpoints met versus an external placebo group. Week-66 mNIS+7 change +0.3 versus +25.1; difference -24.8 points, p<0.001.',
  ''),
 ('NCT04136171','CARDIO-TTRansform','ION-682884-CS2','eplontersen','2026-07-09',CARDIO,'PRIMARY_ENDPOINT_NOT_MET',
  'Primary composite of cardiovascular mortality and recurrent cardiovascular events through Week 140 did not meet statistical significance versus placebo.',
  'Issuer describes tolerability as consistent with previous results; no trial-specific SAE rate is supplied in this release.'),
 ('NCT05079919','CORE-TIMI 72a','ISIS 678354-CS5','olezarsen','2025-11-08',CORE,'PRIMARY_ENDPOINT_MET',
  'CORE six-month placebo-adjusted triglyceride reduction: 50 mg 63%, 80 mg 72%; each p<0.001. Trial-specific presentation table, not the pooled pancreatitis result.', ''),
 ('NCT05552326','CORE2-TIMI 72b','ISIS 678354-CS6','olezarsen','2025-11-08',CORE,'PRIMARY_ENDPOINT_MET',
  'CORE2 six-month placebo-adjusted triglyceride reduction: 50 mg 49%, 80 mg 55%; each p<0.001. Trial-specific presentation table, not the pooled pancreatitis result.', ''),
]
ids={r[0] for r in rows}|{'NCT04544293'}
facts=[]
def fact(nct,q,text,url,date,classification='DOCUMENTED_SOURCE_FACT',locator='Trial-specific section',**extra):
    facts.append(dict(nctId=nct,assessmentNumber=q,evidence=text,sourceUrl=url,publicationDate=date,
       classification=classification,sourceLocator=locator,reviewedAt='2026-11-06',
       evidenceScope='HISTORICAL_SOURCE_FACT_NOT_PREDICTION',**extra))

ir['records']=[r for r in ir['records'] if r['nctId'] not in ids]
adjudications['records']=[r for r in adjudications['records'] if r['nctId'] not in ids-{'NCT04544293'}]
for nct,study,protocol,drug,date,url,outcome,efficacy,safety in rows:
    if registry[nct]['sponsorProtocol']!=protocol:
        raise ValueError('EXACT_PROTOCOL_CROSSWALK_MISMATCH')
    crosswalk=f'Exact registry {nct}, sponsor protocol {protocol}; {study}, {drug}. Indication: '+ '; '.join(registry[nct]['conditions'])
    ir['records'].append(dict(nctId=nct,ticker='IONS',company='Ionis Pharmaceuticals',study=study,drug=drug,
        sourceDate=date,companyUrl=url,endpointInterpretation='PRIMARY_NOT_MET' if outcome.endswith('NOT_MET') else 'PRIMARY_MET',
        specificEvidence=efficacy,safetyEvidence=safety,crosswalk=crosswalk,
        regulatory='Application links are trial/indication specific; CARDIO failure cannot inherit polyneuropathy approval.'))
    adjudications['records'].append(dict(nctId=nct,endpointOutcome=outcome,rationale=efficacy,evidenceUrl=url,
        evidenceType='OFFICIAL_ISSUER_TRIAL_SPECIFIC_RESULTS',sourceDate=date,reviewedAt='2026-11-06',
        identityCrosswalk=crosswalk,identityEvidenceUrl=registry[nct]['sourceUrl'],
        qualification='Observed historical result, not a prospective prediction. Dose, external-comparator and pooled-program distinctions remain explicit.'))
    fact(nct,1,efficacy,url,date,'DOCUMENTED_PRIMARY_ENDPOINT_NOT_MET' if outcome.endswith('NOT_MET') else 'DOCUMENTED_PRIMARY_ENDPOINT_MET')
    fact(nct,29,f'{study} source-dated public results are available; no forecast inferred.',url,date)
    if safety: fact(nct,3,safety,url,date)

for nct,items,url,date in [
 ('NCT04568434',{
  5:'80 mg and 50 mg monthly doses tested; 80 mg primary comparison succeeded, 50 mg failed significance. Dose selection adequacy is ungraded.',
  17:'Acute pancreatitis episodes: placebo 11, 80 mg 1, 50 mg 1. Descriptive counts; confirmatory secondary inference is restricted by the gatekeeping plan.',
  21:'80 mg placebo-adjusted triglyceride reduction was 59% at 12 months; no extrapolation beyond trial follow-up.',
  23:'All-cause SAEs: 80 mg 14%, 50 mg 19%, placebo 39%; related serious TEAEs are a separate attribution category.'},BALANCE,'2024-04-07'),
 ('NCT05139810',{
  4:'Donidalorsen targets prekallikrein production; mechanistic rationale is documented, not numerically validated.',
  17:'Q4W reduction in mean monthly attacks over weeks 5-25 was 87%, p<0.001, a key secondary endpoint.',
  18:'AE-QoL measured patient-reported quality of life. OASISplus extension improvement is not substituted for OASIS-HAE results.',
  23:'No serious TEAEs related to donidalorsen in OASIS-HAE; this does not establish zero all-cause SAEs.',
  24:'One Q8W participant discontinued following noncompliance and a TEAE; OASISplus retention is a separate cohort.'},OASIS,'2024-05-31'),
 ('NCT04136171',{
  19:'Prespecified monotherapy subgroup HR 0.71 was nominally significant; no treatment effect in baseline stabilizer users. The overall primary endpoint remains failed.',
  11:'Placebo comparison on available standard care; 57% in each arm used a stabilizer at baseline and another 24% initiated one during follow-up.',
  28:'WAINUA polyneuropathy approval is a distinct indication from the failed ATTR cardiomyopathy study.'},CARDIO,'2026-07-09'),
 ('NCT04136184',{
  11:'Efficacy comparison uses external historical placebo from NEURO-TTR NCT01737398, not a concurrent placebo arm.',
  18:'Norfolk QoL-DN is a co-primary patient-reported outcome; week-66 improvement was assessed against historical placebo.'},NEURO,'2023-09-28'),
]:
    for q,text in items.items(): fact(nct,q,text,url,date)

# Plans were publicly uploaded after their nominal document dates. Do not use
# these retrieved versions as proof of what was available before readout.
for nct,url,docdate,items in [
 ('NCT04568434','https://cdn.clinicaltrials.gov/large-docs/34/NCT04568434/Prot_SAP_000.pdf','2023-08-02',{
  13:('Protocol 10.2, p68','Plan assumed TG change SD 46%, 14 per active dose and 14 pooled placebo, 90% power for a 60-point difference at two-sided alpha .05; about 60 enrolled planned.'),
  14:('Protocol 10.6.3.1, pp72-73','Primary TG analysis uses retrieved-dropout multiple imputation when sufficient data exist; otherwise jump-to-reference washout imputation. No robustness grade assigned.'),
  15:('Protocol 10.5, p69','Gatekeeping tests 80 mg then 50 mg. Confirmatory secondary testing requires both primary comparisons significant; 50 mg p=.078 limits secondary inference.')}),
 ('NCT05139810','https://cdn.clinicaltrials.gov/large-docs/10/NCT05139810/Prot_SAP_000.pdf','2022-07-12',{
  13:('Protocol 10.2, p61','Poisson-model simulations assumed 13.26 placebo versus 1.38 Q4W attacks per six months; 54 patients gave at least 90% power at alpha .05; approximately 84 planned including Q8W/dropouts.'),
  14:('SAP 4.9.1.3, pp22-23','Main attack-rate analysis uses time-adjusted observed rates; sensitivity uses jump-to-reference multiple imputation. AE-QoL uses MMRM without main-analysis imputation; J2R sensitivity is separate.'),
  15:('Protocol 10.5, p62; SAP 4.9.1.4','Hierarchical testing controls primary and secondary analyses at alpha .05. The protocol delegates the final secondary sequence to the SAP; no independent error-control adequacy score assigned.')}),
]:
    for q,(locator,text) in items.items():
        fact(nct,q,text,url,'2025-02-13',locator=locator,sourceDocumentDate=docdate,
             publicUploadDate='2025-02-13',chronologyQualification='Publicly posted post-readout; never prospective prediction input or proof of original preregistration.')

for nct,url,date,program,text in [
 ('NCT04568434',FDABALANCE,'2024-12-19','NDA_218614_TRYNGOLZA_FCS','FDA original approval for adult FCS explicitly names NCT04568434.'),
 ('NCT05139810',FDAOASIS,'2025-08-21','NDA_219407_DAWNZERA_HAE','FDA label section 14 explicitly names OASIS-HAE NCT05139810 for HAE prophylaxis age >=12.'),
 ('NCT04136184',FDANEURO,'2023-12-21','WAINUA_ATTRV_POLYNEUROPATHY','FDA original approval uses NEURO-TTRansform NCT04136184 for adult hereditary ATTR polyneuropathy, not cardiomyopathy.'),
 ('NCT05079919',FDACORE,'2026-06','NDA_218614_S004_TRYNGOLZA_SHTG','FDA June 2026 label section 14.2 identifies NCT05079919 as Trial 2 in the severe hypertriglyceridemia indication.'),
 ('NCT05552326',FDACORE,'2026-06','NDA_218614_S004_TRYNGOLZA_SHTG','FDA June 2026 label section 14.2 identifies NCT05552326 as Trial 3 in the severe hypertriglyceridemia indication.'),
]:
    r=next(r for r in ir['records'] if r['nctId']==nct)
    r.update(regulatoryProgramId=program,regulatoryEvidenceStatus='FDA_APPROVED_HISTORICAL',regulatoryReviewType='NOT_VERIFIED',
        regulatoryEvidence=text,regulatoryEvidenceUrl=url,regulatorySourceDate=date)
    # Keep the FDA event date distinct from webpage publication metadata or a
    # label's month-only revision. Never backdate a web snapshot to approval.
    published={'NCT04568434':'2026-05-01','NCT04136184':'2026-04-29','NCT05139810':'2025-08'}.get(nct,date)
    fact(nct,30,text+' Historical approval/label evidence is not a PDUFA goal date.',url,published,
         sourceEventDate=date,sourceDateKind='FDA_PAGE_PUBLICATION_METADATA_OR_LABEL_REVISION',
         **({'publicationDatePrecision':'MONTH'} if len(published)==7 else {}))

fact('NCT04568434',20,'Issuer readout reports a 44% placebo-adjusted reduction; FDA snapshot reports 42.5%. Source analysis/version differences require interpretation before assigning clinical-importance judgments.',
     FDABALANCE,'2026-05-01','REQUIRES_INTERPRETATION')

# Screenshot calendars supplied this lead; the dated issuer/SEC originals supply
# the evidence. Do not borrow IMPALA-2 efficacy for the extension/pediatric trials.
nct='NCT04544293'
endpoint=next(r for r in adjudications['records'] if r['nctId']==nct)
ir['records'].append(dict(nctId=nct,ticker='SVRA',company='Savara',study='IMPALA-2',drug='molgramostim',
 sourceDate='2026-08-11',companyUrl=SAVARA,endpointInterpretation='PRIMARY_MET',
 specificEvidence=endpoint['rationale'],safetyEvidence='',crosswalk='IMPALA-2 NCT04544293; exact registry molgramostim/autoimmune PAP identity and primary publication DOI 10.1056/NEJMoa2410542.',
 regulatory='As of August 11, 2026, issuer reported BLA review and November 22, 2026 target. No FDA outcome inferred.',
 regulatoryProgramId='MOLBREEVI_BLA_AUTOIMMUNE_PAP',regulatoryEvidenceStatus='ISSUER_REPORTED_BLA_UNDER_FDA_REVIEW',
 regulatoryReviewType='PRIORITY',regulatoryEvidence='Dated issuer quarterly release reports MOLBREEVI BLA PDUFA target November 22, 2026; SEC Q2 10-Q describes three-month extension for a major amendment. Independent FDA correspondence and newer source freshness still require review.',
 regulatoryEvidenceUrl=SAVARA,regulatorySourceDate='2026-08-11',pdufaGoalDate='2026-11-22',
 pdufaEvidenceUrl='https://www.sec.gov/Archives/edgar/data/1160308/000119312526344585/svra-20260630.htm'))
fact(nct,30,'As of issuer August 11, 2026 disclosure, MOLBREEVI BLA target is November 22, 2026 following a major-amendment extension. This is issuer-reported, not independently FDA-confirmed or a numerical forecast.',SAVARA,'2026-08-11')
fact(nct,4,'Molgramostim supplies GM-CSF activity; autoimmune PAP involves neutralizing GM-CSF antibodies and impaired macrophage surfactant clearance. Mechanistic documentation, not target-validation score.',SAVARA,'2026-08-11')

ir['assessmentRecords']=[r for r in ir['assessmentRecords'] if r['nctId'] not in ids]+facts
ir['trialCount']=len(ir['records']);ir['companyCount']=len({r['ticker'] for r in ir['records']})
ir['regulatoryApplicationLinkCount']=sum(bool(r.get('regulatoryEvidenceStatus')) for r in ir['records'])
ir['regulatoryApplicationProgramCount']=len({r['regulatoryProgramId'] for r in ir['records'] if r.get('regulatoryProgramId')})
adjudications['totalReviewed']=len(adjudications['records'])
adjudications['counts']={k:sum(r['endpointOutcome']==k for r in adjudications['records']) for k in adjudications['counts']}
for company in queue['companies']:
    if company['ticker'] not in ['IONS','SVRA']:continue
    company['officialInvestorRelationsUrl']='https://ir.ionis.com/' if company['ticker']=='IONS' else 'https://investors.savarapharma.com/'
    company['searchStatus']='PARTIALLY_REVIEWED'
    for trial in company['trials']:
        if trial['nctId'] not in ids:continue
        trial.update(identityMatched=True,assessmentReviewStatus='PARTIALLY_REVIEWED',
          questionReview=[dict(number=q,status=next((f['classification'] for f in facts if f['nctId']==trial['nctId'] and f['assessmentNumber']==q),'NOT_YET_REVIEWED')) for q in range(1,31)])
write('phase3CompanyWebsiteEvidence20261105.json',ir)
write('phase3EndpointAdjudications20261105.json',adjudications)
write('phase3InvestorRelationsResearchQueue20261106.json',queue)
print(json.dumps(dict(newQuestionRecords=len(facts),endpointOutcomes=adjudications['counts'],trialLinks=ir['regulatoryApplicationLinkCount'],programs=ir['regulatoryApplicationProgramCount'])))

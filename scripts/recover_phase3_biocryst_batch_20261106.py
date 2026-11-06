"""Append a second source-reviewed issuer batch; retain first-batch provenance."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1] / 'new-platform/frontend/data'
def read(name): return json.loads((root/name).read_text())
def write(name, value): (root/name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
ir = read('phase3CompanyWebsiteEvidence20261105.json')
endpoints = read('phase3EndpointAdjudications20261105.json')
queue = read('phase3InvestorRelationsResearchQueue20261106.json')
facts = []
rows = [
    ('NCT03485911', 'APeX-2', 'BCX7353-302', 'berotralstat (BCX7353)', '2019-05-21',
     'https://www.sec.gov/Archives/edgar/data/882796/000117184319003529/exh_991.htm',
     'PRIMARY_ENDPOINT_MET', '24-week attack-rate reduction versus placebo: 150 mg 44%, p<0.001; 110 mg 30%, p=0.024.',
     'No drug-related SAEs reported. Diarrhea: 110 mg 7.3%, 150 mg 10%, placebo 0% (drug-related events).'),
    ('NCT02303626', 'OPuS-2', 'BCX4161-301', 'avoralstat (BCX4161)', '2016-02-08',
     'https://www.sec.gov/Archives/edgar/data/882796/000117184316007701/f8k_020816.htm',
     'PRIMARY_ENDPOINT_NOT_MET', 'Neither 500 mg nor 300 mg three times daily significantly reduced mean HAE attack rate versus placebo over 12 weeks.', ''),
    ('NCT03873116', 'APeX-J', 'BCX7353-301', 'berotralstat (BCX7353)', '2020-12-23',
     'https://pubmed.ncbi.nlm.nih.gov/33247955/',
     'PRIMARY_ENDPOINT_MET', '150 mg reduced 24-week HAE attack rate: 1.11 versus 2.18 attacks/month, p=0.003. This result is specific to 150 mg; it does not establish 110 mg success.',
     'Among 13 berotralstat recipients across doses, nasopharyngitis occurred in 4 (31%); abdominal pain, cough, diarrhea and pyrexia each in 2 (15%).'),
]
def fact(nct, q, text, url, date, classification='DOCUMENTED_SOURCE_FACT'):
    facts.append(dict(nctId=nct, assessmentNumber=q, evidence=text, sourceUrl=url, publicationDate=date,
        classification=classification, sourceLocator='Trial-specific results', reviewedAt='2026-11-06',
        evidenceScope='HISTORICAL_SOURCE_FACT_NOT_PREDICTION'))
ids={r[0] for r in rows}
ir['records']=[r for r in ir['records'] if r['nctId'] not in ids]
endpoints['records']=[r for r in endpoints['records'] if r['nctId'] not in ids]
for nct, study, protocol, drug, date, url, status, efficacy, safety in rows:
    crosswalk=f'Official registry: {nct} = {protocol} = {study}; drug {drug}; indication HAE.'
    ir['records'].append(dict(nctId=nct, ticker='BCRX', company='BioCryst Pharmaceuticals', study=study,
        drug=drug, sourceDate=date, companyUrl=url, endpointInterpretation='PRIMARY_NOT_MET' if status.endswith('NOT_MET') else 'PRIMARY_MET',
        specificEvidence=efficacy, safetyEvidence=safety, regulatory='No cross-drug, cross-trial or cross-country FDA outcome inferred.', crosswalk=crosswalk))
    endpoints['records'].append(dict(nctId=nct, endpointOutcome=status, rationale=efficacy, evidenceUrl=url,
        evidenceType='PEER_REVIEWED_PHASE3_RESULTS' if study=='APeX-J' else 'OFFICIAL_ISSUER_TRIAL_SPECIFIC_RESULTS',
        reviewedAt='2026-11-06', sourceDate=date, identityCrosswalk=crosswalk,
        identityEvidenceUrl='https://clinicaltrials.gov/study/'+nct,
        qualification='Historical result only, no retrospective prediction. APeX-J is a separate 19-patient Japanese study; avoralstat is a separate drug from berotralstat.'))
    fact(nct, 1, efficacy, url, date, 'DOCUMENTED_PRIMARY_ENDPOINT_NOT_MET' if status.endswith('NOT_MET') else 'DOCUMENTED_PRIMARY_ENDPOINT_MET')
    fact(nct, 29, f'{study} source-specific results published {date}.', url, date)
    if safety: fact(nct, 3, safety, url, date)

nct, _, _, _, date, url, *_ = rows[0]
for q, text in {
    5:'110 mg and 150 mg once daily tested; 150 mg reduction 44%, 110 mg 30%. No optimal-dose score inferred.',
    17:'At 150 mg, 50% had >=70% reduction versus baseline, compared with 15% on placebo, p=0.002.',
    19:'Randomization stratified by baseline attack rate <2 versus >=2/month. Reported 150 mg reductions by stratum: 66% and 40%. Subgroup credibility ungraded.',
    23:'No drug-related SAEs reported; this does not mean zero all-cause SAEs.',
    24:'All 108 patients completing 24 weeks continued into the extension; this is conditional retention, not 100% retention of all randomized patients.',
    26:'Type I/II HAE patients recruited in United States, Canada and Europe; representativeness ungraded.',
}.items(): fact(nct, q, text, url, date)

label='https://www.accessdata.fda.gov/drugsatfda_docs/label/2020/214094s000lbl.pdf'
record=next(r for r in ir['records'] if r['nctId']==nct)
record.update(regulatoryProgramId='NDA_214094_ORLADEYO_HAE_PROPHYLAXIS',regulatoryEvidenceStatus='FDA_APPROVED_HISTORICAL',
    regulatoryReviewType='NOT_VERIFIED', regulatorySourceDate='2020-12-03',regulatoryEvidenceUrl=label,
    regulatoryEvidence='Original FDA label section 14 explicitly identifies APeX-2 NCT03485911 as Trial 1 supporting historical HAE prophylaxis approval in adults and patients aged >=12. Not acute treatment; not a new target date.')
for q,text in {
    4:'FDA describes plasma kallikrein inhibition reducing excess bradykinin generation in C1-inhibitor deficiency/dysfunction HAE; this is mechanistic documentation, not a target-validity grade.',
    6:'Original controlled study population: 66% female, 93% Caucasian, mean age 41.6; generalizability requires interpretation.',
    24:'FDA Trial 1 adverse-reaction discontinuation: 110 mg 7%, 150 mg 3%, placebo 3%. This differs from extension retention.',
    30:record['regulatoryEvidence'],
}.items():
    # One selected fact per question, with the fuller FDA discontinuation metric
    # replacing the conditional extension metric in the normalized slot.
    facts[:]=[r for r in facts if (r['nctId'],r['assessmentNumber'])!=(nct,q)]
    fact(nct,q,text,label,'2020-12-03')

j=rows[2]
for q,text in {12:'19 randomized: 110 mg n=6, 150 mg n=7, placebo n=6.',
               22:'Nasopharyngitis in 4/13 berotralstat recipients across both doses; not a 150 mg-specific rate.',
               26:'Japanese trial population; no global population inference.'}.items():fact(j[0],q,text,j[5],j[4])
ir['assessmentRecords']=[r for r in ir['assessmentRecords'] if r['nctId'] not in ids]+facts
ir['trialCount']=len(ir['records']);ir['companyCount']=len({r['ticker'] for r in ir['records']})
ir['regulatoryApplicationLinkCount']=sum(bool(r.get('regulatoryEvidenceStatus')) for r in ir['records'])
ir['regulatoryApplicationProgramCount']=len({r['regulatoryProgramId'] for r in ir['records'] if r.get('regulatoryProgramId')})
endpoints['totalReviewed']=len(endpoints['records'])
endpoints['counts']={s:sum(r['endpointOutcome']==s for r in endpoints['records']) for s in endpoints['counts']}
company=next(c for c in queue['companies'] if c['ticker']=='BCRX')
company['officialInvestorRelationsUrl']='https://ir.biocryst.com/'
company['searchStatus']='PARTIALLY_REVIEWED'
for trial in company['trials']:
    trial['identityMatched']=trial['nctId'] in ids
    trial['assessmentReviewStatus']='PARTIALLY_REVIEWED' if trial['nctId'] in ids else 'NOT_YET_REVIEWED'
    trial['questionReview']=[dict(number=q,status=next((r['classification'] for r in facts if r['nctId']==trial['nctId'] and r['assessmentNumber']==q),'NOT_YET_REVIEWED')) for q in range(1,31)]
write('phase3CompanyWebsiteEvidence20261105.json',ir)
write('phase3EndpointAdjudications20261105.json',endpoints)
write('phase3InvestorRelationsResearchQueue20261106.json',queue)
print(json.dumps(dict(facts=len(facts),outcomes=endpoints['counts'],links=ir['regulatoryApplicationLinkCount'])))

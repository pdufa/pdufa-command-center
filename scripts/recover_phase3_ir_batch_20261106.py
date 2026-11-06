"""Idempotent, reviewed Ardelyx batch. No network inference or numerical scoring."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'new-platform/frontend'
DATA = ROOT / 'data'

def read(path):
    return json.loads(path.read_text())

def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

ir = read(DATA / 'phase3CompanyWebsiteEvidence20261105.json')
endpoints = read(DATA / 'phase3EndpointAdjudications20261105.json')
ledger = read(ROOT / 'public/phase3-unified-classifications-2026-11-05.json')
release = 'https://ir.ardelyx.com/news-releases/news-release-details/'
sec = 'https://www.sec.gov/Archives/edgar/data/1437402/'
fda_ibs = 'https://www.accessdata.fda.gov/drugsatfda_docs/label/2019/211801s000lbl.pdf'
fda_x = 'https://www.accessdata.fda.gov/drugsatfda_docs/nda/2024/213931Orig1s000Lbl.pdf'
paper = 'https://pmc.ncbi.nlm.nih.gov/articles/PMC8183489/'
rows = [
    ('NCT02621892', 'T3MPO-1', 'TEN-01-301', '2017-05-12',
     release + 'ardelyx-reports-successful-phase-3-t3mpo-1-trial-tenapanor',
     'Composite response 27.0% versus 18.7%, p=0.02, over at least 6/12 weeks.',
     'Diarrhea 14.6% versus 1.7%; diarrhea discontinuations 5.9% versus 0.6% (preliminary issuer results).'),
    ('NCT02686138', 'T3MPO-2', 'TEN-01-302', '2017-10-11',
     sec + '000119312517307919/d648753d8k.htm',
     'Composite response 36.5% versus 23.7%, p<0.001, over at least 6/12 weeks.',
     'Diarrhea 16.0% versus 3.7%; placebo-adjusted diarrhea discontinuation rate 5.8 percentage points.'),
    ('NCT03427125', 'PHREEDOM', 'TEN-02-301', '2019-12-03',
     sec + '000119312519304803/d843175d8k.htm',
     'Enriched efficacy set (n=131): withdrawal-period phosphorus LS mean difference -1.4 mg/dL, p<0.0001.',
     'Open-label diarrhea discontinuations 16%; withdrawal period 0.8%. Open-label SAE rates 17.2% tenapanor versus 22.6% sevelamer.'),
    ('NCT03824587', 'AMPLIFY', 'TEN-02-202', '2019-09-03',
     release + 'ardelyx-announces-positive-results-pivotal-phase-3-amplify-study',
     'Week-4 phosphorus reduction 0.84 versus 0.19 mg/dL with background binders, p=0.0004.',
     'Diarrhea discontinuations 2.6% versus 0.8%; no tenapanor-related SAEs reported.'),
]
facts = []
def fact(nct, q, text, url, date, status='DOCUMENTED_SOURCE_FACT', locator=''):
    facts.append(dict(nctId=nct, assessmentNumber=q, evidence=text, sourceUrl=url,
                      publicationDate=date, classification=status, sourceLocator=locator,
                      reviewedAt='2026-11-06', evidenceScope='HISTORICAL_SOURCE_FACT_NOT_PREDICTION'))

for nct, study, protocol, date, url, efficacy, safety in rows:
    crosswalk = f'{study} = {protocol} = {nct}; FDA label section 14 explicitly identifies protocol and NCT.'
    record = dict(nctId=nct, ticker='ARDX', company='Ardelyx', study=study, drug='tenapanor',
                  sourceDate=date, companyUrl=url, endpointInterpretation='PRIMARY_MET',
                  specificEvidence=efficacy, safetyEvidence=safety, crosswalk=crosswalk,
                  regulatory='Historical application evidence is separate from the clinical endpoint; no future target date inferred.')
    ir['records'] = [r for r in ir['records'] if r['nctId'] != nct] + [record]
    endpoint = dict(nctId=nct, endpointOutcome='PRIMARY_ENDPOINT_MET', rationale=efficacy,
                    evidenceUrl=url, evidenceType='OFFICIAL_ISSUER_TRIAL_SPECIFIC_RESULTS',
                    sourceDate=date, reviewedAt='2026-11-06', identityCrosswalk=crosswalk,
                    identityEvidenceUrl=fda_ibs if study.startswith('T3') else fda_x,
                    qualification='Historical issuer result; no retrospective prediction. ' +
                    ('Primary analysis is enriched, not the full randomized population.' if study == 'PHREEDOM' else
                     'Primary success does not establish success of every secondary endpoint.'))
    endpoints['records'] = [r for r in endpoints['records'] if r['nctId'] != nct] + [endpoint]
    fact(nct, 1, efficacy, url, date, 'DOCUMENTED_PRIMARY_ENDPOINT_MET')
    fact(nct, 3, safety, url, date)
    fact(nct, 24, safety, url, date)
    fact(nct, 29, f'{study} trial-specific readout published {date}.', url, date)

fact('NCT02621892', 17, 'CSBM 6/12-week secondary response: 33.9% versus 29.4%, p=0.27; primary success does not resolve this secondary failure.', rows[0][4], rows[0][3])
fact('NCT02621892', 21, 'Durable composite responders: 13.0% versus 3.3%, p<0.001 (9/12 weeks including at least 3/4 final weeks).', rows[0][4], rows[0][3])
fact('NCT02686138', 17, 'CSBM 6/12-week response 47.4% versus 33.3%, p<0.001; pain response 49.8% versus 38.3%, p=0.004.', rows[1][4], rows[1][3])
fact('NCT02686138', 21, 'Durable composite response 18.1% versus 5.0%, p<0.001.', rows[1][4], rows[1][3])
fact('NCT02686138', 22, 'Nasopharyngitis 4.4% versus 3.7%; descriptive issuer AE data.', rows[1][4], rows[1][3])
fact('NCT03427125', 6, 'Primary efficacy set required completion of 26 weeks and phosphorus reduction >=1.2 mg/dL; not all randomized participants.', rows[2][4], rows[2][3])
fact('NCT03427125', 23, 'Open-label SAE rates: 17.2% tenapanor (n=419), 22.6% sevelamer (n=137).', rows[2][4], rows[2][3])
fact('NCT03427125', 28, 'Issuer reports FDA accepted the enriched primary efficacy analysis set; historical issuer statement, not independent correspondence review.', rows[2][4], rows[2][3])
fact('NCT03824587', 17, 'Week-4 FGF23 reduction 22%-24%, p<=0.0027; all key secondary endpoints reported met.', rows[3][4], rows[3][3])
fact('NCT03824587', 23, 'Issuer reported no tenapanor-related serious adverse events; this is not zero all-cause SAEs.', rows[3][4], rows[3][3])
fact('NCT03824587', 5, 'Starting dose 30 mg twice daily, adjusted for phosphorus and GI tolerability; not proof of optimal dose.', rows[3][4], rows[3][3])

# Statistical methods are documentary facts, with a separate correction-review warning.
for q, text in {
    6: 'Rome III adults aged 18-75; applicability to routine practice needs interpretation.',
    13: 'Planned 300/arm; 95% power for a 15-point response difference, assuming active response >=45%.',
    14: 'Weekly missing days imputed from recorded-day average; <4 diary days meant nonresponse that week.',
    18: 'IBS-QOL measured at baseline and weeks 12 and 26; no clinical-importance score assigned.',
    23: 'Four tenapanor participants had SAEs; one diarrhea SAE possibly related; no deaths.',
    26: 'Study enrolled at 92 US centers; representativeness was not graded.',
}.items():
    fact('NCT02686138', q, text + ' Original 2021 report; later correction requires review.', paper, '2020-12-18', locator='Methods / Results')
for nct, pmid, date in [('NCT02686138','42447341','2026-07-14'), ('NCT03427125','42096282','2026-05-07')]:
    fact(nct, 15, 'A later publication correction is indexed. Its implications and multiplicity methods remain unreviewed; no absence-of-disclosure claim.',
         f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/', date, 'REQUIRES_INTERPRETATION')

# FDA-label crosswalks also recover a fifth trial's application linkage without
# extrapolating the other trials' primary analysis to it.
for nct, study, protocol in [('NCT02675998','BLOCK','TEN-02-201')]:
    ir['records'] = [r for r in ir['records'] if r['nctId'] != nct] + [dict(
        nctId=nct, ticker='ARDX', company='Ardelyx', study=study, drug='tenapanor',
        sourceDate='2023-10-17', companyUrl='', endpointInterpretation='NOT_YET_REVIEWED',
        specificEvidence='FDA label supplies exact NCT/protocol identity; original primary analysis remains to be reviewed.',
        safetyEvidence='', regulatory='Historical application crosswalk only.',
        crosswalk=f'FDA section 14: {protocol} = {nct}.')]

for r in ir['records']:
    if r['nctId'] not in {x[0] for x in rows} | {'NCT02675998'}:
        continue
    ibs = r['nctId'] in ['NCT02621892','NCT02686138']
    r.update(regulatoryProgramId='NDA_211801_IBSRELA_ADULT_IBSC' if ibs else 'NDA_213931_XPHOZAH_CKD_DIALYSIS',
             regulatoryEvidenceStatus='FDA_APPROVED_HISTORICAL', regulatoryReviewType='NOT_VERIFIED',
             regulatoryEvidence='FDA label section 14 identifies this exact trial in the approved ' +
                 ('adult IBS-C program.' if ibs else 'CKD dialysis hyperphosphatemia program; indication is add-on use for inadequate binder response or intolerance.'),
             regulatoryEvidenceUrl=fda_ibs if ibs else fda_x,
             regulatorySourceDate='2019-09-12' if ibs else '2023-10-17')
    fact(r['nctId'], 30, r['regulatoryEvidence'] + ' Approval is historical; PDUFA goal date is not inferred.',
         r['regulatoryEvidenceUrl'], r['regulatorySourceDate'])

# Continue to the next issuer documents without promoting pooled program safety.
safety_url = release + 'ardelyx-successfully-completes-t3mpo-3-safety-extension-study'
accel_url = release + 'ardelyx-completes-enrollment-phase-3-accel-clinical-trial'
for nct, study, protocol, date, url, text in [
    ('NCT02727751', 'T3MPO-3', 'TEN-01-303', '2018-01-03', safety_url,
     'Issuer interim cohort: 240 treated; diarrhea 9.2%; diarrhea discontinuation 1.7%. Not the later 312-patient publication population.'),
    ('NCT07382167', 'ACCEL', 'TEN-03-301', '2026-11-03', accel_url,
     'Issuer reports enrollment complete; topline data expected in second half of 2027. Expected readout is not a PDUFA date or outcome.'),
]:
    ir['records'] = [r for r in ir['records'] if r['nctId'] != nct] + [dict(
        nctId=nct, ticker='ARDX', company='Ardelyx', study=study, drug='tenapanor', sourceDate=date,
        companyUrl=url, endpointInterpretation='NO_BINARY_PASS_FAIL' if study=='T3MPO-3' else 'NOT_YET_REVIEWED',
        specificEvidence=text, safetyEvidence=text if study=='T3MPO-3' else '',
        regulatory='No application or PDUFA linkage inferred from another indication.',
        crosswalk=f'{study} = {protocol} = {nct}; official registry acronym and protocol crosswalk. Scientific publication PMID 37668173 also identifies T3MPO-3.')]
    if study=='T3MPO-3':
        fact(nct, 3, text, url, date)
        fact(nct, 24, text, url, date)
        fact(nct, 29, 'Open-label long-term safety readout, without a binary efficacy hypothesis.', url, date)
        fact(nct, 1, 'Descriptive open-label safety extension, not a binary controlled efficacy trial.',
             'https://pubmed.ncbi.nlm.nih.gov/37668173/', '2023-09-05', 'DOCUMENTED_NON_BINARY_ENDPOINT')
        fact(nct, 15, 'Later correction PMID 42252906 and differing interim/publication denominators require review; multiplicity is not adjudicated.',
             'https://pubmed.ncbi.nlm.nih.gov/37668173/', '2023-09-05', 'REQUIRES_INTERPRETATION')
        endpoints['records'] = [r for r in endpoints['records'] if r['nctId'] != nct] + [dict(
            nctId=nct, endpointOutcome='NO_BINARY_PASS_FAIL', rationale='T3MPO-3 is an open-label safety extension without a binary efficacy hypothesis.',
            evidenceUrl='https://pubmed.ncbi.nlm.nih.gov/37668173/', evidenceType='PEER_REVIEWED_SAFETY_EXTENSION',
            sourceDate='2023-09-05', reviewedAt='2026-11-06', qualification='Not an efficacy PASS. Later correction and interim versus final denominator differences remain under review.')]
    else:
        fact(nct, 29, text, url, date)
        fact(nct, 12, 'Enrollment complete per issuer; no success forecast follows.', url, date)
        fact(nct, 28, 'IBSRELA is not approved for CIC according to this dated issuer disclosure; adult IBS-C approval does not transfer.', url, date)
ir['assessmentRecords'] = [r for r in ir.get('assessmentRecords',[]) if r['nctId'] not in {x[0] for x in rows} | {'NCT02675998','NCT02727751','NCT07382167'}] + facts
ir['lastResearchDate'] = '2026-11-06'
ir['trialCount'] = len(ir['records'])
ir['companyCount'] = len({r['ticker'] for r in ir['records']})
ir['regulatoryApplicationLinkCount'] = sum(bool(r.get('regulatoryEvidenceStatus')) for r in ir['records'])
ir['regulatoryApplicationProgramCount'] = len({r['regulatoryProgramId'] for r in ir['records'] if r.get('regulatoryProgramId')})
ir['regulatoryApplicationScope'] = 'Exact trial-to-drug/indication application links; historical approvals are not future PDUFA dates or trial efficacy verdicts.'
endpoints['totalReviewed'] = len(endpoints['records'])
endpoints['counts'] = {s:sum(r['endpointOutcome']==s for r in endpoints['records']) for s in ['PRIMARY_ENDPOINT_MET','PRIMARY_ENDPOINT_NOT_MET','NO_BINARY_PASS_FAIL']}
write(DATA / 'phase3CompanyWebsiteEvidence20261105.json', ir)
write(DATA / 'phase3EndpointAdjudications20261105.json', endpoints)

# A resumable queue enumerates every census NCT without falsely claiming review.
queue = dict(schemaVersion=1, asOf='2026-11-06', baselineCommit='a7cc2e0c8e4131c3f1885ab00e7a057b70d5c0f1',
             baselineLiveAudit='https://pdufa-new-dashboard.vercel.app/api/phase3-missing-data-audit',
             baselineUnscored=14675, scope='Every census trial; review status does not imply numerical scoring.', companies=[])
queue_path = DATA / 'phase3InvestorRelationsResearchQueue20261106.json'
previous_companies = {c['ticker']:c for c in read(queue_path)['companies']} if queue_path.exists() else {}
for ticker in sorted({r['ticker'] for r in ledger['rows']}):
    if ticker != 'ARDX' and ticker in previous_companies:
        queue['companies'].append(previous_companies[ticker])
        continue
    trials = [r for r in ledger['rows'] if r['ticker']==ticker]
    existing = [r for r in ir['records'] if r['ticker']==ticker]
    matched = {r['nctId'] for r in existing}
    queue['companies'].append(dict(ticker=ticker, company=trials[0]['company'],
        officialInvestorRelationsUrl='https://ir.ardelyx.com/' if ticker=='ARDX' else None,
        searchStatus='PARTIALLY_REVIEWED' if ticker=='ARDX' else 'LEGACY_EVIDENCE_PRESENT_REVIEW_NOT_RECONSTRUCTED' if existing else 'NOT_YET_REVIEWED',
        trials=[dict(nctId=r['nctId'], identityMatched=r['nctId'] in matched,
                     assessmentReviewStatus='PARTIALLY_REVIEWED' if r['nctId'] in matched else 'NOT_YET_REVIEWED',
                     questionReview=[dict(number=q, status=next((f['classification'] for f in facts if f['nctId']==r['nctId'] and f['assessmentNumber']==q), 'NOT_YET_REVIEWED')) for q in range(1,31)] if ticker=='ARDX' else []) for r in trials],
        blockers=['IR T3MPO-2 and PHREEDOM pages returned HTTP 403 in web tool; official SEC 8-K fallback read.',
                  'Later T3MPO-2 and PHREEDOM publication corrections need full-text review.'] if ticker=='ARDX' else []))
write(DATA / 'phase3InvestorRelationsResearchQueue20261106.json', queue)
print(json.dumps(dict(trials=ir['trialCount'], facts=len(facts), endpoints=endpoints['counts'], links=ir['regulatoryApplicationLinkCount'])))
